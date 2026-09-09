from pathlib import Path
import subprocess
import tempfile
import unittest


class PublicTreeTests(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[1]
    FORBIDDEN_COMPONENTS = {
        ".claude",
        ".codex",
        ".agents",
        ".codex_work",
        "attachments",
        "bundles",
        "memory",
        "tool_output",
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
        "bundle-manifest.json",
    }

    def _git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("git", *arguments),
            cwd=self.ROOT,
            check=False,
            text=True,
            capture_output=True,
        )

    def _require_checkout(self):
        result = self._git("rev-parse", "--show-toplevel")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(result.stdout.strip()).resolve(), self.ROOT.resolve())

    def test_public_file_set_excludes_private_research_material(self):
        self._require_checkout()
        result = self._git("ls-files", "-z", "--cached", "--others", "--exclude-standard")
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = [Path(name) for name in result.stdout.split("\0") if name]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(self.FORBIDDEN_COMPONENTS.isdisjoint(path.parts))
                self.assertNotIn(path.name, self.FORBIDDEN_NAMES)
                self.assertFalse(path.name == ".env" or (
                    path.name.startswith(".env.") and path.name != ".env.example"
                ), path)
                self.assertNotEqual(path.suffix.lower(), ".jsonl", path)
                if path.suffix.lower() == ".pdf":
                    self.assertEqual(path.as_posix(), "assets/model-card-pipeline.pdf")

    def test_gitignore_covers_private_boundary(self):
        self._require_checkout()
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
            "bundles/example/tool_output/hf/example.json",
            "bundles/example/tool_output/docling/paper.json",
            "bundles/example/bundle-manifest.json",
            "custom-output/example/tool_output/hf/example.json",
            "custom-output/example/bundle-manifest.json",
            "runs/example/usage.jsonl",
            ".env.production",
            ".agents/session.json",
            "memory/notes.md",
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

    def test_privacy_checks_run_in_a_linked_worktree_and_reject_forced_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repo"
            repository.mkdir()
            (repository / ".gitignore").write_bytes((self.ROOT / ".gitignore").read_bytes())

            def git(*args):
                return subprocess.run(
                    ["git", "-C", str(repository), *args],
                    check=True, capture_output=True, text=True,
                )

            git("init", "-q")
            git("add", ".gitignore")
            git("-c", "user.name=Test", "-c", "user.email=test@example.org",
                "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
            worktree = Path(temporary) / "worktree"
            git("worktree", "add", "--detach", str(worktree))
            self.assertTrue((worktree / ".git").is_file())
            checker = PublicTreeTests()
            checker.ROOT = worktree
            checker.test_public_file_set_excludes_private_research_material()
            checker.test_gitignore_covers_private_boundary()
            private = worktree / "bundles" / "example" / "bundle-manifest.json"
            private.parent.mkdir(parents=True)
            private.write_text("{}", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "-f", str(private)],
                           check=True, capture_output=True)
            with self.assertRaises(AssertionError):
                checker.test_public_file_set_excludes_private_research_material()

    def test_cards_directory_contains_only_canonical_json_markdown_pairs(self):
        """The corpus grew from a twelve-card roster to a full run, so the invariant is
        checked rather than the file list: every card is a JSON and Markdown pair named
        after the model in lower case, nothing else lives here, and the roster of flagship
        base and instruct pairs is still among them."""
        cards = self.ROOT / "cards"
        json_paths = {path.stem for path in cards.iterdir() if path.suffix == ".json"}
        markdown_paths = {path.stem for path in cards.iterdir() if path.suffix == ".md"}
        self.assertEqual(json_paths, markdown_paths)
        self.assertTrue(json_paths)
        self.assertTrue(all(name == name.lower() for name in json_paths))
        self.assertLessEqual(
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
            json_paths,
        )
        self.assertTrue(
            all(
                path.is_file() and path.suffix in {".json", ".md"}
                for path in cards.iterdir()
            )
        )
