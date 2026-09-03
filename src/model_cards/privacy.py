"""Deterministic privacy audit for a proposed public repository tree.

The audit reports only portable paths, stable codes, and cryptographic hashes.
Matched credentials, source text, prompts, provider payloads, and machine paths
are never copied into a finding.  Callers can audit a directory snapshot or an
explicit list such as the output of ``git ls-files``; no Git subprocess or
network access is required.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
from typing import Any, Iterable, Sequence

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .public_markdown import render_public_markdown
from .public_export import PublicExportError, assert_public_projection
from .publication_schema import (
    PUBLICATION_SCHEMA,
    PublicationValidationError,
    validate_publication_card,
)


PRIVACY_AUDIT_VERSION = "public-tree-privacy/v1"
DEFAULT_MAX_FILE_BYTES = 10_000_000

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_REPORT_ID_RE = re.compile(r"^privacy_report_[0-9a-f]{32}$")
_FINDING_ID_RE = re.compile(r"^privacy_finding_[0-9a-f]{24}$")

# Environment/build trees are not proposed public files.  An explicit file
# list is never pruned, so a caller can still audit any of them deliberately.
_TREE_CONTROL_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
    }
)

_PRIVATE_COMPONENTS = frozenset(
    {
        ".claude",
        ".codex",
        "attachment",
        "attachments",
        "handoff",
        "handoffs",
        "official-source-bundle",
        "official-source-bundles",
        "official_source_bundle",
        "official_source_bundles",
        "private-candidate-evidence",
        "provider-trace",
        "provider-traces",
        "provider_trace",
        "provider_traces",
        "run-artifacts",
        "run_artifacts",
        "runs",
        "source-bodies",
        "source-bundle",
        "source-bundles",
        "source-freeze",
        "source_bodies",
        "source_bundle",
        "source_bundles",
        "source_freeze",
        "vault",
    }
)

_PRIVATE_NAMES = frozenset(
    {
        "agents.md",
        "claude.md",
        "codex.md",
        "family-risk-authorizations.json",
        "handoff.md",
        "provider-execution.json",
        "provider-orchestration.json",
        "provider-result.json",
        "source-bundle.json",
        "source_bundle.json",
        "usage.jsonl",
        "usage-ledger.jsonl",
        "usage_ledger.jsonl",
    }
)

_PRIVATE_JSON_KEYS = frozenset(
    {
        "authorization",
        "authorization_header",
        "authorization_sha256",
        "bindings",
        "context_after",
        "context_before",
        "contract_version",
        "cost_ledger",
        "evidence",
        "environmental_information",
        "exact_text",
        "lifecycle",
        "omission_review_events",
        "prompt",
        "provenance",
        "provider_trace",
        "raw_prompt",
        "raw_request",
        "raw_response",
        "request",
        "response",
        "reviews",
        "snapshot_path",
        "source_bundle",
        "source_content",
        "source_text",
        "surrounding_context",
        "system_prompt",
        "usage_ledger",
        "use_and_risk",
        "validation",
        "validation_checks",
    }
)

# JSON Schema contracts may legitimately *name* private fields in a
# ``properties`` map to forbid or describe them.  Only these reviewed repository
# locations receive that narrow, schema-aware treatment.  A filename suffix or
# a directory named ``schema`` is not sufficient: arbitrary JSON there remains
# subject to the ordinary private-key scan.
_JSON_SCHEMA_CONTRACT_PATHS = frozenset(
    {
        "schema/model-card.schema.json",
        "src/model_cards/resources/audit-card.schema.json",
        "src/model_cards/resources/model-card.schema.json",
        "evaluation/annotation.schema.json",
        "evaluation/item-manifest.schema.json",
        "evaluation/paired-audit-labels.schema.json",
        "evaluation/paired-audit-target-map.schema.json",
        "evaluation/reviewer-packet.schema.json",
        "evaluation/target-sheet.schema.json",
    }
)
_JSON_SCHEMA_NAME_MAP_KEYS = frozenset(
    {
        "$defs",
        "definitions",
        "dependentRequired",
        "dependentSchemas",
        "patternProperties",
        "properties",
    }
)
_JSON_SCHEMA_DESCRIPTOR_PRIVATE_KEYS = frozenset(
    {
        ("$.x-model-card", "contract_version"),
    }
)

_CODE_OR_DOC_SUFFIXES = frozenset(
    {
        ".c",
        ".cc",
        ".cfg",
        ".css",
        ".go",
        ".h",
        ".html",
        ".ini",
        ".java",
        ".js",
        ".md",
        ".py",
        ".rst",
        ".sh",
        ".toml",
        ".ts",
        ".tsx",
        ".yaml",
        ".yml",
    }
)
_SOURCE_CODE_SUFFIXES = frozenset(
    {".c", ".cc", ".go", ".h", ".java", ".js", ".py", ".sh", ".ts", ".tsx"}
)

_TOKEN_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"(?<![A-Za-z0-9])hf_[A-Za-z0-9]{20,}"),
    re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_ASSIGNMENT_RE = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|client[_-]?secret)"
    r"\s*[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_./+=-]{16,})"
)
_BEARER_RE = re.compile(r"(?i)\bbearer\s+([A-Za-z0-9._~+/-]{20,})")
_BASIC_AUTH_RE = re.compile(
    r"(?i)\bauthorization\s*:\s*basic\s+([A-Za-z0-9+/]{16,}={0,2})"
)
_AUTH_URL_RE = re.compile(r"https?://([^\s/@:]+):([^\s/@]+)@[^\s/]+")
_GENERIC_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:file://|(?:^|[\s\"'])~[/\\]|[A-Z]:[\\/]Users[\\/]"
    r"|/Users/[^/\s]+/|/home/[^/\s]+/|/private/var/folders/|/var/folders/)"
)

_PLACEHOLDER_TERMS = frozenset(
    {
        "changeme",
        "example",
        "fake",
        "not-read-by-fixture",
        "placeholder",
        "private",
        "redacted",
        "secret",
        "synthetic",
        "test",
        "token",
        "user",
        "username",
        "your",
    }
)


class PrivacyAuditError(ValueError):
    """The audit request or a serialized report is malformed."""


class PrivacyFindingCode(str, Enum):
    PRIVATE_PATH_COMPONENT = "private_path_component"
    PRIVATE_FILE_NAME = "private_file_name"
    FORBIDDEN_JSONL = "forbidden_jsonl"
    FORBIDDEN_LOG = "forbidden_log"
    FORBIDDEN_ENV = "forbidden_env"
    PROVIDER_ARTIFACT = "provider_artifact"
    SOURCE_BODY = "source_body"
    UNSAFE_SYMLINK = "unsafe_symlink"
    MISSING_FILE = "missing_file"
    UNSAFE_FILE_TYPE = "unsafe_file_type"
    FILE_TOO_LARGE = "file_too_large"
    CREDENTIAL = "credential"
    AUTHENTICATED_URL = "authenticated_url"
    MACHINE_LOCAL_PATH = "machine_local_path"
    JSON_INVALID_UTF8 = "json_invalid_utf8"
    JSON_MALFORMED = "json_malformed"
    JSON_DUPLICATE_KEY = "json_duplicate_key"
    JSON_NONFINITE_NUMBER = "json_nonfinite_number"
    JSON_PRIVATE_KEY = "json_private_key"
    CARD_SCHEMA_INVALID = "card_schema_invalid"
    CARD_RUNTIME_INVALID = "card_runtime_invalid"
    CARD_PRIVACY_INVALID = "card_privacy_invalid"
    CARD_MARKDOWN_INVALID = "card_markdown_invalid"
    CARD_NON_JSON = "card_non_json"


@dataclass(frozen=True)
class PrivacyFinding:
    finding_id: str
    code: PrivacyFindingCode
    relative_path: str
    path_sha256: str
    content_sha256: str | None
    evidence_sha256: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "code", PrivacyFindingCode(self.code))
        except (TypeError, ValueError) as exc:
            raise PrivacyAuditError("privacy finding code is invalid") from exc
        _validate_relative_path(self.relative_path)
        for name in ("path_sha256", "evidence_sha256"):
            if not isinstance(getattr(self, name), str) or not _SHA256_RE.fullmatch(
                getattr(self, name)
            ):
                raise PrivacyAuditError(f"privacy finding {name} is invalid")
        if self.content_sha256 is not None and not _SHA256_RE.fullmatch(
            self.content_sha256
        ):
            raise PrivacyAuditError("privacy finding content_sha256 is invalid")
        expected = _finding_id(
            self.code,
            self.relative_path,
            self.path_sha256,
            self.content_sha256,
            self.evidence_sha256,
        )
        if not _FINDING_ID_RE.fullmatch(self.finding_id) or self.finding_id != expected:
            raise PrivacyAuditError("privacy finding id does not match content")

    def to_dict(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "code": self.code.value,
            "relative_path": self.relative_path,
            "path_sha256": self.path_sha256,
            "content_sha256": self.content_sha256,
            "evidence_sha256": self.evidence_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PrivacyFinding":
        item = _strict_object(
            value,
            {
                "finding_id",
                "code",
                "relative_path",
                "path_sha256",
                "content_sha256",
                "evidence_sha256",
            },
            "privacy finding",
        )
        return cls(**item)


@dataclass(frozen=True)
class PrivacyAuditReport:
    report_version: str
    report_id: str
    scope: str
    file_set_sha256: str
    files_checked: int
    bytes_checked: int
    cards_checked: int
    findings: tuple[PrivacyFinding, ...]
    passed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "findings", tuple(self.findings))
        if self.report_version != PRIVACY_AUDIT_VERSION:
            raise PrivacyAuditError("privacy report version is unsupported")
        if self.scope not in {"tree", "explicit_file_list"}:
            raise PrivacyAuditError("privacy report scope is invalid")
        if not _SHA256_RE.fullmatch(self.file_set_sha256):
            raise PrivacyAuditError("privacy report file_set_sha256 is invalid")
        for name in ("files_checked", "bytes_checked", "cards_checked"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PrivacyAuditError(f"privacy report {name} is invalid")
        if not all(isinstance(item, PrivacyFinding) for item in self.findings):
            raise PrivacyAuditError("privacy report findings are invalid")
        expected_order = tuple(
            sorted(
                self.findings,
                key=lambda item: (
                    item.relative_path,
                    item.code.value,
                    item.evidence_sha256,
                    item.finding_id,
                ),
            )
        )
        if self.findings != expected_order:
            raise PrivacyAuditError("privacy report findings are not canonical")
        finding_ids = [item.finding_id for item in self.findings]
        if len(finding_ids) != len(set(finding_ids)):
            raise PrivacyAuditError("privacy report contains duplicate findings")
        if not isinstance(self.passed, bool) or self.passed != (not self.findings):
            raise PrivacyAuditError("privacy report pass status is inconsistent")
        expected = _report_id(
            scope=self.scope,
            file_set_sha256=self.file_set_sha256,
            files_checked=self.files_checked,
            bytes_checked=self.bytes_checked,
            cards_checked=self.cards_checked,
            findings=self.findings,
            passed=self.passed,
        )
        if not _REPORT_ID_RE.fullmatch(self.report_id) or self.report_id != expected:
            raise PrivacyAuditError("privacy report id does not match content")

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "report_id": self.report_id,
            "scope": self.scope,
            "file_set_sha256": self.file_set_sha256,
            "files_checked": self.files_checked,
            "bytes_checked": self.bytes_checked,
            "cards_checked": self.cards_checked,
            "findings": [item.to_dict() for item in self.findings],
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PrivacyAuditReport":
        item = _strict_object(
            value,
            {
                "report_version",
                "report_id",
                "scope",
                "file_set_sha256",
                "files_checked",
                "bytes_checked",
                "cards_checked",
                "findings",
                "passed",
            },
            "privacy report",
        )
        if not isinstance(item["findings"], list):
            raise PrivacyAuditError("privacy report findings must be a list")
        return cls(
            report_version=item["report_version"],
            report_id=item["report_id"],
            scope=item["scope"],
            file_set_sha256=item["file_set_sha256"],
            files_checked=item["files_checked"],
            bytes_checked=item["bytes_checked"],
            cards_checked=item["cards_checked"],
            findings=tuple(PrivacyFinding.from_dict(v) for v in item["findings"]),
            passed=item["passed"],
        )


@dataclass(frozen=True)
class _FileSnapshot:
    relative_path: str
    path: Path
    kind: str
    content: bytes | None
    content_sha256: str | None
    byte_size: int
    symlink_target: str | None


class _DuplicateJsonKey(ValueError):
    pass


class _NonfiniteJsonNumber(ValueError):
    pass


def audit_public_tree(
    repo_root: str | os.PathLike[str],
    tracked_files: Sequence[str | os.PathLike[str]] | None = None,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
) -> PrivacyAuditReport:
    """Audit a public tree or explicit portable file list without copying secrets.

    ``tracked_files`` paths are relative to ``repo_root``.  Omitting it walks
    the supplied tree while pruning only VCS, dependency, and build caches.
    Private run/source directories are intentionally *not* pruned: if present
    in the proposed tree they produce findings.
    """

    root = Path(repo_root)
    if root.is_symlink() or not root.is_dir():
        raise PrivacyAuditError("repo_root must be a real directory")
    root = root.resolve()
    if isinstance(max_file_bytes, bool) or not isinstance(max_file_bytes, int) \
            or max_file_bytes <= 0:
        raise PrivacyAuditError("max_file_bytes must be a positive integer")
    if tracked_files is None:
        relative_paths = _walk_tree(root)
        scope = "tree"
    else:
        relative_paths = _normalize_explicit_paths(tracked_files)
        scope = "explicit_file_list"
    audited_paths = frozenset(relative_paths)

    Draft202012Validator.check_schema(PUBLICATION_SCHEMA)
    card_validator = Draft202012Validator(
        PUBLICATION_SCHEMA, format_checker=FormatChecker()
    )

    findings: list[PrivacyFinding] = []
    inventory: list[dict[str, Any]] = []
    files_checked = 0
    bytes_checked = 0
    cards_checked = 0
    machine_prefixes = _machine_prefixes(root)

    for relative in relative_paths:
        path = root.joinpath(*PurePosixPath(relative).parts)
        snapshot, snapshot_findings = _snapshot_file(
            root, relative, path, max_file_bytes=max_file_bytes
        )
        findings.extend(snapshot_findings)
        inventory.append(
            {
                "relative_path": relative,
                "path_sha256": _sha256(relative.encode("utf-8")),
                "kind": snapshot.kind,
                "content_sha256": snapshot.content_sha256,
                "byte_size": snapshot.byte_size,
                "symlink_target_sha256": (
                    None
                    if snapshot.symlink_target is None
                    else _sha256(
                        snapshot.symlink_target.encode(
                            "utf-8", errors="surrogateescape"
                        )
                    )
                ),
            }
        )
        findings.extend(_path_findings(snapshot))
        is_card = _is_card_path(relative)
        is_card_markdown = _is_card_markdown_path(relative)
        if is_card:
            cards_checked += 1
        elif _is_cards_entry(relative) and not is_card_markdown:
            findings.append(_finding(snapshot, PrivacyFindingCode.CARD_NON_JSON, relative))
        if snapshot.content is None:
            if is_card:
                findings.append(
                    _finding(
                        snapshot,
                        PrivacyFindingCode.CARD_SCHEMA_INVALID,
                        "card_content_unavailable",
                    )
                )
            continue
        files_checked += 1
        bytes_checked += snapshot.byte_size
        findings.extend(_content_findings(snapshot, machine_prefixes))
        json_value, json_findings = _json_audit(snapshot)
        findings.extend(json_findings)
        if is_card:
            findings.extend(
                _card_findings(snapshot, json_value, card_validator)
            )
            findings.extend(
                _card_json_pair_findings(
                    root,
                    snapshot,
                    json_value,
                    audited_paths=audited_paths,
                )
            )
        elif is_card_markdown:
            findings.extend(
                _card_markdown_findings(
                    root,
                    snapshot,
                    audited_paths=audited_paths,
                )
            )

    ordered = tuple(
        sorted(
            _deduplicate_findings(findings),
            key=lambda item: (
                item.relative_path,
                item.code.value,
                item.evidence_sha256,
                item.finding_id,
            ),
        )
    )
    file_set_sha256 = _sha256(_canonical_json(inventory))
    passed = not ordered
    report_id = _report_id(
        scope=scope,
        file_set_sha256=file_set_sha256,
        files_checked=files_checked,
        bytes_checked=bytes_checked,
        cards_checked=cards_checked,
        findings=ordered,
        passed=passed,
    )
    return PrivacyAuditReport(
        report_version=PRIVACY_AUDIT_VERSION,
        report_id=report_id,
        scope=scope,
        file_set_sha256=file_set_sha256,
        files_checked=files_checked,
        bytes_checked=bytes_checked,
        cards_checked=cards_checked,
        findings=ordered,
        passed=passed,
    )


def serialize_privacy_report(report: PrivacyAuditReport) -> bytes:
    if not isinstance(report, PrivacyAuditReport):
        raise PrivacyAuditError("report must be a PrivacyAuditReport")
    return _canonical_json(report.to_dict())


def load_privacy_report(payload: bytes | str) -> PrivacyAuditReport:
    if isinstance(payload, str):
        raw = payload.encode("utf-8")
    elif isinstance(payload, bytes):
        raw = payload
    else:
        raise PrivacyAuditError("privacy report payload must be bytes or text")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, PrivacyAuditError):
        raise PrivacyAuditError("privacy report is not strict JSON") from None
    if raw != _canonical_json(value):
        raise PrivacyAuditError("privacy report is stale or non-canonical")
    return PrivacyAuditReport.from_dict(value)


def _walk_tree(root: Path) -> tuple[str, ...]:
    result: list[str] = []

    def visit(directory: Path, prefix: PurePosixPath) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as exc:
            raise PrivacyAuditError("cannot enumerate public tree") from exc
        for entry in entries:
            relative_path = prefix / entry.name if prefix.parts else PurePosixPath(entry.name)
            relative = relative_path.as_posix()
            if entry.is_symlink():
                result.append(relative)
            elif entry.is_dir(follow_symlinks=False):
                if entry.name.casefold() not in _TREE_CONTROL_DIRS \
                        and not entry.name.casefold().endswith(".egg-info"):
                    visit(Path(entry.path), relative_path)
            else:
                result.append(relative)

    visit(root, PurePosixPath())
    return tuple(result)


def _normalize_explicit_paths(
    paths: Sequence[str | os.PathLike[str]],
) -> tuple[str, ...]:
    if isinstance(paths, (str, bytes, os.PathLike)):
        raise PrivacyAuditError("tracked_files must be a sequence of relative paths")
    normalized = []
    for raw in paths:
        value = os.fspath(raw)
        if not isinstance(value, str):
            raise PrivacyAuditError("tracked file path must be text")
        _validate_relative_path(value)
        normalized.append(value)
    if len(normalized) != len(set(normalized)):
        raise PrivacyAuditError("tracked_files contains duplicates")
    return tuple(sorted(normalized))


def _snapshot_file(
    root: Path,
    relative: str,
    path: Path,
    *,
    max_file_bytes: int,
) -> tuple[_FileSnapshot, list[PrivacyFinding]]:
    findings: list[PrivacyFinding] = []
    path_hash = _sha256(relative.encode("utf-8"))
    if path.is_symlink():
        try:
            target = os.readlink(path)
        except OSError:
            target = "unreadable-symlink"
        link_hash = _sha256(target.encode("utf-8", errors="surrogateescape"))
        unsafe = False
        if os.path.isabs(target):
            unsafe = True
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
        except (OSError, RuntimeError, ValueError):
            unsafe = True
            resolved = None
        if resolved is not None and (
            not resolved.is_file() or resolved.is_symlink()
        ):
            unsafe = True
        if unsafe:
            snapshot = _FileSnapshot(
                relative, path, "unsafe_symlink", None, link_hash, 0, target
            )
            findings.append(
                _finding_from_parts(
                    relative,
                    PrivacyFindingCode.UNSAFE_SYMLINK,
                    path_hash,
                    link_hash,
                    target.encode("utf-8", errors="surrogateescape"),
                )
            )
            return snapshot, findings
        assert resolved is not None
        return _read_snapshot(
            relative, resolved, "safe_symlink", target, max_file_bytes
        )
    if not path.exists():
        snapshot = _FileSnapshot(relative, path, "missing", None, None, 0, None)
        findings.append(
            _finding_from_parts(
                relative,
                PrivacyFindingCode.MISSING_FILE,
                path_hash,
                None,
                relative.encode("utf-8"),
            )
        )
        return snapshot, findings
    try:
        mode = path.stat(follow_symlinks=False).st_mode
    except OSError:
        mode = 0
    if not stat.S_ISREG(mode):
        snapshot = _FileSnapshot(relative, path, "unsafe_file_type", None, None, 0, None)
        findings.append(
            _finding_from_parts(
                relative,
                PrivacyFindingCode.UNSAFE_FILE_TYPE,
                path_hash,
                None,
                str(mode).encode("ascii"),
            )
        )
        return snapshot, findings
    return _read_snapshot(relative, path, "regular", None, max_file_bytes)


def _read_snapshot(
    relative: str,
    path: Path,
    kind: str,
    symlink_target: str | None,
    max_file_bytes: int,
) -> tuple[_FileSnapshot, list[PrivacyFinding]]:
    try:
        size = path.stat().st_size
        digest = hashlib.sha256()
        chunks = []
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1_048_576)
                if not chunk:
                    break
                digest.update(chunk)
                if size <= max_file_bytes:
                    chunks.append(chunk)
    except OSError:
        snapshot = _FileSnapshot(relative, path, "unreadable", None, None, 0, symlink_target)
        finding = _finding_from_parts(
            relative,
            PrivacyFindingCode.UNSAFE_FILE_TYPE,
            _sha256(relative.encode()),
            None,
            b"unreadable",
        )
        return snapshot, [finding]
    content_hash = digest.hexdigest()
    content = b"".join(chunks) if size <= max_file_bytes else None
    snapshot = _FileSnapshot(
        relative, path, kind, content, content_hash, size, symlink_target
    )
    findings = []
    if content is None:
        findings.append(
            _finding(
                snapshot,
                PrivacyFindingCode.FILE_TOO_LARGE,
                f"size:{size}:limit:{max_file_bytes}",
            )
        )
    return snapshot, findings


def _path_findings(snapshot: _FileSnapshot) -> list[PrivacyFinding]:
    path = PurePosixPath(snapshot.relative_path)
    lowered_parts = [part.casefold() for part in path.parts]
    findings = []
    for part in sorted(set(lowered_parts).intersection(_PRIVATE_COMPONENTS)):
        findings.append(
            _finding(snapshot, PrivacyFindingCode.PRIVATE_PATH_COMPONENT, part)
        )
    name = path.name.casefold()
    if name in _PRIVATE_NAMES or name.startswith("pasted-text"):
        findings.append(_finding(snapshot, PrivacyFindingCode.PRIVATE_FILE_NAME, name))
    if name == ".env" or name.startswith(".env.") or path.suffix.casefold() == ".env":
        findings.append(_finding(snapshot, PrivacyFindingCode.FORBIDDEN_ENV, name))
    if path.suffix.casefold() == ".jsonl":
        findings.append(_finding(snapshot, PrivacyFindingCode.FORBIDDEN_JSONL, name))
    if path.suffix.casefold() == ".log":
        findings.append(_finding(snapshot, PrivacyFindingCode.FORBIDDEN_LOG, name))
    if path.suffix.casefold() == ".pdf" and (
        not lowered_parts or lowered_parts[0] != "assets"
    ):
        findings.append(_finding(snapshot, PrivacyFindingCode.SOURCE_BODY, name))
    stem = path.stem.casefold().replace("_", "-")
    source_code = path.suffix.casefold() in _SOURCE_CODE_SUFFIXES
    if not source_code and (stem in {
        "cost-ledger",
        "family-risk-authorizations",
        "ledger",
        "prompt",
        "provider-execution",
        "provider-orchestration",
        "provider-result",
        "provider-trace",
        "raw-prompt",
        "raw-request",
        "raw-response",
        "request",
        "response",
        "system-prompt",
        "trace",
        "usage",
        "usage-ledger",
    } or stem.startswith(
        ("provider-trace-", "raw-request-", "raw-response-", "usage-ledger-")
    )):
        findings.append(_finding(snapshot, PrivacyFindingCode.PROVIDER_ARTIFACT, stem))
    if not source_code and (
        "handoff" in stem or stem.startswith(("run-state", "run-manifest"))
    ):
        findings.append(_finding(snapshot, PrivacyFindingCode.PRIVATE_FILE_NAME, stem))
    if not source_code and stem in {"source-body", "source-content", "source-text"}:
        findings.append(_finding(snapshot, PrivacyFindingCode.SOURCE_BODY, stem))
    return findings


def _content_findings(
    snapshot: _FileSnapshot,
    machine_prefixes: tuple[str, ...],
) -> list[PrivacyFinding]:
    assert snapshot.content is not None
    try:
        text = snapshot.content.decode("utf-8")
    except UnicodeDecodeError:
        text = snapshot.content.decode("utf-8", errors="ignore")
    findings = []
    for pattern in _TOKEN_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(
                _finding(snapshot, PrivacyFindingCode.CREDENTIAL, match.group(0))
            )
    for match in _ASSIGNMENT_RE.finditer(text):
        candidate = match.group(1)
        if not _looks_placeholder(candidate) and _looks_secret(candidate):
            findings.append(
                _finding(snapshot, PrivacyFindingCode.CREDENTIAL, candidate)
            )
    for match in _BEARER_RE.finditer(text):
        candidate = match.group(1)
        if not _looks_placeholder(candidate):
            findings.append(
                _finding(snapshot, PrivacyFindingCode.CREDENTIAL, candidate)
            )
    for match in _BASIC_AUTH_RE.finditer(text):
        candidate = match.group(1)
        if not _looks_placeholder(candidate):
            findings.append(
                _finding(snapshot, PrivacyFindingCode.CREDENTIAL, candidate)
            )
    for match in _AUTH_URL_RE.finditer(text):
        username, password = match.groups()
        if not (_looks_placeholder(username) or _looks_placeholder(password)):
            findings.append(
                _finding(snapshot, PrivacyFindingCode.AUTHENTICATED_URL, match.group(0))
            )
    for prefix in machine_prefixes:
        if prefix and prefix in text:
            findings.append(
                _finding(snapshot, PrivacyFindingCode.MACHINE_LOCAL_PATH, prefix)
            )
    # Generic local paths are meaningful in artifacts/data, while source and
    # documentation are allowed to explain that such paths are prohibited.
    if Path(snapshot.relative_path).suffix.casefold() not in _CODE_OR_DOC_SUFFIXES:
        for match in _GENERIC_LOCAL_PATH_RE.finditer(text):
            findings.append(
                _finding(snapshot, PrivacyFindingCode.MACHINE_LOCAL_PATH, match.group(0))
            )
    return findings


def _json_audit(
    snapshot: _FileSnapshot,
) -> tuple[Any | None, list[PrivacyFinding]]:
    if Path(snapshot.relative_path).suffix.casefold() != ".json":
        return None, []
    assert snapshot.content is not None
    try:
        text = snapshot.content.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, [
            _finding(snapshot, PrivacyFindingCode.JSON_INVALID_UTF8, str(exc.start))
        ]
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_file_keys,
            parse_constant=_reject_nonfinite_file_number,
        )
    except _DuplicateJsonKey as exc:
        return None, [
            _finding(snapshot, PrivacyFindingCode.JSON_DUPLICATE_KEY, str(exc))
        ]
    except _NonfiniteJsonNumber as exc:
        return None, [
            _finding(snapshot, PrivacyFindingCode.JSON_NONFINITE_NUMBER, str(exc))
        ]
    except json.JSONDecodeError as exc:
        return None, [
            _finding(
                snapshot,
                PrivacyFindingCode.JSON_MALFORMED,
                f"line:{exc.lineno}:column:{exc.colno}",
            )
        ]
    findings = []
    schema_contract = _validated_json_schema_contract(
        snapshot.relative_path, value
    )
    for json_path, key in _private_json_keys(
        value, schema_contract=schema_contract
    ):
        findings.append(
            _finding(
                snapshot,
                PrivacyFindingCode.JSON_PRIVATE_KEY,
                f"{json_path}:{key}",
            )
        )
    return value, findings


def _card_findings(
    snapshot: _FileSnapshot,
    value: Any | None,
    validator: Draft202012Validator,
) -> list[PrivacyFinding]:
    if value is None:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_SCHEMA_INVALID,
                "strict_json_unavailable",
            )
        ]
    findings = []
    errors = sorted(
        validator.iter_errors(value),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        error = errors[0]
        location = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        findings.append(
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_SCHEMA_INVALID,
                f"{location}:{error.validator}",
            )
        )
    try:
        validate_publication_card(value)
    except (PublicationValidationError, KeyError, TypeError, ValueError) as exc:
        findings.append(
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_RUNTIME_INVALID,
                type(exc).__name__,
            )
        )
    try:
        assert_public_projection(value)
    except PublicExportError as exc:
        findings.append(
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_PRIVACY_INVALID,
                type(exc).__name__ + ":" + str(exc),
            )
        )
    return findings


def _card_markdown_findings(
    root: Path,
    snapshot: _FileSnapshot,
    *,
    audited_paths: frozenset[str],
) -> list[PrivacyFinding]:
    """Require ``cards/NAME.md`` to exactly render sibling ``NAME.json``."""

    if snapshot.content is None:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "markdown_content_unavailable",
            )
        ]

    markdown_path = PurePosixPath(snapshot.relative_path)
    json_relative = markdown_path.with_suffix(".json")
    if json_relative.as_posix() not in audited_paths:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "sibling_json_outside_audit_scope",
            )
        ]
    json_path = root.joinpath(*json_relative.parts)
    if json_path.is_symlink() or not json_path.is_file():
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "sibling_json_unavailable",
            )
        ]

    try:
        json_raw = json_path.read_bytes()
        card = json.loads(
            json_raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_file_keys,
            parse_constant=_reject_nonfinite_file_number,
        )
        validate_publication_card(card)
        assert_public_projection(card)
        expected = render_public_markdown(
            card,
            json_filename=json_relative.name,
            json_sha256=_sha256(json_raw),
        ).encode("utf-8")
    except (
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
        _DuplicateJsonKey,
        _NonfiniteJsonNumber,
        PublicationValidationError,
        PublicExportError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "sibling_json_invalid:" + type(exc).__name__,
            )
        ]

    if snapshot.content != expected:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "render_mismatch",
            )
        ]
    return []


def _card_json_pair_findings(
    root: Path,
    snapshot: _FileSnapshot,
    value: Any | None,
    *,
    audited_paths: frozenset[str],
) -> list[PrivacyFinding]:
    """Require ``cards/NAME.json`` to have its exact deterministic Markdown."""

    json_path = PurePosixPath(snapshot.relative_path)
    markdown_relative = json_path.with_suffix(".md")
    if markdown_relative.as_posix() not in audited_paths:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "sibling_markdown_outside_audit_scope",
            )
        ]
    markdown_path = root.joinpath(*markdown_relative.parts)
    if markdown_path.is_symlink() or not markdown_path.is_file():
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "sibling_markdown_unavailable",
            )
        ]
    if snapshot.content is None or not isinstance(value, dict):
        return []
    try:
        validate_publication_card(value)
        assert_public_projection(value)
        expected = render_public_markdown(
            value,
            json_filename=json_path.name,
            json_sha256=_sha256(snapshot.content),
        ).encode("utf-8")
        actual = markdown_path.read_bytes()
    except (
        OSError,
        PublicationValidationError,
        PublicExportError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "sibling_markdown_check_failed:" + type(exc).__name__,
            )
        ]
    if actual != expected:
        return [
            _finding(
                snapshot,
                PrivacyFindingCode.CARD_MARKDOWN_INVALID,
                "sibling_markdown_render_mismatch",
            )
        ]
    return []


def _private_json_keys(
    value: Any,
    path: str = "$",
    *,
    schema_contract: bool = False,
    schema_name_map: bool = False,
) -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            if (
                isinstance(key, str)
                and not schema_name_map
                and key.casefold() in _PRIVATE_JSON_KEYS
                and not (
                    schema_contract
                    and (path, key.casefold())
                    in _JSON_SCHEMA_DESCRIPTOR_PRIVATE_KEYS
                )
            ):
                yield path, key.casefold()
            child_name_map = bool(
                schema_contract
                and not schema_name_map
                and isinstance(key, str)
                and key in _JSON_SCHEMA_NAME_MAP_KEYS
                and isinstance(item, dict)
            )
            yield from _private_json_keys(
                item,
                f"{path}.{key}",
                schema_contract=schema_contract,
                schema_name_map=child_name_map,
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _private_json_keys(
                item,
                f"{path}[{index}]",
                schema_contract=schema_contract,
            )


def _validated_json_schema_contract(relative: str, value: Any) -> bool:
    if relative not in _JSON_SCHEMA_CONTRACT_PATHS or not isinstance(value, dict):
        return False
    if value.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        return False
    try:
        Draft202012Validator.check_schema(value)
    except SchemaError:
        return False
    return True


def _is_card_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    return len(path.parts) == 2 and path.parts[0].casefold() == "cards" \
        and path.suffix.casefold() == ".json"


def _is_card_markdown_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    return (
        len(path.parts) == 2
        and path.parts[0].casefold() == "cards"
        and path.suffix == ".md"
    )


def _is_cards_entry(relative: str) -> bool:
    path = PurePosixPath(relative)
    return bool(path.parts) and path.parts[0].casefold() == "cards"


def _machine_prefixes(root: Path) -> tuple[str, ...]:
    candidates = {str(root) + os.sep}
    parts = root.parts
    if len(parts) >= 3 and parts[1].casefold() in {"users", "home"}:
        candidates.add(str(Path(*parts[:3])) + os.sep)
    return tuple(sorted(candidates))


def _looks_placeholder(value: str) -> bool:
    lowered = value.casefold()
    normalized = re.split(r"[^a-z0-9]+", lowered)
    return any(
        term in _PLACEHOLDER_TERMS
        or any(term.startswith(prefix) for prefix in ("example", "synthetic", "test", "your"))
        for term in normalized
        if term
    )


def _looks_secret(value: str) -> bool:
    classes = sum(
        bool(pattern.search(value))
        for pattern in (
            re.compile(r"[a-z]"),
            re.compile(r"[A-Z]"),
            re.compile(r"[0-9]"),
            re.compile(r"[^A-Za-z0-9]"),
        )
    )
    return len(value) >= 20 and classes >= 2


def _finding(
    snapshot: _FileSnapshot,
    code: PrivacyFindingCode,
    evidence: str | bytes,
) -> PrivacyFinding:
    return _finding_from_parts(
        snapshot.relative_path,
        code,
        _sha256(snapshot.relative_path.encode("utf-8")),
        snapshot.content_sha256,
        evidence.encode("utf-8") if isinstance(evidence, str) else evidence,
    )


def _finding_from_parts(
    relative_path: str,
    code: PrivacyFindingCode,
    path_sha256: str,
    content_sha256: str | None,
    evidence: bytes,
) -> PrivacyFinding:
    evidence_sha256 = _sha256(code.value.encode() + b"\0" + evidence)
    finding_id = _finding_id(
        code, relative_path, path_sha256, content_sha256, evidence_sha256
    )
    return PrivacyFinding(
        finding_id=finding_id,
        code=code,
        relative_path=relative_path,
        path_sha256=path_sha256,
        content_sha256=content_sha256,
        evidence_sha256=evidence_sha256,
    )


def _deduplicate_findings(
    findings: Sequence[PrivacyFinding],
) -> tuple[PrivacyFinding, ...]:
    return tuple({item.finding_id: item for item in findings}.values())


def _finding_id(
    code: PrivacyFindingCode,
    relative_path: str,
    path_sha256: str,
    content_sha256: str | None,
    evidence_sha256: str,
) -> str:
    value = {
        "code": code.value,
        "relative_path": relative_path,
        "path_sha256": path_sha256,
        "content_sha256": content_sha256,
        "evidence_sha256": evidence_sha256,
    }
    return "privacy_finding_" + _sha256(_canonical_json(value))[:24]


def _report_id(
    *,
    scope: str,
    file_set_sha256: str,
    files_checked: int,
    bytes_checked: int,
    cards_checked: int,
    findings: Sequence[PrivacyFinding],
    passed: bool,
) -> str:
    value = {
        "report_version": PRIVACY_AUDIT_VERSION,
        "scope": scope,
        "file_set_sha256": file_set_sha256,
        "files_checked": files_checked,
        "bytes_checked": bytes_checked,
        "cards_checked": cards_checked,
        "findings": [item.to_dict() for item in findings],
        "passed": passed,
    }
    return "privacy_report_" + _sha256(_canonical_json(value))[:32]


def _validate_relative_path(value: Any) -> None:
    if not isinstance(value, str) or not value or "\\" in value or "\0" in value:
        raise PrivacyAuditError("public file path must be relative normalized POSIX text")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value \
            or any(part in {"", ".", ".."} for part in path.parts):
        raise PrivacyAuditError("public file path must be relative normalized POSIX text")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise PrivacyAuditError("public file path contains control characters")


def _strict_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PrivacyAuditError(f"{name} must be a closed object")
    return dict(value)


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                ensure_ascii=False,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PrivacyAuditError("privacy value is not canonical JSON") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_duplicate_file_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(_sha256(key.encode("utf-8")))
        result[key] = value
    return result


def _reject_nonfinite_file_number(value: str) -> None:
    raise _NonfiniteJsonNumber(_sha256(value.encode("ascii")))


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PrivacyAuditError("privacy report contains duplicate keys")
        result[key] = value
    return result


def _reject_nonfinite_json(value: str) -> None:
    raise PrivacyAuditError("privacy report contains a non-finite number")
