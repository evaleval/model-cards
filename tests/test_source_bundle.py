from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from model_cards.source_bundle import (
    BundleIntegrityError,
    CollectionStatus,
    DeclarationStatus,
    FetchStatus,
    RelationToTarget,
    RemoteObject,
    RetrievalMode,
    SourceBundleError,
    SourceKind,
    collect_hf_source_bundle,
    parse_target_request,
    replay_source_bundle,
)


COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FakeHuggingFaceAdapter:
    def __init__(
        self,
        *,
        resolved_revision: str = COMMIT,
        metadata: RemoteObject | None = None,
        files: dict[str, RemoteObject] | None = None,
    ) -> None:
        self.resolved_revision = resolved_revision
        self.metadata = metadata or RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "id": "acme/Instruct",
                    "sha": resolved_revision,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )
        self.files = {
            "README.md": RemoteObject(FetchStatus.OK, b"# Exact model\n"),
            "config.json": RemoteObject(FetchStatus.OK, b"{\"model_type\":\"test\"}\n"),
        }
        if files:
            self.files.update(files)
        self.resolve_calls: list[tuple[str, str | None]] = []
        self.fetch_calls: list[tuple[str, str, str, int]] = []

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        self.resolve_calls.append((model_id, requested_revision))
        return self.resolved_revision

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        self.fetch_calls.append(("metadata", model_id, revision, max_bytes))
        return self.metadata

    def fetch_file(
        self, model_id: str, revision: str, repo_path: str, *, max_bytes: int
    ) -> RemoteObject:
        self.fetch_calls.append((repo_path, model_id, revision, max_bytes))
        return self.files.get(
            repo_path,
            RemoteObject(FetchStatus.MISSING, reason_code="not_found"),
        )


