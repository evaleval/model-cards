from __future__ import annotations

from copy import deepcopy
import unittest

from jsonschema import Draft202012Validator

from model_cards.publication_contract import (
    FIELD_PATHS,
    LIST_FIELDS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    PUBLICATION_SECTIONS,
    SECTION_FIELDS,
    build_publication_schema,
)
from model_cards.publication_schema import (
    PUBLICATION_SCHEMA,
    blank_publication_card,
    canonical_field_path,
    get_field,
    load_publication_schema,
    publication_coverage,
    set_field,
    validate_field_value,
    validate_publication_card,
)


EXPECTED_FIELDS = {
    "identity": (
        "model_id",
        "name",
        "developed_by",
        "model_type",
        "license",
        "release_date",
        "version",
        "summary",
    ),
    "lineage": ("base_models", "model_family", "derivatives"),
    "specifications": (
        "architecture_type",
        "num_parameters",
        "context_length",
        "precision",
        "model_size",
        "input_output",
    ),
    "training_context": (
        "training_data",
        "training_data_size",
        "data_cutoff",
        "adaptations",
    ),
    "access_and_adoption": ("access_type", "downloads", "likes"),
    "evaluation": (
        "results_summary",
        "benchmark_scores",
        "human_evals",
        "safety_evals",
    ),
    "links": (
        "model_card",
        "system_card",
        "tech_report",
        "code_repository",
        "citation",
    ),
}


