from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.artifact import project_card
from model_cards.bindings import source_from_dict
from model_cards.claim_gate import (
    ClaimCandidate,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
    correct_candidate,
    evaluate_claim_gate,
)
from model_cards.factreasoner import (
    IBM_FACTREASONER_UPSTREAM_REVISION,
    CheckOutcome,
    CheckerResponse,
    run_factreasoner,
)
from model_cards.pipeline import PrivacyScanReport, RiskStageSummary
from model_cards.publication import project_publication_card
from model_cards.publication_schema import PUBLICATION_SCHEMA
from model_cards.publication_sources import enrich_publication_card
from model_cards.publication_validation import run_publication_validation
from model_cards.review import reassign_binding, withhold_binding
from model_cards.review_audit import (
    ReviewClosureEvidence,
    ReviewedCandidateAudit,
    audit_reviewed_candidate,
    verify_reviewed_candidate_audit,
)
from model_cards.risk_mapping import (
    RiskCatalog,
    TaxonomyRisk,
    map_candidate_risks,
)
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import build_source_document_catalog
from tests.helpers import synthetic_artifact, synthetic_specification


class SupportingChecker:
    checker_id = "tests/review_closure_support"
    checker_revision = "fixture-v1"

    def check(self, request):
        return CheckerResponse(
            outcome=CheckOutcome.SUPPORT,
            reason_code="fixture_support",
            cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
        )


class UnavailableChecker:
    checker_id = "ibm/factreasoner-fr1"
    checker_revision = IBM_FACTREASONER_UPSTREAM_REVISION

    def check(self, request):
        return CheckerResponse(
            outcome=CheckOutcome.UNAVAILABLE,
            reason_code="fixture_unavailable",
        )


class PinnedIdentitySupportingChecker(SupportingChecker):
    """Synthetic identity fixture; it is not retained execution evidence."""

    checker_id = "ibm/factreasoner-fr1"
    checker_revision = IBM_FACTREASONER_UPSTREAM_REVISION


RISK_CATALOG = RiskCatalog.build(
    (
        TaxonomyRisk(
            risk_id="atlas-example-risk",
            name="Example risk",
            description="A synthetic taxonomy fixture for an empty context set.",
            source_url="https://example.org/risk",
        ),
    )
)


class _PublicationCatalogAdapter:
    def resolve_revision(self, model_id, requested_revision):
        return "1" * 40

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
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(FetchStatus.OK, b"# Synthetic Model 1B\n")
        if repo_path == "config.json":
            return RemoteObject(FetchStatus.OK, b"{}\n")
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


