"""Offline-first, exact-revision Hugging Face source bundles.

The collector in this module deliberately has no HTTP implementation.  Callers
provide a small adapter that resolves a requested model revision and returns
bounded remote objects.  This keeps network policy outside the evidence layer
and makes replay fully offline and deterministic.

Only public, portable Hugging Face URLs and relative content-object paths are
serialized.  Local paths, adapter exceptions, credentials, and response
headers never enter a bundle.
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
from urllib.parse import quote


MANIFEST_VERSION = "hf-source-bundle/v1"
DEFAULT_MAX_FILES = 16
DEFAULT_MAX_FILE_BYTES = 1_000_000
DEFAULT_MAX_TOTAL_BYTES = 4_000_000

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_MODEL_PART_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$")
_SOURCE_ID_RE = re.compile(r"^src_[0-9a-f]{24}$")
_BUNDLE_ID_RE = re.compile(r"^hf_bundle_[0-9a-f]{32}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")

_PRIMARY_PATHS = ("README.md", "config.json")
_RELEVANT_JSON_NAMES = {
    "adapter_config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "special_tokens_map.json",
    "tokenizer_config.json",
}
_RELEVANT_TEXT_TOKENS = (
    "readme",
    "model_card",
    "license",
    "notice",
    "responsible",
    "safety",
    "use_policy",
    "usage",
    "training",
    "data",
    "evaluation",
    "limitation",
)


class SourceBundleError(ValueError):
    """Base class for collector and replay integrity failures."""


class RevisionResolutionError(SourceBundleError):
    """Raised when an adapter cannot bind a request to one exact commit."""


class BundleIntegrityError(SourceBundleError):
    """Raised when an offline bundle is mutated, stale, or internally unsafe."""


class FetchStatus(str, Enum):
    OK = "ok"
    MISSING = "missing"
    GATED = "gated"
    UNAVAILABLE = "unavailable"


class CollectionStatus(str, Enum):
    COLLECTED = "collected"
    MISSING = "missing"
    GATED = "gated"
    UNAVAILABLE = "unavailable"


class RetrievalMode(str, Enum):
    DIRECT = "direct"
    METADATA_FALLBACK = "metadata_fallback"
    NOT_COLLECTED = "not_collected"
    SIZE_LIMIT = "size_limit"


class SourceKind(str, Enum):
    MODEL_METADATA = "model_metadata"
    README = "readme"
    CONFIG = "config"
    DECLARED_FILE = "declared_file"


class RelationToTarget(str, Enum):
    EXACT_TARGET = "exact_target"
    BASE_MODEL = "base_model"
    UNKNOWN = "unknown"


class DeclarationStatus(str, Enum):
    DECLARED = "declared"
    CONSISTENT = "consistent"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class RemoteObject:
    """One adapter response, already classified at the network boundary."""

    status: FetchStatus
    content: bytes | None = None
    reason_code: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", FetchStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise SourceBundleError("remote object has an invalid fetch status") from exc
        if self.status is FetchStatus.OK:
            if not isinstance(self.content, bytes):
                raise SourceBundleError("an ok remote object must contain bytes")
            if self.reason_code is not None:
                raise SourceBundleError("an ok remote object cannot have a reason code")
        elif self.content is not None:
            raise SourceBundleError("a non-ok remote object cannot contain bytes")
        if self.reason_code is not None and (
            not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(self.reason_code)
        ):
            raise SourceBundleError("remote reason_code must be a portable identifier")


class HuggingFaceSourceAdapter(Protocol):
    """Injected network boundary used by :func:`collect_hf_source_bundle`."""

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        """Return the exact lowercase 40-character commit for the request."""

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        """Fetch ``/api/models/{id}/revision/{commit}`` within ``max_bytes``."""

    def fetch_file(
        self, model_id: str, revision: str, repo_path: str, *, max_bytes: int
    ) -> RemoteObject:
        """Fetch one repository file at the exact commit within ``max_bytes``."""


@dataclass(frozen=True)
class TargetIdentity:
    model_id: str
    revision: str

    def __post_init__(self) -> None:
        _validate_model_id(self.model_id)
        if not isinstance(self.revision, str) or not _COMMIT_RE.fullmatch(self.revision):
            raise SourceBundleError("revision must be a resolved 40-character lowercase commit")

    def to_dict(self) -> dict[str, str]:
        return {"model_id": self.model_id, "revision": self.revision}

    @classmethod
    def from_dict(cls, value: Any) -> "TargetIdentity":
        item = _strict_object(value, {"model_id", "revision"}, "target")
        return cls(model_id=item["model_id"], revision=item["revision"])


@dataclass(frozen=True)
class CollectionLimits:
    max_files: int = DEFAULT_MAX_FILES
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES

    def __post_init__(self) -> None:
        if isinstance(self.max_files, bool) or not isinstance(self.max_files, int):
            raise SourceBundleError("max_files must be an integer")
        if not 3 <= self.max_files <= 64:
            raise SourceBundleError("max_files must be between 3 and 64")
        for name, value in (
            ("max_file_bytes", self.max_file_bytes),
            ("max_total_bytes", self.max_total_bytes),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise SourceBundleError(f"{name} must be a positive integer")
        if self.max_file_bytes > self.max_total_bytes:
            raise SourceBundleError("max_file_bytes cannot exceed max_total_bytes")

    def to_dict(self) -> dict[str, int]:
        return {
            "max_files": self.max_files,
            "max_file_bytes": self.max_file_bytes,
            "max_total_bytes": self.max_total_bytes,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "CollectionLimits":
        item = _strict_object(
            value, {"max_files", "max_file_bytes", "max_total_bytes"}, "limits"
        )
        return cls(
            max_files=item["max_files"],
            max_file_bytes=item["max_file_bytes"],
            max_total_bytes=item["max_total_bytes"],
        )


@dataclass(frozen=True)
class SourceRecord:
    source_id: str
    kind: SourceKind
    repository_path: str | None
    source_url: str
    target_model_id: str
    target_revision: str
    status: CollectionStatus
    fetch_status: FetchStatus
    retrieval: RetrievalMode
    media_type: str
    object_path: str | None
    sha256: str | None
    byte_size: int | None
    reason_code: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise BundleIntegrityError("source_id is invalid")
        for name, enum_type in (
            ("kind", SourceKind),
            ("status", CollectionStatus),
            ("fetch_status", FetchStatus),
            ("retrieval", RetrievalMode),
        ):
            try:
                object.__setattr__(self, name, enum_type(getattr(self, name)))
            except (TypeError, ValueError) as exc:
                raise BundleIntegrityError(f"source {name} is invalid") from exc
        target = TargetIdentity(self.target_model_id, self.target_revision)
        if self.kind is SourceKind.MODEL_METADATA:
            if self.repository_path is not None:
                raise BundleIntegrityError("model metadata cannot have a repository path")
        else:
            if not isinstance(self.repository_path, str):
                raise BundleIntegrityError("file source requires a repository path")
            _validate_repo_path(self.repository_path)
        expected_id = _source_id(target, self.kind, self.repository_path)
        if self.source_id != expected_id:
            raise BundleIntegrityError("source_id does not match the exact target and source")
        if not isinstance(self.source_url, str) or self.source_url != _expected_source_url(self):
            raise BundleIntegrityError("source URL does not match the exact target revision")
        if not isinstance(self.media_type, str) or self.media_type != _media_type(
            self.kind, self.repository_path
        ):
            raise BundleIntegrityError("source media_type is invalid")
        if self.reason_code is not None and (
            not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(self.reason_code)
        ):
            raise BundleIntegrityError("source reason_code is invalid")

        content_values = (self.object_path, self.sha256, self.byte_size)
        if self.status is CollectionStatus.COLLECTED:
            if self.sha256 is None or not isinstance(self.sha256, str) or not _DIGEST_RE.fullmatch(
                self.sha256
            ):
                raise BundleIntegrityError("collected source requires a SHA-256 digest")
            if (
                isinstance(self.byte_size, bool)
                or not isinstance(self.byte_size, int)
                or self.byte_size < 0
            ):
                raise BundleIntegrityError("collected source requires a non-negative byte size")
            expected_object_path = _object_path(self.sha256)
            if self.object_path != expected_object_path:
                raise BundleIntegrityError("source object path is not content-addressed")
        elif content_values != (None, None, None):
            raise BundleIntegrityError("uncollected source cannot reference content")

        if self.retrieval is RetrievalMode.DIRECT:
            if (
                self.status is not CollectionStatus.COLLECTED
                or self.fetch_status is not FetchStatus.OK
            ):
                raise BundleIntegrityError("direct retrieval must be an ok collected source")
            if self.reason_code is not None:
                raise BundleIntegrityError("direct retrieval cannot have a reason code")
        elif self.retrieval is RetrievalMode.METADATA_FALLBACK:
            if self.kind is not SourceKind.CONFIG:
                raise BundleIntegrityError("only config may use metadata fallback")
            if self.fetch_status is FetchStatus.OK:
                raise BundleIntegrityError("metadata fallback must preserve a non-ok fetch status")
            valid_fallback = (
                self.status is CollectionStatus.COLLECTED and self.reason_code is not None
            ) or (
                self.status is CollectionStatus.UNAVAILABLE
                and self.reason_code == "size_limit"
            )
            if not valid_fallback:
                raise BundleIntegrityError("metadata fallback state is invalid")
        elif self.retrieval is RetrievalMode.NOT_COLLECTED:
            expected_status = CollectionStatus(self.fetch_status.value)
            if self.fetch_status is FetchStatus.OK or self.status is not expected_status:
                raise BundleIntegrityError("uncollected source status must preserve fetch status")
            if self.reason_code is None:
                raise BundleIntegrityError("uncollected source must preserve a reason code")
        else:
            if (
                self.status is not CollectionStatus.UNAVAILABLE
                or self.fetch_status is not FetchStatus.OK
                or self.reason_code != "size_limit"
            ):
                raise BundleIntegrityError("size-limited source state is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "kind": self.kind.value,
            "repository_path": self.repository_path,
            "source_url": self.source_url,
            "target_model_id": self.target_model_id,
            "target_revision": self.target_revision,
            "status": self.status.value,
            "fetch_status": self.fetch_status.value,
            "retrieval": self.retrieval.value,
            "media_type": self.media_type,
            "object_path": self.object_path,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
            "reason_code": self.reason_code,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "SourceRecord":
        keys = {
            "source_id",
            "kind",
            "repository_path",
            "source_url",
            "target_model_id",
            "target_revision",
            "status",
            "fetch_status",
            "retrieval",
            "media_type",
            "object_path",
            "sha256",
            "byte_size",
            "reason_code",
        }
        return cls(**_strict_object(value, keys, "source record"))


@dataclass(frozen=True)
class RelationRecord:
    source_id: str
    declaration_path: str
    declared_model_id: str
    relation_to_target: RelationToTarget

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise BundleIntegrityError("relation source_id is invalid")
        if not isinstance(self.declaration_path, str) or not self.declaration_path:
            raise BundleIntegrityError("relation declaration_path is invalid")
        if (
            not isinstance(self.declared_model_id, str)
            or not self.declared_model_id
            or len(self.declared_model_id) > 256
            or not _is_portable_text(self.declared_model_id)
        ):
            raise BundleIntegrityError("declared model id is invalid")
        try:
            object.__setattr__(
                self, "relation_to_target", RelationToTarget(self.relation_to_target)
            )
        except (TypeError, ValueError) as exc:
            raise BundleIntegrityError("relation_to_target is invalid") from exc

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "declaration_path": self.declaration_path,
            "declared_model_id": self.declared_model_id,
            "relation_to_target": self.relation_to_target.value,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RelationRecord":
        item = _strict_object(
            value,
            {"source_id", "declaration_path", "declared_model_id", "relation_to_target"},
            "relation record",
        )
        return cls(**item)


@dataclass(frozen=True)
class DeclarationRecord:
    kind: str
    value: str
    source_id: str
    declaration_path: str
    status: DeclarationStatus

    def __post_init__(self) -> None:
        if self.kind != "license":
            raise BundleIntegrityError("only license declarations are supported in v1")
        if (
            not isinstance(self.value, str)
            or not self.value
            or len(self.value) > 256
            or not _is_portable_text(self.value)
        ):
            raise BundleIntegrityError("declaration value is invalid")
        if not isinstance(self.source_id, str) or not _SOURCE_ID_RE.fullmatch(self.source_id):
            raise BundleIntegrityError("declaration source_id is invalid")
        if not isinstance(self.declaration_path, str) or not self.declaration_path:
            raise BundleIntegrityError("declaration path is invalid")
        try:
            object.__setattr__(self, "status", DeclarationStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise BundleIntegrityError("declaration status is invalid") from exc

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "value": self.value,
            "source_id": self.source_id,
            "declaration_path": self.declaration_path,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "DeclarationRecord":
        item = _strict_object(
            value,
            {"kind", "value", "source_id", "declaration_path", "status"},
            "declaration record",
        )
        return cls(**item)


@dataclass(frozen=True)
class BundleManifest:
    manifest_version: str
    bundle_id: str
    target: TargetIdentity
    requested_revision: str | None
    limits: CollectionLimits
    sources: tuple[SourceRecord, ...]
    relations: tuple[RelationRecord, ...]
    declarations: tuple[DeclarationRecord, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "relations", tuple(self.relations))
        object.__setattr__(self, "declarations", tuple(self.declarations))
        if self.manifest_version != MANIFEST_VERSION:
            raise BundleIntegrityError(f"unsupported manifest version: {self.manifest_version!r}")
        if not isinstance(self.target, TargetIdentity):
            raise BundleIntegrityError("manifest target is invalid")
        if not isinstance(self.limits, CollectionLimits):
            raise BundleIntegrityError("manifest limits are invalid")
        _validate_requested_revision(self.requested_revision)
        if not isinstance(self.bundle_id, str) or not _BUNDLE_ID_RE.fullmatch(self.bundle_id):
            raise BundleIntegrityError("bundle_id is invalid")
        if len(self.sources) > self.limits.max_files:
            raise BundleIntegrityError("manifest exceeds its source count limit")
        if not all(isinstance(item, SourceRecord) for item in self.sources):
            raise BundleIntegrityError("manifest sources are invalid")
        if not all(isinstance(item, RelationRecord) for item in self.relations):
            raise BundleIntegrityError("manifest relations are invalid")
        if not all(isinstance(item, DeclarationRecord) for item in self.declarations):
            raise BundleIntegrityError("manifest declarations are invalid")

        source_ids = [item.source_id for item in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise BundleIntegrityError("manifest contains duplicate source ids")
        source_keys = [(item.kind.value, item.repository_path) for item in self.sources]
        if len(source_keys) != len(set(source_keys)):
            raise BundleIntegrityError("manifest contains duplicate logical sources")
        required = {SourceKind.MODEL_METADATA, SourceKind.README, SourceKind.CONFIG}
        present = {item.kind for item in self.sources if item.kind in required}
        if present != required:
            raise BundleIntegrityError("manifest must contain metadata, README, and config records")

        known_sources = set(source_ids)
        for source in self.sources:
            if (source.target_model_id, source.target_revision) != (
                self.target.model_id,
                self.target.revision,
            ):
                raise BundleIntegrityError("source target drifts from manifest target")
            if source.byte_size is not None and source.byte_size > self.limits.max_file_bytes:
                raise BundleIntegrityError("source exceeds the recorded per-file limit")
        stored_total = sum(item.byte_size or 0 for item in self.sources)
        if stored_total > self.limits.max_total_bytes:
            raise BundleIntegrityError("manifest exceeds its total byte limit")

        relation_keys: set[tuple[str, str, str]] = set()
        for relation in self.relations:
            if relation.source_id not in known_sources:
                raise BundleIntegrityError("relation references an unknown source")
            key = (
                relation.source_id,
                relation.declaration_path,
                relation.declared_model_id,
            )
            if key in relation_keys:
                raise BundleIntegrityError("manifest contains duplicate relation records")
            relation_keys.add(key)
            expected_relation = _classify_relation(
                relation.declared_model_id, self.target.model_id
            )
            if relation.relation_to_target is not expected_relation:
                raise BundleIntegrityError("relation classification is inconsistent")

        declaration_keys: set[tuple[str, str, str, str]] = set()
        for declaration in self.declarations:
            if declaration.source_id not in known_sources:
                raise BundleIntegrityError("declaration references an unknown source")
            key = (
                declaration.kind,
                declaration.value,
                declaration.source_id,
                declaration.declaration_path,
            )
            if key in declaration_keys:
                raise BundleIntegrityError("manifest contains duplicate declarations")
            declaration_keys.add(key)
        _validate_declaration_statuses(self.declarations)

        expected_bundle_id = _bundle_id(
            target=self.target,
            requested_revision=self.requested_revision,
            limits=self.limits,
            sources=self.sources,
            relations=self.relations,
            declarations=self.declarations,
        )
        if self.bundle_id != expected_bundle_id:
            raise BundleIntegrityError("bundle_id does not match the closed manifest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "bundle_id": self.bundle_id,
            "target": self.target.to_dict(),
            "requested_revision": self.requested_revision,
            "limits": self.limits.to_dict(),
            "sources": [item.to_dict() for item in self.sources],
            "relations": [item.to_dict() for item in self.relations],
            "declarations": [item.to_dict() for item in self.declarations],
        }

    @classmethod
    def from_dict(cls, value: Any) -> "BundleManifest":
        item = _strict_object(
            value,
            {
                "manifest_version",
                "bundle_id",
                "target",
                "requested_revision",
                "limits",
                "sources",
                "relations",
                "declarations",
            },
            "manifest",
        )
        for name in ("sources", "relations", "declarations"):
            if not isinstance(item[name], list):
                raise BundleIntegrityError(f"manifest {name} must be a list")
        return cls(
            manifest_version=item["manifest_version"],
            bundle_id=item["bundle_id"],
            target=TargetIdentity.from_dict(item["target"]),
            requested_revision=item["requested_revision"],
            limits=CollectionLimits.from_dict(item["limits"]),
            sources=tuple(SourceRecord.from_dict(entry) for entry in item["sources"]),
            relations=tuple(RelationRecord.from_dict(entry) for entry in item["relations"]),
            declarations=tuple(
                DeclarationRecord.from_dict(entry) for entry in item["declarations"]
            ),
        )


@dataclass(frozen=True)
class ReplayedSource:
    record: SourceRecord
    content: bytes | None


@dataclass(frozen=True)
class ReplayedSourceBundle:
    manifest: BundleManifest
    sources: tuple[ReplayedSource, ...]

    def source(self, source_id: str) -> ReplayedSource:
        for source in self.sources:
            if source.record.source_id == source_id:
                return source
        raise KeyError(f"unknown source: {source_id}")

    @property
    def contents(self) -> Mapping[str, bytes]:
        """Immutable mapping of collected source IDs to their exact bytes."""

        return MappingProxyType(
            {
                item.record.source_id: item.content
                for item in self.sources
                if item.content is not None
            }
        )


def parse_target_request(
    model_id: str, revision: str | None = None
) -> tuple[str, str | None]:
    """Parse ``namespace/name`` or ``namespace/name@revision`` without resolving it."""

    if not isinstance(model_id, str):
        raise SourceBundleError("model_id must be a string")
    if "@" in model_id:
        if revision is not None:
            raise SourceBundleError("revision cannot be supplied twice")
        model_id, embedded_revision = model_id.rsplit("@", 1)
        revision = embedded_revision
    _validate_model_id(model_id)
    _validate_requested_revision(revision)
    return model_id, revision


def collect_hf_source_bundle(
    model_id: str,
    destination: str | os.PathLike[str],
    adapter: HuggingFaceSourceAdapter,
    *,
    revision: str | None = None,
    max_files: int = DEFAULT_MAX_FILES,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> BundleManifest:
    """Collect a bounded exact-target source bundle and atomically publish it locally."""

    destination_path = Path(destination)
    if destination_path.exists() or destination_path.is_symlink():
        raise FileExistsError(f"bundle destination already exists: {destination_path}")
    parsed_model_id, requested_revision = parse_target_request(model_id, revision)
    limits = CollectionLimits(max_files, max_file_bytes, max_total_bytes)
    try:
        resolved_revision = adapter.resolve_revision(parsed_model_id, requested_revision)
    except Exception as exc:
        raise RevisionResolutionError(
            "the adapter could not resolve the requested model revision"
        ) from exc
    if not isinstance(resolved_revision, str) or not _COMMIT_RE.fullmatch(resolved_revision):
        raise RevisionResolutionError(
            "the adapter did not return an exact 40-character lowercase commit"
        )
    target = TargetIdentity(parsed_model_id, resolved_revision)

    objects: dict[str, bytes] = {}
    sources: list[SourceRecord] = []
    total_bytes = 0

    metadata_response = _require_remote_object(
        adapter.fetch_model_metadata(
            target.model_id, target.revision, max_bytes=limits.max_file_bytes
        ),
        "model metadata",
    )
    metadata_source, metadata_data, stored = _collect_metadata(
        target, metadata_response, limits, total_bytes, objects
    )
    sources.append(metadata_source)
    total_bytes += stored

    readme_response = _require_remote_object(
        adapter.fetch_file(
            target.model_id,
            target.revision,
            "README.md",
            max_bytes=limits.max_file_bytes,
        ),
        "README.md",
    )
    readme_source, readme_text, stored = _collect_file(
        target=target,
        kind=SourceKind.README,
        repo_path="README.md",
        response=readme_response,
        limits=limits,
        total_bytes=total_bytes,
        objects=objects,
    )
    sources.append(readme_source)
    total_bytes += stored

    config_response = _require_remote_object(
        adapter.fetch_file(
            target.model_id,
            target.revision,
            "config.json",
            max_bytes=limits.max_file_bytes,
        ),
        "config.json",
    )
    config_fallback = None
    if config_response.status is not FetchStatus.OK and isinstance(metadata_data, dict):
        candidate = metadata_data.get("config")
        if isinstance(candidate, dict):
            config_fallback = _canonical_json(candidate)
    config_source, _, stored = _collect_file(
        target=target,
        kind=SourceKind.CONFIG,
        repo_path="config.json",
        response=config_response,
        limits=limits,
        total_bytes=total_bytes,
        objects=objects,
        metadata_fallback=config_fallback,
    )
    sources.append(config_source)
    total_bytes += stored

    declared_paths = _declared_relevant_paths(metadata_data)
    remaining_slots = limits.max_files - len(sources)
    for repo_path in declared_paths[:remaining_slots]:
        response = _require_remote_object(
            adapter.fetch_file(
                target.model_id,
                target.revision,
                repo_path,
                max_bytes=limits.max_file_bytes,
            ),
            repo_path,
        )
        source, _, stored = _collect_file(
            target=target,
            kind=SourceKind.DECLARED_FILE,
            repo_path=repo_path,
            response=response,
            limits=limits,
            total_bytes=total_bytes,
            objects=objects,
        )
        sources.append(source)
        total_bytes += stored

    relations = _discover_relations(
        target, metadata_source, metadata_data, readme_source, readme_text
    )
    declarations = _discover_declarations(
        metadata_source, metadata_data, readme_source, readme_text
    )
    manifest = _make_manifest(
        target=target,
        requested_revision=requested_revision,
        limits=limits,
        sources=tuple(sources),
        relations=relations,
        declarations=declarations,
    )
    _atomic_write_bundle(destination_path, manifest, objects)
    return manifest


def replay_source_bundle(
    bundle_dir: str | os.PathLike[str],
    *,
    expected_model_id: str | None = None,
    expected_revision: str | None = None,
) -> ReplayedSourceBundle:
    """Replay a bundle offline after rehashing all files and checking target identity."""

    root = Path(bundle_dir)
    if root.is_symlink() or not root.is_dir():
        raise BundleIntegrityError("bundle path must be a real directory")
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise BundleIntegrityError("bundle manifest is missing or unsafe")
    manifest_bytes = manifest_path.read_bytes()
    try:
        raw_manifest = json.loads(
            manifest_bytes.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, BundleIntegrityError) as exc:
        if isinstance(exc, BundleIntegrityError):
            raise
        raise BundleIntegrityError("bundle manifest is not strict UTF-8 JSON") from exc
    if manifest_bytes != _canonical_json(raw_manifest):
        raise BundleIntegrityError("bundle manifest is stale or non-canonical")
    manifest = BundleManifest.from_dict(raw_manifest)

    if expected_model_id is not None:
        _validate_model_id(expected_model_id)
        if manifest.target.model_id != expected_model_id:
            raise BundleIntegrityError("bundle model_id does not match the expected target")
    if expected_revision is not None:
        if not isinstance(expected_revision, str) or not _COMMIT_RE.fullmatch(expected_revision):
            raise SourceBundleError("expected_revision must be an exact lowercase commit")
        if manifest.target.revision != expected_revision:
            raise BundleIntegrityError("bundle revision does not match the expected target")

    expected_files = {"manifest.json"}
    expected_files.update(
        source.object_path for source in manifest.sources if source.object_path is not None
    )
    actual_files: set[str] = set()
    for entry in root.rglob("*"):
        if entry.is_symlink():
            raise BundleIntegrityError("bundle contains a symbolic link")
        if entry.is_file():
            relative = entry.relative_to(root).as_posix()
            _validate_bundle_relative_path(relative)
            actual_files.add(relative)
    if actual_files != expected_files:
        missing = sorted(expected_files - actual_files)
        unexpected = sorted(actual_files - expected_files)
        raise BundleIntegrityError(
            f"bundle file set is stale (missing={missing}, unexpected={unexpected})"
        )

    content_by_object: dict[str, bytes] = {}
    for object_path in sorted(expected_files - {"manifest.json"}):
        path = root.joinpath(*PurePosixPath(object_path).parts)
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if object_path != _object_path(digest):
            raise BundleIntegrityError("content object bytes do not match their address")
        content_by_object[object_path] = data

    replayed: list[ReplayedSource] = []
    for source in manifest.sources:
        content = None
        if source.object_path is not None:
            content = content_by_object[source.object_path]
            if len(content) != source.byte_size:
                raise BundleIntegrityError("source byte size does not match replayed content")
            if hashlib.sha256(content).hexdigest() != source.sha256:
                raise BundleIntegrityError("source digest does not match replayed content")
        replayed.append(ReplayedSource(record=source, content=content))
    return ReplayedSourceBundle(manifest=manifest, sources=tuple(replayed))


def _collect_metadata(
    target: TargetIdentity,
    response: RemoteObject,
    limits: CollectionLimits,
    total_bytes: int,
    objects: dict[str, bytes],
) -> tuple[SourceRecord, dict[str, Any] | None, int]:
    if response.status is not FetchStatus.OK:
        return (
            _status_source(
                target,
                SourceKind.MODEL_METADATA,
                None,
                response.status,
                response.reason_code,
            ),
            None,
            0,
        )
    assert response.content is not None
    if len(response.content) > limits.max_file_bytes or (
        total_bytes + len(response.content) > limits.max_total_bytes
    ):
        return _size_limited_source(target, SourceKind.MODEL_METADATA, None), None, 0
    try:
        text = response.content.decode("utf-8")
        data = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, BundleIntegrityError) as exc:
        raise SourceBundleError("model metadata is not strict UTF-8 JSON") from exc
    if not isinstance(data, dict):
        raise SourceBundleError("model metadata must be a JSON object")
    metadata_sha = data.get("sha")
    if metadata_sha is not None and metadata_sha != target.revision:
        raise SourceBundleError("model metadata revision drifts from the resolved target")
    for identity_key in ("id", "modelId"):
        metadata_model_id = data.get(identity_key)
        if metadata_model_id is not None and metadata_model_id != target.model_id:
            raise SourceBundleError("model metadata repository drifts from the resolved target")
    record = _collected_source(
        target,
        SourceKind.MODEL_METADATA,
        None,
        response.content,
        FetchStatus.OK,
        RetrievalMode.DIRECT,
    )
    objects.setdefault(record.sha256, response.content)
    return record, data, len(response.content)


def _collect_file(
    *,
    target: TargetIdentity,
    kind: SourceKind,
    repo_path: str,
    response: RemoteObject,
    limits: CollectionLimits,
    total_bytes: int,
    objects: dict[str, bytes],
    metadata_fallback: bytes | None = None,
) -> tuple[SourceRecord, str | None, int]:
    _validate_repo_path(repo_path)
    content = response.content
    retrieval = RetrievalMode.DIRECT
    if response.status is not FetchStatus.OK:
        if metadata_fallback is None:
            return (
                _status_source(
                    target, kind, repo_path, response.status, response.reason_code
                ),
                None,
                0,
            )
        content = metadata_fallback
        retrieval = RetrievalMode.METADATA_FALLBACK
    assert content is not None
    if len(content) > limits.max_file_bytes or total_bytes + len(content) > limits.max_total_bytes:
        if retrieval is RetrievalMode.METADATA_FALLBACK:
            return (
                _metadata_fallback_size_limited_source(
                    target, kind, repo_path, response.status
                ),
                None,
                0,
            )
        return _size_limited_source(target, kind, repo_path), None, 0
    text = None
    if _media_type(kind, repo_path) in ("text/markdown", "text/plain"):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SourceBundleError(f"declared text source is not UTF-8: {repo_path}") from exc
    elif _media_type(kind, repo_path) == "application/json":
        try:
            json.loads(
                content.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_nonfinite_json,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, BundleIntegrityError) as exc:
            raise SourceBundleError(f"declared JSON source is invalid: {repo_path}") from exc
    record = _collected_source(
        target,
        kind,
        repo_path,
        content,
        response.status,
        retrieval,
        reason_code=(response.reason_code or response.status.value)
        if retrieval is RetrievalMode.METADATA_FALLBACK
        else None,
    )
    objects.setdefault(record.sha256, content)
    return record, text, len(content)


def _collected_source(
    target: TargetIdentity,
    kind: SourceKind,
    repo_path: str | None,
    content: bytes,
    fetch_status: FetchStatus,
    retrieval: RetrievalMode,
    reason_code: str | None = None,
) -> SourceRecord:
    digest = hashlib.sha256(content).hexdigest()
    return SourceRecord(
        source_id=_source_id(target, kind, repo_path),
        kind=kind,
        repository_path=repo_path,
        source_url=_expected_source_url_values(
            kind, repo_path, target.model_id, target.revision, retrieval
        ),
        target_model_id=target.model_id,
        target_revision=target.revision,
        status=CollectionStatus.COLLECTED,
        fetch_status=fetch_status,
        retrieval=retrieval,
        media_type=_media_type(kind, repo_path),
        object_path=_object_path(digest),
        sha256=digest,
        byte_size=len(content),
        reason_code=reason_code,
    )


def _status_source(
    target: TargetIdentity,
    kind: SourceKind,
    repo_path: str | None,
    fetch_status: FetchStatus,
    reason_code: str | None,
) -> SourceRecord:
    if fetch_status is FetchStatus.OK:
        raise SourceBundleError("ok response cannot produce an uncollected status record")
    retrieval = RetrievalMode.NOT_COLLECTED
    return SourceRecord(
        source_id=_source_id(target, kind, repo_path),
        kind=kind,
        repository_path=repo_path,
        source_url=_expected_source_url_values(
            kind, repo_path, target.model_id, target.revision, retrieval
        ),
        target_model_id=target.model_id,
        target_revision=target.revision,
        status=CollectionStatus(fetch_status.value),
        fetch_status=fetch_status,
        retrieval=retrieval,
        media_type=_media_type(kind, repo_path),
        object_path=None,
        sha256=None,
        byte_size=None,
        reason_code=reason_code or fetch_status.value,
    )


def _size_limited_source(
    target: TargetIdentity, kind: SourceKind, repo_path: str | None
) -> SourceRecord:
    retrieval = RetrievalMode.SIZE_LIMIT
    return SourceRecord(
        source_id=_source_id(target, kind, repo_path),
        kind=kind,
        repository_path=repo_path,
        source_url=_expected_source_url_values(
            kind, repo_path, target.model_id, target.revision, retrieval
        ),
        target_model_id=target.model_id,
        target_revision=target.revision,
        status=CollectionStatus.UNAVAILABLE,
        fetch_status=FetchStatus.OK,
        retrieval=retrieval,
        media_type=_media_type(kind, repo_path),
        object_path=None,
        sha256=None,
        byte_size=None,
        reason_code="size_limit",
    )


def _metadata_fallback_size_limited_source(
    target: TargetIdentity,
    kind: SourceKind,
    repo_path: str,
    fetch_status: FetchStatus,
) -> SourceRecord:
    retrieval = RetrievalMode.METADATA_FALLBACK
    return SourceRecord(
        source_id=_source_id(target, kind, repo_path),
        kind=kind,
        repository_path=repo_path,
        source_url=_expected_source_url_values(
            kind, repo_path, target.model_id, target.revision, retrieval
        ),
        target_model_id=target.model_id,
        target_revision=target.revision,
        status=CollectionStatus.UNAVAILABLE,
        fetch_status=fetch_status,
        retrieval=retrieval,
        media_type=_media_type(kind, repo_path),
        object_path=None,
        sha256=None,
        byte_size=None,
        reason_code="size_limit",
    )


def _declared_relevant_paths(metadata: dict[str, Any] | None) -> tuple[str, ...]:
    if metadata is None:
        return ()
    siblings = metadata.get("siblings", [])
    if siblings is None:
        return ()
    if not isinstance(siblings, list):
        raise SourceBundleError("model metadata siblings must be a list")
    declared: list[str] = []
    seen: set[str] = set()
    for entry in siblings:
        if isinstance(entry, str):
            path = entry
        elif isinstance(entry, dict) and isinstance(entry.get("rfilename"), str):
            path = entry["rfilename"]
        else:
            continue
        _validate_repo_path(path)
        if path in seen:
            raise SourceBundleError("model metadata contains duplicate declared files")
        seen.add(path)
        if path in _PRIMARY_PATHS or not _is_relevant_declared_path(path):
            continue
        declared.append(path)
    # Human-readable declarations carry more source value than auxiliary JSON
    # when the caller's file budget is tight.  Each group is still stable.
    return tuple(
        sorted(
            declared,
            key=lambda value: (
                PurePosixPath(value).suffix.casefold() == ".json",
                value.casefold(),
                value,
            ),
        )
    )


def _is_relevant_declared_path(path: str) -> bool:
    name = PurePosixPath(path).name.casefold()
    if name in _RELEVANT_JSON_NAMES:
        return True
    suffix = PurePosixPath(name).suffix
    if suffix not in {".md", ".txt", ""}:
        return False
    stem = PurePosixPath(name).stem
    return any(token in stem for token in _RELEVANT_TEXT_TOKENS)


def _discover_relations(
    target: TargetIdentity,
    metadata_source: SourceRecord,
    metadata: dict[str, Any] | None,
    readme_source: SourceRecord,
    readme_text: str | None,
) -> tuple[RelationRecord, ...]:
    raw: list[tuple[str, str, str]] = []
    if metadata is not None and metadata_source.status is CollectionStatus.COLLECTED:
        for path, value in _metadata_values(metadata, "base_model"):
            for declared in _flatten_declared_values(value):
                raw.append((metadata_source.source_id, path, declared))
    if readme_text is not None and readme_source.status is CollectionStatus.COLLECTED:
        for declared in _frontmatter_values(readme_text, "base_model"):
            raw.append((readme_source.source_id, "frontmatter.base_model", declared))
    records: list[RelationRecord] = []
    seen: set[tuple[str, str, str]] = set()
    for source_id, path, declared in raw:
        key = (source_id, path, declared)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            RelationRecord(
                source_id=source_id,
                declaration_path=path,
                declared_model_id=declared,
                relation_to_target=_classify_relation(declared, target.model_id),
            )
        )
    return tuple(
        sorted(
            records,
            key=lambda item: (
                item.source_id,
                item.declaration_path,
                item.declared_model_id,
            ),
        )
    )


def _discover_declarations(
    metadata_source: SourceRecord,
    metadata: dict[str, Any] | None,
    readme_source: SourceRecord,
    readme_text: str | None,
) -> tuple[DeclarationRecord, ...]:
    raw: list[tuple[str, str, str]] = []
    if metadata is not None and metadata_source.status is CollectionStatus.COLLECTED:
        for path, value in _metadata_values(metadata, "license"):
            for declared in _flatten_declared_values(value):
                raw.append((metadata_source.source_id, path, declared))
    if readme_text is not None and readme_source.status is CollectionStatus.COLLECTED:
        for declared in _frontmatter_values(readme_text, "license"):
            raw.append((readme_source.source_id, "frontmatter.license", declared))
    unique = sorted(set(raw), key=lambda item: (item[0], item[1], item[2]))
    normalized = {value.strip().casefold() for _, _, value in unique}
    if len(normalized) > 1:
        status = DeclarationStatus.CONFLICT
    elif len(unique) > 1:
        status = DeclarationStatus.CONSISTENT
    else:
        status = DeclarationStatus.DECLARED
    return tuple(
        DeclarationRecord(
            kind="license",
            value=value,
            source_id=source_id,
            declaration_path=path,
            status=status,
        )
        for source_id, path, value in unique
    )


def _metadata_values(metadata: dict[str, Any], key: str) -> tuple[tuple[str, Any], ...]:
    values: list[tuple[str, Any]] = []
    if key in metadata:
        values.append((f"/{key}", metadata[key]))
    for container_key in ("cardData", "card_data"):
        container = metadata.get(container_key)
        if isinstance(container, dict) and key in container:
            values.append((f"/{container_key}/{key}", container[key]))
    return tuple(values)


def _flatten_declared_values(value: Any) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(value, str):
        candidate = _clean_declared_value(value)
        if candidate is not None:
            values.append(candidate)
    elif isinstance(value, list):
        for item in value:
            values.extend(_flatten_declared_values(item))
    elif isinstance(value, dict):
        for key in ("model_id", "name", "id"):
            if key in value:
                values.extend(_flatten_declared_values(value[key]))
                break
        else:
            candidate = _clean_declared_value(
                json.dumps(
                    value,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            if candidate is not None:
                values.append(candidate)
    return tuple(values)


def _frontmatter_values(text: str, key: str) -> tuple[str, ...]:
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return ()
    end = None
    for index in range(1, min(len(lines), 512)):
        if lines[index].strip() in {"---", "..."}:
            end = index
            break
    if end is None:
        return ()
    values: list[str] = []
    index = 1
    while index < end:
        line = lines[index]
        if line.startswith((" ", "\t")) or ":" not in line:
            index += 1
            continue
        name, raw_value = line.split(":", 1)
        if name.strip() != key:
            index += 1
            continue
        raw_value = raw_value.strip()
        if raw_value:
            for candidate in _parse_inline_yaml_values(raw_value):
                cleaned = _clean_declared_value(candidate)
                if cleaned is not None:
                    values.append(cleaned)
            index += 1
            continue
        index += 1
        while index < end:
            nested = lines[index]
            if nested and not nested.startswith((" ", "\t", "-")):
                break
            stripped = nested.strip()
            if stripped.startswith("-"):
                candidate = stripped[1:].strip()
                if candidate.startswith(("name:", "model_id:", "id:")):
                    candidate = candidate.split(":", 1)[1].strip()
                cleaned = _clean_declared_value(candidate)
                if cleaned is not None:
                    values.append(cleaned)
            elif stripped.startswith(("name:", "model_id:", "id:")):
                cleaned = _clean_declared_value(stripped.split(":", 1)[1].strip())
                if cleaned is not None:
                    values.append(cleaned)
            index += 1
        continue
    return tuple(values)


def _parse_inline_yaml_values(value: str) -> tuple[str, ...]:
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1]
        return tuple(item.strip() for item in body.split(",") if item.strip())
    return (value,)


def _clean_declared_value(value: str) -> str | None:
    candidate = value.strip()
    if len(candidate) >= 2 and candidate[0] == candidate[-1] and candidate[0] in {"'", '"'}:
        candidate = candidate[1:-1].strip()
    if not candidate or candidate.casefold() in {"null", "none", "~"}:
        return None
    if len(candidate) > 256 or not _is_portable_text(candidate):
        return None
    return candidate


def _classify_relation(declared_model_id: str, target_model_id: str) -> RelationToTarget:
    if declared_model_id == target_model_id:
        return RelationToTarget.EXACT_TARGET
    try:
        _validate_model_id(declared_model_id)
    except SourceBundleError:
        return RelationToTarget.UNKNOWN
    return RelationToTarget.BASE_MODEL


def _validate_declaration_statuses(declarations: Sequence[DeclarationRecord]) -> None:
    grouped: dict[str, list[DeclarationRecord]] = {}
    for declaration in declarations:
        grouped.setdefault(declaration.kind, []).append(declaration)
    for records in grouped.values():
        normalized = {item.value.strip().casefold() for item in records}
        if len(normalized) > 1:
            expected = DeclarationStatus.CONFLICT
        elif len(records) > 1:
            expected = DeclarationStatus.CONSISTENT
        else:
            expected = DeclarationStatus.DECLARED
        if any(item.status is not expected for item in records):
            raise BundleIntegrityError("declaration conflict status is inconsistent")


def _make_manifest(
    *,
    target: TargetIdentity,
    requested_revision: str | None,
    limits: CollectionLimits,
    sources: tuple[SourceRecord, ...],
    relations: tuple[RelationRecord, ...],
    declarations: tuple[DeclarationRecord, ...],
) -> BundleManifest:
    return BundleManifest(
        manifest_version=MANIFEST_VERSION,
        bundle_id=_bundle_id(
            target=target,
            requested_revision=requested_revision,
            limits=limits,
            sources=sources,
            relations=relations,
            declarations=declarations,
        ),
        target=target,
        requested_revision=requested_revision,
        limits=limits,
        sources=sources,
        relations=relations,
        declarations=declarations,
    )


def _bundle_id(
    *,
    target: TargetIdentity,
    requested_revision: str | None,
    limits: CollectionLimits,
    sources: Sequence[SourceRecord],
    relations: Sequence[RelationRecord],
    declarations: Sequence[DeclarationRecord],
) -> str:
    payload = {
        "manifest_version": MANIFEST_VERSION,
        "target": target.to_dict(),
        "requested_revision": requested_revision,
        "limits": limits.to_dict(),
        "sources": [item.to_dict() for item in sources],
        "relations": [item.to_dict() for item in relations],
        "declarations": [item.to_dict() for item in declarations],
    }
    return "hf_bundle_" + hashlib.sha256(_canonical_json(payload)).hexdigest()[:32]


def _atomic_write_bundle(
    destination: Path, manifest: BundleManifest, objects: Mapping[str, bytes]
) -> None:
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"bundle destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.tmp-", dir=str(destination.parent))
    )
    published = False
    try:
        for digest, content in sorted(objects.items()):
            if hashlib.sha256(content).hexdigest() != digest:
                raise SourceBundleError("collector object digest is inconsistent")
            path = temporary.joinpath(*PurePosixPath(_object_path(digest)).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            _write_file(path, content)
        _write_file(temporary / "manifest.json", _canonical_json(manifest.to_dict()))
        _fsync_directories(temporary)
        os.rename(temporary, destination)
        published = True
        parent_descriptor = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(parent_descriptor)
        finally:
            os.close(parent_descriptor)
    finally:
        if not published and temporary.exists():
            shutil.rmtree(temporary)


def _write_file(path: Path, content: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directories(root: Path) -> None:
    directories = [entry for entry in root.rglob("*") if entry.is_dir()]
    directories.append(root)
    for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _validate_model_id(model_id: Any) -> None:
    if not isinstance(model_id, str) or len(model_id) > 96 or model_id.count("/") != 1:
        raise SourceBundleError("model_id must be one namespace/name identifier")
    namespace, name = model_id.split("/")
    for part in (namespace, name):
        if (
            not _MODEL_PART_RE.fullmatch(part)
            or ".." in part
            or "--" in part
            or part in {".", ".."}
        ):
            raise SourceBundleError("model_id contains an invalid repository component")


def _validate_requested_revision(revision: Any) -> None:
    if revision is None:
        return
    if (
        not isinstance(revision, str)
        or not revision
        or len(revision) > 200
        or revision.strip() != revision
        or revision.startswith("/")
        or revision.endswith("/")
        or ".." in revision.split("/")
        or any(ord(character) < 32 or ord(character) == 127 for character in revision)
    ):
        raise SourceBundleError("requested revision is invalid")


def _validate_repo_path(path: Any) -> None:
    if (
        not isinstance(path, str)
        or not path
        or len(path) > 512
        or "\\" in path
        or any(ord(character) < 32 or ord(character) == 127 for character in path)
    ):
        raise SourceBundleError("repository path is invalid or unsafe")
    pure = PurePosixPath(path)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise SourceBundleError("repository path is invalid or unsafe")
    if pure.as_posix() != path:
        raise SourceBundleError("repository path is not canonical")


def _validate_bundle_relative_path(path: str) -> None:
    _validate_repo_path(path)
    if path != "manifest.json" and not path.startswith("objects/sha256/"):
        raise BundleIntegrityError("bundle contains a file outside the closed layout")


def _source_id(
    target: TargetIdentity, kind: SourceKind, repository_path: str | None
) -> str:
    payload = {
        "target": target.to_dict(),
        "kind": SourceKind(kind).value,
        "repository_path": repository_path,
    }
    return "src_" + hashlib.sha256(_canonical_json(payload)).hexdigest()[:24]


def _object_path(digest: str) -> str:
    if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
        raise BundleIntegrityError("content digest is invalid")
    return f"objects/sha256/{digest[:2]}/{digest}"


def _media_type(kind: SourceKind, repo_path: str | None) -> str:
    if kind in {SourceKind.MODEL_METADATA, SourceKind.CONFIG}:
        return "application/json"
    assert repo_path is not None
    suffix = PurePosixPath(repo_path).suffix.casefold()
    if suffix == ".json":
        return "application/json"
    if suffix == ".md":
        return "text/markdown"
    return "text/plain"


def _metadata_url(model_id: str, revision: str) -> str:
    return (
        "https://huggingface.co/api/models/"
        f"{quote(model_id, safe='/')}/revision/{quote(revision, safe='')}"
    )


def _file_url(model_id: str, revision: str, repo_path: str) -> str:
    return (
        f"https://huggingface.co/{quote(model_id, safe='/')}/resolve/"
        f"{quote(revision, safe='')}/{quote(repo_path, safe='/')}"
    )


def _expected_source_url(source: SourceRecord) -> str:
    return _expected_source_url_values(
        source.kind,
        source.repository_path,
        source.target_model_id,
        source.target_revision,
        source.retrieval,
    )


def _expected_source_url_values(
    kind: SourceKind,
    repository_path: str | None,
    model_id: str,
    revision: str,
    retrieval: RetrievalMode,
) -> str:
    if kind is SourceKind.MODEL_METADATA or retrieval is RetrievalMode.METADATA_FALLBACK:
        return _metadata_url(model_id, revision)
    assert repository_path is not None
    return _file_url(model_id, revision, repository_path)


def _strict_object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise BundleIntegrityError(f"{name} is not a closed object")
    return value


def _canonical_json(value: Any) -> bytes:
    try:
        encoded = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SourceBundleError("value is not finite JSON") from exc
    return encoded + b"\n"


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise BundleIntegrityError(f"JSON object contains duplicate key: {key}")
        value[key] = item
    return value


def _reject_nonfinite_json(value: str) -> None:
    raise BundleIntegrityError(f"JSON contains a non-finite number: {value}")


def _require_remote_object(value: Any, label: str) -> RemoteObject:
    if not isinstance(value, RemoteObject):
        raise SourceBundleError(f"adapter returned an invalid response for {label}")
    return value


def _is_portable_text(value: str) -> bool:
    return all(ord(character) >= 32 and ord(character) != 127 for character in value)


__all__ = [
    "BundleIntegrityError",
    "BundleManifest",
    "CollectionLimits",
    "CollectionStatus",
    "DeclarationRecord",
    "DeclarationStatus",
    "FetchStatus",
    "HuggingFaceSourceAdapter",
    "MANIFEST_VERSION",
    "RelationRecord",
    "RelationToTarget",
    "RemoteObject",
    "ReplayedSource",
    "ReplayedSourceBundle",
    "RetrievalMode",
    "RevisionResolutionError",
    "SourceBundleError",
    "SourceKind",
    "SourceRecord",
    "TargetIdentity",
    "collect_hf_source_bundle",
    "parse_target_request",
    "replay_source_bundle",
]
