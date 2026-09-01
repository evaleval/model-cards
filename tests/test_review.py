from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from model_cards.artifact import project_card
from model_cards.render import render_html
from model_cards.review import (
    accept_binding,
    load_artifact,
    reassign_binding,
    save_artifact,
    withhold_binding,
)
from model_cards.schema import NOT_SPECIFIED
from tests.helpers import synthetic_artifact


class ReviewTests(unittest.TestCase):
    def _summary_binding(self, artifact):
        return next(item for item in artifact.bindings if item.field_path == "identity.summary")

    def test_reviews_append_without_mutating_generation_state(self) -> None:
        original = synthetic_artifact()
        binding = self._summary_binding(original)
        withheld = withhold_binding(original, binding.binding_id, reason="needs_check")
        accepted = accept_binding(withheld, binding.binding_id, reason="evidence_confirmed")

        self.assertEqual(original.reviews, ())
        self.assertEqual(len(withheld.reviews), 1)
        self.assertEqual(len(accepted.reviews), 2)
        self.assertEqual(
            project_card(withheld)["identity"]["summary"],
            NOT_SPECIFIED,
        )
        self.assertEqual(
            project_card(accepted)["identity"]["summary"],
            binding.value,
        )

    def test_reassign_projects_from_the_same_verified_evidence(self) -> None:
        original = synthetic_artifact()
        binding = self._summary_binding(original)
        reviewed = reassign_binding(
            original,
            binding.binding_id,
            field_path="evaluation.results_summary",
            relation="exact_target",
            corrected_value=binding.value,
            reason="field_corrected",
        )
        card = project_card(reviewed)
        self.assertEqual(card["identity"]["summary"], NOT_SPECIFIED)
        self.assertEqual(card["evaluation"]["results_summary"], binding.value)
        self.assertEqual(original.bindings, reviewed.bindings)
        html = render_html(reviewed)
        self.assertIn("Generated state", html)
        self.assertIn("evaluation.results_summary", html)

    def test_round_trip_validates_the_projected_card(self) -> None:
        artifact = synthetic_artifact()
        binding = self._summary_binding(artifact)
        reviewed = withhold_binding(artifact, binding.binding_id, reason="needs_check")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "card.json"
            save_artifact(reviewed, path)
            loaded = load_artifact(path)
            self.assertEqual(loaded.to_dict(), reviewed.to_dict())
            self.assertEqual(loaded.bindings, artifact.bindings)
            self.assertEqual(loaded.reviews[: len(reviewed.reviews)], reviewed.reviews)

    def test_review_cannot_accept_a_binding_that_still_fails_policy(self) -> None:
        artifact = synthetic_artifact()
        binding = next(
            item
            for item in artifact.bindings
            if item.field_path == "training_context.training_data_size"
        )
        with self.assertRaises(ValueError):
            accept_binding(artifact, binding.binding_id, reason="scope_unresolved")


if __name__ == "__main__":
    unittest.main()