def _file_digest(value) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ) + "\n"
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ReviewedCandidateAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = synthetic_artifact()
        artifact_sources = tuple(
            source_from_dict(item) for item in synthetic_specification()["sources"]
        )
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        bundle = Path(temporary.name) / "publication-bundle"
        collect_hf_source_bundle(
            self.artifact.target.model_id,
            bundle,
            _PublicationCatalogAdapter(),
        )
        self.publication_catalog = build_source_document_catalog(
            replay_source_bundle(bundle)
        )
        self.sources = artifact_sources + self.publication_catalog.documents

    def reviewed(self):
        binding = next(
            item
            for item in self.artifact.bindings
            if item.field_path == "identity.summary"
        )
        candidate = correct_candidate(
            ClaimCandidate.from_binding(self.artifact.target, binding),
            field_path="evaluation.results_summary",
        )
        decisions = tuple(
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=gate,
                checker="tests/review-audit-checker-v1",
                method="bounded_semantic_review",
                status=DecisionStatus.ACCEPTED,
                reason=(
                    "semantic_entity_scope"
                    if gate is GateName.ENTITY_SCOPE
                    else "semantic_field_fit"
                    if gate is GateName.FIELD_FIT
                    else "semantic_value_support"
                ),
            )
            for gate in (
                GateName.ENTITY_SCOPE,
                GateName.FIELD_FIT,
                GateName.VALUE_SUPPORT,
            )
        )
        return reassign_binding(
            self.artifact,
            binding.binding_id,
            field_path="evaluation.results_summary",
            relation="exact_target",
            corrected_value=binding.value,
            reason="field_corrected",
            sources=self.sources,
            checker_decisions=decisions,
        )

    def closure(self, artifact, checker=None):
        checker = checker or SupportingChecker()
        pre = enrich_publication_card(
            self.publication_catalog,
            artifact.publication_card
            or project_publication_card(project_card(artifact)),
        ).card
        publication_fact = run_factreasoner(
            pre,
            PUBLICATION_SCHEMA,
            artifact.target,
            self.sources,
            checker,
        )
        publication = run_publication_validation(pre, publication_fact)
        final_fact = run_factreasoner(
            publication.final_card,
            PUBLICATION_SCHEMA,
            artifact.target,
            self.sources,
            checker,
        )
        risk_report = map_candidate_risks((), RISK_CATALOG, object(), object())
        risk_summary = RiskStageSummary(
            status=risk_report.status.value,
            reason=risk_report.reason,
            catalog_sha256=risk_report.catalog_sha256,
            context_sha256=risk_report.context_sha256,
            publisher_context_candidate_ids=(),
            publisher_reported_risk_candidate_ids=(),
            taxonomy_candidate_count=0,
            taxonomy_included_count=0,
            mapping_report_sha256=risk_report.report_sha256,
        )
        risk_mapping = {
            "summary": risk_summary.to_dict(),
            "use_contexts": [],
            "taxonomy_derivations": [],
            "factreasoner_withheld_derivation_ids": [],
            "taxonomy_mapping": risk_report.to_dict(),
        }
        checked = sum(
            item.disposition.value == "accepted"
            for item in artifact.effective_bindings()
        ) + 1
        privacy = PrivacyScanReport(
            scanned_card_sha256=_file_digest(publication.final_card),
            checked=checked,
            passed=checked,
            withheld_candidate_ids=(),
            status="completed",
            reason="privacy_safe_projection",
        )
        return ReviewClosureEvidence(
            claim_gate_records=self.claim_gates(),
            publication_catalog=self.publication_catalog,
            publication_factreasoner=publication_fact,
            publication_validation=publication.report,
            final_factreasoner=final_fact,
            risk_catalog=RISK_CATALOG,
            risk_mapping=risk_mapping,
            privacy=privacy,
        )

    def privacy_safe_reviewed(self):
        artifact = self.artifact
        for binding in self.artifact.bindings:
            if binding.origin.value == "quoted":
                artifact = withhold_binding(
                    artifact,
                    binding.binding_id,
                    reason="source_excerpt_withheld",
                )
        return artifact

    def claim_gates(self):
        records = []
        for binding in self.artifact.bindings:
            candidate = ClaimCandidate.from_binding(self.artifact.target, binding)
            decisions = ()
            if binding.origin.value == "quoted":
                decisions = tuple(
                    ProseCheckerDecision.for_candidate(
                        candidate,
                        gate=gate,
                        checker="tests/review-audit-checker-v1",
                        method="bounded_semantic_review",
                        status=DecisionStatus.ACCEPTED,
                        reason=(
                            "semantic_entity_scope"
                            if gate is GateName.ENTITY_SCOPE
                            else "semantic_field_fit"
                            if gate is GateName.FIELD_FIT
                            else "semantic_value_support"
                        ),
                    )
                    for gate in (
                        GateName.ENTITY_SCOPE,
                        GateName.FIELD_FIT,
                        GateName.VALUE_SUPPORT,
                    )
                )
            records.append(
                evaluate_claim_gate(
                    candidate,
                    self.sources,
                    checker_decisions=decisions,
                )
            )
        return tuple(records)

    def test_replays_review_gate_and_recomputes_effective_omissions(self) -> None:
        reviewed = self.reviewed()
        first = audit_reviewed_candidate(reviewed, self.sources)
        second = audit_reviewed_candidate(reviewed, self.sources)
        self.assertEqual(first.to_dict(), second.to_dict())
        decoded = ReviewedCandidateAudit.from_dict(first.to_dict())
        verify_reviewed_candidate_audit(decoded, reviewed, self.sources)
        fields = {item.field_path: item for item in first.fields}
        self.assertFalse(fields["identity.summary"].present)
        self.assertEqual("reassigned", fields["identity.summary"].reason.value)
        self.assertTrue(fields["evaluation.results_summary"].present)
        checks = {item.name: item for item in first.checks}
        self.assertEqual("unavailable", checks["claim_support"].status.value)
        self.assertEqual(
            "passed", checks["review_reassignment_gates"].status.value
        )
        self.assertEqual("passed", checks["omissions"].status.value)
        self.assertEqual("unavailable", checks["factreasoner"].status.value)
        self.assertEqual("unavailable", checks["publication"].status.value)
        self.assertEqual(
            "reviewed_candidate_requires_downstream_revalidation",
            first.verdict,
        )
        serialized = json.dumps(first.to_dict(), sort_keys=True)
        self.assertNotIn("instruction-tuned text model built", serialized)

    def test_fixture_checker_identity_cannot_seal_reviewed_candidate(self) -> None:
        reviewed = self.privacy_safe_reviewed()
        closure = self.closure(reviewed)

        audit = audit_reviewed_candidate(
            reviewed,
            self.sources,
            closure_evidence=closure,
        )

        checks = {item.name: item for item in audit.checks}
        self.assertEqual("failed", checks["factreasoner"].status.value)
        self.assertEqual(
            "factreasoner_checker_identity_mismatch",
            checks["factreasoner"].reason,
        )
        self.assertEqual(
            "reviewed_candidate_requires_downstream_revalidation",
            audit.verdict,
        )
        verify_reviewed_candidate_audit(
            audit,
            reviewed,
            self.sources,
            closure_evidence=closure,
        )

    def test_pinned_identity_without_execution_binding_cannot_seal(self) -> None:
        reviewed = self.privacy_safe_reviewed()
        closure = self.closure(reviewed, PinnedIdentitySupportingChecker())

        audit = audit_reviewed_candidate(
            reviewed,
            self.sources,
            closure_evidence=closure,
        )

        checks = {item.name: item for item in audit.checks}
        self.assertEqual("unavailable", checks["factreasoner"].status.value)
        self.assertEqual(
            "factreasoner_execution_binding_unavailable",
            checks["factreasoner"].reason,
        )
        self.assertNotEqual("reviewed_candidate_closed", audit.verdict)

    def test_stale_privacy_hash_cannot_close(self) -> None:
        reviewed = self.privacy_safe_reviewed()
        closure = self.closure(reviewed)
        stale = ReviewClosureEvidence(
            claim_gate_records=closure.claim_gate_records,
            publication_catalog=closure.publication_catalog,
            publication_factreasoner=closure.publication_factreasoner,
            publication_validation=closure.publication_validation,
            final_factreasoner=closure.final_factreasoner,
            risk_catalog=closure.risk_catalog,
            risk_mapping=closure.risk_mapping,
            privacy=replace(closure.privacy, scanned_card_sha256="0" * 64),
        )

        audit = audit_reviewed_candidate(
            reviewed,
            self.sources,
            closure_evidence=stale,
        )

        checks = {item.name: item for item in audit.checks}
        self.assertEqual("failed", checks["privacy"].status.value)
        self.assertEqual(
            "reviewed_candidate_requires_downstream_revalidation",
            audit.verdict,
        )

    def test_publication_catalog_must_bind_the_replay_sources(self) -> None:
        reviewed = self.privacy_safe_reviewed()
        closure = self.closure(reviewed, PinnedIdentitySupportingChecker())
        publication_source_ids = {
            item.source_id for item in self.publication_catalog.documents
        }
        unbound_sources = tuple(
            item
            for item in self.sources
            if item.source_id not in publication_source_ids
        )

        audit = audit_reviewed_candidate(
            reviewed,
            unbound_sources,
            closure_evidence=closure,
        )

        checks = {item.name: item for item in audit.checks}
        self.assertEqual("failed", checks["publication"].status.value)
        self.assertEqual(
            "publication_revalidation_mismatch",
            checks["publication"].reason,
        )
        self.assertNotEqual("reviewed_candidate_closed", audit.verdict)

    def test_self_consistent_fabricated_risk_summary_cannot_close(self) -> None:
        reviewed = self.privacy_safe_reviewed()
        closure = self.closure(reviewed)
        risk_mapping = json.loads(json.dumps(closure.risk_mapping))
        summary = RiskStageSummary.from_dict(risk_mapping["summary"])
        risk_mapping["summary"] = RiskStageSummary(
            status=summary.status,
            reason="applicability_gate_completed",
            catalog_sha256=summary.catalog_sha256,
            context_sha256=summary.context_sha256,
            publisher_context_candidate_ids=(
                summary.publisher_context_candidate_ids
            ),
            publisher_reported_risk_candidate_ids=(
                summary.publisher_reported_risk_candidate_ids
            ),
            taxonomy_candidate_count=summary.taxonomy_candidate_count,
            taxonomy_included_count=summary.taxonomy_included_count,
            mapping_report_sha256=summary.mapping_report_sha256,
        ).to_dict()
        fabricated = ReviewClosureEvidence(
            claim_gate_records=closure.claim_gate_records,
            publication_catalog=closure.publication_catalog,
            publication_factreasoner=closure.publication_factreasoner,
            publication_validation=closure.publication_validation,
            final_factreasoner=closure.final_factreasoner,
            risk_catalog=closure.risk_catalog,
            risk_mapping=risk_mapping,
            privacy=closure.privacy,
        )

        audit = audit_reviewed_candidate(
            reviewed,
            self.sources,
            closure_evidence=fabricated,
        )

        checks = {item.name: item for item in audit.checks}
        self.assertEqual("failed", checks["risk"].status.value)
        self.assertNotEqual("reviewed_candidate_closed", audit.verdict)

    def test_unavailable_factreasoner_and_empty_review_do_not_close(self) -> None:
        reviewed = self.privacy_safe_reviewed()
        unavailable = audit_reviewed_candidate(
            reviewed,
            self.sources,
            closure_evidence=self.closure(reviewed, UnavailableChecker()),
        )
        zero_review = audit_reviewed_candidate(
            self.artifact,
            self.sources,
            closure_evidence=self.closure(self.artifact),
        )

        unavailable_checks = {item.name: item for item in unavailable.checks}
        zero_checks = {item.name: item for item in zero_review.checks}
        self.assertEqual("unavailable", unavailable_checks["factreasoner"].status.value)
        self.assertEqual("unavailable", zero_checks["review_history"].status.value)
        self.assertNotEqual("reviewed_candidate_closed", unavailable.verdict)
        self.assertNotEqual("reviewed_candidate_closed", zero_review.verdict)

    def test_missing_replay_source_fails_closed(self) -> None:
        reviewed = self.reviewed()
        without_quote_source = tuple(
            item for item in self.sources if item.source_id != "synthetic-model-page"
        )
        with self.assertRaises(ValueError):
            audit_reviewed_candidate(reviewed, without_quote_source)


if __name__ == "__main__":
    unittest.main()
