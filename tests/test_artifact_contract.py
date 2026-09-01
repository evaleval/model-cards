from __future__ import annotations

import unittest

from model_cards.artifact import CardArtifact, project_card
from model_cards.models import LifecycleStatus, ValidationCheck
from tests.helpers import synthetic_artifact


class ArtifactContractTests(unittest.TestCase):
    def _privacy_check(self) -> ValidationCheck:
        return ValidationCheck(
            check_id="privacy",
            status="completed",
            checked=1,
            passed=1,
        )

    def test_generated_validated_requires_a_closed_gate_summary(self) -> None:
        artifact = synthetic_artifact()
        with self.assertRaisesRegex(ValueError, "claim_support and privacy"):
            CardArtifact(
                target=artifact.target,
                bindings=artifact.bindings,
                lifecycle_status=LifecycleStatus.GENERATED_VALIDATED,
            )

    def test_generated_validated_rejects_complete_but_mismatched_counts(self) -> None:
        artifact = synthetic_artifact()
        included = sum(item.disposition.value == "accepted" for item in artifact.bindings)
        with self.assertRaisesRegex(ValueError, "every included binding"):
            CardArtifact(
                target=artifact.target,
                bindings=artifact.bindings,
                lifecycle_status=LifecycleStatus.GENERATED_VALIDATED,
                validation_checks=(
                    ValidationCheck(
                        check_id="claim_support",
                        status="completed",
                        checked=included + 1,
                        passed=included + 1,
                    ),
                    self._privacy_check(),
                ),
            )

    def test_generated_validated_requires_full_outcome_coverage(self) -> None:
        artifact = synthetic_artifact()
        included = sum(item.disposition.value == "accepted" for item in artifact.bindings)
        with self.assertRaisesRegex(ValueError, "passing claim_support"):
            CardArtifact(
                target=artifact.target,
                bindings=artifact.bindings,
                lifecycle_status=LifecycleStatus.GENERATED_VALIDATED,
                validation_checks=(
                    ValidationCheck(
                        check_id="claim_support",
                        status="completed",
                        checked=included,
                        passed=max(0, included - 1),
                    ),
                    self._privacy_check(),
                ),
            )

    def test_passing_required_checks_can_preserve_generated_validated(self) -> None:
        artifact = synthetic_artifact()
        included = sum(item.disposition.value == "accepted" for item in artifact.bindings)
        validated = CardArtifact(
            target=artifact.target,
            bindings=artifact.bindings,
            lifecycle_status=LifecycleStatus.GENERATED_VALIDATED,
            validated_at="2026-09-01T20:00:00+00:00",
            validation_checks=(
                ValidationCheck(
                    check_id="claim_support",
                    status="completed",
                    checked=included,
                    passed=included,
                ),
                self._privacy_check(),
            ),
        )
        card = project_card(validated)
        self.assertEqual(card["lifecycle"]["status"], "generated_validated")
        self.assertEqual(card["validation"]["overall_status"], "passed")
        self.assertEqual(CardArtifact.from_dict(validated.to_dict()), validated)

    def test_status_cannot_be_changed_by_mutating_a_serialized_projection(self) -> None:
        payload = synthetic_artifact().to_dict()
        payload["lifecycle"]["status"] = "generated_validated"
        payload["card"]["lifecycle"]["status"] = "generated_validated"
        with self.assertRaises(ValueError):
            CardArtifact.from_dict(payload)


if __name__ == "__main__":
    unittest.main()
