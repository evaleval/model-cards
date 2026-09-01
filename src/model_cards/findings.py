"""Complete, field-scoped omission findings for composed Model Cards."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable

from .claim_gate import ClaimCandidate, ClaimGateRecord
from .composer import CompositionResult
from .schema import (
    CONTENT_FIELD_PATHS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    canonical_field_path,
    get_field,
)


OMISSION_AUDIT_VERSION = "complete-omission-audit/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")


class FindingError(ValueError):
    """Omission findings are incomplete, inconsistent, or stale."""


class OmissionReason(str, Enum):
    NOT_FOUND = "not_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    NOT_APPLICABLE = "not_applicable"
    CONFLICTING = "conflicting"
    WITHHELD = "withheld"
    MISSED_BY_COMPOSITION = "missed_by_composition"


class FieldAuditStatus(str, Enum):
    PRESENT = "present"
    OMITTED = "omitted"


class FieldAvailabilityStatus(str, Enum):
    SOURCE_PRESENT = "source_present"
    SOURCE_UNAVAILABLE = "source_unavailable"
    NOT_APPLICABLE = "not_applicable"
    SEARCHED_NOT_FOUND = "searched_not_found"


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
        raise FindingError("finding values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise FindingError(f"{label} has an invalid shape")
    return value


def _base_field(field_path: str) -> str:
    base = canonical_field_path(field_path)
    if base != field_path or base not in CONTENT_FIELD_PATHS:
        raise FindingError("availability and omission records require base content fields")
    return base


@dataclass(frozen=True)
class FieldAvailabilityHint:
    """Availability for one field only; never a global source excuse."""

    field_path: str
    status: FieldAvailabilityStatus
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_path", _base_field(self.field_path))
        try:
            object.__setattr__(self, "status", FieldAvailabilityStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise FindingError("field availability status is invalid") from exc
        source_ids = tuple(self.source_ids)
        if source_ids != tuple(sorted(set(source_ids))) or any(
            not isinstance(item, str) or not _SOURCE_ID_RE.fullmatch(item)
            for item in source_ids
        ):
            raise FindingError("field availability source_ids are invalid")
        if self.status is FieldAvailabilityStatus.SOURCE_PRESENT and not source_ids:
            raise FindingError("source_present availability requires a source id")
        object.__setattr__(self, "source_ids", source_ids)

    @property
    def content_sha256(self) -> str:
        return _digest(self._content_payload())

    def _content_payload(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "status": self.status.value,
            "source_ids": list(self.source_ids),
        }

    def to_dict(self) -> dict[str, Any]:
        return self._content_payload()

    @classmethod
    def from_dict(cls, value: Any) -> "FieldAvailabilityHint":
        item = _strict(
            value, {"field_path", "status", "source_ids"}, "field availability hint"
        )
        if not isinstance(item["source_ids"], list):
            raise FindingError("availability source_ids must be an array")
        return cls(
            field_path=item["field_path"],
            status=item["status"],
            source_ids=tuple(item["source_ids"]),
        )


@dataclass(frozen=True)
class FieldOmissionRecord:
    field_path: str
    status: FieldAuditStatus
    reason: OmissionReason | None
    source_present: bool
    candidate_ids: tuple[str, ...]
    included_candidate_ids: tuple[str, ...]
    conflict_sha256s: tuple[str, ...]
    availability_hint_sha256: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_path", _base_field(self.field_path))
        try:
            object.__setattr__(self, "status", FieldAuditStatus(self.status))
            if self.reason is not None:
                object.__setattr__(self, "reason", OmissionReason(self.reason))
        except (TypeError, ValueError) as exc:
            raise FindingError("field omission enum is invalid") from exc
        if not isinstance(self.source_present, bool):
            raise FindingError("field omission source_present must be boolean")
        if self.status is FieldAuditStatus.PRESENT and self.reason is not None:
            raise FindingError("present fields cannot have an omission reason")
        if self.status is FieldAuditStatus.OMITTED and self.reason is None:
            raise FindingError("omitted fields require a closed reason")
        for name in ("candidate_ids", "included_candidate_ids"):
            values = tuple(getattr(self, name))
            if values != tuple(sorted(set(values))) or any(
                not isinstance(item, str) or not _CANDIDATE_RE.fullmatch(item)
                for item in values
            ):
                raise FindingError(f"field omission {name} is invalid")
            object.__setattr__(self, name, values)
        if not set(self.included_candidate_ids) <= set(self.candidate_ids):
            raise FindingError("field omission included candidates are not field candidates")
        conflicts = tuple(self.conflict_sha256s)
        if conflicts != tuple(sorted(set(conflicts))) or any(
            not isinstance(item, str) or not _DIGEST_RE.fullmatch(item)
            for item in conflicts
        ):
            raise FindingError("field omission conflict digests are invalid")
        object.__setattr__(self, "conflict_sha256s", conflicts)
        if self.availability_hint_sha256 is not None and (
            not isinstance(self.availability_hint_sha256, str)
            or not _DIGEST_RE.fullmatch(self.availability_hint_sha256)
        ):
            raise FindingError("field omission availability digest is invalid")
        if self.candidate_ids and not self.source_present:
            raise FindingError("a field with candidates necessarily has source presence")
        if self.reason is OmissionReason.CONFLICTING and not conflicts:
            raise FindingError("conflicting omission requires explicit conflict records")

    @property
    def content_sha256(self) -> str:
        return _digest(self._content_payload())

    def _content_payload(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "status": self.status.value,
            "reason": self.reason.value if self.reason else None,
            "source_present": self.source_present,
            "candidate_ids": list(self.candidate_ids),
            "included_candidate_ids": list(self.included_candidate_ids),
            "conflict_sha256s": list(self.conflict_sha256s),
            "availability_hint_sha256": self.availability_hint_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "record_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "FieldOmissionRecord":
        item = _strict(
            value,
            {
                "field_path",
                "status",
                "reason",
                "source_present",
                "candidate_ids",
                "included_candidate_ids",
                "conflict_sha256s",
                "availability_hint_sha256",
                "record_sha256",
            },
            "field omission record",
        )
        if any(
            not isinstance(item[name], list)
            for name in ("candidate_ids", "included_candidate_ids", "conflict_sha256s")
        ):
            raise FindingError("field omission arrays are malformed")
        record = cls(
            field_path=item["field_path"],
            status=item["status"],
            reason=item["reason"],
            source_present=item["source_present"],
            candidate_ids=tuple(item["candidate_ids"]),
            included_candidate_ids=tuple(item["included_candidate_ids"]),
            conflict_sha256s=tuple(item["conflict_sha256s"]),
            availability_hint_sha256=item["availability_hint_sha256"],
        )
        if item["record_sha256"] != record.content_sha256:
            raise FindingError("field omission record digest mismatch")
        return record


@dataclass(frozen=True)
class OmissionAudit:
    composition_result_sha256: str
    candidate_inventory_sha256: str
    gate_inventory_sha256: str
    availability_sha256: str
    records: tuple[FieldOmissionRecord, ...]
    source_present_omissions: tuple[str, ...]
    audit_version: str = OMISSION_AUDIT_VERSION
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.audit_version != OMISSION_AUDIT_VERSION:
            raise FindingError("omission audit version is not recognized")
        for name in (
            "composition_result_sha256",
            "candidate_inventory_sha256",
            "gate_inventory_sha256",
            "availability_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
                raise FindingError(f"{name} is invalid")
        records = tuple(self.records)
        if not all(isinstance(item, FieldOmissionRecord) for item in records):
            raise FindingError("omission audit contains malformed field records")
        if tuple(item.field_path for item in records) != tuple(CONTENT_FIELD_PATHS):
            raise FindingError("omission audit must cover every schema content field exactly once")
        expected_present = tuple(
            item.field_path
            for item in records
            if item.status is FieldAuditStatus.OMITTED and item.source_present
        )
        if tuple(self.source_present_omissions) != expected_present:
            raise FindingError("source-present omission index is incomplete or stale")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "source_present_omissions", expected_present)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "audit_version": self.audit_version,
            "composition_result_sha256": self.composition_result_sha256,
            "candidate_inventory_sha256": self.candidate_inventory_sha256,
            "gate_inventory_sha256": self.gate_inventory_sha256,
            "availability_sha256": self.availability_sha256,
            "records": [item.to_dict() for item in self.records],
            "source_present_omissions": list(self.source_present_omissions),
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "audit_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "OmissionAudit":
        item = _strict(
            value,
            {
                "audit_version",
                "composition_result_sha256",
                "candidate_inventory_sha256",
                "gate_inventory_sha256",
                "availability_sha256",
                "records",
                "source_present_omissions",
                "audit_sha256",
            },
            "omission audit",
        )
        if not isinstance(item["records"], list) or not isinstance(
            item["source_present_omissions"], list
        ):
            raise FindingError("omission audit arrays are malformed")
        audit = cls(
            audit_version=item["audit_version"],
            composition_result_sha256=item["composition_result_sha256"],
            candidate_inventory_sha256=item["candidate_inventory_sha256"],
            gate_inventory_sha256=item["gate_inventory_sha256"],
            availability_sha256=item["availability_sha256"],
            records=tuple(FieldOmissionRecord.from_dict(x) for x in item["records"]),
            source_present_omissions=tuple(item["source_present_omissions"]),
        )
        if item["audit_sha256"] != audit.content_sha256:
            raise FindingError("omission audit digest mismatch")
        return audit


def audit_omissions(
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    composition_result: CompositionResult,
    availability_hints: Iterable[FieldAvailabilityHint] = (),
) -> OmissionAudit:
    """Classify every schema content field with field-scoped evidence state."""

    candidate_values = tuple(candidates)
    gate_values = tuple(gate_records)
    hints = tuple(availability_hints)
    if not isinstance(composition_result, CompositionResult):
        raise FindingError("omission audit requires a CompositionResult")
    if not all(isinstance(item, ClaimCandidate) for item in candidate_values):
        raise FindingError("omission candidate inventory is malformed")
    if not all(isinstance(item, ClaimGateRecord) for item in gate_values):
        raise FindingError("omission gate inventory is malformed")
    if not all(isinstance(item, FieldAvailabilityHint) for item in hints):
        raise FindingError("omission availability hints are malformed")
    candidates_by_id = {item.candidate_id: item for item in candidate_values}
    gates_by_id = {item.candidate.candidate_id: item for item in gate_values}
    if len(candidates_by_id) != len(candidate_values) or len(gates_by_id) != len(gate_values):
        raise FindingError("omission inventory contains duplicate records")
    if set(candidates_by_id) != set(gates_by_id):
        raise FindingError("omission candidate/gate inventory is incomplete")
    if set(candidates_by_id) != set(composition_result.plan.inventory_candidate_ids):
        raise FindingError("omission inventory differs from composition plan")
    for cid, candidate in candidates_by_id.items():
        if _canonical(candidate.to_dict()) != _canonical(gates_by_id[cid].candidate.to_dict()):
            raise FindingError("omission gate candidate differs from inventory")
    hint_by_field: dict[str, FieldAvailabilityHint] = {}
    for hint in hints:
        if hint.field_path in hint_by_field:
            raise FindingError("duplicate or ambiguous field availability hint")
        hint_by_field[hint.field_path] = hint
    candidate_by_base: dict[str, list[ClaimCandidate]] = {}
    for candidate in candidate_values:
        candidate_by_base.setdefault(canonical_field_path(candidate.field_path), []).append(
            candidate
        )
    conflict_by_base: dict[str, list[Any]] = {}
    for conflict in composition_result.plan.conflicts:
        conflict_by_base.setdefault(canonical_field_path(conflict.field_path), []).append(
            conflict
        )
    included = set(composition_result.plan.included_candidate_ids)
    eligible = set(composition_result.plan.eligible_candidate_ids)
    card = composition_result.card
    records = []
    for field_path in CONTENT_FIELD_PATHS:
        field_candidates = tuple(
            sorted(candidate_by_base.get(field_path, ()), key=lambda item: item.candidate_id)
        )
        candidate_ids = tuple(item.candidate_id for item in field_candidates)
        included_ids = tuple(sorted(set(candidate_ids) & included))
        hint = hint_by_field.get(field_path)
        conflicts = tuple(conflict_by_base.get(field_path, ()))
        conflict_hashes = tuple(sorted(item.content_sha256 for item in conflicts))
        source_present = bool(field_candidates) or (
            hint is not None and hint.status is FieldAvailabilityStatus.SOURCE_PRESENT
        )
        value = get_field(card, field_path)
        if value not in (NOT_SPECIFIED, NOT_APPLICABLE):
            status = FieldAuditStatus.PRESENT
            reason = None
        else:
            status = FieldAuditStatus.OMITTED
            if value == NOT_APPLICABLE:
                reason = OmissionReason.NOT_APPLICABLE
            elif conflicts:
                reason = OmissionReason.CONFLICTING
            elif set(candidate_ids) & (eligible - included):
                reason = OmissionReason.MISSED_BY_COMPOSITION
            elif candidate_ids:
                reason = OmissionReason.WITHHELD
            elif hint is not None and hint.status is FieldAvailabilityStatus.NOT_APPLICABLE:
                reason = OmissionReason.NOT_APPLICABLE
            elif hint is not None and hint.status is FieldAvailabilityStatus.SOURCE_UNAVAILABLE:
                reason = OmissionReason.SOURCE_UNAVAILABLE
            elif hint is not None and hint.status is FieldAvailabilityStatus.SOURCE_PRESENT:
                reason = OmissionReason.MISSED_BY_COMPOSITION
            else:
                reason = OmissionReason.NOT_FOUND
        records.append(
            FieldOmissionRecord(
                field_path=field_path,
                status=status,
                reason=reason,
                source_present=source_present,
                candidate_ids=candidate_ids,
                included_candidate_ids=included_ids,
                conflict_sha256s=conflict_hashes,
                availability_hint_sha256=hint.content_sha256 if hint else None,
            )
        )
    candidate_digest = _digest(
        [
            {"candidate_id": item.candidate_id, "sha256": item.content_sha256}
            for item in sorted(candidate_values, key=lambda item: item.candidate_id)
        ]
    )
    gate_digest = _digest(
        [
            {
                "candidate_id": item.candidate.candidate_id,
                "sha256": item.content_sha256,
            }
            for item in sorted(gate_values, key=lambda item: item.candidate.candidate_id)
        ]
    )
    availability_digest = _digest(
        [item.to_dict() for item in sorted(hints, key=lambda item: item.field_path)]
    )
    source_present_omissions = tuple(
        item.field_path
        for item in records
        if item.status is FieldAuditStatus.OMITTED and item.source_present
    )
    return OmissionAudit(
        composition_result_sha256=composition_result.content_sha256,
        candidate_inventory_sha256=candidate_digest,
        gate_inventory_sha256=gate_digest,
        availability_sha256=availability_digest,
        records=tuple(records),
        source_present_omissions=source_present_omissions,
    )


def verify_omission_audit(
    audit: OmissionAudit,
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    composition_result: CompositionResult,
    availability_hints: Iterable[FieldAvailabilityHint] = (),
) -> None:
    """Strictly replay a complete omission audit."""

    if not isinstance(audit, OmissionAudit):
        raise FindingError("omission replay requires an OmissionAudit")
    replayed = audit_omissions(
        candidates,
        gate_records,
        composition_result,
        availability_hints,
    )
    if _canonical(replayed.to_dict()) != _canonical(audit.to_dict()):
        raise FindingError("omission audit replay mismatch")


__all__ = [
    "OMISSION_AUDIT_VERSION",
    "FieldAuditStatus",
    "FieldAvailabilityHint",
    "FieldAvailabilityStatus",
    "FieldOmissionRecord",
    "FindingError",
    "OmissionAudit",
    "OmissionReason",
    "audit_omissions",
    "verify_omission_audit",
]
