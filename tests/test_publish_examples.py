from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.pipeline import run_offline_pipeline
from model_cards.public_markdown import render_public_markdown
from model_cards.source_bundle import collect_hf_source_bundle
from tests.test_regenerate_frozen_examples import COMMIT, _FrozenAdapter


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_examples.py"


def _card() -> dict[str, object]:
    return {
        "identity": {
            "model_id": "acme-labs/reference-model",
            "name": "Reference Model",
            "developed_by": "Acme Labs",
            "model_type": "Decoder-only language model",
            "license": "Apache-2.0",
            "version": "0123456789abcdef",
            "summary": "A public language model used to verify publication.",
        },
        "lineage": {},
        "specifications": {
            "architecture_type": "dense decoder-only",
            "num_parameters": "7 billion",
            "context_length": "8,192 tokens",
            "precision": "bfloat16",
            "model_size": "13 GiB",
            "input_output": ["text input", "text output"],
        },
        "training_context": {"training_data": "Documented public corpus"},
        "access_and_adoption": {"access_type": "Public weights"},
        "evaluation": {},
        "links": {
            "model_card": "https://huggingface.co/acme-labs/reference-model"
        },
    }


def _card_bytes() -> bytes:
    return (json.dumps(_card(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _load_script():
    specification = importlib.util.spec_from_file_location(
        "publish_examples_script", SCRIPT
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class PublishExamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_script()

    def temporary_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def generated(self, root: Path) -> tuple[Path, Path]:
        root.mkdir(parents=True, exist_ok=True)
        bundle = root / "source-bundle"
        collect_hf_source_bundle(
            "acme/Example-Instruct",
            bundle,
            _FrozenAdapter("acme/Example-Instruct"),
            revision=COMMIT,
        )
        run = root / "generated-run"
        run_offline_pipeline(bundle, run)
        return bundle, run / "public-card.json"

    def test_schema_and_privacy_checked_publication_preserves_exact_bytes(self) -> None:
        root = self.temporary_root()
        bundle, source = self.generated(root)
        raw = source.read_bytes()
        card = json.loads(raw)
        mapping = f"{source}=cards/example.json"

        records = self.module.publish_examples(
            (mapping,), source_bundles=(bundle,), repo_root=root
        )

        self.assertEqual(raw, (root / "cards" / "example.json").read_bytes())
        markdown = render_public_markdown(
            card,
            json_filename="example.json",
            json_sha256=hashlib.sha256(raw).hexdigest(),
        ).encode("utf-8")
        self.assertEqual(markdown, (root / "cards" / "example.md").read_bytes())
        self.assertEqual("cards/example.json", records[0]["destination"])
        self.assertEqual("cards/example.md", records[0]["markdown_destination"])
        self.assertEqual(COMMIT, records[0]["version"])
        self.assertNotIn("revision", records[0])
        self.assertNotIn("lifecycle_status", records[0])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), records[0]["sha256"])
        self.assertEqual(
            hashlib.sha256(markdown).hexdigest(), records[0]["markdown_sha256"]
        )
        self.assertEqual(
            records,
            self.module.publish_examples(
                (mapping,), source_bundles=(bundle,), repo_root=root
            ),
        )

    def test_overwrite_requires_force_and_force_restores_generated_bytes(self) -> None:
        root = self.temporary_root()
        bundle, source = self.generated(root)
        card = json.loads(source.read_bytes())
        destination = root / "cards" / "example.json"
        destination.parent.mkdir()
        destination.write_bytes(b"{}\n")
        markdown_destination = root / "cards" / "example.md"
        markdown_destination.write_text("stale\n", encoding="utf-8")
        mapping = f"{source}=cards/example.json"

        with self.assertRaisesRegex(ValueError, "destination exists"):
            self.module.publish_examples(
                (mapping,), source_bundles=(bundle,), repo_root=root
            )
        self.module.publish_examples(
            (mapping,), source_bundles=(bundle,), repo_root=root, force=True
        )
        self.assertEqual(source.read_bytes(), destination.read_bytes())
        expected_markdown = render_public_markdown(
            card,
            json_filename="example.json",
            json_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            expected_markdown, markdown_destination.read_text(encoding="utf-8")
        )

    def test_batch_preflight_prevents_partial_pair_publication(self) -> None:
        root = self.temporary_root()
        bundle, source = self.generated(root)
        blocked = root / "cards" / "second.md"
        blocked.parent.mkdir()
        blocked.write_text("existing unrelated Markdown\n", encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "destination exists"):
            self.module.publish_examples(
                (
                    f"{source}=cards/first.json",
                    f"{source}=cards/second.json",
                ),
                source_bundles=(bundle, bundle),
                repo_root=root,
            )

        self.assertFalse((root / "cards" / "first.json").exists())
        self.assertFalse((root / "cards" / "first.md").exists())
        self.assertFalse((root / "cards" / "second.json").exists())
        self.assertEqual(
            "existing unrelated Markdown\n", blocked.read_text(encoding="utf-8")
        )

    def test_sensitive_or_non_contract_card_is_not_published(self) -> None:
        root = self.temporary_root()
        bundle, source = self.generated(root)
        value = json.loads(source.read_text(encoding="utf-8"))
        value["identity"]["summary"] = "sk-" + "A" * 24
        source.write_text(json.dumps(value) + "\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            self.module.publish_examples(
                (f"{source}=cards/example.json",),
                source_bundles=(bundle,),
                repo_root=root,
            )
        self.assertFalse((root / "cards" / "example.json").exists())
        self.assertFalse((root / "cards" / "example.md").exists())

    def test_private_audit_schema_fields_are_not_accepted_for_publication(self) -> None:
        root = self.temporary_root()
        bundle, source = self.generated(root)
        value = json.loads(source.read_text(encoding="utf-8"))
        value["lifecycle"] = {"status": "generated_unreviewed"}
        source.write_text(json.dumps(value) + "\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            self.module.publish_examples(
                (f"{source}=cards/example.json",),
                source_bundles=(bundle,),
                repo_root=root,
            )
        self.assertFalse((root / "cards" / "example.json").exists())
        self.assertFalse((root / "cards" / "example.md").exists())

    def test_empty_or_identity_free_card_is_not_published(self) -> None:
        root = self.temporary_root()
        bundle, bound_source = self.generated(root)
        original = bound_source.read_bytes()
        for index, value in enumerate(
            (
                {section: {} for section in json.loads(bound_source.read_text())},
                {**json.loads(bound_source.read_text()), "identity": {}},
            )
        ):
            source = bound_source
            source.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with self.subTest(index=index), self.assertRaises(ValueError):
                self.module.publish_examples(
                    (f"{source}=cards/example-{index}.json",),
                    source_bundles=(bundle,),
                    repo_root=root,
                )
            source.write_bytes(original)

    def test_nested_audit_keys_cannot_hide_in_benchmark_settings(self) -> None:
        root = self.temporary_root()
        bundle, source = self.generated(root)
        value = json.loads(source.read_text(encoding="utf-8"))
        value["evaluation"]["benchmark_scores"] = [
            {
                "benchmark": "MMLU",
                "metric": "accuracy",
                "score": 0.71,
                "setting": {"environmental_information": {"carbon_emissions": "x"}},
            }
        ]
        source.write_text(json.dumps(value) + "\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.module.publish_examples(
                (f"{source}=cards/example.json",),
                source_bundles=(bundle,),
                repo_root=root,
            )

    def test_schema_valid_raw_card_without_bound_artifact_is_rejected(self) -> None:
        root = self.temporary_root()
        source = root / "raw-card.json"
        source.write_bytes(_card_bytes())
        bundle, _bound_source = self.generated(root / "fixture")
        with self.assertRaisesRegex(ValueError, "card-artifact.json"):
            self.module.publish_examples(
                (f"{source}=cards/example.json",),
                source_bundles=(bundle,),
                repo_root=root,
            )


if __name__ == "__main__":
    unittest.main()
