from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from jsonschema import ValidationError

from model_cards.bindings import quote_binding
from model_cards.claim_gate import ClaimCandidate, DecisionStatus, GateName
from model_cards.extraction import ExtractionBatch
from model_cards.factreasoner import (
    ATOM_VERSION,
    CheckRequest,
    CheckStage,
    FactAtom,
    ReferentHypothesis,
    build_source_chunks,
    check_request_sha256,
    retrieve_chunks,
)
from model_cards.models import RelationToTarget, SourceDocument, SourceRole, TargetIdentity
from model_cards.provider import (
    MODEL_ID,
    ProviderResponseError,
    StructuredCallSpec,
    structured_json_call,
)
from model_cards.provider_adapters import (
    MAX_CLAIM_OUTPUT_TOKENS,
    MAX_EXTRACTION_OUTPUT_TOKENS,
    MAX_FACT_OUTPUT_TOKENS,
    OpenRouterApplicabilityChecker,
    OpenRouterClaimChecker,
    OpenRouterFactChecker,
    OpenRouterQuoteExtractor,
    ProviderAdapterError,
    _AggregatePaidCallBudget,
    _Runtime,
    build_nexus_openrouter_inference_engine,
    summarize_aggregate_budget,
)
from model_cards.provider_execution import ProviderExecutionCollector
from model_cards.quality_report import QualityReportError, _provider_metrics
from model_cards.run_ledger import AttemptBinding, BudgetCapError, UsageLedger
from model_cards.risk_mapping import (
    INFERENCE_MODEL,
    NEXUS_PACKAGE_VERSION,
    RiskCandidate,
    TaxonomyRelease,
    TaxonomyRisk,
    UseContext,
)
from model_cards.schema import CONTRACT_SCHEMA


TARGET = TargetIdentity("example-lab/exact-model", "a" * 40)


class FakeCalls:
    def __init__(self, *decisions):
        self.decisions = list(decisions)
        self.specs = []
        self.kwargs = []

    def __call__(self, spec, **kwargs):
        self.specs.append(spec)
        self.kwargs.append(kwargs)
        if not self.decisions:
            raise AssertionError("unexpected provider call")
        decision = self.decisions.pop(0)
        kwargs["validator"](decision)
        return SimpleNamespace(
            decision=decision,
            receipt=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
            resumed=False,
        )


class IgnoringValidatorCall(FakeCalls):
    def __call__(self, spec, **kwargs):
        self.specs.append(spec)
        self.kwargs.append(kwargs)
        if not self.decisions:
            raise AssertionError("unexpected provider call")
        return SimpleNamespace(
            decision=self.decisions.pop(0),
            receipt=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
            resumed=False,
        )


def source(text: str | None = None) -> SourceDocument:
    return SourceDocument(
        source_id="src_" + "b" * 24,
        source_uri=f"https://huggingface.co/{TARGET.model_id}/blob/{TARGET.revision}/README.md",
        role=SourceRole.HUGGING_FACE_SNAPSHOT,
        source_revision=TARGET.revision,
        target=TARGET,
        text=text or "# Summary\nThe exact model is intended for research summarization.",
    )


def candidate() -> ClaimCandidate:
    document = source()
    binding = quote_binding(
        target=TARGET,
        source=document,
        field_path="identity.summary",
        value="The exact model is intended for research summarization.",
        quote="The exact model is intended for research summarization.",
        claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
        relation=RelationToTarget.EXACT_TARGET,
    )
    return ClaimCandidate.from_binding(TARGET, binding)


class ProviderAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.ledger = self.root / "usage.jsonl"
        self.decisions = self.root / "decisions"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def kwargs(self, fake):
        return {
            "provider": "Together",
            "ledger_path": self.ledger,
            "decision_dir": self.decisions,
            "environment": {"OPENROUTER_API_KEY": "not-read-by-fixture"},
            "call": fake,
        }

    def test_quote_extractor_uses_exact_model_strict_schema_and_returns_batch(self) -> None:
        value = {
            "proposals": [
                {
                    "source_id": "src_" + "b" * 24,
                    "field_path": "identity.summary",
                    "value_json": json.dumps(
                        "The exact model is intended for research summarization."
                    ),
                    "quote": "The exact model is intended for research summarization.",
                    "claim_entity": f"{TARGET.model_id}@{TARGET.revision}",
                    "relation": "exact_target",
                    "origin": "source_stated",
                }
            ]
        }
        fake = FakeCalls(value)
        batch = OpenRouterQuoteExtractor(**self.kwargs(fake)).extract_source(
            source(), target=TARGET, source_catalog_sha256="c" * 64
        )
        self.assertEqual(MODEL_ID, batch.inference_model)
        self.assertEqual("Together", batch.provider)
        self.assertEqual(1, len(batch.proposals))
        spec = fake.specs[0]
        payload = json.loads(spec.user_prompt)
        self.assertEqual(MODEL_ID, MODEL_ID)
        self.assertEqual(0, payload["windows"][0]["normalized_start"])
        self.assertFalse(spec.json_schema["additionalProperties"])
        self.assertNotIn(
            "benchmark_scope_json",
            spec.json_schema["properties"]["proposals"]["items"]["properties"],
        )
        self.assertEqual(MAX_EXTRACTION_OUTPUT_TOKENS, spec.max_output_tokens)
        self.assertIn(
            "model_details.num_parameters",
            payload["field_value_contract"]["field_value_schemas"],
        )
        self.assertLess(
            len(payload["field_value_contract"]["$defs"]),
            len(CONTRACT_SCHEMA["$defs"]),
        )
        self.assertEqual(
            {"type": "string", "minLength": 1},
            payload["field_value_contract"]["field_value_schemas"][
                "use_and_risk.limitations"
            ],
        )
        publisher_risk_schema = payload["field_value_contract"][
            "field_value_schemas"
        ]["use_and_risk.identified_risks"]
        self.assertEqual(
            ["name", "description", "applicability_rationale"],
            publisher_risk_schema["required"],
        )
        self.assertFalse(publisher_risk_schema["additionalProperties"])
        self.assertNotIn("risk_id", publisher_risk_schema["properties"])
        self.assertEqual(
            "use_and_risk.identified_risks",
            payload["field_value_contract"]["publisher_risk_item_field"],
        )
        self.assertEqual(
            "source_stated",
            payload["rules"]["publisher_reported_risk"]["origin"],
        )
        self.assertIn(
            "7B",
            payload["rules"]["text_values_preserve_units_and_qualifiers"],
        )
        selection_rule = payload["rules"]["proposal_selection"]
        self.assertIn("highest-value", selection_rule)
        self.assertIn("reserve at least one proposal slot", selection_rule)
        self.assertIn("Never invent", selection_rule)
        self.assertIn("category-reservation rule", spec.system_prompt)
        self.assertEqual("quote_extraction", spec.context_metadata["stage"])
        self.assertNotIn("excerpt", spec.context_metadata)

    def test_quote_extractor_runs_dedicated_use_risk_pass_even_with_core_context(self) -> None:
        intended = "The model is intended for research summarization."
        limitation = "The model may produce inaccurate summaries."
        main = {
            "proposals": [
                {
                    "source_id": "src_" + "b" * 24,
                    "field_path": "use_and_risk.intended_uses[0]",
                    "value_json": json.dumps(intended),
                    "quote": intended,
                    "claim_entity": f"{TARGET.model_id}@{TARGET.revision}",
                    "relation": "exact_target",
                    "origin": "source_stated",
                }
            ]
        }
        recovery = {
            "proposals": [
                {
                    "source_id": "src_" + "b" * 24,
                    "field_path": "use_and_risk.limitations[0]",
                    # Reproduces the provider shape that previously failed the
                    # nested JSON parse despite being safe quoted prose.
                    "value_json": limitation,
                    "quote": limitation,
                    "claim_entity": f"{TARGET.model_id}@{TARGET.revision}",
                    "relation": "exact_target",
                    "origin": "source_stated",
                }
            ]
        }
        fake = FakeCalls(main, recovery)
        batch = OpenRouterQuoteExtractor(**self.kwargs(fake)).extract_source(
            source(
                f"# Intended Uses\n{intended}\n\n"
                f"# Limitations and Risks\n{limitation}"
            ),
            target=TARGET,
            source_catalog_sha256="c" * 64,
        )
        self.assertEqual(2, len(batch.proposals))
        recovered = next(
            item
            for item in batch.proposals
            if item.field_path == "use_and_risk.limitations[0]"
        )
        self.assertEqual(limitation, recovered.value)
        self.assertEqual(
            ["quote_extraction", "quote_extraction_use_risk"],
            [item.context_metadata["stage"] for item in fake.specs],
        )
        risk_schema = fake.specs[1].json_schema
        field_pattern = risk_schema["properties"]["proposals"]["items"][
            "properties"
        ]["field_path"]["pattern"]
        self.assertIn("use_and_risk", field_pattern)
        self.assertNotIn("identity", field_pattern)

    def test_quote_extractor_withholds_invented_source_and_rejects_wrong_target(self) -> None:
        fake = FakeCalls(
            {
                "proposals": [
                    {
                        "source_id": "src_" + "d" * 24,
                        "field_path": "identity.summary",
                        "value_json": '"x"',
                        "quote": "x",
                        "claim_entity": f"{TARGET.model_id}@{TARGET.revision}",
                        "relation": "exact_target",
                        "origin": "source_stated",
                    }
                ]
            }
        )
        batch = OpenRouterQuoteExtractor(**self.kwargs(fake)).extract_source(
            source(), target=TARGET, source_catalog_sha256="c" * 64
        )
        self.assertEqual((), batch.proposals)
        self.assertEqual(1, len(batch.rejections))
        self.assertEqual("source_identifier_mismatch", batch.rejections[0].reason)
        other = TargetIdentity("example-lab/other", "d" * 40)
        with self.assertRaisesRegex(ProviderAdapterError, "exact-target"):
            OpenRouterQuoteExtractor(**self.kwargs(FakeCalls())).extract_source(
                source(), target=other, source_catalog_sha256="c" * 64
            )

    def test_quote_extractor_revalidates_an_injected_call_result(self) -> None:
        decision = {
            "proposals": [
                {
                    "source_id": "src_" + "b" * 24,
                    "field_path": "identity.summary",
                    "value_json": '"summary"',
                    "quote": "q" * 801,
                    "claim_entity": f"{TARGET.model_id}@{TARGET.revision}",
                    "relation": "exact_target",
                    "origin": "source_stated",
                }
            ]
        }
        with self.assertRaises(ValidationError):
            OpenRouterQuoteExtractor(
                **self.kwargs(IgnoringValidatorCall(decision))
            ).extract_source(
                source(), target=TARGET, source_catalog_sha256="c" * 64
            )

    def test_quote_extractor_records_each_invalid_item_without_poisoning_peers(self) -> None:
        valid = {
            "source_id": "src_" + "b" * 24,
            "field_path": "identity.summary",
            "value_json": json.dumps(
                "The exact model is intended for research summarization."
            ),
            "quote": "The exact model is intended for research summarization.",
            "claim_entity": f"{TARGET.model_id}@{TARGET.revision}",
            "relation": "exact_target",
            "origin": "source_stated",
        }
        invalid_value = {
            **valid,
            "field_path": "model_details.num_parameters",
            "value_json": "7",
            "quote": "PRIVATE INVALID PROPOSAL SENTINEL",
        }
        wrong_source = {**valid, "source_id": "src_" + "d" * 24}
        decision = {
            "proposals": [valid, invalid_value, wrong_source, dict(valid)]
        }
        batch = OpenRouterQuoteExtractor(
            **self.kwargs(FakeCalls(decision))
        ).extract_source(
            source(), target=TARGET, source_catalog_sha256="c" * 64
        )
        self.assertEqual(1, len(batch.proposals))
        self.assertEqual([1, 2, 3], [item.proposal_index for item in batch.rejections])
        self.assertEqual(
            [
                "proposal_contract_invalid",
                "source_identifier_mismatch",
                "duplicate_proposal",
            ],
            [item.reason for item in batch.rejections],
        )
        self.assertEqual(
            [
                hashlib.sha256(
                    json.dumps(
                        item,
                        allow_nan=False,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest()
                for item in (invalid_value, wrong_source, dict(valid))
            ],
            [item.proposal_sha256 for item in batch.rejections],
        )
        serialized = json.dumps(batch.to_dict(), sort_keys=True)
        self.assertNotIn("PRIVATE INVALID PROPOSAL SENTINEL", serialized)
        self.assertEqual(batch, ExtractionBatch.from_dict(batch.to_dict()))

    def test_quote_extractor_replays_server_string_bounds_locally(self) -> None:
        base = {
            "source_id": "src_" + "b" * 24,
            "field_path": "identity.summary",
            "value_json": '"summary"',
            "quote": "summary",
            "claim_entity": f"{TARGET.model_id}@{TARGET.revision}",
            "relation": "exact_target",
            "origin": "source_stated",
        }
        for field, value in (
            ("source_id", "s" * 129),
            ("field_path", "a." + "b" * 159),
            ("value_json", '"' + "v" * 1_600 + '"'),
            ("quote", "q" * 801),
            ("claim_entity", "e" * 257),
            ("origin", "source_stated" * 20),
        ):
            proposal = dict(base)
            proposal[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                OpenRouterQuoteExtractor(
                    **self.kwargs(FakeCalls({"proposals": [proposal]}))
                ).extract_source(
                    source(), target=TARGET, source_catalog_sha256="c" * 64
                )

    def test_claim_checker_runs_independent_closed_decisions(self) -> None:
        fake = FakeCalls(
            {"status": "accepted", "reason": "semantic_entity_scope"},
            {"status": "accepted", "reason": "semantic_field_fit"},
            {"status": "accepted", "reason": "semantic_value_support"},
        )
        checker = OpenRouterClaimChecker(**self.kwargs(fake))
        item = candidate()
        entity = checker.decide(item, GateName.ENTITY_SCOPE)
        field = checker.decide(item, GateName.FIELD_FIT)
        value = checker.decide(item, GateName.VALUE_SUPPORT)
        self.assertEqual(GateName.ENTITY_SCOPE, entity.gate)
        self.assertEqual(GateName.FIELD_FIT, field.gate)
        self.assertEqual(GateName.VALUE_SUPPORT, value.gate)
        self.assertNotEqual(entity.request_sha256, field.request_sha256)
        self.assertNotEqual(field.request_sha256, value.request_sha256)
        self.assertEqual(3, len(fake.specs))
        for spec in fake.specs:
            payload = json.loads(spec.user_prompt)
            self.assertEqual(MAX_CLAIM_OUTPUT_TOKENS, spec.max_output_tokens)
            self.assertEqual(item.candidate_id, payload["candidate_id"])
            self.assertEqual(item.value, payload["value"])
            self.assertNotIn("corrected_value", spec.json_schema["properties"])
        entity_payload = json.loads(fake.specs[0].user_prompt)
        self.assertIn("containing document", entity_payload["task"])
        self.assertIn("sibling checkpoint", entity_payload["task"])
        self.assertEqual(
            item.target.to_dict(), entity_payload["evidence"][0]["source_target"]
        )

    def test_claim_checker_can_withhold_same_document_sibling_attribution(self) -> None:
        document = source(
            "# Exact Model\n\n## Sibling Checkpoint\n\n"
            "example-lab/sibling-model has 13B parameters."
        )
        binding = quote_binding(
            target=TARGET,
            source=document,
            field_path="identity.summary",
            value="example-lab/sibling-model has 13B parameters.",
            quote="example-lab/sibling-model has 13B parameters.",
            claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            section_path=("Exact Model", "Sibling Checkpoint"),
        )
        item = ClaimCandidate.from_binding(TARGET, binding)
        fake = FakeCalls({"status": "withheld", "reason": "wrong_entity"})

        decision = OpenRouterClaimChecker(**self.kwargs(fake)).decide(
            item, GateName.ENTITY_SCOPE
        )

        self.assertEqual(DecisionStatus.WITHHELD, decision.status)
        self.assertEqual("wrong_entity", decision.reason)
        payload = json.loads(fake.specs[0].user_prompt)
        self.assertEqual(
            ["Exact Model", "Sibling Checkpoint"],
            payload["evidence"][0]["section_path"],
        )

    def test_claim_checker_rejects_mismatched_status_reason(self) -> None:
        fake = FakeCalls({"status": "accepted", "reason": "wrong_field"})
        checker = OpenRouterClaimChecker(**self.kwargs(fake))
        with self.assertRaisesRegex(ProviderAdapterError, "status/reason"):
            checker.decide(candidate(), GateName.FIELD_FIT)

    def test_fact_checker_cites_only_supplied_frozen_chunks(self) -> None:
        document = source(
            "# Summary\nThe exact model is intended for research summarization."
        )
        atom = FactAtom(
            atom_version=ATOM_VERSION,
            target=TARGET,
            field_path="identity.summary",
            value_path="identity.summary",
            ordinal=0,
            statement="The exact model is intended for research summarization.",
            hypothesis=ReferentHypothesis(
                f"{TARGET.model_id}@{TARGET.revision}",
                RelationToTarget.EXACT_TARGET,
            ),
            field_value_sha256="e" * 64,
        )
        chunks = build_source_chunks((document,)).chunks
        contexts = retrieve_chunks(atom, chunks)
        request = CheckRequest(
            atom=atom,
            stage=CheckStage.RETRIEVAL,
            contexts=contexts,
            fallback_complete=True,
        )
        chunk_id = contexts[0].chunk.chunk_id
        fake = FakeCalls(
            {
                "decisions": [
                    {
                        "request_sha256": check_request_sha256(request),
                        "outcome": "support",
                        "cited_chunk_ids": [chunk_id],
                    }
                ]
            }
        )
        response = OpenRouterFactChecker(**self.kwargs(fake)).check(request)
        self.assertEqual("support", response.outcome.value)
        self.assertEqual((chunk_id,), response.cited_chunk_ids)
        payload = json.loads(fake.specs[0].user_prompt)
        self.assertEqual(MAX_FACT_OUTPUT_TOKENS, fake.specs[0].max_output_tokens)
        self.assertEqual(request.hypothesis, payload["checks"][0]["hypothesis"])
        self.assertEqual({chunk_id}, {item["chunk_id"] for item in payload["contexts"]})
        self.assertEqual("factreasoner_batch", fake.specs[0].context_metadata["stage"])

        bad = FakeCalls(
            {
                "decisions": [
                    {
                        "request_sha256": check_request_sha256(request),
                        "outcome": "support",
                        "cited_chunk_ids": ["chunk-invented"],
                    }
                ]
            }
        )
        with self.assertRaises(ProviderAdapterError):
            OpenRouterFactChecker(**self.kwargs(bad)).check(request)

        class InvalidThenValid(FakeCalls):
            def __call__(self, spec, **kwargs):
                self.specs.append(spec)
                self.kwargs.append(kwargs)
                if len(self.specs) == 1:
                    raise ProviderResponseError(
                        "synthetic invalid structured decision",
                        reason_code="structured_decision_invalid",
                    )
                decision = self.decisions.pop(0)
                kwargs["validator"](decision)
                return SimpleNamespace(
                    decision=decision,
                    receipt=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
                    resumed=False,
                )

        retried = InvalidThenValid(
            {
                "decisions": [
                    {
                        "request_sha256": check_request_sha256(request),
                        "outcome": "neutral",
                        "cited_chunk_ids": [chunk_id],
                    }
                ]
            }
        )
        retried_response = OpenRouterFactChecker(**self.kwargs(retried)).check(request)
        self.assertEqual("neutral", retried_response.outcome.value)
        self.assertEqual("no_complete_support", retried_response.reason_code)
        self.assertEqual(2, len(retried.specs))
        self.assertTrue(retried.specs[0].attempt_id.endswith(".attempt1"))
        self.assertTrue(retried.specs[1].attempt_id.endswith(".attempt2"))
        self.assertEqual(
            retried.specs[0].logical_call_id,
            retried.specs[1].logical_call_id,
        )

    def test_fact_checker_batches_and_exact_request_cache_avoid_repeat_calls(self) -> None:
        document = source("# Summary\nThe exact model emits grounded summaries.")
        chunks = build_source_chunks((document,)).chunks
        requests = []
        for ordinal, statement in enumerate(
            ("The exact model emits summaries.", "The exact model is grounded.")
        ):
            atom = FactAtom(
                atom_version=ATOM_VERSION,
                target=TARGET,
                field_path="identity.summary",
                value_path=f"identity.summary[{ordinal}]",
                ordinal=ordinal,
                statement=statement,
                hypothesis=ReferentHypothesis(
                    f"{TARGET.model_id}@{TARGET.revision}",
                    RelationToTarget.EXACT_TARGET,
                ),
                field_value_sha256="e" * 64,
            )
            contexts = retrieve_chunks(atom, chunks)
            requests.append(
                CheckRequest(
                    atom=atom,
                    stage=CheckStage.RETRIEVAL,
                    contexts=contexts,
                    fallback_complete=True,
                )
            )
        decisions = {
            "decisions": [
                {
                    "request_sha256": check_request_sha256(request),
                    "outcome": "support",
                    "cited_chunk_ids": [request.contexts[0].chunk.chunk_id],
                }
                for request in requests
            ]
        }
        fake = FakeCalls(decisions)
        checker = OpenRouterFactChecker(**self.kwargs(fake))

        first = checker.check_many(tuple(requests))
        replayed = tuple(checker.check(item) for item in requests)

        self.assertEqual(first, replayed)
        self.assertEqual(1, len(fake.specs))
        self.assertEqual(2, fake.specs[0].context_metadata["request_count"])
        with self.assertRaisesRegex(ProviderAdapterError, "between 1 and 64"):
            checker.check_many(tuple(requests[0] for _ in range(65)))

    def test_shared_aggregate_budget_caps_fresh_calls_but_allows_replay(self) -> None:
        from tests.test_provider import (
            FixtureTransport,
            SCHEMA,
            route_payload,
            success_payload,
            validator,
        )

        aggregate = self.root / "aggregate-budget.jsonl"

        def spec(name: str) -> StructuredCallSpec:
            return StructuredCallSpec(
                logical_call_id=f"aggregate.{name}",
                attempt_id=f"aggregate.{name}.attempt1",
                provider="Together",
                schema_name=f"aggregate_{name}",
                json_schema=SCHEMA,
                system_prompt="Return one fixture value.",
                user_prompt="Return the normalized fixture value.",
                max_output_tokens=32,
                context_metadata={"stage": "fixture"},
            )

        first_transport = FixtureTransport(
            [(200, success_payload(provider="Together"))],
            routes=[route_payload(provider="Together")],
        )
        first_runtime = _Runtime.build(
            provider="Together",
            ledger_path=self.root / "target-1" / "usage.jsonl",
            decision_dir=self.root / "target-1" / "decisions",
            aggregate_budget_path=aggregate,
            environment={"OPENROUTER_API_KEY": "fixture-key"},
            transport=first_transport,
            call=structured_json_call,
        )
        initial = first_runtime.invoke(
            spec("first"),
            decision_name="aggregate-first.json",
            validator=validator,
        )
        self.assertFalse(initial.resumed)
        journal_before = aggregate.read_bytes()

        blocked_transport = FixtureTransport(
            [(200, success_payload(provider="Together"))],
            routes=[route_payload(provider="Together")],
        )
        with mock.patch("model_cards.provider_adapters.GLOBAL_PAID_CALL_CAP", 1):
            with self.assertRaisesRegex(BudgetCapError, "paid-call cap"):
                _Runtime.build(
                    provider="Together",
                    ledger_path=self.root / "target-2" / "usage.jsonl",
                    decision_dir=self.root / "target-2" / "decisions",
                    aggregate_budget_path=aggregate,
                    environment={"OPENROUTER_API_KEY": "fixture-key"},
                    transport=blocked_transport,
                    call=structured_json_call,
                ).invoke(
                    spec("second"),
                    decision_name="aggregate-second.json",
                    validator=validator,
                )

            forbidden = FixtureTransport([])
            replay = _Runtime.build(
                provider="Together",
                ledger_path=self.root / "target-1" / "usage.jsonl",
                decision_dir=self.root / "target-1" / "decisions",
                aggregate_budget_path=aggregate,
                environment={},
                transport=forbidden,
                call=structured_json_call,
            ).invoke(
                spec("first"),
                decision_name="aggregate-first.json",
                validator=validator,
            )

        self.assertTrue(replay.resumed)
        self.assertEqual(0, blocked_transport.paid_count)
        self.assertEqual([], forbidden.requests)
        self.assertEqual(journal_before, aggregate.read_bytes())
        summary = summarize_aggregate_budget(aggregate)
        self.assertEqual(1, summary["paid_calls"])
        self.assertEqual("0", summary["reserved_usd_capacity"])
        self.assertNotIn(str(self.root), aggregate.read_text())

    def test_shared_aggregate_budget_enforces_usd_cap_before_paid_send(self) -> None:
        from tests.test_provider import (
            FixtureTransport,
            SCHEMA,
            route_payload,
            success_payload,
            validator,
        )

        aggregate = self.root / "aggregate-usd-budget.jsonl"

        def invoke(name: str, transport: FixtureTransport):
            call_spec = StructuredCallSpec(
                logical_call_id=f"aggregate.usd.{name}",
                attempt_id=f"aggregate.usd.{name}.attempt1",
                provider="Together",
                schema_name=f"aggregate_usd_{name}",
                json_schema=SCHEMA,
                system_prompt="Return one fixture value.",
                user_prompt="Return the normalized fixture value.",
                max_output_tokens=32,
                context_metadata={"stage": "fixture"},
            )
            return _Runtime.build(
                provider="Together",
                ledger_path=self.root / name / "usage.jsonl",
                decision_dir=self.root / name / "decisions",
                aggregate_budget_path=aggregate,
                environment={"OPENROUTER_API_KEY": "fixture-key"},
                transport=transport,
                call=structured_json_call,
            ).invoke(
                call_spec,
                decision_name=f"aggregate-usd-{name}.json",
                validator=validator,
            )

        first_transport = FixtureTransport(
            [(200, success_payload(provider="Together", cost="0.001"))],
            routes=[route_payload(provider="Together")],
        )
        invoke("first-usd", first_transport)
        first_summary = summarize_aggregate_budget(aggregate)
        first_commitment = Decimal(first_summary["total_usd_commitment"])
        self.assertGreater(first_commitment, Decimal("0"))
        journal_before = aggregate.read_bytes()

        blocked_transport = FixtureTransport(
            [(200, success_payload(provider="Together", cost="0.001"))],
            routes=[route_payload(provider="Together")],
        )
        with mock.patch(
            "model_cards.provider_adapters.GLOBAL_USD_CAP",
            first_commitment * Decimal("1.5"),
        ):
            with self.assertRaisesRegex(BudgetCapError, "USD cap"):
                invoke("second-usd", blocked_transport)

        self.assertEqual(0, blocked_transport.paid_count)
        self.assertEqual(journal_before, aggregate.read_bytes())

    def test_existing_ledger_with_another_provider_is_rejected(self) -> None:
        UsageLedger(self.ledger).begin_attempt(
            AttemptBinding(
                logical_call_id="foreign.fixture",
                attempt_id="foreign.fixture.attempt1",
                model=MODEL_ID,
                provider="OtherProvider",
                request_sha256="1" * 64,
                schema_sha256="2" * 64,
                sidecar_path_sha256="3" * 64,
                context_metadata={"stage": "fixture"},
            )
        )

        with self.assertRaisesRegex(ProviderAdapterError, "unpinned provider"):
            _Runtime.build(
                provider="Together",
                ledger_path=self.ledger,
                decision_dir=self.decisions,
                environment={},
                transport=None,
                call=structured_json_call,
            )
        self.assertFalse(self.decisions.exists())

    def test_quality_metrics_reject_another_provider_identity(self) -> None:
        UsageLedger(self.ledger).begin_attempt(
            AttemptBinding(
                logical_call_id="foreign.fixture",
                attempt_id="foreign.fixture.attempt1",
                model=MODEL_ID,
                provider="OtherProvider",
                request_sha256="1" * 64,
                schema_sha256="2" * 64,
                sidecar_path_sha256="3" * 64,
                context_metadata={"stage": "fixture"},
            )
        )

        with self.assertRaisesRegex(QualityReportError, "provider summary"):
            _provider_metrics(self.ledger)

    def test_semantic_retry_replays_attempt_two_from_its_own_sidecar(self) -> None:
        from tests.test_provider import FixtureTransport, route_payload, success_payload

        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "additionalProperties": False,
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        }

        def validate(value):
            if not isinstance(value, dict) or set(value) != {"value"}:
                raise ValueError("decision shape is invalid")
            if not isinstance(value["value"], str):
                raise ValueError("decision value is invalid")

        spec = StructuredCallSpec(
            logical_call_id="semantic.retry.fixture",
            attempt_id="semantic.retry.fixture.attempt1",
            provider="Together",
            schema_name="semantic_retry_fixture",
            json_schema=schema,
            system_prompt="Return one fixture value.",
            user_prompt="Return the normalized fixture value.",
            max_output_tokens=32,
            context_metadata={"stage": "fixture"},
        )
        transport = FixtureTransport(
            [
                (
                    200,
                    success_payload(
                        decision={"wrong": "shape"}, provider="Together"
                    ),
                ),
                (
                    200,
                    success_payload(
                        decision={"value": "normalized"}, provider="Together"
                    ),
                ),
            ],
            routes=[
                route_payload(provider="Together"),
                route_payload(provider="Together"),
            ],
        )
        collector = ProviderExecutionCollector()
        runtime = _Runtime.build(
            provider="Together",
            ledger_path=self.ledger,
            decision_dir=self.decisions,
            aggregate_budget_path=self.root / "aggregate-budget.jsonl",
            environment={"OPENROUTER_API_KEY": "fixture-key"},
            transport=transport,
            call=structured_json_call,
            execution_collector=collector,
        )

        initial = runtime.invoke(
            spec,
            decision_name="semantic-retry.json",
            validator=validate,
            semantic_retries=1,
        )

        self.assertFalse(initial.resumed)
        self.assertEqual({"value": "normalized"}, initial.decision)
        self.assertFalse((self.decisions / "semantic-retry.attempt1.json").exists())
        self.assertTrue((self.decisions / "semantic-retry.attempt2.json").is_file())
        self.assertEqual(2, transport.paid_count)
        self.assertEqual(1, len(collector.bindings))
        self.assertEqual(
            "semantic.retry.fixture.attempt2", collector.bindings[0].attempt_id
        )
        aggregate_before_replay = (self.root / "aggregate-budget.jsonl").read_bytes()

        forbidden = FixtureTransport([])
        replay = _Runtime.build(
            provider="Together",
            ledger_path=self.ledger,
            decision_dir=self.decisions,
            aggregate_budget_path=self.root / "aggregate-budget.jsonl",
            environment={},
            transport=forbidden,
            call=structured_json_call,
            execution_collector=collector,
        ).invoke(
            spec,
            decision_name="semantic-retry.json",
            validator=validate,
            semantic_retries=1,
        )

        self.assertTrue(replay.resumed)
        self.assertEqual(initial.decision, replay.decision)
        self.assertEqual([], forbidden.requests)
        self.assertEqual(1, len(collector.bindings))
        self.assertEqual(initial.execution, replay.execution)
        self.assertEqual(2, UsageLedger(self.ledger).audit_state()["paid_calls"])
        self.assertEqual(
            aggregate_before_replay,
            (self.root / "aggregate-budget.jsonl").read_bytes(),
        )

    def test_collector_rejects_result_without_typed_execution_binding(self) -> None:
        from tests.test_provider import SCHEMA, validator

        spec = StructuredCallSpec(
            logical_call_id="collector.missing.binding",
            attempt_id="collector.missing.binding.attempt1",
            provider="Together",
            schema_name="collector_missing_binding",
            json_schema=SCHEMA,
            system_prompt="Return one fixture value.",
            user_prompt="Return the normalized fixture value.",
            max_output_tokens=32,
            context_metadata={"stage": "fixture"},
        )
        runtime = _Runtime.build(
            provider="Together",
            ledger_path=self.ledger,
            decision_dir=self.decisions,
            environment={},
            transport=None,
            call=FakeCalls({"value": "normalized"}),
            execution_collector=ProviderExecutionCollector(),
        )

        with self.assertRaisesRegex(
            ProviderAdapterError, "no typed execution binding"
        ):
            runtime.invoke(
                spec,
                decision_name="collector-missing-binding.json",
                validator=validator,
            )

    def test_collector_rejects_decision_changed_after_settled_call(self) -> None:
        from tests.test_provider import (
            FixtureTransport,
            SCHEMA,
            route_payload,
            success_payload,
            validator,
        )

        spec = StructuredCallSpec(
            logical_call_id="collector.changed.decision",
            attempt_id="collector.changed.decision.attempt1",
            provider="Together",
            schema_name="collector_changed_decision",
            json_schema=SCHEMA,
            system_prompt="Return one fixture value.",
            user_prompt="Return the normalized fixture value.",
            max_output_tokens=32,
            context_metadata={"stage": "fixture"},
        )

        def changed_call(call_spec, **kwargs):
            settled = structured_json_call(call_spec, **kwargs)
            return replace(settled, decision={"value": "changed after settlement"})

        collector = ProviderExecutionCollector()
        runtime = _Runtime.build(
            provider="Together",
            ledger_path=self.ledger,
            decision_dir=self.decisions,
            environment={"OPENROUTER_API_KEY": "fixture-key"},
            transport=FixtureTransport(
                [(200, success_payload(provider="Together"))],
                routes=[route_payload(provider="Together")],
            ),
            call=changed_call,
            execution_collector=collector,
        )

        with self.assertRaisesRegex(
            ProviderAdapterError, "differs from its settled execution"
        ):
            runtime.invoke(
                spec,
                decision_name="collector-changed-decision.json",
                validator=validator,
            )
        self.assertEqual((), collector.bindings)

    def test_risk_applicability_keeps_taxonomy_inference_distinct(self) -> None:
        use_context = UseContext(
            context_id="context:research_summary",
            description="The publisher intends the model for research summarization workflows.",
            supporting_fields=("use_and_risk.intended_uses[0]",),
            supporting_candidate_ids=("claim-" + "1" * 24,),
            source_refs=("src_" + "b" * 24,),
        )
        risk = TaxonomyRisk(
            risk_id="atlas-inaccurate-output",
            name="Inaccurate output",
            description="Generated summaries may contain inaccurate information.",
            source_url="https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas",
        )

        class Detector:
            detector_version = NEXUS_PACKAGE_VERSION
            inference_model = INFERENCE_MODEL
            inference_config_sha256 = "2" * 64

        risk_candidate = RiskCandidate.build(
            risk, (use_context,), Detector(), TaxonomyRelease()
        )
        rationale = (
            "The grounded research summarization context makes inaccurate generated "
            "summaries a specifically applicable candidate risk."
        )
        fake = FakeCalls(
            {
                "status": "accepted",
                "reason": "specific_use_context_supported",
                "rationale": rationale,
            }
        )
        decision = OpenRouterApplicabilityChecker(**self.kwargs(fake)).assess(
            risk_candidate, (use_context,)
        )
        self.assertEqual("accepted", decision.status.value)
        public = risk_candidate.public_value(decision, risk)
        self.assertEqual("taxonomy_identified", public["identification_origin"])
        self.assertEqual("generated_unreviewed", public["review_status"])
        self.assertNotIn("publisher_reported", json.dumps(public))

    def test_nexus_engine_wraps_taxonomy_array_schema_without_hidden_client(self) -> None:
        fake = FakeCalls({"prediction": ["Inaccurate output"]})
        try:
            engine = build_nexus_openrouter_inference_engine(**self.kwargs(fake))
        except ProviderAdapterError as exc:
            if "unavailable" in str(exc):
                self.skipTest("optional ai-atlas-nexus extra is not installed")
            raise
        schema = {
            "type": "array",
            "items": {"type": "string", "enum": ["Inaccurate output"]},
            "uniqueItems": True,
        }
        outputs = engine.generate(
            ["Choose specifically applicable risks."],
            response_format=schema,
            postprocessors=["list_of_str"],
        )
        self.assertEqual(["Inaccurate output"], outputs[0].prediction)
        self.assertEqual(MODEL_ID, engine.model_name_or_path)
        self.assertIs(engine.backend, engine)
        self.assertEqual("nexus_risk_selection", fake.specs[0].context_metadata["stage"])

    def test_runtime_requires_explicit_provider_and_safe_private_paths(self) -> None:
        with self.assertRaisesRegex(ProviderAdapterError, "provider"):
            OpenRouterClaimChecker(
                provider="",
                ledger_path=self.ledger,
                decision_dir=self.decisions,
            )
        with self.assertRaisesRegex(ProviderAdapterError, "pinned"):
            OpenRouterClaimChecker(
                provider="Baidu",
                ledger_path=self.ledger,
                decision_dir=self.decisions,
            )
        symlink = self.root / "linked"
        real = self.root / "real"
        real.mkdir()
        symlink.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ProviderAdapterError, "symlink"):
            OpenRouterClaimChecker(
                provider="Together",
                ledger_path=self.ledger,
                decision_dir=symlink,
            )


if __name__ == "__main__":
    unittest.main()
