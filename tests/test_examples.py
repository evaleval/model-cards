from __future__ import annotations

import json
from pathlib import Path
import unittest

from model_cards.artifact import project_card
from model_cards.bindings import build_artifact
from model_cards.render import render_html, render_json
from model_cards.schema import NOT_SPECIFIED


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class CheckedInExampleTests(unittest.TestCase):
    CASES = {
        "mixed-evidence": EXAMPLES / "synthetic-input.json",
        "family-scope": EXAMPLES / "cards" / "family-scope" / "input.json",
        "conflicting-sources": EXAMPLES / "cards" / "conflicting-sources" / "input.json",
    }

    def _artifact(self, name: str):
        specification = json.loads(self.CASES[name].read_text(encoding="utf-8"))
        return build_artifact(specification)

    def test_committed_outputs_match_current_renderer(self) -> None:
        for name in self.CASES:
            with self.subTest(name=name):
                artifact = self._artifact(name)
                directory = EXAMPLES / "cards" / name
                self.assertEqual(
                    (directory / "card.json").read_text(encoding="utf-8"),
                    render_json(artifact),
                )
                self.assertEqual(
                    (directory / "card.html").read_text(encoding="utf-8"),
                    render_html(artifact),
                )

    def test_family_quantity_is_withheld(self) -> None:
        artifact = self._artifact("family-scope")
        card = project_card(artifact)
        self.assertEqual(
            card["training_context"]["training_data_size"],
            NOT_SPECIFIED,
        )
        binding = next(
            item
            for item in artifact.bindings
            if item.field_path == "training_context.training_data_size"
        )
        self.assertEqual(binding.disposition.value, "withheld")
        self.assertEqual(binding.reason, "family_scope_not_target")

    def test_conflicting_context_lengths_fail_closed(self) -> None:
        artifact = self._artifact("conflicting-sources")
        card = project_card(artifact)
        self.assertEqual(card["specifications"]["context_length"], NOT_SPECIFIED)
        flags = card["provenance_and_quality"]["flagged_fields"]
        conflicts = flags["specifications.context_length"]
        self.assertEqual(len(conflicts), 2)
        self.assertEqual(
            {item["reason"] for item in conflicts},
            {"conflicting_accepted_values"},
        )


if __name__ == "__main__":
    unittest.main()
