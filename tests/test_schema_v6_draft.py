from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "model-card-v6-draft.schema.json"


class SchemaV6DraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_adds_use_and_risk_to_the_v5_sections(self) -> None:
        expected_sections = {
            "identity",
            "lineage",
            "specifications",
            "training_context",
            "access_and_adoption",
            "evaluation",
            "links",
            "use_and_risk",
            "provenance_and_quality",
        }
        self.assertEqual(set(self.schema["required"]), expected_sections)
        self.assertEqual(
            self.schema["$defs"]["provenanceAndQuality"]["properties"]["card_info"],
            {"$ref": "#/$defs/cardInfo"},
        )
        card_info = self.schema["$defs"]["cardInfo"]
        self.assertFalse(card_info["additionalProperties"])
        self.assertEqual(card_info["properties"]["schema_version"]["const"], "6")
        self.assertEqual(
            self.schema["$defs"]["provenanceAndQuality"]["properties"]["provenance"]
            ["$ref"],
            "#/$defs/publicProvenance",
        )

        use_and_risk = self.schema["$defs"]["useAndRisk"]
        self.assertEqual(
            set(use_and_risk["required"]),
            {
                "schema_version",
                "intended_uses",
                "out_of_scope_uses",
                "limitations",
                "known_biases",
                "identified_risks",
                "mitigations",
            },
        )

    def test_risks_retain_origin_taxonomy_grounding_and_review_state(self) -> None:
        risk = self.schema["$defs"]["risk"]
        required = set(risk["required"])
        for field in (
            "risk_id",
            "identification_origin",
            "taxonomy",
            "applicability_rationale",
            "grounds",
            "mapping_provenance",
            "review_status",
            "mitigation_refs",
        ):
            self.assertIn(field, required)

        self.assertEqual(
            set(risk["properties"]["identification_origin"]["enum"]),
            {"publisher_reported", "taxonomy_identified"},
        )
        self.assertEqual(
            set(risk["properties"]["review_status"]["enum"]),
            {"candidate", "reviewed", "rejected"},
        )
        taxonomy = self.schema["$defs"]["taxonomyReference"]
        self.assertIn("version", taxonomy["required"])
        self.assertIn("snapshot_sha256", taxonomy["required"])
        mapping = self.schema["$defs"]["mappingProvenance"]
        self.assertEqual(
            set(mapping["required"]),
            {
                "method",
                "tool_version",
                "inference_model",
                "inference_config_sha256",
            },
        )
        source_reference = self.schema["$defs"]["publicSourceReference"]
        self.assertEqual(
            set(source_reference["required"]),
            {
                "source_id",
                "source_uri",
                "source_revision",
                "source_sha256",
                "locator",
                "claimed_entity",
                "relation",
            },
        )
        self.assertEqual(
            source_reference["properties"]["locator"]["$ref"],
            "#/$defs/publicLocator",
        )

    def test_all_internal_definition_references_resolve(self) -> None:
        definitions = self.schema["$defs"]
        unresolved: list[str] = []

        def visit(value: object) -> None:
            if isinstance(value, dict):
                reference = value.get("$ref")
                if isinstance(reference, str) and reference.startswith("#/$defs/"):
                    if reference.removeprefix("#/$defs/") not in definitions:
                        unresolved.append(reference)
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(self.schema)
        self.assertEqual(unresolved, [])


if __name__ == "__main__":
    unittest.main()
