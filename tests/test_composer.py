from __future__ import annotations

from copy import deepcopy
import json
import unittest

from model_cards.bindings import quote_binding, source_from_dict, structured_binding
from model_cards.claim_gate import (
    ClaimCandidate,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
    evaluate_claim_gate,
)
from model_cards.composer import (
    ComposerError,
    CompositionResult,
    ConflictReason,
    WriterChoice,
    WriterSelection,
    compose_model_card,
    compose_pass_a,
    compose_pass_b,
    verify_composition_result,
)
from model_cards.models import RelationToTarget, SourceDocument, SourceRole, TargetIdentity
from model_cards.schema import NOT_SPECIFIED, validate_public_card
from tests.helpers import synthetic_artifact, synthetic_specification


class _InventingWriter:
    def select(self, writer_input):
        summary = writer_input.accepted_candidates[0]
        return WriterSelection((WriterChoice.create(summary.candidate_id, "invented"),))


class _UnknownWriter:
    def select(self, writer_input):
        return WriterSelection((WriterChoice.create("claim-" + "0" * 24, "invented"),))


class _SelectNoneWriter:
    def select(self, writer_input):
        return WriterSelection(())


class ComposerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = synthetic_artifact()
        self.target = self.artifact.target
        self.sources = tuple(
            source_from_dict(item) for item in synthetic_specification()["sources"]
        )

    def checks(self, candidate: ClaimCandidate):
        return (
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.FIELD_FIT,
                checker="tests/composer-prose-checker-v1",
                method="bounded_semantic_field_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_field_fit",
            ),
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.VALUE_SUPPORT,
                checker="tests/composer-prose-checker-v1",
                method="bounded_complete_value_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_value_support",
            ),
        )

    def quote_candidate(
        self,
        *,
        source: SourceDocument,
        field_path: str,
        value,
        quote: str,
        relation=RelationToTarget.EXACT_TARGET,
        claim_entity: str | None = None,
        benchmark_scope=None,
    ):
        binding = quote_binding(
            target=self.target,
            source=source,
            field_path=field_path,
            value=value,
            quote=quote,
            claim_entity=claim_entity
            or f"{self.target.model_id}@{self.target.revision}",
            relation=relation,
            benchmark_scope=benchmark_scope,
        )
        candidate = ClaimCandidate.from_binding(self.target, binding)
        record = evaluate_claim_gate(
            candidate,
            (*self.sources, source),
            self.checks(candidate),
        )
        return candidate, record

    def structured_candidate(self, source, field_path, pointer):
        binding = structured_binding(
            target=self.target,
            source=source,
            field_path=field_path,
            pointer=pointer,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        candidate = ClaimCandidate.from_binding(self.target, binding)
        record = evaluate_claim_gate(candidate, (*self.sources, source))
        return candidate, record

    def test_two_pass_composition_is_schema_valid_and_strictly_replayable(self) -> None:
        candidates = []
        records = []
        for field_path in ("identity.name", "identity.license", "model_details.context_length"):
            binding = next(
                item for item in self.artifact.bindings if item.field_path == field_path
            )
            candidate = ClaimCandidate.from_binding(self.target, binding)
            record = evaluate_claim_gate(candidate, self.sources)
            candidates.append(candidate)
            records.append(record)

        inventory = compose_pass_a(candidates, records, self.sources)
        result = compose_pass_b(inventory)
        card = result.card
        validate_public_card(card)
        self.assertEqual(card["identity"]["name"], "Synthetic Model 1B")
        self.assertEqual(card["identity"]["model_id"], self.target.model_id)
        self.assertEqual(card["identity"]["revision"], self.target.revision)
        self.assertEqual(
            result.plan.derivations[0].name,
            "exact-target-consensus",
        )
        self.assertEqual(result.plan.derivations[0].version, "v1")
        self.assertEqual(
            set(result.plan.included_candidate_ids),
            {item.candidate_id for item in candidates},
        )
        encoded = result.to_dict()
        decoded = CompositionResult.from_dict(deepcopy(encoded))
        self.assertEqual(decoded.to_dict(), encoded)
        verify_composition_result(decoded, candidates, records, self.sources)

    def test_complete_inventory_rejects_missing_gate_record_and_mixed_target(self) -> None:
        bindings = [
            next(item for item in self.artifact.bindings if item.field_path == field)
            for field in ("identity.name", "identity.license")
        ]
        candidates = [ClaimCandidate.from_binding(self.target, item) for item in bindings]
        records = [evaluate_claim_gate(candidates[0], self.sources)]
        with self.assertRaisesRegex(ComposerError, "incomplete"):
            compose_model_card(candidates, records, self.sources)

        other = ClaimCandidate(
            target=TargetIdentity("example-lab/other", "9" * 40),
            field_path=candidates[1].field_path,
            value=candidates[1].value,
            claim_entity=candidates[1].claim_entity,
            relation=candidates[1].relation,
            evidence=candidates[1].evidence,
        )
        other_record = evaluate_claim_gate(other, self.sources)
        with self.assertRaisesRegex(ComposerError, "mixes exact targets"):
            compose_model_card(
                (candidates[0], other),
                (records[0], other_record),
                self.sources,
            )

    def test_distinct_scalar_values_create_explicit_conflict_and_no_priority(self) -> None:
        source = SourceDocument(
            source_id="synthetic-scalar-conflict",
            source_uri="https://example.invalid/reports/scalar-conflict",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="scalar-conflict-v1",
            target=self.target,
            synthetic=True,
            text="First exact summary. Second exact summary.",
        )
        first = self.quote_candidate(
            source=source,
            field_path="identity.summary",
            value="First exact summary.",
            quote="First exact summary.",
        )
        second = self.quote_candidate(
            source=source,
            field_path="identity.summary",
            value="Second exact summary.",
            quote="Second exact summary.",
        )
        result = compose_model_card(
            (first[0], second[0]),
            (first[1], second[1]),
            (*self.sources, source),
        )
        self.assertEqual(result.card["identity"]["summary"], NOT_SPECIFIED)
        self.assertEqual(len(result.plan.conflicts), 1)
        conflict = result.plan.conflicts[0]
        self.assertEqual(conflict.field_path, "identity.summary")
        self.assertEqual(conflict.reason, ConflictReason.DISTINCT_ELIGIBLE_VALUES)
        self.assertEqual(set(conflict.candidate_ids), {first[0].candidate_id, second[0].candidate_id})
        self.assertFalse(result.plan.included_candidate_ids)

    def test_same_list_index_conflict_blocks_the_list_but_distinct_indices_project(self) -> None:
        source = SourceDocument(
            source_id="synthetic-list-conflict",
            source_uri="https://example.invalid/reports/list-conflict",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="list-conflict-v1",
            target=self.target,
            synthetic=True,
            text=(
                "Synthetic Model 1B reports 73.5 accuracy on Toy A in zero-shot. "
                "Synthetic Model 1B reports 74.0 accuracy on Toy B in zero-shot."
            ),
        )

        def score(index, benchmark, score):
            value = {
                "benchmark": benchmark,
                "metric": "accuracy",
                "score": score,
                "setting": "zero-shot",
            }
            quote = (
                f"Synthetic Model 1B reports {score:.1f} accuracy on {benchmark} in zero-shot."
            )
            return self.quote_candidate(
                source=source,
                field_path=f"evaluation.benchmark_scores[{index}]",
                value=value,
                quote=quote,
                benchmark_scope={
                    "benchmark": benchmark,
                    "metric": "accuracy",
                    "setting": "zero-shot",
                },
            )

        a0 = score(0, "Toy A", 73.5)
        b0 = score(0, "Toy B", 74.0)
        conflicted = compose_model_card(
            (a0[0], b0[0]),
            (a0[1], b0[1]),
            (*self.sources, source),
        )
        self.assertEqual(conflicted.card["evaluation"]["benchmark_scores"], NOT_SPECIFIED)
        self.assertEqual(
            conflicted.plan.conflicts[0].reason,
            ConflictReason.DISTINCT_ELIGIBLE_VALUES,
        )

        b1 = score(1, "Toy B", 74.0)
        projected = compose_model_card(
            (a0[0], b1[0]),
            (a0[1], b1[1]),
            (*self.sources, source),
        )
        self.assertEqual(len(projected.card["evaluation"]["benchmark_scores"]), 2)

    def test_equivalent_duplicate_values_coalesce_and_retain_references(self) -> None:
        sources = []
        pairs = []
        for index in (1, 2):
            source = SourceDocument(
                source_id=f"synthetic-equivalent-{index}",
                source_uri=f"https://example.invalid/reports/equivalent-{index}",
                role=SourceRole.DEVELOPER_REPORT,
                source_revision=f"equivalent-v{index}",
                target=self.target,
                synthetic=True,
                text="Same exact summary.",
            )
            sources.append(source)
            pairs.append(
                self.quote_candidate(
                    source=source,
                    field_path="identity.summary",
                    value="Same exact summary.",
                    quote="Same exact summary.",
                )
            )
        candidates = tuple(item[0] for item in pairs)
        all_sources = (*self.sources, *sources)
        records = tuple(
            evaluate_claim_gate(candidate, all_sources, self.checks(candidate))
            for candidate in candidates
        )
        result = compose_model_card(candidates, records, all_sources)
        self.assertEqual(result.card["identity"]["summary"], "Same exact summary.")
        self.assertFalse(result.plan.conflicts)
        self.assertEqual(len(result.plan.included_candidate_ids), 2)
        refs = result.card["provenance"]["field_references"]["identity.summary"]
        self.assertEqual(len(refs), 2)

    def test_ineligible_candidate_never_reaches_writer_or_projection(self) -> None:
        binding = next(
            item for item in self.artifact.bindings if item.field_path == "identity.summary"
        )
        candidate = ClaimCandidate.from_binding(self.target, binding)
        record = evaluate_claim_gate(candidate, self.sources)
        self.assertFalse(record.projection_eligible)
        result = compose_model_card((candidate,), (record,), self.sources)
        self.assertEqual(result.card["identity"]["summary"], NOT_SPECIFIED)
        self.assertEqual(result.plan.eligible_candidate_ids, ())
        self.assertEqual(result.plan.writer_input.accepted_candidates, ())
        self.assertEqual(result.plan.excluded_candidate_ids, (candidate.candidate_id,))

    def test_writer_cannot_invent_value_or_unknown_candidate(self) -> None:
        binding = next(
            item for item in self.artifact.bindings if item.field_path == "identity.name"
        )
        candidate = ClaimCandidate.from_binding(self.target, binding)
        record = evaluate_claim_gate(candidate, self.sources)
        for writer in (_InventingWriter(), _UnknownWriter()):
            with self.subTest(writer=type(writer).__name__):
                with self.assertRaises(ComposerError):
                    compose_model_card(
                        (candidate,),
                        (record,),
                        self.sources,
                        writer=writer,
                    )

    def test_writer_may_only_omit_and_omission_remains_explicit(self) -> None:
        binding = next(
            item for item in self.artifact.bindings if item.field_path == "identity.name"
        )
        candidate = ClaimCandidate.from_binding(self.target, binding)
        record = evaluate_claim_gate(candidate, self.sources)
        result = compose_model_card(
            (candidate,),
            (record,),
            self.sources,
            writer=_SelectNoneWriter(),
        )
        self.assertEqual(result.card["identity"]["name"], NOT_SPECIFIED)
        self.assertEqual(result.plan.eligible_candidate_ids, (candidate.candidate_id,))
        self.assertEqual(result.plan.included_candidate_ids, ())

    def test_plan_and_card_never_contain_unselected_source_body(self) -> None:
        source = SourceDocument(
            source_id="synthetic-private-body",
            source_uri="https://example.invalid/reports/bounded",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="bounded-v1",
            target=self.target,
            synthetic=True,
            text="Published exact fact. PRIVATE UNUSED BODY MUST NEVER LEAK.",
        )
        candidate, record = self.quote_candidate(
            source=source,
            field_path="identity.summary",
            value="Published exact fact.",
            quote="Published exact fact.",
        )
        result = compose_model_card(
            (candidate,),
            (record,),
            (*self.sources, source),
        )
        serialized = json.dumps(result.to_dict(), sort_keys=True)
        self.assertNotIn("PRIVATE UNUSED BODY MUST NEVER LEAK", serialized)
        summary = result.plan.writer_input.accepted_candidates[0]
        reference_json = json.dumps([item.to_dict() for item in summary.references])
        self.assertNotIn("Published exact fact", reference_json)
        self.assertNotIn("quote", reference_json)
        self.assertNotIn("fragment", reference_json)

    def test_gate_eligible_but_wrong_source_relation_policy_fails_closed(self) -> None:
        source = SourceDocument(
            source_id="synthetic-index-narrative",
            source_uri="https://example.invalid/index/narrative",
            role=SourceRole.EEE_INDEX,
            source_revision="index-v1",
            target=self.target,
            synthetic=True,
            text="Index supplied narrative.",
        )
        candidate, record = self.quote_candidate(
            source=source,
            field_path="identity.summary",
            value="Index supplied narrative.",
            quote="Index supplied narrative.",
        )
        self.assertTrue(record.projection_eligible)
        with self.assertRaisesRegex(ComposerError, "relation policy"):
            compose_model_card(
                (candidate,),
                (record,),
                (*self.sources, source),
            )

    def test_changed_source_gate_or_serialized_card_breaks_replay(self) -> None:
        source = SourceDocument(
            source_id="synthetic-replay-source",
            source_uri="https://example.invalid/reports/replay",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="replay-v1",
            target=self.target,
            synthetic=True,
            text="Replay exact summary.",
        )
        candidate, record = self.quote_candidate(
            source=source,
            field_path="identity.summary",
            value="Replay exact summary.",
            quote="Replay exact summary.",
        )
        sources = (*self.sources, source)
        result = compose_model_card((candidate,), (record,), sources)

        drifted = SourceDocument(
            source_id=source.source_id,
            source_uri=source.source_uri,
            role=source.role,
            source_revision=source.source_revision,
            target=source.target,
            synthetic=True,
            text="Replay exact summary. Drift.",
        )
        drifted_sources = tuple(
            drifted if item.source_id == source.source_id else item for item in sources
        )
        with self.assertRaises(Exception):
            verify_composition_result(result, (candidate,), (record,), drifted_sources)

        ineligible_record = evaluate_claim_gate(candidate, sources)
        with self.assertRaises(ComposerError):
            verify_composition_result(
                result,
                (candidate,),
                (ineligible_record,),
                sources,
            )

        tampered = result.to_dict()
        tampered["card"]["identity"]["summary"] = "invented"
        with self.assertRaises(ComposerError):
            CompositionResult.from_dict(tampered)


if __name__ == "__main__":
    unittest.main()
