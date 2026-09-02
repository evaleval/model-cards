from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from model_cards._schema_sync import audit_schema_text, schema_text
from model_cards.contract import build_contract_schema
from model_cards.models import (
    LifecycleStatus,
    RelationToTarget,
    SourceRole,
    ValidationCheckStatus,
)
from model_cards.schema import load_contract_schema
from model_cards.publication_contract import build_publication_schema
from model_cards.publication_schema import PUBLICATION_SCHEMA


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SCHEMA = ROOT / "schema" / "model-card.schema.json"
PACKAGED_SCHEMA = ROOT / "src" / "model_cards" / "resources" / "model-card.schema.json"
PACKAGED_AUDIT_SCHEMA = ROOT / "src" / "model_cards" / "resources" / "audit-card.schema.json"


class ModelCardSchemaTests(unittest.TestCase):
    def test_generated_public_and_packaged_schemas_are_identical(self) -> None:
        generated = schema_text()
        self.assertEqual(PUBLIC_SCHEMA.read_text(encoding="utf-8"), generated)
        self.assertEqual(PACKAGED_SCHEMA.read_text(encoding="utf-8"), generated)
        self.assertEqual(PUBLICATION_SCHEMA, build_publication_schema())
        self.assertEqual(
            PACKAGED_AUDIT_SCHEMA.read_text(encoding="utf-8"),
            audit_schema_text(),
        )
        self.assertEqual(load_contract_schema(), build_contract_schema())

    def test_is_a_real_draft_2020_12_schema(self) -> None:
        schema = json.loads(PUBLIC_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        Draft202012Validator.check_schema(schema)

    def test_defines_the_richer_private_audit_contract(self) -> None:
        schema = build_contract_schema()
        self.assertEqual(
            set(schema["required"]),
            {
                "contract_version",
                "identity",
                "lineage",
                "model_details",
                "training",
                "evaluation",
                "environmental_information",
                "use_and_risk",
                "provenance",
                "validation",
                "lifecycle",
            },
        )
        self.assertEqual(schema["properties"]["contract_version"]["const"], "1")
        self.assertEqual(
            set(schema["$defs"]["lifecycle"]["properties"]["status"]["enum"]),
            {"generated_unreviewed", "generated_validated"},
        )

    def test_public_schema_is_exactly_the_agreed_seven_sections(self) -> None:
        schema = build_publication_schema()
        self.assertEqual(
            schema["required"],
            [
                "identity",
                "lineage",
                "specifications",
                "training_context",
                "access_and_adoption",
                "evaluation",
                "links",
            ],
        )
        self.assertNotIn("environmental_information", schema["properties"])
        self.assertNotIn("use_and_risk", schema["properties"])
        self.assertNotIn("provenance", schema["properties"])

    def test_risk_and_source_records_use_automated_status_and_portable_uris(self) -> None:
        definitions = build_contract_schema()["$defs"]
        self.assertEqual(
            set(definitions["risk"]["properties"]["review_status"]["enum"]),
            {"generated_unreviewed", "generated_validated", "rejected"},
        )
        manifest = definitions["provenance"]["properties"]["source_manifest"]
        self.assertEqual(manifest["additionalProperties"], {"$ref": "#/$defs/publicSourceReference"})
        self.assertIn("source_uri", definitions["fieldReference"]["required"])
        self.assertIn("source_uri", definitions["publicSourceReference"]["required"])

    def test_python_types_match_the_canonical_contract_enums(self) -> None:
        definitions = build_contract_schema()["$defs"]
        self.assertEqual(
            {item.value for item in RelationToTarget},
            set(definitions["modelReference"]["properties"]["relation"]["enum"]),
        )
        self.assertEqual(
            {item.value for item in SourceRole},
            set(definitions["fieldReference"]["properties"]["source_role"]["enum"]),
        )
        self.assertEqual(
            {item.value for item in LifecycleStatus},
            set(definitions["lifecycle"]["properties"]["status"]["enum"]),
        )
        self.assertEqual(
            {item.value for item in ValidationCheckStatus},
            set(definitions["checkSummary"]["properties"]["status"]["enum"]),
        )

    def test_all_internal_definition_references_resolve(self) -> None:
        schema = build_contract_schema()
        definitions = schema["$defs"]
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

        visit(schema)
        self.assertEqual(unresolved, [])


if __name__ == "__main__":
    unittest.main()
