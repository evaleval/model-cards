from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
)
from model_cards.artifact import CardArtifact
from model_cards.composer import CompositionResult
from model_cards.extraction import (
    ExtractionBatch,
    QuoteProposal,
    materialize_quote_batch,
)
from model_cards.factreasoner import (
    CheckOutcome,
    CheckerResponse,
    FactReasonerRecord,
)
from model_cards.field_repair import (
    FieldRepairRecord,
    verify_field_repair_record,
)
from model_cards.findings import OmissionAudit
from model_cards.models import LifecycleStatus, RelationToTarget
from model_cards.models import BindingOrigin, Disposition
from model_cards.official_discovery import discover_official_sources
from model_cards.official_sources import (
    OfficialFetchStatus,
    OfficialRemoteObject,
    collect_official_sources,
)
from model_cards.policy import decide_binding
from model_cards.pipeline import (
    CompositionStatus,
    PipelineError,
    PipelineRepairReport,
    PipelineResult,
    run_offline_pipeline,
    verify_pipeline_result,
)
from model_cards.risk_mapping import (
    ApplicabilityDecision,
    ApplicabilityStatus,
    INFERENCE_MODEL,
    NEXUS_PACKAGE_VERSION,
    NexusSelection,
    RiskCatalog,
    TaxonomyRisk,
)
from model_cards.run_state import RunStateError
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import build_source_document_catalog


REVISION = "a" * 40
README = """# Exact target

The exact target is an instruction-following language model.

## Uses

The publisher intends this model for personalized assistant responses.

## Conflicting summaries

First exact summary. Second exact summary.

## Private-looking example

/Users/alice/private-model-note
"""


class Adapter:
    def resolve_revision(self, model_id, requested_revision):
        return REVISION

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(
            FetchStatus.OK,
            json.dumps(
                {
                    "id": "acme/Instruct",
                    "sha": REVISION,
                    "pipeline_tag": "text-generation",
                    "config": {
                        "model_type": "fixture-transformer",
                        "torch_dtype": "float16",
                    },
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
            return RemoteObject(FetchStatus.OK, README.encode("utf-8"))
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                b'{"model_type":"fixture-transformer","torch_dtype":"float16"}',
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class UnavailableAdapter(Adapter):
    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(FetchStatus.GATED, reason_code="auth_required")

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        return RemoteObject(FetchStatus.GATED, reason_code="auth_required")


class OfficialLinkedAdapter(Adapter):
    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    README
                    + "\n[Official developer code](https://github.com/acme/instruct)\n"
                ).encode("utf-8"),
            )
        return super().fetch_file(
            model_id, revision, repo_path, max_bytes=max_bytes
        )


class OfficialFixtureAdapter:
    def fetch(self, url, *, max_bytes, max_redirects):
        if url != "https://github.com/acme/instruct":
            return OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE,
                reason_code="fixture_not_provided",
            )
        return OfficialRemoteObject(
            OfficialFetchStatus.OK,
            content=(
                "Official exact-target developer documentation for acme/Instruct."
            ).encode("utf-8"),
            final_url=url,
            redirect_chain=(url,),
            media_type="text/plain",
        )

class SupportingFactChecker:
    checker_id = "tests/supporting_fact_checker"
    checker_revision = "fixture-v1"

    def check(self, request):
        return CheckerResponse(
            outcome=CheckOutcome.SUPPORT,
            reason_code="fixture_source_support",
            cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
        )


class SelectiveFactChecker:
    checker_revision = "fixture-v1"

    def __init__(self, field_path: str, outcome: CheckOutcome) -> None:
        self.field_path = field_path
        self.outcome = outcome
        self.checker_id = f"tests/selective_{outcome.value}_{field_path.replace('.', '_')}"

    def check(self, request):
        if request.atom.field_path == self.field_path:
            return CheckerResponse(
                outcome=self.outcome,
                reason_code=f"fixture_{self.outcome.value}",
                cited_chunk_ids=(
                    (request.contexts[0].chunk.chunk_id,)
                    if self.outcome
                    in {CheckOutcome.SUPPORT, CheckOutcome.CONTRADICTION}
                    else ()
                ),
            )
        return CheckerResponse(
            outcome=CheckOutcome.SUPPORT,
            reason_code="fixture_source_support",
            cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
        )


