from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from model_cards.migrate import migrate_legacy_card
from model_cards.schema import validate_public_card


class MigrationTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]

    def _legacy_card(self) -> dict:
        target = "owner/model@" + "a" * 40
        missing = "Not specified"
        return {
            "identity": {
                "model_id": "owner/model",
                "name": "Example Model",
                "developed_by": "Example Lab",
                "model_type": "decoder-only",
                "license": "MIT",
                "release_date": missing,
                "version": "a" * 40,
                "summary": "A synthetic retained fact.",
            },
            "lineage": {
                "base_models": [{"model_id": "owner/base", "relation": "base"}],
                "model_family": missing,
                "derivatives": missing,
            },
            "specifications": {
                "architecture_type": "dense",
                "num_parameters": "1B",
                "context_length": "4096",
                "precision": "bfloat16",
                "modalities": ["input: text", "output: text"],
                "model_stage": "base",
            },
            "training_context": {
                "training_data": "Synthetic data",
                "training_data_size": missing,
                "data_cutoff": missing,
                "adaptations": missing,
            },
            "access_and_adoption": {"access_type": "open-weight", "downloads": missing},
            "evaluation": {
                "results_summary": missing,
                "benchmark_scores": missing,
                "related_model_scores": missing,
                "human_evals": missing,
                "safety_evals": missing,
                "evaluation_sources": missing,
            },
            "links": {
                "model_card": "https://huggingface.co/owner/model",
                "system_card": missing,
                "tech_report": "https://example.org/report",
                "code_repository": "https://example.org/code",
            },
            "provenance_and_quality": {
                "provenance": {
                    "quote_verify": {"emitted": 2, "verified": 2, "rejected": 0}
                },
                "flagged_fields": ["training_context.data_cutoff"],
                "missing_fields": ["training_context.data_cutoff"],
                "coverage_score": 0.5,
                "card_info": {
                    "target": target,
                    "generated_at": "2026-08-30T12:00:00+00:00",
                    "composer_commit": "b" * 40,
                    "llm": "example/model",
                    "source_manifest": {"README.md": "c" * 64},
                },
            },
        }

    def test_migration_is_deterministic_and_relocates_facts_without_rewriting(self) -> None:
        legacy = self._legacy_card()
        original = deepcopy(legacy)
        first = migrate_legacy_card(legacy)
        second = migrate_legacy_card(original)
        self.assertEqual(first, second)
        self.assertEqual(legacy, original)
        self.assertEqual(first["identity"]["summary"], original["identity"]["summary"])
        self.assertEqual(first["identity"]["revision"], original["identity"]["version"])
        for field, value in original["specifications"].items():
            self.assertEqual(first["model_details"][field], value)
        self.assertEqual(first["training"], original["training_context"])
        self.assertEqual(first["evaluation"], original["evaluation"])
        self.assertEqual(first["lineage"]["base_models"][0]["relation"], "base_model")
        self.assertEqual(first["lifecycle"]["status"], "generated_unreviewed")
        self.assertIn("environmental_information.hardware", first["validation"]["missing_fields"])
        self.assertIn("use_and_risk.identified_risks", first["validation"]["missing_fields"])
        validate_public_card(first)

    def test_checked_in_cards_are_idempotent_contract_instances(self) -> None:
        for path in sorted((self.ROOT / "cards").glob("*.json")):
            with self.subTest(path=path):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(migrate_legacy_card(value), value)


if __name__ == "__main__":
    unittest.main()
