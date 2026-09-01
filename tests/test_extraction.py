from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.claim_gate import (
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
    evaluate_claim_gate,
)
from model_cards.extraction import (
    ExtractionBatch,
    ExtractionError,
    ProposalStatus,
    QuoteProposal,
    build_source_windows,
    deterministic_structured_candidates,
    extraction_response_schema,
    materialize_quote_batch,
    proposals_from_provider_value,
)
from model_cards.models import RelationToTarget
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import build_source_document_catalog


REVISION = "a" * 40
README = """# Model Overview

The exact target is an instruction-following language model.

## Evaluation Results

The reported exact-target score is 73.5 on ExampleBench.

## Limitations

The model may produce incorrect answers in personalized assistant responses.
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
                    "config": {"model_type": "test", "torch_dtype": "float16"},
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
            return RemoteObject(FetchStatus.OK, README.encode())
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                b'{"model_type":"test","torch_dtype":"float16"}',
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "bundle"
        collect_hf_source_bundle("acme/Instruct", root, Adapter())
        self.catalog = build_source_document_catalog(replay_source_bundle(root))
        self.readme = next(
            item for item in self.catalog.documents if item.source_uri.endswith("/README.md")
        )

    def proposal(self, **changes) -> QuoteProposal:
        values = {
            "source_id": self.readme.source_id,
            "field_path": "identity.summary",
            "value": "The exact target is an instruction-following language model.",
            "quote": "The exact target is an instruction-following language model.",
            "claim_entity": f"acme/Instruct@{REVISION}",
            "relation": RelationToTarget.EXACT_TARGET,
            "benchmark_scope": None,
            "origin": "source_stated",
        }
        values.update(changes)
        return QuoteProposal(**values)

    def batch(self, *proposals: QuoteProposal) -> ExtractionBatch:
        return ExtractionBatch.build(
            target=self.catalog.target,
            source_catalog_sha256=self.catalog.catalog_sha256,
            provider="Baidu",
            inference_config_sha256="b" * 64,
            proposals=proposals,
        )

    @staticmethod
    def checker(candidate, gate):
        return ProseCheckerDecision.for_candidate(
            candidate,
            gate=gate,
            checker="deepseek/deepseek-v4-flash-0731",
            method="strict_schema_semantic_check",
            status=DecisionStatus.ACCEPTED,
            reason="semantic_check_supported",
        )

    def test_bounded_windows_are_deterministic_and_ephemeral(self) -> None:
        windows = build_source_windows(self.readme, window_chars=500, overlap=50)
        self.assertEqual(1, len(windows))
        self.assertLessEqual(len(windows[0].excerpt), 500)
        self.assertEqual(windows, build_source_windows(self.readme, window_chars=500, overlap=50))
        self.assertFalse(hasattr(windows[0], "to_dict"))
        self.assertNotIn("/Users/", repr(windows[0]))
        with self.assertRaises(ExtractionError):
            build_source_windows(self.readme, window_chars=100, overlap=0)

    def test_quote_materialization_recomputes_coordinates_and_section_context(self) -> None:
        proposal = self.proposal()
        result = materialize_quote_batch(self.batch(proposal), self.catalog)
        self.assertEqual(1, len(result.candidates))
        candidate = result.candidates[0]
        evidence = candidate.evidence[0]
        self.assertTrue(evidence.verified)
        self.assertEqual(("Model Overview",), evidence.section_path)
        self.assertEqual(ProposalStatus.MATERIALIZED, result.outcomes[0].status)
        decisions = (
            self.checker(candidate, GateName.FIELD_FIT),
            self.checker(candidate, GateName.VALUE_SUPPORT),
        )
        gate = evaluate_claim_gate(candidate, self.catalog.documents, decisions)
        self.assertTrue(gate.projection_eligible)

    def test_publisher_context_wrapper_is_constructed_locally_not_by_provider(self) -> None:
        description = (
            "The model may produce incorrect answers in personalized assistant responses."
        )
        proposal = self.proposal(
            field_path="use_and_risk.limitations[0]",
            value=description,
            quote=description,
        )
        candidate = materialize_quote_batch(self.batch(proposal), self.catalog).candidates[0]
        self.assertEqual(description, candidate.value["description"])
        self.assertEqual("publisher_reported", candidate.value["origin"])
        self.assertEqual([self.readme.source_id], candidate.value["source_refs"])
        self.assertTrue(candidate.value["context_id"].startswith("context:"))
        self.assertNotIn(candidate.value["context_id"], README)
        self.assertEqual(
            ("Model Overview", "Limitations"), candidate.evidence[0].section_path
        )
        gate = evaluate_claim_gate(
            candidate,
            self.catalog.documents,
            (
                self.checker(candidate, GateName.FIELD_FIT),
                self.checker(candidate, GateName.VALUE_SUPPORT),
            ),
        )
        self.assertTrue(gate.projection_eligible)
        with self.assertRaisesRegex(ExtractionError, "item index"):
            self.proposal(field_path="use_and_risk.limitations", value=description)

    def test_supported_quote_cannot_cover_a_different_numeric_value(self) -> None:
        proposal = self.proposal(
            field_path="evaluation.results_summary",
            value="The reported exact-target score is 99.0 on ExampleBench.",
            quote="The reported exact-target score is 73.5 on ExampleBench.",
        )
        candidate = materialize_quote_batch(self.batch(proposal), self.catalog).candidates[0]
        gate = evaluate_claim_gate(
            candidate,
            self.catalog.documents,
            (
                self.checker(candidate, GateName.FIELD_FIT),
                self.checker(candidate, GateName.VALUE_SUPPORT),
            ),
        )
        self.assertFalse(gate.projection_eligible)
        self.assertEqual(
            "complete_value_not_in_evidence",
            next(item for item in gate.decisions if item.gate is GateName.VALUE_SUPPORT).reason,
        )

    def test_nonmatching_quote_remains_an_immutable_candidate_for_gate_withholding(self) -> None:
        proposal = self.proposal(quote="A paraphrase absent from the frozen source.")
        candidate = materialize_quote_batch(self.batch(proposal), self.catalog).candidates[0]
        self.assertFalse(candidate.evidence[0].verified)
        gate = evaluate_claim_gate(
            candidate,
            self.catalog.documents,
            (
                self.checker(candidate, GateName.FIELD_FIT),
                self.checker(candidate, GateName.VALUE_SUPPORT),
            ),
        )
        coordinate = next(
            item for item in gate.decisions if item.gate is GateName.COORDINATE_INTEGRITY
        )
        self.assertEqual(DecisionStatus.WITHHELD, coordinate.status)
        self.assertEqual("quote_coordinates_unverified", coordinate.reason)

    def test_unavailable_or_structured_source_proposal_is_visible_not_materialized(self) -> None:
        missing = self.proposal(source_id="src_" + "f" * 24)
        structured_source = next(item for item in self.catalog.documents if item.data is not None)
        wrong_kind = self.proposal(source_id=structured_source.source_id)
        result = materialize_quote_batch(self.batch(missing, wrong_kind), self.catalog)
        self.assertEqual((), result.candidates)
        self.assertEqual(
            {ProposalStatus.SOURCE_UNAVAILABLE, ProposalStatus.SOURCE_KIND_MISMATCH},
            {item.status for item in result.outcomes},
        )

    def test_closed_registry_discovers_replayable_structured_candidates(self) -> None:
        result = deterministic_structured_candidates(self.catalog)
        fields = {item.field_path for item in result.candidates}
        self.assertTrue(
            {
                "identity.model_id",
                "identity.revision",
                "identity.model_type",
                "model_details.architecture_type",
                "model_details.precision",
            }
            <= fields
        )
        for candidate in result.candidates:
            gate = evaluate_claim_gate(candidate, self.catalog.documents)
            self.assertTrue(gate.projection_eligible, candidate.field_path)

    def test_provider_value_boundary_uses_json_strings_and_rejects_duplicates(self) -> None:
        raw = {
            "proposals": [
                {
                    "source_id": self.readme.source_id,
                    "field_path": "evaluation.benchmark_scores[0]",
                    "value_json": json.dumps(
                        {
                            "benchmark": "ExampleBench",
                            "metric": "accuracy",
                            "score": 73.5,
                            "setting": "zero-shot",
                        }
                    ),
                    "quote": "The reported exact-target score is 73.5 on ExampleBench.",
                    "claim_entity": f"acme/Instruct@{REVISION}",
                    "relation": "exact_target",
                    "benchmark_scope_json": json.dumps(
                        {
                            "benchmark": "ExampleBench",
                            "metric": "accuracy",
                            "setting": "zero-shot",
                        }
                    ),
                    "origin": "source_stated",
                }
            ]
        }
        proposal = proposals_from_provider_value(raw)[0]
        self.assertEqual(73.5, proposal.value["score"])
        bad = json.loads(json.dumps(raw))
        bad["proposals"][0]["value_json"] = '{"score":73.5,"score":99.0}'
        with self.assertRaisesRegex(ExtractionError, "invalid canonical JSON"):
            proposals_from_provider_value(bad)
        schema = extraction_response_schema()
        self.assertTrue(schema["strict"])
        self.assertFalse(schema["schema"]["additionalProperties"])
        item_schema = schema["schema"]["properties"]["proposals"]["items"]
        self.assertFalse(item_schema["additionalProperties"])

    def test_batch_round_trip_is_content_addressed_and_contains_no_source_body(self) -> None:
        batch = self.batch(self.proposal())
        restored = ExtractionBatch.from_dict(batch.to_dict())
        self.assertEqual(batch, restored)
        serialized = json.dumps(batch.to_dict())
        self.assertNotIn("The reported exact-target score", serialized)
        self.assertNotIn("provider response", serialized.casefold())
        with self.assertRaises(ExtractionError):
            replace(batch, source_catalog_sha256="0" * 64)

    def test_stale_catalog_or_wrong_model_fails_before_materialization(self) -> None:
        batch = self.batch(self.proposal())
        stale_batch = ExtractionBatch.build(
            target=batch.target,
            source_catalog_sha256="0" * 64,
            provider=batch.provider,
            inference_config_sha256=batch.inference_config_sha256,
            proposals=batch.proposals,
        )
        with self.assertRaisesRegex(ExtractionError, "stale"):
            materialize_quote_batch(stale_batch, self.catalog)
        with self.assertRaisesRegex(ExtractionError, "unauthorized"):
            replace(batch, inference_model="another/model")


if __name__ == "__main__":
    unittest.main()
