from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
from unittest import mock
import unittest

from model_cards.public_markdown import render_public_markdown
from model_cards.publication_schema import validate_publication_card
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "regenerate_frozen_examples.py"
COMMIT = "a" * 40


def _json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class _FrozenAdapter:
    def __init__(self, model_id: str, *, rich: bool = True) -> None:
        self.model_id = model_id
        self.rich = rich

    def resolve_revision(self, model_id, requested_revision):
        if model_id != self.model_id or requested_revision != COMMIT:
            raise AssertionError("unexpected synthetic exact target")
        return COMMIT

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        metadata = {
            "id": self.model_id,
            "modelId": self.model_id,
            "sha": COMMIT,
            "siblings": [
                {"rfilename": "README.md"},
                {"rfilename": "config.json"},
            ],
        }
        if self.rich:
            metadata.update(
                {
                    "author": self.model_id.split("/", 1)[0],
                    "pipeline_tag": "text-generation",
                    "private": False,
                    "gated": False,
                    "downloads": 1234,
                    "likes": 56,
                    "tags": [
                        "license:apache-2.0",
                        "arxiv:2401.12345",
                        "base_model:acme/Example-Base",
                    ],
                    "cardData": {
                        "license": "apache-2.0",
                        "datasets": ["acme/training-set"],
                        "base_model": "acme/Example-Base",
                    },
                    "safetensors": {
                        "parameters": {"BF16": 1_073_741_824},
                        "total": 1_073_741_824,
                    },
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                        {"rfilename": "model.safetensors"},
                    ],
                }
            )
        return RemoteObject(FetchStatus.OK, _json_bytes(metadata))

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    f"# {self.model_id.rsplit('/', 1)[-1]}\n\n"
                    f"{self.model_id} is a frozen synthetic language model fixture.\n\n"
                    "- Context Length: 8,192 tokens\n\n"
                    "[Code repository](https://github.com/acme/example)\n\n"
                    "```bibtex\n"
                    "@misc{example2024, title={Example Technical Report}, "
                    "author={Acme}, year={2024}, eprint={2401.12345}}\n"
                    "```\n"
                ).encode("utf-8"),
            )
        if repo_path == "config.json":
            value = (
                {
                    "architectures": ["ExampleForCausalLM"],
                    "model_type": "example",
                    "max_position_embeddings": 4096,
                    "n_routed_experts": 8,
                    "num_experts_per_tok": 2,
                }
                if self.rich
                else {}
            )
            return RemoteObject(FetchStatus.OK, _json_bytes(value))
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


def _load_script():
    specification = importlib.util.spec_from_file_location(
        "regenerate_frozen_examples_script", SCRIPT
    )
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


class RegenerateFrozenExamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_script()

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.pilot = self.root / "pilot"
        self.repo = self.root / "repository"
        self.run_output = self.root / "private-batch"
        self.pilot.mkdir()
        self.repo.mkdir()

    def bundle(self, target_name: str, model_id: str, *, rich: bool = True) -> Path:
        destination = self.pilot / target_name / "source-bundle"
        destination.parent.mkdir()
        collect_hf_source_bundle(
            model_id,
            destination,
            _FrozenAdapter(model_id, rich=rich),
            revision=COMMIT,
        )
        return destination

    def test_provider_free_batch_replays_and_publishes_exact_pairs(self) -> None:
        self.bundle("target-example", "acme/Example-Instruct")
        with mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network attempted")
        ):
            first = self.module.regenerate_frozen_examples(
                pilot_root=self.pilot,
                run_output=self.run_output,
                repo_root=self.repo,
            )

        self.assertEqual(1, len(first))
        json_path = self.repo / first[0]["destination"]
        markdown_path = self.repo / first[0]["markdown_destination"]
        self.assertTrue(json_path.is_file())
        self.assertTrue(markdown_path.is_file())
        raw = json_path.read_bytes()
        card = json.loads(raw)
        validate_publication_card(card)
        self.assertGreaterEqual(self.module.specified_field_count(card), 15)
        self.assertEqual("acme/Example-Instruct", card["identity"]["model_id"])
        self.assertEqual(COMMIT, card["identity"]["version"])
        self.assertEqual(
            render_public_markdown(
                card,
                json_filename=json_path.name,
                json_sha256=hashlib.sha256(raw).hexdigest(),
            ).encode("utf-8"),
            markdown_path.read_bytes(),
        )
        run_dir = next((self.run_output / "targets").iterdir())
        self.assertEqual(b"", (run_dir / "usage.jsonl").read_bytes())
        journal_before = (run_dir / "journal.jsonl").read_bytes()

        with mock.patch.object(
            socket, "create_connection", side_effect=AssertionError("network attempted")
        ):
            second = self.module.regenerate_frozen_examples(
                pilot_root=self.pilot,
                run_output=self.run_output,
                repo_root=self.repo,
            )
        self.assertEqual(first, second)
        self.assertEqual(raw, json_path.read_bytes())
        self.assertEqual(journal_before, (run_dir / "journal.jsonl").read_bytes())

    def test_full_batch_is_preflighted_before_any_card_is_published(self) -> None:
        self.bundle("target-rich", "acme/Rich-Instruct")
        self.bundle("target-sparse", "acme/Sparse", rich=False)

        with self.assertRaisesRegex(ValueError, "specified-field floor"):
            self.module.regenerate_frozen_examples(
                pilot_root=self.pilot,
                run_output=self.run_output,
                repo_root=self.repo,
            )
        self.assertFalse((self.repo / "cards").exists())

    def test_duplicate_model_ids_fail_before_private_runs_or_publication(self) -> None:
        self.bundle("target-one", "acme/Duplicate")
        self.bundle("target-two", "acme/Duplicate")

        with self.assertRaisesRegex(ValueError, "unique model IDs"):
            self.module.regenerate_frozen_examples(
                pilot_root=self.pilot,
                run_output=self.run_output,
                repo_root=self.repo,
            )
        self.assertFalse(self.run_output.exists())
        self.assertFalse((self.repo / "cards").exists())

    def test_same_basename_is_safely_and_deterministically_disambiguated(self) -> None:
        first = self.module.destination_filename_map(
            ("one-org/Same-Model", "other-org/same-model")
        )
        second = self.module.destination_filename_map(reversed(tuple(first)))
        self.assertEqual(first, second)
        self.assertEqual(2, len({name.casefold() for name in first.values()}))
        self.assertTrue(all(name.endswith(".json") for name in first.values()))
        self.assertTrue(all(name == name.lower() for name in first.values()))
        self.assertTrue(
            all("/" not in name and "\\" not in name for name in first.values())
        )


if __name__ == "__main__":
    unittest.main()
