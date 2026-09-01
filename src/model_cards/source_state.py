"""Shared immutable replay state for Hub and optional official source bundles.

The state object is the common boundary needed by provider orchestration and the
offline pipeline.  It retains typed in-memory documents for evidence processing,
but its serialized identity contains only portable identifiers, hashes, counts,
and target metadata.  Bundle paths and source bodies are never serialized or
shown in its representation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping

from .combined_sources import (
    CombinedSourceDocumentCatalog,
    combine_source_document_catalogs,
)
from .models import SourceDocument, TargetIdentity
from .official_documents import (
    OfficialDocumentCatalog,
    build_official_document_catalog,
)
from .official_sources import replay_official_sources
from .source_bundle import replay_source_bundle
from .source_documents import SourceDocumentCatalog, build_source_document_catalog


SOURCE_STATE_VERSION = "immutable-source-state/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class SourceStateError(RuntimeError):
    """A frozen source bundle, catalog, ancestry link, or replay has drifted."""


class SourceStateMode(str, Enum):
    HF_ONLY = "hf_only"
    HF_AND_OFFICIAL = "hf_and_official"


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
        raise SourceStateError("source-state identity must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _bundle_path(value: str | os.PathLike[str], label: str) -> Path:
    path = Path(value)
    if path.is_symlink() or not path.is_dir():
        raise SourceStateError(f"{label} bundle must be a real non-symlink directory")
    # Preserve the lexical location for later symlink-swap detection.  Resolving
    # it here would silently keep reading an old target after a path replacement.
    return Path(os.path.abspath(path))


def _combined_snapshot_digest(
    *,
    target: TargetIdentity,
    hf_bundle_id: str,
    hf_manifest_sha256: str,
    hf_catalog_sha256: str,
    official_bundle_id: str,
    official_manifest_sha256: str,
    official_catalog_sha256: str,
    combined_bundle_id: str,
    combined_catalog_sha256: str,
) -> str:
    return _digest(
        {
            "source_state_version": SOURCE_STATE_VERSION,
            "mode": SourceStateMode.HF_AND_OFFICIAL.value,
            "target": target.to_dict(),
            "hf": {
                "bundle_id": hf_bundle_id,
                "manifest_sha256": hf_manifest_sha256,
                "catalog_sha256": hf_catalog_sha256,
            },
            "official": {
                "bundle_id": official_bundle_id,
                "manifest_sha256": official_manifest_sha256,
                "catalog_sha256": official_catalog_sha256,
            },
            "combined": {
                "bundle_id": combined_bundle_id,
                "catalog_sha256": combined_catalog_sha256,
            },
        }
    )


@dataclass(frozen=True)
class ImmutableSourceState:
    """Typed source catalogs plus a body-free immutable replay identity."""

    mode: SourceStateMode
    target: TargetIdentity
    hf_bundle_id: str
    hf_manifest_sha256: str
    hf_catalog_sha256: str
    official_bundle_id: str | None
    official_manifest_sha256: str | None
    official_catalog_sha256: str | None
    active_catalog_bundle_id: str
    active_catalog_sha256: str
    snapshot_sha256: str
    hf_catalog: SourceDocumentCatalog = field(repr=False, compare=False)
    official_catalog: OfficialDocumentCatalog | None = field(
        repr=False, compare=False
    )
    combined_catalog: CombinedSourceDocumentCatalog | None = field(
        repr=False, compare=False
    )
    _hf_bundle_directory: Path = field(repr=False, compare=False)
    _official_bundle_directory: Path | None = field(repr=False, compare=False)
    state_version: str = SOURCE_STATE_VERSION

    def __post_init__(self) -> None:
        if self.state_version != SOURCE_STATE_VERSION:
            raise SourceStateError("source-state version is unsupported")
        try:
            mode = SourceStateMode(self.mode)
        except (TypeError, ValueError) as exc:
            raise SourceStateError("source-state mode is invalid") from exc
        object.__setattr__(self, "mode", mode)
        if not isinstance(self.target, TargetIdentity):
            raise SourceStateError("source-state target is invalid")
        if not isinstance(self.hf_catalog, SourceDocumentCatalog):
            raise SourceStateError("source-state Hub catalog is invalid")
        if self.hf_catalog.target != self.target:
            raise SourceStateError("source-state Hub catalog target differs")
        if self.hf_catalog.bundle_id != self.hf_bundle_id:
            raise SourceStateError("source-state Hub bundle identity differs")
        if self.hf_catalog.catalog_sha256 != self.hf_catalog_sha256:
            raise SourceStateError("source-state Hub catalog digest differs")
        for name in (
            "hf_manifest_sha256",
            "hf_catalog_sha256",
            "active_catalog_sha256",
            "snapshot_sha256",
        ):
            if not isinstance(getattr(self, name), str) or not _DIGEST_RE.fullmatch(
                getattr(self, name)
            ):
                raise SourceStateError(f"source-state {name} is invalid")
        if not isinstance(self.active_catalog_bundle_id, str) or not self.active_catalog_bundle_id:
            raise SourceStateError("source-state active catalog bundle identity is invalid")

        official_values = (
            self.official_bundle_id,
            self.official_manifest_sha256,
            self.official_catalog_sha256,
            self.official_catalog,
            self.combined_catalog,
            self._official_bundle_directory,
        )
        if mode is SourceStateMode.HF_ONLY:
            if any(item is not None for item in official_values):
                raise SourceStateError("HF-only state cannot contain official source identity")
            if (
                self.active_catalog_bundle_id != self.hf_bundle_id
                or self.active_catalog_sha256 != self.hf_catalog_sha256
                or self.snapshot_sha256 != self.hf_manifest_sha256
            ):
                raise SourceStateError("HF-only state is not backward compatible")
        else:
            if any(item is None for item in official_values):
                raise SourceStateError("combined state requires complete official identity")
            assert self.official_catalog is not None
            assert self.combined_catalog is not None
            assert self.official_bundle_id is not None
            assert self.official_manifest_sha256 is not None
            assert self.official_catalog_sha256 is not None
            if self.official_catalog.target != self.target:
                raise SourceStateError("official and Hub targets differ")
            if self.official_catalog.source_bundle_id != self.hf_bundle_id:
                raise SourceStateError("official bundle has another Hub-bundle ancestry")
            if (
                self.official_catalog.official_bundle_id != self.official_bundle_id
                or self.official_catalog.catalog_sha256
                != self.official_catalog_sha256
            ):
                raise SourceStateError("official catalog identity differs")
            if (
                self.combined_catalog.hf_catalog is not self.hf_catalog
                or self.combined_catalog.official_catalog is not self.official_catalog
                or self.combined_catalog.target != self.target
                or self.combined_catalog.bundle_id != self.active_catalog_bundle_id
                or self.combined_catalog.catalog_sha256 != self.active_catalog_sha256
            ):
                raise SourceStateError("combined catalog identity differs")
            expected_snapshot = _combined_snapshot_digest(
                target=self.target,
                hf_bundle_id=self.hf_bundle_id,
                hf_manifest_sha256=self.hf_manifest_sha256,
                hf_catalog_sha256=self.hf_catalog_sha256,
                official_bundle_id=self.official_bundle_id,
                official_manifest_sha256=self.official_manifest_sha256,
                official_catalog_sha256=self.official_catalog_sha256,
                combined_bundle_id=self.active_catalog_bundle_id,
                combined_catalog_sha256=self.active_catalog_sha256,
            )
            if self.snapshot_sha256 != expected_snapshot:
                raise SourceStateError("combined source snapshot digest differs")

        if not isinstance(self._hf_bundle_directory, Path):
            raise SourceStateError("source-state Hub replay location is invalid")
        if self._hf_bundle_directory.is_symlink():
            raise SourceStateError("source-state Hub replay location became a symlink")
        if self._official_bundle_directory is not None and (
            not isinstance(self._official_bundle_directory, Path)
            or self._official_bundle_directory.is_symlink()
        ):
            raise SourceStateError("source-state official replay location is invalid")

    @property
    def catalog(self) -> SourceDocumentCatalog | CombinedSourceDocumentCatalog:
        return self.hf_catalog if self.combined_catalog is None else self.combined_catalog

    @property
    def documents(self) -> tuple[SourceDocument, ...]:
        return self.catalog.documents

    @property
    def records(self) -> tuple[Any, ...]:
        return self.catalog.records

    @property
    def by_id(self) -> Mapping[str, SourceDocument]:
        return self.catalog.by_id

    def to_dict(self) -> dict[str, Any]:
        """Return portable replay identity only; never bodies or local paths."""

        return {
            "source_state_version": self.state_version,
            "mode": self.mode.value,
            "target": self.target.to_dict(),
            "hf_bundle_id": self.hf_bundle_id,
            "hf_manifest_sha256": self.hf_manifest_sha256,
            "hf_catalog_sha256": self.hf_catalog_sha256,
            "official_bundle_id": self.official_bundle_id,
            "official_manifest_sha256": self.official_manifest_sha256,
            "official_catalog_sha256": self.official_catalog_sha256,
            "active_catalog_version": self.catalog.catalog_version,
            "active_catalog_bundle_id": self.active_catalog_bundle_id,
            "active_catalog_sha256": self.active_catalog_sha256,
            "record_count": len(self.records),
            "document_count": len(self.documents),
            "snapshot_sha256": self.snapshot_sha256,
        }

    def reverify(self) -> "ImmutableSourceState":
        return reverify_source_state(self)


def _load_once(
    hf_bundle_directory: str | os.PathLike[str],
    official_bundle_directory: str | os.PathLike[str] | None,
) -> ImmutableSourceState:
    hf_path = _bundle_path(hf_bundle_directory, "Hugging Face")
    hf_bundle = replay_source_bundle(hf_path)
    hf_catalog = build_source_document_catalog(hf_bundle)
    hf_manifest_sha256 = _digest(hf_bundle.manifest.to_dict())

    if official_bundle_directory is None:
        return ImmutableSourceState(
            mode=SourceStateMode.HF_ONLY,
            target=hf_catalog.target,
            hf_bundle_id=hf_catalog.bundle_id,
            hf_manifest_sha256=hf_manifest_sha256,
            hf_catalog_sha256=hf_catalog.catalog_sha256,
            official_bundle_id=None,
            official_manifest_sha256=None,
            official_catalog_sha256=None,
            active_catalog_bundle_id=hf_catalog.bundle_id,
            active_catalog_sha256=hf_catalog.catalog_sha256,
            snapshot_sha256=hf_manifest_sha256,
            hf_catalog=hf_catalog,
            official_catalog=None,
            combined_catalog=None,
            _hf_bundle_directory=hf_path,
            _official_bundle_directory=None,
        )

    official_path = _bundle_path(official_bundle_directory, "official")
    official_bundle = replay_official_sources(official_path)
    if official_bundle.manifest.target != hf_bundle.manifest.target:
        raise SourceStateError("official and Hugging Face bundle targets differ")
    if official_bundle.manifest.source_bundle_id != hf_bundle.manifest.bundle_id:
        raise SourceStateError("official bundle was discovered from another Hub bundle")
    official_catalog = build_official_document_catalog(official_bundle)
    combined_catalog = combine_source_document_catalogs(hf_catalog, official_catalog)
    official_manifest_sha256 = _digest(official_bundle.manifest.to_dict())
    snapshot_sha256 = _combined_snapshot_digest(
        target=hf_catalog.target,
        hf_bundle_id=hf_catalog.bundle_id,
        hf_manifest_sha256=hf_manifest_sha256,
        hf_catalog_sha256=hf_catalog.catalog_sha256,
        official_bundle_id=official_catalog.official_bundle_id,
        official_manifest_sha256=official_manifest_sha256,
        official_catalog_sha256=official_catalog.catalog_sha256,
        combined_bundle_id=combined_catalog.bundle_id,
        combined_catalog_sha256=combined_catalog.catalog_sha256,
    )
    return ImmutableSourceState(
        mode=SourceStateMode.HF_AND_OFFICIAL,
        target=hf_catalog.target,
        hf_bundle_id=hf_catalog.bundle_id,
        hf_manifest_sha256=hf_manifest_sha256,
        hf_catalog_sha256=hf_catalog.catalog_sha256,
        official_bundle_id=official_catalog.official_bundle_id,
        official_manifest_sha256=official_manifest_sha256,
        official_catalog_sha256=official_catalog.catalog_sha256,
        active_catalog_bundle_id=combined_catalog.bundle_id,
        active_catalog_sha256=combined_catalog.catalog_sha256,
        snapshot_sha256=snapshot_sha256,
        hf_catalog=hf_catalog,
        official_catalog=official_catalog,
        combined_catalog=combined_catalog,
        _hf_bundle_directory=hf_path,
        _official_bundle_directory=official_path,
    )


def load_source_state(
    hf_bundle_directory: str | os.PathLike[str],
    official_bundle_directory: str | os.PathLike[str] | None = None,
) -> ImmutableSourceState:
    """Strictly replay and interpret one HF bundle plus optional official bundle."""

    try:
        return _load_once(hf_bundle_directory, official_bundle_directory)
    except SourceStateError:
        raise
    except Exception as exc:
        raise SourceStateError("immutable source-state replay failed closed") from exc


def reverify_source_state(state: ImmutableSourceState) -> ImmutableSourceState:
    """Replay both original bundle paths and reject any identity or content drift."""

    if not isinstance(state, ImmutableSourceState):
        raise SourceStateError("source-state reverification requires a typed state")
    current = load_source_state(
        state._hf_bundle_directory,
        state._official_bundle_directory,
    )
    if current.to_dict() != state.to_dict():
        raise SourceStateError("immutable source state has drifted")
    return current


__all__ = [
    "SOURCE_STATE_VERSION",
    "ImmutableSourceState",
    "SourceStateError",
    "SourceStateMode",
    "load_source_state",
    "reverify_source_state",
]
