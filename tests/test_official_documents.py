from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from model_cards.models import RelationToTarget, SourceRole, TargetIdentity
from model_cards.official_discovery import (
    DiscoveryStatus,
    OfficialSourceKind,
    discover_official_sources,
)
from model_cards.official_documents import (
    HTML_TEXT_PARSER_VERSION,
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
from model_cards.pdf_extraction import (
    PDF_EXTRACTOR_VERSION,
    PDF_PARSER_NAME,
    PDF_PARSER_VERSION,
    PdfExtractionLimits,
    PdfExtractionResult,
    PdfExtractionStatus,
)
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from tests.test_pdf_extraction import encrypted_pdf, image_only_pdf, text_pdf


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
        if "relation_assertions" not in kwargs:
            kwargs["relation_assertions"] = tuple(
                RelationAssertion(
                    candidate.record_id,
                    discovery.target.model_id,
                    RelationToTarget.EXACT_TARGET,
                    candidate.declaring_source_id,
                    candidate.declaration_locator,
                    discovery.target.revision,
                )
                for candidate in discovery.records
                if candidate.status is DiscoveryStatus.DISCOVERED
            )
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
            digest = hashlib.sha256(body).hexdigest()
            self.assertEqual(f"sha256:{digest}", document.source_revision)
            self.assertEqual(digest, document.sha256)
            record = catalog.records_by_id[document.source_id]
            self.assertEqual(document.source_revision, record.source_revision)
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
        self.assertTrue(
            all(record.source_revision == "unresolved" for record in by_uri.values())
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
                discovery.target.revision,
            ),
            RelationAssertion(
                candidate.record_id,
                "acme/Base",
                RelationToTarget.BASE_MODEL,
                candidate.declaring_source_id,
                candidate.declaration_locator,
                discovery.target.revision,
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

    def test_declared_nonexact_relation_is_audited_but_not_loaded(self) -> None:
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
            discovery.target.revision,
        )
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, b"Base model report", "text/plain")},
                relation_assertions=(assertion,),
            )
        )
        record = next(item for item in catalog.records if item.source_uri == code)
        self.assertEqual(OfficialLoadStatus.BLOCKED, record.status)
        self.assertEqual("related_source_not_exact_target", record.reason_code)
        self.assertFalse(record.evidence_eligible)
        self.assertEqual(1, len(record.relations))
        self.assertEqual(RelationToTarget.BASE_MODEL, record.relations[0].relation_to_target)
        self.assertEqual(RelationState.DECLARED, record.relations[0].state)
        self.assertNotIn(record.source_id, catalog.by_id)
        with self.assertRaisesRegex(
            OfficialDocumentError, "declared exact-target relation"
        ):
            replace(
                record,
                status=OfficialLoadStatus.LOADED,
                reason_code="loaded",
                evidence_eligible=True,
                document_mode=OfficialDocumentMode.TEXT,
                rendered_sha256=record.source_sha256,
            )

    def test_unasserted_source_keeps_unresolved_audit_record_without_document(self) -> None:
        code = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({code})\n")
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, b"Unasserted source", "text/plain")},
                relation_assertions=(),
            )
        )

        record = next(item for item in catalog.records if item.source_uri == code)
        self.assertEqual(OfficialLoadStatus.CONFLICTING, record.status)
        self.assertEqual("relation_unresolved", record.reason_code)
        self.assertFalse(record.evidence_eligible)
        self.assertEqual(1, len(record.relations))
        self.assertEqual(RelationToTarget.UNKNOWN, record.relations[0].relation_to_target)
        self.assertEqual(RelationState.UNRESOLVED, record.relations[0].state)
        self.assertNotIn(record.source_id, catalog.by_id)

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

    def test_valid_pdf_loads_as_versioned_text_from_frozen_bytes(self) -> None:
        paper = "https://arxiv.org/pdf/2401.01234.pdf"
        pdf_body = text_pdf("Exact model limitation", "References: Smith 2026")
        discovery = self.discovery(f"[Paper]({paper})\n")
        replayed = self.replay(
            discovery,
            {paper: response(paper, pdf_body, "application/pdf")},
        )
        first = build_official_document_catalog(replayed)
        second = build_official_document_catalog(replayed)

        document = next(item for item in first.documents if item.source_uri == paper)
        record = first.records_by_id[document.source_id]
        source_digest = hashlib.sha256(pdf_body).hexdigest()
        self.assertEqual(OfficialLoadStatus.LOADED, record.status)
        self.assertEqual("loaded_pdf_text", record.reason_code)
        self.assertEqual(OfficialDocumentMode.PDF_TEXT, record.document_mode)
        self.assertEqual("Exact model limitation\n\nReferences: Smith 2026", document.text)
        self.assertEqual(source_digest, document.sha256)
        self.assertEqual(f"sha256:{source_digest}", document.source_revision)
        self.assertEqual(
            hashlib.sha256((document.text or "").encode("utf-8")).hexdigest(),
            record.rendered_sha256,
        )
        self.assertEqual(PDF_EXTRACTOR_VERSION, first.pdf_extractor_version)
        self.assertEqual(PDF_PARSER_NAME, first.pdf_parser_name)
        self.assertEqual(PDF_PARSER_VERSION, first.pdf_parser_version)
        self.assertEqual(PdfExtractionLimits(), first.pdf_extraction_limits)
        self.assertEqual(first.catalog_sha256, second.catalog_sha256)
        serialized = json.loads(serialize_official_document_catalog(first))
        self.assertEqual(PDF_EXTRACTOR_VERSION, serialized["pdf_extractor_version"])
        self.assertEqual(PDF_PARSER_NAME, serialized["pdf_parser_name"])
        self.assertEqual(PDF_PARSER_VERSION, serialized["pdf_parser_version"])
        self.assertEqual(
            PdfExtractionLimits().to_dict(),
            serialized["pdf_extraction_limits"],
        )
        with self.assertRaisesRegex(OfficialDocumentError, "PDF parser identity"):
            replace(first, pdf_parser_version="different-parser/v1")
        with self.assertRaisesRegex(OfficialDocumentError, "digest"):
            replace(
                first,
                pdf_extraction_limits=PdfExtractionLimits(max_pages=1),
            )

    def test_pdf_nontext_outcomes_are_explicit_and_never_create_documents(self) -> None:
        urls = {
            "malformed": "https://arxiv.org/pdf/2401.01234.pdf",
            "encrypted": "https://arxiv.org/pdf/2401.01235.pdf",
            "image": "https://arxiv.org/pdf/2401.01236.pdf",
            "limited": "https://arxiv.org/pdf/2401.01237.pdf",
        }
        discovery = self.discovery(
            "\n".join(f"[Paper]({url})" for url in urls.values())
        )
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {
                    urls["malformed"]: response(
                        urls["malformed"],
                        b"%PDF-1.7\nnot a complete PDF",
                        "application/pdf",
                    ),
                    urls["encrypted"]: response(
                        urls["encrypted"], encrypted_pdf(), "application/pdf"
                    ),
                    urls["image"]: response(
                        urls["image"], image_only_pdf(), "application/pdf"
                    ),
                    urls["limited"]: response(
                        urls["limited"],
                        text_pdf("longer than five characters"),
                        "application/pdf",
                    ),
                },
            ),
            pdf_extraction_limits=PdfExtractionLimits(max_text_characters=5),
        )
        by_uri = {item.source_uri: item for item in catalog.records if item.source_uri}
        expected = {
            "malformed": (OfficialLoadStatus.INVALID_PDF, "malformed_pdf"),
            "encrypted": (OfficialLoadStatus.ENCRYPTED_PDF, "encrypted_pdf"),
            "image": (OfficialLoadStatus.IMAGE_ONLY_PDF, "image_only_pdf"),
            "limited": (
                OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
                "text_character_limit",
            ),
        }
        for name, (status, reason) in expected.items():
            with self.subTest(name=name):
                record = by_uri[urls[name]]
                self.assertEqual(status, record.status)
                self.assertEqual(reason, record.reason_code)
                self.assertIsNone(record.document_mode)
                self.assertIsNone(record.rendered_sha256)
                self.assertNotIn(record.source_id, catalog.by_id)
        self.assertFalse(catalog.documents)

    def test_pdf_unavailable_failure_and_time_limit_map_to_closed_outcomes(self) -> None:
        paper = "https://arxiv.org/pdf/2401.01234.pdf"
        pdf_body = text_pdf("Exact model report")
        discovery = self.discovery(f"[Paper]({paper})\n")
        replayed = self.replay(
            discovery,
            {paper: response(paper, pdf_body, "application/pdf")},
        )
        source_digest = hashlib.sha256(pdf_body).hexdigest()
        cases = (
            (
                PdfExtractionStatus.PARSER_UNAVAILABLE,
                "parser_not_installed",
                OfficialLoadStatus.PDF_EXTRACTION_UNAVAILABLE,
            ),
            (
                PdfExtractionStatus.FAILED,
                "unexpected_extraction_failure",
                OfficialLoadStatus.PDF_EXTRACTION_FAILED,
            ),
            (
                PdfExtractionStatus.TIME_LIMIT,
                "wall_time_limit",
                OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
            ),
        )
        for extraction_status, reason, expected_status in cases:
            with self.subTest(status=extraction_status.value):
                result = PdfExtractionResult(
                    status=extraction_status,
                    reason_code=reason,
                    source_sha256=source_digest,
                    source_byte_size=len(pdf_body),
                    limits=PdfExtractionLimits(),
                )
                with patch(
                    "model_cards.official_documents.extract_pdf_text",
                    return_value=result,
                ):
                    catalog = build_official_document_catalog(replayed)
                record = next(item for item in catalog.records if item.source_uri == paper)
                self.assertEqual(expected_status, record.status)
                self.assertEqual(reason, record.reason_code)
                self.assertFalse(catalog.documents)

    def test_pdf_result_must_match_the_catalog_parser_profile(self) -> None:
        paper = "https://arxiv.org/pdf/2401.01234.pdf"
        pdf_body = text_pdf("Exact model report")
        discovery = self.discovery(f"[Paper]({paper})\n")
        replayed = self.replay(
            discovery,
            {paper: response(paper, pdf_body, "application/pdf")},
        )
        mismatched = PdfExtractionResult(
            status=PdfExtractionStatus.PARSER_UNAVAILABLE,
            reason_code="parser_not_installed",
            source_sha256=hashlib.sha256(pdf_body).hexdigest(),
            source_byte_size=len(pdf_body),
            limits=PdfExtractionLimits(max_pages=1),
        )
        with patch(
            "model_cards.official_documents.extract_pdf_text",
            return_value=mismatched,
        ), self.assertRaisesRegex(OfficialDocumentError, "profile"):
            build_official_document_catalog(replayed)

    def test_nonexact_pdf_relation_is_rejected_before_parser_invocation(self) -> None:
        paper = "https://arxiv.org/pdf/2401.01234.pdf"
        discovery = self.discovery(f"[Paper]({paper})\n")
        candidate = next(
            item for item in discovery.records
            if item.status is DiscoveryStatus.DISCOVERED
        )
        assertion = RelationAssertion(
            candidate.record_id,
            "acme/Base",
            RelationToTarget.BASE_MODEL,
            candidate.declaring_source_id,
            candidate.declaration_locator,
            discovery.target.revision,
        )
        replayed = self.replay(
            discovery,
            {paper: response(paper, text_pdf("Base report"), "application/pdf")},
            relation_assertions=(assertion,),
        )
        with patch("model_cards.official_documents.extract_pdf_text") as extractor:
            catalog = build_official_document_catalog(replayed)
        extractor.assert_not_called()
        record = next(item for item in catalog.records if item.source_uri == paper)
        self.assertEqual(OfficialLoadStatus.BLOCKED, record.status)
        self.assertEqual("related_source_not_exact_target", record.reason_code)
        self.assertFalse(catalog.documents)

    def test_unknown_media_type_remains_explicitly_unsupported(self) -> None:
        code = "https://github.com/acme/binary"
        discovery = self.discovery(f"[Code]({code})\n")
        binary_body = b"not interpreted"
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {
                    code: response(code, binary_body, "application/octet-stream"),
                },
            )
        )
        by_uri = {item.source_uri: item for item in catalog.records if item.source_uri}
        self.assertEqual(
            OfficialLoadStatus.UNSUPPORTED_MEDIA_TYPE, by_uri[code].status
        )
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

    def test_record_rejects_external_revision_drift(self) -> None:
        code = "https://github.com/acme/model"
        discovery = self.discovery(f"[Code]({code})\n")
        catalog = build_official_document_catalog(
            self.replay(
                discovery,
                {code: response(code, b"source", "text/plain")},
            )
        )
        with self.assertRaisesRegex(OfficialDocumentError, "frozen byte state"):
            replace(
                catalog.records[0],
                source_revision="sha256:" + "f" * 64,
            )


if __name__ == "__main__":
    unittest.main()
