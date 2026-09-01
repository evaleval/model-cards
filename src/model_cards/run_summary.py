"""Privacy-safe deterministic summaries for one completed local pipeline run.

The summary layer is intentionally read-only with respect to run control state.
It verifies the immutable manifest, chained journal, registered artifacts,
serialized ``PipelineResult``, and the run's single usage ledger before writing
two canonical derived JSON files.  Existing summaries are verified byte for
byte and are never overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Any, Mapping, Sequence

from .pipeline import PipelineError, PipelineRepairReport, PipelineResult
from .run_ledger import LedgerError, UsageLedger
from .run_state import (
    JOURNAL_FILENAME,
    MANIFEST_FILENAME,
    USAGE_LEDGER_FILENAME,
    RunEvent,
    RunStateError,
    RunStore,
)


USAGE_SUMMARY_VERSION = "model-card-usage-summary/v1"
AUDIT_VIEW_VERSION = "model-card-audit-view/v1"
RUN_SUMMARY_RESULT_VERSION = "model-card-run-summary-result/v1"
USAGE_SUMMARY_FILENAME = "usage-summary.json"
AUDIT_VIEW_FILENAME = "audit-view.json"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_RE = re.compile(r"^model_card_run_[0-9a-f]{24}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:file://|(?:^|[\s\"'])~[/\\]|[A-Z]:[\\/]Users[\\/]"
    r"|/Users/[^/\s]+/|/home/[^/\s]+/|/private/(?:var/)?|/tmp/|/var/folders/)"
)
_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?:^|[^a-z0-9/])(?:file://|~[/\\]|[a-z]:[/\\]|/(?!/)(?:[^/\s\"']+(?:/|$)))"
)
_SYSTEM_ROOT_ALIASES = {
    Path("/tmp"): Path("/private/tmp"),
    Path("/var"): Path("/private/var"),
}
_BANNED_KEYS = frozenset(
    {
        "authorization",
        "credential",
        "evidence",
        "local_path",
        "prompt",
        "prompt_text",
        "quote",
        "raw_request",
        "raw_response",
        "request_body",
        "response",
        "source_body",
        "source_content",
        "source_text",
        "trace",
    }
)
_USAGE_METRIC_KEYS = frozenset(
    {
        "paid_calls",
        "committed_usd",
        "global_halt",
        "attempt_count",
        "receipt_count",
        "token_receipt_count",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "retry_count",
        "latency_ms",
        "max_latency_ms",
        "providers",
        "attempt_statuses",
        "terminal_outcomes",
    }
)


class RunSummaryError(RuntimeError):
    """The run, ledger, or an existing derived summary is unsafe or stale."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RunSummaryError("run summary values must be finite JSON") from exc


def _canonical_file(value: Any) -> bytes:
    return _canonical(value) + b"\n"


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise RunSummaryError(f"{label} is not a lowercase SHA-256 digest")
    return value


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise RunSummaryError(f"{label} has an invalid closed shape")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise RunSummaryError("summary input contains a duplicate JSON key")
        output[key] = value
    return output


def _reject_nonfinite(value: str) -> None:
    raise RunSummaryError(f"summary input contains non-finite JSON: {value}")


