from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    SourceBundleError,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import (
    SourceLoadStatus,
    build_source_document_catalog,
)


COMMIT = "a" * 40


class Adapter:
    def __init__(self, *, metadata: bytes, files: dict[str, RemoteObject]) -> None:
        self.metadata = metadata
        self.files = files

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        return COMMIT

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        return RemoteObject(FetchStatus.OK, self.metadata)

    def fetch_file(
        self,
        model_id: str,
        revision: str,
        repo_path: str,
        *,
        max_bytes: int,
    ) -> RemoteObject:
        return self.files.get(
            repo_path,
            RemoteObject(FetchStatus.MISSING, reason_code="not_found"),
        )


def metadata(*paths: str) -> bytes:
    return json.dumps(
        {
            "id": "acme/Instruct",
            "sha": COMMIT,
            "siblings": [{"rfilename": item} for item in paths],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class SourceDocumentCatalogTests(unittest.TestCase):
    def collect(self, adapter: Adapter):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        bundle_dir = Path(temporary.name) / "bundle"
        collect_hf_source_bundle("acme/Instruct", bundle_dir, adapter)
        return replay_source_bundle(bundle_dir)

    def test_loads_exact_text_and_json_with_frozen_raw_byte_hashes(self) -> None:
        config = b'{\n  "model_type": "test",\n  "hidden_size": 64\n}\n'
        bundle = self.collect(
            Adapter(
                metadata=metadata("README.md", "config.json", "TRAINING.md"),
                files={
                    "README.md": RemoteObject(
                        FetchStatus.OK, b"# Exact target\nPublisher limitations.\n"
                    ),
                    "config.json": RemoteObject(FetchStatus.OK, config),
                    "TRAINING.md": RemoteObject(FetchStatus.OK, b"Training facts.\n"),
                },
            )
        )
        catalog = build_source_document_catalog(bundle)

        self.assertEqual(len(bundle.sources), len(catalog.records))
        self.assertTrue(
            all(item.status is SourceLoadStatus.LOADED for item in catalog.records)
        )
        self.assertEqual(len(bundle.sources), len(catalog.documents))
        config_source = next(
            item for item in bundle.sources if item.record.repository_path == "config.json"
        )
        config_document = catalog.by_id[config_source.record.source_id]
        self.assertEqual({"model_type": "test", "hidden_size": 64}, config_document.data)
        # Parsing must not replace the exact frozen-byte hash with a JSON reserialization hash.
        self.assertEqual(config_source.record.sha256, config_document.sha256)
        self.assertNotIn("Exact target", json.dumps(catalog.to_dict()))
        self.assertNotIn("Training facts", json.dumps(catalog.to_dict()))

    def test_preserves_missing_and_gated_sources_as_explicit_outcomes(self) -> None:
        bundle = self.collect(
            Adapter(
                metadata=metadata("README.md", "config.json"),
                files={
                    "README.md": RemoteObject(
                        FetchStatus.GATED, reason_code="auth_required"
                    ),
                    "config.json": RemoteObject(
                        FetchStatus.MISSING, reason_code="not_found"
                    ),
                },
            )
        )
        catalog = build_source_document_catalog(bundle)
        states = {
            item.source_kind: (item.status, item.reason_code) for item in catalog.records
        }
        self.assertEqual(
            (SourceLoadStatus.GATED, "auth_required"), states["readme"]
        )
        self.assertEqual(
            (SourceLoadStatus.MISSING, "not_found"), states["config"]
        )
        self.assertEqual(1, len(catalog.documents))  # model metadata only

    def test_empty_collected_source_is_visible_instead_of_becoming_evidence(self) -> None:
        bundle = self.collect(
            Adapter(
                metadata=metadata("README.md", "config.json", "SAFETY.md"),
                files={
                    "README.md": RemoteObject(FetchStatus.OK, b"# Model\n"),
                    "config.json": RemoteObject(FetchStatus.OK, b'{"ok":true}'),
                    "SAFETY.md": RemoteObject(FetchStatus.OK, b""),
                },
            )
        )
        catalog = build_source_document_catalog(bundle)
        by_kind_and_path = {}
        for source, record in zip(bundle.sources, catalog.records):
            by_kind_and_path[source.record.repository_path] = record.status
        self.assertEqual(SourceLoadStatus.EMPTY, by_kind_and_path["SAFETY.md"])
        self.assertEqual(
            {item.source_id for item in catalog.documents},
            {
                item.source_id
                for item in catalog.records
                if item.status is SourceLoadStatus.LOADED
            },
        )

    def test_collector_rejects_malformed_declared_content_before_cataloging(self) -> None:
        for name, body in (
            ("adapter_config.json", b'{"x":1,"x":2}'),
            ("SAFETY.md", b"\xff\xfe"),
        ):
            with self.subTest(name=name), self.assertRaises(SourceBundleError):
                self.collect(
                    Adapter(
                        metadata=metadata("README.md", "config.json", name),
                        files={
                            "README.md": RemoteObject(FetchStatus.OK, b"# Model\n"),
                            "config.json": RemoteObject(FetchStatus.OK, b'{"ok":true}'),
                            name: RemoteObject(FetchStatus.OK, body),
                        },
                    )
                )

    def test_catalog_is_deterministic_for_the_same_replayed_bundle(self) -> None:
        bundle = self.collect(
            Adapter(
                metadata=metadata("README.md", "config.json"),
                files={
                    "README.md": RemoteObject(FetchStatus.OK, b"# Model\n"),
                    "config.json": RemoteObject(FetchStatus.OK, b'{"x":1}\n'),
                },
            )
        )
        first = build_source_document_catalog(bundle)
        second = build_source_document_catalog(bundle)
        self.assertEqual(first.catalog_sha256, second.catalog_sha256)
        self.assertEqual(first.to_dict(), second.to_dict())


if __name__ == "__main__":
    unittest.main()
