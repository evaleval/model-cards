from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
import importlib.util
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.claim_gate import ClaimGateRecord
from model_cards.cli import main as modelcards_main
from model_cards.extraction import (
    EXTRACTION_SCHEMA_NAME,
    USE_RISK_EXTRACTION_SCHEMA_NAME,
)
from model_cards.factreasoner import FactReasonerRecord, IBMFactReasonerAdapter
from model_cards.family_risk import (
    FamilyDecisionStatus,
    FamilyRiskAuthorizationReport,
    build_family_risk_authorization_report,
)
from model_cards.orchestration import (
    ORCHESTRATION_MANIFEST_FILENAME,
    ProviderOrchestrationResult,
    run_provider_assisted_pipeline,
)
from model_cards.provider import (
    MODEL_ID,
    OPENROUTER_API_URL,
    OPENROUTER_ROUTE_URL,
    PINNED_PROVIDER,
    ProviderHttpRequest,
    ProviderHttpResponse,
)
from model_cards.provider_execution import (
    PROVIDER_EXECUTION_MANIFEST_FILENAME,
    ProviderExecutionRunEvidence,
)
from model_cards.publication_validation import PublicationValidationReport
from model_cards.review import accept_binding, save_artifact
from model_cards.review_audit import (
    CLOSED_VERDICT,
    ReviewClosureEvidence,
    audit_reviewed_candidate,
)
from model_cards.quality_report import (
    _load_exports,
    _load_extraction,
    _load_repair_chain,
    _load_risk,
)
from model_cards.risk_mapping import (
    NEXUS_PACKAGE_VERSION,
    RiskCatalog,
    load_pinned_nexus_catalog,
)
from model_cards.run_ledger import UsageLedger
from model_cards.pipeline import PrivacyScanReport
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
)
from model_cards.source_state import load_source_state


REVISION = "a" * 40
FAMILY_MODEL_ID = "google/gemma-3-4b-it"
USE_STATEMENT = (
    "The google/gemma-3-4b-it checkpoint is intended for research assistants "
    "that answer factual questions."
)
FAMILY_USE_STATEMENT = (
    "Gemma 3 models are intended for research assistants that generate creative "
    "text and factual answers."
)
SYNTHETIC_KEY = "synthetic_openrouter_key_for_offline_integration"


