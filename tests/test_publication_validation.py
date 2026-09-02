from __future__ import annotations

from copy import deepcopy
import unittest

from model_cards.factreasoner import (
    CheckOutcome,
    CheckerResponse,
    FieldAction,
    run_factreasoner,
)
from model_cards.models import SourceDocument, SourceRole, TargetIdentity
from model_cards.publication_contract import FIELD_PATHS
from model_cards.publication_schema import (
    PUBLICATION_SCHEMA,
    blank_publication_card,
    validate_publication_card,
)
from model_cards.publication_validation import (
    PublicationFieldReason,
    PublicationValidationError,
    PublicationValidationReplayError,
    PublicationValidationReport,
    audit_publication_fields,
    remove_publication_fields,
    repair_or_withhold_publication_fields,
    replay_publication_validation,
    run_publication_validation,
)


TARGET = TargetIdentity("acme/Example-Instruct", "a" * 40)


class PublicationChecker:
    checker_id = "tests/publication-checker"
    checker_revision = "tests-publication-v1"

    def check(self, request):
        if request.atom.field_path == "identity.summary":
            return CheckerResponse(
                outcome=CheckOutcome.CONTRADICTION,
                reason_code="fixture_contradiction",
                cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
            )
        if request.atom.field_path == "identity.developed_by":
            return CheckerResponse(
                outcome=CheckOutcome.UNAVAILABLE,
                reason_code="fixture_unavailable",
            )
        return CheckerResponse(
            outcome=CheckOutcome.SUPPORT,
            reason_code="fixture_support",
            cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
        )


def publication_card(*, expanded: bool = True):
    card = blank_publication_card(include_unknown_fields=expanded)
    card["identity"].update(
        {
            "model_id": TARGET.model_id,
            "version": TARGET.revision,
            "developed_by": "Acme Research",
            "summary": "The released model has 99 billion parameters.",
        }
    )
    validate_publication_card(card)
    return card


def factreasoner_record(card):
    source = SourceDocument(
        source_id="publication-source",
        source_uri="https://example.org/model-card",
        role=SourceRole.DEVELOPER_REPORT,
        source_revision="report-v1",
        target=TARGET,
        text=(
            "Acme Research publishes acme/Example-Instruct at revision "
            f"{TARGET.revision}. The released model has 7 billion parameters. "
            "This retained source is deliberately long enough for bounded retrieval."
        ),
    )
    return run_factreasoner(
        card,
        PUBLICATION_SCHEMA,
        TARGET,
        (source,),
        PublicationChecker(),
    )


class PublicationValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pre = publication_card()
        self.fact = factreasoner_record(self.pre)

    def test_only_material_repair_decisions_are_selected_and_removed(self) -> None:
        actions = {
            item.field_path: item.action for item in self.fact.field_decisions
        }
        self.assertIs(
            actions["identity.summary"], FieldAction.REPAIR_OR_WITHHOLD
        )
        self.assertIs(
            actions["identity.developed_by"], FieldAction.COLLECT_OR_WITHHOLD
        )

        fields = repair_or_withhold_publication_fields(self.fact)
        self.assertEqual(("identity.summary",), fields)
        final = remove_publication_fields(self.pre, fields)

        self.assertNotIn("summary", final["identity"])
        self.assertEqual("Acme Research", final["identity"]["developed_by"])
        validate_publication_card(final)

    def test_sparse_field_removal_is_deletion_only_and_non_mutating(self) -> None:
        sparse = publication_card(expanded=False)
        before = deepcopy(sparse)

        final = remove_publication_fields(sparse, ("identity.summary",))

        self.assertEqual(before, sparse)
        self.assertNotIn("summary", final["identity"])
        with self.assertRaisesRegex(PublicationValidationError, "absent"):
            remove_publication_fields(final, ("identity.summary",))
        with self.assertRaisesRegex(PublicationValidationError, "unique"):
            remove_publication_fields(
                sparse, ("identity.summary", "identity.summary")
            )

    def test_audit_accounts_for_all_33_fields_with_closed_reasons(self) -> None:
        final = remove_publication_fields(self.pre, ("identity.summary",))

        records = audit_publication_fields(self.pre, final)

        self.assertEqual(FIELD_PATHS, tuple(item.field_path for item in records))
        by_path = {item.field_path: item for item in records}
        self.assertIs(
            by_path["identity.summary"].reason,
            PublicationFieldReason.WITHHELD,
        )
        self.assertTrue(by_path["identity.summary"].source_present)
        self.assertIs(
            by_path["identity.developed_by"].reason,
            PublicationFieldReason.PRESENT,
        )
        self.assertIs(
            by_path["links.system_card"].reason,
            PublicationFieldReason.NOT_FOUND,
        )
        self.assertFalse(by_path["links.system_card"].source_present)

        changed = deepcopy(final)
        changed["identity"]["developed_by"] = "Different developer"
        with self.assertRaisesRegex(PublicationValidationError, "added or changed"):
            audit_publication_fields(self.pre, changed)

    def test_report_roundtrips_and_replays_without_checker_calls(self) -> None:
        outcome = run_publication_validation(self.pre, self.fact)
        encoded = outcome.report.to_dict()

        restored = PublicationValidationReport.from_dict(deepcopy(encoded))
        replayed = replay_publication_validation(restored, self.pre, self.fact)

        self.assertEqual(encoded, restored.to_dict())
        self.assertEqual(outcome.final_card, replayed.final_card)
        self.assertEqual(("identity.summary",), restored.withheld_field_paths)
        self.assertEqual(
            restored.withheld_field_paths, restored.source_present_omissions
        )
        self.assertEqual(33, len(restored.records))

    def test_report_and_replay_fail_closed_on_tampering(self) -> None:
        outcome = run_publication_validation(self.pre, self.fact)
        encoded = outcome.report.to_dict()
        encoded["report_sha256"] = "0" * 64
        with self.assertRaisesRegex(PublicationValidationError, "digest mismatch"):
            PublicationValidationReport.from_dict(encoded)

        changed = deepcopy(self.pre)
        changed["identity"]["summary"] = "A changed unsupported claim."
        with self.assertRaises(PublicationValidationReplayError):
            replay_publication_validation(outcome.report, changed, self.fact)

        outcome.final_card["identity"]["developed_by"] = "Mutated"
        with self.assertRaisesRegex(PublicationValidationError, "integrity"):
            outcome.validate_integrity()


if __name__ == "__main__":
    unittest.main()
