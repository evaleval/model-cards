from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from types import SimpleNamespace
from unittest import mock
import unittest

from model_cards.factreasoner import (
    IBM_FACTREASONER_UPSTREAM_REVISION,
    CheckOutcome,
    CheckRequest,
    CheckerResponse,
    CheckStage,
    FactReasonerError,
    FactReasonerReplayError,
    FactReasonerRecord,
    FieldAction,
    FieldCoverageStatus,
    IBMFactReasonerAdapter,
    MAX_FACT_CHECKS_PER_BATCH,
    ReferentHypothesis,
    RetrievalConfig,
    SourceAvailability,
    atomize_card,
    build_source_chunks,
    hypotheses_from_provenance,
    replay_factreasoner,
    retrieve_chunks,
    run_factreasoner,
)
from model_cards.models import RelationToTarget, SourceDocument, SourceRole, TargetIdentity
from model_cards.provider import ProviderResponseError, ProviderTerminalAttemptError
from model_cards.run_ledger import LedgerConflictError
from model_cards.artifact import project_card
from model_cards.schema import CONTRACT_SCHEMA
from tests.helpers import synthetic_artifact


TARGET = TargetIdentity("acme/Instruct", "a" * 40)


def contract(details: dict[str, dict]) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "x-model-card": {"bindable_sections": ["identity", "details"]},
        "type": "object",
        "required": ["identity", "details", "validation"],
        "properties": {
            "identity": {
                "type": "object",
                "required": ["model_id", "revision", "name"],
                "properties": {
                    "model_id": {"type": "string"},
                    "revision": {"type": "string"},
                    "name": {"type": "string"},
                },
                "additionalProperties": False,
            },
            "details": {
                "type": "object",
                "required": list(details),
                "properties": details,
                "additionalProperties": False,
            },
            "validation": {
                "type": "object",
                "required": ["coverage"],
                "properties": {"coverage": {"type": "number"}},
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    }


def card(**details):
    return {
        "identity": {
            "model_id": TARGET.model_id,
            "revision": TARGET.revision,
            "name": "Acme Instruct",
        },
        "details": details,
        "validation": {"coverage": 1.0},
    }


def source(
    text: str,
    *,
    source_id: str = "source-1",
    target: TargetIdentity | None = TARGET,
) -> SourceDocument:
    return SourceDocument(
        source_id=source_id,
        source_uri=f"https://example.org/{source_id}",
        role=SourceRole.DEVELOPER_REPORT,
        source_revision="report-v1",
        target=target,
        text=text,
    )


def identity_source(extra: str = "", **kwargs) -> SourceDocument:
    return source(
        "# Identity\n"
        f"Model ID {TARGET.model_id}. Revision {TARGET.revision}. Name Acme Instruct.\n\n"
        "# Details\n"
        + extra,
        **kwargs,
    )


class FixtureChecker:
    checker_id = "fixture/checker"
    checker_revision = "fixture-v1"

    def __init__(self, responder=None) -> None:
        self.calls = []
        self.responder = responder or self.support

    @staticmethod
    def support(request):
        return CheckerResponse(
            outcome=CheckOutcome.SUPPORT,
            reason_code="fixture_support",
            cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
        )

    def check(self, request):
        self.calls.append(request)
        return self.responder(request)


class FactReasonerKernelTests(unittest.TestCase):
    def test_audit_contract_paths_and_projection_use_the_canonical_schema(self) -> None:
        artifact = synthetic_artifact()
        result = atomize_card(project_card(artifact), CONTRACT_SCHEMA, artifact.target)
        self.assertEqual(len(result.field_coverage), 47)
        relations = {item.hypothesis.relation for item in result.atoms}
        self.assertIn(RelationToTarget.EXACT_TARGET, relations)
        self.assertIn(RelationToTarget.BASE_MODEL, relations)
        self.assertIn(RelationToTarget.COMPARISON_MODEL, relations)
        score_atoms = [
            item
            for item in result.atoms
            if item.field_path == "evaluation.benchmark_scores"
        ]
        self.assertEqual(1, len(score_atoms))
        self.assertEqual("evaluation.benchmark_scores[0]", score_atoms[0].value_path)
        self.assertIn('"benchmark":"Toy Reasoning"', score_atoms[0].statement)
        self.assertIn('"metric":"accuracy"', score_atoms[0].statement)
        self.assertIn('"score":73.5', score_atoms[0].statement)

    def test_bibtex_citation_is_one_metadata_unit_not_fragment_atoms(self) -> None:
        schema = contract({"citation": {"type": "string"}})
        citation = (
            "```bibtex\n"
            "@misc{gemma3,\n"
            "  title={Gemma 3},\n"
            "  author={Example Lab}\n"
            "}\n"
            "```"
        )

        result = atomize_card(card(citation=citation), schema, TARGET)

        atoms = [item for item in result.atoms if item.field_path == "details.citation"]
        self.assertEqual(1, len(atoms))
        self.assertIn("@misc{gemma3", atoms[0].statement)
        self.assertNotEqual("}", atoms[0].statement.strip())

    def test_schema_parametric_atomization_covers_every_final_field(self) -> None:
        schema = contract(
            {
                "summary": {"type": "string"},
                "scores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["benchmark", "score"],
                        "properties": {
                            "benchmark": {"type": "string"},
                            "score": {"type": "number"},
                        },
                        "additionalProperties": False,
                    },
                },
                "empty_findings": {"type": "array"},
                "missing": {"type": "string"},
            }
        )
        value = card(
            summary="The model is instruction tuned. It accepts text.",
            scores=[{"benchmark": "Toy", "score": 0.75}],
            empty_findings=[],
            missing="Not specified",
        )
        result = atomize_card(value, schema, TARGET)

        expected = {
            "identity.model_id",
            "identity.revision",
            "identity.name",
            "details.summary",
            "details.scores",
            "details.empty_findings",
            "details.missing",
        }
        self.assertEqual(expected, {item.field_path for item in result.field_coverage})
        missing = next(
            item for item in result.field_coverage if item.field_path == "details.missing"
        )
        self.assertIs(missing.status, FieldCoverageStatus.ABSENCE)
        self.assertEqual(missing.atom_ids, ())
        empty = next(
            item for item in result.field_coverage if item.field_path == "details.empty_findings"
        )
        self.assertIs(empty.status, FieldCoverageStatus.CHECKED)
        self.assertEqual(len(empty.atom_ids), 1)
        score_atoms = [item for item in result.atoms if item.field_path == "details.scores"]
        self.assertEqual({item.value_path for item in score_atoms}, {
            "details.scores[0].benchmark",
            "details.scores[0].score",
        })
        self.assertEqual(
            {item.atom_id for item in result.atoms},
            {atom_id for item in result.field_coverage for atom_id in item.atom_ids},
        )

    def test_optional_schema_fields_are_accounted_for_as_absent(self) -> None:
        schema = contract(
            {
                "present": {"type": "string"},
                "optional": {"type": "string"},
            }
        )
        schema["properties"]["details"]["required"] = ["present"]
        value = card(present="Source-backed value.")

        result = atomize_card(value, schema, TARGET)

        optional = next(
            item
            for item in result.field_coverage
            if item.field_path == "details.optional"
        )
        self.assertIs(optional.status, FieldCoverageStatus.ABSENCE)
        self.assertEqual((), optional.atom_ids)

    def test_wrong_target_referent_is_rejected_and_wrong_scope_is_unavailable(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        value = card(claim="The model accepts text.")
        with self.assertRaisesRegex(FactReasonerError, "exact-target hypothesis"):
            atomize_card(
                value,
                schema,
                TARGET,
                field_hypotheses={
                    "details.claim": ReferentHypothesis(
                        "acme/Other@" + "b" * 40,
                        RelationToTarget.EXACT_TARGET,
                    )
                },
            )

        checker = FixtureChecker()
        wrong_target = TargetIdentity("acme/Other", "b" * 40)
        record = run_factreasoner(
            value,
            schema,
            TARGET,
            (identity_source("The model accepts text.", target=wrong_target),),
            checker,
        )
        self.assertFalse(checker.calls)
        self.assertTrue(record.decisions)
        self.assertTrue(all(item.outcome is CheckOutcome.UNAVAILABLE for item in record.decisions))
        self.assertTrue(
            all(item.reason_code == "no_in_scope_frozen_source" for item in record.decisions)
        )
        self.assertNotIn("fabrication", json.dumps(record.to_dict()).casefold())

    def test_structured_items_carry_per_referent_relation_hypotheses(self) -> None:
        schema = contract(
            {
                "comparisons": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["model_id", "score"],
                        "properties": {
                            "model_id": {"type": "string"},
                            "score": {"type": "number"},
                        },
                        "additionalProperties": False,
                    },
                }
            }
        )
        result = atomize_card(
            card(comparisons=[{"model_id": "acme/Other", "score": 0.5}]),
            schema,
            TARGET,
            field_hypotheses={
                "details.comparisons[0]": ReferentHypothesis(
                    "acme/Other@" + "b" * 40,
                    RelationToTarget.COMPARISON_MODEL,
                )
            },
        )
        atoms = [item for item in result.atoms if item.field_path == "details.comparisons"]
        self.assertEqual(len(atoms), 2)
        self.assertTrue(
            all(item.hypothesis.relation is RelationToTarget.COMPARISON_MODEL for item in atoms)
        )
        self.assertTrue(all("acme/Other@" in item.checker_hypothesis for item in atoms))

        provenance = {
            "provenance": {
                "field_references": {
                    "details.comparisons[0]": [
                        {
                            "claimed_entity": "acme/Other@" + "b" * 40,
                            "relation": "comparison_model",
                        },
                        {
                            "claimed_entity": "acme/Other@" + "b" * 40,
                            "relation": "comparison_model",
                        },
                    ]
                }
            }
        }
        inferred = hypotheses_from_provenance(provenance)
        self.assertIs(
            inferred["details.comparisons[0]"].relation,
            RelationToTarget.COMPARISON_MODEL,
        )

        conflicting = deepcopy(provenance)
        conflicting["provenance"]["field_references"]["details.comparisons[0]"][1][
            "claimed_entity"
        ] = "acme/Different@" + "c" * 40
        with self.assertRaisesRegex(FactReasonerError, "conflicting referent"):
            hypotheses_from_provenance(conflicting)

    def test_exact_number_and_name_boosts_control_deterministic_order(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        atom = next(
            item
            for item in atomize_card(
                card(claim="OLMo reports 8B parameters."), schema, TARGET
            ).atoms
            if item.field_path == "details.claim"
        )
        corpus = build_source_chunks(
            (
                source(
                    "OLMo reports parameters and architecture details repeatedly, but 18B.",
                    source_id="source-wrong",
                ),
                source("Short note: OLMo reports 8B.", source_id="source-exact"),
            )
        )
        first = retrieve_chunks(atom, corpus.chunks, top_k=2)
        second = retrieve_chunks(atom, tuple(reversed(corpus.chunks)), top_k=2)
        self.assertEqual(first[0].chunk.source_id, "source-exact")
        self.assertEqual(
            [item.chunk.chunk_id for item in first],
            [item.chunk.chunk_id for item in second],
        )

    def test_exact_number_mismatch_and_contradiction_require_repair_or_withhold(self) -> None:
        schema = contract({"parameter_count": {"type": "string"}})
        value = card(parameter_count="OLMo has 8B parameters.")

        def respond(request):
            if request.atom.field_path == "details.parameter_count":
                context = next(
                    item for item in request.contexts if "7B" in item.text
                )
                return CheckerResponse(
                    CheckOutcome.CONTRADICTION,
                    "exact_number_mismatch",
                    (context.chunk.chunk_id,),
                )
            return FixtureChecker.support(request)

        record = run_factreasoner(
            value,
            schema,
            TARGET,
            (identity_source("OLMo has 7B parameters."),),
            FixtureChecker(respond),
        )
        atom = next(item for item in record.atoms if item.field_path == "details.parameter_count")
        decision = next(item for item in record.decisions if item.atom_id == atom.atom_id)
        field = next(item for item in record.field_decisions if item.field_path == atom.field_path)
        self.assertIs(decision.outcome, CheckOutcome.CONTRADICTION)
        self.assertIs(decision.field_action, FieldAction.REPAIR_OR_WITHHOLD)
        self.assertIs(field.action, FieldAction.REPAIR_OR_WITHHOLD)
        cited = [item for item in decision.attempts[-1].evidence if item.cited]
        self.assertEqual(len(cited), 1)
        self.assertIsNotNone(cited[0].char_start)

    def test_material_neutral_runs_bounded_full_source_fallback(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        checker = FixtureChecker(
            lambda request: CheckerResponse(CheckOutcome.NEUTRAL, "no_relation")
        )
        record = run_factreasoner(
            card(claim="An unsupported material claim."),
            schema,
            TARGET,
            (identity_source("Other retained source material."),),
            checker,
        )
        claim_atom = next(item for item in record.atoms if item.field_path == "details.claim")
        decision = next(item for item in record.decisions if item.atom_id == claim_atom.atom_id)
        self.assertIs(decision.outcome, CheckOutcome.NEUTRAL)
        self.assertEqual(decision.reason_code, "neutral_after_bounded_fallback")
        self.assertIs(decision.field_action, FieldAction.REPAIR_OR_WITHHOLD)
        self.assertEqual([item.stage for item in decision.attempts], [
            CheckStage.RETRIEVAL,
            CheckStage.FULL_SOURCE_FALLBACK,
        ])
        self.assertTrue(decision.attempts[-1].fallback_complete)
        self.assertTrue(decision.attempts[-1].evidence)

    def test_batch_checker_runs_complete_primary_then_neutral_fallback_waves(self) -> None:
        fields = {
            f"claim_{index:02d}": {"type": "string"}
            for index in range(70)
        }
        schema = contract(fields)
        value = card(
            **{
                name: f"The exact model has documented property {index}."
                for index, name in enumerate(fields)
            }
        )

        class BatchChecker:
            checker_id = "fixture/batch-checker"
            checker_revision = "fixture-batch-v1"

            def __init__(self):
                self.batches = []

            def check(self, _request):
                raise AssertionError("single-check path must not be used")

            def check_many(self, requests):
                stage = requests[0].stage
                self.assert_single_stage(requests, stage)
                self.batches.append((stage, len(requests)))
                if stage is CheckStage.RETRIEVAL:
                    return tuple(
                        CheckerResponse(CheckOutcome.NEUTRAL, "no_relation")
                        for _ in requests
                    )
                return tuple(
                    CheckerResponse(
                        CheckOutcome.SUPPORT,
                        "fixture_support",
                        (request.contexts[0].chunk.chunk_id,),
                    )
                    for request in requests
                )

            @staticmethod
            def assert_single_stage(requests, stage):
                if any(item.stage is not stage for item in requests):
                    raise AssertionError("mixed FactReasoner stages")

        checker = BatchChecker()
        record = run_factreasoner(
            value,
            schema,
            TARGET,
            (
                identity_source(
                    "\n".join(
                        f"The exact model has documented property {index}."
                        for index in range(70)
                    )
                ),
            ),
            checker,
        )

        atom_count = len(record.atoms)
        remainder = atom_count - MAX_FACT_CHECKS_PER_BATCH
        self.assertGreater(remainder, 0)
        self.assertLessEqual(remainder, MAX_FACT_CHECKS_PER_BATCH)
        self.assertEqual(
            [
                (CheckStage.RETRIEVAL, MAX_FACT_CHECKS_PER_BATCH),
                (CheckStage.RETRIEVAL, remainder),
                (CheckStage.FULL_SOURCE_FALLBACK, MAX_FACT_CHECKS_PER_BATCH),
                (CheckStage.FULL_SOURCE_FALLBACK, remainder),
            ],
            checker.batches,
        )
        self.assertTrue(
            all(
                decision.outcome is CheckOutcome.SUPPORT
                and len(decision.attempts) == 2
                for decision in record.decisions
            )
        )

    def test_missing_and_thin_sources_are_visible_without_checker_calls(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        value = card(claim="A claim needing evidence.")
        missing_checker = FixtureChecker()
        missing = run_factreasoner(
            value,
            schema,
            TARGET,
            (),
            missing_checker,
            source_availability=(
                SourceAvailability("missing-doc", "missing", "not_found"),
            ),
        )
        self.assertFalse(missing_checker.calls)
        self.assertEqual(missing.source_availability[0].status, "missing")
        self.assertTrue(all(item.outcome is CheckOutcome.UNAVAILABLE for item in missing.decisions))
        self.assertTrue(
            all(item.field_action is FieldAction.COLLECT_OR_WITHHOLD for item in missing.decisions)
        )

        thin_checker = FixtureChecker()
        thin = run_factreasoner(
            value,
            schema,
            TARGET,
            (source("tiny"),),
            thin_checker,
            config=RetrievalConfig(min_source_chars=20),
        )
        self.assertFalse(thin_checker.calls)
        self.assertTrue(all(item.reason_code == "thin_frozen_source" for item in thin.decisions))

    def test_markdown_section_and_table_context_keep_exact_coordinates(self) -> None:
        text = (
            "# Evaluation\n\n"
            "## Main Results\n\n"
            "| Model | Score | Setting |\n"
            "| --- | --- | --- |\n"
            "| Acme Instruct | 0.75 | zero-shot |\n"
        )
        corpus = build_source_chunks((source(text),))
        row = next(item for item in corpus.chunks if "0.75" in item.text)
        self.assertEqual(row.section_path, ("Evaluation", "Main Results"))
        self.assertIn("| Model | Score | Setting |", row.table_context)
        self.assertEqual(text[row.char_start : row.char_end], row.text)

    def test_json_sources_emit_pointer_coordinates(self) -> None:
        document = SourceDocument(
            source_id="json-source",
            source_uri="https://example.org/config.json",
            role=SourceRole.HUGGING_FACE_METADATA,
            source_revision=TARGET.revision,
            target=TARGET,
            data={"model": {"hidden_size": 4096}},
            content_sha256="f" * 64,
        )
        corpus = build_source_chunks((document,))
        chunk = next(item for item in corpus.chunks if "4096" in item.text)
        self.assertEqual(chunk.json_pointer, "/model/hidden_size")
        self.assertIsNone(chunk.char_start)
        self.assertEqual(chunk.source_sha256, "f" * 64)

    def test_strict_round_trip_rejects_duplicate_atoms_and_tampered_decisions(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        record = run_factreasoner(
            card(claim="The model accepts text."),
            schema,
            TARGET,
            (identity_source("The model accepts text."),),
            FixtureChecker(),
        )
        encoded = record.to_dict()
        self.assertEqual(FactReasonerRecord.from_dict(deepcopy(encoded)).to_dict(), encoded)

        duplicate = deepcopy(encoded)
        duplicate["atoms"].append(deepcopy(duplicate["atoms"][0]))
        with self.assertRaisesRegex(FactReasonerError, "duplicate atom"):
            FactReasonerRecord.from_dict(duplicate)

        tampered = deepcopy(encoded)
        tampered["decisions"][0]["outcome"] = "neutral"
        with self.assertRaises(FactReasonerError):
            FactReasonerRecord.from_dict(tampered)

        extra = deepcopy(encoded)
        extra["private_trace"] = "not part of the record"
        with self.assertRaisesRegex(FactReasonerError, "invalid shape"):
            FactReasonerRecord.from_dict(extra)

    def test_deterministic_rerun_replay_and_complete_atom_coverage(self) -> None:
        schema = contract({"claim": {"type": "string"}, "missing": {"type": "string"}})
        value = card(claim="The model accepts text. It emits text.", missing="Not applicable")
        frozen = (identity_source("The model accepts text. It emits text."),)
        first = run_factreasoner(value, schema, TARGET, frozen, FixtureChecker())
        second = run_factreasoner(value, schema, TARGET, frozen, FixtureChecker())
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(
            [item.atom_id for item in first.atoms],
            [item.atom_id for item in first.decisions],
        )
        self.assertEqual(
            len(first.atoms),
            sum(
                len(item.atom_ids)
                for item in first.field_coverage
                if item.status is FieldCoverageStatus.CHECKED
            ),
        )
        replayed = replay_factreasoner(
            first,
            value,
            schema,
            TARGET,
            frozen,
            FixtureChecker(),
        )
        self.assertEqual(replayed.to_dict(), first.to_dict())
        with self.assertRaises(FactReasonerReplayError):
            replay_factreasoner(
                first,
                value,
                schema,
                TARGET,
                (identity_source("The retained source changed."),),
                FixtureChecker(),
            )

    def test_checker_unavailability_remains_a_complete_typed_decision(self) -> None:
        schema = contract({"claim": {"type": "string"}})

        def unavailable(_request):
            raise RuntimeError("offline")

        record = run_factreasoner(
            card(claim="The model accepts text."),
            schema,
            TARGET,
            (identity_source("The model accepts text."),),
            FixtureChecker(unavailable),
        )
        self.assertTrue(record.decisions)
        for decision in record.decisions:
            self.assertIs(decision.outcome, CheckOutcome.UNAVAILABLE)
            self.assertEqual(decision.reason_code, "checker_unavailable")
            self.assertEqual(len(decision.attempts), 1)
            self.assertTrue(decision.attempts[0].evidence)

    def test_provider_checker_failures_preserve_fatal_boundaries(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        args = (
            card(claim="The model accepts text."),
            schema,
            TARGET,
            (identity_source("The model accepts text."),),
        )

        def response_error(reason_code):
            def fail(_request):
                raise ProviderResponseError("synthetic", reason_code=reason_code)

            return fail

        unavailable = run_factreasoner(
            *args, FixtureChecker(response_error("http_bad_request"))
        )
        self.assertTrue(
            all(item.outcome is CheckOutcome.UNAVAILABLE for item in unavailable.decisions)
        )
        terminal_unavailable = run_factreasoner(
            *args,
            FixtureChecker(
                lambda _request: (_ for _ in ()).throw(
                    ProviderTerminalAttemptError(
                        "synthetic", reason_code="http_bad_request"
                    )
                )
            ),
        )
        self.assertTrue(
            all(
                item.outcome is CheckOutcome.UNAVAILABLE
                for item in terminal_unavailable.decisions
            )
        )

        for error in (
            ProviderResponseError(
                "synthetic", reason_code="returned_provider_mismatch"
            ),
            ProviderTerminalAttemptError(
                "synthetic", reason_code="cost_over_reservation"
            ),
            LedgerConflictError("synthetic"),
        ):
            with self.subTest(error=type(error).__name__), self.assertRaises(
                type(error)
            ):
                run_factreasoner(
                    *args,
                    FixtureChecker(lambda _request, error=error: (_ for _ in ()).throw(error)),
                )

    def test_truncated_fallback_is_marked_source_limited(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        config = RetrievalConfig(
            max_chunk_chars=50,
            chunk_overlap_chars=5,
            max_source_chars=200,
            max_total_source_chars=200,
            min_source_chars=10,
            max_fallback_chunks=1,
            max_fallback_chars=50,
        )
        record = run_factreasoner(
            card(claim="A claim absent from retained text."),
            schema,
            TARGET,
            (identity_source("unrelated words " * 40),),
            FixtureChecker(lambda request: CheckerResponse(CheckOutcome.NEUTRAL, "no_relation")),
            config=config,
        )
        self.assertTrue(record.corpus_truncated)
        self.assertTrue(all(item.source_limited for item in record.decisions))

    def test_optional_ibm_adapter_is_lazy_and_pinned(self) -> None:
        with mock.patch("model_cards.factreasoner.importlib.import_module") as imported:
            adapter = IBMFactReasonerAdapter()
            imported.assert_not_called()
        self.assertEqual(adapter.checker_revision, IBM_FACTREASONER_UPSTREAM_REVISION)

    def test_ibm_adapter_runs_fr1_graph_and_normalizes_pgmpy_marginal(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        atom = next(
            item
            for item in atomize_card(
                card(claim="Acme Instruct supports exact source grounding."),
                schema,
                TARGET,
            ).atoms
            if item.field_path == "details.claim"
        )
        corpus = build_source_chunks(
            (identity_source("Acme Instruct supports exact source grounding."),)
        )
        contexts = retrieve_chunks(atom, corpus.chunks, top_k=2)
        request = CheckRequest(
            atom=atom,
            stage=CheckStage.RETRIEVAL,
            contexts=contexts,
            fallback_complete=len(contexts) == len(corpus.chunks),
        )
        graphs = []

        class FakeNode:
            def __init__(self, identifier, node_type, probability):
                self.id = identifier
                self.type = node_type
                self.probability = probability

        class FakeEdge:
            def __init__(self, source_id, target_id, relation, probability, link):
                self.source = source_id
                self.target = target_id
                self.type = relation
                self.probability = probability
                self.link = link

        class FakeGraph:
            def __init__(self):
                self.nodes = []
                self.edges = []
                graphs.append(self)

            def add_node(self, node):
                self.nodes.append(node)

            def add_edge(self, edge):
                self.edges.append(edge)

        class FakeReasoner:
            def __init__(self, *, nli_extractor, merlin_path, use_priors):
                self.markov_network = None
                self.merlin_path = merlin_path
                self.use_priors = use_priors

            def from_fact_graph(self, graph):
                self.markov_network = graph

        class FakeVariableElimination:
            def __init__(self, network):
                self.network = network

            def query(self, *, variables, show_progress):
                self.variables = variables
                self.show_progress = show_progress
                return SimpleNamespace(values=[0.07, 0.43])

        adapter = IBMFactReasonerAdapter(FixtureChecker())
        runtime = SimpleNamespace(
            fact_reasoner=FakeReasoner,
            fact_graph=FakeGraph,
            node=FakeNode,
            edge=FakeEdge,
            variable_elimination=FakeVariableElimination,
            prior_prob_atom=0.5,
            prior_prob_context=0.9,
        )
        with mock.patch.object(adapter, "_load_upstream", return_value=runtime):
            response = adapter.check(request)

        self.assertEqual(CheckOutcome.SUPPORT, response.outcome)
        self.assertEqual(
            (contexts[0].chunk.chunk_id,), response.cited_chunk_ids
        )
        self.assertEqual(1, len(graphs))
        self.assertEqual(1, len(graphs[0].edges))
        self.assertEqual("entailment", graphs[0].edges[0].type)
        self.assertEqual(0.9, graphs[0].edges[0].probability)
        inference = adapter.inference_for(request)
        self.assertIsNotNone(inference)
        self.assertAlmostEqual(0.14, inference.atom_false_probability)
        self.assertAlmostEqual(0.86, inference.atom_true_probability)
        self.assertEqual(
            (contexts[0].chunk.chunk_id,), inference.cited_chunk_ids
        )

    @unittest.skipUnless(
        IBMFactReasonerAdapter.is_installed(),
        "exact pinned IBM FactReasoner extra is not installed",
    )
    def test_installed_ibm_adapter_runs_without_merlin_or_live_calls(self) -> None:
        schema = contract({"claim": {"type": "string"}})
        atom = next(
            item
            for item in atomize_card(
                card(claim="Acme Instruct supports exact source grounding."),
                schema,
                TARGET,
            ).atoms
            if item.field_path == "details.claim"
        )
        corpus = build_source_chunks(
            (identity_source("Acme Instruct supports exact source grounding."),)
        )
        contexts = retrieve_chunks(atom, corpus.chunks, top_k=2)
        request = CheckRequest(
            atom=atom,
            stage=CheckStage.RETRIEVAL,
            contexts=contexts,
            fallback_complete=len(contexts) == len(corpus.chunks),
        )
        adapter = IBMFactReasonerAdapter(FixtureChecker())

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            response = adapter.check(request)

        self.assertEqual(CheckOutcome.SUPPORT, response.outcome)
        self.assertEqual("", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())
        inference = adapter.inference_for(request)
        self.assertIsNotNone(inference)
        self.assertGreater(inference.atom_true_probability, 0.5)


if __name__ == "__main__":
    unittest.main()
