"""Frozen collection of publisher-declared primary sources.

This module is the deliberately small network boundary after
``official_discovery``.  Discovery records links; this layer is the first place
where bytes can become evidence.  Only publisher-declared, policy-verified
HTTPS candidates are fetched.  Secondary, scholarly, and EvalEval material is
kept discovery-only until another collection proves its authority and exact
relation.

The on-disk bundle is content addressed and replayed without a network.  Its
manifest contains portable URLs and logical object paths, never collector-local
paths, credentials, response headers, or source bodies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence
from urllib.parse import parse_qsl, unquote, urlsplit

from .official_discovery import (
    DiscoveryProvenance,
    DiscoveryStatus,
    OfficialDiscoveryManifest,
    OfficialSourceKind,
    OfficialSourcePolicy,
)
from .models import RelationToTarget
from .source_bundle import TargetIdentity


OFFICIAL_BUNDLE_VERSION = "official-source-bundle/v1"
EVALEVAL_JOIN_SHAPE = "evaleval-exact-model-join/v1"
DEFAULT_MAX_SOURCES = 32
DEFAULT_MAX_SOURCE_BYTES = 8_000_000
DEFAULT_MAX_TOTAL_BYTES = 32_000_000
DEFAULT_MAX_REDIRECTS = 4

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_ID_RE = re.compile(r"^primary_src_[0-9a-f]{24}$")
_RELATION_ID_RE = re.compile(r"^source_relation_[0-9a-f]{24}$")
_EVAL_RELATION_ID_RE = re.compile(r"^evaluation_relation_[0-9a-f]{24}$")
_BUNDLE_ID_RE = re.compile(r"^official_bundle_[0-9a-f]{32}$")
_DISCOVERY_RECORD_ID_RE = re.compile(r"^official_source_[0-9a-f]{24}$")
_HF_SOURCE_ID_RE = re.compile(r"^src_[0-9a-f]{24}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MODEL_ID_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$"
)


class OfficialSourceError(ValueError):
    """Base class for official-source collection and strict replay errors."""


class OfficialSourceIntegrityError(OfficialSourceError):
    """A frozen official-source bundle is stale, unsafe, or inconsistent."""


class OfficialFetchStatus(str, Enum):
    OK = "ok"
    MISSING = "missing"
    GATED = "gated"
    BLOCKED = "blocked"
    UNAVAILABLE = "unavailable"


class OfficialSourceStatus(str, Enum):
    COLLECTED = "collected"
    MISSING = "missing"
    GATED = "gated"
    BLOCKED = "blocked"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"
    DISCOVERY_ONLY = "discovery_only"


class SourceAuthority(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SCHOLARLY_DISCOVERY = "scholarly_discovery"
    EVALEVAL_DISCOVERY = "evaleval_discovery"


class RelationState(str, Enum):
    DECLARED = "declared"
    CONFLICTING = "conflicting"
    UNRESOLVED = "unresolved"


class EvalEvalJoinTier(str, Enum):
    EXACT = "exact"
    CASE_INSENSITIVE = "case_insensitive"
    NONE = "none"


class EvalEvalAvailability(str, Enum):
    MATCHED = "matched"
    NO_MATCH = "no_match"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class OfficialRemoteObject:
    """One bounded adapter response with an explicit redirect trace.

    For an ``ok`` response, ``redirect_chain`` contains the requested URL as
    its first item and the final response URL as its last item.  This lets the
    evidence boundary re-check every redirect rather than trusting an HTTP
    client's final URL.
    """

    status: OfficialFetchStatus
    content: bytes | None = None
    final_url: str | None = None
    redirect_chain: tuple[str, ...] = ()
    media_type: str | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", OfficialFetchStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise OfficialSourceError("official remote status is invalid") from exc
        object.__setattr__(self, "redirect_chain", tuple(self.redirect_chain))
        if self.status is OfficialFetchStatus.OK:
            if not isinstance(self.content, bytes):
                raise OfficialSourceError("an ok official response requires bytes")
            if not isinstance(self.final_url, str):
                raise OfficialSourceError("an ok official response requires a final URL")
            if not self.redirect_chain:
                raise OfficialSourceError("an ok official response requires a redirect trace")
            if self.redirect_chain[-1] != self.final_url:
                raise OfficialSourceError("official final URL must close the redirect trace")
            if not isinstance(self.media_type, str) or not _valid_media_type(self.media_type):
                raise OfficialSourceError("an ok official response requires a media type")
            if self.reason_code is not None:
                raise OfficialSourceError("an ok official response cannot have a reason code")
        else:
            if self.content is not None:
                raise OfficialSourceError("a non-ok official response cannot contain bytes")
            if self.final_url is not None or self.redirect_chain or self.media_type is not None:
                raise OfficialSourceError(
                    "a non-ok official response cannot claim a response resource"
                )
            _validate_reason(self.reason_code, required=True)


class OfficialSourceAdapter(Protocol):
    """Injected network boundary.  Implementations must enforce byte limits."""

    def fetch(
        self, url: str, *, max_bytes: int, max_redirects: int
    ) -> OfficialRemoteObject:
        """Fetch one HTTPS resource and return a classified bounded response."""


@dataclass(frozen=True)
class OfficialCollectionLimits:
    max_sources: int = DEFAULT_MAX_SOURCES
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_redirects: int = DEFAULT_MAX_REDIRECTS

    def __post_init__(self) -> None:
        for name in ("max_sources", "max_source_bytes", "max_total_bytes", "max_redirects"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise OfficialSourceError(f"{name} must be a positive integer")
        if not 1 <= self.max_sources <= 64:
            raise OfficialSourceError("max_sources must be between 1 and 64")
        if self.max_source_bytes > self.max_total_bytes:
            raise OfficialSourceError("max_source_bytes cannot exceed max_total_bytes")
        if self.max_redirects > 10:
            raise OfficialSourceError("max_redirects cannot exceed 10")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_sources": self.max_sources,
            "max_source_bytes": self.max_source_bytes,
            "max_total_bytes": self.max_total_bytes,
            "max_redirects": self.max_redirects,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "OfficialCollectionLimits":
        item = _strict_object(
            value,
            {"max_sources", "max_source_bytes", "max_total_bytes", "max_redirects"},
            "official collection limits",
        )
        return cls(**item)


@dataclass(frozen=True)
class RelationAssertion:
    """One explicit publisher relation assertion for a discovered source."""

    candidate_record_id: str
    subject_model_id: str
    relation_to_target: RelationToTarget
    declaring_source_id: str
    declaration_locator: str

    def __post_init__(self) -> None:
        if not _DISCOVERY_RECORD_ID_RE.fullmatch(self.candidate_record_id):
            raise OfficialSourceError("relation candidate_record_id is invalid")
        _validate_modelish_id(self.subject_model_id)
        try:
            object.__setattr__(
                self, "relation_to_target", RelationToTarget(self.relation_to_target)
            )
        except (TypeError, ValueError) as exc:
            raise OfficialSourceError("relation_to_target is invalid") from exc
        if not _HF_SOURCE_ID_RE.fullmatch(self.declaring_source_id):
            raise OfficialSourceError("relation declaring_source_id is invalid")
        _validate_locator(self.declaration_locator)


@dataclass(frozen=True)
class DiscoveryHint:
    """A non-authoritative link supplied by secondary or scholarly discovery."""

    kind: OfficialSourceKind
    url: str
    authority: SourceAuthority
    reason_code: str

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "kind", OfficialSourceKind(self.kind))
            object.__setattr__(self, "authority", SourceAuthority(self.authority))
        except (TypeError, ValueError) as exc:
            raise OfficialSourceError("discovery hint classification is invalid") from exc
        if self.authority not in {
            SourceAuthority.SECONDARY,
            SourceAuthority.SCHOLARLY_DISCOVERY,
            SourceAuthority.EVALEVAL_DISCOVERY,
        }:
            raise OfficialSourceError("a discovery hint cannot claim primary authority")
        _validate_https_url(self.url)
        _validate_reason(self.reason_code, required=True)


@dataclass(frozen=True)
class ContentPin:
    candidate_record_id: str
    expected_sha256: str

    def __post_init__(self) -> None:
        if not _DISCOVERY_RECORD_ID_RE.fullmatch(self.candidate_record_id):
            raise OfficialSourceError("content pin candidate_record_id is invalid")
        if not _SHA256_RE.fullmatch(self.expected_sha256):
            raise OfficialSourceError("content pin SHA-256 is invalid")


@dataclass(frozen=True)
class CollectedOfficialSource:
    source_id: str
    candidate_record_id: str | None
    kind: OfficialSourceKind
    authority: SourceAuthority
    status: OfficialSourceStatus
    requested_url: str | None
    final_url: str | None
    redirect_chain: tuple[str, ...]
    declaring_source_id: str | None
    declaration_locator: str
    media_type: str | None
    object_path: str | None
    sha256: str | None
    expected_sha256: str | None
    byte_size: int | None
    reason_code: str
    evidence_eligible: bool

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "kind", OfficialSourceKind(self.kind))
            object.__setattr__(self, "authority", SourceAuthority(self.authority))
            object.__setattr__(self, "status", OfficialSourceStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise OfficialSourceIntegrityError("official source classification is invalid") from exc
        object.__setattr__(self, "redirect_chain", tuple(self.redirect_chain))
        if not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise OfficialSourceIntegrityError("official source_id is invalid")
        if self.candidate_record_id is not None and not _DISCOVERY_RECORD_ID_RE.fullmatch(
            self.candidate_record_id
        ):
            raise OfficialSourceIntegrityError("official candidate_record_id is invalid")
        if self.declaring_source_id is not None and not _HF_SOURCE_ID_RE.fullmatch(
            self.declaring_source_id
        ):
            raise OfficialSourceIntegrityError("official declaring source is invalid")
        _validate_locator(self.declaration_locator)
        _validate_reason(self.reason_code, required=True)
        if self.expected_sha256 is not None and not _SHA256_RE.fullmatch(
            self.expected_sha256
        ):
            raise OfficialSourceIntegrityError("official expected digest is invalid")

        stored = self.object_path is not None
        if stored:
            if not isinstance(self.sha256, str) or not _SHA256_RE.fullmatch(self.sha256):
                raise OfficialSourceIntegrityError("stored official source requires a digest")
            if self.object_path != _object_path(self.sha256):
                raise OfficialSourceIntegrityError("official object path is not content addressed")
            if isinstance(self.byte_size, bool) or not isinstance(self.byte_size, int) \
                    or self.byte_size < 0:
                raise OfficialSourceIntegrityError("stored official source requires a byte size")
            if not isinstance(self.final_url, str) or not self.redirect_chain:
                raise OfficialSourceIntegrityError("stored official source requires redirect provenance")
            if self.redirect_chain[0] != self.requested_url \
                    or self.redirect_chain[-1] != self.final_url:
                raise OfficialSourceIntegrityError("official redirect trace is not closed")
            if not isinstance(self.media_type, str) or not _valid_media_type(self.media_type):
                raise OfficialSourceIntegrityError("stored official media type is invalid")
            if self.status not in {
                OfficialSourceStatus.COLLECTED,
                OfficialSourceStatus.CONFLICTING,
            }:
                raise OfficialSourceIntegrityError("only collected/conflicting sources store bytes")
        elif any(
            value is not None
            for value in (self.final_url, self.media_type, self.sha256, self.byte_size)
        ) or self.redirect_chain:
            raise OfficialSourceIntegrityError("unstored official source has response metadata")

        if self.requested_url is not None:
            _validate_https_url(self.requested_url)
        if self.final_url is not None:
            _validate_https_url(self.final_url)
        for url in self.redirect_chain:
            _validate_https_url(url)

        eligible = (
            self.status is OfficialSourceStatus.COLLECTED
            and self.authority is SourceAuthority.PRIMARY
            and stored
            and self.reason_code == "verified_primary_source"
        )
        if self.evidence_eligible is not eligible:
            raise OfficialSourceIntegrityError("official evidence eligibility is inconsistent")
        expected_id = _source_id(
            candidate_record_id=self.candidate_record_id,
            kind=self.kind,
            authority=self.authority,
            status=self.status,
            requested_url=self.requested_url,
            final_url=self.final_url,
            declaring_source_id=self.declaring_source_id,
            declaration_locator=self.declaration_locator,
            sha256=self.sha256,
            expected_sha256=self.expected_sha256,
            reason_code=self.reason_code,
        )
        if self.source_id != expected_id:
            raise OfficialSourceIntegrityError("official source_id does not match content")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "candidate_record_id": self.candidate_record_id,
            "kind": self.kind.value,
            "authority": self.authority.value,
            "status": self.status.value,
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "redirect_chain": list(self.redirect_chain),
            "declaring_source_id": self.declaring_source_id,
            "declaration_locator": self.declaration_locator,
            "media_type": self.media_type,
            "object_path": self.object_path,
            "sha256": self.sha256,
            "expected_sha256": self.expected_sha256,
            "byte_size": self.byte_size,
            "reason_code": self.reason_code,
            "evidence_eligible": self.evidence_eligible,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "CollectedOfficialSource":
        keys = {
            "source_id", "candidate_record_id", "kind", "authority", "status",
            "requested_url", "final_url", "redirect_chain", "declaring_source_id",
            "declaration_locator", "media_type", "object_path", "sha256",
            "expected_sha256", "byte_size", "reason_code", "evidence_eligible",
        }
        item = _strict_object(value, keys, "collected official source")
        if not isinstance(item["redirect_chain"], list) or not all(
            isinstance(entry, str) for entry in item["redirect_chain"]
        ):
            raise OfficialSourceIntegrityError("redirect_chain must be a string list")
        item["redirect_chain"] = tuple(item["redirect_chain"])
        return cls(**item)


@dataclass(frozen=True)
class SourceRelation:
    relation_id: str
    source_id: str
    subject_model_id: str
    target_model_id: str
    relation_to_target: RelationToTarget
    state: RelationState
    declaring_source_id: str
    declaration_locator: str

    def __post_init__(self) -> None:
        if not _RELATION_ID_RE.fullmatch(self.relation_id):
            raise OfficialSourceIntegrityError("source relation_id is invalid")
        if not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise OfficialSourceIntegrityError("source relation source_id is invalid")
        _validate_modelish_id(self.subject_model_id)
        _validate_model_id(self.target_model_id)
        try:
            object.__setattr__(
                self, "relation_to_target", RelationToTarget(self.relation_to_target)
            )
            object.__setattr__(self, "state", RelationState(self.state))
        except (TypeError, ValueError) as exc:
            raise OfficialSourceIntegrityError("source relation classification is invalid") from exc
        if not _HF_SOURCE_ID_RE.fullmatch(self.declaring_source_id):
            raise OfficialSourceIntegrityError("source relation declaration source is invalid")
        _validate_locator(self.declaration_locator)
        if self.relation_to_target is RelationToTarget.EXACT_TARGET \
                and self.subject_model_id != self.target_model_id:
            raise OfficialSourceIntegrityError("exact-target relation subject must be target")
        if self.state is RelationState.UNRESOLVED \
                and self.relation_to_target is not RelationToTarget.UNKNOWN:
            raise OfficialSourceIntegrityError("only unknown relations can be unresolved")
        expected = _relation_id(
            self.source_id,
            self.subject_model_id,
            self.target_model_id,
            self.relation_to_target,
            self.state,
            self.declaring_source_id,
            self.declaration_locator,
        )
        if self.relation_id != expected:
            raise OfficialSourceIntegrityError("source relation_id does not match content")

    def to_dict(self) -> dict[str, str]:
        return {
            "relation_id": self.relation_id,
            "source_id": self.source_id,
            "subject_model_id": self.subject_model_id,
            "target_model_id": self.target_model_id,
            "relation_to_target": self.relation_to_target.value,
            "state": self.state.value,
            "declaring_source_id": self.declaring_source_id,
            "declaration_locator": self.declaration_locator,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "SourceRelation":
        keys = {
            "relation_id", "source_id", "subject_model_id", "target_model_id",
            "relation_to_target", "state", "declaring_source_id", "declaration_locator",
        }
        return cls(**_strict_object(value, keys, "source relation"))


@dataclass(frozen=True)
class EvalEvalEvaluationRow:
    """The exact seven-field row emitted by the documented EvalEval join."""

    evaluation_name: Any
    metric_name: Any
    metric_id: Any
    score: Any
    hf_repo: Any
    evaluation_result_id: Any
    source_file: str

    def __post_init__(self) -> None:
        _validate_portable_path(self.source_file, "EvalEval source_file")
        for name in (
            "evaluation_name", "metric_name", "metric_id", "hf_repo",
            "evaluation_result_id",
        ):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or len(value) > 1024 or not _portable_text(value)
            ):
                raise OfficialSourceIntegrityError(f"EvalEval {name} is invalid")
        if isinstance(self.score, (dict, list)):
            _canonical_json(self.score)
        elif self.score is not None and not isinstance(self.score, (str, int, float, bool)):
            raise OfficialSourceIntegrityError("EvalEval score is not JSON-compatible")
        _canonical_json(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluation_name": self.evaluation_name,
            "metric_name": self.metric_name,
            "metric_id": self.metric_id,
            "score": self.score,
            "hf_repo": self.hf_repo,
            "evaluation_result_id": self.evaluation_result_id,
            "source_file": self.source_file,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "EvalEvalEvaluationRow":
        keys = {
            "evaluation_name", "metric_name", "metric_id", "score", "hf_repo",
            "evaluation_result_id", "source_file",
        }
        return cls(**_strict_object(value, keys, "EvalEval evaluation row"))


@dataclass(frozen=True)
class EvalEvalJoinRecord:
    """Closed shape returned by the exact-id EvalEval datastore join.

    This intentionally preserves the documented five top-level keys.  Record
    paths must already be sanitized to datastore-relative POSIX paths before
    crossing this boundary.
    """

    model_id: str
    tier: EvalEvalJoinTier
    matched_id: str | None
    benchmarks: tuple[tuple[str, tuple[EvalEvalEvaluationRow, ...]], ...]
    record_files: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_model_id(self.model_id)
        try:
            object.__setattr__(self, "tier", EvalEvalJoinTier(self.tier))
        except (TypeError, ValueError) as exc:
            raise OfficialSourceIntegrityError("EvalEval join tier is invalid") from exc
        normalized_benchmarks = tuple(
            (name, tuple(rows)) for name, rows in self.benchmarks
        )
        object.__setattr__(self, "benchmarks", normalized_benchmarks)
        object.__setattr__(self, "record_files", tuple(self.record_files))
        names = [item[0] for item in normalized_benchmarks]
        if names != sorted(set(names)):
            raise OfficialSourceIntegrityError("EvalEval benchmarks must be sorted and unique")
        for name, rows in normalized_benchmarks:
            if not name or len(name) > 256 or not _portable_text(name):
                raise OfficialSourceIntegrityError("EvalEval benchmark name is invalid")
            if not all(isinstance(row, EvalEvalEvaluationRow) for row in rows):
                raise OfficialSourceIntegrityError("EvalEval benchmark rows are invalid")
        if self.record_files != tuple(sorted(set(self.record_files))):
            raise OfficialSourceIntegrityError("EvalEval record_files must be sorted and unique")
        for path in self.record_files:
            _validate_portable_path(path, "EvalEval record file")
        row_paths = {
            row.source_file for _, rows in normalized_benchmarks for row in rows
        }
        if not row_paths.issubset(set(self.record_files)):
            raise OfficialSourceIntegrityError("EvalEval row references an unlisted record file")
        if self.tier is EvalEvalJoinTier.NONE:
            if self.matched_id is not None or normalized_benchmarks or self.record_files:
                raise OfficialSourceIntegrityError("an unmatched EvalEval join must be empty")
        else:
            if not isinstance(self.matched_id, str):
                raise OfficialSourceIntegrityError("a matched EvalEval join requires matched_id")
            _validate_model_id(self.matched_id)
            if self.tier is EvalEvalJoinTier.EXACT and self.matched_id != self.model_id:
                raise OfficialSourceIntegrityError("exact EvalEval join changed model id")
            if self.tier is EvalEvalJoinTier.CASE_INSENSITIVE and (
                self.matched_id == self.model_id
                or self.matched_id.casefold() != self.model_id.casefold()
            ):
                raise OfficialSourceIntegrityError("case-insensitive EvalEval join is inconsistent")

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "tier": self.tier.value,
            "matched_id": self.matched_id,
            "benchmarks": {
                name: [row.to_dict() for row in rows]
                for name, rows in self.benchmarks
            },
            "record_files": list(self.record_files),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "EvalEvalJoinRecord":
        item = _strict_object(
            value,
            {"model_id", "tier", "matched_id", "benchmarks", "record_files"},
            "EvalEval join record",
        )
        if not isinstance(item["benchmarks"], dict):
            raise OfficialSourceIntegrityError("EvalEval benchmarks must be an object")
        if not isinstance(item["record_files"], list) or not all(
            isinstance(entry, str) for entry in item["record_files"]
        ):
            raise OfficialSourceIntegrityError("EvalEval record_files must be a string list")
        benchmarks = []
        for name, rows in item["benchmarks"].items():
            if not isinstance(name, str) or not isinstance(rows, list):
                raise OfficialSourceIntegrityError("EvalEval benchmark entry is malformed")
            benchmarks.append(
                (name, tuple(EvalEvalEvaluationRow.from_dict(row) for row in rows))
            )
        return cls(
            model_id=item["model_id"], tier=item["tier"], matched_id=item["matched_id"],
            benchmarks=tuple(benchmarks), record_files=tuple(item["record_files"]),
        )


@dataclass(frozen=True)
class EvalEvalEnvelope:
    availability: EvalEvalAvailability
    reason_code: str
    join_shape: str
    join: EvalEvalJoinRecord | None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "availability", EvalEvalAvailability(self.availability))
        except (TypeError, ValueError) as exc:
            raise OfficialSourceIntegrityError("EvalEval availability is invalid") from exc
        _validate_reason(self.reason_code, required=True)
        if self.join_shape != EVALEVAL_JOIN_SHAPE:
            raise OfficialSourceIntegrityError("EvalEval join shape is unsupported")
        if self.availability is EvalEvalAvailability.UNAVAILABLE:
            if self.join is not None:
                raise OfficialSourceIntegrityError("unavailable EvalEval cannot contain a join")
        elif not isinstance(self.join, EvalEvalJoinRecord):
            raise OfficialSourceIntegrityError("available EvalEval requires a join")
        elif self.availability is EvalEvalAvailability.NO_MATCH:
            if self.join.tier is not EvalEvalJoinTier.NONE:
                raise OfficialSourceIntegrityError("EvalEval no_match requires tier none")
        elif self.join.tier is EvalEvalJoinTier.NONE:
            raise OfficialSourceIntegrityError("EvalEval matched cannot use tier none")

    def to_dict(self) -> dict[str, Any]:
        return {
            "availability": self.availability.value,
            "reason_code": self.reason_code,
            "join_shape": self.join_shape,
            "join": None if self.join is None else self.join.to_dict(),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "EvalEvalEnvelope":
        item = _strict_object(
            value, {"availability", "reason_code", "join_shape", "join"},
            "EvalEval envelope",
        )
        join = None if item["join"] is None else EvalEvalJoinRecord.from_dict(item["join"])
        return cls(
            availability=item["availability"], reason_code=item["reason_code"],
            join_shape=item["join_shape"], join=join,
        )


@dataclass(frozen=True)
class EvaluationRecordRelation:
    relation_id: str
    evaluation_result_id: str | None
    source_file: str
    benchmark: str
    claimed_model_id: str | None
    target_model_id: str
    relation_to_target: RelationToTarget
    evidence_eligible: bool = False

    def __post_init__(self) -> None:
        if not _EVAL_RELATION_ID_RE.fullmatch(self.relation_id):
            raise OfficialSourceIntegrityError("evaluation relation_id is invalid")
        for name in ("evaluation_result_id", "claimed_model_id"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not value or len(value) > 1024
                or not _portable_text(value)
            ):
                raise OfficialSourceIntegrityError(f"evaluation relation {name} is invalid")
        _validate_portable_path(self.source_file, "evaluation relation source_file")
        if not self.benchmark or len(self.benchmark) > 256 or not _portable_text(self.benchmark):
            raise OfficialSourceIntegrityError("evaluation relation benchmark is invalid")
        _validate_model_id(self.target_model_id)
        try:
            object.__setattr__(
                self, "relation_to_target", RelationToTarget(self.relation_to_target)
            )
        except (TypeError, ValueError) as exc:
            raise OfficialSourceIntegrityError("evaluation relation classification is invalid") from exc
        if self.relation_to_target is RelationToTarget.EXACT_TARGET \
                and self.claimed_model_id != self.target_model_id:
            raise OfficialSourceIntegrityError("exact evaluation relation must name target")
        if self.evidence_eligible is not False:
            raise OfficialSourceIntegrityError(
                "EvalEval evaluation records remain discovery-only until separately verified"
            )
        expected = _evaluation_relation_id(
            self.evaluation_result_id, self.source_file, self.benchmark,
            self.claimed_model_id, self.target_model_id, self.relation_to_target,
        )
        if self.relation_id != expected:
            raise OfficialSourceIntegrityError("evaluation relation_id does not match content")

    def to_dict(self) -> dict[str, Any]:
        return {
            "relation_id": self.relation_id,
            "evaluation_result_id": self.evaluation_result_id,
            "source_file": self.source_file,
            "benchmark": self.benchmark,
            "claimed_model_id": self.claimed_model_id,
            "target_model_id": self.target_model_id,
            "relation_to_target": self.relation_to_target.value,
            "evidence_eligible": self.evidence_eligible,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "EvaluationRecordRelation":
        keys = {
            "relation_id", "evaluation_result_id", "source_file", "benchmark",
            "claimed_model_id", "target_model_id", "relation_to_target",
            "evidence_eligible",
        }
        return cls(**_strict_object(value, keys, "evaluation record relation"))


@dataclass(frozen=True)
class OfficialSourceManifest:
    manifest_version: str
    bundle_id: str
    target: TargetIdentity
    source_bundle_id: str
    discovery_id: str
    policy: OfficialSourcePolicy
    limits: OfficialCollectionLimits
    sources: tuple[CollectedOfficialSource, ...]
    relations: tuple[SourceRelation, ...]
    evaleval: EvalEvalEnvelope
    evaluation_relations: tuple[EvaluationRecordRelation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "relations", tuple(self.relations))
        object.__setattr__(self, "evaluation_relations", tuple(self.evaluation_relations))
        if self.manifest_version != OFFICIAL_BUNDLE_VERSION:
            raise OfficialSourceIntegrityError("official manifest version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise OfficialSourceIntegrityError("official manifest target is invalid")
        if not re.fullmatch(r"hf_bundle_[0-9a-f]{32}", self.source_bundle_id):
            raise OfficialSourceIntegrityError("official source bundle id is invalid")
        if not re.fullmatch(r"official_discovery_[0-9a-f]{32}", self.discovery_id):
            raise OfficialSourceIntegrityError("official discovery id is invalid")
        if not isinstance(self.policy, OfficialSourcePolicy) \
                or not isinstance(self.limits, OfficialCollectionLimits):
            raise OfficialSourceIntegrityError("official manifest policy/limits are invalid")
        if not isinstance(self.evaleval, EvalEvalEnvelope):
            raise OfficialSourceIntegrityError("official manifest EvalEval envelope is invalid")
        if not all(isinstance(item, CollectedOfficialSource) for item in self.sources):
            raise OfficialSourceIntegrityError("official manifest sources are invalid")
        if not all(isinstance(item, SourceRelation) for item in self.relations):
            raise OfficialSourceIntegrityError("official manifest relations are invalid")
        if not all(
            isinstance(item, EvaluationRecordRelation) for item in self.evaluation_relations
        ):
            raise OfficialSourceIntegrityError("evaluation relations are invalid")
        if len(self.sources) > self.limits.max_sources:
            raise OfficialSourceIntegrityError("official manifest exceeds source limit")
        source_ids = [item.source_id for item in self.sources]
        if source_ids != sorted(set(source_ids)):
            raise OfficialSourceIntegrityError("official sources must be sorted and unique")
        relation_ids = [item.relation_id for item in self.relations]
        if relation_ids != sorted(set(relation_ids)):
            raise OfficialSourceIntegrityError("official relations must be sorted and unique")
        eval_ids = [item.relation_id for item in self.evaluation_relations]
        if eval_ids != sorted(set(eval_ids)):
            raise OfficialSourceIntegrityError("evaluation relations must be sorted and unique")
        known_sources = set(source_ids)
        for relation in self.relations:
            if relation.source_id not in known_sources:
                raise OfficialSourceIntegrityError("relation references an unknown official source")
            if relation.target_model_id != self.target.model_id:
                raise OfficialSourceIntegrityError("relation target drifts from official target")
        stored_total = sum(item.byte_size or 0 for item in self.sources)
        if stored_total > self.limits.max_total_bytes:
            raise OfficialSourceIntegrityError("official manifest exceeds total byte limit")
        for source in self.sources:
            if source.byte_size is not None and source.byte_size > self.limits.max_source_bytes:
                raise OfficialSourceIntegrityError("official source exceeds per-source limit")
        expected_id = _bundle_id(
            target=self.target,
            source_bundle_id=self.source_bundle_id,
            discovery_id=self.discovery_id,
            policy=self.policy,
            limits=self.limits,
            sources=self.sources,
            relations=self.relations,
            evaleval=self.evaleval,
            evaluation_relations=self.evaluation_relations,
        )
        if not _BUNDLE_ID_RE.fullmatch(self.bundle_id) or self.bundle_id != expected_id:
            raise OfficialSourceIntegrityError("official bundle_id does not match manifest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "bundle_id": self.bundle_id,
            "target": self.target.to_dict(),
            "source_bundle_id": self.source_bundle_id,
            "discovery_id": self.discovery_id,
            "policy": self.policy.to_dict(),
            "limits": self.limits.to_dict(),
            "sources": [item.to_dict() for item in self.sources],
            "relations": [item.to_dict() for item in self.relations],
            "evaleval": self.evaleval.to_dict(),
            "evaluation_relations": [item.to_dict() for item in self.evaluation_relations],
        }

    @classmethod
    def from_dict(cls, value: Any) -> "OfficialSourceManifest":
        keys = {
            "manifest_version", "bundle_id", "target", "source_bundle_id",
            "discovery_id", "policy", "limits", "sources", "relations",
            "evaleval", "evaluation_relations",
        }
        item = _strict_object(value, keys, "official source manifest")
        for name in ("sources", "relations", "evaluation_relations"):
            if not isinstance(item[name], list):
                raise OfficialSourceIntegrityError(f"official manifest {name} must be a list")
        return cls(
            manifest_version=item["manifest_version"], bundle_id=item["bundle_id"],
            target=TargetIdentity.from_dict(item["target"]),
            source_bundle_id=item["source_bundle_id"], discovery_id=item["discovery_id"],
            policy=OfficialSourcePolicy.from_dict(item["policy"]),
            limits=OfficialCollectionLimits.from_dict(item["limits"]),
            sources=tuple(CollectedOfficialSource.from_dict(v) for v in item["sources"]),
            relations=tuple(SourceRelation.from_dict(v) for v in item["relations"]),
            evaleval=EvalEvalEnvelope.from_dict(item["evaleval"]),
            evaluation_relations=tuple(
                EvaluationRecordRelation.from_dict(v)
                for v in item["evaluation_relations"]
            ),
        )


@dataclass(frozen=True)
class ReplayedOfficialSource:
    record: CollectedOfficialSource
    content: bytes | None


@dataclass(frozen=True)
class ReplayedOfficialSourceBundle:
    manifest: OfficialSourceManifest
    sources: tuple[ReplayedOfficialSource, ...]

    @property
    def contents(self) -> Mapping[str, bytes]:
        return MappingProxyType(
            {
                item.record.source_id: item.content
                for item in self.sources
                if item.content is not None
            }
        )


def collect_official_sources(
    discovery: OfficialDiscoveryManifest,
    destination: str | os.PathLike[str],
    adapter: OfficialSourceAdapter,
    *,
    relation_assertions: Sequence[RelationAssertion] = (),
    discovery_hints: Sequence[DiscoveryHint] = (),
    content_pins: Sequence[ContentPin] = (),
    evaleval_join: EvalEvalJoinRecord | None = None,
    evaleval_unavailable_reason: str = "not_provided",
    max_sources: int = DEFAULT_MAX_SOURCES,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    max_redirects: int = DEFAULT_MAX_REDIRECTS,
) -> OfficialSourceManifest:
    """Collect verified primary bytes and atomically publish a frozen bundle."""

    if not isinstance(discovery, OfficialDiscoveryManifest):
        raise OfficialSourceError("discovery must be an OfficialDiscoveryManifest")
    destination_path = Path(destination)
    if destination_path.exists() or destination_path.is_symlink():
        raise FileExistsError(f"official bundle destination already exists: {destination_path}")
    limits = OfficialCollectionLimits(
        max_sources=max_sources,
        max_source_bytes=max_source_bytes,
        max_total_bytes=max_total_bytes,
        max_redirects=max_redirects,
    )
    assertions = _index_assertions(discovery, relation_assertions)
    pins = _index_pins(discovery, content_pins)
    if len(discovery.records) + len(discovery_hints) > limits.max_sources:
        raise OfficialSourceError("official source candidates exceed max_sources")

    sources: list[CollectedOfficialSource] = []
    pending_relations: list[tuple[CollectedOfficialSource, tuple[RelationAssertion, ...]]] = []
    objects: dict[str, bytes] = {}
    total_bytes = 0

    for candidate in discovery.records:
        explicit = assertions.get(candidate.record_id, ())
        pin = pins.get(candidate.record_id)
        if candidate.status is DiscoveryStatus.DISCOVERED:
            source, data = _fetch_candidate(
                discovery, candidate, adapter, explicit, pin, limits, total_bytes
            )
            if data is not None:
                objects[source.object_path or ""] = data
                total_bytes += len(data)
        else:
            source = _nonfetch_candidate(candidate, pin)
        sources.append(source)
        pending_relations.append((source, explicit))

    for index, hint in enumerate(discovery_hints):
        source = _hint_source(hint, index)
        sources.append(source)

    ordered_sources = tuple(sorted(sources, key=lambda item: item.source_id))
    relations: list[SourceRelation] = []
    for source, explicit in pending_relations:
        if source.declaring_source_id is None:
            continue
        relations.extend(
            _source_relations(discovery.target, source, explicit)
        )
    ordered_relations = tuple(sorted(relations, key=lambda item: item.relation_id))

    evaleval = _evaleval_envelope(
        discovery.target, evaleval_join, evaleval_unavailable_reason
    )
    evaluation_relations = tuple(
        sorted(_evaluation_relations(discovery.target, evaleval), key=lambda item: item.relation_id)
    )
    bundle_id = _bundle_id(
        target=discovery.target,
        source_bundle_id=discovery.source_bundle_id,
        discovery_id=discovery.discovery_id,
        policy=discovery.policy,
        limits=limits,
        sources=ordered_sources,
        relations=ordered_relations,
        evaleval=evaleval,
        evaluation_relations=evaluation_relations,
    )
    manifest = OfficialSourceManifest(
        manifest_version=OFFICIAL_BUNDLE_VERSION,
        bundle_id=bundle_id,
        target=discovery.target,
        source_bundle_id=discovery.source_bundle_id,
        discovery_id=discovery.discovery_id,
        policy=discovery.policy,
        limits=limits,
        sources=ordered_sources,
        relations=ordered_relations,
        evaleval=evaleval,
        evaluation_relations=evaluation_relations,
    )
    _atomic_write_bundle(destination_path, manifest, objects)
    return manifest


def replay_official_sources(
    bundle_dir: str | os.PathLike[str],
    *,
    expected_target: TargetIdentity | None = None,
    expected_discovery_id: str | None = None,
) -> ReplayedOfficialSourceBundle:
    """Replay a frozen bundle after strict JSON, file-set, and hash checks."""

    root = Path(bundle_dir)
    if root.is_symlink() or not root.is_dir():
        raise OfficialSourceIntegrityError("official bundle path must be a real directory")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise OfficialSourceIntegrityError("official bundle manifest is missing or unsafe")
    raw = manifest_path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, OfficialSourceError):
        raise OfficialSourceIntegrityError(
            "official manifest is not strict UTF-8 JSON"
        ) from None
    if raw != _canonical_json(value):
        raise OfficialSourceIntegrityError("official manifest is stale or non-canonical")
    manifest = OfficialSourceManifest.from_dict(value)
    if expected_target is not None and manifest.target != expected_target:
        raise OfficialSourceIntegrityError("official manifest target differs from expected target")
    if expected_discovery_id is not None and manifest.discovery_id != expected_discovery_id:
        raise OfficialSourceIntegrityError("official manifest references another discovery")

    expected_files = {"manifest.json"}
    expected_files.update(
        source.object_path for source in manifest.sources if source.object_path is not None
    )
    actual_files: set[str] = set()
    for entry in root.rglob("*"):
        if entry.is_symlink():
            raise OfficialSourceIntegrityError("official bundle contains a symbolic link")
        if entry.is_file():
            relative = entry.relative_to(root).as_posix()
            _validate_portable_path(relative, "official bundle path")
            actual_files.add(relative)
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        unexpected = sorted(actual_files - expected_files)
        raise OfficialSourceIntegrityError(
            f"official bundle file set is stale (missing={missing}, unexpected={unexpected})"
        )

    content_by_object: dict[str, bytes] = {}
    for object_path in sorted(expected_files - {"manifest.json"}):
        path = root.joinpath(*PurePosixPath(object_path).parts)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if object_path != _object_path(digest):
            raise OfficialSourceIntegrityError("official source bytes do not match address")
        content_by_object[object_path] = data
    replayed = []
    for source in manifest.sources:
        data = None
        if source.object_path is not None:
            data = content_by_object[source.object_path]
            if hashlib.sha256(data).hexdigest() != source.sha256 \
                    or len(data) != source.byte_size:
                raise OfficialSourceIntegrityError("official source hash/size does not replay")
        replayed.append(ReplayedOfficialSource(record=source, content=data))
    return ReplayedOfficialSourceBundle(manifest=manifest, sources=tuple(replayed))


def load_evaleval_join(value: Any) -> EvalEvalJoinRecord:
    """Load the exact documented EvalEval join shape from an in-memory object."""

    return EvalEvalJoinRecord.from_dict(value)


def _fetch_candidate(
    discovery: OfficialDiscoveryManifest,
    candidate: Any,
    adapter: OfficialSourceAdapter,
    assertions: tuple[RelationAssertion, ...],
    pin: ContentPin | None,
    limits: OfficialCollectionLimits,
    total_bytes: int,
) -> tuple[CollectedOfficialSource, bytes | None]:
    requested = candidate.normalized_url
    assert isinstance(requested, str)
    reason = _verify_policy_url(candidate.kind, requested, discovery.policy)
    if reason is not None:
        return _build_source(
            candidate_record_id=candidate.record_id, kind=candidate.kind,
            authority=SourceAuthority.PRIMARY, status=OfficialSourceStatus.BLOCKED,
            requested_url=requested, declaring_source_id=candidate.declaring_source_id,
            declaration_locator=candidate.declaration_locator,
            expected_sha256=None if pin is None else pin.expected_sha256,
            reason_code="policy_revalidation_failed", evidence_eligible=False,
        ), None
    if total_bytes >= limits.max_total_bytes:
        return _build_source(
            candidate_record_id=candidate.record_id, kind=candidate.kind,
            authority=SourceAuthority.PRIMARY, status=OfficialSourceStatus.BLOCKED,
            requested_url=requested, declaring_source_id=candidate.declaring_source_id,
            declaration_locator=candidate.declaration_locator,
            expected_sha256=None if pin is None else pin.expected_sha256,
            reason_code="total_size_limit", evidence_eligible=False,
        ), None
    remaining = min(limits.max_source_bytes, limits.max_total_bytes - total_bytes)
    try:
        response = adapter.fetch(
            requested, max_bytes=remaining, max_redirects=limits.max_redirects
        )
    except Exception:
        response = OfficialRemoteObject(
            OfficialFetchStatus.UNAVAILABLE, reason_code="adapter_failure"
        )
    if not isinstance(response, OfficialRemoteObject):
        raise OfficialSourceError("official adapter returned an invalid response")
    if response.status is not OfficialFetchStatus.OK:
        mapped = {
            OfficialFetchStatus.MISSING: OfficialSourceStatus.MISSING,
            OfficialFetchStatus.GATED: OfficialSourceStatus.GATED,
            OfficialFetchStatus.BLOCKED: OfficialSourceStatus.BLOCKED,
            OfficialFetchStatus.UNAVAILABLE: OfficialSourceStatus.UNAVAILABLE,
        }[response.status]
        return _build_source(
            candidate_record_id=candidate.record_id, kind=candidate.kind,
            authority=SourceAuthority.PRIMARY, status=mapped, requested_url=requested,
            declaring_source_id=candidate.declaring_source_id,
            declaration_locator=candidate.declaration_locator,
            expected_sha256=None if pin is None else pin.expected_sha256,
            reason_code=response.reason_code or "unavailable", evidence_eligible=False,
        ), None
    assert response.content is not None and response.final_url is not None
    if response.redirect_chain[0] != requested:
        return _blocked_redirect(candidate, pin, "redirect_origin_mismatch"), None
    if len(response.redirect_chain) - 1 > limits.max_redirects:
        return _blocked_redirect(candidate, pin, "redirect_limit"), None
    for url in response.redirect_chain:
        redirect_reason = _verify_policy_url(candidate.kind, url, discovery.policy)
        if redirect_reason is not None:
            return _blocked_redirect(candidate, pin, "redirect_policy_violation"), None
    if len(response.content) > remaining:
        return _build_source(
            candidate_record_id=candidate.record_id, kind=candidate.kind,
            authority=SourceAuthority.PRIMARY, status=OfficialSourceStatus.BLOCKED,
            requested_url=requested, declaring_source_id=candidate.declaring_source_id,
            declaration_locator=candidate.declaration_locator,
            expected_sha256=None if pin is None else pin.expected_sha256,
            reason_code="size_limit", evidence_eligible=False,
        ), None
    digest = hashlib.sha256(response.content).hexdigest()
    unique_assertions = {
        (item.subject_model_id, item.relation_to_target) for item in assertions
    }
    conflicting_relation = len(unique_assertions) > 1
    unresolved_relation = any(
        relation is RelationToTarget.UNKNOWN for _, relation in unique_assertions
    )
    drift = pin is not None and pin.expected_sha256 != digest
    status = (
        OfficialSourceStatus.CONFLICTING
        if drift or conflicting_relation or unresolved_relation
        else OfficialSourceStatus.COLLECTED
    )
    reason_code = (
        "source_drift" if drift else
        "conflicting_official_declarations" if conflicting_relation else
        "relation_unresolved" if unresolved_relation else
        "verified_primary_source"
    )
    eligible = status is OfficialSourceStatus.COLLECTED
    return _build_source(
        candidate_record_id=candidate.record_id, kind=candidate.kind,
        authority=SourceAuthority.PRIMARY, status=status, requested_url=requested,
        final_url=response.final_url, redirect_chain=response.redirect_chain,
        declaring_source_id=candidate.declaring_source_id,
        declaration_locator=candidate.declaration_locator,
        media_type=response.media_type, sha256=digest,
        expected_sha256=None if pin is None else pin.expected_sha256,
        byte_size=len(response.content), reason_code=reason_code,
        evidence_eligible=eligible,
    ), response.content


def _blocked_redirect(candidate: Any, pin: ContentPin | None, reason: str):
    return _build_source(
        candidate_record_id=candidate.record_id, kind=candidate.kind,
        authority=SourceAuthority.PRIMARY, status=OfficialSourceStatus.BLOCKED,
        requested_url=candidate.normalized_url,
        declaring_source_id=candidate.declaring_source_id,
        declaration_locator=candidate.declaration_locator,
        expected_sha256=None if pin is None else pin.expected_sha256,
        reason_code=reason, evidence_eligible=False,
    )


def _nonfetch_candidate(candidate: Any, pin: ContentPin | None) -> CollectedOfficialSource:
    if candidate.provenance is DiscoveryProvenance.SECONDARY_HINT:
        authority = SourceAuthority.SECONDARY
        status = OfficialSourceStatus.DISCOVERY_ONLY
        reason = "secondary_hint_only"
    elif candidate.status is DiscoveryStatus.UNAVAILABLE:
        authority = SourceAuthority.PRIMARY
        status = (
            OfficialSourceStatus.MISSING
            if candidate.reason_code == "not_declared"
            else OfficialSourceStatus.UNAVAILABLE
        )
        reason = candidate.reason_code
    else:
        authority = SourceAuthority.PRIMARY
        status = OfficialSourceStatus.BLOCKED
        reason = candidate.reason_code
    return _build_source(
        candidate_record_id=candidate.record_id, kind=candidate.kind,
        authority=authority, status=status, requested_url=candidate.normalized_url,
        declaring_source_id=candidate.declaring_source_id,
        declaration_locator=candidate.declaration_locator,
        expected_sha256=None if pin is None else pin.expected_sha256,
        reason_code=reason, evidence_eligible=False,
    )


def _hint_source(hint: DiscoveryHint, index: int) -> CollectedOfficialSource:
    locator = f"bounded-discovery[{index}]"
    return _build_source(
        candidate_record_id=None, kind=hint.kind, authority=hint.authority,
        status=OfficialSourceStatus.DISCOVERY_ONLY, requested_url=hint.url,
        declaring_source_id=None, declaration_locator=locator,
        reason_code=hint.reason_code, evidence_eligible=False,
    )


def _build_source(
    *, candidate_record_id: str | None, kind: OfficialSourceKind,
    authority: SourceAuthority, status: OfficialSourceStatus,
    requested_url: str | None, declaring_source_id: str | None,
    declaration_locator: str, reason_code: str, evidence_eligible: bool,
    final_url: str | None = None, redirect_chain: Sequence[str] = (),
    media_type: str | None = None, sha256: str | None = None,
    expected_sha256: str | None = None, byte_size: int | None = None,
) -> CollectedOfficialSource:
    source_id = _source_id(
        candidate_record_id=candidate_record_id, kind=kind, authority=authority,
        status=status, requested_url=requested_url, final_url=final_url,
        declaring_source_id=declaring_source_id,
        declaration_locator=declaration_locator, sha256=sha256,
        expected_sha256=expected_sha256, reason_code=reason_code,
    )
    return CollectedOfficialSource(
        source_id=source_id, candidate_record_id=candidate_record_id, kind=kind,
        authority=authority, status=status, requested_url=requested_url,
        final_url=final_url, redirect_chain=tuple(redirect_chain),
        declaring_source_id=declaring_source_id,
        declaration_locator=declaration_locator, media_type=media_type,
        object_path=None if sha256 is None else _object_path(sha256), sha256=sha256,
        expected_sha256=expected_sha256, byte_size=byte_size,
        reason_code=reason_code, evidence_eligible=evidence_eligible,
    )


def _source_relations(
    target: TargetIdentity,
    source: CollectedOfficialSource,
    assertions: tuple[RelationAssertion, ...],
) -> list[SourceRelation]:
    if not assertions:
        assertions = (
            RelationAssertion(
                candidate_record_id=source.candidate_record_id or "",
                subject_model_id=target.model_id,
                relation_to_target=RelationToTarget.EXACT_TARGET,
                declaring_source_id=source.declaring_source_id or "",
                declaration_locator=source.declaration_locator,
            ),
        )
    unique = {
        (
            item.subject_model_id, item.relation_to_target,
            item.declaring_source_id, item.declaration_locator,
        ): item
        for item in assertions
    }
    conflicting = len({(item.subject_model_id, item.relation_to_target) for item in unique.values()}) > 1
    result = []
    for item in unique.values():
        state = (
            RelationState.CONFLICTING if conflicting else
            RelationState.UNRESOLVED if item.relation_to_target is RelationToTarget.UNKNOWN else
            RelationState.DECLARED
        )
        relation_id = _relation_id(
            source.source_id, item.subject_model_id, target.model_id,
            item.relation_to_target, state, item.declaring_source_id,
            item.declaration_locator,
        )
        result.append(
            SourceRelation(
                relation_id=relation_id, source_id=source.source_id,
                subject_model_id=item.subject_model_id,
                target_model_id=target.model_id,
                relation_to_target=item.relation_to_target, state=state,
                declaring_source_id=item.declaring_source_id,
                declaration_locator=item.declaration_locator,
            )
        )
    return result


def _evaleval_envelope(
    target: TargetIdentity,
    join: EvalEvalJoinRecord | None,
    unavailable_reason: str,
) -> EvalEvalEnvelope:
    if join is None:
        _validate_reason(unavailable_reason, required=True)
        return EvalEvalEnvelope(
            availability=EvalEvalAvailability.UNAVAILABLE,
            reason_code=unavailable_reason,
            join_shape=EVALEVAL_JOIN_SHAPE,
            join=None,
        )
    if join.model_id != target.model_id:
        raise OfficialSourceError("EvalEval join model_id differs from target")
    if join.tier is EvalEvalJoinTier.NONE:
        return EvalEvalEnvelope(
            availability=EvalEvalAvailability.NO_MATCH, reason_code="no_exact_join",
            join_shape=EVALEVAL_JOIN_SHAPE, join=join,
        )
    return EvalEvalEnvelope(
        availability=EvalEvalAvailability.MATCHED,
        reason_code="discovery_records_only",
        join_shape=EVALEVAL_JOIN_SHAPE,
        join=join,
    )


def _evaluation_relations(
    target: TargetIdentity, envelope: EvalEvalEnvelope
) -> list[EvaluationRecordRelation]:
    if envelope.join is None:
        return []
    result = []
    exact_join = envelope.join.tier is EvalEvalJoinTier.EXACT
    for benchmark, rows in envelope.join.benchmarks:
        for row in rows:
            relation = (
                RelationToTarget.EXACT_TARGET
                if exact_join and row.hf_repo == target.model_id
                else RelationToTarget.UNKNOWN
            )
            relation_id = _evaluation_relation_id(
                row.evaluation_result_id, row.source_file, benchmark,
                row.hf_repo, target.model_id, relation,
            )
            result.append(
                EvaluationRecordRelation(
                    relation_id=relation_id,
                    evaluation_result_id=row.evaluation_result_id,
                    source_file=row.source_file, benchmark=benchmark,
                    claimed_model_id=row.hf_repo, target_model_id=target.model_id,
                    relation_to_target=relation, evidence_eligible=False,
                )
            )
    return result


def _index_assertions(
    discovery: OfficialDiscoveryManifest,
    assertions: Sequence[RelationAssertion],
) -> dict[str, tuple[RelationAssertion, ...]]:
    known = {item.record_id: item for item in discovery.records}
    result: dict[str, list[RelationAssertion]] = {}
    for assertion in assertions:
        if not isinstance(assertion, RelationAssertion):
            raise OfficialSourceError("relation assertions are invalid")
        candidate = known.get(assertion.candidate_record_id)
        if candidate is None or candidate.status is not DiscoveryStatus.DISCOVERED:
            raise OfficialSourceError("relation assertion references an unfetchable candidate")
        if assertion.declaring_source_id != candidate.declaring_source_id:
            raise OfficialSourceError("relation assertion declaration source is inconsistent")
        result.setdefault(assertion.candidate_record_id, []).append(assertion)
    return {
        key: tuple(sorted(values, key=lambda item: (
            item.subject_model_id, item.relation_to_target.value,
            item.declaration_locator,
        )))
        for key, values in result.items()
    }


def _index_pins(
    discovery: OfficialDiscoveryManifest, pins: Sequence[ContentPin]
) -> dict[str, ContentPin]:
    known = {item.record_id for item in discovery.records}
    result = {}
    for pin in pins:
        if not isinstance(pin, ContentPin) or pin.candidate_record_id not in known:
            raise OfficialSourceError("content pin references an unknown candidate")
        if pin.candidate_record_id in result:
            raise OfficialSourceError("duplicate content pin")
        result[pin.candidate_record_id] = pin
    return result


def _verify_policy_url(
    kind: OfficialSourceKind,
    url: str,
    policy: OfficialSourcePolicy,
) -> str | None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except (TypeError, ValueError, UnicodeError):
        return "malformed_url"
    if parsed.scheme != "https" or parsed.username is not None \
            or parsed.password is not None or port not in (None, 443):
        return "unsafe_url"
    host = (parsed.hostname or "").casefold().rstrip(".")
    decoded_path = unquote(parsed.path)
    if parsed.fragment or "\\" in decoded_path \
            or any(part in {".", ".."} for part in decoded_path.split("/")) \
            or any(ord(character) < 32 or ord(character) == 127 for character in decoded_path):
        return "unsafe_url"
    if host == "openreview.net":
        parameters = parse_qsl(parsed.query, keep_blank_values=True)
        if len(parameters) != 1 or parameters[0][0] != "id" or not parameters[0][1]:
            return "unsafe_query"
    elif parsed.query:
        # Discovery strips tracking parameters.  A redirect that adds a query
        # could contain a signed URL or credential and must not enter a frozen
        # manifest.
        return "unsafe_query"
    if host in policy.owned_hosts:
        return None if parsed.path not in {"", "/"} else "resource_unverified"
    if kind is OfficialSourceKind.PAPER:
        if host in policy.publication_hosts:
            return _publication_reason(host, parsed.path, parsed.query)
        if host in policy.code_hosts:
            return _owner_reason(parsed.path, policy.publisher_owners)
        return "untrusted_host"
    if kind is OfficialSourceKind.SYSTEM_CARD and host in policy.publication_hosts:
        return _publication_reason(host, parsed.path, parsed.query)
    if host not in policy.code_hosts:
        return "untrusted_host"
    return _owner_reason(parsed.path, policy.publisher_owners)


def _publication_reason(host: str, path: str, query: str) -> str | None:
    decoded = unquote(path)
    if host == "arxiv.org":
        return None if re.fullmatch(
            r"/(?:abs|pdf)/[0-9]{4}\.[0-9]{4,5}(?:v[0-9]+)?(?:\.pdf)?", decoded
        ) else "resource_unverified"
    if host == "openreview.net":
        params = dict(parse_qsl(query, keep_blank_values=False))
        return None if decoded in {"/forum", "/pdf", "/attachment"} \
            and params.get("id") else "resource_unverified"
    return None if decoded not in {"", "/"} else "resource_unverified"


def _owner_reason(path: str, owners: Sequence[str]) -> str | None:
    parts = [unquote(value).casefold() for value in path.split("/") if value]
    if len(parts) < 2:
        return "ownership_unverified"
    return None if parts[0] in set(owners) else "ownership_mismatch"


def _source_id(**values: Any) -> str:
    return "primary_src_" + hashlib.sha256(_canonical_json(values)).hexdigest()[:24]


def _relation_id(
    source_id: str, subject_model_id: str, target_model_id: str,
    relation: RelationToTarget, state: RelationState,
    declaring_source_id: str, locator: str,
) -> str:
    value = {
        "source_id": source_id, "subject_model_id": subject_model_id,
        "target_model_id": target_model_id, "relation_to_target": relation.value,
        "state": state.value, "declaring_source_id": declaring_source_id,
        "declaration_locator": locator,
    }
    return "source_relation_" + hashlib.sha256(_canonical_json(value)).hexdigest()[:24]


def _evaluation_relation_id(
    evaluation_result_id: str | None, source_file: str, benchmark: str,
    claimed_model_id: str | None, target_model_id: str,
    relation: RelationToTarget,
) -> str:
    value = {
        "evaluation_result_id": evaluation_result_id, "source_file": source_file,
        "benchmark": benchmark, "claimed_model_id": claimed_model_id,
        "target_model_id": target_model_id, "relation_to_target": relation.value,
    }
    return "evaluation_relation_" + hashlib.sha256(_canonical_json(value)).hexdigest()[:24]


def _bundle_id(**values: Any) -> str:
    serializable = {
        "target": values["target"].to_dict(),
        "source_bundle_id": values["source_bundle_id"],
        "discovery_id": values["discovery_id"],
        "policy": values["policy"].to_dict(),
        "limits": values["limits"].to_dict(),
        "sources": [item.to_dict() for item in values["sources"]],
        "relations": [item.to_dict() for item in values["relations"]],
        "evaleval": values["evaleval"].to_dict(),
        "evaluation_relations": [
            item.to_dict() for item in values["evaluation_relations"]
        ],
    }
    return "official_bundle_" + hashlib.sha256(_canonical_json(serializable)).hexdigest()[:32]


def _object_path(digest: str) -> str:
    return f"objects/sha256/{digest[:2]}/{digest}"


def _atomic_write_bundle(
    destination: Path,
    manifest: OfficialSourceManifest,
    objects: Mapping[str, bytes],
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=destination.parent)
    )
    try:
        for object_path, data in sorted(objects.items()):
            if not object_path:
                raise OfficialSourceIntegrityError("official object path is missing")
            path = temporary.joinpath(*PurePosixPath(object_path).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (temporary / "manifest.json").write_bytes(_canonical_json(manifest.to_dict()))
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def _validate_https_url(value: Any) -> None:
    if not isinstance(value, str) or len(value) > 4096 or not _portable_text(value):
        raise OfficialSourceIntegrityError("official URL is invalid")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError, UnicodeError) as exc:
        raise OfficialSourceIntegrityError("official URL is malformed") from exc
    if parsed.scheme != "https" or not parsed.hostname \
            or parsed.username is not None or parsed.password is not None \
            or port not in (None, 443) or parsed.fragment:
        raise OfficialSourceIntegrityError("official URL is not safe canonical HTTPS")


def _validate_model_id(value: Any) -> None:
    if not isinstance(value, str) or not _MODEL_ID_RE.fullmatch(value):
        raise OfficialSourceIntegrityError("model id is invalid")


def _validate_modelish_id(value: Any) -> None:
    if not isinstance(value, str) or not value or len(value) > 256 \
            or not _portable_text(value):
        raise OfficialSourceIntegrityError("relation subject model id is invalid")


def _validate_locator(value: Any) -> None:
    if not isinstance(value, str) or not value or len(value) > 512 \
            or not _portable_text(value):
        raise OfficialSourceIntegrityError("declaration locator is invalid")


def _validate_reason(value: Any, *, required: bool) -> None:
    if value is None and not required:
        return
    if not isinstance(value, str) or not _REASON_RE.fullmatch(value):
        raise OfficialSourceIntegrityError("reason code is invalid")


def _validate_portable_path(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value or "\\" in value:
        raise OfficialSourceIntegrityError(f"{label} must be a relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value \
            or any(part in {"", ".", ".."} for part in path.parts):
        raise OfficialSourceIntegrityError(f"{label} must be a normalized relative POSIX path")


def _valid_media_type(value: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", value))


def _portable_text(value: str) -> bool:
    return all(ord(character) >= 32 and ord(character) != 127 for character in value)


def _strict_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise OfficialSourceIntegrityError(f"{name} must be a closed object")
    return dict(value)


def _canonical_json(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8") + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise OfficialSourceIntegrityError("value is not canonical JSON") from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise OfficialSourceIntegrityError("official manifest has duplicate JSON keys")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise OfficialSourceIntegrityError("official manifest contains a non-finite number")