class PublicationSchemaTests(unittest.TestCase):
    def test_schema_has_exact_agreed_sections_and_fields(self) -> None:
        self.assertEqual(SECTION_FIELDS, EXPECTED_FIELDS)
        self.assertEqual(PUBLICATION_SECTIONS, tuple(EXPECTED_FIELDS))
        self.assertEqual(len(FIELD_PATHS), 33)
        self.assertEqual(
            PUBLICATION_SCHEMA["required"],
            list(EXPECTED_FIELDS),
        )
        self.assertFalse(PUBLICATION_SCHEMA["additionalProperties"])
        for section, fields in EXPECTED_FIELDS.items():
            definition = PUBLICATION_SCHEMA["$defs"][section]
            self.assertEqual(tuple(definition["properties"]), fields)
            self.assertNotIn("required", definition)
            self.assertFalse(definition["additionalProperties"])

        forbidden = {
            "contract_version",
            "provenance",
            "validation",
            "lifecycle",
            "environmental_information",
            "use_and_risk",
        }
        self.assertTrue(forbidden.isdisjoint(PUBLICATION_SCHEMA["properties"]))

    def test_schema_builder_is_valid_and_returns_fresh_values(self) -> None:
        schema = build_publication_schema()
        Draft202012Validator.check_schema(schema)
        self.assertEqual(schema, load_publication_schema())
        schema["$defs"]["identity"]["properties"].clear()
        self.assertIn("model_id", build_publication_schema()["$defs"]["identity"]["properties"])

    def test_blank_card_has_sections_without_placeholder_wall(self) -> None:
        card = blank_publication_card()
        self.assertEqual(card, {section: {} for section in EXPECTED_FIELDS})
        validate_publication_card(card)
        self.assertEqual(publication_coverage(card), 0.0)

        expanded = blank_publication_card(include_unknown_fields=True)
        self.assertEqual(expanded["identity"]["version"], NOT_SPECIFIED)
        self.assertEqual(expanded["links"]["citation"], NOT_SPECIFIED)
        validate_publication_card(expanded)

    def test_unknown_sections_and_fields_are_rejected(self) -> None:
        for mutate in (
            lambda card: card.update({"environmental_information": {}}),
            lambda card: card["identity"].update({"revision": "abc"}),
            lambda card: card["links"].update({"technical_report": "https://example.test"}),
        ):
            card = blank_publication_card()
            mutate(card)
            with self.subTest(card=card), self.assertRaises(ValueError):
                validate_publication_card(card)

    def test_sections_are_required_but_fields_may_be_omitted(self) -> None:
        card = blank_publication_card()
        del card["training_context"]
        with self.assertRaises(ValueError):
            validate_publication_card(card)

        card = blank_publication_card()
        card["identity"]["model_id"] = NOT_SPECIFIED
        card["lineage"]["base_models"] = NOT_APPLICABLE
        validate_publication_card(card)

    def test_exact_hf_and_openrouter_like_ids_and_typed_references(self) -> None:
        card = blank_publication_card()
        card["identity"]["model_id"] = "deepseek/deepseek-v4-flash-0731"
        card["identity"]["version"] = "0731"
        card["lineage"]["base_models"] = [
            {
                "model_id": "deepseek-ai/DeepSeek-V3",
                "relation": "base_model",
                "version": "main",
            }
        ]
        card["lineage"]["derivatives"] = [
            {
                "model_id": "example/org/model",
                "relation": "derivative_model",
                "kind": "fine-tune",
            }
        ]
        validate_publication_card(card)

        card["identity"]["model_id"] = "no-slash"
        with self.assertRaises(ValueError):
            validate_publication_card(card)

        card = blank_publication_card()
        card["lineage"]["base_models"] = [
            {"model_id": "example/child", "relation": "derivative_model"}
        ]
        with self.assertRaises(ValueError):
            validate_publication_card(card)

    def test_benchmark_rows_are_typed_and_closed(self) -> None:
        row = {
            "benchmark": "MMLU",
            "metric": "accuracy",
            "score": 0.71,
            "setting": "5-shot",
            "split": "test",
        }
        validate_field_value("evaluation.benchmark_scores[0]", row)

        for invalid in (
            {"benchmark": "MMLU", "metric": "accuracy", "score": 0.71},
            {**row, "private_source": "local bundle"},
            {**row, "score": True},
            {**row, "setting": {"lifecycle": {"status": "released"}}},
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_field_value("evaluation.benchmark_scores[0]", invalid)

    def test_field_helpers_support_omission_and_list_items(self) -> None:
        self.assertEqual(
            LIST_FIELDS,
            {
                "lineage.base_models",
                "lineage.derivatives",
                "specifications.input_output",
                "evaluation.benchmark_scores",
            },
        )
        card = blank_publication_card()
        self.assertEqual(get_field(card, "identity.name", NOT_SPECIFIED), NOT_SPECIFIED)
        set_field(card, "identity.name", "DeepSeek V4 Flash")
        set_field(card, "specifications.input_output[0]", "input: text")
        set_field(card, "specifications.input_output[1]", "output: text")
        self.assertEqual(get_field(card, "identity.name"), "DeepSeek V4 Flash")
        self.assertEqual(
            get_field(card, "specifications.input_output[1]"),
            "output: text",
        )
        self.assertEqual(
            canonical_field_path("specifications.input_output[1]"),
            "specifications.input_output",
        )
        with self.assertRaises(ValueError):
            get_field(card, "identity.name[0]")
        validate_publication_card(card)

    def test_coverage_is_deterministic_and_does_not_count_absence(self) -> None:
        card = blank_publication_card()
        card["identity"].update(
            {
                "model_id": "allenai/OLMo-2-1124-7B",
                "name": "OLMo 2 7B",
                "release_date": NOT_SPECIFIED,
            }
        )
        card["lineage"]["derivatives"] = NOT_APPLICABLE
        card["specifications"]["input_output"] = ["input: text", "output: text"]
        expected = round(3 / 33, 6)
        self.assertEqual(publication_coverage(card), expected)
        self.assertEqual(publication_coverage(deepcopy(card)), expected)

    def test_public_and_local_audit_schema_identities_are_distinct(self) -> None:
        from model_cards.schema import CONTRACT_SCHEMA

        self.assertNotEqual(PUBLICATION_SCHEMA["$id"], CONTRACT_SCHEMA["$id"])
        self.assertEqual(
            "urn:evaleval:model-cards:local-audit-card:v1",
            CONTRACT_SCHEMA["$id"],
        )


if __name__ == "__main__":
    unittest.main()
