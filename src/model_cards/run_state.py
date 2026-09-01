"""Minimal crash-safe state for resumable local generation runs.

The control plane is intentionally small: one immutable manifest, one chained
append-only journal, and the provider usage ledger managed by ``run_ledger``.
Journal entries bind stage results by repository-relative name and digest; they
never contain source bodies, prompts, provider payloads, credentials, or local
absolute paths.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from types import MappingProxyType
from typing import Any, Callable, Iterator, Mapping, Sequence

from .models import TargetIdentity


RUN_MANIFEST_VERSION = "model-card-run/v1"
RUN_JOURNAL_VERSION = "model-card-run-journal/v1"
MANIFEST_FILENAME = "run-manifest.json"
JOURNAL_FILENAME = "journal.jsonl"
USAGE_LEDGER_FILENAME = "usage.jsonl"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_RUN_ID_RE = re.compile(r"^model_card_run_[0-9a-f]{24}$")
_EVENT_ID_RE = re.compile(r"^run_event_[0-9a-f]{24}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_BANNED_KEY_PARTS = (
    "prompt",
    "response",
    "request_body",
    "source_text",
    "source_content",
    "evidence_text",
    "api_key",
    "credential",
    "secret",
    "authorization",
    "trace",
    "local_path",
)
_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:^|\s)(?:/Users/|/home/|/private/|/tmp/|[A-Z]:[\\/]Users[\\/]|file://|~[/\\])"
)
_STAGES = frozenset(
    {
        "collect",
        "discover",
        "extract",
        "claim_gate",
        "compose",
        "risk_map",
        "factreasoner",
        "omission_audit",
        "repair",
        "privacy",
        "export",
        "aggregate",
        "complete",
    }
)
_STATUSES = frozenset({"completed", "unavailable", "withheld", "failed"})


class RunStateError(RuntimeError):
    """Run state is malformed, stale, unsafe, or conflicts with a prior run."""


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
        raise RunStateError("run state must contain finite JSON values") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise RunStateError(f"{label} has an invalid closed shape")
    return value


def _safe_metadata(value: Any, *, path: str = "metadata") -> Any:
    """Return a detached, bounded JSON value after privacy validation."""

    raw = _canonical(value)
    if len(raw) > 16_384:
        raise RunStateError(f"{path} exceeds its byte bound")
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 128:
                raise RunStateError(f"{path} has an invalid key")
            lowered = key.casefold()
            if any(part in lowered for part in _BANNED_KEY_PARTS):
                raise RunStateError(f"{path} contains a private key")
            output[key] = _safe_metadata(item, path=f"{path}.{key}")
        return output
    if isinstance(value, list):
        return [_safe_metadata(item, path=f"{path}[]") for item in value]
    if isinstance(value, str):
        if len(value) > 2048 or "\x00" in value or _LOCAL_PATH_RE.search(value):
            raise RunStateError(f"{path} contains unsafe text")
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise RunStateError(f"{path} is not JSON")


@dataclass(frozen=True)
class RunManifest:
    target: TargetIdentity
    source_bundle_id: str
    source_manifest_sha256: str
    configuration: Mapping[str, Any]
    manifest_version: str = RUN_MANIFEST_VERSION
    run_id: str = dataclass_field(init=False)
    manifest_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.manifest_version != RUN_MANIFEST_VERSION:
            raise RunStateError("unsupported run manifest version")
        if not isinstance(self.target, TargetIdentity):
            raise RunStateError("run target is invalid")
        if (
            not isinstance(self.source_bundle_id, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{2,63}_[0-9a-f]{16,64}", self.source_bundle_id)
        ):
            raise RunStateError("source bundle identifier is invalid")
        if not isinstance(self.source_manifest_sha256, str) or not _DIGEST_RE.fullmatch(
            self.source_manifest_sha256
        ):
            raise RunStateError("source manifest digest is invalid")
        if not isinstance(self.configuration, Mapping):
            raise RunStateError("run configuration must be an object")
        configuration = _safe_metadata(dict(self.configuration), path="configuration")
        object.__setattr__(self, "configuration", MappingProxyType(configuration))
        content = self._content_payload()
        object.__setattr__(self, "run_id", "model_card_run_" + _digest(content)[:24])
        object.__setattr__(self, "manifest_sha256", _digest(content))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "target": self.target.to_dict(),
            "source_bundle_id": self.source_bundle_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "configuration": dict(self.configuration),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._content_payload(),
            "run_id": self.run_id,
            "manifest_sha256": self.manifest_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RunManifest":
        item = _strict(
            value,
            {
                "manifest_version",
                "run_id",
                "target",
                "source_bundle_id",
                "source_manifest_sha256",
                "configuration",
                "manifest_sha256",
            },
            "run manifest",
        )
        manifest = cls(
            manifest_version=item["manifest_version"],
            target=TargetIdentity.from_dict(item["target"]),
            source_bundle_id=item["source_bundle_id"],
            source_manifest_sha256=item["source_manifest_sha256"],
            configuration=item["configuration"],
        )
        if item["run_id"] != manifest.run_id or not _RUN_ID_RE.fullmatch(item["run_id"]):
            raise RunStateError("run identifier does not match manifest content")
        if item["manifest_sha256"] != manifest.manifest_sha256:
            raise RunStateError("run manifest digest does not match content")
        return manifest


def _timestamp(value: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RunStateError("journal timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RunStateError("journal timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise RunStateError("journal timestamp is not UTC")


def _relative_artifact(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or "\\" in value:
        raise RunStateError("journal artifact path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise RunStateError("journal artifact path must be safe and relative")
    if value in {MANIFEST_FILENAME, JOURNAL_FILENAME, USAGE_LEDGER_FILENAME}:
        raise RunStateError("journal cannot register a control file as a stage artifact")
    return value


@dataclass(frozen=True)
class RunEvent:
    sequence: int
    run_id: str
    stage: str
    logical_id: str
    status: str
    reason: str
    artifact_path: str | None
    artifact_sha256: str | None
    input_sha256s: tuple[str, ...]
    metrics: Mapping[str, Any]
    created_at: str
    previous_event_sha256: str | None
    journal_version: str = RUN_JOURNAL_VERSION
    event_id: str = dataclass_field(init=False)
    event_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.journal_version != RUN_JOURNAL_VERSION:
            raise RunStateError("unsupported run journal version")
        if not isinstance(self.sequence, int) or isinstance(self.sequence, bool) or self.sequence < 1:
            raise RunStateError("journal sequence is invalid")
        if not isinstance(self.run_id, str) or not _RUN_ID_RE.fullmatch(self.run_id):
            raise RunStateError("journal run identifier is invalid")
        if self.stage not in _STAGES:
            raise RunStateError("journal stage is invalid")
        if not isinstance(self.logical_id, str) or not _CODE_RE.fullmatch(self.logical_id):
            raise RunStateError("journal logical identifier is invalid")
        if self.status not in _STATUSES:
            raise RunStateError("journal status is invalid")
        if not isinstance(self.reason, str) or not _CODE_RE.fullmatch(self.reason):
            raise RunStateError("journal reason code is invalid")
        artifact_path = _relative_artifact(self.artifact_path)
        object.__setattr__(self, "artifact_path", artifact_path)
        if (artifact_path is None) != (self.artifact_sha256 is None):
            raise RunStateError("journal artifact path and digest must appear together")
        if self.artifact_sha256 is not None and not _DIGEST_RE.fullmatch(
            self.artifact_sha256
        ):
            raise RunStateError("journal artifact digest is invalid")
        inputs = tuple(self.input_sha256s)
        if inputs != tuple(sorted(set(inputs))) or any(not _DIGEST_RE.fullmatch(x) for x in inputs):
            raise RunStateError("journal input digests must be sorted and unique")
        object.__setattr__(self, "input_sha256s", inputs)
        if not isinstance(self.metrics, Mapping):
            raise RunStateError("journal metrics must be an object")
        metrics = _safe_metadata(dict(self.metrics), path="metrics")
        object.__setattr__(self, "metrics", MappingProxyType(metrics))
        _timestamp(self.created_at)
        if self.previous_event_sha256 is not None and not _DIGEST_RE.fullmatch(
            self.previous_event_sha256
        ):
            raise RunStateError("previous journal digest is invalid")
        content = self._content_payload()
        digest = _digest(content)
        object.__setattr__(self, "event_id", "run_event_" + digest[:24])
        object.__setattr__(self, "event_sha256", digest)

    def _content_payload(self) -> dict[str, Any]:
        return {
            "journal_version": self.journal_version,
            "sequence": self.sequence,
            "run_id": self.run_id,
            "stage": self.stage,
            "logical_id": self.logical_id,
            "status": self.status,
            "reason": self.reason,
            "artifact_path": self.artifact_path,
            "artifact_sha256": self.artifact_sha256,
            "input_sha256s": list(self.input_sha256s),
            "metrics": dict(self.metrics),
            "created_at": self.created_at,
            "previous_event_sha256": self.previous_event_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._content_payload(),
            "event_id": self.event_id,
            "event_sha256": self.event_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RunEvent":
        item = _strict(
            value,
            {
                "journal_version",
                "sequence",
                "run_id",
                "stage",
                "logical_id",
                "status",
                "reason",
                "artifact_path",
                "artifact_sha256",
                "input_sha256s",
                "metrics",
                "created_at",
                "previous_event_sha256",
                "event_id",
                "event_sha256",
            },
            "run event",
        )
        if not isinstance(item["input_sha256s"], list):
            raise RunStateError("journal input_sha256s must be an array")
        event = cls(
            journal_version=item["journal_version"],
            sequence=item["sequence"],
            run_id=item["run_id"],
            stage=item["stage"],
            logical_id=item["logical_id"],
            status=item["status"],
            reason=item["reason"],
            artifact_path=item["artifact_path"],
            artifact_sha256=item["artifact_sha256"],
            input_sha256s=tuple(item["input_sha256s"]),
            metrics=item["metrics"],
            created_at=item["created_at"],
            previous_event_sha256=item["previous_event_sha256"],
        )
        if item["event_id"] != event.event_id or not _EVENT_ID_RE.fullmatch(item["event_id"]):
            raise RunStateError("journal event identifier is inconsistent")
        if item["event_sha256"] != event.event_sha256:
            raise RunStateError("journal event digest is inconsistent")
        return event


def _read_strict_object(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunStateError(f"control file is not strict UTF-8 JSON: {path.name}") from exc
    if not isinstance(value, dict):
        raise RunStateError(f"control file root is not an object: {path.name}")
    if raw != _canonical(value) + b"\n":
        raise RunStateError(f"control file is not canonical: {path.name}")
    return value


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise RunStateError("control JSON contains a duplicate key")
        output[key] = value
    return output


def _reject_nonfinite(value: str) -> None:
    raise RunStateError(f"control JSON contains non-finite number: {value}")


def _atomic_new(path: Path, payload: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing to replace run control file: {path.name}")
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    temp_path = Path(temporary)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_path, path)
        os.unlink(temp_path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


@contextmanager
def _locked_journal(path: Path) -> Iterator[Any]:
    if path.is_symlink() or path.parent.is_symlink():
        raise RunStateError("run journal path is unsafe")
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(descriptor, "r+b", buffering=0) as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            handle.flush()
            os.fsync(handle.fileno())
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _events_from_bytes(raw: bytes, manifest: RunManifest) -> tuple[RunEvent, ...]:
    events = []
    if not raw:
        return ()
    if not raw.endswith(b"\n"):
        raise RunStateError("run journal has a torn final line")
    for line in raw.splitlines():
        try:
            value = json.loads(
                line.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RunStateError("run journal is not strict JSONL") from exc
        if line != _canonical(value):
            raise RunStateError("run journal line is not canonical")
        events.append(RunEvent.from_dict(value))
    previous = None
    logical_keys = set()
    for sequence, event in enumerate(events, 1):
        if event.sequence != sequence or event.run_id != manifest.run_id:
            raise RunStateError("run journal sequence or target is inconsistent")
        if event.previous_event_sha256 != previous:
            raise RunStateError("run journal hash chain is broken")
        key = (event.stage, event.logical_id)
        if key in logical_keys:
            raise RunStateError("run journal contains a duplicate logical stage")
        logical_keys.add(key)
        previous = event.event_sha256
    return tuple(events)


class RunStore:
    """One admitted target with immutable manifest and append-only stage state."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root)
        if self.root.is_symlink() or not self.root.is_dir():
            raise RunStateError("run root must be a real directory")
        self.manifest_path = self.root / MANIFEST_FILENAME
        self.journal_path = self.root / JOURNAL_FILENAME
        self.usage_ledger_path = self.root / USAGE_LEDGER_FILENAME

    @classmethod
    def initialize(
        cls, root: str | os.PathLike[str], manifest: RunManifest
    ) -> "RunStore":
        if not isinstance(manifest, RunManifest):
            raise RunStateError("run initialization requires a typed manifest")
        path = Path(root)
        if path.is_symlink():
            raise RunStateError("run root cannot be a symlink")
        path.mkdir(parents=True, exist_ok=True)
        store = cls(path)
        if store.manifest_path.exists() or store.manifest_path.is_symlink():
            existing = store.manifest
            if existing != manifest:
                raise RunStateError("run directory is already admitted to another target/config")
        else:
            _atomic_new(store.manifest_path, _canonical(manifest.to_dict()) + b"\n")
        # Creating the ordinary locked files is idempotent and stores no event.
        for control in (store.journal_path, store.usage_ledger_path):
            if control.is_symlink():
                raise RunStateError("run control file cannot be a symlink")
            descriptor = os.open(control, os.O_RDWR | os.O_CREAT, 0o600)
            os.close(descriptor)
        return store

    @classmethod
    def open(cls, root: str | os.PathLike[str]) -> "RunStore":
        store = cls(root)
        store.manifest
        store.events(verify_artifacts=True)
        return store

    @property
    def manifest(self) -> RunManifest:
        if self.manifest_path.is_symlink() or not self.manifest_path.is_file():
            raise RunStateError("run manifest is missing or unsafe")
        return RunManifest.from_dict(_read_strict_object(self.manifest_path))

    def events(self, *, verify_artifacts: bool = False) -> tuple[RunEvent, ...]:
        manifest = self.manifest
        with _locked_journal(self.journal_path) as handle:
            handle.seek(0)
            events = _events_from_bytes(handle.read(), manifest)
        if verify_artifacts:
            for event in events:
                if event.artifact_path is None:
                    continue
                path = self.root.joinpath(*PurePosixPath(event.artifact_path).parts)
                if path.is_symlink() or not path.is_file():
                    raise RunStateError("registered run artifact is missing or unsafe")
                if hashlib.sha256(path.read_bytes()).hexdigest() != event.artifact_sha256:
                    raise RunStateError("registered run artifact has drifted")
        return events

    def record_stage(
        self,
        *,
        stage: str,
        logical_id: str,
        status: str,
        reason: str,
        artifact_path: str | os.PathLike[str] | None = None,
        input_sha256s: Sequence[str] = (),
        metrics: Mapping[str, Any] | None = None,
        clock: Clock = utc_now,
    ) -> RunEvent:
        manifest = self.manifest
        relative = None
        artifact_digest = None
        if artifact_path is not None:
            artifact = Path(artifact_path)
            try:
                relative = artifact.resolve(strict=True).relative_to(self.root.resolve()).as_posix()
            except (OSError, ValueError) as exc:
                raise RunStateError("stage artifact must be a file inside the run root") from exc
            relative = _relative_artifact(relative)
            if artifact.is_symlink() or not artifact.is_file():
                raise RunStateError("stage artifact must be a regular non-symlink file")
            artifact_digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        normalized_inputs = tuple(sorted(set(input_sha256s)))
        normalized_metrics = dict(metrics or {})
        with _locked_journal(self.journal_path) as handle:
            handle.seek(0)
            events = _events_from_bytes(handle.read(), manifest)
            existing = next(
                (
                    item
                    for item in events
                    if item.stage == stage and item.logical_id == logical_id
                ),
                None,
            )
            if existing is not None:
                requested = (
                    status,
                    reason,
                    relative,
                    artifact_digest,
                    normalized_inputs,
                    normalized_metrics,
                )
                retained = (
                    existing.status,
                    existing.reason,
                    existing.artifact_path,
                    existing.artifact_sha256,
                    existing.input_sha256s,
                    dict(existing.metrics),
                )
                if requested != retained:
                    raise RunStateError("logical stage already has a different result")
                return existing
            now = clock()
            if not isinstance(now, datetime) or now.tzinfo is None:
                raise RunStateError("run journal clock must return an aware datetime")
            created_at = now.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            )
            event = RunEvent(
                sequence=len(events) + 1,
                run_id=manifest.run_id,
                stage=stage,
                logical_id=logical_id,
                status=status,
                reason=reason,
                artifact_path=relative,
                artifact_sha256=artifact_digest,
                input_sha256s=normalized_inputs,
                metrics=normalized_metrics,
                created_at=created_at,
                previous_event_sha256=(events[-1].event_sha256 if events else None),
            )
            handle.seek(0, os.SEEK_END)
            handle.write(_canonical(event.to_dict()) + b"\n")
            return event


__all__ = [
    "JOURNAL_FILENAME",
    "MANIFEST_FILENAME",
    "RUN_JOURNAL_VERSION",
    "RUN_MANIFEST_VERSION",
    "RunEvent",
    "RunManifest",
    "RunStateError",
    "RunStore",
    "USAGE_LEDGER_FILENAME",
]
