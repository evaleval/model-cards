from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_examples.py"
SOURCE_CARD = ROOT / "cards" / "olmo-2-1124-7b.json"


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

    def test_schema_and_privacy_checked_publication_preserves_exact_bytes(self) -> None:
        root = self.temporary_root()
        source = root / "generated.json"
        raw = SOURCE_CARD.read_bytes()
        source.write_bytes(raw)
        mapping = f"{source}=cards/example.json"

        records = self.module.publish_examples((mapping,), repo_root=root)

        self.assertEqual(raw, (root / "cards" / "example.json").read_bytes())
        self.assertEqual("cards/example.json", records[0]["destination"])
        self.assertEqual("generated_unreviewed", records[0]["lifecycle_status"])
        self.assertEqual(records, self.module.publish_examples((mapping,), repo_root=root))

    def test_overwrite_requires_force_and_force_restores_generated_bytes(self) -> None:
        root = self.temporary_root()
        source = root / "generated.json"
        source.write_bytes(SOURCE_CARD.read_bytes())
        destination = root / "cards" / "example.json"
        destination.parent.mkdir()
        destination.write_bytes(b"{}\n")
        mapping = f"{source}=cards/example.json"

        with self.assertRaisesRegex(ValueError, "destination exists"):
            self.module.publish_examples((mapping,), repo_root=root)
        self.module.publish_examples((mapping,), repo_root=root, force=True)
        self.assertEqual(source.read_bytes(), destination.read_bytes())

    def test_sensitive_or_non_contract_card_is_not_published(self) -> None:
        root = self.temporary_root()
        source = root / "generated.json"
        value = json.loads(SOURCE_CARD.read_text(encoding="utf-8"))
        value["identity"]["summary"] = "sk-" + "A" * 24
        source.write_text(json.dumps(value) + "\n", encoding="utf-8")

        with self.assertRaises(ValueError):
            self.module.publish_examples(
                (f"{source}=cards/example.json",), repo_root=root
            )
        self.assertFalse((root / "cards" / "example.json").exists())


if __name__ == "__main__":
    unittest.main()
