from __future__ import annotations

from dataclasses import replace
import tempfile
from pathlib import Path
import unittest

from model_cards.bindings import source_from_dict
from model_cards.claim_gate import (
    ClaimCandidate,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
    correct_candidate,
)
from model_cards.artifact import project_card
from model_cards.publication import project_publication_card
from model_cards.render import render_html
from model_cards.review import (
    accept_binding,
    load_artifact,
    reassign_binding,
    save_artifact,
    withhold_binding,
)
from model_cards.schema import NOT_SPECIFIED
from tests.helpers import synthetic_artifact, synthetic_specification


class ReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = tuple(
            source_from_dict(item) for item in synthetic_specification()["sources"]
        )

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
        candidate = correct_candidate(
            ClaimCandidate.from_binding(original.target, binding),
            field_path="evaluation.results_summary",
        )
        checks = tuple(
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=gate,
                checker="tests/review-prose-checker-v1",
                method=(
                    "bounded_semantic_entity_review"
                    if gate is GateName.ENTITY_SCOPE
                    else "bounded_semantic_field_review"
                    if gate is GateName.FIELD_FIT
                    else "bounded_complete_value_review"
                ),
                status=DecisionStatus.ACCEPTED,
                reason=(
                    "semantic_entity_scope"
                    if gate is GateName.ENTITY_SCOPE
                    else "semantic_field_fit"
                    if gate is GateName.FIELD_FIT
                    else "semantic_value_support"
                ),
            )
            for gate in (
                GateName.ENTITY_SCOPE,
                GateName.FIELD_FIT,
                GateName.VALUE_SUPPORT,
            )
        )
        reviewed = reassign_binding(
            original,
            binding.binding_id,
            field_path="evaluation.results_summary",
            relation="exact_target",
            corrected_value=binding.value,
            reason="field_corrected",
            sources=self.sources,
            checker_decisions=checks,
        )
        card = project_card(reviewed)
        self.assertEqual(card["identity"]["summary"], NOT_SPECIFIED)
        self.assertEqual(card["evaluation"]["results_summary"], binding.value)
        self.assertEqual(original.bindings, reviewed.bindings)
        self.assertEqual(1, len(reviewed.review_gate_records))
        self.assertEqual("generated_unreviewed", reviewed.lifecycle_status.value)
        self.assertFalse(reviewed.validation_checks)
        html = render_html(reviewed)
        self.assertIn("Generated state", html)
        self.assertIn("evaluation.results_summary", html)

    def test_reassign_cannot_project_an_unsupported_replacement(self) -> None:
        original = synthetic_artifact()
        binding = self._summary_binding(original)
        unsupported = "A fabricated result that is absent from every source."
        candidate = correct_candidate(
            ClaimCandidate.from_binding(original.target, binding),
            field_path="evaluation.results_summary",
            value=unsupported,
        )
        checks = tuple(
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=gate,
                checker="tests/review-prose-checker-v1",
                method="bounded_semantic_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_review_claimed",
            )
            for gate in (
                GateName.ENTITY_SCOPE,
                GateName.FIELD_FIT,
                GateName.VALUE_SUPPORT,
            )
        )
        with self.assertRaisesRegex(ValueError, "did not pass all four claim gates"):
            reassign_binding(
                original,
                binding.binding_id,
                field_path="evaluation.results_summary",
                relation="exact_target",
                corrected_value=unsupported,
                reason="fabricated_replacement",
                sources=self.sources,
                checker_decisions=checks,
            )

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
            if item.field_path == "training.training_data_size"
        )
        with self.assertRaises(ValueError):
            accept_binding(artifact, binding.binding_id, reason="scope_unresolved")

    def test_projection_neutral_review_preserves_publication_snapshot(self) -> None:
        artifact = synthetic_artifact()
        publication = project_publication_card(project_card(artifact))
        published = replace(
            artifact,
            publication_card=publication,
            publication_source_catalog_sha256="a" * 64,
        )
        binding = self._summary_binding(published)

        accepted = accept_binding(
            published,
            binding.binding_id,
            reason="evidence_confirmed",
        )
        withheld = withhold_binding(
            published,
            binding.binding_id,
            reason="needs_check",
        )

        self.assertEqual(publication, accepted.publication_card)
        self.assertEqual(published.derivations, accepted.derivations)
        self.assertIsNone(withheld.publication_card)


if __name__ == "__main__":
    unittest.main()
