from __future__ import annotations

from copy import deepcopy
import json
import unittest

from model_cards.bindings import quote_binding
from model_cards.claim_gate import (
    ClaimCandidate,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
    correct_candidate,
    evaluate_claim_gate,
)
from model_cards.composer import compose_model_card
from model_cards.factreasoner import (
    CheckOutcome,
    CheckerResponse,
    FieldAction,
    run_factreasoner,
)
from model_cards.field_repair import (
    MAX_SEMANTIC_ATTEMPTS_PER_FIELD,
    AttemptDisposition,
    FieldRepairError,
    FieldRepairRecord,
    ReauditName,
    ReauditStatus,
    RepairOutcome,
    RepairProposal,
    RepairReason,
    RepairSubmission,
    run_field_repair,
    verify_field_repair_record,
)
from model_cards.findings import audit_omissions
from model_cards.models import RelationToTarget, SourceDocument, SourceRole, TargetIdentity
from model_cards.risk_mapping import (
    RiskCatalog,
    TaxonomyRisk,
    map_candidate_risks,
)
from model_cards.schema import CONTRACT_SCHEMA


TARGET = TargetIdentity("example-lab/Repair-1B", "a" * 40)
FIELD = "identity.summary"
OLD_VALUE = "The old field-level summary is explicitly reported."
FIRST_VALUE = "The first bounded repair is explicitly reported."
NEW_VALUE = "The repaired field-level summary is explicitly reported."


class _FactChecker:
    checker_id = "tests/field-repair-fact-checker"
    checker_revision = "fixture-v1"

    def __init__(self, *, neutral_field: str | None = None) -> None:
        self.neutral_field = neutral_field

    def check(self, request):
        outcome = (
            CheckOutcome.NEUTRAL
            if request.atom.field_path == self.neutral_field
            else CheckOutcome.SUPPORT
        )
        return CheckerResponse(
            outcome=outcome,
            reason_code=(
                "fixture_neutral" if outcome is CheckOutcome.NEUTRAL else "fixture_support"
            ),
            cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
        )


def _risk_report():
    catalog = RiskCatalog.build(
        (
            TaxonomyRisk(
                risk_id="risk-test",
                name="Test risk",
                description="A fixture-only taxonomy risk.",
                source_url="https://example.org/risk-test",
            ),
        )
    )
    # Empty grounded use context is a valid completed re-audit with zero inferred
    # risks; neither adapter is invoked on this closed path.
    return map_candidate_risks((), catalog, object(), object())


class FieldRepairKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = SourceDocument(
            source_id="repair-report-v1",
            source_uri="https://example.org/model/repair-report",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="repair-report-v1",
            target=TARGET,
            synthetic=True,
            text=(
                "# Model identity\n"
                f"Selected model {TARGET.model_id} at revision {TARGET.revision}.\n\n"
                "# Summaries\n"
                f"{OLD_VALUE}\n"
                f"{FIRST_VALUE}\n"
                f"{NEW_VALUE}\n"
                "An unrelated local-looking phrase is deliberately absent from every quote."
            ),
        )
        old_binding = quote_binding(
            target=TARGET,
            source=self.source,
            field_path=FIELD,
            value=OLD_VALUE,
            quote=OLD_VALUE,
            claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        first_binding = quote_binding(
            target=TARGET,
            source=self.source,
            field_path=FIELD,
            value=FIRST_VALUE,
            quote=FIRST_VALUE,
            claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        new_binding = quote_binding(
            target=TARGET,
            source=self.source,
            field_path=FIELD,
            value=NEW_VALUE,
            quote=NEW_VALUE,
            claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        self.first_evidence = first_binding.evidence[0]
        self.new_evidence = new_binding.evidence[0]
        # The predecessor deliberately preserves all relevant, already accepted
        # field evidence so later proposals can only narrow this explicit pool.
        self.prior = ClaimCandidate(
            target=TARGET,
            field_path=FIELD,
            value=OLD_VALUE,
            claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=(old_binding.evidence[0], self.first_evidence, self.new_evidence),
        )
        self.prior_gate = evaluate_claim_gate(
            self.prior,
            (self.source,),
            self._checks(self.prior),
        )
        self.original = compose_model_card(
            (self.prior,),
            (self.prior_gate,),
            (self.source,),
        )
        self.original_omission = audit_omissions(
            (self.prior,),
            (self.prior_gate,),
            self.original,
        )
        self.original_fact = run_factreasoner(
            self.original.card,
            CONTRACT_SCHEMA,
            TARGET,
            (self.source,),
            _FactChecker(neutral_field=FIELD),
        )
        field_decision = next(
            item for item in self.original_fact.field_decisions if item.field_path == FIELD
        )
        self.assertIs(field_decision.action, FieldAction.REPAIR_OR_WITHHOLD)

    def _checks(self, candidate, *, value_status=DecisionStatus.ACCEPTED):
        return (
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.ENTITY_SCOPE,
                checker="tests/field-repair-semantic-v1",
                method="bounded_entity_scope",
                status=DecisionStatus.ACCEPTED,
                reason="entity_scope_checked",
            ),
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.FIELD_FIT,
                checker="tests/field-repair-semantic-v1",
                method="bounded_field_fit",
                status=DecisionStatus.ACCEPTED,
                reason="field_fit_checked",
            ),
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.VALUE_SUPPORT,
                checker="tests/field-repair-semantic-v1",
                method="bounded_value_support",
                status=value_status,
                reason=(
                    "complete_value_supported"
                    if value_status is DecisionStatus.ACCEPTED
                    else "complete_value_unsupported"
                ),
            ),
        )

    def _reaudited_submission(self, candidate, *, include_risk=True):
        gate = evaluate_claim_gate(candidate, (self.source,), self._checks(candidate))
        composition = compose_model_card((candidate,), (gate,), (self.source,))
        omission = audit_omissions((candidate,), (gate,), composition)
        fact = run_factreasoner(
            composition.card,
            CONTRACT_SCHEMA,
            TARGET,
            (self.source,),
            _FactChecker(),
        )
        report = _risk_report() if include_risk else None
        return RepairSubmission(
            proposal=RepairProposal(candidate, self._checks(candidate)),
            repaired_composition=composition,
            factreasoner_record=fact,
            omission_audit=omission,
            risk_report=report,
            risk_card_sha256=composition.card_sha256 if include_risk else None,
        )

    def _run(self, submissions):
        return run_field_repair(
            field_path=FIELD,
            predecessor_candidate_id=self.prior.candidate_id,
            candidates=(self.prior,),
            gate_records=(self.prior_gate,),
            sources=(self.source,),
            composition_result=self.original,
            omission_audit=self.original_omission,
            factreasoner_record=self.original_fact,
            submissions=submissions,
        )

    def test_one_field_repair_passes_all_required_reaudits_and_replays(self) -> None:
        candidate = correct_candidate(
            self.prior,
            value=NEW_VALUE,
            evidence=(self.new_evidence,),
        )
        submission = self._reaudited_submission(candidate)
        record = self._run((submission,))

        self.assertIs(record.outcome, RepairOutcome.REPAIRED)
        self.assertIs(record.reason, RepairReason.ALL_CHECKS_PASSED)
        self.assertEqual(record.selected_candidate_id, candidate.candidate_id)
        attempt = record.attempts[0]
        self.assertIs(attempt.disposition, AttemptDisposition.ACCEPTED)
        self.assertEqual(attempt.changed_components, ("value", "evidence"))
        self.assertTrue(attempt.gate_record.projection_eligible)
        self.assertEqual(
            tuple(item.name for item in attempt.downstream_reaudit.checks),
            (
                ReauditName.SCHEMA,
                ReauditName.FACTREASONER,
                ReauditName.OMISSION,
                ReauditName.RISK,
                ReauditName.PRIVACY,
            ),
        )
        self.assertTrue(
            all(
                item.status is ReauditStatus.PASSED
                for item in attempt.downstream_reaudit.checks
            )
        )

        encoded = record.to_dict()
        decoded = FieldRepairRecord.from_dict(deepcopy(encoded))
        self.assertEqual(decoded.to_dict(), encoded)
        verify_field_repair_record(
            decoded,
            field_path=FIELD,
            predecessor_candidate_id=self.prior.candidate_id,
            candidates=(self.prior,),
            gate_records=(self.prior_gate,),
            sources=(self.source,),
            composition_result=self.original,
            omission_audit=self.original_omission,
            factreasoner_record=self.original_fact,
            submissions=(submission,),
        )

        serialized = json.dumps(encoded, sort_keys=True)
        for forbidden in (
            "source_text",
            "source_content",
            "prompt",
            "provider_trace",
            "cost_ledger",
            "/Users/",
            "/private/",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_downstream_failure_is_withheld_then_second_linked_attempt_can_repair(self) -> None:
        first = correct_candidate(
            self.prior,
            value=FIRST_VALUE,
            evidence=(self.first_evidence,),
        )
        first_submission = self._reaudited_submission(first, include_risk=False)
        second = correct_candidate(
            first,
            value=NEW_VALUE,
            evidence=(self.new_evidence,),
        )
        second_submission = self._reaudited_submission(second)
        record = self._run((first_submission, second_submission))

        self.assertIs(record.outcome, RepairOutcome.REPAIRED)
        self.assertIs(record.attempts[0].disposition, AttemptDisposition.REAUDIT_WITHHELD)
        self.assertIs(
            record.attempts[0].reason,
            RepairReason.DOWNSTREAM_REAUDIT_UNAVAILABLE,
        )
        risk = next(
            item
            for item in record.attempts[0].downstream_reaudit.checks
            if item.name is ReauditName.RISK
        )
        self.assertIs(risk.status, ReauditStatus.UNAVAILABLE)
        self.assertEqual(
            record.attempts[1].predecessor_candidate_id,
            first.candidate_id,
        )
        self.assertEqual(record.selected_candidate_id, second.candidate_id)

    def test_two_failed_semantic_attempts_withhold_and_third_is_rejected(self) -> None:
        first = correct_candidate(
            self.prior,
            value=FIRST_VALUE,
            evidence=(self.first_evidence,),
        )
        second = correct_candidate(
            first,
            value=NEW_VALUE,
            evidence=(self.new_evidence,),
        )
        submissions = (
            RepairSubmission(
                proposal=RepairProposal(
                    first,
                    self._checks(first, value_status=DecisionStatus.WITHHELD),
                )
            ),
            RepairSubmission(
                proposal=RepairProposal(
                    second,
                    self._checks(second, value_status=DecisionStatus.WITHHELD),
                )
            ),
        )
        record = self._run(submissions)
        self.assertIs(record.outcome, RepairOutcome.WITHHELD)
        self.assertIs(record.reason, RepairReason.SEMANTIC_ATTEMPT_LIMIT_EXHAUSTED)
        self.assertEqual(len(record.attempts), MAX_SEMANTIC_ATTEMPTS_PER_FIELD)
        self.assertTrue(
            all(
                item.disposition is AttemptDisposition.GATE_WITHHELD
                for item in record.attempts
            )
        )
        with self.assertRaisesRegex(FieldRepairError, "at most two"):
            self._run((*submissions, submissions[-1]))

    def test_no_accepted_field_evidence_creates_explicit_zero_attempt_withhold(self) -> None:
        withheld_gate = evaluate_claim_gate(
            self.prior,
            (self.source,),
            self._checks(self.prior, value_status=DecisionStatus.WITHHELD),
        )
        composition = compose_model_card(
            (self.prior,),
            (withheld_gate,),
            (self.source,),
        )
        omission = audit_omissions((self.prior,), (withheld_gate,), composition)
        fact = run_factreasoner(
            composition.card,
            CONTRACT_SCHEMA,
            TARGET,
            (self.source,),
            _FactChecker(),
        )
        record = run_field_repair(
            field_path=FIELD,
            predecessor_candidate_id=self.prior.candidate_id,
            candidates=(self.prior,),
            gate_records=(withheld_gate,),
            sources=(self.source,),
            composition_result=composition,
            omission_audit=omission,
            factreasoner_record=fact,
            submissions=(),
        )
        self.assertIs(record.outcome, RepairOutcome.WITHHELD)
        self.assertIs(record.reason, RepairReason.NO_ACCEPTED_RELEVANT_EVIDENCE)
        self.assertFalse(record.attempts)
        self.assertFalse(record.context.allowed_evidence_sha256s)

    def test_evidence_is_field_local_and_checker_cannot_silently_mutate_proposal(self) -> None:
        unrelated_binding = quote_binding(
            target=TARGET,
            source=self.source,
            field_path=FIELD,
            value="An unrelated local-looking phrase is deliberately absent from every quote.",
            quote="An unrelated local-looking phrase is deliberately absent from every quote.",
            claim_entity=f"{TARGET.model_id}@{TARGET.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        outside_pool = correct_candidate(
            self.prior,
            value=NEW_VALUE,
            evidence=unrelated_binding.evidence,
        )
        with self.assertRaisesRegex(FieldRepairError, "evidence outside"):
            self._run(
                (
                    RepairSubmission(
                        proposal=RepairProposal(outside_pool, self._checks(outside_pool))
                    ),
                )
            )

        intended = correct_candidate(
            self.prior,
            value=NEW_VALUE,
            evidence=(self.new_evidence,),
        )
        stale_checks = self._checks(intended)
        mutated = ClaimCandidate(
            target=intended.target,
            field_path=intended.field_path,
            value=FIRST_VALUE,
            claim_entity=intended.claim_entity,
            relation=intended.relation,
            evidence=intended.evidence,
            previous_candidate_id=self.prior.candidate_id,
        )
        with self.assertRaisesRegex(ValueError, "stale checker decision"):
            self._run(
                (
                    RepairSubmission(
                        proposal=RepairProposal(mutated, stale_checks),
                    ),
                )
            )

        changed_field = correct_candidate(
            self.prior,
            field_path="identity.name",
            value="Repair 1B",
        )
        with self.assertRaisesRegex(FieldRepairError, "changes fields"):
            self._run(
                (
                    RepairSubmission(
                        proposal=RepairProposal(changed_field, self._checks(changed_field)),
                    ),
                )
            )

        local_path = correct_candidate(
            self.prior,
            value="Internal output at /Users/example/private/result.json",
            evidence=(self.new_evidence,),
        )
        with self.assertRaisesRegex(FieldRepairError, "private or local-path"):
            RepairProposal(local_path, self._checks(local_path))

    def test_serialized_tampering_and_source_drift_fail_closed(self) -> None:
        candidate = correct_candidate(
            self.prior,
            value=NEW_VALUE,
            evidence=(self.new_evidence,),
        )
        submission = self._reaudited_submission(candidate)
        record = self._run((submission,))
        tampered = deepcopy(record.to_dict())
        tampered["attempts"][0]["proposal"]["candidate"]["value"] = "silently rewritten"
        with self.assertRaises(ValueError):
            FieldRepairRecord.from_dict(tampered)

        drifted = SourceDocument(
            source_id=self.source.source_id,
            source_uri=self.source.source_uri,
            role=self.source.role,
            source_revision=self.source.source_revision,
            target=self.source.target,
            synthetic=True,
            text=self.source.text + "\nDrift.",
        )
        with self.assertRaises(ValueError):
            verify_field_repair_record(
                record,
                field_path=FIELD,
                predecessor_candidate_id=self.prior.candidate_id,
                candidates=(self.prior,),
                gate_records=(self.prior_gate,),
                sources=(drifted,),
                composition_result=self.original,
                omission_audit=self.original_omission,
                factreasoner_record=self.original_fact,
                submissions=(submission,),
            )


if __name__ == "__main__":
    unittest.main()
