from pathlib import Path
import subprocess
import unittest


class PublicTreeTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    FORBIDDEN_COMPONENTS = {
        ".claude",
        ".codex",
        "attachments",
        "private-candidate-evidence",
        "provider-traces",
        "source-bundle",
        "source-bundles",
        "source-freeze",
        "source_bundle",
        "source_bundles",
        "vault",
    }
    FORBIDDEN_NAMES = {
        "AGENTS.md",
        "CLAUDE.md",
        "CODEX.md",
        "pasted-text.txt",
        "source-bundle.json",
        "source_bundle.json",
    }

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("git", *arguments),
            cwd=self.ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def test_public_file_set_excludes_private_research_material(self):
        if not (self.ROOT / ".git").is_dir():
            self.skipTest("tracked-file check requires a Git checkout")
        result = self._git("ls-files", "--cached", "--others", "--exclude-standard")
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = [Path(line) for line in result.stdout.splitlines() if line]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(self.FORBIDDEN_COMPONENTS.isdisjoint(path.parts))
                self.assertNotIn(path.name, self.FORBIDDEN_NAMES)
                if path.suffix.lower() == ".pdf":
                    self.assertEqual(path.as_posix(), "assets/model-card-pipeline.pdf")

    def test_gitignore_covers_private_boundary(self):
        if not (self.ROOT / ".git").is_dir():
            self.skipTest("gitignore check requires a Git checkout")
        should_ignore = (
            "source_bundle/source-bundle.json",
            "nested/source-bundles/source.json",
            "nested/source-freeze/manifest.json",
            "private-candidate-evidence/audit.json",
            "vault/notes.md",
            "attachments/pasted-text.txt",
            ".claude/settings.json",
            ".codex/config.json",
            "nested/CLAUDE.md",
            "nested/AGENTS.md",
            "assets/unreviewed.pdf",
        )
        for path in should_ignore:
            with self.subTest(path=path):
                result = self._git("check-ignore", "--no-index", "--quiet", path)
                self.assertEqual(result.returncode, 0, path)

        allowed = self._git(
            "check-ignore",
            "--no-index",
            "--quiet",
            "assets/model-card-pipeline.pdf",
        )
        self.assertEqual(allowed.returncode, 1)

    def test_cards_directory_contains_only_canonical_json_examples(self):
        cards = self.ROOT / "cards"
        self.assertEqual(
            {path.name for path in cards.iterdir()},
            {
                "olmo-2-1124-7b.json",
                "olmo-2-1124-7b-instruct.json",
            },
        )
        self.assertTrue(
            all(path.is_file() and path.suffix == ".json" for path in cards.iterdir())
        )


if __name__ == "__main__":
    unittest.main()
