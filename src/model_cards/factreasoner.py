"""Deterministic, source-bounded FactReasoner validation kernel.

This module adapts three generic mechanisms proven in Auto-BenchmarkCard:
referent-explicit hypotheses, BM25 retrieval with exact-number anchoring, and a
neutral-only bounded full-source fallback.  It deliberately does not port the
workflow or model-serving orchestration.

``support`` means only that an injected checker found support in the supplied
frozen source contexts.  It is not proof of truth, entity attribution, or field
fit; those remain separate gates.  Missing, thin, out-of-scope, or checker-
unavailable evidence is recorded as ``unavailable`` and is never converted into
an accusation about how the card text was produced.
"""

from __future__ import annotations

from collections import Counter
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import importlib
import importlib.metadata as importlib_metadata
import importlib.util
import json
import math
import os
import re
import threading
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .models import RelationToTarget, SourceDocument, TargetIdentity
from .provider import (
    ProviderError,
    ProviderResponseError,
    ProviderTerminalAttemptError,
    RECOVERABLE_PROVIDER_FAILURE_REASON_CODES,
    TransportUncertainError,
)
from .run_ledger import LedgerError


FACTREASONER_KERNEL_VERSION = "model-card-factreasoner/v4"
ATOM_VERSION = "model-card-fact-atom/v1"
CHUNK_VERSION = "model-card-source-chunk/v1"
DECISION_VERSION = "model-card-fact-decision/v1"
RECORD_VERSION = "model-card-factreasoner-record/v1"
RETRIEVAL_VERSION = "hybrid-bm25-token-vector/v1"
IBM_FACTREASONER_UPSTREAM_REVISION = "41eb0c21baa2a8bba4030cf0d619aa00fae2ed84"
IBM_FACTREASONER_UPSTREAM_URL = "https://github.com/IBM/FactReasoner.git"
IBM_FACTREASONER_ADAPTER_VERSION = "model-card-ibm-factreasoner-fr1/v2"
IBM_FACTREASONER_INFERENCE_METHOD = "pgmpy-variable-elimination"
CHECK_REQUEST_VERSION = "model-card-fact-check-request/v1"
MAX_FACT_CHECKS_PER_BATCH = 64
# OpenRouter's exact structured decision is categorical and does not promise
# token log probabilities.  This fixed, declared factor strength replaces no
# hidden confidence estimate; it is simply the deterministic FR1 edge weight.
IBM_FACTREASONER_RELATION_PROBABILITY = 0.9

# Upstream writes graph diagnostics directly to process-global stdout/stderr.
# A provider-assisted CLI must keep stdout as one machine-readable JSON object,
# so serialize the short local graph/inference section while both streams point
# at the null device.  No model or network call occurs inside this section.
_IBM_FACTREASONER_STDIO_LOCK = threading.Lock()


@contextmanager
def _suppress_upstream_factreasoner_output() -> Iterable[None]:
    with _IBM_FACTREASONER_STDIO_LOCK:
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with redirect_stdout(sink), redirect_stderr(sink):
                yield

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z][a-z0-9._:/-]{1,127}$")
_TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-_][A-Za-z0-9]+)*|\d+(?:[.,]\d+)*%?")
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])[-+]?(?:\d+(?:[.,]\d+)*|\.\d+)"
    r"(?:\s?(?:%|[KMBT]|thousand|million|billion|trillion))?(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_NAME_RE = re.compile(
    r"\b(?:[A-Z][A-Za-z0-9._/-]*)(?:\s+[A-Z][A-Za-z0-9._/-]*){0,4}\b"
)
_MODEL_ID_RE = re.compile(r"\b[A-Za-z0-9._-]+/[A-Za-z0-9._-]+\b")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TABLE_SEPARATOR_RE = re.compile(
    r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$"
)
_ABSENCE_VALUES = frozenset({"not specified", "not applicable"})
_ROW_ATOM_FIELDS = frozenset(
    {
        "evaluation.benchmark_scores",
        "evaluation.related_model_scores",
    }
)


class FactReasonerError(ValueError):
    """Malformed or internally inconsistent FactReasoner material."""


class FactReasonerReplayError(FactReasonerError):
    """A serialized record no longer replays against its declared inputs."""


class UpstreamFactReasonerUnavailable(FactReasonerError):
    """The optional pinned IBM FactReasoner integration is not available."""

    def __init__(self, message: str, *, reason_code: str) -> None:
        super().__init__(message)
        _require_code(reason_code, "upstream FactReasoner reason_code")
        self.reason_code = reason_code


class CheckOutcome(str, Enum):
    SUPPORT = "support"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"
    UNAVAILABLE = "unavailable"


class CheckStage(str, Enum):
    RETRIEVAL = "retrieval"
    FULL_SOURCE_FALLBACK = "full_source_fallback"


class FieldAction(str, Enum):
    NONE = "none"
    REPAIR_OR_WITHHOLD = "repair_or_withhold"
    COLLECT_OR_WITHHOLD = "collect_or_withhold"


