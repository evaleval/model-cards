from __future__ import annotations

from copy import deepcopy
import unittest

from model_cards.bindings import source_from_dict, structured_binding
from model_cards.claim_gate import ClaimCandidate, evaluate_claim_gate
from model_cards.composer import WriterSelection, compose_model_card
from model_cards.findings import (
    FieldAuditStatus,
    FieldAvailabilityHint,
    FieldAvailabilityStatus,
    FindingError,
    OmissionAudit,
    OmissionReason,
    audit_omissions,
    verify_omission_audit,
)
from model_cards.models import RelationToTarget, SourceDocument, SourceRole
from model_cards.schema import CONTENT_FIELD_PATHS
from tests.helpers import synthetic_artifact, synthetic_specification


class _SelectNoneWriter:
    def select(self, writer_input):
        return WriterSelection(())


class FindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = synthetic_artifact()
        self.target = self.artifact.target
        self.sources = tuple(
            source_from_dict(item) for item in synthetic_specification()["sources"]
        )

    def candidate(self, field_path):
        binding = next(
            item for item in self.artifact.bindings if item.field_path == field_path
        )
        return ClaimCandidate.from_binding(self.target, binding)

    @staticmethod
    def field(audit, field_path):
        return next(item for item in audit.records if item.field_path == field_path)

    def basic_inventory(self):
        included = self.candidate("identity.name")
        withheld = self.candidate("identity.summary")
        records = (
            evaluate_claim_gate(included, self.sources),
            evaluate_claim_gate(withheld, self.sources),
        )
        result = compose_model_card((included, withheld), records, self.sources)
        return (included, withheld), records, result

    def test_audit_covers_every_content_field_and_detects_withheld_source_presence(self) -> None:
        candidates, records, result = self.basic_inventory()
        audit = audit_omissions(candidates, records, result)

        self.assertEqual(
            tuple(item.field_path for item in audit.records),
            tuple(CONTENT_FIELD_PATHS),
        )
        self.assertEqual(len(audit.records), len(CONTENT_FIELD_PATHS))
        name = self.field(audit, "identity.name")
        self.assertEqual(name.status, FieldAuditStatus.PRESENT)
        self.assertIsNone(name.reason)
        summary = self.field(audit, "identity.summary")
        self.assertEqual(summary.status, FieldAuditStatus.OMITTED)
        self.assertEqual(summary.reason, OmissionReason.WITHHELD)
        self.assertTrue(summary.source_present)
        self.assertIn("identity.summary", audit.source_present_omissions)

        non_core = self.field(audit, "environmental_information.carbon_emissions")
        self.assertEqual(non_core.status, FieldAuditStatus.OMITTED)
        self.assertEqual(non_core.reason, OmissionReason.NOT_FOUND)
        self.assertFalse(non_core.source_present)

    def test_field_scoped_unavailability_does_not_excuse_other_fields(self) -> None:
        candidates, records, result = self.basic_inventory()
        unavailable = FieldAvailabilityHint(
            field_path="environmental_information.hardware",
            status=FieldAvailabilityStatus.SOURCE_UNAVAILABLE,
            source_ids=("source-hardware",),
        )
        audit = audit_omissions(candidates, records, result, (unavailable,))
        hardware = self.field(audit, "environmental_information.hardware")
        energy = self.field(audit, "environmental_information.energy_consumption")

        self.assertEqual(hardware.reason, OmissionReason.SOURCE_UNAVAILABLE)
        self.assertEqual(energy.reason, OmissionReason.NOT_FOUND)
        self.assertFalse(hardware.source_present)
        self.assertFalse(energy.source_present)

    def test_source_present_without_candidate_is_missed_by_composition(self) -> None:
        candidates, records, result = self.basic_inventory()
        hint = FieldAvailabilityHint(
            field_path="use_and_risk.limitations",
            status=FieldAvailabilityStatus.SOURCE_PRESENT,
            source_ids=("source-limitations",),
        )
        audit = audit_omissions(candidates, records, result, (hint,))
        finding = self.field(audit, "use_and_risk.limitations")
        self.assertEqual(finding.reason, OmissionReason.MISSED_BY_COMPOSITION)
        self.assertTrue(finding.source_present)
        self.assertIn(finding.field_path, audit.source_present_omissions)

    def test_not_applicable_and_searched_not_found_are_closed_field_reasons(self) -> None:
        candidates, records, result = self.basic_inventory()
        hints = (
            FieldAvailabilityHint(
                field_path="environmental_information.training_time",
                status=FieldAvailabilityStatus.NOT_APPLICABLE,
            ),
            FieldAvailabilityHint(
                field_path="use_and_risk.known_biases",
                status=FieldAvailabilityStatus.SEARCHED_NOT_FOUND,
                source_ids=("source-search",),
            ),
        )
        audit = audit_omissions(candidates, records, result, hints)
        self.assertEqual(
            self.field(audit, "environmental_information.training_time").reason,
            OmissionReason.NOT_APPLICABLE,
        )
        self.assertEqual(
            self.field(audit, "use_and_risk.known_biases").reason,
            OmissionReason.NOT_FOUND,
        )

    def test_eligible_writer_omission_is_missed_by_composition(self) -> None:
        candidate = self.candidate("identity.name")
        record = evaluate_claim_gate(candidate, self.sources)
        result = compose_model_card(
            (candidate,),
            (record,),
            self.sources,
            writer=_SelectNoneWriter(),
        )
        audit = audit_omissions((candidate,), (record,), result)
        finding = self.field(audit, "identity.name")
        self.assertEqual(finding.reason, OmissionReason.MISSED_BY_COMPOSITION)
        self.assertTrue(finding.source_present)
        self.assertEqual(finding.included_candidate_ids, ())

    def test_conflict_is_explicit_in_composition_and_omission_record(self) -> None:
        sources = []
        candidates = []
        for index, name in ((1, "First Name"), (2, "Second Name")):
            source = SourceDocument(
                source_id=f"synthetic-name-conflict-{index}",
                source_uri=f"hf://{self.target.model_id}@{self.target.revision}/metadata-{index}.json",
                role=SourceRole.HUGGING_FACE_METADATA,
                source_revision=self.target.revision,
                target=self.target,
                synthetic=True,
                data={"display_name": name},
            )
            binding = structured_binding(
                target=self.target,
                source=source,
                field_path="identity.name",
                pointer="/display_name",
                claim_entity=f"{self.target.model_id}@{self.target.revision}",
                relation=RelationToTarget.EXACT_TARGET,
            )
            sources.append(source)
            candidates.append(ClaimCandidate.from_binding(self.target, binding))
        all_sources = (*self.sources, *sources)
        records = tuple(evaluate_claim_gate(item, all_sources) for item in candidates)
        result = compose_model_card(candidates, records, all_sources)
        audit = audit_omissions(candidates, records, result)
        finding = self.field(audit, "identity.name")

        self.assertEqual(finding.reason, OmissionReason.CONFLICTING)
        self.assertTrue(finding.source_present)
        self.assertEqual(
            finding.conflict_sha256s,
            tuple(item.content_sha256 for item in result.plan.conflicts),
        )
        self.assertEqual(set(finding.candidate_ids), {item.candidate_id for item in candidates})

    def test_audit_round_trip_replay_and_tamper_are_strict(self) -> None:
        candidates, records, result = self.basic_inventory()
        hints = (
            FieldAvailabilityHint(
                field_path="use_and_risk.out_of_scope_uses",
                status=FieldAvailabilityStatus.SOURCE_PRESENT,
                source_ids=("source-out-of-scope",),
            ),
        )
        audit = audit_omissions(candidates, records, result, hints)
        encoded = audit.to_dict()
        decoded = OmissionAudit.from_dict(deepcopy(encoded))
        self.assertEqual(decoded.to_dict(), encoded)
        verify_omission_audit(decoded, candidates, records, result, hints)

        tampered = deepcopy(encoded)
        record = next(
            item for item in tampered["records"] if item["field_path"] == "identity.summary"
        )
        record["reason"] = "not_found"
        with self.assertRaises(FindingError):
            OmissionAudit.from_dict(tampered)

        with self.assertRaises(FindingError):
            audit_omissions(candidates, records, result, (*hints, hints[0]))

        other_result = compose_model_card(
            candidates,
            records,
            self.sources,
            writer=_SelectNoneWriter(),
        )
        with self.assertRaises(FindingError):
            verify_omission_audit(decoded, candidates, records, other_result, hints)

    def test_all_omission_reasons_are_closed(self) -> None:
        self.assertEqual(
            {item.value for item in OmissionReason},
            {
                "not_found",
                "source_unavailable",
                "not_applicable",
                "conflicting",
                "withheld",
                "missed_by_composition",
            },
        )


if __name__ == "__main__":
    unittest.main()
