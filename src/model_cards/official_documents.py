"""Strict conversion of frozen official sources into typed evidence documents.

The official-source bundle establishes publisher authority, exact-target scope,
and immutable response bytes.  This module is the provider-free interpretation
boundary.  It produces one closed load record for every manifest source and an
in-memory :class:`~model_cards.models.SourceDocument` only when all authority,
collection, integrity, encoding, and media-type checks pass.

Source bodies are intentionally absent from every serialized catalog shape.
The catalog is instead bound to the original content digest, the deterministic
interpretation digest, and versioned HTML and PDF parser identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from html.parser import HTMLParser
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import parse_qsl, unquote, urlsplit

from .models import (
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from .official_discovery import OfficialSourceKind
from .official_sources import (
    CollectedOfficialSource,
    OfficialSourceStatus,
    RelationState,
    ReplayedOfficialSource,
    ReplayedOfficialSourceBundle,
    SourceAuthority,
    SourceRelation,
)
from .pdf_extraction import (
    PDF_EXTRACTOR_VERSION,
    PDF_PARSER_NAME,
    PDF_PARSER_VERSION,
    PdfExtractionLimits,
    PdfExtractionStatus,
    extract_pdf_text,
)


OFFICIAL_DOCUMENT_CATALOG_VERSION = "official-document-catalog/v2"
HTML_TEXT_PARSER_VERSION = "stdlib-html-visible-text/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_OFFICIAL_REVISION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_RELATION_ID_RE = re.compile(r"^source_relation_[0-9a-f]{24}$")
_SOURCE_ID_RE = re.compile(r"^primary_src_[0-9a-f]{24}$")
_MODEL_ID_RE = re.compile(
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?/"
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?$"
)


class OfficialDocumentError(ValueError):
    """A replayed official source cannot safely become evidence."""


class OfficialLoadStatus(str, Enum):
    """Closed interpretation outcome for one official manifest source."""

    LOADED = "loaded"
    MISSING = "missing"
    GATED = "gated"
    BLOCKED = "blocked"
    CONFLICTING = "conflicting"
    UNAVAILABLE = "unavailable"
    DISCOVERY_ONLY = "discovery_only"
    INVALID_UTF8 = "invalid_utf8"
    INVALID_JSON = "invalid_json"
    INVALID_HTML = "invalid_html"
    UNSAFE_TEXT = "unsafe_text"
    EMPTY = "empty"
    INVALID_PDF = "invalid_pdf"
    ENCRYPTED_PDF = "encrypted_pdf"
    IMAGE_ONLY_PDF = "image_only_pdf"
    PDF_LIMIT_EXCEEDED = "pdf_limit_exceeded"
    PDF_EXTRACTION_UNAVAILABLE = "pdf_extraction_unavailable"
    PDF_EXTRACTION_FAILED = "pdf_extraction_failed"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"


_RELATION_ADMISSION_REASONS = frozenset(
    {"related_source_not_exact_target", "relation_unresolved"}
)

_PDF_LOAD_STATUS_BY_EXTRACTION = MappingProxyType(
    {
        PdfExtractionStatus.EXTRACTED: OfficialLoadStatus.LOADED,
        PdfExtractionStatus.ENCRYPTED: OfficialLoadStatus.ENCRYPTED_PDF,
        PdfExtractionStatus.MALFORMED: OfficialLoadStatus.INVALID_PDF,
        PdfExtractionStatus.IMAGE_ONLY: OfficialLoadStatus.IMAGE_ONLY_PDF,
        PdfExtractionStatus.EMPTY: OfficialLoadStatus.EMPTY,
        PdfExtractionStatus.UNSAFE_TEXT: OfficialLoadStatus.UNSAFE_TEXT,
        PdfExtractionStatus.SOURCE_LIMIT: OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
        PdfExtractionStatus.PAGE_LIMIT: OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
        PdfExtractionStatus.TEXT_LIMIT: OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
        PdfExtractionStatus.TIME_LIMIT: OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
        PdfExtractionStatus.RESOURCE_LIMIT: OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
        PdfExtractionStatus.PARSER_UNAVAILABLE:
            OfficialLoadStatus.PDF_EXTRACTION_UNAVAILABLE,
        PdfExtractionStatus.ISOLATION_UNAVAILABLE:
            OfficialLoadStatus.PDF_EXTRACTION_UNAVAILABLE,
        PdfExtractionStatus.FAILED: OfficialLoadStatus.PDF_EXTRACTION_FAILED,
    }
)


def _relations_admit_exact_target(
    relations: tuple["OfficialRelationRecord", ...],
) -> bool:
    if len(relations) != 1:
        return False
    relation = relations[0]
    return (
        relation.state is RelationState.DECLARED
        and relation.relation_to_target is RelationToTarget.EXACT_TARGET
        and relation.subject_model_id == relation.target_model_id
    )


def _relation_admission_reason(
    relations: tuple["OfficialRelationRecord", ...],
) -> str:
    if (
        len(relations) != 1
        or any(item.state is not RelationState.DECLARED for item in relations)
        or any(
            item.relation_to_target is RelationToTarget.UNKNOWN
            for item in relations
        )
    ):
        return "relation_unresolved"
    return "related_source_not_exact_target"


class OfficialDocumentMode(str, Enum):
    TEXT = "text"
    JSON = "json"
    HTML_TEXT = "html_text"
    PDF_TEXT = "pdf_text"


@dataclass(frozen=True)
class OfficialRelationRecord:
    """Portable relation state associated with one official source."""

    relation_id: str
    subject_model_id: str
    target_model_id: str
    relation_to_target: RelationToTarget
    state: RelationState

    def __post_init__(self) -> None:
        if not isinstance(self.relation_id, str) or not _RELATION_ID_RE.fullmatch(
            self.relation_id
        ):
            raise OfficialDocumentError("official relation id is invalid")
        for name in ("subject_model_id", "target_model_id"):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or not value
                or len(value) > 256
                or not _portable_text(value)
            ):
                raise OfficialDocumentError(f"official relation {name} is invalid")
        if not _MODEL_ID_RE.fullmatch(self.target_model_id):
            raise OfficialDocumentError("official relation target_model_id is invalid")
        try:
            object.__setattr__(
                self,
                "relation_to_target",
                RelationToTarget(self.relation_to_target),
            )
            object.__setattr__(self, "state", RelationState(self.state))
        except (TypeError, ValueError) as exc:
            raise OfficialDocumentError(
                "official relation classification is invalid"
            ) from exc
        if (
            self.relation_to_target is RelationToTarget.EXACT_TARGET
            and self.subject_model_id != self.target_model_id
        ):
            raise OfficialDocumentError(
                "an exact official relation must identify the target"
            )
        if (
            self.state is RelationState.UNRESOLVED
            and self.relation_to_target is not RelationToTarget.UNKNOWN
        ):
            raise OfficialDocumentError(
                "only an unknown official relation can be unresolved"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "relation_id": self.relation_id,
            "subject_model_id": self.subject_model_id,
            "target_model_id": self.target_model_id,
            "relation_to_target": self.relation_to_target.value,
            "state": self.state.value,
        }


@dataclass(frozen=True)
class OfficialSourceLoadRecord:
    """One immutable, body-free outcome for one official manifest source."""

    source_id: str
    source_uri: str | None
    source_revision: str
    source_kind: OfficialSourceKind
    authority: SourceAuthority
    collection_status: OfficialSourceStatus
    status: OfficialLoadStatus
    collection_reason_code: str
    reason_code: str
    evidence_eligible: bool
    media_type: str | None
    source_sha256: str | None
    byte_size: int | None
    document_mode: OfficialDocumentMode | None
    rendered_sha256: str | None
    relations: tuple[OfficialRelationRecord, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "relations", tuple(self.relations))
        if not isinstance(self.source_id, str) or not _SOURCE_ID_RE.fullmatch(
            self.source_id
        ):
            raise OfficialDocumentError("official load source_id is invalid")
        if self.source_uri is not None:
            _validate_public_source_uri(self.source_uri)
        if not isinstance(self.source_revision, str) or (
            self.source_revision != "unresolved"
            and not _OFFICIAL_REVISION_RE.fullmatch(self.source_revision)
        ):
            raise OfficialDocumentError("official load revision is not immutable")
        try:
            object.__setattr__(
                self, "source_kind", OfficialSourceKind(self.source_kind)
            )
            object.__setattr__(self, "authority", SourceAuthority(self.authority))
            object.__setattr__(
                self,
                "collection_status",
                OfficialSourceStatus(self.collection_status),
            )
            object.__setattr__(self, "status", OfficialLoadStatus(self.status))
            if self.document_mode is not None:
                object.__setattr__(
                    self,
                    "document_mode",
                    OfficialDocumentMode(self.document_mode),
                )
        except (TypeError, ValueError) as exc:
            raise OfficialDocumentError(
                "official load classification is invalid"
            ) from exc
        for name in ("collection_reason_code", "reason_code"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _REASON_RE.fullmatch(value):
                raise OfficialDocumentError(f"official load {name} is invalid")
        if not isinstance(self.evidence_eligible, bool):
            raise OfficialDocumentError("official load eligibility must be boolean")
        if self.media_type is not None and (
            not isinstance(self.media_type, str)
            or not re.fullmatch(r"[a-z0-9.+-]+/[a-z0-9.+-]+", self.media_type)
        ):
            raise OfficialDocumentError("official load media type is invalid")
        for name in ("source_sha256", "rendered_sha256"):
            value = getattr(self, name)
            if value is not None and (
                not isinstance(value, str) or not _DIGEST_RE.fullmatch(value)
            ):
                raise OfficialDocumentError(f"official load {name} is invalid")
        if self.byte_size is not None and (
            isinstance(self.byte_size, bool)
            or not isinstance(self.byte_size, int)
            or self.byte_size < 0
        ):
            raise OfficialDocumentError("official load byte_size is invalid")
        if not all(isinstance(item, OfficialRelationRecord) for item in self.relations):
            raise OfficialDocumentError("official load relations are invalid")
        relation_ids = [item.relation_id for item in self.relations]
        if relation_ids != sorted(set(relation_ids)):
            raise OfficialDocumentError(
                "official load relations must be sorted and unique"
            )
        if any(item.target_model_id == "" for item in self.relations):
            raise OfficialDocumentError("official load relation target is empty")

        stored = self.source_sha256 is not None or self.byte_size is not None
        if stored and (self.source_sha256 is None or self.byte_size is None):
            raise OfficialDocumentError(
                "official load stored-byte metadata is incomplete"
            )
        expected_revision = (
            f"sha256:{self.source_sha256}" if stored else "unresolved"
        )
        if self.source_revision != expected_revision:
            raise OfficialDocumentError(
                "official load revision differs from its frozen byte state"
            )
        if self.collection_status in {
            OfficialSourceStatus.COLLECTED,
            OfficialSourceStatus.CONFLICTING,
        }:
            if not stored or self.source_uri is None or self.media_type is None:
                raise OfficialDocumentError(
                    "stored official collection state lacks immutable metadata"
                )
        elif stored or self.media_type is not None:
            raise OfficialDocumentError(
                "unstored official collection state claims response metadata"
            )

        expected_noncollected = {
            OfficialSourceStatus.MISSING: OfficialLoadStatus.MISSING,
            OfficialSourceStatus.GATED: OfficialLoadStatus.GATED,
            OfficialSourceStatus.BLOCKED: OfficialLoadStatus.BLOCKED,
            OfficialSourceStatus.CONFLICTING: OfficialLoadStatus.CONFLICTING,
            OfficialSourceStatus.UNAVAILABLE: OfficialLoadStatus.UNAVAILABLE,
            OfficialSourceStatus.DISCOVERY_ONLY: OfficialLoadStatus.DISCOVERY_ONLY,
        }
        expected = expected_noncollected.get(self.collection_status)
        if expected is not None and self.status is not expected:
            raise OfficialDocumentError(
                "official load status loses the collection outcome"
            )
        if self.collection_status is OfficialSourceStatus.COLLECTED:
            exact_target_admitted = _relations_admit_exact_target(self.relations)
            relation_blocked = (
                self.status is OfficialLoadStatus.BLOCKED
                and self.reason_code in _RELATION_ADMISSION_REASONS
            )
            if self.authority is not SourceAuthority.PRIMARY:
                raise OfficialDocumentError(
                    "collected official evidence must be verified primary authority"
                )
            if relation_blocked:
                if self.evidence_eligible or exact_target_admitted:
                    raise OfficialDocumentError(
                        "relation-blocked official source claims exact-target admission"
                    )
            elif not self.evidence_eligible or not exact_target_admitted:
                raise OfficialDocumentError(
                    "collected official evidence lacks a declared exact-target relation"
                )
            collected_outcomes = {
                OfficialLoadStatus.LOADED,
                OfficialLoadStatus.BLOCKED,
                OfficialLoadStatus.INVALID_UTF8,
                OfficialLoadStatus.INVALID_JSON,
                OfficialLoadStatus.INVALID_HTML,
                OfficialLoadStatus.UNSAFE_TEXT,
                OfficialLoadStatus.EMPTY,
                OfficialLoadStatus.INVALID_PDF,
                OfficialLoadStatus.ENCRYPTED_PDF,
                OfficialLoadStatus.IMAGE_ONLY_PDF,
                OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
                OfficialLoadStatus.PDF_EXTRACTION_UNAVAILABLE,
                OfficialLoadStatus.PDF_EXTRACTION_FAILED,
                OfficialLoadStatus.UNSUPPORTED_MEDIA_TYPE,
            }
            if self.status not in collected_outcomes:
                raise OfficialDocumentError(
                    "collected official source has an impossible load outcome"
                )
            if (
                self.status is OfficialLoadStatus.BLOCKED
                and not relation_blocked
            ):
                raise OfficialDocumentError(
                    "collected official source has an invalid blocked outcome"
                )
            pdf_only_outcomes = {
                OfficialLoadStatus.INVALID_PDF,
                OfficialLoadStatus.ENCRYPTED_PDF,
                OfficialLoadStatus.IMAGE_ONLY_PDF,
                OfficialLoadStatus.PDF_LIMIT_EXCEEDED,
                OfficialLoadStatus.PDF_EXTRACTION_UNAVAILABLE,
                OfficialLoadStatus.PDF_EXTRACTION_FAILED,
            }
            if (
                self.status in pdf_only_outcomes
                and self.media_type != "application/pdf"
            ):
                raise OfficialDocumentError(
                    "a PDF-only load outcome requires PDF source media"
                )
        elif self.evidence_eligible:
            raise OfficialDocumentError(
                "a non-collected official source cannot be evidence eligible"
            )

        if self.status is OfficialLoadStatus.LOADED:
            if self.document_mode is None or self.rendered_sha256 is None:
                raise OfficialDocumentError(
                    "loaded official sources require interpretation metadata"
                )
            expected_modes = {
                "application/json": OfficialDocumentMode.JSON,
                "text/html": OfficialDocumentMode.HTML_TEXT,
                "text/markdown": OfficialDocumentMode.TEXT,
                "text/plain": OfficialDocumentMode.TEXT,
                "application/pdf": OfficialDocumentMode.PDF_TEXT,
            }
            if expected_modes.get(self.media_type) is not self.document_mode:
                raise OfficialDocumentError(
                    "loaded official media type and interpretation mode diverge"
                )
        elif self.document_mode is not None or self.rendered_sha256 is not None:
            raise OfficialDocumentError(
                "unloaded official sources cannot claim a document interpretation"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "source_revision": self.source_revision,
            "source_kind": self.source_kind.value,
            "authority": self.authority.value,
            "collection_status": self.collection_status.value,
            "status": self.status.value,
            "collection_reason_code": self.collection_reason_code,
            "reason_code": self.reason_code,
            "evidence_eligible": self.evidence_eligible,
            "media_type": self.media_type,
            "source_sha256": self.source_sha256,
            "byte_size": self.byte_size,
            "document_mode": (
                None if self.document_mode is None else self.document_mode.value
            ),
            "rendered_sha256": self.rendered_sha256,
            "relations": [item.to_dict() for item in self.relations],
        }


@dataclass(frozen=True)
class OfficialDocumentCatalog:
    """Content-addressed official evidence catalog without serialized bodies."""

    catalog_version: str
    html_parser_version: str
    pdf_extractor_version: str
    pdf_parser_name: str
    pdf_parser_version: str
    pdf_extraction_limits: PdfExtractionLimits
    official_bundle_id: str
    source_bundle_id: str
    target: TargetIdentity
    records: tuple[OfficialSourceLoadRecord, ...]
    documents: tuple[SourceDocument, ...]
    catalog_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "records", tuple(self.records))
        object.__setattr__(self, "documents", tuple(self.documents))
        if self.catalog_version != OFFICIAL_DOCUMENT_CATALOG_VERSION:
            raise OfficialDocumentError("official document catalog version is unsupported")
        if self.html_parser_version != HTML_TEXT_PARSER_VERSION:
            raise OfficialDocumentError("official HTML parser version is unsupported")
        if self.pdf_extractor_version != PDF_EXTRACTOR_VERSION:
            raise OfficialDocumentError("official PDF extractor version is unsupported")
        if (
            self.pdf_parser_name != PDF_PARSER_NAME
            or self.pdf_parser_version != PDF_PARSER_VERSION
        ):
            raise OfficialDocumentError("official PDF parser identity is unsupported")
        if not isinstance(self.pdf_extraction_limits, PdfExtractionLimits):
            raise OfficialDocumentError("official PDF extraction limits are invalid")
        if not isinstance(self.official_bundle_id, str) or not re.fullmatch(
            r"official_bundle_[0-9a-f]{32}", self.official_bundle_id
        ):
            raise OfficialDocumentError("official document bundle id is invalid")
        if not isinstance(self.source_bundle_id, str) or not re.fullmatch(
            r"hf_bundle_[0-9a-f]{32}", self.source_bundle_id
        ):
            raise OfficialDocumentError("official catalog source bundle id is invalid")
        if not isinstance(self.target, TargetIdentity):
            raise OfficialDocumentError("official document target is invalid")
        if not all(isinstance(item, OfficialSourceLoadRecord) for item in self.records):
            raise OfficialDocumentError("official document records are invalid")
        if not all(isinstance(item, SourceDocument) for item in self.documents):
            raise OfficialDocumentError("official evidence documents are invalid")
        record_ids = [item.source_id for item in self.records]
        document_ids = [item.source_id for item in self.documents]
        if record_ids != sorted(set(record_ids)):
            raise OfficialDocumentError(
                "official document records must be sorted and unique"
            )
        if document_ids != sorted(set(document_ids)):
            raise OfficialDocumentError(
                "official evidence documents must be sorted and unique"
            )
        loaded_ids = {
            item.source_id
            for item in self.records
            if item.status is OfficialLoadStatus.LOADED
        }
        if set(document_ids) != loaded_ids:
            raise OfficialDocumentError(
                "loaded official records and evidence documents diverge"
            )
        by_record = {item.source_id: item for item in self.records}
        for record in self.records:
            if any(
                relation.target_model_id != self.target.model_id
                for relation in record.relations
            ):
                raise OfficialDocumentError(
                    "official load relation differs from the exact catalog target"
                )
        for document in self.documents:
            record = by_record[document.source_id]
            expected_role = _role_for_kind(record.source_kind)
            if (
                document.source_uri != record.source_uri
                or document.source_revision != record.source_revision
                or document.target != self.target
                or document.role is not expected_role
                or document.synthetic
                or document.content_sha256 != record.source_sha256
                or document.sha256 != record.source_sha256
                or _rendered_digest(document) != record.rendered_sha256
            ):
                raise OfficialDocumentError(
                    "official evidence document identity diverges from its load record"
                )
            expected_mode = (
                OfficialDocumentMode.JSON
                if document.data is not None
                else (
                    OfficialDocumentMode.HTML_TEXT
                    if record.media_type == "text/html"
                    else (
                        OfficialDocumentMode.PDF_TEXT
                        if record.media_type == "application/pdf"
                        else OfficialDocumentMode.TEXT
                    )
                )
            )
            if record.document_mode is not expected_mode:
                raise OfficialDocumentError(
                    "official document interpretation mode is inconsistent"
                )
        expected_digest = _catalog_digest(
            self.official_bundle_id,
            self.source_bundle_id,
            self.target,
            self.records,
            self.documents,
            html_parser_version=self.html_parser_version,
            pdf_extractor_version=self.pdf_extractor_version,
            pdf_parser_name=self.pdf_parser_name,
            pdf_parser_version=self.pdf_parser_version,
            pdf_extraction_limits=self.pdf_extraction_limits,
        )
        if self.catalog_sha256 != expected_digest:
            raise OfficialDocumentError(
                "official document catalog digest is inconsistent"
            )

    @property
    def by_id(self) -> Mapping[str, SourceDocument]:
        return MappingProxyType({item.source_id: item for item in self.documents})

    @property
    def records_by_id(self) -> Mapping[str, OfficialSourceLoadRecord]:
        return MappingProxyType({item.source_id: item for item in self.records})

    def to_dict(self) -> dict[str, Any]:
        """Return the portable body-free catalog representation."""

        return {
            "catalog_version": self.catalog_version,
            "html_parser_version": self.html_parser_version,
            "pdf_extractor_version": self.pdf_extractor_version,
            "pdf_parser_name": self.pdf_parser_name,
            "pdf_parser_version": self.pdf_parser_version,
            "pdf_extraction_limits": self.pdf_extraction_limits.to_dict(),
            "official_bundle_id": self.official_bundle_id,
            "source_bundle_id": self.source_bundle_id,
            "target": self.target.to_dict(),
            "records": [item.to_dict() for item in self.records],
            "document_ids": [item.source_id for item in self.documents],
            "catalog_sha256": self.catalog_sha256,
        }

    def canonical_bytes(self) -> bytes:
        """Serialize the public catalog deterministically, never with bodies."""

        OfficialDocumentCatalog(
            catalog_version=self.catalog_version,
            html_parser_version=self.html_parser_version,
            pdf_extractor_version=self.pdf_extractor_version,
            pdf_parser_name=self.pdf_parser_name,
            pdf_parser_version=self.pdf_parser_version,
            pdf_extraction_limits=self.pdf_extraction_limits,
            official_bundle_id=self.official_bundle_id,
            source_bundle_id=self.source_bundle_id,
            target=self.target,
            records=self.records,
            documents=self.documents,
            catalog_sha256=self.catalog_sha256,
        )
        return _canonical_json(self.to_dict())


def build_official_document_catalog(
    bundle: ReplayedOfficialSourceBundle,
    *,
    pdf_extraction_limits: PdfExtractionLimits | None = None,
) -> OfficialDocumentCatalog:
    """Interpret one strictly replayed official bundle without provider calls."""

    if not isinstance(bundle, ReplayedOfficialSourceBundle):
        raise OfficialDocumentError(
            "bundle must be a verified ReplayedOfficialSourceBundle"
        )
    active_pdf_limits = (
        PdfExtractionLimits()
        if pdf_extraction_limits is None
        else pdf_extraction_limits
    )
    if not isinstance(active_pdf_limits, PdfExtractionLimits):
        raise OfficialDocumentError(
            "pdf_extraction_limits must be PdfExtractionLimits"
        )
    _validate_replayed_bundle(bundle)
    target = TargetIdentity(
        model_id=bundle.manifest.target.model_id,
        revision=bundle.manifest.target.revision,
    )
    relations_by_source = _relations_by_source(bundle.manifest.relations)
    records: list[OfficialSourceLoadRecord] = []
    documents: list[SourceDocument] = []
    for replayed in bundle.sources:
        relations = relations_by_source.get(replayed.record.source_id, ())
        record, document = _load_official_source(
            replayed,
            target,
            relations,
            pdf_extraction_limits=active_pdf_limits,
        )
        records.append(record)
        if document is not None:
            documents.append(document)
    record_values = tuple(sorted(records, key=lambda item: item.source_id))
    document_values = tuple(sorted(documents, key=lambda item: item.source_id))
    digest = _catalog_digest(
        bundle.manifest.bundle_id,
        bundle.manifest.source_bundle_id,
        target,
        record_values,
        document_values,
        html_parser_version=HTML_TEXT_PARSER_VERSION,
        pdf_extractor_version=PDF_EXTRACTOR_VERSION,
        pdf_parser_name=PDF_PARSER_NAME,
        pdf_parser_version=PDF_PARSER_VERSION,
        pdf_extraction_limits=active_pdf_limits,
    )
    return OfficialDocumentCatalog(
        catalog_version=OFFICIAL_DOCUMENT_CATALOG_VERSION,
        html_parser_version=HTML_TEXT_PARSER_VERSION,
        pdf_extractor_version=PDF_EXTRACTOR_VERSION,
        pdf_parser_name=PDF_PARSER_NAME,
        pdf_parser_version=PDF_PARSER_VERSION,
        pdf_extraction_limits=active_pdf_limits,
        official_bundle_id=bundle.manifest.bundle_id,
        source_bundle_id=bundle.manifest.source_bundle_id,
        target=target,
        records=record_values,
        documents=document_values,
        catalog_sha256=digest,
    )


def serialize_official_document_catalog(
    catalog: OfficialDocumentCatalog,
) -> bytes:
    """Return canonical UTF-8 JSON for a verified body-free catalog."""

    if not isinstance(catalog, OfficialDocumentCatalog):
        raise OfficialDocumentError("catalog must be an OfficialDocumentCatalog")
    # ``canonical_bytes`` reconstructs the immutable catalog first so even
    # nested mutable JSON values cannot be altered after initial validation.
    return catalog.canonical_bytes()


def _validate_replayed_bundle(bundle: ReplayedOfficialSourceBundle) -> None:
    manifest_sources = tuple(bundle.manifest.sources)
    replayed_sources = tuple(bundle.sources)
    if len(manifest_sources) != len(replayed_sources):
        raise OfficialDocumentError(
            "official replay does not cover every manifest source exactly once"
        )
    for manifest_source, replayed in zip(manifest_sources, replayed_sources):
        if not isinstance(replayed, ReplayedOfficialSource):
            raise OfficialDocumentError("official replay contains an invalid source")
        if replayed.record != manifest_source:
            raise OfficialDocumentError(
                "official replay record order or identity differs from the manifest"
            )
        content = replayed.content
        if manifest_source.object_path is None:
            if content is not None:
                raise OfficialDocumentError(
                    "unstored official replay source contains unmanifested bytes"
                )
            continue
        if not isinstance(content, bytes):
            raise OfficialDocumentError(
                "stored official replay source is missing immutable bytes"
            )
        if (
            hashlib.sha256(content).hexdigest() != manifest_source.sha256
            or len(content) != manifest_source.byte_size
        ):
            raise OfficialDocumentError(
                "official replay bytes differ from the manifest digest or size"
            )


def _relations_by_source(
    relations: tuple[SourceRelation, ...],
) -> dict[str, tuple[OfficialRelationRecord, ...]]:
    values: dict[str, list[OfficialRelationRecord]] = {}
    for relation in relations:
        record = OfficialRelationRecord(
            relation_id=relation.relation_id,
            subject_model_id=relation.subject_model_id,
            target_model_id=relation.target_model_id,
            relation_to_target=relation.relation_to_target,
            state=relation.state,
        )
        values.setdefault(relation.source_id, []).append(record)
    return {
        source_id: tuple(sorted(items, key=lambda item: item.relation_id))
        for source_id, items in values.items()
    }


def _load_official_source(
    replayed: ReplayedOfficialSource,
    target: TargetIdentity,
    relations: tuple[OfficialRelationRecord, ...],
    *,
    pdf_extraction_limits: PdfExtractionLimits,
) -> tuple[OfficialSourceLoadRecord, SourceDocument | None]:
    source = replayed.record
    source_uri = source.final_url or source.requested_url
    noncollected = {
        OfficialSourceStatus.MISSING: OfficialLoadStatus.MISSING,
        OfficialSourceStatus.GATED: OfficialLoadStatus.GATED,
        OfficialSourceStatus.BLOCKED: OfficialLoadStatus.BLOCKED,
        OfficialSourceStatus.CONFLICTING: OfficialLoadStatus.CONFLICTING,
        OfficialSourceStatus.UNAVAILABLE: OfficialLoadStatus.UNAVAILABLE,
        OfficialSourceStatus.DISCOVERY_ONLY: OfficialLoadStatus.DISCOVERY_ONLY,
    }
    if source.status is not OfficialSourceStatus.COLLECTED:
        return (
            _make_record(
                source,
                target,
                relations,
                status=noncollected[source.status],
                reason_code=source.reason_code,
                document_mode=None,
                rendered_sha256=None,
            ),
            None,
        )
    if not _relations_admit_exact_target(relations):
        return (
            _make_record(
                source,
                target,
                relations,
                status=OfficialLoadStatus.BLOCKED,
                reason_code=_relation_admission_reason(relations),
                document_mode=None,
                rendered_sha256=None,
                evidence_eligible=False,
            ),
            None,
        )
    if (
        not source.evidence_eligible
        or source.authority is not SourceAuthority.PRIMARY
    ):
        # A valid v1 official manifest already forbids this state.  Keep the
        # interpretation boundary independently fail-closed for forged wrappers.
        raise OfficialDocumentError(
            "collected official bytes lack verified primary evidence authority"
        )
    content = replayed.content
    if not isinstance(content, bytes):
        raise OfficialDocumentError("collected official source has no replayed bytes")
    if not content:
        return (
            _make_record(
                source,
                target,
                relations,
                status=OfficialLoadStatus.EMPTY,
                reason_code="empty_source",
                document_mode=None,
                rendered_sha256=None,
            ),
            None,
        )
    if source.media_type == "application/pdf":
        extraction = extract_pdf_text(content, limits=pdf_extraction_limits)
        if (
            extraction.source_sha256 != source.sha256
            or extraction.source_byte_size != source.byte_size
        ):
            raise OfficialDocumentError(
                "PDF extraction input differs from the frozen official source"
            )
        if (
            extraction.extractor_version != PDF_EXTRACTOR_VERSION
            or extraction.parser_name != PDF_PARSER_NAME
            or extraction.parser_version != PDF_PARSER_VERSION
            or extraction.limits != pdf_extraction_limits
        ):
            raise OfficialDocumentError(
                "PDF extraction profile differs from the catalog binding"
            )
        load_status = _PDF_LOAD_STATUS_BY_EXTRACTION[extraction.status]
        if load_status is not OfficialLoadStatus.LOADED:
            return (
                _make_record(
                    source,
                    target,
                    relations,
                    status=load_status,
                    reason_code=extraction.reason_code,
                    document_mode=None,
                    rendered_sha256=None,
                ),
                None,
            )
        if extraction.text is None or extraction.output_sha256 is None:
            raise OfficialDocumentError(
                "successful PDF extraction lacks bound output text"
            )
        document = SourceDocument(
            source_id=source.source_id,
            source_uri=source_uri,
            role=_role_for_kind(source.kind),
            source_revision=f"sha256:{source.sha256}",
            target=target,
            text=extraction.text,
            synthetic=False,
            content_sha256=source.sha256,
        )
        if _rendered_digest(document) != extraction.output_sha256:
            raise OfficialDocumentError(
                "PDF extraction output differs from its recorded digest"
            )
        return (
            _make_record(
                source,
                target,
                relations,
                status=OfficialLoadStatus.LOADED,
                reason_code="loaded_pdf_text",
                document_mode=OfficialDocumentMode.PDF_TEXT,
                rendered_sha256=extraction.output_sha256,
            ),
            document,
        )
    if source.media_type not in {
        "application/json",
        "text/html",
        "text/markdown",
        "text/plain",
    }:
        return (
            _make_record(
                source,
                target,
                relations,
                status=OfficialLoadStatus.UNSUPPORTED_MEDIA_TYPE,
                reason_code="unsupported_media_type",
                document_mode=None,
                rendered_sha256=None,
            ),
            None,
        )
    try:
        text = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return (
            _make_record(
                source,
                target,
                relations,
                status=OfficialLoadStatus.INVALID_UTF8,
                reason_code="invalid_utf8",
                document_mode=None,
                rendered_sha256=None,
            ),
            None,
        )
    if not text:
        return (
            _make_record(
                source,
                target,
                relations,
                status=OfficialLoadStatus.EMPTY,
                reason_code="empty_source",
                document_mode=None,
                rendered_sha256=None,
            ),
            None,
        )

    common = {
        "source_id": source.source_id,
        "source_uri": source_uri,
        "role": _role_for_kind(source.kind),
        "source_revision": f"sha256:{source.sha256}",
        "target": target,
        "synthetic": False,
        "content_sha256": source.sha256,
    }
    document: SourceDocument
    mode: OfficialDocumentMode
    if source.media_type == "application/json":
        try:
            data = json.loads(
                text,
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite_constant,
            )
            _validate_finite_json(data)
            if data is None:
                raise OfficialDocumentError(
                    "top-level JSON null cannot become a typed source document"
                )
            _canonical_json(data)
        except (
            json.JSONDecodeError,
            OfficialDocumentError,
            RecursionError,
            TypeError,
            ValueError,
        ):
            return (
                _make_record(
                    source,
                    target,
                    relations,
                    status=OfficialLoadStatus.INVALID_JSON,
                    reason_code="invalid_json",
                    document_mode=None,
                    rendered_sha256=None,
                ),
                None,
            )
        document = SourceDocument(**common, data=data)
        mode = OfficialDocumentMode.JSON
    elif source.media_type == "text/html":
        unsafe_reason = _unsafe_text_reason(text)
        if unsafe_reason is not None:
            return (
                _make_record(
                    source,
                    target,
                    relations,
                    status=OfficialLoadStatus.UNSAFE_TEXT,
                    reason_code=unsafe_reason,
                    document_mode=None,
                    rendered_sha256=None,
                ),
                None,
            )
        try:
            rendered = _html_to_text(text)
        except OfficialDocumentError:
            return (
                _make_record(
                    source,
                    target,
                    relations,
                    status=OfficialLoadStatus.INVALID_HTML,
                    reason_code="invalid_html",
                    document_mode=None,
                    rendered_sha256=None,
                ),
                None,
            )
        if not rendered:
            return (
                _make_record(
                    source,
                    target,
                    relations,
                    status=OfficialLoadStatus.EMPTY,
                    reason_code="empty_html_text",
                    document_mode=None,
                    rendered_sha256=None,
                ),
                None,
            )
        document = SourceDocument(**common, text=rendered)
        mode = OfficialDocumentMode.HTML_TEXT
    else:
        unsafe_reason = _unsafe_text_reason(text)
        if unsafe_reason is not None:
            return (
                _make_record(
                    source,
                    target,
                    relations,
                    status=OfficialLoadStatus.UNSAFE_TEXT,
                    reason_code=unsafe_reason,
                    document_mode=None,
                    rendered_sha256=None,
                ),
                None,
            )
        if not text.strip():
            return (
                _make_record(
                    source,
                    target,
                    relations,
                    status=OfficialLoadStatus.EMPTY,
                    reason_code="empty_source",
                    document_mode=None,
                    rendered_sha256=None,
                ),
                None,
            )
        document = SourceDocument(**common, text=text)
        mode = OfficialDocumentMode.TEXT
    rendered_sha256 = _rendered_digest(document)
    return (
        _make_record(
            source,
            target,
            relations,
            status=OfficialLoadStatus.LOADED,
            reason_code="loaded",
            document_mode=mode,
            rendered_sha256=rendered_sha256,
        ),
        document,
    )


def _make_record(
    source: CollectedOfficialSource,
    target: TargetIdentity,
    relations: tuple[OfficialRelationRecord, ...],
    *,
    status: OfficialLoadStatus,
    reason_code: str,
    document_mode: OfficialDocumentMode | None,
    rendered_sha256: str | None,
    evidence_eligible: bool | None = None,
) -> OfficialSourceLoadRecord:
    return OfficialSourceLoadRecord(
        source_id=source.source_id,
        source_uri=source.final_url or source.requested_url,
        source_revision=(
            f"sha256:{source.sha256}"
            if source.sha256 is not None
            else "unresolved"
        ),
        source_kind=source.kind,
        authority=source.authority,
        collection_status=source.status,
        status=status,
        collection_reason_code=source.reason_code,
        reason_code=reason_code,
        evidence_eligible=(
            source.evidence_eligible
            if evidence_eligible is None
            else evidence_eligible
        ),
        media_type=source.media_type,
        source_sha256=source.sha256,
        byte_size=source.byte_size,
        document_mode=document_mode,
        rendered_sha256=rendered_sha256,
        relations=relations,
    )


def _role_for_kind(kind: OfficialSourceKind) -> SourceRole:
    return (
        SourceRole.DEVELOPER_CODE
        if kind is OfficialSourceKind.CODE
        else SourceRole.DEVELOPER_REPORT
    )


class _VisibleHTMLTextParser(HTMLParser):
    """Small deterministic parser that never executes or fetches HTML content."""

    _BLOCK_TAGS = frozenset(
        {
            "address",
            "article",
            "aside",
            "blockquote",
            "br",
            "dd",
            "div",
            "dl",
            "dt",
            "figcaption",
            "figure",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "hr",
            "li",
            "main",
            "nav",
            "ol",
            "p",
            "pre",
            "section",
            "table",
            "tbody",
            "td",
            "tfoot",
            "th",
            "thead",
            "tr",
            "ul",
        }
    )
    _SUPPRESSED_TAGS = frozenset(
        {"head", "iframe", "noscript", "script", "style", "template"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.suppressed: list[str] = []
        self.invalid = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        lowered = tag.casefold()
        if lowered in self._SUPPRESSED_TAGS:
            self.suppressed.append(lowered)
            return
        if not self.suppressed and lowered in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        lowered = tag.casefold()
        if not self.suppressed and lowered in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered in self._SUPPRESSED_TAGS:
            if not self.suppressed or self.suppressed[-1] != lowered:
                self.invalid = True
            else:
                self.suppressed.pop()
            return
        if not self.suppressed and lowered in self._BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.suppressed:
            self.parts.append(data)

    def handle_decl(self, decl: str) -> None:
        if not decl.strip().casefold().startswith("doctype html"):
            self.invalid = True

    def unknown_decl(self, data: str) -> None:
        self.invalid = True

    def handle_pi(self, data: str) -> None:
        self.invalid = True

    def rendered_text(self) -> str:
        if self.invalid or self.suppressed:
            raise OfficialDocumentError("HTML contains an unsafe or unclosed construct")
        raw = "".join(self.parts).replace("\r\n", "\n").replace("\r", "\n")
        lines = []
        for line in raw.split("\n"):
            normalized = re.sub(r"[\t\f\v ]+", " ", line).strip()
            if normalized:
                lines.append(normalized)
        return "\n".join(lines)


def _html_to_text(text: str) -> str:
    parser = _VisibleHTMLTextParser()
    try:
        parser.feed(text)
        parser.close()
        return parser.rendered_text()
    except (AssertionError, RecursionError, ValueError) as exc:
        raise OfficialDocumentError("HTML parsing failed") from exc


def _unsafe_text_reason(text: str) -> str | None:
    for character in text:
        codepoint = ord(character)
        if codepoint == 0 or codepoint == 127:
            return "unsafe_text_controls"
        if codepoint < 32 and character not in {"\t", "\n", "\r", "\f"}:
            return "unsafe_text_controls"
    return None


def _rendered_digest(document: SourceDocument) -> str:
    if document.text is not None:
        payload = document.text.encode("utf-8")
    else:
        payload = _canonical_json(document.data)
    return hashlib.sha256(payload).hexdigest()


def _catalog_digest(
    bundle_id: str,
    source_bundle_id: str,
    target: TargetIdentity,
    records: tuple[OfficialSourceLoadRecord, ...],
    documents: tuple[SourceDocument, ...],
    *,
    html_parser_version: str,
    pdf_extractor_version: str,
    pdf_parser_name: str,
    pdf_parser_version: str,
    pdf_extraction_limits: PdfExtractionLimits,
) -> str:
    value = {
        "catalog_version": OFFICIAL_DOCUMENT_CATALOG_VERSION,
        "html_parser_version": html_parser_version,
        "pdf_extractor_version": pdf_extractor_version,
        "pdf_parser_name": pdf_parser_name,
        "pdf_parser_version": pdf_parser_version,
        "pdf_extraction_limits": pdf_extraction_limits.to_dict(),
        "official_bundle_id": bundle_id,
        "source_bundle_id": source_bundle_id,
        "target": target.to_dict(),
        "records": [item.to_dict() for item in records],
        "document_ids": [item.source_id for item in documents],
    }
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise OfficialDocumentError("value is not finite canonical JSON") from exc


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OfficialDocumentError("official source JSON contains a duplicate key")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise OfficialDocumentError(
        f"official source JSON contains a non-finite constant: {value}"
    )


def _validate_finite_json(value: Any) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise OfficialDocumentError("official source JSON number is non-finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_finite_json(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise OfficialDocumentError("official source JSON key is not text")
            _validate_finite_json(item)
        return
    raise OfficialDocumentError("official source JSON has a non-JSON value")


def _portable_text(value: str) -> bool:
    return all(ord(character) >= 32 and ord(character) != 127 for character in value)


def _validate_public_source_uri(value: Any) -> None:
    if not isinstance(value, str) or any(character.isspace() for character in value):
        raise OfficialDocumentError("official load source_uri is not portable HTTPS")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError, UnicodeError):
        raise OfficialDocumentError(
            "official load source_uri is not portable HTTPS"
        ) from None
    host = (parsed.hostname or "").casefold().rstrip(".")
    decoded_path = unquote(parsed.path)
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.fragment
        or host in {"localhost", "127.0.0.1", "::1"}
        or "\\" in decoded_path
        or any(part in {".", ".."} for part in decoded_path.split("/"))
        or any(ord(character) < 32 or ord(character) == 127 for character in decoded_path)
    ):
        raise OfficialDocumentError("official load source_uri is not portable HTTPS")
    if parsed.query:
        parameters = parse_qsl(parsed.query, keep_blank_values=True)
        if (
            host != "openreview.net"
            or len(parameters) != 1
            or parameters[0][0] != "id"
            or not parameters[0][1]
        ):
            raise OfficialDocumentError(
                "official load source_uri contains an unsafe query"
            )


__all__ = [
    "HTML_TEXT_PARSER_VERSION",
    "OFFICIAL_DOCUMENT_CATALOG_VERSION",
    "PDF_EXTRACTOR_VERSION",
    "PDF_PARSER_NAME",
    "PDF_PARSER_VERSION",
    "OfficialDocumentCatalog",
    "OfficialDocumentError",
    "OfficialDocumentMode",
    "OfficialLoadStatus",
    "OfficialRelationRecord",
    "OfficialSourceLoadRecord",
    "PdfExtractionLimits",
    "build_official_document_catalog",
    "serialize_official_document_catalog",
]
