from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from jsonschema import Draft202012Validator, FormatChecker

from model_cards.public_export import (
    PublicExportError,
    assert_public_projection,
    export_public_card,
)
from model_cards.review import save_artifact
from model_cards.schema import CONTRACT_SCHEMA, validate_public_card
from tests.helpers import synthetic_artifact


class PublicExportTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    EXPECTED_CARD_FACTS = {
        "olmo-2-1124-7b.json": {
            "model_id": "allenai/OLMo-2-1124-7B",
            "revision": "7df9a82518afdecae4e8c026b27adccc8c1f0032",
            "coverage_score": 0.113636,
            "score_rows": 0,
        },
        "olmo-2-1124-7b-instruct.json": {
            "model_id": "allenai/OLMo-2-1124-7B-Instruct",
            "revision": "470b1fba1ae01581f270116362ee4aa1b97f4c84",
            "coverage_score": 0.136364,
            "score_rows": 0,
        },
        "mistral-7b-v0.3.json": {
            "model_id": "mistralai/Mistral-7B-v0.3",
            "revision": "caa1feb0e54d415e2df31207e5f4e273e33509b1",
            "coverage_score": 0.113636,
            "score_rows": 0,
        },
    }

    def _write_artifact(self, root: Path, value=None) -> Path:
        path = root / "artifact.json"
        if value is None:
            save_artifact(synthetic_artifact(), path)
        else:
            path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_exports_the_projection_from_the_actual_card_artifact_dialect(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = synthetic_artifact()
            source = root / "artifact.json"
            save_artifact(artifact, source)
            output = root / "card.json"

            record = export_public_card(source, output)
            exported = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(exported, artifact.to_dict()["card"])
            validate_public_card(exported)
            self.assertEqual(record["artifact_id"], artifact.artifact_id)
            self.assertEqual(record["contract_version"], "1")
            self.assertEqual(record["lifecycle_status"], "generated_unreviewed")
            self.assertNotIn("bindings", exported)
            self.assertNotIn("reviews", exported)

    def test_force_controls_overwrite(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._write_artifact(root)
            output = root / "card.json"
            export_public_card(source, output)
            with self.assertRaises(PublicExportError):
                export_public_card(source, output)
            export_public_card(source, output, force=True)

    def test_privacy_boundary_rejects_private_structure_and_paths(self) -> None:
        unsafe = (
            {"source_bundle": {"content": "private"}},
            {"value": "/Users/example/.cache/model"},
            {"value": "~/private/model"},
            {"value": "https://user:secret@example.org/model"},
            {"/Users/example/private": "redacted"},
        )
        for value in unsafe:
            with self.subTest(value=value), self.assertRaises(PublicExportError):
                assert_public_projection(value)

    def test_tampered_projection_artifact_id_and_contract_are_rejected(self) -> None:
        mutations = (
            lambda value: value["card"]["identity"].update({"name": "tampered"}),
            lambda value: value.update({"artifact_id": "card_" + "0" * 24}),
            lambda value: value.update({"contract_version": "2"}),
            lambda value: value["bindings"][0].update({"reason": "tampered_reason"}),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate), TemporaryDirectory() as temporary:
                root = Path(temporary)
                value = synthetic_artifact().to_dict()
                mutate(value)
                with self.assertRaises(PublicExportError):
                    export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_public_source_manifest_cannot_disguise_content(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = synthetic_artifact().to_dict()
            value["card"]["provenance"]["source_manifest"]["synthetic-hf-metadata"] = {
                "source_uri": "https://example.invalid/source",
                "source_role": "hugging_face_metadata",
                "source_revision": "main",
                "source_sha256": "private notes rather than a digest",
            }
            with self.assertRaises(PublicExportError):
                export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_output_must_be_a_new_regular_json_path(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = self._write_artifact(root)
            with self.assertRaises(PublicExportError):
                export_public_card(source, root / "card.md")

            directory = root / "directory.json"
            directory.mkdir()
            with self.assertRaises(PublicExportError):
                export_public_card(source, directory, force=True)

            target = root / "elsewhere.json"
            target.write_text("{}", encoding="utf-8")
            symlink = root / "symlink.json"
            symlink.symlink_to(target)
            with self.assertRaises(PublicExportError):
                export_public_card(source, symlink, force=True)

    def test_every_checked_in_card_passes_the_actual_draft_validator(self) -> None:
        validator = Draft202012Validator(CONTRACT_SCHEMA, format_checker=FormatChecker())
        cards = self.ROOT / "cards"
        self.assertEqual({path.name for path in cards.iterdir()}, set(self.EXPECTED_CARD_FACTS))
        for path in sorted(cards.glob("*.json")):
            with self.subTest(path=path):
                card = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(list(validator.iter_errors(card)), [])
                validate_public_card(card)
                assert_public_projection(card)
                expected = self.EXPECTED_CARD_FACTS[path.name]
                self.assertEqual(card["contract_version"], "1")
                self.assertEqual(card["identity"]["model_id"], expected["model_id"])
                self.assertEqual(card["identity"]["revision"], expected["revision"])
                self.assertEqual(card["validation"]["coverage_score"], expected["coverage_score"])
                scores = card["evaluation"]["benchmark_scores"]
                self.assertEqual(len(scores) if isinstance(scores, list) else 0, expected["score_rows"])
                self.assertEqual(card["lifecycle"]["status"], "generated_unreviewed")
                self.assertTrue(card["provenance"]["source_manifest"])
                for source in card["provenance"]["source_manifest"].values():
                    self.assertIn("source_uri", source)
                    self.assertNotIn("/Users/", source["source_uri"])


if __name__ == "__main__":
    unittest.main()
