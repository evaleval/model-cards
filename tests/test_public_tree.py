from pathlib import Path
import subprocess
import unittest


class PublicTreeTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    FORBIDDEN_COMPONENTS = {
        ".claude",
        ".codex",
        "attachments",
        "official-source-bundle",
        "official-source-bundles",
        "official_source_bundle",
        "official_source_bundles",
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
        "family-risk-authorizations.json",
        "pasted-text.txt",
        "provider-execution.json",
        "provider-orchestration.json",
        "provider-result.json",
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
            "nested/official-source-bundle/objects/sha256/ab/source",
            "nested/official_source_bundles/manifest.json",
            "nested/source-freeze/manifest.json",
            "private-candidate-evidence/audit.json",
            "vault/notes.md",
            "attachments/pasted-text.txt",
            ".claude/settings.json",
            ".codex/config.json",
            "nested/CLAUDE.md",
            "nested/AGENTS.md",
            "nested/family-risk-authorizations.json",
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

    def test_cards_directory_contains_only_canonical_json_markdown_pairs(self):
        cards = self.ROOT / "cards"
        json_paths = {path.stem for path in cards.iterdir() if path.suffix == ".json"}
        markdown_paths = {path.stem for path in cards.iterdir() if path.suffix == ".md"}
        self.assertEqual(
            json_paths,
            {
                "deepseek-v3",
                "deepseek-v3-base",
                "gemma-3-4b-it",
                "gemma-3-4b-pt",
                "llama-3.1-8b",
                "llama-3.1-8b-instruct",
                "mistral-7b-instruct-v0.3",
                "mistral-7b-v0.3",
                "olmo-2-1124-7b",
                "olmo-2-1124-7b-instruct",
                "qwen3-8b",
                "qwen3-8b-base",
            },
        )
        self.assertEqual(json_paths, markdown_paths)
        self.assertTrue(
            all(
                path.is_file() and path.suffix in {".json", ".md"}
                for path in cards.iterdir()
            )
        )


if __name__ == "__main__":
    unittest.main()
