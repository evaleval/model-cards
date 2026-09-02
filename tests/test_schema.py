from __future__ import annotations

from copy import deepcopy
import unittest

from jsonschema import Draft202012Validator

from model_cards.schema import (
    CONTRACT_SCHEMA,
    FIELD_PATHS,
    NOT_SPECIFIED,
    blank_card,
    canonical_field_path,
    get_field,
    set_field,
    validate_field_value,
    validate_public_card,
)


class SchemaTests(unittest.TestCase):
    def _minimal_card(self):
        card = blank_card()
        card["identity"]["model_id"] = "example/model"
        card["identity"]["revision"] = "a" * 40
        return card

    def test_contract_paths_are_derived_and_defaults_are_honest(self) -> None:
        self.assertEqual(len(FIELD_PATHS), 47)
        self.assertIn("environmental_information.carbon_emissions", FIELD_PATHS)
        self.assertIn("use_and_risk.identified_risks", FIELD_PATHS)
        card = self._minimal_card()
        self.assertEqual(
            get_field(card, "environmental_information.carbon_emissions"),
            NOT_SPECIFIED,
        )
        validate_public_card(card)

    def test_indexed_paths_use_the_same_benchmark_subschema(self) -> None:
        card = self._minimal_card()
        row = {"benchmark": "Toy", "metric": "accuracy", "score": 1, "setting": "reported"}
        set_field(card, "evaluation.benchmark_scores[0]", row)
        self.assertEqual(get_field(card, "evaluation.benchmark_scores[0]"), row)
        self.assertEqual(
            canonical_field_path("evaluation.benchmark_scores[0]"),
            "evaluation.benchmark_scores",
        )
        validate_public_card(card)

    def test_unknown_and_non_list_paths_are_rejected(self) -> None:
        for field_path in (
            "evaluation.imaginary_field",
            "identity.name[0]",
            "evaluation.evaluation_sources[00]",
        ):
            with self.subTest(field_path=field_path), self.assertRaises(ValueError):
                get_field(self._minimal_card(), field_path)

    def test_field_and_whole_card_validation_share_the_contract(self) -> None:
        with self.assertRaises(ValueError):
            validate_field_value("identity.name", {"not": "a scalar"})
        card = self._minimal_card()
        card["identity"]["name"] = {"not": "a scalar"}
        with self.assertRaises(ValueError):
            validate_public_card(card)

    def test_benchmark_rows_require_setting_and_reject_extra_keys(self) -> None:
        for row in (
            {"benchmark": "Toy", "metric": "accuracy", "score": 1},
            {
                "benchmark": "Toy",
                "metric": "accuracy",
                "score": 1,
                "setting": "reported",
                "private": "text",
            },
        ):
            with self.subTest(row=row), self.assertRaises(ValueError):
                validate_field_value("evaluation.benchmark_scores[0]", row)

    def test_additional_sections_and_unsafe_lifecycle_labels_fail(self) -> None:
        for mutate in (
            lambda card: card.update({"private": {}}),
            lambda card: card["lifecycle"].update({"status": "human_reviewed"}),
            lambda card: card["lifecycle"].update({"status": "released"}),
        ):
            card = self._minimal_card()
            mutate(card)
            with self.assertRaises(ValueError):
                validate_public_card(card)

    def test_lifecycle_and_validation_summary_cannot_disagree(self) -> None:
        missing_gates = self._minimal_card()
        missing_gates["lifecycle"]["status"] = "generated_validated"
        missing_gates["validation"]["overall_status"] = "passed"
        self.assertTrue(list(Draft202012Validator(CONTRACT_SCHEMA).iter_errors(missing_gates)))
        with self.assertRaises(ValueError):
            validate_public_card(missing_gates)

        unreviewed_pass = self._minimal_card()
        unreviewed_pass["validation"]["overall_status"] = "passed"
        self.assertTrue(list(Draft202012Validator(CONTRACT_SCHEMA).iter_errors(unreviewed_pass)))

    def test_generated_validated_requires_closed_gate_counts(self) -> None:
        card = self._minimal_card()
        card["lifecycle"]["status"] = "generated_validated"
        card["validation"]["overall_status"] = "passed"
        card["validation"]["checks"] = {
            "claim_support": {
                "status": "completed",
                "checked": 5,
                "passed": 1,
                "withheld": 0,
                "failed": 0,
                "unavailable": 0,
            },
            "privacy": {
                "status": "completed",
                "checked": 1,
                "passed": 1,
                "withheld": 0,
                "failed": 0,
                "unavailable": 0,
            },
        }
        self.assertEqual(list(Draft202012Validator(CONTRACT_SCHEMA).iter_errors(card)), [])
        with self.assertRaisesRegex(ValueError, "outcomes do not cover"):
            validate_public_card(card)

    def test_contract_object_is_not_aliased_by_callers(self) -> None:
        copied = deepcopy(CONTRACT_SCHEMA)
        copied["title"] = "changed"
        self.assertNotEqual(copied, CONTRACT_SCHEMA)


if __name__ == "__main__":
    unittest.main()
