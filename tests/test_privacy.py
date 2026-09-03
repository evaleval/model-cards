from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from model_cards.public_markdown import render_public_markdown
from model_cards.privacy import (
    PrivacyAuditError,
    PrivacyAuditReport,
    PrivacyFindingCode,
    audit_public_tree,
    load_privacy_report,
    serialize_privacy_report,
)


ROOT = Path(__file__).resolve().parents[1]


def _safe_card() -> dict[str, object]:
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
            "num_parameters": "7 billion",
            "input_output": ["text input", "text output"],
        },
        "training_context": {},
        "access_and_adoption": {"access_type": "Public weights"},
        "evaluation": {},
        "links": {
            "model_card": "https://huggingface.co/acme-labs/reference-model"
        },
    }


def _safe_card_bytes() -> bytes:
    return (json.dumps(_safe_card(), ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def _safe_markdown(json_filename: str, raw: bytes) -> str:
    return render_public_markdown(
        json.loads(raw),
        json_filename=json_filename,
        json_sha256=hashlib.sha256(raw).hexdigest(),
    )


class PrivacyAuditTests(unittest.TestCase):
    def temporary_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name)

    def write(self, root: Path, relative: str, content: str | bytes) -> Path:
        path = root.joinpath(*Path(relative).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def codes(self, report: PrivacyAuditReport) -> set[PrivacyFindingCode]:
        return {item.code for item in report.findings}

    def test_safe_code_docs_schema_asset_and_card_pass_deterministically(self) -> None:
        root = self.temporary_root()
        self.write(
            root,
            "README.md",
            "Public documentation explains that /Users/example/private, API keys, "
            "provider traces, and https://user:secret@example.org are prohibited.\n",
        )
        self.write(
            root,
            "src/tool.py",
            'SENSITIVE_PATTERN = r"/Users/|api[_-]?key|provider_trace"\n',
        )
        self.write(
            root,
            "schema/model-card.schema.json",
            json.dumps(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "description": "Provider prompts remain private",
                            "type": "string",
                        }
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self.write(
            root,
            "evaluation/reviewer-packet.schema.json",
            json.dumps(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "properties": {
                        "source_paths_removed": {"const": True},
                        "source_uris_removed": {"const": True},
                    },
                },
                indent=2,
            )
            + "\n",
        )
        self.write(root, "assets/diagram.pdf", b"%PDF-1.4\npublic diagram\n")
        card_raw = _safe_card_bytes()
        self.write(root, "cards/model.json", card_raw)
        self.write(root, "cards/model.md", _safe_markdown("model.json", card_raw))
        files = (
            "README.md",
            "assets/diagram.pdf",
            "cards/model.json",
            "cards/model.md",
            "evaluation/reviewer-packet.schema.json",
            "schema/model-card.schema.json",
            "src/tool.py",
        )
        first = audit_public_tree(root, files)
        second = audit_public_tree(root, tuple(reversed(files)))
        self.assertTrue(first.passed)
        self.assertEqual((), first.findings)
        self.assertEqual(7, first.files_checked)
        self.assertEqual(1, first.cards_checked)
        self.assertEqual(first, second)
        self.assertEqual(first, load_privacy_report(serialize_privacy_report(first)))

    def test_schema_names_do_not_exempt_private_payload_keys(self) -> None:
        for relative in (
            "evaluation/leak.schema.json",
            "evaluation/reviewer-packet.schema.json",
            "schema/unreviewed.json",
        ):
            with self.subTest(relative=relative):
                root = self.temporary_root()
                self.write(
                    root,
                    relative,
                    json.dumps(
                        {
                            "$schema": "https://json-schema.org/draft/2020-12/schema",
                            "type": "object",
                            "source_text": "confidential frozen publisher source body",
                        }
                    )
                    + "\n",
                )
                report = audit_public_tree(root, (relative,))
                self.assertFalse(report.passed)
                self.assertIn(
                    PrivacyFindingCode.JSON_PRIVATE_KEY, self.codes(report)
                )

    def test_reviewed_schema_descriptor_allows_only_its_exact_metadata_key(self) -> None:
        root = self.temporary_root()
        self.write(
            root,
            "src/model_cards/resources/audit-card.schema.json",
            json.dumps(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "x-model-card": {"contract_version": "synthetic-v1"},
                }
            )
            + "\n",
        )
        report = audit_public_tree(
            root, ("src/model_cards/resources/audit-card.schema.json",)
        )
        self.assertTrue(report.passed)

        self.write(
            root,
            "src/model_cards/resources/audit-card.schema.json",
            json.dumps(
                {
                    "$schema": "https://json-schema.org/draft/2020-12/schema",
                    "type": "object",
                    "source_text": "private source body",
                    "x-model-card": {"contract_version": "synthetic-v1"},
                }
            )
            + "\n",
        )
        rejected = audit_public_tree(
            root, ("src/model_cards/resources/audit-card.schema.json",)
        )
        self.assertFalse(rejected.passed)
        self.assertIn(PrivacyFindingCode.JSON_PRIVATE_KEY, self.codes(rejected))

    def test_secret_auth_url_and_real_machine_path_are_hashed_not_copied(self) -> None:
        root = self.temporary_root()
        secret = "A9zK2mP8qR4vT7xW3nL6cD1s"
        authenticated = f"https://production:{secret}@example.org/private"
        local_path = str(Path.home() / ".codex" / "attachments" / "private.txt")
        self.write(
            root,
            "config.json",
            json.dumps(
                {
                    "api_key": secret,
                    "endpoint": authenticated,
                    "artifact": local_path,
                }
            )
            + "\n",
        )
        report = audit_public_tree(root, ("config.json",))
        self.assertFalse(report.passed)
        self.assertTrue(
            {
                PrivacyFindingCode.CREDENTIAL,
                PrivacyFindingCode.AUTHENTICATED_URL,
                PrivacyFindingCode.MACHINE_LOCAL_PATH,
            }.issubset(self.codes(report))
        )
        serialized = serialize_privacy_report(report).decode("utf-8")
        self.assertNotIn(secret, serialized)
        self.assertNotIn(authenticated, serialized)
        self.assertNotIn(local_path, serialized)
        self.assertTrue(all(item.path_sha256 for item in report.findings))
        self.assertTrue(all(item.evidence_sha256 for item in report.findings))

    def test_private_artifact_paths_and_file_types_fail_closed(self) -> None:
        root = self.temporary_root()
        files = {
            ".env": "OPENROUTER_API_KEY=redacted\n",
            "runs/job/progress.md": "private run state\n",
            "attachments/pasted-text-1.txt": "private attachment\n",
            "vault/notes.md": "research notes\n",
            ".claude/settings.json": "{}\n",
            ".codex/handoff.json": "{}\n",
            "source-bundle/README.md": "publisher source body\n",
            "official-source-bundle/objects/sha256/ab/source": "official publisher HTML body\n",
            "official_source_bundle/manifest.json": "{}\n",
            "provider-traces/trace.json": '{"request":{},"response":{}}\n',
            "provider-execution.json": '{"executions":[],"receipt":{}}\n',
            "provider-orchestration.json": '{"provider":"Together"}\n',
            "provider-result.json": '{"provider":"Together"}\n',
            "family-risk-authorizations.json": '{"authorizations":[]}\n',
            "prompt.md": "raw provider prompt\n",
            "codex-handoff.json": "{}\n",
            "usage.jsonl": '{"usage":1}\n',
            "execution.log": "raw provider output\n",
        }
        for relative, content in files.items():
            self.write(root, relative, content)
        report = audit_public_tree(root, tuple(files))
        codes = self.codes(report)
        self.assertFalse(report.passed)
        self.assertIn(PrivacyFindingCode.PRIVATE_PATH_COMPONENT, codes)
        self.assertIn(PrivacyFindingCode.PRIVATE_FILE_NAME, codes)
        self.assertIn(PrivacyFindingCode.FORBIDDEN_ENV, codes)
        self.assertIn(PrivacyFindingCode.FORBIDDEN_JSONL, codes)
        self.assertIn(PrivacyFindingCode.FORBIDDEN_LOG, codes)
        self.assertIn(PrivacyFindingCode.PROVIDER_ARTIFACT, codes)
        self.assertIn(PrivacyFindingCode.JSON_PRIVATE_KEY, codes)

    def test_private_run_control_records_are_never_public_files(self) -> None:
        for name in (
            "family-risk-authorizations.json",
            "provider-execution.json",
            "provider-orchestration.json",
            "provider-result.json",
        ):
            with self.subTest(name=name):
                root = self.temporary_root()
                self.write(root, name, '{}\n')
                report = audit_public_tree(root, (name,))
                self.assertFalse(report.passed)
                self.assertTrue(
                    {
                        PrivacyFindingCode.PRIVATE_FILE_NAME,
                        PrivacyFindingCode.PROVIDER_ARTIFACT,
                    }.issubset(self.codes(report))
                )

    def test_provider_payload_and_source_body_are_rejected_without_path_hints(self) -> None:
        root = self.temporary_root()
        self.write(
            root,
            "trace.json",
            json.dumps(
                {
                    "provider_trace": {"route": "private"},
                    "raw_request": {"prompt": "private source text"},
                    "raw_response": {"output": "raw output"},
                    "usage_ledger": [{"cost": 1}],
                }
            )
            + "\n",
        )
        self.write(root, "paper.pdf", b"%PDF-1.4\nsource paper bytes\n")
        report = audit_public_tree(root, ("paper.pdf", "trace.json"))
        self.assertFalse(report.passed)
        self.assertIn(PrivacyFindingCode.PROVIDER_ARTIFACT, self.codes(report))
        self.assertIn(PrivacyFindingCode.JSON_PRIVATE_KEY, self.codes(report))
        self.assertIn(PrivacyFindingCode.SOURCE_BODY, self.codes(report))
        serialized = serialize_privacy_report(report)
        self.assertNotIn(b"private source text", serialized)
        self.assertNotIn(b"raw output", serialized)

    def test_unsafe_symlinks_are_rejected_but_safe_internal_file_links_are_audited(self) -> None:
        root = self.temporary_root()
        outside = self.temporary_root() / "outside.txt"
        outside.write_text("outside private bytes", encoding="utf-8")
        escaping = root / "escaping.txt"
        escaping.symlink_to(outside)
        self.write(root, "docs/public.txt", "safe public content\n")
        safe = root / "safe-link.txt"
        safe.symlink_to("docs/public.txt")

        report = audit_public_tree(root, ("escaping.txt", "safe-link.txt"))
        self.assertFalse(report.passed)
        unsafe = [
            item for item in report.findings
            if item.code is PrivacyFindingCode.UNSAFE_SYMLINK
        ]
        self.assertEqual(1, len(unsafe))
        self.assertEqual("escaping.txt", unsafe[0].relative_path)
        self.assertEqual(1, report.files_checked)
        self.assertNotIn("outside private bytes", serialize_privacy_report(report).decode())

    def test_absolute_and_broken_symlinks_are_unsafe(self) -> None:
        root = self.temporary_root()
        self.write(root, "target.txt", "public\n")
        (root / "absolute.txt").symlink_to(root / "target.txt")
        (root / "broken.txt").symlink_to("missing.txt")
        report = audit_public_tree(root, ("absolute.txt", "broken.txt"))
        self.assertEqual(
            2,
            sum(
                item.code is PrivacyFindingCode.UNSAFE_SYMLINK
                for item in report.findings
            ),
        )

    def test_non_sanitized_json_duplicate_nonfinite_and_malformed_are_explicit(self) -> None:
        root = self.temporary_root()
        self.write(root, "duplicate.json", b'{"a":1,"a":2}\n')
        self.write(root, "nonfinite.json", b'{"score":NaN}\n')
        self.write(root, "malformed.json", b'{"open": true\n')
        self.write(root, "utf8.json", b'{"value":"\xff"}\n')
        report = audit_public_tree(
            root,
            ("duplicate.json", "malformed.json", "nonfinite.json", "utf8.json"),
        )
        self.assertEqual(
            {
                PrivacyFindingCode.JSON_DUPLICATE_KEY,
                PrivacyFindingCode.JSON_MALFORMED,
                PrivacyFindingCode.JSON_NONFINITE_NUMBER,
                PrivacyFindingCode.JSON_INVALID_UTF8,
            },
            self.codes(report),
        )

    def test_every_card_uses_packaged_schema_runtime_and_export_privacy_boundary(self) -> None:
        root = self.temporary_root()
        card = _safe_card()
        card["source_bundle"] = {"source_text": "private publisher body"}
        self.write(root, "cards/unsafe.json", json.dumps(card) + "\n")
        self.write(root, "cards/notes.md", "not a public JSON card\n")
        self.write(root, "cards/asset.txt", "arbitrary non-card file\n")
        report = audit_public_tree(root)
        codes = self.codes(report)
        self.assertEqual(1, report.cards_checked)
        self.assertIn(PrivacyFindingCode.CARD_SCHEMA_INVALID, codes)
        self.assertIn(PrivacyFindingCode.CARD_RUNTIME_INVALID, codes)
        self.assertIn(PrivacyFindingCode.CARD_PRIVACY_INVALID, codes)
        self.assertIn(PrivacyFindingCode.CARD_MARKDOWN_INVALID, codes)
        self.assertIn(PrivacyFindingCode.CARD_NON_JSON, codes)
        self.assertIn(PrivacyFindingCode.JSON_PRIVATE_KEY, codes)
        serialized = serialize_privacy_report(report)
        self.assertNotIn(b"private publisher body", serialized)

        malformed_root = self.temporary_root()
        self.write(malformed_root, "cards/broken.json", '{"broken":\n')
        malformed = audit_public_tree(malformed_root)
        self.assertEqual(1, malformed.cards_checked)
        self.assertIn(PrivacyFindingCode.JSON_MALFORMED, self.codes(malformed))
        self.assertIn(PrivacyFindingCode.CARD_SCHEMA_INVALID, self.codes(malformed))

    def test_markdown_companion_must_exactly_match_its_public_json(self) -> None:
        root = self.temporary_root()
        raw = _safe_card_bytes()
        self.write(root, "cards/model.json", raw)
        self.write(root, "cards/model.md", _safe_markdown("model.json", raw))
        valid = audit_public_tree(root)
        self.assertTrue(valid.passed)
        self.assertEqual(1, valid.cards_checked)

        self.write(root, "cards/model.md", "# Tampered card\n")
        tampered = audit_public_tree(root)
        self.assertEqual(
            {PrivacyFindingCode.CARD_MARKDOWN_INVALID}, self.codes(tampered)
        )

        orphan_root = self.temporary_root()
        self.write(orphan_root, "cards/orphan.md", "# Orphan\n")
        orphan = audit_public_tree(orphan_root)
        self.assertEqual(
            {PrivacyFindingCode.CARD_MARKDOWN_INVALID}, self.codes(orphan)
        )

        json_only_root = self.temporary_root()
        self.write(json_only_root, "cards/orphan.json", raw)
        json_only = audit_public_tree(json_only_root)
        self.assertEqual(
            {PrivacyFindingCode.CARD_MARKDOWN_INVALID}, self.codes(json_only)
        )

        scoped_root = self.temporary_root()
        self.write(scoped_root, "cards/model.json", raw)
        self.write(scoped_root, "cards/model.md", _safe_markdown("model.json", raw))
        json_scope = audit_public_tree(scoped_root, ("cards/model.json",))
        markdown_scope = audit_public_tree(scoped_root, ("cards/model.md",))
        self.assertEqual(
            {PrivacyFindingCode.CARD_MARKDOWN_INVALID}, self.codes(json_scope)
        )
        self.assertEqual(
            {PrivacyFindingCode.CARD_MARKDOWN_INVALID}, self.codes(markdown_scope)
        )

    def test_nested_cards_entries_never_bypass_public_card_checks(self) -> None:
        root = self.temporary_root()
        audit_card = _safe_card()
        audit_card["environmental_information"] = {"carbon_emissions": "hidden"}
        self.write(root, "cards/archive/audit-card.json", json.dumps(audit_card) + "\n")
        self.write(root, "cards/archive/readme.md", "nested card material\n")

        report = audit_public_tree(root)
        self.assertEqual(0, report.cards_checked)
        self.assertIn(PrivacyFindingCode.CARD_NON_JSON, self.codes(report))
        self.assertIn(PrivacyFindingCode.JSON_PRIVATE_KEY, self.codes(report))

    def test_audit_contract_card_is_not_a_valid_public_card(self) -> None:
        root = self.temporary_root()
        card = _safe_card()
        card["lifecycle"] = {"status": "generated_unreviewed"}
        self.write(root, "cards/model.json", json.dumps(card) + "\n")

        report = audit_public_tree(root)
        self.assertTrue(
            {
                PrivacyFindingCode.CARD_SCHEMA_INVALID,
                PrivacyFindingCode.CARD_RUNTIME_INVALID,
            }.issubset(self.codes(report))
        )

    def test_tree_scope_sees_run_artifacts_while_explicit_scope_is_exact(self) -> None:
        root = self.temporary_root()
        self.write(root, "README.md", "safe\n")
        self.write(root, "runs/private/progress.md", "private\n")
        tree = audit_public_tree(root)
        explicit = audit_public_tree(root, ("README.md",))
        self.assertEqual("tree", tree.scope)
        self.assertFalse(tree.passed)
        self.assertEqual("explicit_file_list", explicit.scope)
        self.assertTrue(explicit.passed)

    def test_missing_file_and_bad_explicit_paths_do_not_escape_root(self) -> None:
        root = self.temporary_root()
        report = audit_public_tree(root, ("missing.txt",))
        self.assertEqual({PrivacyFindingCode.MISSING_FILE}, self.codes(report))
        for paths in (("../outside",), ("/absolute",), ("a\\b",), ("same", "same")):
            with self.subTest(paths=paths), self.assertRaises(PrivacyAuditError):
                audit_public_tree(root, paths)

    def test_report_is_closed_canonical_and_content_addressed(self) -> None:
        root = self.temporary_root()
        self.write(root, "README.md", "safe\n")
        report = audit_public_tree(root)
        payload = serialize_privacy_report(report)
        raw = json.loads(payload)
        raw["files_checked"] += 1
        tampered = json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n"
        with self.assertRaises(PrivacyAuditError):
            load_privacy_report(tampered)
        raw = json.loads(payload)
        raw["unexpected"] = True
        opened = json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n"
        with self.assertRaisesRegex(PrivacyAuditError, "closed object"):
            load_privacy_report(opened)
        with self.assertRaisesRegex(PrivacyAuditError, "non-canonical"):
            load_privacy_report(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    unittest.main()
