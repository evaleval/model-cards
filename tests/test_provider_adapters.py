from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from model_cards.bindings import quote_binding
from model_cards.claim_gate import ClaimCandidate, GateName
from model_cards.factreasoner import (
    ATOM_VERSION,
    CheckRequest,
    CheckStage,
    FactAtom,
    ReferentHypothesis,
    build_source_chunks,
    retrieve_chunks,
)
from model_cards.models import RelationToTarget, SourceDocument, SourceRole, TargetIdentity
from model_cards.provider import MODEL_ID
from model_cards.provider_adapters import (
    OpenRouterApplicabilityChecker,
    OpenRouterClaimChecker,
    OpenRouterFactChecker,
    OpenRouterQuoteExtractor,
    ProviderAdapterError,
    build_nexus_openrouter_inference_engine,
)
from model_cards.risk_mapping import (
    INFERENCE_MODEL,
    NEXUS_PACKAGE_VERSION,
    RiskCandidate,
    TaxonomyRelease,
    TaxonomyRisk,
    UseContext,
)


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
            "provider": "Baidu",
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
                    "benchmark_scope_json": None,
                    "origin": "source_stated",
                }
            ]
        }
        fake = FakeCalls(value)
        batch = OpenRouterQuoteExtractor(**self.kwargs(fake)).extract_source(
            source(), target=TARGET, source_catalog_sha256="c" * 64
        )
        self.assertEqual(MODEL_ID, batch.inference_model)
        self.assertEqual("Baidu", batch.provider)
        self.assertEqual(1, len(batch.proposals))
        spec = fake.specs[0]
        self.assertEqual(MODEL_ID, MODEL_ID)
        self.assertEqual(0, json.loads(spec.user_prompt)["windows"][0]["normalized_start"])
        self.assertFalse(spec.json_schema["additionalProperties"])
        self.assertEqual("quote_extraction", spec.context_metadata["stage"])
        self.assertNotIn("excerpt", spec.context_metadata)

    def test_quote_extractor_rejects_invented_source_and_wrong_target(self) -> None:
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
                        "benchmark_scope_json": None,
                        "origin": "source_stated",
                    }
                ]
            }
        )
        with self.assertRaises(ProviderAdapterError):
            OpenRouterQuoteExtractor(**self.kwargs(fake)).extract_source(
                source(), target=TARGET, source_catalog_sha256="c" * 64
            )
        other = TargetIdentity("example-lab/other", "d" * 40)
        with self.assertRaisesRegex(ProviderAdapterError, "exact-target"):
            OpenRouterQuoteExtractor(**self.kwargs(FakeCalls())).extract_source(
                source(), target=other, source_catalog_sha256="c" * 64
            )

    def test_claim_checker_runs_independent_closed_decisions(self) -> None:
        fake = FakeCalls(
            {"status": "accepted", "reason": "semantic_field_fit"},
            {"status": "accepted", "reason": "semantic_value_support"},
        )
        checker = OpenRouterClaimChecker(**self.kwargs(fake))
        item = candidate()
        field = checker.decide(item, GateName.FIELD_FIT)
        value = checker.decide(item, GateName.VALUE_SUPPORT)
        self.assertEqual(GateName.FIELD_FIT, field.gate)
        self.assertEqual(GateName.VALUE_SUPPORT, value.gate)
        self.assertNotEqual(field.request_sha256, value.request_sha256)
        self.assertEqual(2, len(fake.specs))
        for spec in fake.specs:
            payload = json.loads(spec.user_prompt)
            self.assertEqual(item.candidate_id, payload["candidate_id"])
            self.assertEqual(item.value, payload["value"])
            self.assertNotIn("corrected_value", spec.json_schema["properties"])

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
                "outcome": "support",
                "reason_code": "support_in_context",
                "cited_chunk_ids": [chunk_id],
            }
        )
        response = OpenRouterFactChecker(**self.kwargs(fake)).check(request)
        self.assertEqual("support", response.outcome.value)
        self.assertEqual((chunk_id,), response.cited_chunk_ids)
        payload = json.loads(fake.specs[0].user_prompt)
        self.assertEqual(request.hypothesis, payload["hypothesis"])
        self.assertEqual({chunk_id}, {item["chunk_id"] for item in payload["contexts"]})

        bad = FakeCalls(
            {
                "outcome": "support",
                "reason_code": "support_in_context",
                "cited_chunk_ids": ["chunk-invented"],
            }
        )
        with self.assertRaises(ProviderAdapterError):
            OpenRouterFactChecker(**self.kwargs(bad)).check(request)

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
        symlink = self.root / "linked"
        real = self.root / "real"
        real.mkdir()
        symlink.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ProviderAdapterError, "symlink"):
            OpenRouterClaimChecker(
                provider="Baidu",
                ledger_path=self.ledger,
                decision_dir=symlink,
            )


if __name__ == "__main__":
    unittest.main()
