from __future__ import annotations

import unittest

from model_cards.schema import (
    NOT_SPECIFIED,
    SCHEMA_V5_FIELD_PATHS,
    blank_card,
    canonical_field_path,
    get_field,
    set_field,
    validate_complete_card,
)


class SchemaTests(unittest.TestCase):
    def test_v5_has_exactly_38_fields(self) -> None:
        card = blank_card()
        validate_complete_card(card)
        self.assertEqual(len(SCHEMA_V5_FIELD_PATHS), 38)
        self.assertTrue(all(get_field(card, path) == NOT_SPECIFIED for path in SCHEMA_V5_FIELD_PATHS))

    def test_indexed_paths_are_values_within_canonical_fields(self) -> None:
        card = blank_card()
        row = {"benchmark": "Toy", "metric": "accuracy", "score": 1, "setting": "reported"}
        set_field(card, "evaluation.benchmark_scores[0]", row)
        self.assertEqual(get_field(card, "evaluation.benchmark_scores[0]"), row)
        self.assertEqual(
            canonical_field_path("evaluation.benchmark_scores[0]"),
            "evaluation.benchmark_scores",
        )
        validate_complete_card(card)

    def test_unknown_field_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            get_field(blank_card(), "evaluation.imaginary_field")

    def test_scalar_indexes_and_noncanonical_indexes_are_rejected(self) -> None:
        for field_path in ("identity.name[0]", "evaluation.evaluation_sources[00]"):
            with self.subTest(field_path=field_path):
                with self.assertRaises(ValueError):
                    get_field(blank_card(), field_path)

    def test_complete_card_enforces_field_types(self) -> None:
        card = blank_card()
        card["identity"]["name"] = {"not": "a scalar"}
        with self.assertRaises(ValueError):
            validate_complete_card(card)

    def test_benchmark_rows_require_an_explicit_setting(self) -> None:
        card = blank_card()
        with self.assertRaises(ValueError):
            set_field(
                card,
                "evaluation.benchmark_scores[0]",
                {"benchmark": "Toy", "metric": "accuracy", "score": 1},
            )


if __name__ == "__main__":
    unittest.main()
