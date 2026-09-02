from __future__ import annotations

import hashlib
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
from model_cards.public_markdown import render_public_markdown
from model_cards.publication_contract import PUBLICATION_SECTIONS
from model_cards.publication_schema import (
    PUBLICATION_SCHEMA,
    publication_coverage,
    validate_publication_card,
)
from model_cards.review import save_artifact
from model_cards.pipeline import run_offline_pipeline
from model_cards.source_bundle import collect_hf_source_bundle
from tests.helpers import synthetic_artifact
from tests.test_regenerate_frozen_examples import COMMIT, _FrozenAdapter


class PublicExportTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    MINIMUM_PUBLISHED_CARDS = 12
    MINIMUM_SPECIFIED_FIELDS = 15

    def _write_artifact(self, root: Path, value=None) -> Path:
        path = root / "artifact.json"
        if value is None:
            save_artifact(synthetic_artifact(), path)
        else:
            path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def _pipeline_files(self, root: Path) -> tuple[Path, Path, Path]:
        bundle = root / "source-bundle"
        collect_hf_source_bundle(
            "acme/Example-Instruct",
            bundle,
            _FrozenAdapter("acme/Example-Instruct"),
            revision=COMMIT,
        )
        run = root / "run"
        run_offline_pipeline(bundle, run)
        return bundle, run / "card-artifact.json", run / "public-card.json"

    def test_exports_the_replay_bound_publication_snapshot(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, source, pipeline_card = self._pipeline_files(root)
            output = root / "card.json"

            record = export_public_card(
                source,
                output,
                source_bundle_directory=bundle,
            )
            exported = json.loads(output.read_text(encoding="utf-8"))

            expected = json.loads(pipeline_card.read_text(encoding="utf-8"))
            self.assertEqual(exported, expected)
            validate_publication_card(exported)
            self.assertEqual(set(PUBLICATION_SECTIONS), set(exported))
            self.assertEqual(
                COMMIT, exported["identity"]["version"]
            )
            for audit_only_section in (
                "environmental_information",
                "use_and_risk",
                "provenance",
                "validation",
                "lifecycle",
            ):
                self.assertNotIn(audit_only_section, exported)
            self.assertEqual(record["publication_field_count"], 33)
            self.assertEqual(
                set(record),
                {
                    "card_projection_sha256",
                    "coverage_score",
                    "exact_target",
                    "publication_field_count",
                    "publication_schema_sha256",
                    "score_rows",
                },
            )
            self.assertNotIn("bindings", exported)
            self.assertNotIn("reviews", exported)

    def test_legacy_artifact_without_publication_snapshot_is_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, _artifact, _card = self._pipeline_files(root)
            source = self._write_artifact(root)
            with self.assertRaisesRegex(
                PublicExportError, "replay-bound publication snapshot"
            ):
                export_public_card(
                    source,
                    root / "card.json",
                    source_bundle_directory=bundle,
                )

    def test_force_controls_overwrite(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, source, _pipeline_card = self._pipeline_files(root)
            output = root / "card.json"
            export_public_card(source, output, source_bundle_directory=bundle)
            with self.assertRaises(PublicExportError):
                export_public_card(source, output, source_bundle_directory=bundle)
            export_public_card(
                source,
                output,
                source_bundle_directory=bundle,
                force=True,
            )

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

    def test_privacy_boundary_rejects_nested_audit_only_keys(self) -> None:
        for key in (
            "contract_version",
            "environmental_information",
            "lifecycle",
            "provenance",
            "use_and_risk",
            "validation",
        ):
            with self.subTest(key=key), self.assertRaises(PublicExportError):
                assert_public_projection({"outer": {key: {}}})

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
                bundle, source, _pipeline_card = self._pipeline_files(root)
                value = json.loads(source.read_text(encoding="utf-8"))
                mutate(value)
                with self.assertRaises(PublicExportError):
                    export_public_card(
                        self._write_artifact(root, value),
                        root / "card.json",
                        source_bundle_directory=bundle,
                    )

    def test_public_source_manifest_cannot_disguise_content(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, source, _pipeline_card = self._pipeline_files(root)
            value = json.loads(source.read_text(encoding="utf-8"))
            value["card"]["provenance"]["source_manifest"]["synthetic-hf-metadata"] = {
                "source_uri": "https://example.invalid/source",
                "source_role": "hugging_face_metadata",
                "source_revision": "main",
                "source_sha256": "private notes rather than a digest",
            }
            with self.assertRaises(PublicExportError):
                export_public_card(
                    self._write_artifact(root, value),
                    root / "card.json",
                    source_bundle_directory=bundle,
                )

    def test_output_must_be_a_new_regular_json_path(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle, source, _pipeline_card = self._pipeline_files(root)
            with self.assertRaises(PublicExportError):
                export_public_card(
                    source,
                    root / "card.md",
                    source_bundle_directory=bundle,
                )

            directory = root / "directory.json"
            directory.mkdir()
            with self.assertRaises(PublicExportError):
                export_public_card(
                    source,
                    directory,
                    source_bundle_directory=bundle,
                    force=True,
                )

            target = root / "elsewhere.json"
            target.write_text("{}", encoding="utf-8")
            symlink = root / "symlink.json"
            symlink.symlink_to(target)
            with self.assertRaises(PublicExportError):
                export_public_card(
                    source,
                    symlink,
                    source_bundle_directory=bundle,
                    force=True,
                )

    def test_every_checked_in_card_passes_the_actual_draft_validator(self) -> None:
        validator = Draft202012Validator(
            PUBLICATION_SCHEMA, format_checker=FormatChecker()
        )
        cards = self.ROOT / "cards"
        json_paths = sorted(cards.glob("*.json"))
        markdown_paths = sorted(cards.glob("*.md"))
        self.assertGreaterEqual(len(json_paths), self.MINIMUM_PUBLISHED_CARDS)
        self.assertEqual(
            {path.stem for path in json_paths},
            {path.stem for path in markdown_paths},
        )

        model_ids: set[str] = set()
        total_score_rows = 0
        for path in json_paths:
            with self.subTest(path=path):
                card = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(list(validator.iter_errors(card)), [])
                validate_publication_card(card)
                assert_public_projection(card)
                self.assertEqual(set(PUBLICATION_SECTIONS), set(card))
                for audit_only_section in (
                    "environmental_information",
                    "use_and_risk",
                    "provenance",
                    "validation",
                    "lifecycle",
                ):
                    self.assertNotIn(audit_only_section, card)

                model_id = card["identity"]["model_id"]
                self.assertNotIn(model_id, model_ids)
                model_ids.add(model_id)
                self.assertRegex(card["identity"]["version"], r"^[0-9a-f]{40}$")
                self.assertGreaterEqual(
                    round(publication_coverage(card) * 33),
                    self.MINIMUM_SPECIFIED_FIELDS,
                )
                scores = card["evaluation"].get("benchmark_scores")
                total_score_rows += len(scores) if isinstance(scores, list) else 0

                markdown_path = cards / f"{path.stem}.md"
                json_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(
                    render_public_markdown(
                        card,
                        json_filename=path.name,
                        json_sha256=json_sha256,
                    ),
                    markdown_path.read_text(encoding="utf-8"),
                )

        self.assertEqual(len(model_ids), len(json_paths))
        self.assertGreater(total_score_rows, 0)


if __name__ == "__main__":
    unittest.main()
