"""One body-free catalog over a frozen Hub bundle and its official sources."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from types import MappingProxyType
from typing import Any, Mapping

from .models import SourceDocument, TargetIdentity
from .official_documents import OfficialDocumentCatalog
from .source_documents import SourceDocumentCatalog


COMBINED_CATALOG_VERSION = "combined-source-document-catalog/v1"


class CombinedSourceError(ValueError):
    """Hub and official catalogs do not describe one immutable target snapshot."""


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
        raise CombinedSourceError("combined source catalog is not finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class CombinedSourceDocumentCatalog:
    """Duck-compatible evidence catalog consumed by extraction and FactReasoner."""

    hf_catalog: SourceDocumentCatalog
    official_catalog: OfficialDocumentCatalog
    catalog_version: str = COMBINED_CATALOG_VERSION
    bundle_id: str = field(init=False)
    catalog_sha256: str = field(init=False)
    records: tuple[Any, ...] = field(init=False, repr=False)
    documents: tuple[SourceDocument, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.catalog_version != COMBINED_CATALOG_VERSION:
            raise CombinedSourceError("combined source catalog version is unsupported")
        if not isinstance(self.hf_catalog, SourceDocumentCatalog):
            raise CombinedSourceError("combined catalog requires a Hub catalog")
        if not isinstance(self.official_catalog, OfficialDocumentCatalog):
            raise CombinedSourceError("combined catalog requires an official catalog")
        if self.hf_catalog.target != self.official_catalog.target:
            raise CombinedSourceError("Hub and official targets differ")
        if self.official_catalog.source_bundle_id != self.hf_catalog.bundle_id:
            raise CombinedSourceError("official sources were discovered from another Hub bundle")

        records = tuple(
            sorted(
                (*self.hf_catalog.records, *self.official_catalog.records),
                key=lambda item: item.source_id,
            )
        )
        documents = tuple(
            sorted(
                (*self.hf_catalog.documents, *self.official_catalog.documents),
                key=lambda item: item.source_id,
            )
        )
        record_ids = [item.source_id for item in records]
        document_ids = [item.source_id for item in documents]
        if len(record_ids) != len(set(record_ids)):
            raise CombinedSourceError("combined catalog has duplicate source records")
        if len(document_ids) != len(set(document_ids)):
            raise CombinedSourceError("combined catalog has duplicate evidence documents")
        if any(item.target != self.target for item in documents):
            raise CombinedSourceError("combined evidence document target differs")
        loaded_ids = {
            item.source_id
            for item in records
            if getattr(getattr(item, "status", None), "value", None) == "loaded"
        }
        if set(document_ids) != loaded_ids:
            raise CombinedSourceError("combined loaded records and documents diverge")

        identity = {
            "catalog_version": self.catalog_version,
            "hf_bundle_id": self.hf_catalog.bundle_id,
            "hf_catalog_sha256": self.hf_catalog.catalog_sha256,
            "official_bundle_id": self.official_catalog.official_bundle_id,
            "official_catalog_sha256": self.official_catalog.catalog_sha256,
        }
        bundle_id = "combined_bundle_" + _digest(identity)[:32]
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "documents", documents)
        object.__setattr__(self, "bundle_id", bundle_id)
        object.__setattr__(self, "catalog_sha256", _digest(self._payload()))

    @property
    def target(self) -> TargetIdentity:
        return self.hf_catalog.target

    @property
    def by_id(self) -> Mapping[str, SourceDocument]:
        return MappingProxyType({item.source_id: item for item in self.documents})

    def _payload(self) -> dict[str, Any]:
        return {
            "catalog_version": self.catalog_version,
            "bundle_id": self.bundle_id,
            "target": self.target.to_dict(),
            "hf_catalog": self.hf_catalog.to_dict(),
            "official_catalog": self.official_catalog.to_dict(),
            "document_ids": [item.source_id for item in self.documents],
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize only portable identities and load outcomes, never source bodies."""

        return {**self._payload(), "catalog_sha256": self.catalog_sha256}

    def canonical_bytes(self) -> bytes:
        return _canonical(self.to_dict())


def combine_source_document_catalogs(
    hf_catalog: SourceDocumentCatalog,
    official_catalog: OfficialDocumentCatalog,
) -> CombinedSourceDocumentCatalog:
    return CombinedSourceDocumentCatalog(hf_catalog, official_catalog)


__all__ = [
    "COMBINED_CATALOG_VERSION",
    "CombinedSourceDocumentCatalog",
    "CombinedSourceError",
    "combine_source_document_catalogs",
]