class FieldCoverageStatus(str, Enum):
    CHECKED = "checked"
    ABSENCE = "absence"


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise FactReasonerError("FactReasoner values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FactReasonerError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        raise FactReasonerError(
            f"{label} has an invalid shape ({'; '.join(details)})"
        )
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise FactReasonerError(f"{label} must be an array")
    return value


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise FactReasonerError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_code(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise FactReasonerError(f"{label} is invalid")
    return value


def _target_from_dict(value: Any, label: str = "target") -> TargetIdentity:
    item = _strict_object(value, {"model_id", "revision"}, label)
    return TargetIdentity(model_id=item["model_id"], revision=item["revision"])


def _enum(enum_type: type[Enum], value: Any, label: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise FactReasonerError(f"{label} is invalid") from exc


def _content_hash(instance: Any, payload: Mapping[str, Any], label: str) -> None:
    expected = _digest(payload)
    object.__setattr__(instance, "_content_sha256", expected)
    if not _DIGEST_RE.fullmatch(expected):  # pragma: no cover - hashlib invariant
        raise FactReasonerError(f"{label} digest is invalid")


@dataclass(frozen=True)
class RetrievalConfig:
    """Closed resource bounds for chunking, retrieval, and fallback."""

    max_chunk_chars: int = 900
    chunk_overlap_chars: int = 90
    max_source_chars: int = 50_000
    max_total_source_chars: int = 120_000
    top_k: int = 4
    min_source_chars: int = 24
    max_fallback_chunks: int = 64
    max_fallback_chars: int = 48_000

    def __post_init__(self) -> None:
        values = (
            self.max_chunk_chars,
            self.chunk_overlap_chars,
            self.max_source_chars,
            self.max_total_source_chars,
            self.top_k,
            self.min_source_chars,
            self.max_fallback_chunks,
            self.max_fallback_chars,
        )
        if any(not isinstance(item, int) or isinstance(item, bool) for item in values):
            raise FactReasonerError("retrieval bounds must be integers")
        positive = (
            self.max_chunk_chars,
            self.max_source_chars,
            self.max_total_source_chars,
            self.top_k,
            self.min_source_chars,
            self.max_fallback_chunks,
            self.max_fallback_chars,
        )
        if any(item <= 0 for item in positive):
            raise FactReasonerError("retrieval bounds must be positive")
        if self.chunk_overlap_chars < 0:
            raise FactReasonerError("chunk overlap cannot be negative")
        if self.chunk_overlap_chars >= self.max_chunk_chars:
            raise FactReasonerError("chunk overlap must be smaller than a chunk")
        if self.max_source_chars > self.max_total_source_chars:
            raise FactReasonerError("per-source bound cannot exceed total-source bound")
        if self.max_fallback_chars < self.max_chunk_chars:
            raise FactReasonerError("fallback character bound must hold at least one chunk")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_chunk_chars": self.max_chunk_chars,
            "chunk_overlap_chars": self.chunk_overlap_chars,
            "max_source_chars": self.max_source_chars,
            "max_total_source_chars": self.max_total_source_chars,
            "top_k": self.top_k,
            "min_source_chars": self.min_source_chars,
            "max_fallback_chunks": self.max_fallback_chunks,
            "max_fallback_chars": self.max_fallback_chars,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RetrievalConfig":
        item = _strict_object(
            value,
            {
                "max_chunk_chars",
                "chunk_overlap_chars",
                "max_source_chars",
                "max_total_source_chars",
                "top_k",
                "min_source_chars",
                "max_fallback_chunks",
                "max_fallback_chars",
            },
            "retrieval config",
        )
        return cls(**item)


@dataclass(frozen=True)
class ReferentHypothesis:
    """Explicit entity/relation hypothesis carried into every checker request."""

    referent: str
    relation: RelationToTarget

    def __post_init__(self) -> None:
        if not isinstance(self.referent, str) or not self.referent.strip():
            raise FactReasonerError("hypothesis referent must be non-empty")
        object.__setattr__(
            self,
            "relation",
            _enum(RelationToTarget, self.relation, "hypothesis relation"),
        )

    def to_dict(self) -> dict[str, str]:
        return {"referent": self.referent, "relation": self.relation.value}

    @classmethod
    def from_dict(cls, value: Any) -> "ReferentHypothesis":
        item = _strict_object(value, {"referent", "relation"}, "referent hypothesis")
        return cls(referent=item["referent"], relation=item["relation"])


def _target_reference(target: TargetIdentity) -> str:
    return f"{target.model_id}@{target.revision}"


def _validate_hypothesis(target: TargetIdentity, hypothesis: ReferentHypothesis) -> None:
    target_reference = _target_reference(target)
    if (
        hypothesis.relation is RelationToTarget.EXACT_TARGET
        and hypothesis.referent != target_reference
    ):
        raise FactReasonerError(
            "exact-target hypothesis referent must equal the selected target revision"
        )
    if (
        hypothesis.relation is not RelationToTarget.EXACT_TARGET
        and hypothesis.referent == target_reference
    ):
        raise FactReasonerError(
            "non-target relation cannot name the selected target as its referent"
        )


def verbalize_hypothesis(
    target: TargetIdentity,
    field_path: str,
    statement: str,
    hypothesis: ReferentHypothesis,
) -> str:
    """Return a target-, referent-, relation-, and field-explicit hypothesis."""

    _validate_hypothesis(target, hypothesis)
    return (
        f'For selected target "{_target_reference(target)}", the claim referent is '
        f'"{hypothesis.referent}" with relation "{hypothesis.relation.value}"; '
        f'field "{field_path}" asserts: {statement}'
    )


@dataclass(frozen=True)
class FactAtom:
    atom_version: str
    target: TargetIdentity
    field_path: str
    value_path: str
    ordinal: int
    statement: str
    hypothesis: ReferentHypothesis
    field_value_sha256: str
    atom_id: str = dataclass_field(init=False)
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.atom_version != ATOM_VERSION:
            raise FactReasonerError("unsupported fact atom version")
        if not isinstance(self.target, TargetIdentity):
            raise FactReasonerError("fact atom target is invalid")
        if not isinstance(self.field_path, str) or "." not in self.field_path:
            raise FactReasonerError("fact atom field_path is invalid")
        if not isinstance(self.value_path, str) or not self.value_path.startswith(
            self.field_path
        ):
            raise FactReasonerError("fact atom value_path is invalid")
        if not isinstance(self.ordinal, int) or isinstance(self.ordinal, bool) or self.ordinal < 0:
            raise FactReasonerError("fact atom ordinal is invalid")
        if not isinstance(self.statement, str) or not self.statement.strip():
            raise FactReasonerError("fact atom statement must be non-empty")
        if not isinstance(self.hypothesis, ReferentHypothesis):
            raise FactReasonerError("fact atom hypothesis is invalid")
        _validate_hypothesis(self.target, self.hypothesis)
        _require_digest(self.field_value_sha256, "field value digest")
        _content_hash(self, self._content_payload(), "fact atom")
        object.__setattr__(self, "atom_id", "atom-" + self._content_sha256[:24])

    def _content_payload(self) -> dict[str, Any]:
        return {
            "atom_version": self.atom_version,
            "target": self.target.to_dict(),
            "field_path": self.field_path,
            "value_path": self.value_path,
            "ordinal": self.ordinal,
            "statement": self.statement,
            "hypothesis": self.hypothesis.to_dict(),
            "field_value_sha256": self.field_value_sha256,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    @property
    def checker_hypothesis(self) -> str:
        return verbalize_hypothesis(
            self.target,
            self.field_path,
            self.statement,
            self.hypothesis,
        )

    def validate_integrity(self) -> None:
        if self._content_sha256 != _digest(self._content_payload()):
            raise FactReasonerError(f"fact atom integrity failed: {self.atom_id}")
        if self.atom_id != "atom-" + self._content_sha256[:24]:
            raise FactReasonerError("fact atom identifier is inconsistent")

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_id": self.atom_id,
            **self._content_payload(),
            "atom_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "FactAtom":
        item = _strict_object(
            value,
            {
                "atom_id",
                "atom_version",
                "target",
                "field_path",
                "value_path",
                "ordinal",
                "statement",
                "hypothesis",
                "field_value_sha256",
                "atom_sha256",
            },
            "fact atom",
        )
        atom = cls(
            atom_version=item["atom_version"],
            target=_target_from_dict(item["target"], "fact atom target"),
            field_path=item["field_path"],
            value_path=item["value_path"],
            ordinal=item["ordinal"],
            statement=item["statement"],
            hypothesis=ReferentHypothesis.from_dict(item["hypothesis"]),
            field_value_sha256=item["field_value_sha256"],
        )
        if item["atom_id"] != atom.atom_id or item["atom_sha256"] != atom.content_sha256:
            raise FactReasonerError("serialized fact atom digest is inconsistent")
        return atom


@dataclass(frozen=True)
class FieldCoverage:
    field_path: str
    status: FieldCoverageStatus
    field_value_sha256: str
    atom_ids: tuple[str, ...]
    reason_code: str
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.field_path, str) or "." not in self.field_path:
            raise FactReasonerError("field coverage path is invalid")
        object.__setattr__(
            self,
            "status",
            _enum(FieldCoverageStatus, self.status, "field coverage status"),
        )
        _require_digest(self.field_value_sha256, "field coverage value digest")
        atom_ids = tuple(self.atom_ids)
        if len(atom_ids) != len(set(atom_ids)):
            raise FactReasonerError("field coverage has duplicate atom identifiers")
        if any(not isinstance(item, str) or not item.startswith("atom-") for item in atom_ids):
            raise FactReasonerError("field coverage atom identifier is invalid")
        object.__setattr__(self, "atom_ids", atom_ids)
        _require_code(self.reason_code, "field coverage reason_code")
        if self.status is FieldCoverageStatus.CHECKED and not atom_ids:
            raise FactReasonerError("checked field coverage requires at least one atom")
        if self.status is FieldCoverageStatus.ABSENCE and atom_ids:
            raise FactReasonerError("absence field coverage cannot contain atoms")
        _content_hash(self, self._content_payload(), "field coverage")

    def _content_payload(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "status": self.status.value,
            "field_value_sha256": self.field_value_sha256,
            "atom_ids": list(self.atom_ids),
            "reason_code": self.reason_code,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "coverage_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "FieldCoverage":
        item = _strict_object(
            value,
            {
                "field_path",
                "status",
                "field_value_sha256",
                "atom_ids",
                "reason_code",
                "coverage_sha256",
            },
            "field coverage",
        )
        coverage = cls(
            field_path=item["field_path"],
            status=item["status"],
            field_value_sha256=item["field_value_sha256"],
            atom_ids=tuple(_array(item["atom_ids"], "field coverage atom_ids")),
            reason_code=item["reason_code"],
        )
        if item["coverage_sha256"] != coverage.content_sha256:
            raise FactReasonerError("serialized field coverage digest is inconsistent")
        return coverage


@dataclass(frozen=True)
class AtomizationResult:
    card_sha256: str
    schema_sha256: str
    atoms: tuple[FactAtom, ...]
    field_coverage: tuple[FieldCoverage, ...]

    def __post_init__(self) -> None:
        _require_digest(self.card_sha256, "card digest")
        _require_digest(self.schema_sha256, "schema digest")
        object.__setattr__(self, "atoms", tuple(self.atoms))
        object.__setattr__(self, "field_coverage", tuple(self.field_coverage))
        if not all(isinstance(item, FactAtom) for item in self.atoms):
            raise FactReasonerError("atomization atoms must be typed records")
        if not all(isinstance(item, FieldCoverage) for item in self.field_coverage):
            raise FactReasonerError("atomization field coverage must be typed records")
        atom_ids = [item.atom_id for item in self.atoms]
        if len(atom_ids) != len(set(atom_ids)):
            raise FactReasonerError("atomization produced duplicate atom identifiers")
        coverage_paths = [item.field_path for item in self.field_coverage]
        if len(coverage_paths) != len(set(coverage_paths)):
            raise FactReasonerError("atomization produced duplicate field coverage")
        covered = [atom_id for item in self.field_coverage for atom_id in item.atom_ids]
        if Counter(covered) != Counter(atom_ids):
            raise FactReasonerError("field coverage and atomization diverge")


@dataclass(frozen=True)
class SourceAvailability:
    """Visible frozen-source load outcome, including non-loaded sources."""

    source_id: str
    status: str
    reason_code: str
    source_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_code(self.source_id, "source availability source_id")
        _require_code(self.status, "source availability status")
        _require_code(self.reason_code, "source availability reason_code")
        if self.source_sha256 is not None:
            _require_digest(self.source_sha256, "source availability digest")
        if self.status == "loaded" and self.source_sha256 is None:
            raise FactReasonerError("loaded source availability requires a digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "status": self.status,
            "reason_code": self.reason_code,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "SourceAvailability":
        item = _strict_object(
            value,
            {"source_id", "status", "reason_code", "source_sha256"},
            "source availability",
        )
        return cls(**item)

    @classmethod
    def from_catalog_record(cls, value: Any) -> "SourceAvailability":
        if isinstance(value, Mapping):
            status = value.get("status")
            return cls(
                source_id=value.get("source_id"),
                status=getattr(status, "value", status),
                reason_code=value.get("reason_code"),
                source_sha256=value.get("source_sha256"),
            )
        status = getattr(value, "status", None)
        return cls(
            source_id=getattr(value, "source_id"),
            status=getattr(status, "value", status),
            reason_code=getattr(value, "reason_code"),
            source_sha256=getattr(value, "source_sha256", None),
        )


@dataclass(frozen=True)
class SourceChunk:
    """One exact slice or JSON pointer from a frozen source."""

    chunk_version: str
    source_id: str
    source_uri: str
    source_revision: str
    source_sha256: str
    source_target: TargetIdentity | None
    text: str
    char_start: int | None
    char_end: int | None
    json_pointer: str | None
    section_path: tuple[str, ...]
    table_context: str | None
    chunk_id: str = dataclass_field(init=False)
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.chunk_version != CHUNK_VERSION:
            raise FactReasonerError("unsupported source chunk version")
        _require_code(self.source_id, "source chunk source_id")
        if not isinstance(self.source_uri, str) or not self.source_uri:
            raise FactReasonerError("source chunk URI is invalid")
        if not isinstance(self.source_revision, str) or not self.source_revision:
            raise FactReasonerError("source chunk revision is invalid")
        _require_digest(self.source_sha256, "source chunk source digest")
        if self.source_target is not None and not isinstance(
            self.source_target, TargetIdentity
        ):
            raise FactReasonerError("source chunk target is invalid")
        if not isinstance(self.text, str) or not self.text.strip():
            raise FactReasonerError("source chunk text must be non-empty")
        span = self.char_start is not None or self.char_end is not None
        pointer = self.json_pointer is not None
        if span == pointer:
            raise FactReasonerError("source chunk requires exactly one coordinate kind")
        if span:
            if (
                not isinstance(self.char_start, int)
                or isinstance(self.char_start, bool)
                or not isinstance(self.char_end, int)
                or isinstance(self.char_end, bool)
                or self.char_start < 0
                or self.char_end <= self.char_start
            ):
                raise FactReasonerError("source chunk character span is invalid")
        if pointer and (
            not isinstance(self.json_pointer, str) or not self.json_pointer.startswith("/")
        ):
            raise FactReasonerError("source chunk JSON pointer is invalid")
        section_path = tuple(self.section_path)
        if any(not isinstance(item, str) or not item for item in section_path):
            raise FactReasonerError("source chunk section path is invalid")
        object.__setattr__(self, "section_path", section_path)
        if self.table_context is not None and (
            not isinstance(self.table_context, str) or not self.table_context.strip()
        ):
            raise FactReasonerError("source chunk table context is invalid")
        _content_hash(self, self._content_payload(), "source chunk")
        object.__setattr__(self, "chunk_id", "chunk-" + self._content_sha256[:24])

    def _content_payload(self, *, include_text: bool = True) -> dict[str, Any]:
        payload = {
            "chunk_version": self.chunk_version,
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "source_target": self.source_target.to_dict() if self.source_target else None,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "json_pointer": self.json_pointer,
            "section_path": list(self.section_path),
            "table_context": self.table_context,
        }
        if include_text:
            payload["text"] = self.text
        return payload

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def validate_integrity(self) -> None:
        if self._content_sha256 != _digest(self._content_payload()):
            raise FactReasonerError(f"source chunk integrity failed: {self.chunk_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            **self._content_payload(),
            "chunk_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "SourceChunk":
        item = _strict_object(
            value,
            {
                "chunk_id",
                "chunk_version",
                "source_id",
                "source_uri",
                "source_revision",
                "source_sha256",
                "source_target",
                "text",
                "char_start",
                "char_end",
                "json_pointer",
                "section_path",
                "table_context",
                "chunk_sha256",
            },
            "source chunk",
        )
        target = item["source_target"]
        chunk = cls(
            chunk_version=item["chunk_version"],
            source_id=item["source_id"],
            source_uri=item["source_uri"],
            source_revision=item["source_revision"],
            source_sha256=item["source_sha256"],
            source_target=(
                _target_from_dict(target, "source chunk target")
                if target is not None
                else None
            ),
            text=item["text"],
            char_start=item["char_start"],
            char_end=item["char_end"],
            json_pointer=item["json_pointer"],
            section_path=tuple(_array(item["section_path"], "source chunk section_path")),
            table_context=item["table_context"],
        )
        if item["chunk_id"] != chunk.chunk_id or item["chunk_sha256"] != chunk.content_sha256:
            raise FactReasonerError("serialized source chunk digest is inconsistent")
        return chunk


@dataclass(frozen=True)
class ChunkCorpus:
    chunks: tuple[SourceChunk, ...]
    sources: tuple[SourceAvailability, ...]
    original_chars: int
    indexed_chars: int
    truncated: bool
    corpus_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "chunks", tuple(self.chunks))
        object.__setattr__(self, "sources", tuple(self.sources))
        if not all(isinstance(item, SourceChunk) for item in self.chunks):
            raise FactReasonerError("chunk corpus chunks must be typed records")
        if not all(isinstance(item, SourceAvailability) for item in self.sources):
            raise FactReasonerError("chunk corpus sources must be typed records")
        if any(
            not isinstance(item, int) or isinstance(item, bool) or item < 0
            for item in (self.original_chars, self.indexed_chars)
        ):
            raise FactReasonerError("chunk corpus character counts are invalid")
        if not isinstance(self.truncated, bool):
            raise FactReasonerError("chunk corpus truncated flag is invalid")
        if self.indexed_chars > self.original_chars:
            raise FactReasonerError("chunk corpus indexed chars exceed source chars")
        chunk_ids = [item.chunk_id for item in self.chunks]
        source_ids = [item.source_id for item in self.sources]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise FactReasonerError("chunk corpus has duplicate chunk identifiers")
        if len(source_ids) != len(set(source_ids)):
            raise FactReasonerError("chunk corpus has duplicate source records")
        expected = _digest(self._content_payload())
        if self.corpus_sha256 != expected:
            raise FactReasonerError("chunk corpus digest is inconsistent")

    def _content_payload(self) -> dict[str, Any]:
        return {
            "chunks": [item.to_dict() for item in self.chunks],
            "sources": [item.to_dict() for item in self.sources],
            "original_chars": self.original_chars,
            "indexed_chars": self.indexed_chars,
            "truncated": self.truncated,
        }


def _resolve_schema(schema: Mapping[str, Any], node: Mapping[str, Any]) -> Mapping[str, Any]:
    current: Mapping[str, Any] = node
    seen: set[str] = set()
    while isinstance(current.get("$ref"), str):
        reference = current["$ref"]
        if not reference.startswith("#/") or reference in seen:
            raise FactReasonerError("atomizer supports only acyclic internal schema references")
        seen.add(reference)
        value: Any = schema
        for component in reference[2:].split("/"):
            component = component.replace("~1", "/").replace("~0", "~")
            if not isinstance(value, Mapping) or component not in value:
                raise FactReasonerError(f"schema reference does not resolve: {reference}")
            value = value[component]
        if not isinstance(value, Mapping):
            raise FactReasonerError(f"schema reference is not an object: {reference}")
        current = value
    return current


def _property_order(node: Mapping[str, Any]) -> tuple[str, ...]:
    properties = node.get("properties", {})
    if not isinstance(properties, Mapping):
        return ()
    required = node.get("required", [])
    ordered = [item for item in required if isinstance(item, str) and item in properties]
    ordered.extend(sorted(item for item in properties if item not in ordered))
    return tuple(ordered)


def _eligible_field_specs(
    card: Mapping[str, Any], schema: Mapping[str, Any]
) -> tuple[tuple[str, Any], ...]:
    metadata = schema.get("x-model-card", {})
    sections: Sequence[str] | None = None
    if isinstance(metadata, Mapping):
        declared = metadata.get("bindable_sections") or metadata.get("eligible_sections")
        if isinstance(declared, Sequence) and not isinstance(declared, (str, bytes)):
            sections = tuple(str(item) for item in declared)
    root = _resolve_schema(schema, schema)
    root_properties = root.get("properties", {})
    if not isinstance(root_properties, Mapping):
        raise FactReasonerError("card schema must declare root properties")
    if sections is None:
        excluded = {
            "$schema",
            "contract_version",
            "provenance",
            "validation",
            "lifecycle",
        }
        sections = tuple(
            item for item in _property_order(root) if item not in excluded
        )

    fields: list[tuple[str, Any]] = []
    for section in sections:
        if section not in card or section not in root_properties:
            raise FactReasonerError(f"eligible schema section is missing from card: {section}")
        section_value = card[section]
        section_schema = _resolve_schema(schema, root_properties[section])
        if not isinstance(section_value, Mapping):
            fields.append((section, section_value))
            continue
        required_fields = {
            item
            for item in section_schema.get("required", ())
            if isinstance(item, str)
        }
        for field in _property_order(section_schema):
            if field not in section_value:
                if field in required_fields:
                    raise FactReasonerError(
                        f"eligible field is missing from card: {section}.{field}"
                    )
                fields.append((f"{section}.{field}", None))
            else:
                fields.append((f"{section}.{field}", section_value[field]))
    if not fields:
        raise FactReasonerError("schema exposes no eligible final fields")
    return tuple(fields)


def _is_absence(value: Any) -> bool:
    return value is None or (
        isinstance(value, str) and value.strip().casefold() in _ABSENCE_VALUES
    )


def _json_pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _sentence_atoms(text: str) -> tuple[str, ...]:
    normalized = text.strip()
    if not normalized:
        return ("The field is an empty string.",)

    # A citation is a metadata unit, not a sequence of prose claims.  Splitting
    # fenced BibTeX at line boundaries used to create hypotheses such as ``}``
    # and ``title={...},``.  Keep the complete unit together so the checker can
    # compare it to an exact source citation without manufacturing fragments.
    lowered = normalized.casefold()
    if "```bibtex" in lowered or normalized.startswith("@"):
        return (normalized,)

    parts = re.split(
        r"(?:\r?\n\s*(?:[-*]\s+)?)|(?<=[.!?])\s+|;\s+(?=[A-Z])",
        normalized,
    )
    atoms = tuple(
        item.strip()
        for item in parts
        if item.strip() and re.search(r"[A-Za-z0-9]", item)
    )
    return atoms or (normalized,)


def _scalar_text(path: str, value: Any, context: tuple[str, ...]) -> str:
    label = path.rsplit(".", 1)[-1].replace("_", " ")
    rendered = _canonical(value)
    prefix = f"Within {'; '.join(context)}, " if context else ""
    return f"{prefix}{label} is {rendered}."


def _context_for_mapping(value: Mapping[str, Any]) -> tuple[str, ...]:
    context = []
    for key in sorted(value):
        item = value[key]
        if _is_absence(item) or isinstance(item, (Mapping, list)):
            continue
        rendered = _canonical(item)
        if len(rendered) <= 120:
            context.append(f"{key}={rendered}")
    return tuple(context)


def _atomic_values(
    value: Any,
    value_path: str,
    context: tuple[str, ...] = (),
) -> tuple[tuple[str, str], ...]:
    if isinstance(value, str):
        if value_path.rsplit(".", 1)[-1] == "citation":
            return ((value_path, _scalar_text(value_path, value, context)),)
        return tuple((value_path, item) for item in _sentence_atoms(value))
    if isinstance(value, Mapping):
        if not value:
            return ((value_path, f'Field "{value_path}" is an empty object.'),)
        if any(
            value_path == field or value_path.startswith(field + "[")
            for field in _ROW_ATOM_FIELDS
        ):
            # Benchmark results are factual tuples.  Checking each scalar in
            # isolation loses the benchmark/model/metric/value association and
            # recreates the wrong-row leakage observed in the AAAI audit.
            return (
                (
                    value_path,
                    f'Complete score row for "{value_path}" is {_canonical(value)}.',
                ),
            )
        local_context = context + _context_for_mapping(value)
        atoms: list[tuple[str, str]] = []
        for key in sorted(value):
            item = value[key]
            child = f"{value_path}.{key}"
            if isinstance(item, (Mapping, list)):
                atoms.extend(_atomic_values(item, child, local_context))
            else:
                atoms.append((child, _scalar_text(child, item, local_context)))
        return tuple(atoms)
    if isinstance(value, list):
        if not value:
            return ((value_path, f'Field "{value_path}" is an empty list.'),)
        atoms = []
        for index, item in enumerate(value):
            child = f"{value_path}[{index}]"
            if isinstance(item, (Mapping, list)):
                atoms.extend(_atomic_values(item, child, context))
            elif isinstance(item, str):
                atoms.extend((child, part) for part in _sentence_atoms(item))
            else:
                atoms.append((child, _scalar_text(child, item, context)))
        return tuple(atoms)
    return ((value_path, _scalar_text(value_path, value, context)),)


def hypotheses_from_provenance(
    card: Mapping[str, Any],
) -> dict[str, ReferentHypothesis]:
    """Read unambiguous per-field referent hypotheses from public provenance.

    Multiple evidence references may support one field, but they must agree on
    the claimed entity and target relation.  Ambiguity is rejected instead of
    silently choosing one referent.  Cards without public field references
    simply return an empty mapping and use the explicit exact-target default.
    """

    provenance = card.get("provenance") if isinstance(card, Mapping) else None
    if provenance is None:
        return {}
    if not isinstance(provenance, Mapping):
        raise FactReasonerError("card provenance must be an object")
    references = provenance.get("field_references", {})
    if not isinstance(references, Mapping):
        raise FactReasonerError("card provenance field_references must be an object")
    if any(not isinstance(item, str) for item in references):
        raise FactReasonerError("field provenance path is invalid")
    hypotheses: dict[str, ReferentHypothesis] = {}
    for field_path in sorted(references):
        entries = references[field_path]
        if not isinstance(field_path, str) or not isinstance(entries, list) or not entries:
            raise FactReasonerError("field provenance reference is malformed")
        pairs = set()
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise FactReasonerError("field provenance entry must be an object")
            referent = entry.get("claimed_entity")
            relation = entry.get("relation")
            if not isinstance(referent, str) or not referent.strip():
                raise FactReasonerError("field provenance claimed_entity is invalid")
            try:
                typed_relation = RelationToTarget(relation)
            except (TypeError, ValueError) as exc:
                raise FactReasonerError("field provenance relation is invalid") from exc
            pairs.add((referent, typed_relation))
        if len(pairs) != 1:
            raise FactReasonerError(
                f"field provenance has conflicting referent hypotheses: {field_path}"
            )
        referent, relation = next(iter(pairs))
        hypotheses[field_path] = ReferentHypothesis(referent, relation)
    return hypotheses


def atomize_card(
    card: Mapping[str, Any],
    schema: Mapping[str, Any],
    target: TargetIdentity,
    *,
    field_hypotheses: Mapping[str, ReferentHypothesis] | None = None,
) -> AtomizationResult:
    """Atomize every schema-eligible final field and account for absences.

    The schema decides which sections and fields are eligible.  Every eligible
    field receives one ``FieldCoverage`` record: absence markers are explicit,
    and every other value yields at least one independently addressable atom.
    """

    if not isinstance(card, Mapping) or not isinstance(schema, Mapping):
        raise FactReasonerError("card and schema must be mappings")
    if not isinstance(target, TargetIdentity):
        raise FactReasonerError("atomization target must be a TargetIdentity")
    try:
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(card),
            key=lambda item: tuple(str(part) for part in item.absolute_path),
        )
    except SchemaError as exc:
        raise FactReasonerError("atomization schema is not valid Draft 2020-12") from exc
    if errors:
        raise FactReasonerError(f"card does not satisfy atomization schema: {errors[0].message}")

    inferred_hypotheses = hypotheses_from_provenance(card)
    field_hypotheses = {**inferred_hypotheses, **(field_hypotheses or {})}
    field_specs = _eligible_field_specs(card, schema)
    eligible_paths = {path for path, _ in field_specs}
    unknown = {
        key
        for key in field_hypotheses
        if not isinstance(key, str)
        or not any(
            key == path
            or key.startswith(path + "[")
            or key.startswith(path + ".")
            for path in eligible_paths
        )
    }
    if unknown:
        raise FactReasonerError(
            "hypotheses name non-eligible fields: " + ", ".join(sorted(unknown))
        )
    atoms: list[FactAtom] = []
    coverage: list[FieldCoverage] = []
    default_hypothesis = ReferentHypothesis(
        referent=_target_reference(target),
        relation=RelationToTarget.EXACT_TARGET,
    )
    for field_path, value in field_specs:
        value_digest = _digest(value)
        if _is_absence(value):
            coverage.append(
                FieldCoverage(
                    field_path=field_path,
                    status=FieldCoverageStatus.ABSENCE,
                    field_value_sha256=value_digest,
                    atom_ids=(),
                    reason_code="declared_absence",
                )
            )
            continue
        field_atoms = []
        for ordinal, (value_path, statement) in enumerate(
            _atomic_values(deepcopy(value), field_path)
        ):
            matching_hypotheses = [
                key
                for key in field_hypotheses
                if value_path == key
                or value_path.startswith(key + ".")
                or value_path.startswith(key + "[")
            ]
            hypothesis_key = max(matching_hypotheses, key=len, default=None)
            hypothesis = (
                field_hypotheses[hypothesis_key]
                if hypothesis_key is not None
                else default_hypothesis
            )
            if not isinstance(hypothesis, ReferentHypothesis):
                raise FactReasonerError(
                    f"field hypothesis is not typed: {hypothesis_key or field_path}"
                )
            _validate_hypothesis(target, hypothesis)
            atom = FactAtom(
                atom_version=ATOM_VERSION,
                target=target,
                field_path=field_path,
                value_path=value_path,
                ordinal=ordinal,
                statement=statement,
                hypothesis=hypothesis,
                field_value_sha256=value_digest,
            )
            atoms.append(atom)
            field_atoms.append(atom.atom_id)
        coverage.append(
            FieldCoverage(
                field_path=field_path,
                status=FieldCoverageStatus.CHECKED,
                field_value_sha256=value_digest,
                atom_ids=tuple(field_atoms),
                reason_code="atomized",
            )
        )
    return AtomizationResult(
        card_sha256=_digest(card),
        schema_sha256=_digest(schema),
        atoms=tuple(atoms),
        field_coverage=tuple(coverage),
    )


def _line_offsets(text: str) -> tuple[tuple[int, int, str], ...]:
    output = []
    offset = 0
    for line in text.splitlines(keepends=True):
        end = offset + len(line)
        output.append((offset, end, line))
        offset = end
    if offset < len(text):
        output.append((offset, len(text), text[offset:]))
    return tuple(output)


def _bounded_spans(
    text: str,
    start: int,
    end: int,
    max_chars: int,
    overlap: int,
) -> tuple[tuple[int, int], ...]:
    spans = []
    cursor = start
    while cursor < end:
        proposed = min(cursor + max_chars, end)
        if proposed < end:
            boundary = text.rfind(" ", cursor + max_chars // 2, proposed)
            if boundary > cursor:
                proposed = boundary
        if proposed <= cursor:
            proposed = min(cursor + max_chars, end)
        spans.append((cursor, proposed))
        if proposed >= end:
            break
        cursor = max(proposed - overlap, cursor + 1)
    return tuple(spans)


def _make_text_chunk(
    source: SourceDocument,
    text: str,
    start: int,
    end: int,
    section_path: tuple[str, ...],
    table_context: str | None = None,
) -> SourceChunk | None:
    body = text[start:end]
    if not body.strip():
        return None
    return SourceChunk(
        chunk_version=CHUNK_VERSION,
        source_id=source.source_id,
        source_uri=source.source_uri,
        source_revision=source.source_revision,
        source_sha256=source.sha256,
        source_target=source.target,
        text=body,
        char_start=start,
        char_end=end,
        json_pointer=None,
        section_path=section_path,
        table_context=table_context,
    )


def _text_chunks(
    source: SourceDocument, text: str, config: RetrievalConfig
) -> tuple[SourceChunk, ...]:
    lines = _line_offsets(text)
    chunks: list[SourceChunk] = []
    headings: list[str] = []
    index = 0
    paragraph_start: int | None = None
    paragraph_end: int | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph_start, paragraph_end
        if paragraph_start is None or paragraph_end is None:
            return
        for start, end in _bounded_spans(
            text,
            paragraph_start,
            paragraph_end,
            config.max_chunk_chars,
            config.chunk_overlap_chars,
        ):
            chunk = _make_text_chunk(source, text, start, end, tuple(headings))
            if chunk:
                chunks.append(chunk)
        paragraph_start = paragraph_end = None

    while index < len(lines):
        start, end, line = lines[index]
        stripped = line.strip()
        heading = _HEADING_RE.match(stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            headings[level - 1 :] = [heading.group(2)]
            index += 1
            continue
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        is_table = "|" in stripped and index + 1 < len(lines) and _TABLE_SEPARATOR_RE.match(
            lines[index + 1][2].strip()
        )
        if is_table:
            flush_paragraph()
            header = line.rstrip("\r\n")
            separator = lines[index + 1][2].rstrip("\r\n")
            table_context = header + "\n" + separator
            index += 2
            rows = []
            while index < len(lines):
                row_start, row_end, row = lines[index]
                if "|" not in row.strip() or not row.strip():
                    break
                rows.append((row_start, row_end))
                index += 1
            if not rows:
                rows.append((start, lines[index - 1][1]))
            for row_start, row_end in rows:
                for span_start, span_end in _bounded_spans(
                    text,
                    row_start,
                    row_end,
                    config.max_chunk_chars,
                    config.chunk_overlap_chars,
                ):
                    chunk = _make_text_chunk(
                        source,
                        text,
                        span_start,
                        span_end,
                        tuple(headings),
                        table_context,
                    )
                    if chunk:
                        chunks.append(chunk)
            continue
        if paragraph_start is None:
            paragraph_start = start
        paragraph_end = end
        index += 1
    flush_paragraph()
    return tuple(chunks)


def _pointer(path: tuple[str | int, ...]) -> str:
    return "/" + "/".join(_json_pointer_escape(str(item)) for item in path)


def _json_leaves(value: Any, path: tuple[str | int, ...] = ()) -> Iterable[tuple[str, Any]]:
    if isinstance(value, Mapping):
        if not value:
            yield _pointer(path or ("root",)), {}
        for key in sorted(value):
            yield from _json_leaves(value[key], path + (str(key),))
    elif isinstance(value, list):
        if not value:
            yield _pointer(path or ("root",)), []
        for index, item in enumerate(value):
            yield from _json_leaves(item, path + (index,))
    else:
        yield _pointer(path or ("root",)), value


def _json_chunks(
    source: SourceDocument,
    data: Any,
    max_chars: int,
    chunk_chars: int,
) -> tuple[SourceChunk, ...]:
    chunks = []
    consumed = 0
    for pointer, value in _json_leaves(data):
        rendered = f"{pointer} = {_canonical(value)}"
        remaining = max_chars - consumed
        if remaining <= 0:
            break
        rendered = rendered[:remaining]
        for offset in range(0, len(rendered), chunk_chars):
            part = rendered[offset : offset + chunk_chars]
            if not part.strip():
                continue
            chunks.append(
                SourceChunk(
                    chunk_version=CHUNK_VERSION,
                    source_id=source.source_id,
                    source_uri=source.source_uri,
                    source_revision=source.source_revision,
                    source_sha256=source.sha256,
                    source_target=source.target,
                    text=part,
                    char_start=None,
                    char_end=None,
                    json_pointer=pointer,
                    section_path=tuple(
                        component.replace("~1", "/").replace("~0", "~")
                        for component in pointer.strip("/").split("/")[:-1]
                        if component
                    ),
                    table_context=None,
                )
            )
        consumed += len(rendered)
    return tuple(chunks)


def _normalize_availability(
    sources: Sequence[SourceDocument],
    source_availability: Sequence[SourceAvailability | Any],
) -> tuple[SourceAvailability, ...]:
    loaded = {
        source.source_id: SourceAvailability(
            source_id=source.source_id,
            status="loaded",
            reason_code="loaded",
            source_sha256=source.sha256,
        )
        for source in sources
    }
    explicit = {}
    for value in source_availability:
        item = (
            value
            if isinstance(value, SourceAvailability)
            else SourceAvailability.from_catalog_record(value)
        )
        if item.source_id in explicit:
            raise FactReasonerError("duplicate source availability record")
        explicit[item.source_id] = item
    for source_id, availability in loaded.items():
        existing = explicit.get(source_id)
        if existing is not None and existing != availability:
            raise FactReasonerError("loaded source and availability record disagree")
        explicit[source_id] = availability
    return tuple(explicit[key] for key in sorted(explicit))


def build_source_chunks(
    sources: Sequence[SourceDocument],
    *,
    config: RetrievalConfig | None = None,
    source_availability: Sequence[SourceAvailability | Any] = (),
) -> ChunkCorpus:
    """Build bounded chunks only from typed frozen ``SourceDocument`` inputs."""

    config = config or RetrievalConfig()
    if not isinstance(config, RetrievalConfig):
        raise FactReasonerError("chunking config must be RetrievalConfig")
    frozen_sources = tuple(sources)
    if not all(isinstance(item, SourceDocument) for item in frozen_sources):
        raise FactReasonerError("chunking accepts only typed frozen SourceDocument inputs")
    source_ids = [item.source_id for item in frozen_sources]
    if len(source_ids) != len(set(source_ids)):
        raise FactReasonerError("chunking received duplicate source identifiers")
    availability = _normalize_availability(frozen_sources, source_availability)
    chunks: list[SourceChunk] = []
    source_sizes = {
        item.source_id: (
            len(item.text) if item.text is not None else len(_canonical(item.data))
        )
        for item in frozen_sources
    }
    original_chars = sum(source_sizes.values())
    indexed_chars = 0
    truncated = False
    remaining_total = config.max_total_source_chars
    for source in sorted(frozen_sources, key=lambda item: item.source_id):
        if remaining_total <= 0:
            truncated = True
            continue
        if source.text is not None:
            source_text = source.text[: min(config.max_source_chars, remaining_total)]
            source_chunks = _text_chunks(source, source_text, config)
            consumed = len(source_text)
        else:
            rendered = _canonical(source.data)
            consumed = min(len(rendered), config.max_source_chars, remaining_total)
            source_chunks = _json_chunks(
                source,
                source.data,
                consumed,
                config.max_chunk_chars,
            )
        indexed_chars += consumed
        remaining_total -= consumed
        chunks.extend(source_chunks)
        if consumed < source_sizes[source.source_id]:
            truncated = True
    truncated = truncated or indexed_chars < original_chars
    payload = {
        "chunks": [item.to_dict() for item in chunks],
        "sources": [item.to_dict() for item in availability],
        "original_chars": original_chars,
        "indexed_chars": indexed_chars,
        "truncated": truncated,
    }
    return ChunkCorpus(
        chunks=tuple(chunks),
        sources=availability,
        original_chars=original_chars,
        indexed_chars=indexed_chars,
        truncated=truncated,
        corpus_sha256=_digest(payload),
    )


def _tokenize(text: str) -> tuple[str, ...]:
    return tuple(item.casefold().replace(",", "") for item in _TOKEN_RE.findall(text))


def _number_anchors(text: str) -> tuple[str, ...]:
    return tuple(sorted({item.casefold().replace(",", "") for item in _NUMBER_RE.findall(text)}))


def _name_anchors(text: str) -> tuple[str, ...]:
    anchors = {item.casefold() for item in _MODEL_ID_RE.findall(text)}
    stop = {"the", "this", "for", "field", "within", "not", "specified", "applicable"}
    for match in _NAME_RE.findall(text):
        normalized = " ".join(match.split()).casefold()
        if normalized not in stop and len(normalized) > 2:
            anchors.add(normalized)
    return tuple(sorted(anchors))


def _retrieval_text(chunk: SourceChunk) -> str:
    parts = [" ".join(chunk.section_path)]
    if chunk.table_context:
        parts.append(chunk.table_context)
    parts.append(chunk.text)
    return "\n".join(item for item in parts if item)


def _bm25_scores(query: Sequence[str], chunks: Sequence[SourceChunk]) -> tuple[float, ...]:
    documents = [_tokenize(_retrieval_text(item)) for item in chunks]
    count = len(documents)
    if not count:
        return ()
    frequencies = Counter()
    for document in documents:
        frequencies.update(set(document))
    idf = {
        token: math.log((count - frequency + 0.5) / (frequency + 0.5) + 1.0)
        for token, frequency in frequencies.items()
    }
    lengths = [len(item) for item in documents]
    average = sum(lengths) / count if count else 1.0
    query_terms = set(query)
    scores = []
    for document, length in zip(documents, lengths):
        term_counts = Counter(document)
        score = 0.0
        for token in sorted(query_terms):
            frequency = term_counts.get(token, 0)
            if not frequency:
                continue
            score += idf.get(token, 0.0) * (frequency * 2.5) / (
                frequency + 1.5 * (1.0 - 0.75 + 0.75 * length / (average or 1.0))
            )
        scores.append(score)
    return tuple(scores)


def _cosine(query: Counter[str], document: Counter[str]) -> float:
    if not query or not document:
        return 0.0
    numerator = sum(value * document.get(token, 0) for token, value in query.items())
    left = math.sqrt(sum(value * value for value in query.values()))
    right = math.sqrt(sum(value * value for value in document.values()))
    return numerator / (left * right) if left and right else 0.0


@dataclass(frozen=True)
class CheckContext:
    """A checker-visible chunk plus deterministic retrieval metadata."""

    chunk: SourceChunk
    stage: CheckStage
    retrieval_score: float

    def __post_init__(self) -> None:
        if not isinstance(self.chunk, SourceChunk):
            raise FactReasonerError("check context chunk is invalid")
        object.__setattr__(self, "stage", _enum(CheckStage, self.stage, "check stage"))
        if (
            not isinstance(self.retrieval_score, (int, float))
            or isinstance(self.retrieval_score, bool)
            or not math.isfinite(self.retrieval_score)
            or self.retrieval_score < 0
        ):
            raise FactReasonerError("check context retrieval score is invalid")
        object.__setattr__(self, "retrieval_score", round(float(self.retrieval_score), 8))

    @property
    def text(self) -> str:
        metadata = []
        if self.chunk.section_path:
            metadata.append("SECTION: " + " > ".join(self.chunk.section_path))
        if self.chunk.table_context:
            metadata.append("TABLE HEADER:\n" + self.chunk.table_context)
        metadata.append(self.chunk.text)
        return "\n".join(metadata)


def retrieve_chunks(
    atom: FactAtom,
    chunks: Sequence[SourceChunk],
    *,
    top_k: int = 4,
) -> tuple[CheckContext, ...]:
    """Bounded deterministic hybrid BM25 + token-vector retrieval."""

    if not isinstance(atom, FactAtom):
        raise FactReasonerError("retrieval atom is invalid")
    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        raise FactReasonerError("retrieval top_k must be positive")
    candidates = tuple(chunks)
    if not all(isinstance(item, SourceChunk) for item in candidates):
        raise FactReasonerError("retrieval candidates must be source chunks")
    query_text = " ".join(
        (
            atom.statement,
            atom.field_path.replace(".", " ").replace("_", " "),
            atom.hypothesis.referent,
        )
    )
    query_tokens = _tokenize(query_text)
    query_vector = Counter(query_tokens)
    lexical = _bm25_scores(query_tokens, candidates)
    numbers = _number_anchors(atom.statement)
    names = _name_anchors(atom.statement)
    ranked = []
    for index, chunk in enumerate(candidates):
        retrieval_text = _retrieval_text(chunk)
        normalized = retrieval_text.casefold().replace(",", "")
        vector = _cosine(query_vector, Counter(_tokenize(retrieval_text)))
        chunk_numbers = _number_anchors(retrieval_text)
        exact_number_count = sum(item in chunk_numbers for item in numbers)
        exact_name_count = sum(item in normalized for item in names)
        score = lexical[index] + vector
        score += exact_number_count * 3.0
        score += exact_name_count * 0.8
        if numbers and chunk_numbers and not exact_number_count:
            score *= 0.7
        ranked.append(
            (
                -round(score, 8),
                chunk.source_id,
                chunk.char_start if chunk.char_start is not None else -1,
                chunk.json_pointer or "",
                chunk.chunk_id,
                CheckContext(
                    chunk=chunk,
                    stage=CheckStage.RETRIEVAL,
                    retrieval_score=max(score, 0.0),
                ),
            )
        )
    ranked.sort(key=lambda item: item[:-1])
    return tuple(item[-1] for item in ranked[:top_k])


@dataclass(frozen=True)
class CheckRequest:
    atom: FactAtom
    stage: CheckStage
    contexts: tuple[CheckContext, ...]
    fallback_complete: bool

    def __post_init__(self) -> None:
        if not isinstance(self.atom, FactAtom):
            raise FactReasonerError("checker request atom is invalid")
        object.__setattr__(self, "stage", _enum(CheckStage, self.stage, "check stage"))
        contexts = tuple(self.contexts)
        if not contexts or not all(isinstance(item, CheckContext) for item in contexts):
            raise FactReasonerError("checker request requires contexts")
        if any(item.stage is not self.stage for item in contexts):
            raise FactReasonerError("checker context stage disagrees with request")
        if len({item.chunk.chunk_id for item in contexts}) != len(contexts):
            raise FactReasonerError("checker request has duplicate chunks")
        object.__setattr__(self, "contexts", contexts)
        if not isinstance(self.fallback_complete, bool):
            raise FactReasonerError("checker fallback_complete flag is invalid")

    @property
    def hypothesis(self) -> str:
        return self.atom.checker_hypothesis


@dataclass(frozen=True)
class CheckerResponse:
    outcome: CheckOutcome
    reason_code: str
    cited_chunk_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome", _enum(CheckOutcome, self.outcome, "checker outcome"))
        _require_code(self.reason_code, "checker response reason_code")
        cited = tuple(self.cited_chunk_ids)
        if len(cited) != len(set(cited)) or any(
            not isinstance(item, str) or not item.startswith("chunk-") for item in cited
        ):
            raise FactReasonerError("checker response cited chunks are invalid")
        if self.outcome in {CheckOutcome.SUPPORT, CheckOutcome.CONTRADICTION} and not cited:
            raise FactReasonerError("support and contradiction require cited evidence")
        if self.outcome is CheckOutcome.UNAVAILABLE and cited:
            raise FactReasonerError("unavailable checker response cannot cite evidence")
        object.__setattr__(self, "cited_chunk_ids", cited)


class FactChecker(Protocol):
    """Injected checker boundary; implementations receive no unfrozen source."""

    checker_id: str
    checker_revision: str

    def check(self, request: CheckRequest) -> CheckerResponse:
        ...


class BatchFactChecker(FactChecker, Protocol):
    """Optional bounded batch extension for exact per-request decisions."""

    def check_many(
        self, requests: Sequence[CheckRequest]
    ) -> tuple[CheckerResponse, ...]:
        ...


def check_request_sha256(request: CheckRequest) -> str:
    """Hash every semantic input visible at the injected checker boundary."""

    if not isinstance(request, CheckRequest):
        raise FactReasonerError("checker request digest requires a CheckRequest")
    request.atom.validate_integrity()
    for context in request.contexts:
        context.chunk.validate_integrity()
    return _digest(
        {
            "request_version": CHECK_REQUEST_VERSION,
            "atom_sha256": request.atom.content_sha256,
            "hypothesis": request.hypothesis,
            "stage": request.stage.value,
            "contexts": [
                {
                    "chunk_id": item.chunk.chunk_id,
                    "chunk_sha256": item.chunk.content_sha256,
                    "retrieval_score": item.retrieval_score,
                }
                for item in request.contexts
            ],
            "fallback_complete": request.fallback_complete,
        }
    )


@dataclass(frozen=True)
class EvidenceCoordinate:
    chunk_id: str
    chunk_sha256: str
    source_id: str
    source_uri: str
    source_revision: str
    source_sha256: str
    char_start: int | None
    char_end: int | None
    json_pointer: str | None
    section_path: tuple[str, ...]
    table_context: str | None
    retrieval_score: float
    cited: bool
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.chunk_id, str) or not self.chunk_id.startswith("chunk-"):
            raise FactReasonerError("evidence coordinate chunk_id is invalid")
        _require_digest(self.chunk_sha256, "evidence chunk digest")
        _require_code(self.source_id, "evidence source_id")
        if not isinstance(self.source_uri, str) or not self.source_uri:
            raise FactReasonerError("evidence source URI is invalid")
        if not isinstance(self.source_revision, str) or not self.source_revision:
            raise FactReasonerError("evidence source revision is invalid")
        _require_digest(self.source_sha256, "evidence source digest")
        span = self.char_start is not None or self.char_end is not None
        pointer = self.json_pointer is not None
        if span == pointer:
            raise FactReasonerError("evidence coordinate kind is ambiguous")
        if span and (
            not isinstance(self.char_start, int)
            or isinstance(self.char_start, bool)
            or not isinstance(self.char_end, int)
            or isinstance(self.char_end, bool)
            or self.char_start < 0
            or self.char_end <= self.char_start
        ):
            raise FactReasonerError("evidence character span is invalid")
        if pointer and (
            not isinstance(self.json_pointer, str) or not self.json_pointer.startswith("/")
        ):
            raise FactReasonerError("evidence JSON pointer is invalid")
        section_path = tuple(self.section_path)
        if any(not isinstance(item, str) or not item for item in section_path):
            raise FactReasonerError("evidence section path is invalid")
        object.__setattr__(self, "section_path", section_path)
        if self.table_context is not None and not isinstance(self.table_context, str):
            raise FactReasonerError("evidence table context is invalid")
        if (
            not isinstance(self.retrieval_score, (int, float))
            or isinstance(self.retrieval_score, bool)
            or not math.isfinite(self.retrieval_score)
            or self.retrieval_score < 0
        ):
            raise FactReasonerError("evidence retrieval score is invalid")
        object.__setattr__(self, "retrieval_score", round(float(self.retrieval_score), 8))
        if not isinstance(self.cited, bool):
            raise FactReasonerError("evidence cited flag is invalid")
        _content_hash(self, self._content_payload(), "evidence coordinate")

    def _content_payload(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "chunk_sha256": self.chunk_sha256,
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "json_pointer": self.json_pointer,
            "section_path": list(self.section_path),
            "table_context": self.table_context,
            "retrieval_score": self.retrieval_score,
            "cited": self.cited,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "coordinate_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "EvidenceCoordinate":
        item = _strict_object(
            value,
            {
                "chunk_id",
                "chunk_sha256",
                "source_id",
                "source_uri",
                "source_revision",
                "source_sha256",
                "char_start",
                "char_end",
                "json_pointer",
                "section_path",
                "table_context",
                "retrieval_score",
                "cited",
                "coordinate_sha256",
            },
            "evidence coordinate",
        )
        coordinate = cls(
            chunk_id=item["chunk_id"],
            chunk_sha256=item["chunk_sha256"],
            source_id=item["source_id"],
            source_uri=item["source_uri"],
            source_revision=item["source_revision"],
            source_sha256=item["source_sha256"],
            char_start=item["char_start"],
            char_end=item["char_end"],
            json_pointer=item["json_pointer"],
            section_path=tuple(
                _array(item["section_path"], "evidence coordinate section_path")
            ),
            table_context=item["table_context"],
            retrieval_score=item["retrieval_score"],
            cited=item["cited"],
        )
        if item["coordinate_sha256"] != coordinate.content_sha256:
            raise FactReasonerError("serialized evidence coordinate digest is inconsistent")
        return coordinate


def _coordinate(context: CheckContext, cited: set[str]) -> EvidenceCoordinate:
    chunk = context.chunk
    return EvidenceCoordinate(
        chunk_id=chunk.chunk_id,
        chunk_sha256=chunk.content_sha256,
        source_id=chunk.source_id,
        source_uri=chunk.source_uri,
        source_revision=chunk.source_revision,
        source_sha256=chunk.source_sha256,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
        json_pointer=chunk.json_pointer,
        section_path=chunk.section_path,
        table_context=chunk.table_context,
        retrieval_score=context.retrieval_score,
        cited=chunk.chunk_id in cited,
    )


@dataclass(frozen=True)
class CheckerAttempt:
    checker_id: str
    checker_revision: str
    stage: CheckStage
    outcome: CheckOutcome
    reason_code: str
    fallback_complete: bool
    evidence: tuple[EvidenceCoordinate, ...]
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        _require_code(self.checker_id, "checker_id")
        if not isinstance(self.checker_revision, str) or not self.checker_revision:
            raise FactReasonerError("checker revision is invalid")
        object.__setattr__(self, "stage", _enum(CheckStage, self.stage, "check stage"))
        object.__setattr__(self, "outcome", _enum(CheckOutcome, self.outcome, "check outcome"))
        _require_code(self.reason_code, "checker attempt reason_code")
        if not isinstance(self.fallback_complete, bool):
            raise FactReasonerError("checker attempt fallback flag is invalid")
        evidence = tuple(self.evidence)
        if not all(isinstance(item, EvidenceCoordinate) for item in evidence):
            raise FactReasonerError("checker attempt evidence must be typed coordinates")
        if len({item.chunk_id for item in evidence}) != len(evidence):
            raise FactReasonerError("checker attempt has duplicate evidence coordinates")
        object.__setattr__(self, "evidence", evidence)
        cited = [item for item in evidence if item.cited]
        if self.outcome in {CheckOutcome.SUPPORT, CheckOutcome.CONTRADICTION} and not cited:
            raise FactReasonerError("informative checker attempt requires cited evidence")
        if self.outcome is CheckOutcome.UNAVAILABLE and cited:
            raise FactReasonerError("unavailable checker attempt cannot cite evidence")
        _content_hash(self, self._content_payload(), "checker attempt")

    def _content_payload(self) -> dict[str, Any]:
        return {
            "checker_id": self.checker_id,
            "checker_revision": self.checker_revision,
            "stage": self.stage.value,
            "outcome": self.outcome.value,
            "reason_code": self.reason_code,
            "fallback_complete": self.fallback_complete,
            "evidence": [item.to_dict() for item in self.evidence],
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "attempt_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "CheckerAttempt":
        item = _strict_object(
            value,
            {
                "checker_id",
                "checker_revision",
                "stage",
                "outcome",
                "reason_code",
                "fallback_complete",
                "evidence",
                "attempt_sha256",
            },
            "checker attempt",
        )
        attempt = cls(
            checker_id=item["checker_id"],
            checker_revision=item["checker_revision"],
            stage=item["stage"],
            outcome=item["outcome"],
            reason_code=item["reason_code"],
            fallback_complete=item["fallback_complete"],
            evidence=tuple(
                EvidenceCoordinate.from_dict(entry)
                for entry in _array(item["evidence"], "checker attempt evidence")
            ),
        )
        if item["attempt_sha256"] != attempt.content_sha256:
            raise FactReasonerError("serialized checker attempt digest is inconsistent")
        return attempt


@dataclass(frozen=True)
class AtomDecision:
    decision_version: str
    atom_id: str
    outcome: CheckOutcome
    field_action: FieldAction
    reason_code: str
    source_limited: bool
    attempts: tuple[CheckerAttempt, ...]
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.decision_version != DECISION_VERSION:
            raise FactReasonerError("unsupported atom decision version")
        if not isinstance(self.atom_id, str) or not self.atom_id.startswith("atom-"):
            raise FactReasonerError("atom decision identifier is invalid")
        object.__setattr__(self, "outcome", _enum(CheckOutcome, self.outcome, "atom outcome"))
        object.__setattr__(
            self,
            "field_action",
            _enum(FieldAction, self.field_action, "field action"),
        )
        _require_code(self.reason_code, "atom decision reason_code")
        if not isinstance(self.source_limited, bool):
            raise FactReasonerError("atom decision source_limited flag is invalid")
        attempts = tuple(self.attempts)
        if not all(isinstance(item, CheckerAttempt) for item in attempts):
            raise FactReasonerError("atom decision attempts must be typed records")
        object.__setattr__(self, "attempts", attempts)
        expected_action = {
            CheckOutcome.SUPPORT: FieldAction.NONE,
            CheckOutcome.CONTRADICTION: FieldAction.REPAIR_OR_WITHHOLD,
            CheckOutcome.NEUTRAL: FieldAction.REPAIR_OR_WITHHOLD,
            CheckOutcome.UNAVAILABLE: FieldAction.COLLECT_OR_WITHHOLD,
        }[self.outcome]
        if self.field_action is not expected_action:
            raise FactReasonerError("atom outcome and field action disagree")
        if attempts and attempts[-1].outcome is not self.outcome:
            raise FactReasonerError("atom decision disagrees with final checker attempt")
        if not attempts and self.outcome is not CheckOutcome.UNAVAILABLE:
            raise FactReasonerError("non-unavailable atom decision requires a checker attempt")
        if len(attempts) > 2:
            raise FactReasonerError("atom decision exceeds the two-tier checker bound")
        if len(attempts) == 2 and (
            attempts[0].outcome is not CheckOutcome.NEUTRAL
            or attempts[1].stage is not CheckStage.FULL_SOURCE_FALLBACK
        ):
            raise FactReasonerError("second checker attempt is not a neutral fallback")
        _content_hash(self, self._content_payload(), "atom decision")

    def _content_payload(self) -> dict[str, Any]:
        return {
            "decision_version": self.decision_version,
            "atom_id": self.atom_id,
            "outcome": self.outcome.value,
            "field_action": self.field_action.value,
            "reason_code": self.reason_code,
            "source_limited": self.source_limited,
            "attempts": [item.to_dict() for item in self.attempts],
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "decision_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "AtomDecision":
        item = _strict_object(
            value,
            {
                "decision_version",
                "atom_id",
                "outcome",
                "field_action",
                "reason_code",
                "source_limited",
                "attempts",
                "decision_sha256",
            },
            "atom decision",
        )
        decision = cls(
            decision_version=item["decision_version"],
            atom_id=item["atom_id"],
            outcome=item["outcome"],
            field_action=item["field_action"],
            reason_code=item["reason_code"],
            source_limited=item["source_limited"],
            attempts=tuple(
                CheckerAttempt.from_dict(entry)
                for entry in _array(item["attempts"], "atom decision attempts")
            ),
        )
        if item["decision_sha256"] != decision.content_sha256:
            raise FactReasonerError("serialized atom decision digest is inconsistent")
        return decision


@dataclass(frozen=True)
class FieldDecision:
    field_path: str
    atom_ids: tuple[str, ...]
    outcomes: tuple[CheckOutcome, ...]
    action: FieldAction
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.field_path, str) or "." not in self.field_path:
            raise FactReasonerError("field decision path is invalid")
        atom_ids = tuple(self.atom_ids)
        outcomes = tuple(_enum(CheckOutcome, item, "field atom outcome") for item in self.outcomes)
        if not atom_ids or len(atom_ids) != len(outcomes):
            raise FactReasonerError("field decision atom/outcome coverage is invalid")
        if any(not isinstance(item, str) or not item.startswith("atom-") for item in atom_ids):
            raise FactReasonerError("field decision atom identifier is invalid")
        if len(atom_ids) != len(set(atom_ids)):
            raise FactReasonerError("field decision has duplicate atom identifiers")
        object.__setattr__(self, "atom_ids", atom_ids)
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(self, "action", _enum(FieldAction, self.action, "field action"))
        expected = FieldAction.NONE
        if any(item in {CheckOutcome.CONTRADICTION, CheckOutcome.NEUTRAL} for item in outcomes):
            expected = FieldAction.REPAIR_OR_WITHHOLD
        elif any(item is CheckOutcome.UNAVAILABLE for item in outcomes):
            expected = FieldAction.COLLECT_OR_WITHHOLD
        if self.action is not expected:
            raise FactReasonerError("field decision outcomes and action disagree")
        _content_hash(self, self._content_payload(), "field decision")

    def _content_payload(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "atom_ids": list(self.atom_ids),
            "outcomes": [item.value for item in self.outcomes],
            "action": self.action.value,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "field_decision_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "FieldDecision":
        item = _strict_object(
            value,
            {"field_path", "atom_ids", "outcomes", "action", "field_decision_sha256"},
            "field decision",
        )
        decision = cls(
            field_path=item["field_path"],
            atom_ids=tuple(_array(item["atom_ids"], "field decision atom_ids")),
            outcomes=tuple(_array(item["outcomes"], "field decision outcomes")),
            action=item["action"],
        )
        if item["field_decision_sha256"] != decision.content_sha256:
            raise FactReasonerError("serialized field decision digest is inconsistent")
        return decision


@dataclass(frozen=True)
class FactReasonerRecord:
    record_version: str
    kernel_version: str
    target: TargetIdentity
    card_sha256: str
    schema_sha256: str
    corpus_sha256: str
    retrieval_version: str
    retrieval_config: RetrievalConfig
    checker_id: str
    checker_revision: str
    source_availability: tuple[SourceAvailability, ...]
    corpus_truncated: bool
    atoms: tuple[FactAtom, ...]
    field_coverage: tuple[FieldCoverage, ...]
    decisions: tuple[AtomDecision, ...]
    field_decisions: tuple[FieldDecision, ...]
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self.record_version != RECORD_VERSION
            or self.kernel_version != FACTREASONER_KERNEL_VERSION
        ):
            raise FactReasonerError("unsupported FactReasoner record version")
        if not isinstance(self.target, TargetIdentity):
            raise FactReasonerError("FactReasoner record target is invalid")
        for value, label in (
            (self.card_sha256, "record card digest"),
            (self.schema_sha256, "record schema digest"),
            (self.corpus_sha256, "record corpus digest"),
        ):
            _require_digest(value, label)
        if self.retrieval_version != RETRIEVAL_VERSION:
            raise FactReasonerError("unsupported retrieval version")
        if not isinstance(self.retrieval_config, RetrievalConfig):
            raise FactReasonerError("record retrieval config is invalid")
        _require_code(self.checker_id, "record checker_id")
        if not isinstance(self.checker_revision, str) or not self.checker_revision:
            raise FactReasonerError("record checker revision is invalid")
        if not isinstance(self.corpus_truncated, bool):
            raise FactReasonerError("record corpus_truncated flag is invalid")
        source_availability = tuple(self.source_availability)
        atoms = tuple(self.atoms)
        coverage = tuple(self.field_coverage)
        decisions = tuple(self.decisions)
        field_decisions = tuple(self.field_decisions)
        object.__setattr__(self, "source_availability", source_availability)
        object.__setattr__(self, "atoms", atoms)
        object.__setattr__(self, "field_coverage", coverage)
        object.__setattr__(self, "decisions", decisions)
        object.__setattr__(self, "field_decisions", field_decisions)
        typed_groups = (
            (source_availability, SourceAvailability, "source availability"),
            (atoms, FactAtom, "atoms"),
            (coverage, FieldCoverage, "field coverage"),
            (decisions, AtomDecision, "decisions"),
            (field_decisions, FieldDecision, "field decisions"),
        )
        for values, record_type, label in typed_groups:
            if not all(isinstance(item, record_type) for item in values):
                raise FactReasonerError(f"record {label} must contain typed records")

        source_ids = [item.source_id for item in source_availability]
        atom_ids = [item.atom_id for item in atoms]
        coverage_paths = [item.field_path for item in coverage]
        decision_ids = [item.atom_id for item in decisions]
        field_paths = [item.field_path for item in field_decisions]
        if len(source_ids) != len(set(source_ids)):
            raise FactReasonerError("record has duplicate source availability")
        if len(atom_ids) != len(set(atom_ids)):
            raise FactReasonerError("record has duplicate atom identifiers")
        if len(coverage_paths) != len(set(coverage_paths)):
            raise FactReasonerError("record has duplicate field coverage")
        if len(decision_ids) != len(set(decision_ids)):
            raise FactReasonerError("record has duplicate atom decisions")
        if decision_ids != atom_ids:
            raise FactReasonerError("record does not contain exactly one decision per atom")
        if any(atom.target != self.target for atom in atoms):
            raise FactReasonerError("record atom target disagrees with record target")
        covered = [atom_id for item in coverage for atom_id in item.atom_ids]
        if Counter(covered) != Counter(atom_ids):
            raise FactReasonerError("record field coverage and atoms diverge")
        checked_coverage = [
            item for item in coverage if item.status is FieldCoverageStatus.CHECKED
        ]
        if field_paths != [item.field_path for item in checked_coverage]:
            raise FactReasonerError("record field decisions do not cover checked fields")
        decision_by_id = {item.atom_id: item for item in decisions}
        for field, field_decision in zip(checked_coverage, field_decisions):
            if field_decision.atom_ids != field.atom_ids:
                raise FactReasonerError("field decision atom coverage is inconsistent")
            expected_outcomes = tuple(
                decision_by_id[item].outcome for item in field.atom_ids
            )
            if field_decision.outcomes != expected_outcomes:
                raise FactReasonerError("field decision outcome coverage is inconsistent")
        for atom in atoms:
            atom.validate_integrity()
        _content_hash(self, self._content_payload(), "FactReasoner record")

    def _content_payload(self) -> dict[str, Any]:
        return {
            "record_version": self.record_version,
            "kernel_version": self.kernel_version,
            "target": self.target.to_dict(),
            "card_sha256": self.card_sha256,
            "schema_sha256": self.schema_sha256,
            "corpus_sha256": self.corpus_sha256,
            "retrieval_version": self.retrieval_version,
            "retrieval_config": self.retrieval_config.to_dict(),
            "checker_id": self.checker_id,
            "checker_revision": self.checker_revision,
            "source_availability": [item.to_dict() for item in self.source_availability],
            "corpus_truncated": self.corpus_truncated,
            "atoms": [item.to_dict() for item in self.atoms],
            "field_coverage": [item.to_dict() for item in self.field_coverage],
            "decisions": [item.to_dict() for item in self.decisions],
            "field_decisions": [item.to_dict() for item in self.field_decisions],
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def validate_integrity(self) -> None:
        if self._content_sha256 != _digest(self._content_payload()):
            raise FactReasonerError("FactReasoner record integrity failed")
        for atom in self.atoms:
            atom.validate_integrity()

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "record_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "FactReasonerRecord":
        item = _strict_object(
            value,
            {
                "record_version",
                "kernel_version",
                "target",
                "card_sha256",
                "schema_sha256",
                "corpus_sha256",
                "retrieval_version",
                "retrieval_config",
                "checker_id",
                "checker_revision",
                "source_availability",
                "corpus_truncated",
                "atoms",
                "field_coverage",
                "decisions",
                "field_decisions",
                "record_sha256",
            },
            "FactReasoner record",
        )
        record = cls(
            record_version=item["record_version"],
            kernel_version=item["kernel_version"],
            target=_target_from_dict(item["target"], "FactReasoner record target"),
            card_sha256=item["card_sha256"],
            schema_sha256=item["schema_sha256"],
            corpus_sha256=item["corpus_sha256"],
            retrieval_version=item["retrieval_version"],
            retrieval_config=RetrievalConfig.from_dict(item["retrieval_config"]),
            checker_id=item["checker_id"],
            checker_revision=item["checker_revision"],
            source_availability=tuple(
                SourceAvailability.from_dict(entry)
                for entry in _array(
                    item["source_availability"], "record source_availability"
                )
            ),
            corpus_truncated=item["corpus_truncated"],
            atoms=tuple(
                FactAtom.from_dict(entry)
                for entry in _array(item["atoms"], "record atoms")
            ),
            field_coverage=tuple(
                FieldCoverage.from_dict(entry)
                for entry in _array(item["field_coverage"], "record field_coverage")
            ),
            decisions=tuple(
                AtomDecision.from_dict(entry)
                for entry in _array(item["decisions"], "record decisions")
            ),
            field_decisions=tuple(
                FieldDecision.from_dict(entry)
                for entry in _array(item["field_decisions"], "record field_decisions")
            ),
        )
        if item["record_sha256"] != record.content_sha256:
            raise FactReasonerError("serialized FactReasoner record digest is inconsistent")
        return record


def _checker_identity(checker: FactChecker) -> tuple[str, str]:
    checker_id = getattr(checker, "checker_id", None)
    checker_revision = getattr(checker, "checker_revision", None)
    _require_code(checker_id, "checker_id")
    if not isinstance(checker_revision, str) or not checker_revision:
        raise FactReasonerError("checker_revision is invalid")
    if not callable(getattr(checker, "check", None)):
        raise FactReasonerError("checker does not implement check(request)")
    return checker_id, checker_revision


def _source_target_matches(target: TargetIdentity, chunk: SourceChunk) -> bool:
    return chunk.source_target == target


def _referent_model_id(referent: str) -> str:
    return referent.rsplit("@", 1)[0] if "@" in referent else referent


def _scope_chunks(atom: FactAtom, chunks: Sequence[SourceChunk]) -> tuple[SourceChunk, ...]:
    if atom.hypothesis.relation is RelationToTarget.EXACT_TARGET:
        return tuple(item for item in chunks if _source_target_matches(atom.target, item))
    referent_model = _referent_model_id(atom.hypothesis.referent)
    return tuple(
        item
        for item in chunks
        if item.source_target is not None
        and item.source_target.model_id in {atom.target.model_id, referent_model}
    )


def _fallback_contexts(
    chunks: Sequence[SourceChunk], config: RetrievalConfig
) -> tuple[tuple[CheckContext, ...], bool]:
    selected = []
    characters = 0
    ordered = sorted(
        chunks,
        key=lambda item: (
            item.source_id,
            item.char_start if item.char_start is not None else -1,
            item.json_pointer or "",
            item.chunk_id,
        ),
    )
    for chunk in ordered:
        if len(selected) >= config.max_fallback_chunks:
            break
        if characters + len(chunk.text) > config.max_fallback_chars:
            break
        selected.append(
            CheckContext(
                chunk=chunk,
                stage=CheckStage.FULL_SOURCE_FALLBACK,
                retrieval_score=0.0,
            )
        )
        characters += len(chunk.text)
    return tuple(selected), len(selected) == len(ordered)


def _invoke_checker(
    checker: FactChecker,
    checker_id: str,
    checker_revision: str,
    request: CheckRequest,
) -> CheckerAttempt:
    try:
        response = checker.check(request)
    except UpstreamFactReasonerUnavailable as exc:
        response = CheckerResponse(
            outcome=CheckOutcome.UNAVAILABLE,
            reason_code=exc.reason_code,
        )
    except (ProviderResponseError, ProviderTerminalAttemptError) as exc:
        if exc.reason_code not in RECOVERABLE_PROVIDER_FAILURE_REASON_CODES:
            raise
        response = CheckerResponse(
            outcome=CheckOutcome.UNAVAILABLE,
            reason_code="checker_unavailable",
        )
    except (ProviderError, LedgerError, TransportUncertainError):
        raise
    except Exception:  # Non-provider checker availability remains typed data.
        response = CheckerResponse(
            outcome=CheckOutcome.UNAVAILABLE,
            reason_code="checker_unavailable",
        )
    if not isinstance(response, CheckerResponse):
        raise FactReasonerError("checker must return a typed CheckerResponse")
    available = {item.chunk.chunk_id for item in request.contexts}
    if not set(response.cited_chunk_ids).issubset(available):
        raise FactReasonerError("checker cited a chunk outside its request")
    cited = set(response.cited_chunk_ids)
    return CheckerAttempt(
        checker_id=checker_id,
        checker_revision=checker_revision,
        stage=request.stage,
        outcome=response.outcome,
        reason_code=response.reason_code,
        fallback_complete=request.fallback_complete,
        evidence=tuple(_coordinate(item, cited) for item in request.contexts),
    )


def _unavailable_response(reason_code: str) -> CheckerResponse:
    return CheckerResponse(
        outcome=CheckOutcome.UNAVAILABLE,
        reason_code=reason_code,
    )


def _response_attempt(
    response: CheckerResponse,
    request: CheckRequest,
    checker_id: str,
    checker_revision: str,
) -> CheckerAttempt:
    if not isinstance(response, CheckerResponse):
        raise FactReasonerError("checker must return typed CheckerResponse records")
    available = {item.chunk.chunk_id for item in request.contexts}
    if not set(response.cited_chunk_ids).issubset(available):
        raise FactReasonerError("checker cited a chunk outside its request")
    cited = set(response.cited_chunk_ids)
    return CheckerAttempt(
        checker_id=checker_id,
        checker_revision=checker_revision,
        stage=request.stage,
        outcome=response.outcome,
        reason_code=response.reason_code,
        fallback_complete=request.fallback_complete,
        evidence=tuple(_coordinate(item, cited) for item in request.contexts),
    )


def _invoke_checker_many(
    checker: FactChecker,
    checker_id: str,
    checker_revision: str,
    requests: Sequence[CheckRequest],
) -> tuple[CheckerAttempt, ...]:
    """Invoke a checker in deterministic groups of at most 64 requests."""

    ordered = tuple(requests)
    if not all(isinstance(item, CheckRequest) for item in ordered):
        raise FactReasonerError("checker batch requires typed CheckRequest records")
    if not ordered:
        return ()
    batch_method = getattr(checker, "check_many", None)
    if not callable(batch_method):
        return tuple(
            _invoke_checker(
                checker,
                checker_id,
                checker_revision,
                request,
            )
            for request in ordered
        )

    attempts: list[CheckerAttempt] = []
    for start in range(0, len(ordered), MAX_FACT_CHECKS_PER_BATCH):
        batch = ordered[start : start + MAX_FACT_CHECKS_PER_BATCH]
        try:
            responses = batch_method(batch)
        except UpstreamFactReasonerUnavailable as exc:
            responses = tuple(_unavailable_response(exc.reason_code) for _ in batch)
        except (ProviderResponseError, ProviderTerminalAttemptError) as exc:
            if exc.reason_code not in RECOVERABLE_PROVIDER_FAILURE_REASON_CODES:
                raise
            responses = tuple(_unavailable_response("checker_unavailable") for _ in batch)
        except (ProviderError, LedgerError, TransportUncertainError):
            raise
        except Exception:
            responses = tuple(_unavailable_response("checker_unavailable") for _ in batch)
        if (
            not isinstance(responses, Sequence)
            or isinstance(responses, (str, bytes, bytearray))
            or len(responses) != len(batch)
        ):
            raise FactReasonerError(
                "batch checker must return one typed response per request"
            )
        attempts.extend(
            _response_attempt(response, request, checker_id, checker_revision)
            for request, response in zip(batch, responses)
        )
    return tuple(attempts)


def _unavailable_decision(
    atom: FactAtom,
    reason_code: str,
    *,
    source_limited: bool = True,
) -> AtomDecision:
    return AtomDecision(
        decision_version=DECISION_VERSION,
        atom_id=atom.atom_id,
        outcome=CheckOutcome.UNAVAILABLE,
        field_action=FieldAction.COLLECT_OR_WITHHOLD,
        reason_code=reason_code,
        source_limited=source_limited,
        attempts=(),
    )


def _decision_from_attempts(
    atom: FactAtom,
    attempts: Sequence[CheckerAttempt],
    *,
    globally_limited: bool,
) -> AtomDecision:
    values = tuple(attempts)
    if not values:
        raise FactReasonerError("checked atom requires at least one checker attempt")
    final = values[-1]
    action = {
        CheckOutcome.SUPPORT: FieldAction.NONE,
        CheckOutcome.CONTRADICTION: FieldAction.REPAIR_OR_WITHHOLD,
        CheckOutcome.NEUTRAL: FieldAction.REPAIR_OR_WITHHOLD,
        CheckOutcome.UNAVAILABLE: FieldAction.COLLECT_OR_WITHHOLD,
    }[final.outcome]
    reason = final.reason_code
    if final.outcome is CheckOutcome.NEUTRAL:
        reason = "neutral_after_bounded_fallback"
    return AtomDecision(
        decision_version=DECISION_VERSION,
        atom_id=atom.atom_id,
        outcome=final.outcome,
        field_action=action,
        reason_code=reason,
        source_limited=globally_limited or not final.fallback_complete,
        attempts=values,
    )


def _batched_atom_decisions(
    atoms: Sequence[FactAtom],
    corpus: ChunkCorpus,
    checker: FactChecker,
    checker_id: str,
    checker_revision: str,
    config: RetrievalConfig,
) -> tuple[AtomDecision, ...]:
    """Run one complete primary wave, then a neutral-only fallback wave."""

    globally_limited = corpus.truncated or any(
        item.status != "loaded" for item in corpus.sources
    )
    decisions: list[AtomDecision | None] = [None] * len(atoms)
    scoped_by_index: dict[int, tuple[SourceChunk, ...]] = {}
    primary_indices: list[int] = []
    primary_requests: list[CheckRequest] = []
    for index, atom in enumerate(atoms):
        scoped = _scope_chunks(atom, corpus.chunks)
        if not scoped:
            decisions[index] = _unavailable_decision(
                atom, "no_in_scope_frozen_source"
            )
            continue
        if sum(len(item.text.strip()) for item in scoped) < config.min_source_chars:
            decisions[index] = _unavailable_decision(atom, "thin_frozen_source")
            continue
        scoped_by_index[index] = scoped
        primary_contexts = retrieve_chunks(atom, scoped, top_k=config.top_k)
        primary_indices.append(index)
        primary_requests.append(
            CheckRequest(
                atom=atom,
                stage=CheckStage.RETRIEVAL,
                contexts=primary_contexts,
                fallback_complete=len(primary_contexts) == len(scoped),
            )
        )

    primary_attempts = _invoke_checker_many(
        checker,
        checker_id,
        checker_revision,
        primary_requests,
    )
    attempts_by_index: dict[int, list[CheckerAttempt]] = {}
    fallback_indices: list[int] = []
    fallback_requests: list[CheckRequest] = []
    for index, primary in zip(primary_indices, primary_attempts):
        attempts_by_index[index] = [primary]
        if primary.outcome is not CheckOutcome.NEUTRAL:
            decisions[index] = _decision_from_attempts(
                atoms[index],
                (primary,),
                globally_limited=globally_limited,
            )
            continue
        fallback_contexts, fallback_complete = _fallback_contexts(
            scoped_by_index[index], config
        )
        if not fallback_contexts:
            decisions[index] = _unavailable_decision(
                atoms[index], "fallback_source_unavailable"
            )
            continue
        fallback_indices.append(index)
        fallback_requests.append(
            CheckRequest(
                atom=atoms[index],
                stage=CheckStage.FULL_SOURCE_FALLBACK,
                contexts=fallback_contexts,
                fallback_complete=fallback_complete,
            )
        )

    fallback_attempts = _invoke_checker_many(
        checker,
        checker_id,
        checker_revision,
        fallback_requests,
    )
    for index, fallback in zip(fallback_indices, fallback_attempts):
        attempts_by_index[index].append(fallback)
        decisions[index] = _decision_from_attempts(
            atoms[index],
            attempts_by_index[index],
            globally_limited=globally_limited,
        )
    if any(item is None for item in decisions):
        raise FactReasonerError("batched checker left an atom without a decision")
    return tuple(item for item in decisions if item is not None)


def _field_decisions(
    coverage: Sequence[FieldCoverage],
    decisions: Sequence[AtomDecision],
) -> tuple[FieldDecision, ...]:
    by_id = {item.atom_id: item for item in decisions}
    output = []
    for field in coverage:
        if field.status is FieldCoverageStatus.ABSENCE:
            continue
        outcomes = tuple(by_id[item].outcome for item in field.atom_ids)
        action = FieldAction.NONE
        if any(
            item in {CheckOutcome.CONTRADICTION, CheckOutcome.NEUTRAL}
            for item in outcomes
        ):
            action = FieldAction.REPAIR_OR_WITHHOLD
        elif any(item is CheckOutcome.UNAVAILABLE for item in outcomes):
            action = FieldAction.COLLECT_OR_WITHHOLD
        output.append(
            FieldDecision(
                field_path=field.field_path,
                atom_ids=field.atom_ids,
                outcomes=outcomes,
                action=action,
            )
        )
    return tuple(output)


def run_factreasoner(
    card: Mapping[str, Any],
    schema: Mapping[str, Any],
    target: TargetIdentity,
    sources: Sequence[SourceDocument],
    checker: FactChecker,
    *,
    field_hypotheses: Mapping[str, ReferentHypothesis] | None = None,
    source_availability: Sequence[SourceAvailability | Any] = (),
    config: RetrievalConfig | None = None,
) -> FactReasonerRecord:
    """Run complete bounded validation and emit one immutable replay record."""

    config = config or RetrievalConfig()
    checker_id, checker_revision = _checker_identity(checker)
    atomization = atomize_card(
        card,
        schema,
        target,
        field_hypotheses=field_hypotheses,
    )
    corpus = build_source_chunks(
        sources,
        config=config,
        source_availability=source_availability,
    )
    decisions = _batched_atom_decisions(
        atomization.atoms,
        corpus,
        checker,
        checker_id,
        checker_revision,
        config,
    )
    return FactReasonerRecord(
        record_version=RECORD_VERSION,
        kernel_version=FACTREASONER_KERNEL_VERSION,
        target=target,
        card_sha256=atomization.card_sha256,
        schema_sha256=atomization.schema_sha256,
        corpus_sha256=corpus.corpus_sha256,
        retrieval_version=RETRIEVAL_VERSION,
        retrieval_config=config,
        checker_id=checker_id,
        checker_revision=checker_revision,
        source_availability=corpus.sources,
        corpus_truncated=corpus.truncated,
        atoms=atomization.atoms,
        field_coverage=atomization.field_coverage,
        decisions=decisions,
        field_decisions=_field_decisions(atomization.field_coverage, decisions),
    )


def replay_factreasoner(
    record: FactReasonerRecord,
    card: Mapping[str, Any],
    schema: Mapping[str, Any],
    target: TargetIdentity,
    sources: Sequence[SourceDocument],
    checker: FactChecker,
    *,
    field_hypotheses: Mapping[str, ReferentHypothesis] | None = None,
    source_availability: Sequence[SourceAvailability | Any] = (),
) -> FactReasonerRecord:
    """Re-run a record with its closed config and reject any divergence."""

    if not isinstance(record, FactReasonerRecord):
        raise FactReasonerReplayError("replay requires a typed FactReasoner record")
    record.validate_integrity()
    replayed = run_factreasoner(
        card,
        schema,
        target,
        sources,
        checker,
        field_hypotheses=field_hypotheses,
        source_availability=source_availability,
        config=record.retrieval_config,
    )
    if replayed.to_dict() != record.to_dict():
        raise FactReasonerReplayError("FactReasoner replay diverged from the record")
    return replayed


@dataclass(frozen=True)
class IBMFactReasonerInference:
    """Privacy-safe trace for one upstream FR1 marginal computation."""

    request_sha256: str
    upstream_revision: str
    adapter_version: str
    inference_method: str
    nli_checker_id: str
    nli_checker_revision: str
    relation_probability: float
    atom_false_probability: float
    atom_true_probability: float
    outcome: CheckOutcome
    cited_chunk_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_digest(self.request_sha256, "upstream inference request digest")
        if self.upstream_revision != IBM_FACTREASONER_UPSTREAM_REVISION:
            raise FactReasonerError("upstream inference revision is not pinned")
        if self.adapter_version != IBM_FACTREASONER_ADAPTER_VERSION:
            raise FactReasonerError("upstream inference adapter version is invalid")
        if self.inference_method != IBM_FACTREASONER_INFERENCE_METHOD:
            raise FactReasonerError("upstream inference method is invalid")
        _require_code(self.nli_checker_id, "upstream inference NLI checker_id")
        if not isinstance(self.nli_checker_revision, str) or not self.nli_checker_revision:
            raise FactReasonerError("upstream inference NLI checker revision is invalid")
        for value, label in (
            (self.relation_probability, "relation probability"),
            (self.atom_false_probability, "atom false probability"),
            (self.atom_true_probability, "atom true probability"),
        ):
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or not 0.0 <= value <= 1.0
            ):
                raise FactReasonerError(f"upstream inference {label} is invalid")
        if self.relation_probability != IBM_FACTREASONER_RELATION_PROBABILITY:
            raise FactReasonerError("upstream inference relation probability drifted")
        if not math.isclose(
            self.atom_false_probability + self.atom_true_probability,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-12,
        ):
            raise FactReasonerError("upstream inference marginal is not normalized")
        object.__setattr__(
            self, "outcome", _enum(CheckOutcome, self.outcome, "upstream inference outcome")
        )
        cited = tuple(self.cited_chunk_ids)
        if len(cited) != len(set(cited)) or any(
            not isinstance(item, str) or not item.startswith("chunk-") for item in cited
        ):
            raise FactReasonerError("upstream inference cited chunks are invalid")
        object.__setattr__(self, "cited_chunk_ids", cited)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_sha256": self.request_sha256,
            "upstream_revision": self.upstream_revision,
            "adapter_version": self.adapter_version,
            "inference_method": self.inference_method,
            "nli_checker_id": self.nli_checker_id,
            "nli_checker_revision": self.nli_checker_revision,
            "relation_probability": self.relation_probability,
            "atom_marginal": [
                self.atom_false_probability,
                self.atom_true_probability,
            ],
            "outcome": self.outcome.value,
            "cited_chunk_ids": list(self.cited_chunk_ids),
        }


@dataclass(frozen=True)
class _IBMFactReasonerRuntime:
    fact_reasoner: Any
    fact_graph: Any
    node: Any
    edge: Any
    variable_elimination: Any
    prior_prob_atom: float
    prior_prob_context: float


class IBMFactReasonerAdapter:
    """Run IBM FactReasoner's pinned FR1 graph around an exact NLI checker.

    Every existing ``CheckRequest`` already represents one atom and only its
    bounded, frozen contexts, which is precisely FR1's atom-to-own-contexts
    topology.  The injected checker supplies the categorical NLI decision and
    exact cited chunk IDs.  Cited support/contradiction contexts become upstream
    ``FactGraph`` edges with the declared fixed probability above; neutral
    decisions create no edge, matching upstream's neutral filtering.

    The pinned upstream implementation builds its own ``MarkovNetwork``.  This
    adapter queries and normalizes that network with pgmpy's exact
    ``VariableElimination`` instead of invoking the separately compiled Merlin
    executable.  Construction is lazy and performs no model or network call.
    """

    checker_id = "ibm/factreasoner-fr1"
    checker_revision = IBM_FACTREASONER_UPSTREAM_REVISION
    adapter_version = IBM_FACTREASONER_ADAPTER_VERSION
    inference_method = IBM_FACTREASONER_INFERENCE_METHOD
    relation_probability = IBM_FACTREASONER_RELATION_PROBABILITY

    def __init__(self, nli_checker: FactChecker | None = None) -> None:
        self._nli_checker = nli_checker
        self._nli_identity = (
            _checker_identity(nli_checker) if nli_checker is not None else None
        )
        self._upstream: _IBMFactReasonerRuntime | None = None
        self._inferences: dict[str, IBMFactReasonerInference] = {}

    @staticmethod
    def _module_exists(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except (AttributeError, ImportError, ValueError):
            return False

    @staticmethod
    def _normalized_repository_url(value: Any) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        normalized = value.strip().rstrip("/").casefold()
        return normalized[:-4] if normalized.endswith(".git") else normalized

    @classmethod
    def _installed_upstream_revision(cls) -> str | None:
        try:
            distribution = importlib_metadata.distribution("fact_reasoner")
            raw = distribution.read_text("direct_url.json")
            value = json.loads(raw) if raw is not None else None
        except (
            importlib_metadata.PackageNotFoundError,
            json.JSONDecodeError,
            OSError,
            TypeError,
            ValueError,
        ):
            return None
        if not isinstance(value, Mapping):
            return None
        expected_url = cls._normalized_repository_url(IBM_FACTREASONER_UPSTREAM_URL)
        actual_url = cls._normalized_repository_url(value.get("url"))
        vcs = value.get("vcs_info")
        if actual_url != expected_url or not isinstance(vcs, Mapping):
            return None
        revision = vcs.get("commit_id")
        return revision if isinstance(revision, str) else None

    @classmethod
    def installation_status(cls) -> str:
        """Return a stable, non-importing status for orchestration admission."""

        if not cls._module_exists("fact_reasoner"):
            return "ibm_factreasoner_dependency_unavailable"
        if not cls._module_exists("pgmpy"):
            return "ibm_factreasoner_pgmpy_unavailable"
        if cls._installed_upstream_revision() != IBM_FACTREASONER_UPSTREAM_REVISION:
            return "ibm_factreasoner_revision_unverified"
        return "ibm_factreasoner_pinned_dependency_available"

    @classmethod
    def is_installed(cls) -> bool:
        return (
            cls.installation_status()
            == "ibm_factreasoner_pinned_dependency_available"
        )

    def _load_upstream(self) -> _IBMFactReasonerRuntime:
        if self._upstream is not None:
            return self._upstream
        status = self.installation_status()
        if status != "ibm_factreasoner_pinned_dependency_available":
            raise UpstreamFactReasonerUnavailable(
                "the exact pinned IBM FactReasoner and pgmpy dependencies are unavailable",
                reason_code=status,
            )
        try:
            with _suppress_upstream_factreasoner_output():
                assessor = importlib.import_module("fact_reasoner.assessor")
                graph = importlib.import_module("fact_reasoner.fact_graph")
                base = importlib.import_module("fact_reasoner.core.base")
                inference = importlib.import_module("pgmpy.inference")
                runtime = _IBMFactReasonerRuntime(
                    fact_reasoner=getattr(assessor, "FactReasoner"),
                    fact_graph=getattr(graph, "FactGraph"),
                    node=getattr(graph, "Node"),
                    edge=getattr(graph, "Edge"),
                    variable_elimination=getattr(inference, "VariableElimination"),
                    prior_prob_atom=float(getattr(base, "PRIOR_PROB_ATOM")),
                    prior_prob_context=float(getattr(base, "PRIOR_PROB_CONTEXT")),
                )
        except Exception as exc:
            raise UpstreamFactReasonerUnavailable(
                "the pinned IBM FactReasoner API could not be imported",
                reason_code="ibm_factreasoner_import_unavailable",
            ) from exc
        callables = (
            runtime.fact_reasoner,
            runtime.fact_graph,
            runtime.node,
            runtime.edge,
            runtime.variable_elimination,
        )
        if not all(callable(item) for item in callables):
            raise UpstreamFactReasonerUnavailable(
                "the pinned IBM FactReasoner API has an invalid shape",
                reason_code="ibm_factreasoner_api_invalid",
            )
        self._upstream = runtime
        return runtime

    def validate_installation(self) -> None:
        """Import and validate the exact optional runtime without running NLI."""

        self._load_upstream()

    @staticmethod
    def _request_sha256(request: CheckRequest) -> str:
        return check_request_sha256(request)

    def inference_for(self, request: CheckRequest) -> IBMFactReasonerInference | None:
        """Return the recorded marginal for a completed request, if one exists."""

        if not isinstance(request, CheckRequest):
            raise FactReasonerError("upstream inference lookup requires a CheckRequest")
        return self._inferences.get(self._request_sha256(request))

    @property
    def inferences(self) -> tuple[IBMFactReasonerInference, ...]:
        return tuple(self._inferences[key] for key in sorted(self._inferences))

    def provenance(self) -> dict[str, Any]:
        nli_checker_id, nli_checker_revision = self._nli_identity or (None, None)
        return {
            "adapter_version": self.adapter_version,
            "upstream_url": IBM_FACTREASONER_UPSTREAM_URL,
            "upstream_revision": self.checker_revision,
            "configuration": "FR1",
            "inference_method": self.inference_method,
            "relation_probability": self.relation_probability,
            "nli_checker_id": nli_checker_id,
            "nli_checker_revision": nli_checker_revision,
        }

    def _marginal(
        self,
        request: CheckRequest,
        response: CheckerResponse,
        runtime: _IBMFactReasonerRuntime,
    ) -> tuple[float, float]:
        graph = runtime.fact_graph()
        atom_id = request.atom.atom_id
        graph.add_node(runtime.node(atom_id, "atom", runtime.prior_prob_atom))
        cited = set(response.cited_chunk_ids)
        relation_type = {
            CheckOutcome.SUPPORT: "entailment",
            CheckOutcome.CONTRADICTION: "contradiction",
        }.get(response.outcome)
        for context in request.contexts:
            chunk_id = context.chunk.chunk_id
            graph.add_node(runtime.node(chunk_id, "context", runtime.prior_prob_context))
            if relation_type is not None and chunk_id in cited:
                graph.add_edge(
                    runtime.edge(
                        chunk_id,
                        atom_id,
                        relation_type,
                        self.relation_probability,
                        "context_atom",
                    )
                )

        # Upstream currently requires a Merlin path at construction time even
        # when loading a FactGraph. This explicit non-path sentinel is never
        # executed: inference below uses pgmpy over the upstream-built network.
        with _suppress_upstream_factreasoner_output():
            reasoner = runtime.fact_reasoner(
                nli_extractor=None,
                merlin_path="pgmpy-variable-elimination-not-an-executable",
                use_priors=True,
            )
            reasoner.from_fact_graph(graph)
            query = runtime.variable_elimination(reasoner.markov_network).query(
                variables=[atom_id],
                show_progress=False,
            )
        raw_values = getattr(query, "values", None)
        if raw_values is None:
            raise UpstreamFactReasonerUnavailable(
                "pgmpy did not return an atom marginal",
                reason_code="ibm_factreasoner_inference_unavailable",
            )
        if hasattr(raw_values, "reshape"):
            values = tuple(float(item) for item in raw_values.reshape(-1).tolist())
        else:
            try:
                values = tuple(float(item) for item in raw_values)
            except (TypeError, ValueError) as exc:
                raise UpstreamFactReasonerUnavailable(
                    "pgmpy returned an invalid atom marginal",
                    reason_code="ibm_factreasoner_inference_unavailable",
                ) from exc
        if (
            len(values) != 2
            or any(not math.isfinite(item) or item < 0.0 for item in values)
            or sum(values) <= 0.0
        ):
            raise UpstreamFactReasonerUnavailable(
                "pgmpy returned an invalid atom marginal",
                reason_code="ibm_factreasoner_inference_unavailable",
            )
        total = sum(values)
        return values[0] / total, values[1] / total

    def check_many(
        self, requests: Sequence[CheckRequest]
    ) -> tuple[CheckerResponse, ...]:
        ordered = tuple(requests)
        if (
            not ordered
            or len(ordered) > MAX_FACT_CHECKS_PER_BATCH
            or not all(isinstance(item, CheckRequest) for item in ordered)
        ):
            raise FactReasonerError(
                "IBM FactReasoner batch requires between 1 and 64 CheckRequests"
            )
        runtime = self._load_upstream()
        if self._nli_checker is None or self._nli_identity is None:
            raise UpstreamFactReasonerUnavailable(
                "IBM FactReasoner requires an injected exact NLI checker",
                reason_code="ibm_factreasoner_nli_checker_unavailable",
            )
        batch_method = getattr(self._nli_checker, "check_many", None)
        if callable(batch_method):
            nli_responses = batch_method(ordered)
        else:
            nli_responses = tuple(self._nli_checker.check(item) for item in ordered)
        if (
            not isinstance(nli_responses, Sequence)
            or isinstance(nli_responses, (str, bytes, bytearray))
            or len(nli_responses) != len(ordered)
            or not all(isinstance(item, CheckerResponse) for item in nli_responses)
        ):
            raise FactReasonerError(
                "the injected NLI checker returned invalid batch responses"
            )

        nli_checker_id, nli_checker_revision = self._nli_identity
        output: list[CheckerResponse] = []
        pending_inferences: dict[str, IBMFactReasonerInference] = {}
        for request, response in zip(ordered, nli_responses):
            available = {item.chunk.chunk_id for item in request.contexts}
            if not set(response.cited_chunk_ids).issubset(available):
                raise FactReasonerError(
                    "the injected NLI checker cited an unavailable chunk"
                )
            if response.outcome is CheckOutcome.UNAVAILABLE:
                output.append(response)
                continue
            try:
                atom_false, atom_true = self._marginal(request, response, runtime)
            except UpstreamFactReasonerUnavailable:
                raise
            except Exception as exc:
                raise UpstreamFactReasonerUnavailable(
                    "the pinned IBM FactReasoner graph could not be queried",
                    reason_code="ibm_factreasoner_inference_unavailable",
                ) from exc
            if math.isclose(atom_true, atom_false, rel_tol=0.0, abs_tol=1e-12):
                outcome = CheckOutcome.NEUTRAL
            elif atom_true > atom_false:
                outcome = CheckOutcome.SUPPORT
            else:
                outcome = CheckOutcome.CONTRADICTION
            if outcome is not response.outcome:
                raise UpstreamFactReasonerUnavailable(
                    "the upstream FR1 marginal disagrees with the categorical NLI relation",
                    reason_code="ibm_factreasoner_marginal_inconsistent",
                )
            request_sha256 = self._request_sha256(request)
            pending_inferences[request_sha256] = IBMFactReasonerInference(
                request_sha256=request_sha256,
                upstream_revision=self.checker_revision,
                adapter_version=self.adapter_version,
                inference_method=self.inference_method,
                nli_checker_id=nli_checker_id,
                nli_checker_revision=nli_checker_revision,
                relation_probability=self.relation_probability,
                atom_false_probability=atom_false,
                atom_true_probability=atom_true,
                outcome=outcome,
                cited_chunk_ids=response.cited_chunk_ids,
            )
            output.append(
                CheckerResponse(
                    outcome=outcome,
                    reason_code={
                        CheckOutcome.SUPPORT: "upstream_fr1_support",
                        CheckOutcome.CONTRADICTION: "upstream_fr1_contradiction",
                        CheckOutcome.NEUTRAL: "upstream_fr1_neutral",
                    }[outcome],
                    cited_chunk_ids=response.cited_chunk_ids,
                )
            )
        self._inferences.update(pending_inferences)
        return tuple(output)

    def check(self, request: CheckRequest) -> CheckerResponse:
        if not isinstance(request, CheckRequest):
            raise FactReasonerError("IBM FactReasoner adapter requires a CheckRequest")
        return self.check_many((request,))[0]