class SourceBundleTests(unittest.TestCase):
    def collect(self, adapter: FakeHuggingFaceAdapter, model_id: str = "acme/Instruct", **kwargs):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        destination = Path(temporary.name) / "bundle"
        manifest = collect_hf_source_bundle(
            model_id,
            destination,
            adapter,
            **kwargs,
        )
        return destination, manifest

    def source(self, manifest, kind: SourceKind, path: str | None = None):
        matches = [
            item
            for item in manifest.sources
            if item.kind is kind and (path is None or item.repository_path == path)
        ]
        self.assertEqual(1, len(matches))
        return matches[0]

    def canonical_write(self, path: Path, value: object) -> None:
        path.write_bytes(
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )

    def test_embedded_and_explicit_revisions_are_resolved_to_exact_commit(self) -> None:
        embedded = FakeHuggingFaceAdapter()
        destination, manifest = self.collect(embedded, "acme/Instruct@release-1")
        self.assertEqual([("acme/Instruct", "release-1")], embedded.resolve_calls)
        self.assertEqual(COMMIT, manifest.target.revision)
        self.assertEqual("release-1", manifest.requested_revision)
        replayed = replay_source_bundle(
            destination,
            expected_model_id="acme/Instruct",
            expected_revision=COMMIT,
        )
        self.assertEqual(manifest.bundle_id, replayed.manifest.bundle_id)

        explicit = FakeHuggingFaceAdapter()
        _, second = self.collect(explicit, revision="refs/pr/7")
        self.assertEqual([("acme/Instruct", "refs/pr/7")], explicit.resolve_calls)
        self.assertEqual("refs/pr/7", second.requested_revision)

    def test_invalid_or_ambiguous_target_request_is_rejected(self) -> None:
        invalid = ["model", "/model", "org/", "org/a..b", "org/a--b", "org/a/b"]
        for model_id in invalid:
            with self.subTest(model_id=model_id), self.assertRaises(SourceBundleError):
                parse_target_request(model_id)
        with self.assertRaises(SourceBundleError):
            parse_target_request("acme/Instruct@main", "release")
        with self.assertRaises(SourceBundleError):
            parse_target_request("acme/Instruct@")

    def test_adapter_must_resolve_an_exact_lowercase_commit(self) -> None:
        for resolved in ("main", "A" * 40, "a" * 39):
            with self.subTest(resolved=resolved), self.assertRaises(SourceBundleError):
                self.collect(FakeHuggingFaceAdapter(resolved_revision=resolved))

    def test_only_explicit_base_model_declarations_create_relations(self) -> None:
        metadata = RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "sha": COMMIT,
                    "base_model": ["acme/Base", "not a model id"],
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                        {"rfilename": "TRAINING.md"},
                    ],
                }
            ),
        )
        readme = b"""---
base_model: acme/Instruct
---
# Instruct

The name acme/Looks-Like-A-Base is merely prose, not a declaration.
"""
        adapter = FakeHuggingFaceAdapter(
            metadata=metadata,
            files={
                "README.md": RemoteObject(FetchStatus.OK, readme),
                "TRAINING.md": RemoteObject(
                    FetchStatus.OK,
                    b"We compared to acme/Another-Base but did not declare a relation.\n",
                ),
            },
        )
        _, manifest = self.collect(adapter)
        observed = {
            (item.declared_model_id, item.relation_to_target) for item in manifest.relations
        }
        self.assertEqual(
            {
                ("acme/Base", RelationToTarget.BASE_MODEL),
                ("not a model id", RelationToTarget.UNKNOWN),
                ("acme/Instruct", RelationToTarget.EXACT_TARGET),
            },
            observed,
        )
        self.assertNotIn(
            "acme/Looks-Like-A-Base",
            {item.declared_model_id for item in manifest.relations},
        )
        self.assertNotIn(
            "acme/Another-Base",
            {item.declared_model_id for item in manifest.relations},
        )

    def test_gated_config_uses_metadata_fallback_without_losing_gate_status(self) -> None:
        metadata = RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "sha": COMMIT,
                    "config": {"hidden_size": 4096, "model_type": "test"},
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )
        adapter = FakeHuggingFaceAdapter(
            metadata=metadata,
            files={
                "config.json": RemoteObject(FetchStatus.GATED, reason_code="auth_required")
            },
        )
        destination, manifest = self.collect(adapter)
        config = self.source(manifest, SourceKind.CONFIG)
        self.assertIs(config.status, CollectionStatus.COLLECTED)
        self.assertIs(config.fetch_status, FetchStatus.GATED)
        self.assertIs(config.retrieval, RetrievalMode.METADATA_FALLBACK)
        self.assertEqual("auth_required", config.reason_code)
        self.assertIn("/api/models/acme/Instruct/revision/", config.source_url)
        replayed = replay_source_bundle(destination)
        parsed = json.loads(replayed.source(config.source_id).content)
        self.assertEqual(4096, parsed["hidden_size"])

    def test_oversized_metadata_fallback_still_preserves_gated_fetch_class(self) -> None:
        metadata = RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "sha": COMMIT,
                    "config": {"large": "x" * 300},
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )
        adapter = FakeHuggingFaceAdapter(
            metadata=metadata,
            files={
                "README.md": RemoteObject(FetchStatus.OK, b"x" * 500),
                "config.json": RemoteObject(FetchStatus.GATED, reason_code="auth_required")
            },
        )
        _, manifest = self.collect(
            adapter,
            max_file_bytes=1_000,
            max_total_bytes=1_000,
        )
        config = self.source(manifest, SourceKind.CONFIG)
        self.assertIs(config.status, CollectionStatus.UNAVAILABLE)
        self.assertIs(config.fetch_status, FetchStatus.GATED)
        self.assertIs(config.retrieval, RetrievalMode.METADATA_FALLBACK)
        self.assertEqual("size_limit", config.reason_code)

    def test_missing_and_unavailable_statuses_are_preserved(self) -> None:
        missing_readme = FakeHuggingFaceAdapter(
            files={
                "README.md": RemoteObject(FetchStatus.MISSING, reason_code="not_found")
            }
        )
        destination, manifest = self.collect(missing_readme)
        readme = self.source(manifest, SourceKind.README)
        self.assertIs(readme.status, CollectionStatus.MISSING)
        self.assertIs(readme.fetch_status, FetchStatus.MISSING)
        self.assertIs(readme.retrieval, RetrievalMode.NOT_COLLECTED)
        self.assertIsNone(replay_source_bundle(destination).source(readme.source_id).content)

        unavailable = FakeHuggingFaceAdapter(
            metadata=RemoteObject(FetchStatus.UNAVAILABLE, reason_code="network_unavailable"),
            files={
                "README.md": RemoteObject(
                    FetchStatus.UNAVAILABLE, reason_code="network_unavailable"
                ),
                "config.json": RemoteObject(
                    FetchStatus.UNAVAILABLE, reason_code="network_unavailable"
                ),
            },
        )
        _, second = self.collect(unavailable)
        self.assertEqual(3, len(second.sources))
        self.assertTrue(
            all(item.status is CollectionStatus.UNAVAILABLE for item in second.sources)
        )
        self.assertTrue(
            all(item.reason_code == "network_unavailable" for item in second.sources)
        )

    def test_declared_sources_are_bounded_and_weights_are_not_fetched(self) -> None:
        metadata = RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "sha": COMMIT,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                        {"rfilename": "LICENSE"},
                        {"rfilename": "docs/SAFETY.md"},
                        {"rfilename": "generation_config.json"},
                        {"rfilename": "model.safetensors"},
                    ],
                }
            ),
        )
        adapter = FakeHuggingFaceAdapter(
            metadata=metadata,
            files={
                "LICENSE": RemoteObject(FetchStatus.OK, b"Synthetic license text\n"),
                "docs/SAFETY.md": RemoteObject(FetchStatus.OK, b"Synthetic safety text\n"),
                "generation_config.json": RemoteObject(FetchStatus.OK, b"{}\n"),
            },
        )
        _, manifest = self.collect(adapter, max_files=5)
        fetched_paths = [call[0] for call in adapter.fetch_calls]
        self.assertNotIn("model.safetensors", fetched_paths)
        self.assertNotIn("generation_config.json", fetched_paths)
        self.assertEqual(5, len(manifest.sources))
        self.assertEqual(
            ["docs/SAFETY.md", "LICENSE"],
            [
                item.repository_path
                for item in manifest.sources
                if item.kind is SourceKind.DECLARED_FILE
            ],
        )

    def test_conflicting_explicit_licenses_are_recorded_not_resolved(self) -> None:
        metadata = RemoteObject(
            FetchStatus.OK,
            json_bytes(
                {
                    "sha": COMMIT,
                    "license": "apache-2.0",
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )
        readme = RemoteObject(
            FetchStatus.OK,
            b"---\nlicense: mit\n---\n# Exact target\n",
        )
        _, manifest = self.collect(
            FakeHuggingFaceAdapter(metadata=metadata, files={"README.md": readme})
        )
        self.assertEqual({"apache-2.0", "mit"}, {item.value for item in manifest.declarations})
        self.assertTrue(
            all(item.status is DeclarationStatus.CONFLICT for item in manifest.declarations)
        )

    def test_manifest_contains_only_portable_urls_and_relative_object_paths(self) -> None:
        destination, manifest = self.collect(FakeHuggingFaceAdapter())
        manifest_text = (destination / "manifest.json").read_text(encoding="utf-8")
        self.assertNotIn(str(destination), manifest_text)
        for source in manifest.sources:
            self.assertTrue(source.source_url.startswith("https://huggingface.co/"))
            if source.object_path is not None:
                self.assertFalse(Path(source.object_path).is_absolute())
                self.assertNotIn("..", Path(source.object_path).parts)

    def test_replay_rejects_mutated_content_and_stale_files(self) -> None:
        destination, manifest = self.collect(FakeHuggingFaceAdapter())
        readme = self.source(manifest, SourceKind.README)
        object_path = destination.joinpath(*Path(readme.object_path).parts)
        object_path.write_bytes(b"mutated\n")
        with self.assertRaisesRegex(BundleIntegrityError, "content object"):
            replay_source_bundle(destination)

        second_destination, _ = self.collect(FakeHuggingFaceAdapter())
        stale = second_destination / "objects" / "sha256" / "stale"
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_bytes(b"old object")
        with self.assertRaisesRegex(BundleIntegrityError, "stale"):
            replay_source_bundle(second_destination)

    def test_replay_rejects_target_drift(self) -> None:
        destination, _ = self.collect(FakeHuggingFaceAdapter())
        with self.assertRaisesRegex(BundleIntegrityError, "model_id"):
            replay_source_bundle(destination, expected_model_id="other/Model")
        with self.assertRaisesRegex(BundleIntegrityError, "revision"):
            replay_source_bundle(destination, expected_revision=OTHER_COMMIT)

    def test_metadata_target_drift_is_rejected_during_collection(self) -> None:
        drifting = RemoteObject(
            FetchStatus.OK,
            json_bytes({"sha": OTHER_COMMIT, "siblings": []}),
        )
        with self.assertRaisesRegex(SourceBundleError, "drifts"):
            self.collect(FakeHuggingFaceAdapter(metadata=drifting))

        wrong_repository = RemoteObject(
            FetchStatus.OK,
            json_bytes({"id": "other/Model", "sha": COMMIT, "siblings": []}),
        )
        with self.assertRaisesRegex(SourceBundleError, "repository drifts"):
            self.collect(FakeHuggingFaceAdapter(metadata=wrong_repository))

    def test_replay_rejects_unsafe_paths_duplicate_sources_and_open_objects(self) -> None:
        destination, _ = self.collect(FakeHuggingFaceAdapter())
        manifest_path = destination / "manifest.json"
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw["sources"][0]["object_path"] = "../outside"
        self.canonical_write(manifest_path, raw)
        with self.assertRaisesRegex(BundleIntegrityError, "content-addressed"):
            replay_source_bundle(destination)

        duplicate_destination, _ = self.collect(FakeHuggingFaceAdapter())
        duplicate_manifest = duplicate_destination / "manifest.json"
        duplicate_raw = json.loads(duplicate_manifest.read_text(encoding="utf-8"))
        duplicate_raw["sources"].append(duplicate_raw["sources"][0])
        self.canonical_write(duplicate_manifest, duplicate_raw)
        with self.assertRaisesRegex(BundleIntegrityError, "duplicate source"):
            replay_source_bundle(duplicate_destination)

        open_destination, _ = self.collect(FakeHuggingFaceAdapter())
        open_manifest = open_destination / "manifest.json"
        open_raw = json.loads(open_manifest.read_text(encoding="utf-8"))
        open_raw["unexpected_field"] = "not allowed"
        self.canonical_write(open_manifest, open_raw)
        with self.assertRaisesRegex(BundleIntegrityError, "closed object"):
            replay_source_bundle(open_destination)

    def test_unsafe_or_duplicate_declared_repository_paths_are_rejected(self) -> None:
        for siblings in (
            [{"rfilename": "../LICENSE"}],
            [{"rfilename": "LICENSE"}, {"rfilename": "LICENSE"}],
        ):
            metadata = RemoteObject(
                FetchStatus.OK,
                json_bytes({"sha": COMMIT, "siblings": siblings}),
            )
            with self.subTest(siblings=siblings), self.assertRaises(SourceBundleError):
                self.collect(FakeHuggingFaceAdapter(metadata=metadata))

    def test_existing_destination_is_never_overwritten(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        destination = Path(temporary.name) / "existing"
        destination.mkdir()
        marker = destination / "keep.txt"
        marker.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            adapter = FakeHuggingFaceAdapter()
            collect_hf_source_bundle("acme/Instruct", destination, adapter)
        self.assertEqual("keep", marker.read_text(encoding="utf-8"))
        self.assertEqual([], adapter.resolve_calls)


if __name__ == "__main__":
    unittest.main()
