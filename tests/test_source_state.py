from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.combined_sources import CombinedSourceDocumentCatalog
from model_cards.models import RelationToTarget
from model_cards.official_discovery import discover_official_sources
from model_cards.official_sources import (
    OfficialFetchStatus,
    OfficialRemoteObject,
    RelationAssertion,
    collect_official_sources,
    replay_official_sources,
)
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import SourceDocumentCatalog
from model_cards.source_state import (
    SourceStateError,
    SourceStateMode,
    load_source_state,
    reverify_source_state,
)


COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40
CODE_URL = "https://github.com/acme/model"
README_BODY = f"# Exact model\n\n[Code]({CODE_URL})\n"
OFFICIAL_BODY = "Official developer documentation for the exact model."


def canonical(value) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


class HubAdapter:
    def __init__(self, model_id: str, revision: str, suffix: str = "") -> None:
        self.model_id = model_id
        self.revision = revision
        self.suffix = suffix

    def resolve_revision(self, model_id, requested_revision):
        return self.revision

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(
            FetchStatus.OK,
            canonical(
                {
                    "id": self.model_id,
                    "sha": self.revision,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (README_BODY + self.suffix).encode("utf-8"),
            )
        if repo_path == "config.json":
            return RemoteObject(FetchStatus.OK, b'{"model_type":"fixture"}')
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class OfficialAdapter:
    def fetch(self, url, *, max_bytes, max_redirects):
        if url != CODE_URL:
            return OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE,
                reason_code="fixture_not_provided",
            )
        return OfficialRemoteObject(
            OfficialFetchStatus.OK,
            content=OFFICIAL_BODY.encode("utf-8"),
            final_url=url,
            redirect_chain=(url,),
            media_type="text/plain",
        )


class ImmutableSourceStateTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def hf_bundle(
        self,
        name: str,
        *,
        model_id: str = "acme/model",
        revision: str = COMMIT,
        suffix: str = "",
    ) -> Path:
        destination = self.root / name
        collect_hf_source_bundle(
            model_id,
            destination,
            HubAdapter(model_id, revision, suffix),
        )
        return destination

    def official_bundle(self, name: str, hf_bundle: Path) -> Path:
        replayed = replay_source_bundle(hf_bundle)
        discovery = discover_official_sources(replayed)
        destination = self.root / name
        assertions = tuple(
            RelationAssertion(
                candidate.record_id,
                discovery.target.model_id,
                RelationToTarget.EXACT_TARGET,
                candidate.declaring_source_id,
                candidate.declaration_locator,
                discovery.target.revision,
            )
            for candidate in discovery.records
            if candidate.normalized_url == CODE_URL
        )
        collect_official_sources(
            discovery,
            destination,
            OfficialAdapter(),
            relation_assertions=assertions,
        )
        return destination

    def pair(self, prefix: str = "primary") -> tuple[Path, Path]:
        hf = self.hf_bundle(prefix + "-hf")
        return hf, self.official_bundle(prefix + "-official", hf)

    def test_hf_only_preserves_existing_manifest_and_catalog_identities(self) -> None:
        hf = self.hf_bundle("hf-only")
        state = load_source_state(hf)
        replayed = replay_source_bundle(hf)
        expected_manifest_sha256 = hashlib.sha256(
            canonical(replayed.manifest.to_dict())
        ).hexdigest()

        self.assertEqual(SourceStateMode.HF_ONLY, state.mode)
        self.assertIsInstance(state.catalog, SourceDocumentCatalog)
        self.assertIsNone(state.official_catalog)
        self.assertIsNone(state.combined_catalog)
        self.assertEqual(replayed.manifest.bundle_id, state.hf_bundle_id)
        self.assertEqual(state.hf_bundle_id, state.active_catalog_bundle_id)
        self.assertEqual(state.hf_catalog.catalog_sha256, state.active_catalog_sha256)
        self.assertEqual(expected_manifest_sha256, state.hf_manifest_sha256)
        self.assertEqual(expected_manifest_sha256, state.snapshot_sha256)
        self.assertEqual(state.to_dict(), state.reverify().to_dict())

    def test_combined_state_builds_all_catalogs_and_body_free_identity(self) -> None:
        hf, official = self.pair()
        first = load_source_state(hf, official)
        second = load_source_state(hf, official)

        self.assertEqual(SourceStateMode.HF_AND_OFFICIAL, first.mode)
        self.assertIsInstance(first.hf_catalog, SourceDocumentCatalog)
        self.assertIsNotNone(first.official_catalog)
        self.assertIsInstance(first.combined_catalog, CombinedSourceDocumentCatalog)
        self.assertIs(first.combined_catalog, first.catalog)
        self.assertGreater(len(first.documents), len(first.hf_catalog.documents))
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.snapshot_sha256, second.snapshot_sha256)
        self.assertNotEqual(first.snapshot_sha256, first.hf_manifest_sha256)
        self.assertEqual(first.catalog.catalog_sha256, first.active_catalog_sha256)
        self.assertEqual(first.catalog.bundle_id, first.active_catalog_bundle_id)

        serialized = json.dumps(first.to_dict(), sort_keys=True)
        representation = repr(first)
        for forbidden in (
            README_BODY,
            OFFICIAL_BODY,
            str(self.root),
            "source-bundle-copy",
        ):
            self.assertNotIn(forbidden, serialized)
            self.assertNotIn(forbidden, representation)
        self.assertNotIn("documents", first.to_dict())
        self.assertNotIn("records", first.to_dict())
        verified = reverify_source_state(first)
        self.assertEqual(first.to_dict(), verified.to_dict())
        self.assertIsNot(first, verified)

    def test_rejects_target_and_hf_bundle_ancestry_mismatch(self) -> None:
        hf, official = self.pair()
        other_target = self.hf_bundle(
            "other-target",
            model_id="other/model",
            revision=OTHER_COMMIT,
        )
        with self.assertRaisesRegex(SourceStateError, "targets differ"):
            load_source_state(other_target, official)

        same_target_other_snapshot = self.hf_bundle(
            "other-snapshot",
            suffix="\nDifferent frozen bytes.\n",
        )
        self.assertNotEqual(
            replay_source_bundle(hf).manifest.bundle_id,
            replay_source_bundle(same_target_other_snapshot).manifest.bundle_id,
        )
        with self.assertRaisesRegex(SourceStateError, "another Hub bundle"):
            load_source_state(same_target_other_snapshot, official)

    def test_reverification_rejects_hf_content_mutation(self) -> None:
        hf = self.hf_bundle("mutable-hf")
        state = load_source_state(hf)
        replayed = replay_source_bundle(hf)
        stored = next(
            item.record.object_path
            for item in replayed.sources
            if item.record.object_path is not None
        )
        (hf / stored).write_bytes(b"mutated Hub bytes")
        with self.assertRaises(SourceStateError):
            state.reverify()

    def test_reverification_rejects_official_content_mutation(self) -> None:
        hf, official = self.pair("mutable")
        state = load_source_state(hf, official)
        replayed = replay_official_sources(official)
        stored = next(
            item.record.object_path
            for item in replayed.sources
            if item.record.object_path is not None
        )
        (official / stored).write_bytes(b"mutated official bytes")
        with self.assertRaises(SourceStateError):
            state.reverify()

    def test_rejects_symlinked_bundle_roots_and_symlink_swap_on_reverify(self) -> None:
        hf, official = self.pair("linked")
        hf_link = self.root / "hf-link"
        hf_link.symlink_to(hf, target_is_directory=True)
        with self.assertRaisesRegex(SourceStateError, "non-symlink"):
            load_source_state(hf_link)

        official_link = self.root / "official-link"
        official_link.symlink_to(official, target_is_directory=True)
        with self.assertRaisesRegex(SourceStateError, "non-symlink"):
            load_source_state(hf, official_link)

        state = load_source_state(hf, official)
        moved = self.root / "linked-hf-moved"
        hf.rename(moved)
        hf.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(SourceStateError, "non-symlink"):
            state.reverify()

    def test_reverification_requires_a_typed_state(self) -> None:
        with self.assertRaisesRegex(SourceStateError, "typed state"):
            reverify_source_state(object())  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
