"""Strict conversion from a replayed source bundle to typed evidence inputs.

The source-bundle layer preserves bytes and collection failures.  This module is
the only bridge that interprets those bytes as UTF-8 text or strict JSON for the
binding and claim-gate layers.  Conversion is deliberately lossless with respect
to failures: every manifest source receives one immutable load record, including
missing, gated, unavailable, malformed, and empty inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

from .models import SourceDocument, SourceRole, TargetIdentity
from .source_bundle import (
    CollectionStatus,
    ReplayedSource,
    ReplayedSourceBundle,
    SourceKind,
)


CATALOG_VERSION = "source-document-catalog/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")


class SourceDocumentError(ValueError):
    """A replayed source cannot be interpreted without losing integrity."""


class SourceLoadStatus(str, Enum):
    LOADED = "loaded"
    MISSING = "missing"
    GATED = "gated"
    UNAVAILABLE = "unavailable"
    INVALID_UTF8 = "invalid_utf8"
    INVALID_JSON = "invalid_json"
    EMPTY = "empty"


@dataclass(frozen=True)
class SourceLoadRecord:
    """One closed conversion outcome for one manifest source."""

    source_id: str
    source_uri: str
    source_revision: str
    source_kind: str
    status: SourceLoadStatus
    reason_code: str
    source_sha256: str | None
    byte_size: int | None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "status", SourceLoadStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise SourceDocumentError("source load status is invalid") from exc
        if not isinstance(self.source_id, str) or not self.source_id:
            raise SourceDocumentError("source load record requires a source_id")
        if not isinstance(self.source_uri, str) or not self.source_uri.startswith("https://"):
            raise SourceDocumentError("source load record requires a portable HTTPS URI")
        if not isinstance(self.source_revision, str) or not self.source_revision:
            raise SourceDocumentError("source load record requires a revision")
        if not isinstance(self.source_kind, str) or not self.source_kind:
            raise SourceDocumentError("source load record requires a source kind")
        if not isinstance(self.reason_code, str) or not _REASON_RE.fullmatch(
            self.reason_code
        ):
            raise SourceDocumentError("source load reason_code is invalid")
        if self.source_sha256 is not None and (
            not isinstance(self.source_sha256, str)
            or not _DIGEST_RE.fullmatch(self.source_sha256)
        ):
            raise SourceDocumentError("source load digest is invalid")
        if self.byte_size is not None and (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size < 0
        ):
            raise SourceDocumentError("source load byte_size is invalid")
        if self.status is SourceLoadStatus.LOADED:
            if self.source_sha256 is None or self.byte_size is None:
                raise SourceDocumentError("loaded sources require digest and byte size")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "source_revision": self.source_revision,
            "source_kind": self.source_kind,
            "status": self.status.value,
            "reason_code": self.reason_code,
            "source_sha256": self.source_sha256,
            "byte_size": self.byte_size,
        }


@dataclass(frozen=True)
class SourceDocumentCatalog:
    """Typed evidence documents plus a complete per-source outcome ledger."""

    catalog_version: str
    bundle_id: str
    target: TargetIdentity
    records: tuple[SourceLoadRecord, ...]
    documents: tuple[SourceDocument, ...]
    catalog_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "documents", tuple(self.documents))
        if self.catalog_version != CATALOG_VERSION:
            raise SourceDocumentError("unsupported source document catalog version")
        if not isinstance(self.target, TargetIdentity):
            raise SourceDocumentError("source document catalog target is invalid")
        if not isinstance(self.bundle_id, str) or not self.bundle_id:
            raise SourceDocumentError("source document catalog bundle_id is invalid")
        record_ids = [item.source_id for item in self.records]
        document_ids = [item.source_id for item in self.documents]
        if len(record_ids) != len(set(record_ids)):
            raise SourceDocumentError("source document catalog has duplicate records")
        if len(document_ids) != len(set(document_ids)):
            raise SourceDocumentError("source document catalog has duplicate documents")
        loaded_ids = {
            item.source_id
            for item in self.records
            if item.status is SourceLoadStatus.LOADED
        }
        if set(document_ids) != loaded_ids:
            raise SourceDocumentError("loaded records and typed documents diverge")
        by_record = {item.source_id: item for item in self.records}
        for document in self.documents:
            record = by_record[document.source_id]
            if (
                document.source_uri != record.source_uri
                or document.source_revision != record.source_revision
                or document.sha256 != record.source_sha256
            ):
                raise SourceDocumentError("typed document identity diverges from load record")
            if document.target != self.target:
                raise SourceDocumentError("typed document target diverges from catalog target")
        expected = _catalog_digest(
            self.bundle_id,
            self.target,
            self.records,
            self.documents,
        )
        if self.catalog_sha256 != expected:
            raise SourceDocumentError("source document catalog digest is inconsistent")

    @property
    def by_id(self) -> Mapping[str, SourceDocument]:
        return MappingProxyType({item.source_id: item for item in self.documents})

    def to_dict(self) -> dict[str, Any]:
        """Serialize only the outcome catalog, never source bodies."""

        return {
            "catalog_version": self.catalog_version,
            "bundle_id": self.bundle_id,
            "target": self.target.to_dict(),
            "records": [item.to_dict() for item in self.records],
            "document_ids": [item.source_id for item in self.documents],
            "catalog_sha256": self.catalog_sha256,
        }


def build_source_document_catalog(
    bundle: ReplayedSourceBundle,
) -> SourceDocumentCatalog:
    """Interpret every replayed source without discarding failures or source bytes."""

    if not isinstance(bundle, ReplayedSourceBundle):
        raise SourceDocumentError("bundle must be a verified ReplayedSourceBundle")
    target = TargetIdentity(
        model_id=bundle.manifest.target.model_id,
        revision=bundle.manifest.target.revision,
    )
    records: list[SourceLoadRecord] = []
    documents: list[SourceDocument] = []
    for replayed in bundle.sources:
        record, document = _load_source(replayed, target)
        records.append(record)
        if document is not None:
            documents.append(document)
    records_tuple = tuple(records)
    documents_tuple = tuple(documents)
    digest = _catalog_digest(
        bundle.manifest.bundle_id,
        target,
        records_tuple,
        documents_tuple,
    )
    return SourceDocumentCatalog(
        catalog_version=CATALOG_VERSION,
        bundle_id=bundle.manifest.bundle_id,
        target=target,
        records=records_tuple,
        documents=documents_tuple,
        catalog_sha256=digest,
    )


def _load_source(
    replayed: ReplayedSource,
    target: TargetIdentity,
) -> tuple[SourceLoadRecord, SourceDocument | None]:
    source = replayed.record
    if source.status is not CollectionStatus.COLLECTED:
        status = SourceLoadStatus(source.status.value)
        return (
            _record(
                replayed,
                status,
                source.reason_code or f"collection_{status.value}",
            ),
            None,
        )
    content = replayed.content
    if content is None:
        raise SourceDocumentError("collected replay source is missing verified bytes")
    if (
        source.sha256 != hashlib.sha256(content).hexdigest()
        or source.byte_size != len(content)
    ):
        raise SourceDocumentError("replayed source bytes no longer match the manifest")
    if not content:
        return _record(replayed, SourceLoadStatus.EMPTY, "empty_source"), None

    role = (
        SourceRole.HUGGING_FACE_METADATA
        if source.kind is SourceKind.MODEL_METADATA
        else SourceRole.HUGGING_FACE_SNAPSHOT
    )
    common = {
        "source_id": source.source_id,
        "source_uri": source.source_url,
        "role": role,
        "source_revision": source.target_revision,
        "target": target,
        "synthetic": False,
        "content_sha256": source.sha256,
    }
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return _record(replayed, SourceLoadStatus.INVALID_UTF8, "invalid_utf8"), None
    if not text:
        return _record(replayed, SourceLoadStatus.EMPTY, "empty_source"), None

    if source.media_type == "application/json":
        try:
            data = json.loads(
                text,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except (json.JSONDecodeError, SourceDocumentError):
            return _record(replayed, SourceLoadStatus.INVALID_JSON, "invalid_json"), None
        document = SourceDocument(**common, data=data)
    elif source.media_type in {"text/markdown", "text/plain"}:
        document = SourceDocument(**common, text=text)
    else:  # Defensive against future manifest versions; v1 currently closes this set.
        raise SourceDocumentError(f"unsupported collected media type: {source.media_type}")
    return _record(replayed, SourceLoadStatus.LOADED, "loaded"), document


def _record(
    replayed: ReplayedSource,
    status: SourceLoadStatus,
    reason_code: str,
) -> SourceLoadRecord:
    source = replayed.record
    return SourceLoadRecord(
        source_id=source.source_id,
        source_uri=source.source_url,
        source_revision=source.target_revision,
        source_kind=source.kind.value,
        status=status,
        reason_code=reason_code,
        source_sha256=source.sha256,
        byte_size=source.byte_size,
    )


def _catalog_digest(
    bundle_id: str,
    target: TargetIdentity,
    records: tuple[SourceLoadRecord, ...],
    documents: tuple[SourceDocument, ...],
) -> str:
    # Source bodies stay out of the serialized catalog, but their already-verified
    # hashes and the interpretation mode bind the catalog to the exact bytes.
    modes = {
        document.source_id: "text" if document.text is not None else "json"
        for document in documents
    }
    value = {
        "catalog_version": CATALOG_VERSION,
        "bundle_id": bundle_id,
        "target": target.to_dict(),
        "records": [item.to_dict() for item in records],
        "document_modes": modes,
    }
    raw = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SourceDocumentError("source JSON contains a duplicate key")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise SourceDocumentError(f"source JSON contains a non-finite value: {value}")