def _read_canonical_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RunSummaryError(f"{label} is missing or unsafe")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise RunSummaryError(f"{label} cannot be read safely") from exc
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunSummaryError(f"{label} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict) or raw != _canonical_file(value):
        raise RunSummaryError(f"{label} is not a canonical JSON object")
    return value


def _assert_no_symlink_components(path: Path) -> None:
    """Reject caller-controlled aliases while tolerating stable macOS roots."""

    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        try:
            if not current.is_symlink():
                continue
            allowed_target = _SYSTEM_ROOT_ALIASES.get(current)
            if allowed_target is not None and current.resolve(strict=True) == allowed_target:
                continue
        except OSError as exc:
            raise RunSummaryError("run path components cannot be inspected safely") from exc
        raise RunSummaryError("run path contains a symlink component")


def _assert_privacy_safe(value: Any, *, path: str = "summary") -> None:
    encoded = _canonical(value)
    if len(encoded) > 1_000_000:
        raise RunSummaryError("derived run summary exceeds its size bound")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 128:
                raise RunSummaryError(f"{path} contains an invalid key")
            if key.casefold() in _BANNED_KEYS:
                raise RunSummaryError(f"{path} contains a private key")
            _assert_privacy_safe(item, path=f"{path}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _assert_privacy_safe(item, path=f"{path}[]")
        return
    if isinstance(value, str):
        if (
            len(value) > 2048
            or "\x00" in value
            or _LOCAL_PATH_RE.search(value)
            or _ABSOLUTE_PATH_RE.search(value)
        ):
            raise RunSummaryError(f"{path} contains a local path or unsafe text")
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise RunSummaryError(f"{path} is not privacy-safe JSON")


@dataclass(frozen=True)
class _WriteResult:
    artifact_sha256: str
    created: bool
    identity: tuple[int, int] | None


def _write_or_verify(path: Path, value: Mapping[str, Any]) -> _WriteResult:
    _assert_privacy_safe(value)
    payload = _canonical_file(value)
    if path.is_symlink():
        raise RunSummaryError(f"derived summary path is a symlink: {path.name}")
    if path.exists():
        if not path.is_file() or path.read_bytes() != payload:
            raise RunSummaryError(f"derived summary has drifted: {path.name}")
        return _WriteResult(hashlib.sha256(payload).hexdigest(), False, None)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    created = False
    identity: tuple[int, int] | None = None
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        metadata = temporary.stat()
        identity = (metadata.st_dev, metadata.st_ino)
        try:
            os.link(temporary, path)
            created = True
        except FileExistsError:
            if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                raise RunSummaryError(f"derived summary raced with different bytes: {path.name}")
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        _cleanup_created(
            path,
            _WriteResult(hashlib.sha256(payload).hexdigest(), created, identity),
        )
        raise
    finally:
        if temporary.exists():
            temporary.unlink()
    return _WriteResult(hashlib.sha256(payload).hexdigest(), created, identity)


def _cleanup_created(path: Path, written: _WriteResult | None) -> None:
    """Remove only a regular file inode created by this failed invocation."""

    if written is None or not written.created or written.identity is None:
        return
    try:
        metadata = path.lstat()
        if (
            stat.S_ISREG(metadata.st_mode)
            and (metadata.st_dev, metadata.st_ino) == written.identity
        ):
            path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        # Preserve fail-closed behavior if best-effort rollback is impossible.
        return


def _verify_summary_file(path: Path, value: Mapping[str, Any]) -> None:
    if path.is_symlink() or not path.is_file():
        raise RunSummaryError(f"derived summary became unsafe: {path.name}")
    try:
        matches = path.read_bytes() == _canonical_file(value)
    except OSError as exc:
        raise RunSummaryError(f"derived summary cannot be re-read: {path.name}") from exc
    if not matches:
        raise RunSummaryError(f"derived summary changed while writing: {path.name}")


@dataclass(frozen=True)
class RunSummaryArtifactReference:
    filename: str
    artifact_sha256: str

    def __post_init__(self) -> None:
        if self.filename not in {USAGE_SUMMARY_FILENAME, AUDIT_VIEW_FILENAME}:
            raise RunSummaryError("run summary artifact filename is not recognized")
        _require_digest(self.artifact_sha256, "run summary artifact digest")

    def to_dict(self) -> dict[str, str]:
        return {
            "filename": self.filename,
            "artifact_sha256": self.artifact_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RunSummaryArtifactReference":
        return cls(**_strict(value, {"filename", "artifact_sha256"}, "summary artifact"))


@dataclass(frozen=True)
class RunSummaryArtifacts:
    run_id: str
    pipeline_result_sha256: str
    usage_summary_sha256: str
    audit_view_sha256: str
    artifacts: tuple[RunSummaryArtifactReference, ...]
    result_version: str = RUN_SUMMARY_RESULT_VERSION
    result_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.result_version != RUN_SUMMARY_RESULT_VERSION:
            raise RunSummaryError("run summary result version is unsupported")
        if not isinstance(self.run_id, str) or not _RUN_RE.fullmatch(self.run_id):
            raise RunSummaryError("run summary identifier is invalid")
        for name in (
            "pipeline_result_sha256",
            "usage_summary_sha256",
            "audit_view_sha256",
        ):
            _require_digest(getattr(self, name), name)
        artifacts = tuple(self.artifacts)
        if not all(isinstance(item, RunSummaryArtifactReference) for item in artifacts):
            raise RunSummaryError("run summary artifact references are malformed")
        if (
            len(artifacts) != 2
            or artifacts
            != tuple(sorted(artifacts, key=lambda item: item.filename))
            or {item.filename for item in artifacts}
            != {AUDIT_VIEW_FILENAME, USAGE_SUMMARY_FILENAME}
        ):
            raise RunSummaryError("run summary artifact inventory is incomplete")
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "result_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "result_version": self.result_version,
            "run_id": self.run_id,
            "pipeline_result_sha256": self.pipeline_result_sha256,
            "usage_summary_sha256": self.usage_summary_sha256,
            "audit_view_sha256": self.audit_view_sha256,
            "artifacts": [item.to_dict() for item in self.artifacts],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "result_sha256": self.result_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "RunSummaryArtifacts":
        item = _strict(
            value,
            {
                "result_version",
                "run_id",
                "pipeline_result_sha256",
                "usage_summary_sha256",
                "audit_view_sha256",
                "artifacts",
                "result_sha256",
            },
            "run summary result",
        )
        if not isinstance(item["artifacts"], list):
            raise RunSummaryError("run summary artifact references must be an array")
        result = cls(
            result_version=item["result_version"],
            run_id=item["run_id"],
            pipeline_result_sha256=item["pipeline_result_sha256"],
            usage_summary_sha256=item["usage_summary_sha256"],
            audit_view_sha256=item["audit_view_sha256"],
            artifacts=tuple(
                RunSummaryArtifactReference.from_dict(entry)
                for entry in item["artifacts"]
            ),
        )
        if item["result_sha256"] != result.result_sha256:
            raise RunSummaryError("run summary result digest is inconsistent")
        return result


def _single_usage_ledger(root: Path) -> Path:
    ledgers: list[Path] = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = tuple(os.scandir(directory))
        except OSError as exc:
            raise RunSummaryError("run tree cannot be inspected safely") from exc
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink():
                raise RunSummaryError("run tree contains a symlink")
            try:
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False) and entry.name == USAGE_LEDGER_FILENAME:
                    ledgers.append(path)
            except OSError as exc:
                raise RunSummaryError("run tree entry cannot be inspected safely") from exc
    expected = root / USAGE_LEDGER_FILENAME
    if ledgers != [expected] or expected.is_symlink() or not expected.is_file():
        raise RunSummaryError("run must contain exactly one root usage.jsonl ledger")
    return expected


def _file_fingerprint(metadata: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _validated_usage_metrics(
    path: Path,
) -> tuple[dict[str, Any], str, tuple[int, int, int, int, int]]:
    if path.is_symlink() or not path.is_file():
        raise RunSummaryError("usage ledger is missing or unsafe")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_SH)
            try:
                before = handle.read()
                fingerprint = _file_fingerprint(os.fstat(handle.fileno()))
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise RunSummaryError("usage ledger cannot be snapshotted safely") from exc
    before_sha256 = hashlib.sha256(before).hexdigest()
    try:
        descriptor, snapshot_name = tempfile.mkstemp(
            prefix="model-card-usage-snapshot-", suffix=".jsonl"
        )
    except OSError as exc:
        raise RunSummaryError("private usage snapshot cannot be created") from exc
    snapshot_path = Path(snapshot_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(before)
            handle.flush()
            os.fsync(handle.fileno())
        metrics = dict(UsageLedger(snapshot_path).audit_metrics())
        if hashlib.sha256(snapshot_path.read_bytes()).hexdigest() != before_sha256:
            raise RunSummaryError("private usage snapshot changed during its audit")
    except (LedgerError, OSError, ValueError) as exc:
        raise RunSummaryError("usage ledger failed its aggregate audit") from exc
    finally:
        try:
            snapshot_path.unlink()
        except FileNotFoundError:
            pass
    try:
        metadata = path.lstat()
        if (
            path.is_symlink()
            or _file_fingerprint(metadata) != fingerprint
            or hashlib.sha256(path.read_bytes()).hexdigest() != before_sha256
        ):
            raise RunSummaryError("usage ledger changed during summary generation")
    except OSError as exc:
        raise RunSummaryError("usage ledger cannot be re-read safely") from exc
    if set(metrics) != _USAGE_METRIC_KEYS:
        raise RunSummaryError("usage ledger aggregate shape is invalid")
    integer_keys = _USAGE_METRIC_KEYS - {
        "committed_usd",
        "global_halt",
        "providers",
        "attempt_statuses",
        "terminal_outcomes",
    }
    if any(
        not isinstance(metrics[key], int)
        or isinstance(metrics[key], bool)
        or metrics[key] < 0
        for key in integer_keys
    ):
        raise RunSummaryError("usage ledger aggregate count is invalid")
    if not isinstance(metrics["global_halt"], bool):
        raise RunSummaryError("usage ledger halt marker is invalid")
    try:
        committed = Decimal(metrics["committed_usd"])
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise RunSummaryError("usage ledger committed cost is invalid") from exc
    if not committed.is_finite() or committed < 0:
        raise RunSummaryError("usage ledger committed cost is invalid")
    providers = metrics["providers"]
    if (
        not isinstance(providers, list)
        or any(not isinstance(item, str) or not item for item in providers)
        or providers != sorted(set(providers))
    ):
        raise RunSummaryError("usage ledger provider summary is invalid")
    for key, total_key in (
        ("attempt_statuses", "attempt_count"),
        ("terminal_outcomes", "receipt_count"),
    ):
        values = metrics[key]
        if (
            not isinstance(values, dict)
            or any(
                not isinstance(name, str)
                or not _CODE_RE.fullmatch(name)
                or not isinstance(count, int)
                or isinstance(count, bool)
                or count < 0
                for name, count in values.items()
            )
            or list(values) != sorted(values)
            or sum(values.values()) != metrics[total_key]
        ):
            raise RunSummaryError(f"usage ledger {key} summary is invalid")
    if (
        metrics["token_receipt_count"] > metrics["receipt_count"]
        or metrics["prompt_tokens"] + metrics["completion_tokens"]
        != metrics["total_tokens"]
        or metrics["max_latency_ms"] > metrics["latency_ms"]
    ):
        raise RunSummaryError("usage ledger aggregate totals are inconsistent")
    _assert_privacy_safe(metrics, path="usage_metrics")
    return metrics, before_sha256, fingerprint


def _verify_completed_run(
    result: PipelineResult,
    root: Path,
) -> tuple[RunStore, tuple[RunEvent, ...]]:
    if not isinstance(result, PipelineResult):
        raise RunSummaryError("run summary requires a typed PipelineResult")
    try:
        store = RunStore.open(root)
        manifest = store.manifest
        events = store.events(verify_artifacts=True)
    except (RunStateError, OSError, TypeError, ValueError, KeyError) as exc:
        raise RunSummaryError("run state or a registered artifact failed verification") from exc
    if (
        manifest.run_id != result.run_id
        or manifest.target != result.target
        or manifest.source_bundle_id != result.source_bundle_id
        or manifest.source_manifest_sha256 != result.source_manifest_sha256
    ):
        raise RunSummaryError("pipeline result differs from the admitted run")
    if not events or events[-1].stage != "complete" or events[-1].logical_id != "pipeline":
        raise RunSummaryError("run journal does not end in one completed pipeline event")
    complete = events[-1]
    if (
        complete.status != "completed"
        or complete.artifact_path != "pipeline-result.json"
        or complete.artifact_sha256 is None
    ):
        raise RunSummaryError("pipeline completion event is incomplete")
    try:
        serialized = PipelineResult.from_dict(
            _read_canonical_object(root / "pipeline-result.json", "pipeline result")
        )
    except (PipelineError, TypeError, ValueError, KeyError) as exc:
        raise RunSummaryError("serialized pipeline result is invalid") from exc
    if serialized.to_dict() != result.to_dict():
        raise RunSummaryError("serialized pipeline result differs from the supplied result")
    if hashlib.sha256((root / "pipeline-result.json").read_bytes()).hexdigest() != (
        complete.artifact_sha256
    ):
        raise RunSummaryError("pipeline result artifact digest is stale")

    event_by_key = {(item.stage, item.logical_id): item for item in events[:-1]}
    reference_by_key = {(item.stage, item.logical_id): item for item in result.artifacts}
    if set(event_by_key) != set(reference_by_key):
        raise RunSummaryError("pipeline result and journal artifact inventories differ")
    for key, reference in reference_by_key.items():
        event = event_by_key[key]
        if (
            event.artifact_path != reference.filename
            or event.artifact_sha256 != reference.artifact_sha256
            or event.status != reference.status
            or event.reason != reference.reason
        ):
            raise RunSummaryError("pipeline artifact reference differs from the journal")
    exports = {
        (item.stage, item.logical_id): item for item in result.artifacts
    }
    local_artifact = exports.get(("export", "local_artifact"))
    public_card = exports.get(("export", "public_card"))
    if (
        local_artifact is None
        or local_artifact.artifact_sha256 != result.artifact_sha256
        or public_card is None
        or public_card.artifact_sha256 != result.public_card_sha256
    ):
        raise RunSummaryError("pipeline export digests differ from the result")
    return store, events


def _repair_metrics(result: PipelineResult, root: Path) -> dict[str, Any]:
    matches = [
        item
        for item in result.artifacts
        if item.stage == "repair" and item.filename == "repairs.json"
    ]
    if len(matches) != 1:
        raise RunSummaryError("completed pipeline lacks one canonical repair artifact")
    try:
        repair = PipelineRepairReport.from_dict(
            _read_canonical_object(root / matches[0].filename, "repair report")
        )
    except (PipelineError, TypeError, ValueError, KeyError) as exc:
        raise RunSummaryError("serialized repair report is invalid") from exc
    if (
        repair.target != result.target
        or repair.post_repair_composition_sha256 != result.composition_sha256
    ):
        raise RunSummaryError("repair report differs from the final pipeline result")
    outcomes: dict[str, int] = {}
    for record in repair.records:
        key = record.outcome.value
        outcomes[key] = outcomes.get(key, 0) + 1
    return {
        "report_sha256": repair.report_sha256,
        "original_composition_sha256": repair.original_composition_sha256,
        "original_factreasoner_sha256": repair.original_factreasoner_sha256,
        "original_omission_audit_sha256": repair.original_omission_audit_sha256,
        "post_repair_composition_sha256": repair.post_repair_composition_sha256,
        "record_count": len(repair.records),
        "semantic_submission_count": repair.semantic_submission_count,
        "actionable_candidate_count": len(repair.actionable_candidate_ids),
        "structural_withheld_count": len(repair.structural_withheld_candidate_ids),
        "withheld_candidate_count": len(repair.withheld_candidate_ids),
        "derivation_withheld_count": len(
            repair.factreasoner_withheld_derivation_ids
        ),
        "outcomes": {key: outcomes[key] for key in sorted(outcomes)},
    }


def _distribution(values: Sequence[str]) -> dict[str, int]:
    output: dict[str, int] = {}
    for value in values:
        output[value] = output.get(value, 0) + 1
    return {key: output[key] for key in sorted(output)}


def _stage_view(events: Sequence[RunEvent]) -> dict[str, Any]:
    stages: dict[str, dict[str, Any]] = {}
    artifacts = []
    for event in events:
        stage = stages.setdefault(
            event.stage,
            {"event_count": 0, "artifact_count": 0, "statuses": {}},
        )
        stage["event_count"] += 1
        statuses = stage["statuses"]
        statuses[event.status] = statuses.get(event.status, 0) + 1
        if event.artifact_path is not None:
            stage["artifact_count"] += 1
            artifacts.append(
                {
                    "stage": event.stage,
                    "logical_id": event.logical_id,
                    "status": event.status,
                    "reason": event.reason,
                    "filename": event.artifact_path,
                    "artifact_sha256": event.artifact_sha256,
                }
            )
    normalized_stages = {
        key: {
            "event_count": stages[key]["event_count"],
            "artifact_count": stages[key]["artifact_count"],
            "statuses": {
                status: stages[key]["statuses"][status]
                for status in sorted(stages[key]["statuses"])
            },
        }
        for key in sorted(stages)
    }
    artifacts.sort(key=lambda item: (item["stage"], item["logical_id"]))
    return {
        "event_count": len(events),
        "stage_count": len(normalized_stages),
        "artifact_count": len(artifacts),
        "statuses": _distribution([item.status for item in events]),
        "stages": normalized_stages,
        "artifacts": artifacts,
        "artifact_inventory_sha256": _digest(artifacts),
    }


def _validation_view(result: PipelineResult) -> dict[str, Any]:
    flags = result.validation.to_dict()
    return {
        "lifecycle_status": result.lifecycle_status.value,
        "composition_status": result.composition_status.value,
        "claim_count": len(result.claims),
        "projection_eligible_claim_count": sum(
            item.projection_eligible for item in result.claims
        ),
        "included_claim_count": sum(item.included for item in result.claims),
        "conflict_count": result.conflict_count,
        "source_present_omission_count": result.source_present_omission_count,
        "validation_flags": flags,
        "passed_validation_flag_count": sum(flags.values()),
        "validation_flag_count": len(flags),
        "composition_sha256": result.composition_sha256,
        "factreasoner_sha256": result.factreasoner_sha256,
        "omission_audit_sha256": result.omission_audit_sha256,
        "artifact_sha256": result.artifact_sha256,
        "public_card_sha256": result.public_card_sha256,
        "risk": {
            "status": result.risk.status,
            "reason": result.risk.reason,
            "taxonomy_candidate_count": result.risk.taxonomy_candidate_count,
            "taxonomy_included_count": result.risk.taxonomy_included_count,
            "summary_sha256": result.risk.summary_sha256,
        },
        "privacy": {
            "status": result.privacy.status,
            "reason": result.privacy.reason,
            "checked": result.privacy.checked,
            "passed": result.privacy.passed,
            "withheld_candidate_count": len(result.privacy.withheld_candidate_ids),
            "report_sha256": result.privacy.report_sha256,
        },
    }


def write_run_summaries(
    result: PipelineResult,
    run_directory: str | os.PathLike[str],
) -> RunSummaryArtifacts:
    """Verify one completed run and write or verify its two safe summaries."""

    root = Path(run_directory)
    _assert_no_symlink_components(root)
    store, events = _verify_completed_run(result, root)
    manifest_path = store.root / MANIFEST_FILENAME
    journal_path = store.root / JOURNAL_FILENAME
    try:
        manifest_file_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        journal_file_sha256 = hashlib.sha256(journal_path.read_bytes()).hexdigest()
    except OSError as exc:
        raise RunSummaryError("run control files cannot be read safely") from exc
    usage_path = _single_usage_ledger(store.root)
    usage_metrics, ledger_sha256, ledger_fingerprint = _validated_usage_metrics(
        usage_path
    )
    usage_content = {
        "usage_summary_version": USAGE_SUMMARY_VERSION,
        "run_id": result.run_id,
        "target": result.target.to_dict(),
        "pipeline_result_sha256": result.result_sha256,
        "ledger": {
            "filename": USAGE_LEDGER_FILENAME,
            "ledger_count": 1,
            "ledger_sha256": ledger_sha256,
        },
        "metrics": usage_metrics,
    }
    usage_summary_sha256 = _digest(usage_content)
    usage_summary = {
        **usage_content,
        "usage_summary_sha256": usage_summary_sha256,
    }
    stage_view = _stage_view(events)
    repair_view = _repair_metrics(result, store.root)
    validation_view = _validation_view(result)
    usage_artifact_sha256 = hashlib.sha256(
        _canonical_file(usage_summary)
    ).hexdigest()
    audit_content = {
        "audit_view_version": AUDIT_VIEW_VERSION,
        "run_id": result.run_id,
        "target": result.target.to_dict(),
        "pipeline_result_sha256": result.result_sha256,
        "control_digests": {
            "manifest_sha256": store.manifest.manifest_sha256,
            "manifest_file_sha256": manifest_file_sha256,
            "journal_file_sha256": journal_file_sha256,
            "journal_tail_sha256": events[-1].event_sha256,
            "usage_summary_sha256": usage_summary_sha256,
            "usage_summary_artifact_sha256": usage_artifact_sha256,
        },
        "stages": stage_view,
        "validation": validation_view,
        "repair": repair_view,
        "usage": usage_metrics,
        "stage_view_sha256": _digest(stage_view),
        "validation_view_sha256": _digest(validation_view),
        "repair_view_sha256": _digest(repair_view),
        "usage_view_sha256": _digest(usage_metrics),
    }
    audit_view_sha256 = _digest(audit_content)
    audit_view = {**audit_content, "audit_view_sha256": audit_view_sha256}
    audit_artifact_sha256 = hashlib.sha256(_canonical_file(audit_view)).hexdigest()
    usage_summary_path = store.root / USAGE_SUMMARY_FILENAME
    audit_view_path = store.root / AUDIT_VIEW_FILENAME
    usage_write: _WriteResult | None = None
    audit_write: _WriteResult | None = None
    try:
        usage_write = _write_or_verify(usage_summary_path, usage_summary)
        if usage_write.artifact_sha256 != usage_artifact_sha256:
            raise RunSummaryError("usage summary artifact digest is inconsistent")
        audit_write = _write_or_verify(audit_view_path, audit_view)
        if audit_write.artifact_sha256 != audit_artifact_sha256:
            raise RunSummaryError("audit view artifact digest is inconsistent")

        # Re-verify after both writes so an append or artifact replacement
        # during aggregation cannot produce a successfully returned stale view.
        _, final_events = _verify_completed_run(result, store.root)
        final_usage_path = _single_usage_ledger(store.root)
        controls_unchanged = (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            == manifest_file_sha256
            and hashlib.sha256(journal_path.read_bytes()).hexdigest()
            == journal_file_sha256
            and hashlib.sha256(final_usage_path.read_bytes()).hexdigest()
            == ledger_sha256
            and _file_fingerprint(final_usage_path.lstat()) == ledger_fingerprint
        )
        if final_events != events or not controls_unchanged:
            raise RunSummaryError("run changed while summaries were being written")
        _assert_no_symlink_components(store.root)
        _verify_summary_file(usage_summary_path, usage_summary)
        _verify_summary_file(audit_view_path, audit_view)
    except BaseException as exc:
        _cleanup_created(audit_view_path, audit_write)
        _cleanup_created(usage_summary_path, usage_write)
        if isinstance(exc, RunSummaryError):
            raise
        if isinstance(exc, OSError):
            raise RunSummaryError(
                "run changed while summaries were being written"
            ) from exc
        raise
    artifacts = tuple(
        sorted(
            (
                RunSummaryArtifactReference(
                    AUDIT_VIEW_FILENAME, audit_artifact_sha256
                ),
                RunSummaryArtifactReference(
                    USAGE_SUMMARY_FILENAME, usage_artifact_sha256
                ),
            ),
            key=lambda item: item.filename,
        )
    )
    return RunSummaryArtifacts(
        run_id=result.run_id,
        pipeline_result_sha256=result.result_sha256,
        usage_summary_sha256=usage_summary_sha256,
        audit_view_sha256=audit_view_sha256,
        artifacts=artifacts,
    )


__all__ = [
    "AUDIT_VIEW_FILENAME",
    "AUDIT_VIEW_VERSION",
    "RUN_SUMMARY_RESULT_VERSION",
    "USAGE_SUMMARY_FILENAME",
    "USAGE_SUMMARY_VERSION",
    "RunSummaryArtifactReference",
    "RunSummaryArtifacts",
    "RunSummaryError",
    "write_run_summaries",
]