class FixtureRiskDetector:
    detector_name = "ai_atlas_nexus.generic_usecase"
    detector_version = NEXUS_PACKAGE_VERSION
    inference_model = INFERENCE_MODEL
    inference_config_sha256 = "c" * 64

    def detect(self, contexts, catalog):
        return (
            NexusSelection(
                "atlas-output-with-personal-data",
                tuple(item.context_id for item in contexts),
            ),
        )


class CountingRiskDetector(FixtureRiskDetector):
    def __init__(self) -> None:
        self.calls = 0

    def detect(self, contexts, catalog):
        self.calls += 1
        return super().detect(contexts, catalog)


class FixtureRiskChecker:
    def assess(self, candidate, contexts):
        return ApplicabilityDecision.for_candidate(
            candidate,
            status=ApplicabilityStatus.ACCEPTED,
            checker="deepseek/deepseek-v4-flash-0731",
            method="bounded_use_context_applicability",
            reason="specific_use_context_supported",
            rationale=(
                "The accepted publisher use context specifically involves personalized "
                "responses, making disclosure of personal data a relevant candidate risk."
            ),
        )


class WithholdingRiskChecker(FixtureRiskChecker):
    def assess(self, candidate, contexts):
        return ApplicabilityDecision.for_candidate(
            candidate,
            status=ApplicabilityStatus.WITHHELD,
            checker="deepseek/deepseek-v4-flash-0731",
            method="bounded_use_context_applicability",
            reason="risk_not_specific_to_context",
            rationale=(
                "The available publisher context does not specifically establish this "
                "taxonomy risk for the exact target, so the candidate is withheld."
            ),
        )


