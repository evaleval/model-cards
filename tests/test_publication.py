from __future__ import annotations

import unittest

from model_cards.artifact import project_card
from model_cards.publication import project_publication_card, publication_record
from model_cards.publication_contract import SECTION_FIELDS
from model_cards.publication_schema import validate_publication_card
from tests.helpers import synthetic_artifact


class PublicationProjectionTests(unittest.TestCase):
    def test_projection_is_exact_allowlist_and_maps_renamed_fields(self) -> None:
        audit = project_card(synthetic_artifact())
        audit["model_details"]["modalities"] = ["input: text", "output: text"]
        audit["model_details"]["model_stage"] = "instruction/chat"
        public = project_publication_card(audit)

        self.assertEqual(set(public), set(SECTION_FIELDS))
        self.assertEqual(public["identity"]["version"], audit["identity"]["revision"])
        self.assertEqual(
            public["specifications"]["input_output"],
            ["input: text", "output: text", "model stage: instruction/chat"],
        )
        self.assertNotIn("revision", public["identity"])
        self.assertNotIn("environmental_information", public)
        self.assertNotIn("use_and_risk", public)
        self.assertNotIn("provenance", public)
        self.assertNotIn("validation", public)
        self.assertNotIn("lifecycle", public)
        validate_publication_card(public)

    def test_unknowns_are_omitted_and_coverage_uses_33_agreed_fields(self) -> None:
        public = project_publication_card(project_card(synthetic_artifact()))
        self.assertNotIn("release_date", public["identity"])
        record = publication_record(public)
        self.assertEqual(record["field_count"], 33)
        self.assertGreater(record["specified_field_count"], 0)
        self.assertLess(record["specified_field_count"], 33)


if __name__ == "__main__":
    unittest.main()
