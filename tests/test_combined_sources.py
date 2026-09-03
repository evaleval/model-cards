from __future__ import annotations

from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.combined_sources import (
    CombinedSourceError,
    combine_source_document_catalogs,
)
from model_cards.models import RelationToTarget
from model_cards.official_discovery import discover_official_sources
from model_cards.official_documents import build_official_document_catalog
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
from model_cards.source_documents import build_source_document_catalog


COMMIT = "a" * 40
CODE_URL = "https://github.com/acme/model"


class HubAdapter:
    def __init__(self, suffix: str = "") -> None:
        self.suffix = suffix

    def resolve_revision(self, model_id, requested_revision):
        return COMMIT

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(
            FetchStatus.OK,
            json.dumps(
                {
                    "id": model_id,
                    "sha": revision,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode(),
        )

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(FetchStatus.OK, f"[Code]({CODE_URL}){self.suffix}".encode())
        if repo_path == "config.json":
            return RemoteObject(FetchStatus.OK, b'{"model_type":"acme"}')
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class OfficialAdapter:
    def fetch(self, url, *, max_bytes, max_redirects):
        if url != CODE_URL:
            return OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE, reason_code="not_provided"
            )
        return OfficialRemoteObject(
            OfficialFetchStatus.OK,
            content=b"Official developer documentation.",
            final_url=url,
            redirect_chain=(url,),
            media_type="text/plain",
        )


class CombinedSourceTests(unittest.TestCase):
    def catalogs(self, suffix: str = ""):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        hf_root = root / "hf"
        collect_hf_source_bundle("acme/model", hf_root, HubAdapter(suffix))
        replayed_hf = replay_source_bundle(hf_root)
        discovery = discover_official_sources(replayed_hf)
        official_root = root / "official"
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
            official_root,
            OfficialAdapter(),
            relation_assertions=assertions,
        )
        return (
            build_source_document_catalog(replayed_hf),
            build_official_document_catalog(replay_official_sources(official_root)),
        )

    def test_combines_exact_linked_catalogs_without_serializing_bodies(self) -> None:
        hf, official = self.catalogs()
        combined = combine_source_document_catalogs(hf, official)
        self.assertEqual(hf.target, combined.target)
        self.assertEqual(len(hf.records) + len(official.records), len(combined.records))
        self.assertEqual(
            len(hf.documents) + len(official.documents), len(combined.documents)
        )
        self.assertEqual(set(item.source_id for item in combined.documents), set(combined.by_id))
        serialized = combined.canonical_bytes().decode()
        self.assertNotIn("Official developer documentation", serialized)
        self.assertNotIn("[Code]", serialized)
        self.assertEqual(combined.to_dict(), json.loads(serialized))
        second = combine_source_document_catalogs(hf, official)
        self.assertEqual(combined.catalog_sha256, second.catalog_sha256)
        self.assertEqual(combined.bundle_id, second.bundle_id)
        with self.assertRaises(FrozenInstanceError):
            combined.bundle_id = "changed"

    def test_rejects_official_catalog_discovered_from_another_hub_bundle(self) -> None:
        hf, official = self.catalogs()
        other_hf, _ = self.catalogs("\nDifferent frozen README bytes.")
        self.assertEqual(hf.target, other_hf.target)
        self.assertNotEqual(hf.bundle_id, other_hf.bundle_id)
        with self.assertRaisesRegex(CombinedSourceError, "another Hub bundle"):
            combine_source_document_catalogs(other_hf, official)


if __name__ == "__main__":
    unittest.main()
