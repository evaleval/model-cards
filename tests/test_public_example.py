import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from model_cards.public_example import (
    PublicExampleError,
    assert_public_projection,
    export_public_example,
)
from model_cards.schema import blank_card, validate_complete_card


class PublicExampleTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    EXPECTED_PUBLIC_CARDS = {
        "examples/generated/olmo-2-1124-7b/card.json":
            "3fb467b86abcc1ad81619f0bde3327559d01954c4c92aac004669f663243f92a",
        "examples/generated/whisper-large-v3-mlx/card.json":
            "488b8f21cf63f651095a695e89d4ca5777feaae14a2b8f76b9aa6249bc98c3b5",
        "examples/generated/docling-layout-heron/card.json":
            "27a727be1643b06e6aa55d7bf16d997bcf6ec8d571332957b959faa5304045a9",
        "examples/audit-cases/olmo-2-1124-7b-instruct/card.json":
            "ee5ab65974dcd826f638179a5617bcd1a962f6134450a7c3f7c9187eadbe3ee2",
    }
    EXPECTED_PUBLIC_RECORDS = {
        "examples/generated/olmo-2-1124-7b/card.json": {
            "exact_target": (
                "allenai/OLMo-2-1124-7B@"
                "7df9a82518afdecae4e8c026b27adccc8c1f0032"
            ),
            "status": "development",
            "automated_audit": "projected_claim_support_scope_passed",
            "coverage_score": 0.666667,
            "binding_counts": {"accept": 35, "withhold": 6},
            "score_rows": 9,
        },
        "examples/generated/whisper-large-v3-mlx/card.json": {
            "exact_target": (
                "mlx-community/whisper-large-v3-mlx@"
                "49e6aa286ad60c14352c404340ded53710378a11"
            ),
            "status": "historical",
            "automated_audit": "not_run",
            "coverage_score": 0.242424,
            "binding_counts": {"accept": 13},
            "score_rows": 0,
        },
        "examples/generated/docling-layout-heron/card.json": {
            "exact_target": (
                "docling-project/docling-layout-heron@"
                "54100edecdceb65a9d8204d2478ac4cc8d4ca68b"
            ),
            "status": "historical",
            "automated_audit": "not_run",
            "coverage_score": 0.242424,
            "binding_counts": {"accept": 13, "withhold": 2},
            "score_rows": 0,
        },
        "examples/audit-cases/olmo-2-1124-7b-instruct/card.json": {
            "exact_target": (
                "allenai/OLMo-2-1124-7B-Instruct@"
                "470b1fba1ae01581f270116362ee4aa1b97f4c84"
            ),
            "status": "audit-case",
            "automated_audit": "blocked",
            "coverage_score": 0.636364,
            "binding_counts": {"accept": 33, "withhold": 8},
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

    def test_exports_only_card_projection(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(self._artifact()), encoding="utf-8")
            output = root / "public"
            record = export_public_example(
                artifact,
                output,
                status="historical",
                automated_audit="not_run",
            )

            exported = json.loads((output / "card.json").read_text(encoding="utf-8"))
            self.assertEqual(exported, self._artifact()["card"])
            self.assertNotIn("source_bundle", exported)
            self.assertEqual(record["binding_counts"], {"accept": 1, "withhold": 1})
            self.assertEqual(record["human_review"], "not_run")
            self.assertFalse(record["audit_record_in_export"])
            self.assertIn(
                record["audit_annotation_source"],
                {"not_applicable", "operator_supplied_from_non_public_audit_record"},
            )
            self.assertIn(
                record["projection_profile"],
                {"historical_feasibility_v5", "model_assisted_v5"},
            )
            self.assertTrue((output / "card.md").is_file())

    def test_rejects_private_structure_in_card(self):
        card = self._artifact()["card"]
        card["source_bundle"] = {"content": "private"}
        with self.assertRaises(PublicExampleError):
            assert_public_projection(card)

    def test_rejects_unknown_binding_action(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["bindings"][0]["verifier_action"] = "confidential-source-prose"
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    root / "public",
                    status="historical",
                    automated_audit="not_run",
                )

    def test_rejects_private_run_label_as_artifact_id(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["artifact_id"] = "private-20260830-06"
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    root / "public",
                    status="historical",
                    automated_audit="not_run",
                )

    def test_rejects_local_paths(self):
        with self.assertRaises(PublicExampleError):
            assert_public_projection({"value": "/Users/example/.cache/model"})

    def test_rejects_home_relative_paths_and_url_credentials(self):
        for value in ("~/private/model", "https://user:secret@example.org/model"):
            with self.subTest(value=value):
                with self.assertRaises(PublicExampleError):
                    assert_public_projection({"value": value})

    def test_rejects_target_drift(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["identity"]["model_id"] = "owner/other-model"
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    root / "public",
                    status="historical",
                    automated_audit="not_run",
                )

    def test_rejects_schema_metadata_drift(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["provenance_and_quality"]["card_info"]["schema_version"] = "4"
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    root / "public",
                    status="historical",
                    automated_audit="not_run",
                )

    def test_rejects_source_content_disguised_as_manifest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["provenance_and_quality"]["card_info"]["source_manifest"] = {
                "README.md": "private notes that are not a digest"
            }
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    root / "public",
                    status="historical",
                    automated_audit="not_run",
                )

    def test_rejects_unknown_card_info_keys(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = self._artifact()
            value["card"]["provenance_and_quality"]["card_info"]["private_notes"] = "text"
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    root / "public",
                    status="historical",
                    automated_audit="not_run",
                )

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
                artifact = root / "artifact.json"
                artifact.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(PublicExampleError):
                    export_public_example(
                        artifact,
                        root / "public",
                        status="historical",
                        automated_audit="not_run",
                    )

    def test_rejects_unrecognized_card_info_labels(self):
        unsafe_values = {
            "inapplicable_fields": ["private_notes.confidential"],
            "frame": {"private_notes": 1},
            "source_manifest": {"private_notes.md": "b" * 64},
        }
        for key, unsafe in unsafe_values.items():
            with self.subTest(key=key), TemporaryDirectory() as temporary:
                root = Path(temporary)
                value = self._artifact()
                value["card"]["provenance_and_quality"]["card_info"][key] = unsafe
                artifact = root / "artifact.json"
                artifact.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(PublicExampleError):
                    export_public_example(
                        artifact,
                        root / "public",
                        status="historical",
                        automated_audit="not_run",
                    )

        for key, unsafe in {
            "condition": "confidential_source_prose",
            "quality_snapshot": "confidential_source_prose",
            "generated_at": "confidential_source_prose",
            "llm": "confidential source prose",
        }.items():
            with self.subTest(key=key), TemporaryDirectory() as temporary:
                root = Path(temporary)
                value = self._artifact()
                value["card"]["provenance_and_quality"]["card_info"][key] = unsafe
                artifact = root / "artifact.json"
                artifact.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(PublicExampleError):
                    export_public_example(
                        artifact,
                        root / "public",
                        status="historical",
                        automated_audit="not_run",
                    )

    def test_rejects_destination_with_unexpected_files(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(self._artifact()), encoding="utf-8")
            output = root / "public"
            output.mkdir()
            (output / "source_bundle.json").write_text("private", encoding="utf-8")
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    output,
                    status="historical",
                    automated_audit="not_run",
                    force=True,
                )

    def test_rejects_symlinked_output(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / "artifact.json"
            artifact.write_text(json.dumps(self._artifact()), encoding="utf-8")
            output = root / "public"
            output.mkdir()
            target = root / "elsewhere.json"
            target.write_text("{}", encoding="utf-8")
            (output / "card.json").symlink_to(target)
            with self.assertRaises(PublicExampleError):
                export_public_example(
                    artifact,
                    output,
                    status="historical",
                    automated_audit="not_run",
                    force=True,
                )

    def test_checked_in_examples_match_real_projection_digests(self):
        for relative, expected_digest in self.EXPECTED_PUBLIC_CARDS.items():
            card_path = self.ROOT / relative
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

            record_path = card_path.with_name("public-export.json")
            record = json.loads(record_path.read_text(encoding="utf-8"))
            assert_public_projection(record)
            markdown_path = card_path.with_name("card.md")
            assert_public_projection(markdown_path.read_text(encoding="utf-8"))
            self.assertEqual(
                {path.name for path in card_path.parent.iterdir()},
                {"card.json", "card.md", "public-export.json"},
            )
            self.assertEqual(record["card_projection_sha256"], expected_digest)
            self.assertEqual(record["export_scope"], "generated_card_projection_only")
            self.assertEqual(record["human_review"], "not_run")
            self.assertEqual(
                record["schema_validation"],
                "complete_v5_38_field_structure",
            )
            for key, value in self.EXPECTED_PUBLIC_RECORDS[relative].items():
                self.assertEqual(record[key], value)


if __name__ == "__main__":
    unittest.main()
