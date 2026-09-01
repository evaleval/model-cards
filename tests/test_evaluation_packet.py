from __future__ import annotations

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


class HeldOutEvaluationPacketTests(unittest.TestCase):
    def test_empty_public_template_is_schema_valid_and_not_a_result(self) -> None:
        schema = json.loads(
            (REPOSITORY_ROOT / "evaluation" / "annotation.schema.json").read_text(
                encoding="utf-8"
            )
        )
        template = json.loads(
            (REPOSITORY_ROOT / "evaluation" / "annotation-template.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(template)
        self.assertEqual(template["study_status"], "design_only_no_human_results")
        self.assertFalse(template["annotator_confirmation"]["completed"])
        for name in (
            "claim_support",
            "assignment",
            "omissions",
            "risk_applicability",
            "warning_utility",
        ):
            self.assertEqual(template[name], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
