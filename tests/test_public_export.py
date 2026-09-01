import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from model_cards.public_export import (
    PublicExportError,
    assert_public_projection,
    export_public_card,
)
from model_cards.schema import blank_card, validate_complete_card


class PublicExportTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    EXPECTED_PUBLIC_CARDS = {
        "olmo-2-1124-7b.json":
            "3fb467b86abcc1ad81619f0bde3327559d01954c4c92aac004669f663243f92a",
        "olmo-2-1124-7b-instruct.json":
            "ee5ab65974dcd826f638179a5617bcd1a962f6134450a7c3f7c9187eadbe3ee2",
    }
    EXPECTED_CARD_FACTS = {
        "olmo-2-1124-7b.json": {
            "exact_target": (
                "allenai/OLMo-2-1124-7B@"
                "7df9a82518afdecae4e8c026b27adccc8c1f0032"
            ),
            "coverage_score": 0.666667,
            "score_rows": 9,
        },
        "olmo-2-1124-7b-instruct.json": {
            "exact_target": (
                "allenai/OLMo-2-1124-7B-Instruct@"
                "470b1fba1ae01581f270116362ee4aa1b97f4c84"
            ),
            "coverage_score": 0.636364,
            "score_rows": 8,
        },
    }

    def _artifact(self):
        card = blank_card()
        card["identity"].update(
            {
                "model_id": "owner/model",
                "name": "Example",
                "version": "a" * 40,
            }
        )
        card["provenance_and_quality"].update(
            {
                "coverage_score": 0.5,
                "missing_fields": ["evaluation.benchmark_scores"],
                "flagged_fields": [],
                "card_info": {
                    "composer_commit": "c" * 40,
                    "inapplicable_fields": [],
                    "schema_version": "5",
                    "target": f"owner/model@{'a' * 40}",
                    "source_manifest": {"README.md": "b" * 64},
                },
            }
        )
        return {
            "artifact_id": "card_" + "e" * 24,
            "schema_version": "5",
            "target": {
                "model_id": "owner/model",
                "resolved_revision": "a" * 40,
            },
            "bindings": [
                {"verifier_action": "accept"},
                {"verifier_action": "withhold"},
            ],
            "source_bundle": {"content": "must stay local"},
            "card": card,
        }

    def _write_artifact(self, root: Path, value=None) -> Path:
        artifact = root / "artifact.json"
        artifact.write_text(
            json.dumps(self._artifact() if value is None else value),
            encoding="utf-8",
        )
        return artifact

    def test_exports_one_json_card_projection(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = self._write_artifact(root)
            output = root / "card.json"

            record = export_public_card(artifact, output)

            exported = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(exported, self._artifact()["card"])
            self.assertNotIn("source_bundle", exported)
            self.assertEqual(record["binding_counts"], {"accept": 1, "withhold": 1})
            self.assertEqual(record["exact_target"], f"owner/model@{'a' * 40}")
            self.assertEqual(record["score_rows"], 0)
            self.assertEqual(
                {path.name for path in root.iterdir()},
                {"artifact.json", "card.json"},
            )

    def test_force_controls_overwrite(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = self._write_artifact(root)
            output = root / "card.json"
            export_public_card(artifact, output)

            with self.assertRaises(PublicExportError):
                export_public_card(artifact, output)
            export_public_card(artifact, output, force=True)

    def test_rejects_private_structure_in_card(self):
        card = self._artifact()["card"]
        card["source_bundle"] = {"content": "private"}
        with self.assertRaises(PublicExportError):
            assert_public_projection(card)

    def test_rejects_sensitive_dictionary_key(self):
        with self.assertRaises(PublicExportError):
            assert_public_projection({"/Users/example/private": "redacted"})

    def test_rejects_unknown_binding_action(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["bindings"][0]["verifier_action"] = "confidential-source-prose"
            with self.assertRaises(PublicExportError):
                export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_private_run_label_as_artifact_id(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["artifact_id"] = "private-20260830-06"
            with self.assertRaises(PublicExportError):
                export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_local_paths(self):
        with self.assertRaises(PublicExportError):
            assert_public_projection({"value": "/Users/example/.cache/model"})

    def test_rejects_home_relative_paths_and_url_credentials(self):
        for value in ("~/private/model", "https://user:secret@example.org/model"):
            with self.subTest(value=value):
                with self.assertRaises(PublicExportError):
                    assert_public_projection({"value": value})

    def test_rejects_target_drift(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["identity"]["model_id"] = "owner/other-model"
            with self.assertRaises(PublicExportError):
                export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_schema_metadata_drift(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["provenance_and_quality"]["card_info"]["schema_version"] = "4"
            with self.assertRaises(PublicExportError):
                export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_source_content_disguised_as_manifest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["provenance_and_quality"]["card_info"]["source_manifest"] = {
                "README.md": "private notes that are not a digest"
            }
            with self.assertRaises(PublicExportError):
                export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_unknown_card_info_keys(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["provenance_and_quality"]["card_info"]["private_notes"] = "text"
            with self.assertRaises(PublicExportError):
                export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_private_content_in_allowlisted_card_info(self):
        unsafe_values = {
            "condition": {"private_notes": "confidential source prose"},
            "quality_snapshot": {"private_notes": "confidential source prose"},
            "generated_at": {"private_notes": "confidential source prose"},
            "llm": {"private_notes": "confidential source prose"},
        }
        for key, unsafe in unsafe_values.items():
            with self.subTest(key=key), TemporaryDirectory() as temporary:
                root = Path(temporary)
                value = self._artifact()
                value["card"]["provenance_and_quality"]["card_info"][key] = unsafe
                with self.assertRaises(PublicExportError):
                    export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_unrecognized_card_info_labels(self):
        unsafe_values = {
            "inapplicable_fields": ["private_notes.confidential"],
            "frame": {"private_notes": 1},
            "source_manifest": {"private_notes.md": "b" * 64},
            "condition": "confidential_source_prose",
            "quality_snapshot": "confidential_source_prose",
            "generated_at": "confidential_source_prose",
            "llm": "confidential source prose",
        }
        for key, unsafe in unsafe_values.items():
            with self.subTest(key=key), TemporaryDirectory() as temporary:
                root = Path(temporary)
                value = self._artifact()
                value["card"]["provenance_and_quality"]["card_info"][key] = unsafe
                with self.assertRaises(PublicExportError):
                    export_public_card(self._write_artifact(root, value), root / "card.json")

    def test_rejects_non_json_and_directory_destinations(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = self._write_artifact(root)
            with self.assertRaises(PublicExportError):
                export_public_card(artifact, root / "card.md")

            output_directory = root / "card.json"
            output_directory.mkdir()
            with self.assertRaises(PublicExportError):
                export_public_card(artifact, output_directory, force=True)

    def test_rejects_symlinked_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = self._write_artifact(root)
            target = root / "elsewhere.json"
            target.write_text("{}", encoding="utf-8")
            output = root / "card.json"
            output.symlink_to(target)
            with self.assertRaises(PublicExportError):
                export_public_card(artifact, output, force=True)

    def test_checked_in_cards_are_canonical_json_projections(self):
        cards_directory = self.ROOT / "cards"
        self.assertEqual(
            {path.name for path in cards_directory.iterdir()},
            set(self.EXPECTED_PUBLIC_CARDS),
        )

        for filename, expected_digest in self.EXPECTED_PUBLIC_CARDS.items():
            with self.subTest(filename=filename):
                card_path = cards_directory / filename
                card = json.loads(card_path.read_text(encoding="utf-8"))
                validate_complete_card(card)
                assert_public_projection(card)
                canonical = (
                    json.dumps(
                        card,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                    + "\n"
                ).encode("utf-8")
                self.assertEqual(hashlib.sha256(canonical).hexdigest(), expected_digest)

                expected = self.EXPECTED_CARD_FACTS[filename]
                card_info = card["provenance_and_quality"]["card_info"]
                self.assertEqual(card_info["target"], expected["exact_target"])
                self.assertEqual(
                    card["provenance_and_quality"]["coverage_score"],
                    expected["coverage_score"],
                )
                self.assertEqual(
                    len(card["evaluation"]["benchmark_scores"]),
                    expected["score_rows"],
                )


if __name__ == "__main__":
    unittest.main()