class _BundleAdapter:
    def resolve_revision(self, model_id, requested_revision):
        return REVISION

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(
            FetchStatus.OK,
            json.dumps(
                {
                    "id": model_id,
                    "sha": revision,
                    "pipeline_tag": "text-generation",
                    "config": {"model_type": "gemma3"},
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
            return RemoteObject(
                FetchStatus.OK,
                (
                    "# Intended use\n"
                    + USE_STATEMENT
                    + "\n\n## Gemma 3 family use\n"
                    + FAMILY_USE_STATEMENT
                    + "\n"
                ).encode("utf-8"),
            )
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                b'{"architectures":["FixtureTransformerForCausalLM"],"model_type":"gemma3"}',
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


def _route_payload() -> bytes:
    return json.dumps(
        {
            "data": {
                "id": MODEL_ID,
                "endpoints": [
                    {
                        "provider_name": PINNED_PROVIDER,
                        "model_id": MODEL_ID,
                        "status": 0,
                        "supported_parameters": [
                            "max_tokens",
                            "reasoning",
                            "response_format",
                            "structured_outputs",
                            "temperature",
                        ],
                        "pricing": {
                            "prompt": "0.000000001",
                            "completion": "0.000000001",
                        },
                        "context_length": 1_000_000,
                        "max_completion_tokens": 16_384,
                    }
                ],
            }
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _success_payload(decision) -> bytes:
    return json.dumps(
        {
            "model": MODEL_ID,
            "provider": PINNED_PROVIDER,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(
                            decision, sort_keys=True, separators=(",", ":")
                        ),
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
                "cost": "0",
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class _OfflineOpenRouterTransport:
    """Return deterministic structured decisions without opening a socket."""

    def __init__(self, *, forbid_requests: bool = False):
        self.forbid_requests = forbid_requests
        self.requests: list[ProviderHttpRequest] = []
        self.schema_names: list[str] = []
        self.post_payloads: list[dict] = []

    def open(self, request: ProviderHttpRequest) -> ProviderHttpResponse:
        if self.forbid_requests:
            raise AssertionError("replay attempted provider HTTP")
        self.requests.append(request)
        if request.method == "GET":
            return ProviderHttpResponse(
                200,
                OPENROUTER_ROUTE_URL,
                body=_route_payload(),
            )

        payload = json.loads((request.body or b"").decode("utf-8"))
        self.post_payloads.append(payload)
        schema_name = payload["response_format"]["json_schema"]["name"]
        self.schema_names.append(schema_name)
        decision = self._decision(schema_name, payload)
        return ProviderHttpResponse(
            200,
            OPENROUTER_API_URL,
            body=_success_payload(decision),
        )

    @staticmethod
    def _user_payload(payload: dict) -> dict:
        return json.loads(payload["messages"][1]["content"])

    def _decision(self, schema_name: str, request_payload: dict):
        if schema_name == EXTRACTION_SCHEMA_NAME:
            value = self._user_payload(request_payload)
            target = value["target"]
            return {
                "proposals": [
                    {
                        "source_id": value["source"]["source_id"],
                        "field_path": "use_and_risk.intended_uses[0]",
                        "value_json": json.dumps(USE_STATEMENT),
                        "quote": USE_STATEMENT,
                        "claim_entity": (
                            target["model_id"] + "@" + target["revision"]
                        ),
                        "relation": "exact_target",
                        "origin": "source_stated",
                    },
                    {
                        "source_id": value["source"]["source_id"],
                        "field_path": "use_and_risk.intended_uses[1]",
                        "value_json": json.dumps(FAMILY_USE_STATEMENT),
                        "quote": FAMILY_USE_STATEMENT,
                        "claim_entity": "Gemma 3 model family",
                        "relation": "model_family",
                        "origin": "source_stated",
                    },
                ]
            }
        if schema_name == USE_RISK_EXTRACTION_SCHEMA_NAME:
            return {"proposals": []}
        if schema_name == "model_card_entity_scope_v2":
            return {"status": "accepted", "reason": "semantic_entity_scope"}
        if schema_name == "model_card_field_fit_v2":
            return {"status": "accepted", "reason": "semantic_field_fit"}
        if schema_name == "model_card_value_support_v2":
            return {"status": "accepted", "reason": "semantic_value_support"}
        if schema_name == "model_card_family_checkpoint_applicability_v1":
            return {
                "status": "accepted",
                "reason": "family_statement_applies_to_checkpoint",
                "rationale": (
                    "The statement names the Gemma 3 family without excluding the "
                    "instruction-tuned 4B checkpoint, whose registry membership is "
                    "independently established."
                ),
            }
        if schema_name == "nexus_generic_risk_selection_v1":
            schema = request_payload["response_format"]["json_schema"]["schema"]
            allowed = schema["properties"]["prediction"]["items"]["enum"]
            if "Hallucination" not in allowed:
                raise AssertionError("pinned Nexus schema omitted Hallucination")
            return {"prediction": ["Hallucination"]}
        if schema_name == "model_card_risk_applicability_v1":
            return {
                "status": "accepted",
                "reason": "specific_use_context_supported",
                "rationale": (
                    "A factual-question assistant can produce unsupported factual "
                    "answers, so this taxonomy risk is specific to the grounded use."
                ),
            }
        if schema_name == "model_card_factreasoner_batch_v1":
            value = self._user_payload(request_payload)
            return {
                "decisions": [
                    {
                        "request_sha256": check["request_sha256"],
                        "outcome": (
                            "contradiction"
                            if (
                                'field "model_details.architecture_type" asserts: gemma3'
                                in check["hypothesis"]
                            )
                            else "support"
                        ),
                        "cited_chunk_ids": [check["context_ids"][0]],
                    }
                    for check in value["checks"]
                ]
            }
        raise AssertionError(f"unexpected provider schema: {schema_name}")


_HAS_NEXUS = importlib.util.find_spec("ai_atlas_nexus") is not None
_HAS_FACTREASONER = IBMFactReasonerAdapter.is_installed()


@dataclass(frozen=True)
class _FamilyProviderRun:
    root: Path
    bundle: Path
    run: Path
    ledger: Path
    decisions: Path
    aggregate: Path
    catalog: RiskCatalog
    result: ProviderOrchestrationResult
    transport: _OfflineOpenRouterTransport


def _build_family_provider_run(root: Path) -> _FamilyProviderRun:
    """Build one accepted-family offline provider run for closure tests."""

    bundle = root / "bundle"
    run = root / "run"
    ledger = run / "usage.jsonl"
    decisions = run / "provider-decisions"
    aggregate = root / "aggregate-budget.jsonl"
    collect_hf_source_bundle(FAMILY_MODEL_ID, bundle, _BundleAdapter())
    catalog = load_pinned_nexus_catalog()
    transport = _OfflineOpenRouterTransport()
    result = run_provider_assisted_pipeline(
        bundle,
        run,
        provider=PINNED_PROVIDER,
        ledger_path=ledger,
        decision_dir=decisions,
        aggregate_budget_path=aggregate,
        environment={"OPENROUTER_API_KEY": SYNTHETIC_KEY},
        transport=transport,
        risk_catalog=catalog,
        max_risks=1,
    )
    return _FamilyProviderRun(
        root=root,
        bundle=bundle,
        run=run,
        ledger=ledger,
        decisions=decisions,
        aggregate=aggregate,
        catalog=catalog,
        result=result,
        transport=transport,
    )


@unittest.skipUnless(
    _HAS_NEXUS and _HAS_FACTREASONER,
    "exact pinned Nexus and IBM FactReasoner extras are required",
)
class OfflineComponentIntegrationTests(unittest.TestCase):
    def test_real_adapters_complete_and_replay_without_paid_events(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        fixture = _build_family_provider_run(root)
        bundle = fixture.bundle
        run = fixture.run
        ledger = fixture.ledger
        decisions = fixture.decisions
        aggregate = fixture.aggregate
        catalog = fixture.catalog
        first = fixture.result
        transport = fixture.transport
        self.assertEqual(NEXUS_PACKAGE_VERSION, catalog.release.nexus_version)

        self.assertEqual(PINNED_PROVIDER, first.provider)
        self.assertEqual(MODEL_ID, first.to_dict()["model"])
        self.assertEqual("nexus_provider_enabled", first.risk_interface_status)
        self.assertEqual(
            "ibm_factreasoner_fr1_enabled",
            first.factreasoner_interface_status,
        )
        self.assertIsNotNone(first.provider_execution_sha256)
        self.assertTrue((run / PROVIDER_EXECUTION_MANIFEST_FILENAME).is_file())
        execution = ProviderExecutionRunEvidence.load(run)
        self.assertEqual(
            first.provider_execution_sha256,
            execution.manifest.manifest_sha256,
        )
        self.assertGreater(len(execution.manifest.executions), 0)
        verified_decisions = execution.verify()
        family_report = FamilyRiskAuthorizationReport.from_dict(
            json.loads(
                (run / "family-risk-authorizations.json").read_text()
            )
        )
        self.assertEqual(first.pipeline_result.target, family_report.target)
        self.assertEqual(1, len(family_report.family_gates))
        self.assertEqual(1, len(family_report.applicability_decisions))
        self.assertEqual(
            FamilyDecisionStatus.ACCEPTED,
            family_report.applicability_decisions[0].status,
        )
        self.assertEqual(1, len(family_report.authorizations))
        self.assertEqual(1, len(family_report.nexus_inputs))
        family_candidate_id = family_report.family_gates[0].candidate.candidate_id
        self.assertEqual(
            (family_candidate_id,),
            execution.manifest.family_applicability_candidate_ids,
        )
        self.assertGreaterEqual(len(first.quote_candidate_ids), 1)
        self.assertGreaterEqual(
            len(first.prose_decision_sha256s),
            3 * len(first.quote_candidate_ids),
        )
        self.assertEqual(
            first.eligible_text_source_ids,
            execution.manifest.eligible_text_source_ids,
        )
        self.assertEqual(
            first.quote_candidate_ids,
            execution.manifest.quote_candidate_ids,
        )
        self.assertEqual(
            first.eligible_text_source_ids,
            execution.manifest.use_risk_signal_source_ids,
        )
        metadata = [
            item.context_metadata for item in execution.manifest.executions
        ]
        empty_use_risk_execution = next(
            item
            for item in execution.manifest.executions
            if item.context_metadata.get("stage")
            == "quote_extraction_use_risk"
        )
        self.assertEqual(
            {"proposals": []},
            verified_decisions[empty_use_risk_execution.binding_sha256],
        )
        for source_id in execution.manifest.eligible_text_source_ids:
            self.assertEqual(
                1,
                sum(
                    item.get("stage") == "quote_extraction"
                    and item.get("source_id") == source_id
                    for item in metadata
                ),
            )
        for source_id in execution.manifest.use_risk_signal_source_ids:
            self.assertEqual(
                1,
                sum(
                    item.get("stage") == "quote_extraction_use_risk"
                    and item.get("source_id") == source_id
                    for item in metadata
                ),
            )
        for candidate_id in execution.manifest.quote_candidate_ids:
            for stage in ("entity_scope", "field_fit", "value_support"):
                self.assertEqual(
                    1,
                    sum(
                        item.get("stage") == stage
                        and item.get("candidate_id") == candidate_id
                        for item in metadata
                    ),
                )
        self.assertEqual(
            1,
            sum(
                item.get("stage") == "family_applicability"
                and item.get("candidate_id") == family_candidate_id
                for item in metadata
            ),
        )
        family_claim = next(
            item
            for item in first.pipeline_result.claims
            if item.candidate_id == family_candidate_id
        )
        self.assertFalse(family_claim.projection_eligible)
        self.assertFalse(family_claim.included)

        risk = json.loads((run / "risk-mapping.json").read_text())
        self.assertEqual(2, len(risk["use_contexts"]))
        context_descriptions = {
            item["description"] for item in risk["use_contexts"]
        }
        self.assertTrue(
            any(USE_STATEMENT in item for item in context_descriptions)
        )
        self.assertTrue(
            any(FAMILY_USE_STATEMENT in item for item in context_descriptions)
        )
        self.assertTrue(
            all(item["supporting_candidate_ids"] for item in risk["use_contexts"])
        )
        mapping = risk["taxonomy_mapping"]
        self.assertEqual("completed", mapping["status"])
        self.assertEqual(1, len(mapping["candidates"]))
        self.assertEqual(1, len(mapping["decisions"]))
        self.assertEqual(1, len(mapping["included_risks"]))
        included_risk = mapping["included_risks"][0]
        catalog.risk(included_risk["risk_id"])
        self.assertEqual("ai_atlas_nexus", included_risk["mapping_provenance"]["method"])
        self.assertEqual(
            MODEL_ID,
            included_risk["mapping_provenance"]["inference_model"],
        )
        self.assertEqual(1, first.pipeline_result.risk.taxonomy_candidate_count)
        self.assertEqual(1, first.pipeline_result.risk.taxonomy_included_count)

        fact = json.loads((run / "factreasoner.json").read_text())
        self.assertEqual("ibm/factreasoner-fr1", fact["checker_id"])
        informative = {
            item["outcome"]
            for item in fact["decisions"]
            if item["outcome"] in {"support", "neutral", "contradiction"}
        }
        self.assertTrue(informative)
        self.assertIn("support", informative)
        original_fact = json.loads(
            (run / "factreasoner-original.json").read_text()
        )
        self.assertIn(
            "contradiction",
            {item["outcome"] for item in original_fact["decisions"]},
        )
        repairs = json.loads((run / "repairs.json").read_text())
        architecture_repairs = [
            item
            for item in repairs["records"]
            if item["context"]["field_path"]
            == "model_details.architecture_type"
        ]
        self.assertEqual(2, len(architecture_repairs))
        self.assertEqual(
            {"withheld"}, {item["outcome"] for item in architecture_repairs}
        )
        self.assertEqual(0, repairs["semantic_submission_count"])
        self.assertNotEqual(
            repairs["original_composition_sha256"],
            repairs["post_repair_composition_sha256"],
        )
        self.assertNotIn(
            "contradiction",
            {item["outcome"] for item in fact["decisions"]},
        )
        self.assertTrue(first.pipeline_result.validation.factreasoner_passed)

        required_schemas = {
            EXTRACTION_SCHEMA_NAME,
            "model_card_entity_scope_v2",
            "model_card_field_fit_v2",
            "model_card_value_support_v2",
            "model_card_family_checkpoint_applicability_v1",
            "nexus_generic_risk_selection_v1",
            "model_card_risk_applicability_v1",
            "model_card_factreasoner_batch_v1",
        }
        self.assertTrue(required_schemas.issubset(set(transport.schema_names)))
        self.assertGreater(len(transport.post_payloads), 0)
        for payload in transport.post_payloads:
            self.assertEqual(MODEL_ID, payload["model"])
            self.assertEqual([PINNED_PROVIDER], payload["provider"]["order"])
            self.assertIs(payload["provider"]["allow_fallbacks"], False)
            self.assertIs(payload["provider"]["require_parameters"], True)

        admission = json.loads(
            (run / ORCHESTRATION_MANIFEST_FILENAME).read_text()
        )
        self.assertEqual(MODEL_ID, admission["model"])
        self.assertEqual(PINNED_PROVIDER, admission["provider"])
        self.assertEqual("nexus_provider_enabled", admission["risk_interface_status"])
        self.assertEqual(
            "ibm_factreasoner_fr1_enabled",
            admission["factreasoner_interface_status"],
        )
        result = first.pipeline_result
        artifact, _public_card = _load_exports(run, result)
        _risk_value, risk_metrics, _risk_surface = _load_risk(
            run,
            result,
            artifact,
            _load_repair_chain(run, result),
            _load_extraction(run, result),
            admission,
            family_report,
        )
        self.assertEqual(catalog.catalog_sha256, risk_metrics["catalog_sha256"])
        self.assertEqual(1, risk_metrics["applicability_accepted"])
        ledger_events = [json.loads(line) for line in ledger.read_text().splitlines()]
        attempt_bindings = [
            item["payload"]
            for item in ledger_events
            if item["event"] == "attempt_manifest"
        ]
        self.assertTrue(attempt_bindings)
        self.assertEqual({MODEL_ID}, {item["model"] for item in attempt_bindings})
        self.assertEqual(
            {PINNED_PROVIDER}, {item["provider"] for item in attempt_bindings}
        )
        state = UsageLedger(ledger).audit_state()
        self.assertEqual(len(transport.post_payloads), state["paid_calls"])

        source_state = load_source_state(bundle)
        gate_value = json.loads((run / "claim-gates.json").read_text())
        reviewed = accept_binding(
            artifact,
            artifact.bindings[0].binding_id,
            reason="reviewed_against_the_frozen_source",
        )
        closure = ReviewClosureEvidence(
            claim_gate_records=tuple(
                ClaimGateRecord.from_dict(item) for item in gate_value["records"]
            ),
            publication_catalog=source_state.hf_catalog,
            publication_factreasoner=FactReasonerRecord.from_dict(
                json.loads(
                    (run / "factreasoner-publication-original.json").read_text()
                )
            ),
            publication_validation=PublicationValidationReport.from_dict(
                json.loads((run / "publication-validation.json").read_text())
            ),
            final_factreasoner=FactReasonerRecord.from_dict(fact),
            family_authorization=family_report,
            risk_catalog=catalog,
            risk_mapping=risk,
            privacy=PrivacyScanReport.from_dict(
                json.loads((run / "privacy.json").read_text())
            ),
            provider_execution=execution,
        )
        execution_before_review = execution.state_snapshot()
        review_audit = audit_reviewed_candidate(
            reviewed,
            source_state.documents,
            closure_evidence=closure,
        )
        self.assertEqual(CLOSED_VERDICT, review_audit.verdict)
        self.assertEqual(execution_before_review, execution.state_snapshot())

        reviewed_path = root / "reviewed-artifact.json"
        cli_audit_path = root / "review-audit.json"
        save_artifact(reviewed, reviewed_path)
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            status = modelcards_main(
                [
                    "audit-review",
                    str(reviewed_path),
                    "--source-bundle",
                    str(bundle),
                    "--claim-gates",
                    str(run / "claim-gates.json"),
                    "--publication-factreasoner",
                    str(run / "factreasoner-publication-original.json"),
                    "--publication-validation",
                    str(run / "publication-validation.json"),
                    "--final-factreasoner",
                    str(run / "factreasoner.json"),
                    "--family-risk-authorizations",
                    str(run / "family-risk-authorizations.json"),
                    "--risk-mapping",
                    str(run / "risk-mapping.json"),
                    "--privacy",
                    str(run / "privacy.json"),
                    "--provider-run",
                    str(run),
                    "--output",
                    str(cli_audit_path),
                ]
            )
        self.assertEqual(0, status, stderr.getvalue())
        self.assertEqual(
            CLOSED_VERDICT,
            json.loads(cli_audit_path.read_text())["verdict"],
        )
        self.assertEqual(execution_before_review, execution.state_snapshot())

        applicability = family_report.applicability_decisions[0]
        tampered_applicability = replace(
            applicability,
            rationale=(
                "A rewritten rationale remains structurally valid but was never "
                "returned by the retained provider execution."
            ),
        )
        tampered_family_report = build_family_risk_authorization_report(
            tuple(
                ClaimGateRecord.from_dict(item)
                for item in gate_value["records"]
            ),
            (tampered_applicability,),
            target=artifact.target,
        )
        tampered_audit = audit_reviewed_candidate(
            reviewed,
            source_state.documents,
            closure_evidence=replace(
                closure,
                family_authorization=tampered_family_report,
            ),
        )
        self.assertEqual(
            "failed",
            next(
                item.status.value
                for item in tampered_audit.checks
                if item.name == "risk"
            ),
        )
        self.assertEqual(execution_before_review, execution.state_snapshot())

        ledger_before = ledger.read_bytes()
        aggregate_before = aggregate.read_bytes()
        ledger_event_count = len(ledger_before.splitlines())
        aggregate_event_count = len(aggregate_before.splitlines())
        forbidden = _OfflineOpenRouterTransport(forbid_requests=True)
        replay = run_provider_assisted_pipeline(
            bundle,
            run,
            provider=PINNED_PROVIDER,
            ledger_path=ledger,
            decision_dir=decisions,
            aggregate_budget_path=aggregate,
            environment={},
            transport=forbidden,
            risk_catalog=catalog,
            max_risks=1,
        )

        self.assertEqual([], forbidden.requests)
        self.assertEqual(first.result_sha256, replay.result_sha256)
        self.assertEqual(
            first.provider_execution_sha256,
            replay.provider_execution_sha256,
        )
        self.assertEqual(
            first.pipeline_result.result_sha256,
            replay.pipeline_result.result_sha256,
        )
        self.assertEqual(ledger_before, ledger.read_bytes())
        self.assertEqual(aggregate_before, aggregate.read_bytes())
        self.assertEqual(ledger_event_count, len(ledger.read_bytes().splitlines()))
        self.assertEqual(
            aggregate_event_count,
            len(aggregate.read_bytes().splitlines()),
        )


if __name__ == "__main__":
    unittest.main()