RISK_CATALOG = RiskCatalog.build(
    (
        TaxonomyRisk(
            risk_id="atlas-output-with-personal-data",
            name="Output with personal data",
            description="A model might reveal personal data in generated output.",
            source_url="https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas",
        ),
    )
)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = self.root / "bundle"
        self.run = self.root / "run"
        collect_hf_source_bundle("acme/Instruct", self.bundle, Adapter())

    def catalog(self):
        return build_source_document_catalog(replay_source_bundle(self.bundle))

    def quote_input(self, *, field_path: str, value, quote: str):
        catalog = self.catalog()
        readme = next(
            item for item in catalog.documents if item.source_uri.endswith("/README.md")
        )
        proposal = QuoteProposal(
            source_id=readme.source_id,
            field_path=field_path,
            value=value,
            quote=quote,
            claim_entity=f"acme/Instruct@{REVISION}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        batch = ExtractionBatch.build(
            target=catalog.target,
            source_catalog_sha256=catalog.catalog_sha256,
            provider="Baidu",
            inference_config_sha256="b" * 64,
            proposals=(proposal,),
        )
        candidate = materialize_quote_batch(batch, catalog).candidates[0]
        decisions = (
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.FIELD_FIT,
                checker="tests/prose_checker",
                method="bounded_semantic_field_review",
                status=DecisionStatus.ACCEPTED,
                reason="fixture_field_fit",
            ),
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.VALUE_SUPPORT,
                checker="tests/prose_checker",
                method="bounded_complete_value_review",
                status=DecisionStatus.ACCEPTED,
                reason="fixture_value_support",
            ),
        )
        return batch, candidate, decisions

    def run_pipeline(self, **kwargs):
        return run_offline_pipeline(
            self.bundle,
            self.run,
            risk_catalog=RISK_CATALOG,
            **kwargs,
        )

    def test_fixture_e2e_is_validated_source_clean_and_idempotent(self) -> None:
        checker = SupportingFactChecker()
        first = self.run_pipeline(fact_checker=checker)
        self.assertEqual(LifecycleStatus.GENERATED_VALIDATED, first.lifecycle_status)
        self.assertTrue(first.validation.all_passed)
        self.assertEqual(CompositionStatus.COMPLETED, first.composition_status)
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual("acme/Instruct", card["identity"]["model_id"])
        self.assertEqual(REVISION, card["identity"]["revision"])
        self.assertEqual("fixture-transformer", card["model_details"]["architecture_type"])
        self.assertEqual("generated_validated", card["lifecycle"]["status"])
        serialized = json.dumps(first.to_dict(), sort_keys=True)
        self.assertNotIn("instruction-following language model", serialized)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("prompt", serialized.casefold())
        self.assertEqual(b"", (self.run / "usage.jsonl").read_bytes())
        second = self.run_pipeline(fact_checker=SupportingFactChecker())
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(b"", (self.run / "usage.jsonl").read_bytes())
        verify_pipeline_result(
            first,
            self.bundle,
            self.run,
            risk_catalog=RISK_CATALOG,
            fact_checker=SupportingFactChecker(),
        )

    def test_official_bundle_is_ancestry_bound_and_used_by_every_pipeline_stage(self) -> None:
        hf_bundle = self.root / "official-hf-bundle"
        official_bundle = self.root / "official-bundle"
        combined_run = self.root / "combined-run"
        collect_hf_source_bundle(
            "acme/Instruct", hf_bundle, OfficialLinkedAdapter()
        )
        discovery = discover_official_sources(replay_source_bundle(hf_bundle))
        collect_official_sources(
            discovery,
            official_bundle,
            OfficialFixtureAdapter(),
        )

        result = run_offline_pipeline(
            hf_bundle,
            combined_run,
            official_bundle_directory=official_bundle,
            fact_checker=SupportingFactChecker(),
            risk_catalog=RISK_CATALOG,
        )
        state = json.loads((combined_run / "source-state.json").read_text())
        catalog = json.loads((combined_run / "source-catalog.json").read_text())
        self.assertEqual("hf_and_official", state["mode"])
        self.assertTrue(result.source_bundle_id.startswith("combined_bundle_"))
        self.assertEqual(result.source_bundle_id, state["active_catalog_bundle_id"])
        self.assertEqual(result.source_catalog_sha256, state["active_catalog_sha256"])
        self.assertEqual("combined-source-document-catalog/v1", catalog["catalog_version"])
        self.assertGreater(state["document_count"], len(catalog["hf_catalog"]["document_ids"]))
        self.assertIn(
            "primary_src_",
            " ".join(catalog["official_catalog"]["document_ids"]),
        )

        journal_before = (combined_run / "journal.jsonl").read_bytes()
        replayed = verify_pipeline_result(
            result,
            hf_bundle,
            combined_run,
            official_bundle_directory=official_bundle,
            fact_checker=SupportingFactChecker(),
            risk_catalog=RISK_CATALOG,
        )
        self.assertEqual(result.to_dict(), replayed.to_dict())
        self.assertEqual(journal_before, (combined_run / "journal.jsonl").read_bytes())

    def test_quote_claim_requires_supplied_checker_decisions(self) -> None:
        summary = "The exact target is an instruction-following language model."
        batch, candidate, decisions = self.quote_input(
            field_path="identity.summary", value=summary, quote=summary
        )
        without_run = self.root / "without-checker"
        without = run_offline_pipeline(
            self.bundle,
            without_run,
            quote_batches=(batch,),
            fact_checker=SupportingFactChecker(),
            risk_catalog=RISK_CATALOG,
        )
        without_card = json.loads((without_run / "public-card.json").read_text())
        self.assertEqual("Not specified", without_card["identity"]["summary"])
        ref = next(item for item in without.claims if item.candidate_id == candidate.candidate_id)
        self.assertFalse(ref.projection_eligible)
        self.assertFalse(ref.included)

        with_result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SupportingFactChecker(),
        )
        with_card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual(summary, with_card["identity"]["summary"])
        ref = next(
            item for item in with_result.claims if item.candidate_id == candidate.candidate_id
        )
        self.assertTrue(ref.projection_eligible)
        self.assertTrue(ref.included)

    def test_conflicting_supported_values_are_audited_and_withheld(self) -> None:
        first = self.quote_input(
            field_path="identity.summary",
            value="First exact summary.",
            quote="First exact summary.",
        )
        second = self.quote_input(
            field_path="identity.summary",
            value="Second exact summary.",
            quote="Second exact summary.",
        )
        result = self.run_pipeline(
            quote_batches=(first[0], second[0]),
            prose_checker_decisions=(*first[2], *second[2]),
            fact_checker=SupportingFactChecker(),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual("Not specified", card["identity"]["summary"])
        self.assertEqual(1, result.conflict_count)
        self.assertFalse(result.validation.conflicts_clear)
        self.assertEqual(LifecycleStatus.GENERATED_UNREVIEWED, result.lifecycle_status)
        omission = json.loads((self.run / "omissions.json").read_text())
        summary = next(
            item for item in omission["records"] if item["field_path"] == "identity.summary"
        )
        self.assertEqual("conflicting", summary["reason"])

    def test_accepted_taxonomy_mapping_projects_as_a_registered_derivation(self) -> None:
        description = (
            "The publisher intends this model for personalized assistant responses."
        )
        batch, context_candidate, decisions = self.quote_input(
            field_path="use_and_risk.intended_uses[0]",
            value=description,
            quote=description,
        )
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SupportingFactChecker(),
            risk_detector=FixtureRiskDetector(),
            risk_checker=FixtureRiskChecker(),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        risks = card["use_and_risk"]["identified_risks"]
        self.assertEqual(1, len(risks))
        self.assertEqual("taxonomy_identified", risks[0]["identification_origin"])
        self.assertNotEqual("publisher_reported", risks[0]["identification_origin"])
        derivation = card["provenance"]["derivations"][
            "use_and_risk.identified_risks[0]"
        ][0]
        self.assertEqual("taxonomy-risk-derivation/v1", derivation["derivation_version"])
        self.assertEqual(result.risk.mapping_report_sha256, derivation["risk_report_sha256"])
        self.assertEqual(
            context_candidate.candidate_id,
            derivation["input_claims"][0]["candidate_id"],
        )
        self.assertEqual(
            next(
                item.gate_record_sha256
                for item in result.claims
                if item.candidate_id == context_candidate.candidate_id
            ),
            derivation["input_claims"][0]["gate_record_sha256"],
        )
        self.assertEqual(
            risks[0]["source_refs"], derivation["supporting_source_refs"]
        )
        local_artifact = json.loads((self.run / "card-artifact.json").read_text())
        self.assertEqual(1, len(local_artifact["derivations"]))
        self.assertEqual(
            derivation["applicability_decision_sha256"],
            local_artifact["derivations"][0]["applicability_decision_sha256"],
        )
        self.assertEqual(LifecycleStatus.GENERATED_VALIDATED, result.lifecycle_status)

        context_evidence = materialize_quote_batch(batch, self.catalog()).candidates[0].evidence
        disposition, reason = decide_binding(
            target=self.catalog().target,
            field_path="use_and_risk.identified_risks[0]",
            value=risks[0],
            claim_entity=f"acme/Instruct@{REVISION}",
            relation=RelationToTarget.EXACT_TARGET,
            origin=BindingOrigin.QUOTED,
            evidence=context_evidence,
        )
        self.assertEqual(Disposition.REJECTED, disposition)
        self.assertEqual("taxonomy_risk_requires_derivation", reason)

        # A changed upstream digest cannot replay as the same derivation/artifact.
        tampered = deepcopy(local_artifact)
        tampered["derivations"][0]["risk_candidate_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            CardArtifact.from_dict(tampered)
        derivation = CardArtifact.from_dict(local_artifact).derivations[0]
        with self.assertRaisesRegex(ValueError, "contiguously"):
            CardArtifact(
                target=self.catalog().target,
                bindings=CardArtifact.from_dict(local_artifact).bindings,
                derivations=(replace(derivation, field_path="use_and_risk.identified_risks[1]"),),
            )

        replayed = verify_pipeline_result(
            result,
            self.bundle,
            self.run,
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SupportingFactChecker(),
            risk_catalog=RISK_CATALOG,
            risk_detector=FixtureRiskDetector(),
            risk_checker=FixtureRiskChecker(),
        )
        self.assertEqual(result.to_dict(), replayed.to_dict())

    def test_grounded_context_without_risk_provider_emits_no_taxonomy_risk(self) -> None:
        description = (
            "The publisher intends this model for personalized assistant responses."
        )
        batch, _, decisions = self.quote_input(
            field_path="use_and_risk.intended_uses[0]",
            value=description,
            quote=description,
        )
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SupportingFactChecker(),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual("Not specified", card["use_and_risk"]["identified_risks"])
        self.assertEqual("unavailable", result.risk.status)
        self.assertNotIn("derivations", card["provenance"])
        self.assertEqual(LifecycleStatus.GENERATED_UNREVIEWED, result.lifecycle_status)

    def test_withheld_taxonomy_candidate_never_projects_or_derives(self) -> None:
        description = (
            "The publisher intends this model for personalized assistant responses."
        )
        batch, _, decisions = self.quote_input(
            field_path="use_and_risk.intended_uses[0]",
            value=description,
            quote=description,
        )
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SupportingFactChecker(),
            risk_detector=FixtureRiskDetector(),
            risk_checker=WithholdingRiskChecker(),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual("Not specified", card["use_and_risk"]["identified_risks"])
        self.assertNotIn("derivations", card["provenance"])
        self.assertEqual(1, result.risk.taxonomy_candidate_count)
        self.assertEqual(0, result.risk.taxonomy_included_count)
        self.assertFalse(result.validation.risk_passed)
        self.assertEqual(LifecycleStatus.GENERATED_UNREVIEWED, result.lifecycle_status)

    def test_contradiction_is_withheld_field_locally_and_supported_claims_remain(self) -> None:
        summary = "The exact target is an instruction-following language model."
        intended = "The publisher intends this model for personalized assistant responses."
        summary_input = self.quote_input(
            field_path="identity.summary", value=summary, quote=summary
        )
        intended_input = self.quote_input(
            field_path="use_and_risk.intended_uses[0]",
            value=intended,
            quote=intended,
        )
        result = self.run_pipeline(
            quote_batches=(summary_input[0], intended_input[0]),
            prose_checker_decisions=(*summary_input[2], *intended_input[2]),
            fact_checker=SelectiveFactChecker(
                "identity.summary", CheckOutcome.CONTRADICTION
            ),
            risk_detector=FixtureRiskDetector(),
            risk_checker=FixtureRiskChecker(),
        )

        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual("Not specified", card["identity"]["summary"])
        self.assertNotEqual(
            "Not specified", card["use_and_risk"]["intended_uses"]
        )
        self.assertEqual(1, len(card["use_and_risk"]["identified_risks"]))
        references = {item.candidate_id: item for item in result.claims}
        self.assertFalse(references[summary_input[1].candidate_id].included)
        self.assertTrue(references[intended_input[1].candidate_id].included)
        self.assertTrue(result.validation.factreasoner_passed)
        self.assertTrue(result.validation.risk_passed)
        self.assertFalse(result.validation.omissions_clear)
        self.assertEqual(LifecycleStatus.GENERATED_UNREVIEWED, result.lifecycle_status)

        repairs = PipelineRepairReport.from_dict(
            json.loads((self.run / "repairs.json").read_text())
        )
        self.assertEqual((summary_input[1].candidate_id,), repairs.actionable_candidate_ids)
        self.assertEqual(0, repairs.semantic_submission_count)
        self.assertEqual(1, len(repairs.records))
        self.assertEqual("withheld", repairs.records[0].outcome.value)
        self.assertEqual((), repairs.records[0].attempts)

        original_fact = FactReasonerRecord.from_dict(
            json.loads((self.run / "factreasoner-original.json").read_text())
        )
        original_summary = next(
            item
            for item in original_fact.field_decisions
            if item.field_path == "identity.summary"
        )
        self.assertIn(CheckOutcome.CONTRADICTION, original_summary.outcomes)
        final_fact = FactReasonerRecord.from_dict(
            json.loads((self.run / "factreasoner.json").read_text())
        )
        self.assertEqual(final_fact.content_sha256, result.factreasoner_sha256)
        self.assertNotIn(
            "identity.summary",
            {item.field_path for item in final_fact.field_decisions},
        )
        omission = OmissionAudit.from_dict(
            json.loads((self.run / "omissions.json").read_text())
        )
        summary_omission = next(
            item for item in omission.records if item.field_path == "identity.summary"
        )
        self.assertEqual("withheld", summary_omission.reason.value)

    def test_neutral_after_fallback_is_withheld_with_zero_semantic_attempts(self) -> None:
        summary = "The exact target is an instruction-following language model."
        batch, candidate, decisions = self.quote_input(
            field_path="identity.summary", value=summary, quote=summary
        )
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SelectiveFactChecker("identity.summary", CheckOutcome.NEUTRAL),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual("Not specified", card["identity"]["summary"])
        self.assertFalse(
            next(item for item in result.claims if item.candidate_id == candidate.candidate_id).included
        )
        repairs = PipelineRepairReport.from_dict(
            json.loads((self.run / "repairs.json").read_text())
        )
        self.assertEqual((candidate.candidate_id,), repairs.actionable_candidate_ids)
        self.assertEqual(0, repairs.semantic_submission_count)
        original_fact = FactReasonerRecord.from_dict(
            json.loads((self.run / "factreasoner-original.json").read_text())
        )
        field = next(
            item
            for item in original_fact.field_decisions
            if item.field_path == "identity.summary"
        )
        self.assertIn(CheckOutcome.NEUTRAL, field.outcomes)

    def test_unavailable_fact_check_remains_visible_and_unreviewed(self) -> None:
        summary = "The exact target is an instruction-following language model."
        batch, candidate, decisions = self.quote_input(
            field_path="identity.summary", value=summary, quote=summary
        )
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SelectiveFactChecker(
                "identity.summary", CheckOutcome.UNAVAILABLE
            ),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual(summary, card["identity"]["summary"])
        self.assertTrue(
            next(item for item in result.claims if item.candidate_id == candidate.candidate_id).included
        )
        repairs = PipelineRepairReport.from_dict(
            json.loads((self.run / "repairs.json").read_text())
        )
        self.assertEqual((), repairs.records)
        self.assertFalse(result.validation.factreasoner_passed)
        self.assertEqual(LifecycleStatus.GENERATED_UNREVIEWED, result.lifecycle_status)
        final_fact = FactReasonerRecord.from_dict(
            json.loads((self.run / "factreasoner.json").read_text())
        )
        field = next(
            item
            for item in final_fact.field_decisions
            if item.field_path == "identity.summary"
        )
        self.assertIn(CheckOutcome.UNAVAILABLE, field.outcomes)

    def test_repair_record_replays_tamper_fails_and_resume_is_deterministic(self) -> None:
        summary = "The exact target is an instruction-following language model."
        batch, candidate, decisions = self.quote_input(
            field_path="identity.summary", value=summary, quote=summary
        )
        checker = SelectiveFactChecker("identity.summary", CheckOutcome.CONTRADICTION)
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=checker,
        )
        encoded = json.loads((self.run / "repairs.json").read_text())
        report = PipelineRepairReport.from_dict(encoded)
        record = report.records[0]
        self.assertEqual(
            record.to_dict(), FieldRepairRecord.from_dict(record.to_dict()).to_dict()
        )
        extraction = json.loads((self.run / "extraction.json").read_text())
        candidates = tuple(ClaimCandidate.from_dict(item) for item in extraction["candidates"])
        gates = tuple(
            ClaimGateRecord.from_dict(item)
            for item in json.loads((self.run / "claim-gates.json").read_text())["records"]
        )
        verify_field_repair_record(
            record,
            field_path=candidate.field_path,
            predecessor_candidate_id=candidate.candidate_id,
            candidates=candidates,
            gate_records=gates,
            sources=self.catalog().documents,
            composition_result=CompositionResult.from_dict(
                json.loads((self.run / "composition-original.json").read_text())
            ),
            omission_audit=OmissionAudit.from_dict(
                json.loads((self.run / "omissions-original.json").read_text())
            ),
            factreasoner_record=FactReasonerRecord.from_dict(
                json.loads((self.run / "factreasoner-original.json").read_text())
            ),
            submissions=(),
        )
        repair_event = next(
            json.loads(line)
            for line in (self.run / "journal.jsonl").read_text().splitlines()
            if json.loads(line)["stage"] == "repair"
        )
        self.assertEqual(1, repair_event["metrics"]["record_count"])
        self.assertEqual(0, repair_event["metrics"]["semantic_submission_count"])
        self.assertEqual(1, repair_event["metrics"]["fact_withheld_count"])

        tampered = deepcopy(encoded)
        tampered["records"][0]["context"]["factreasoner_record_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            PipelineRepairReport.from_dict(tampered)

        replayed = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SelectiveFactChecker(
                "identity.summary", CheckOutcome.CONTRADICTION
            ),
        )
        self.assertEqual(result.to_dict(), replayed.to_dict())
        verify_pipeline_result(
            result,
            self.bundle,
            self.run,
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SelectiveFactChecker(
                "identity.summary", CheckOutcome.CONTRADICTION
            ),
            risk_catalog=RISK_CATALOG,
        )
        repair_path = self.run / "repairs.json"
        repair_path.write_text(repair_path.read_text() + " ", encoding="utf-8")
        with self.assertRaises(RunStateError):
            self.run_pipeline(
                quote_batches=(batch,),
                prose_checker_decisions=decisions,
                fact_checker=SelectiveFactChecker(
                    "identity.summary", CheckOutcome.CONTRADICTION
                ),
            )

    def test_withheld_use_context_reruns_risk_omission_and_privacy(self) -> None:
        description = (
            "The publisher intends this model for personalized assistant responses."
        )
        batch, candidate, decisions = self.quote_input(
            field_path="use_and_risk.intended_uses[0]",
            value=description,
            quote=description,
        )
        detector = CountingRiskDetector()
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SelectiveFactChecker(
                "use_and_risk.intended_uses", CheckOutcome.CONTRADICTION
            ),
            risk_detector=detector,
            risk_checker=FixtureRiskChecker(),
        )
        card_path = self.run / "public-card.json"
        card = json.loads(card_path.read_text())
        self.assertEqual("Not specified", card["use_and_risk"]["intended_uses"])
        self.assertEqual("Not specified", card["use_and_risk"]["identified_risks"])
        self.assertEqual(0, detector.calls)
        self.assertEqual((), result.risk.publisher_context_candidate_ids)
        self.assertEqual(0, result.risk.taxonomy_candidate_count)
        self.assertFalse(
            next(item for item in result.claims if item.candidate_id == candidate.candidate_id).included
        )
        omission = OmissionAudit.from_dict(
            json.loads((self.run / "omissions.json").read_text())
        )
        intended = next(
            item
            for item in omission.records
            if item.field_path == "use_and_risk.intended_uses"
        )
        self.assertEqual("withheld", intended.reason.value)
        self.assertEqual(
            hashlib.sha256(card_path.read_bytes()).hexdigest(),
            result.privacy.scanned_card_sha256,
        )
        self.assertEqual(0, result.privacy.withheld_candidate_ids.count(candidate.candidate_id))
        self.assertTrue(result.validation.schema_passed)
        self.assertTrue(result.validation.privacy_passed)

    def test_actionable_taxonomy_derivation_is_withheld_before_final_export(self) -> None:
        description = (
            "The publisher intends this model for personalized assistant responses."
        )
        batch, _, decisions = self.quote_input(
            field_path="use_and_risk.intended_uses[0]",
            value=description,
            quote=description,
        )
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SelectiveFactChecker(
                "use_and_risk.identified_risks", CheckOutcome.CONTRADICTION
            ),
            risk_detector=FixtureRiskDetector(),
            risk_checker=FixtureRiskChecker(),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertEqual("Not specified", card["use_and_risk"]["identified_risks"])
        self.assertNotIn("derivations", card["provenance"])
        repairs = PipelineRepairReport.from_dict(
            json.loads((self.run / "repairs.json").read_text())
        )
        self.assertEqual((), repairs.records)
        self.assertEqual(1, len(repairs.factreasoner_withheld_derivation_ids))
        self.assertEqual(1, result.risk.taxonomy_candidate_count)
        self.assertEqual(0, result.risk.taxonomy_included_count)
        self.assertFalse(result.validation.risk_passed)
        final_fact = FactReasonerRecord.from_dict(
            json.loads((self.run / "factreasoner.json").read_text())
        )
        self.assertNotIn(
            "use_and_risk.identified_risks",
            {item.field_path for item in final_fact.field_decisions},
        )

    def test_unsafe_exact_value_is_privacy_withheld_before_export(self) -> None:
        value = "/Users/alice/private-model-note"
        batch, candidate, decisions = self.quote_input(
            field_path="identity.summary", value=value, quote=value
        )
        result = self.run_pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=SupportingFactChecker(),
        )
        card = json.loads((self.run / "public-card.json").read_text())
        self.assertNotIn("/Users/", json.dumps(card))
        self.assertEqual("Not specified", card["identity"]["summary"])
        self.assertEqual((candidate.candidate_id,), result.privacy.withheld_candidate_ids)
        self.assertFalse(result.validation.privacy_passed)
        self.assertEqual(LifecycleStatus.GENERATED_UNREVIEWED, result.lifecycle_status)
        self.assertNotIn("/Users/", json.dumps(result.to_dict()))

    def test_sparse_unavailable_bundle_stays_unreviewed_without_inventing_claims(self) -> None:
        sparse_bundle = self.root / "sparse-bundle"
        sparse_run = self.root / "sparse-run"
        collect_hf_source_bundle("acme/Instruct", sparse_bundle, UnavailableAdapter())
        result = run_offline_pipeline(
            sparse_bundle,
            sparse_run,
            risk_catalog=RISK_CATALOG,
        )
        self.assertEqual(CompositionStatus.UNAVAILABLE, result.composition_status)
        self.assertEqual((), result.claims)
        self.assertEqual(LifecycleStatus.GENERATED_UNREVIEWED, result.lifecycle_status)
        self.assertFalse(result.validation.claim_support_passed)
        card = json.loads((sparse_run / "public-card.json").read_text())
        self.assertEqual("acme/Instruct", card["identity"]["model_id"])
        self.assertEqual("Not specified", card["identity"]["summary"])
        fact = json.loads((sparse_run / "factreasoner.json").read_text())
        self.assertTrue(fact["atoms"])
        self.assertTrue(
            all(item["outcome"] == "unavailable" for item in fact["decisions"])
        )

    def test_result_and_registered_artifact_tampering_fail_closed(self) -> None:
        result = self.run_pipeline(fact_checker=SupportingFactChecker())
        encoded = result.to_dict()
        self.assertEqual(encoded, PipelineResult.from_dict(deepcopy(encoded)).to_dict())
        tampered = deepcopy(encoded)
        tampered["conflict_count"] = 7
        with self.assertRaisesRegex(PipelineError, "digest"):
            PipelineResult.from_dict(tampered)

        public_path = self.run / "public-card.json"
        public_path.write_text(public_path.read_text() + " ", encoding="utf-8")
        with self.assertRaises(RunStateError):
            self.run_pipeline(fact_checker=SupportingFactChecker())

    def test_wrong_catalog_quote_batch_is_rejected_as_stale(self) -> None:
        batch, _, _ = self.quote_input(
            field_path="identity.summary",
            value="First exact summary.",
            quote="First exact summary.",
        )
        other = ExtractionBatch.build(
            target=batch.target,
            source_catalog_sha256="0" * 64,
            provider="Baidu",
            inference_config_sha256="b" * 64,
            proposals=batch.proposals,
        )
        with self.assertRaisesRegex(Exception, "stale"):
            self.run_pipeline(quote_batches=(other,))


if __name__ == "__main__":
    unittest.main()
