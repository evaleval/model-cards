from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.models import RelationToTarget, SourceRole, TargetIdentity
from model_cards.official_discovery import (
    DiscoveryStatus,
    OfficialSourceKind,
    discover_official_sources,
)
from model_cards.official_documents import (
    HTML_TEXT_PARSER_VERSION,
    OfficialDocumentCatalog,
    OfficialDocumentError,
    OfficialDocumentMode,
    OfficialLoadStatus,
    build_official_document_catalog,
    serialize_official_document_catalog,
)
from model_cards.official_sources import (
    ContentPin,
    DiscoveryHint,
    OfficialFetchStatus,
    OfficialRemoteObject,
    RelationAssertion,
    RelationState,
    ReplayedOfficialSource,
    ReplayedOfficialSourceBundle,
    SourceAuthority,
    collect_official_sources,
    replay_official_sources,
)
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)


COMMIT = "e" * 40


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class FrozenHFAdapter:
    def __init__(self, readme: bytes) -> None:
        self.readme = readme

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        return COMMIT

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        return RemoteObject(
            FetchStatus.OK,
            canonical_json(
                {
                    "id": model_id,
                    "sha": revision,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )

    def fetch_file(
        self, model_id: str, revision: str, repo_path: str, *, max_bytes: int
    ) -> RemoteObject:
        if repo_path == "README.md":
            return RemoteObject(FetchStatus.OK, self.readme)
        if repo_path == "config.json":
            return RemoteObject(FetchStatus.OK, b"{}")
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class FrozenOfficialAdapter:
    def __init__(self, responses: dict[str, OfficialRemoteObject]) -> None:
        self.responses = responses

    def fetch(
        self, url: str, *, max_bytes: int, max_redirects: int
    ) -> OfficialRemoteObject:
        return self.responses.get(
            url,
            OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE,
                reason_code="fixture_not_provided",
            ),
        )


def response(
    url: str, body: bytes, media_type: str
) -> OfficialRemoteObject:
    return OfficialRemoteObject(
        OfficialFetchStatus.OK,
        content=body,
        final_url=url,
        redirect_chain=(url,),
        media_type=media_type,
    )


class OfficialDocumentBridgeTests(unittest.TestCase):
    def discovery(self, readme: str):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        hf_path = Path(temporary.name) / "hf"
        collect_hf_source_bundle(
            "acme/Model",
            hf_path,
            FrozenHFAdapter(readme.encode("utf-8")),
        )
        return discover_official_sources(replay_source_bundle(hf_path))

    def replay(
        self,
        discovery,
        responses: dict[str, OfficialRemoteObject],
        **kwargs,
    ) -> ReplayedOfficialSourceBundle:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        destination = Path(temporary.name) / "official"
        collect_official_sources(
            discovery,
            destination,
            FrozenOfficialAdapter(responses),
            **kwargs,
        )
        return replay_official_sources(destination)

    def test_supported_sources_load_with_exact_target_roles_and_digests(self) -> None:
        paper = "https://arxiv.org/abs/2401.01234"
        system = "https://arxiv.org/abs/2401.01235"
        code = "https://github.com/acme/model"
        discovery = self.discovery(
            f"[Technical report]({paper})\n"
            f"[System card]({system})\n"
            f"[Code]({code})\n"
        )
        bodies = {
            paper: b"Developer report text.\n",
            system: b"# System card\n\nDocumented limitation.\n",
            code: b'{"architectures":["AcmeLM"],"nested":{"finite":1.25}}',
        }
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {
                    paper: response(paper, bodies[paper], "text/plain"),
                    system: response(system, bodies[system], "text/markdown"),
                    code: response(code, bodies[code], "application/json"),
                },
            )
        )

        self.assertEqual(len(catalog.records), len(discovery.records))
        self.assertEqual(3, len(catalog.documents))
        by_uri = {item.source_uri: item for item in catalog.documents}
        self.assertEqual(SourceRole.DEVELOPER_REPORT, by_uri[paper].role)
        self.assertEqual(SourceRole.DEVELOPER_REPORT, by_uri[system].role)
        self.assertEqual(SourceRole.DEVELOPER_CODE, by_uri[code].role)
        self.assertEqual({"architectures": ["AcmeLM"], "nested": {"finite": 1.25}}, by_uri[code].data)
        for uri, body in bodies.items():
            document = by_uri[uri]
            self.assertEqual(TargetIdentity("acme/Model", COMMIT), document.target)
            self.assertEqual(COMMIT, document.source_revision)
            self.assertEqual(hashlib.sha256(body).hexdigest(), document.sha256)
            record = catalog.records_by_id[document.source_id]
            self.assertEqual(OfficialLoadStatus.LOADED, record.status)
            self.assertEqual("verified_primary_source", record.collection_reason_code)
            self.assertEqual(SourceAuthority.PRIMARY, record.authority)
            self.assertTrue(record.evidence_eligible)
        self.assertEqual(OfficialDocumentMode.JSON, catalog.records_by_id[by_uri[code].source_id].document_mode)

    def test_html_is_deterministic_visible_text_and_parser_version_is_bound(self) -> None:
        system = "https://arxiv.org/abs/2401.01235"
        body = (
            b"<!DOCTYPE html><html><head><title>Hidden title</title>"
            b"<style>.secret{}</style></head><body><main>"
            b"<h1>A &amp; B</h1><p>Uses <strong>safe</strong> text.</p>"
            b"<script>PRIVATE_SCRIPT_BODY</script><!-- PRIVATE_COMMENT -->"
            b"</main></body></html>"
        )
        discovery = self.discovery(f"[System card]({system})\n")
        replayed = self.replay(
            discovery,
            {system: response(system, body, "text/html")},
        )
        first = build_official_document_catalog(replayed)
        second = build_official_document_catalog(replayed)
        document = next(item for item in first.documents if item.source_uri == system)
        self.assertEqual("A & B\nUses safe text.", document.text)
        self.assertNotIn("Hidden title", document.text or "")
        self.assertNotIn("PRIVATE", document.text or "")
        record = first.records_by_id[document.source_id]
        self.assertEqual(OfficialDocumentMode.HTML_TEXT, record.document_mode)
        self.assertEqual(HTML_TEXT_PARSER_VERSION, first.html_parser_version)
        self.assertEqual(replayed.manifest.source_bundle_id, first.source_bundle_id)
        self.assertEqual(first.catalog_sha256, second.catalog_sha256)
        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        with self.assertRaisesRegex(OfficialDocumentError, "parser version"):
            replace(first, html_parser_version="different-parser/v2")

    def test_collection_failures_and_discovery_only_remain_distinct(self) -> None:
        urls = {
            "missing": "https://github.com/acme/missing",
            "gated": "https://github.com/acme/gated",
            "blocked": "https://github.com/acme/blocked",
            "unavailable": "https://github.com/acme/unavailable",
        }
        discovery = self.discovery(
            "\n".join(f"[Code]({url})" for url in urls.values())
        )
        statuses = {
            "missing": OfficialFetchStatus.MISSING,
            "gated": OfficialFetchStatus.GATED,
            "blocked": OfficialFetchStatus.BLOCKED,
            "unavailable": OfficialFetchStatus.UNAVAILABLE,
        }
        responses = {
            urls[name]: OfficialRemoteObject(status, reason_code=f"fixture_{name}")
            for name, status in statuses.items()
        }
        replayed = self.replay(
            discovery,
            responses,
            discovery_hints=(
                DiscoveryHint(
                    OfficialSourceKind.PAPER,
                    "https://example.org/discovered-paper",
                    SourceAuthority.SCHOLARLY_DISCOVERY,
                    "scholarly_result_only",
                ),
            ),
        )
        catalog = build_official_document_catalog(replayed)
        by_uri = {item.source_uri: item for item in catalog.records if item.source_uri}
        self.assertEqual(OfficialLoadStatus.MISSING, by_uri[urls["missing"]].status)
        self.assertEqual(OfficialLoadStatus.GATED, by_uri[urls["gated"]].status)
        self.assertEqual(OfficialLoadStatus.BLOCKED, by_uri[urls["blocked"]].status)
        self.assertEqual(OfficialLoadStatus.UNAVAILABLE, by_uri[urls["unavailable"]].status)
        self.assertEqual(
            OfficialLoadStatus.DISCOVERY_ONLY,
            by_uri["https://example.org/discovered-paper"].status,
        )
        self.assertEqual(len(replayed.manifest.sources), len(catalog.records))
        self.assertFalse(catalog.documents)

    def test_conflicting_content_and_relation_state_never_become_documents(self) -> None:
        code = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({code})\n")
        candidate = next(
            item
            for item in discovery.records
            if item.status is DiscoveryStatus.DISCOVERED
        )
        assertions = (
            RelationAssertion(
                candidate.record_id,
                "acme/Model",
                RelationToTarget.EXACT_TARGET,
                candidate.declaring_source_id,
                candidate.declaration_locator,
            ),
            RelationAssertion(
                candidate.record_id,
                "acme/Base",
                RelationToTarget.BASE_MODEL,
                candidate.declaring_source_id,
                candidate.declaration_locator,
            ),
        )
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, b"conflicting but stored", "text/plain")},
                relation_assertions=assertions,
            )
        )
        record = next(item for item in catalog.records if item.source_uri == code)
        self.assertEqual(OfficialLoadStatus.CONFLICTING, record.status)
        self.assertEqual("conflicting", record.collection_status.value)
        self.assertEqual(2, len(record.relations))
        self.assertTrue(
            all(item.state is RelationState.CONFLICTING for item in record.relations)
        )
        self.assertNotIn(record.source_id, catalog.by_id)
        with self.assertRaises(FrozenInstanceError):
            record.status = OfficialLoadStatus.LOADED

        drifted = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, b"drifted bytes", "text/plain")},
                content_pins=(ContentPin(candidate.record_id, "0" * 64),),
            )
        )
        drift = next(item for item in drifted.records if item.source_uri == code)
        self.assertEqual(OfficialLoadStatus.CONFLICTING, drift.status)
        self.assertEqual("source_drift", drift.collection_reason_code)

    def test_declared_nonexact_relation_is_preserved_without_relabeling(self) -> None:
        code = "https://github.com/acme/base-model"
        discovery = self.discovery(f"[Code]({code})\n")
        candidate = next(
            item
            for item in discovery.records
            if item.status is DiscoveryStatus.DISCOVERED
        )
        assertion = RelationAssertion(
            candidate.record_id,
            "acme/Base",
            RelationToTarget.BASE_MODEL,
            candidate.declaring_source_id,
            candidate.declaration_locator,
        )
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, b"Base model report", "text/plain")},
                relation_assertions=(assertion,),
            )
        )
        record = next(item for item in catalog.records if item.source_uri == code)
        self.assertEqual(OfficialLoadStatus.LOADED, record.status)
        self.assertEqual(1, len(record.relations))
        self.assertEqual(RelationToTarget.BASE_MODEL, record.relations[0].relation_to_target)
        self.assertEqual(RelationState.DECLARED, record.relations[0].state)
        # The immutable bundle target remains explicit; consumers must use the
        # preserved relation rather than silently promote the source's subject.
        self.assertEqual(TargetIdentity("acme/Model", COMMIT), catalog.by_id[record.source_id].target)

    def test_json_rejects_duplicate_nonfinite_overflow_and_null_roots(self) -> None:
        urls = {
            "duplicate": "https://github.com/acme/duplicate",
            "constant": "https://github.com/acme/constant",
            "overflow": "https://github.com/acme/overflow",
            "null": "https://github.com/acme/null",
            "valid": "https://github.com/acme/valid",
        }
        discovery = self.discovery(
            "\n".join(f"[Code]({url})" for url in urls.values())
        )
        bodies = {
            "duplicate": b'{"x":1,"x":2}',
            "constant": b'{"x":NaN}',
            "overflow": b'{"x":1e9999}',
            "null": b"null",
            "valid": b'{"x":[1,2.5,true,null],"nested":{"ok":"yes"}}',
        }
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {
                    urls[name]: response(urls[name], body, "application/json")
                    for name, body in bodies.items()
                },
            )
        )
        by_uri = {item.source_uri: item for item in catalog.records if item.source_uri}
        for name in ("duplicate", "constant", "overflow", "null"):
            self.assertEqual(OfficialLoadStatus.INVALID_JSON, by_uri[urls[name]].status)
        self.assertEqual(OfficialLoadStatus.LOADED, by_uri[urls["valid"]].status)
        self.assertEqual(
            {"x": [1, 2.5, True, None], "nested": {"ok": "yes"}},
            catalog.by_id[by_uri[urls["valid"]].source_id].data,
        )

    def test_invalid_utf8_unsafe_controls_and_malformed_html_fail_closed(self) -> None:
        urls = {
            "utf8": "https://github.com/acme/utf8",
            "control": "https://github.com/acme/control",
            "html": "https://github.com/acme/html",
        }
        discovery = self.discovery(
            "\n".join(f"[Code]({url})" for url in urls.values())
        )
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {
                    urls["utf8"]: response(urls["utf8"], b"\xff\xfe", "text/plain"),
                    urls["control"]: response(
                        urls["control"], b"visible\x00hidden", "text/markdown"
                    ),
                    urls["html"]: response(
                        urls["html"],
                        b"<html><body>visible<script>never closed",
                        "text/html",
                    ),
                },
            )
        )
        by_uri = {item.source_uri: item for item in catalog.records if item.source_uri}
        self.assertEqual(OfficialLoadStatus.INVALID_UTF8, by_uri[urls["utf8"]].status)
        self.assertEqual(OfficialLoadStatus.UNSAFE_TEXT, by_uri[urls["control"]].status)
        self.assertEqual(OfficialLoadStatus.INVALID_HTML, by_uri[urls["html"]].status)
        self.assertFalse(catalog.documents)

    def test_pdf_and_unknown_media_are_explicitly_unsupported(self) -> None:
        paper = "https://arxiv.org/pdf/2401.01234.pdf"
        code = "https://github.com/acme/binary"
        discovery = self.discovery(
            f"[Paper]({paper})\n[Code]({code})\n"
        )
        pdf_body = b"%PDF-1.7\nReadable-looking text must not become evidence."
        binary_body = b"not interpreted"
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {
                    paper: response(paper, pdf_body, "application/pdf"),
                    code: response(code, binary_body, "application/octet-stream"),
                },
            )
        )
        by_uri = {item.source_uri: item for item in catalog.records if item.source_uri}
        self.assertEqual(OfficialLoadStatus.UNSUPPORTED_PDF, by_uri[paper].status)
        self.assertEqual(
            "pdf_extraction_unsupported", by_uri[paper].reason_code
        )
        self.assertEqual(
            OfficialLoadStatus.UNSUPPORTED_MEDIA_TYPE, by_uri[code].status
        )
        self.assertNotIn(by_uri[paper].source_id, catalog.by_id)
        self.assertNotIn(by_uri[code].source_id, catalog.by_id)

    def test_forged_replay_and_catalog_tampering_are_rejected(self) -> None:
        code = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({code})\n")
        replayed = self.replay(
            discovery,
            {code: response(code, b'{"immutable":"source"}', "application/json")},
        )
        values = list(replayed.sources)
        index = next(
            index
            for index, item in enumerate(values)
            if item.record.requested_url == code
        )
        values[index] = ReplayedOfficialSource(
            record=values[index].record,
            content=b"tampered source",
        )
        forged = ReplayedOfficialSourceBundle(
            manifest=replayed.manifest,
            sources=tuple(values),
        )
        with self.assertRaisesRegex(OfficialDocumentError, "digest or size"):
            build_official_document_catalog(forged)

        reversed_replay = ReplayedOfficialSourceBundle(
            manifest=replayed.manifest,
            sources=tuple(reversed(replayed.sources)),
        )
        with self.assertRaisesRegex(OfficialDocumentError, "order or identity"):
            build_official_document_catalog(reversed_replay)

        catalog = build_official_document_catalog(replayed)
        with self.assertRaisesRegex(OfficialDocumentError, "digest"):
            replace(catalog, catalog_sha256="0" * 64)
        # A mutated inner JSON value is detected before body-free serialization.
        document = next(item for item in catalog.documents if item.source_uri == code)
        self.assertEqual({"immutable": "source"}, document.data)
        assert isinstance(document.data, dict)
        document.data["immutable"] = "tampered"
        with self.assertRaisesRegex(OfficialDocumentError, "identity diverges"):
            serialize_official_document_catalog(catalog)

    def test_serialization_is_canonical_body_free_and_privacy_safe(self) -> None:
        code = "https://github.com/acme/model"
        secret_body = b"PRIVATE_SOURCE_BODY_DO_NOT_SERIALIZE"
        discovery = self.discovery(f"[Code]({code})\n")
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, secret_body, "text/plain")},
            )
        )
        serialized = serialize_official_document_catalog(catalog)
        parsed = json.loads(serialized.decode("utf-8"))
        self.assertEqual(
            serialized,
            json.dumps(
                parsed,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8"),
        )
        rendered = serialized.decode("utf-8")
        self.assertNotIn(secret_body.decode("utf-8"), rendered)
        self.assertNotIn(tempfile.gettempdir(), rendered)
        self.assertNotIn("prompt", rendered.casefold())
        self.assertEqual(
            [item.source_id for item in catalog.documents], parsed["document_ids"]
        )
        self.assertTrue(
            all("text" not in item and "data" not in item for item in parsed["records"])
        )
        with self.assertRaises(OfficialDocumentError):
            serialize_official_document_catalog(object())  # type: ignore[arg-type]

    def test_catalog_rejects_record_target_drift(self) -> None:
        code = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({code})\n")
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, b"source", "text/plain")},
            )
        )
        records = list(catalog.records)
        records[0] = replace(records[0], source_revision="f" * 40)
        with self.assertRaises(OfficialDocumentError):
            OfficialDocumentCatalog(
                catalog_version=catalog.catalog_version,
                html_parser_version=catalog.html_parser_version,
                official_bundle_id=catalog.official_bundle_id,
                source_bundle_id=catalog.source_bundle_id,
                target=catalog.target,
                records=tuple(records),
                documents=catalog.documents,
                catalog_sha256=catalog.catalog_sha256,
            )


if __name__ == "__main__":
    unittest.main()
