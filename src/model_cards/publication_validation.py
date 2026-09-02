"""Deterministic final-public-card withholding and omission accounting.

This module is intentionally independent of pipeline orchestration.  It binds
one FactReasoner record to the exact seven-section publication card it checked,
removes only fields that received the terminal ``repair_or_withhold`` action,
and accounts for all 33 agreed publication fields before and after that
withholding.  ``collect_or_withhold`` remains visible as an unavailable check;
it is not silently converted into a failed claim.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from .factreasoner import FactReasonerRecord, FieldAction
from .publication_contract import (
    FIELD_PATHS,
    FIELD_PATH_SET,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
)
from .publication_schema import (
    PUBLICATION_SCHEMA,
    get_field,
    validate_publication_card,
)


PUBLICATION_VALIDATION_VERSION = "publication-validation/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_MISSING = object()
_FIELD_ORDER = {field_path: index for index, field_path in enumerate(FIELD_PATHS)}


class PublicationValidationError(ValueError):
    """Publication validation inputs or records are inconsistent."""


class PublicationValidationReplayError(PublicationValidationError):
    """A publication validation report diverges from deterministic replay."""


class PublicationFieldReason(str, Enum):
    """Closed final-field outcomes for the publication omission audit."""

    PRESENT = "present"
    NOT_FOUND = "not_found"
    WITHHELD = "withheld"


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
        raise PublicationValidationError(
            "publication validation values must be finite JSON"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PublicationValidationError(f"{label} has an invalid shape")
    return value


def _require_digest(value: Any, label: str, *, optional: bool = False) -> None:
    if optional and value is None:
        return
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise PublicationValidationError(f"{label} is not a SHA-256 digest")


def _ordered_field_paths(values: Iterable[str]) -> tuple[str, ...]:
    paths = tuple(values)
    if any(not isinstance(item, str) or item not in FIELD_PATH_SET for item in paths):
        raise PublicationValidationError(
            "publication field paths must name agreed top-level fields"
        )
    if len(paths) != len(set(paths)):
        raise PublicationValidationError("publication field paths must be unique")
    return tuple(sorted(paths, key=_FIELD_ORDER.__getitem__))


def _raw_field(card: Mapping[str, Any], field_path: str) -> tuple[bool, Any]:
    section, field = field_path.split(".", 1)
    section_value = card[section]
    if field not in section_value:
        return False, _MISSING
    return True, section_value[field]


def _is_substantive(exists: bool, value: Any) -> bool:
    return exists and value not in (NOT_SPECIFIED, NOT_APPLICABLE)


def _value_digest(exists: bool, value: Any) -> str | None:
    return _digest(value) if exists else None


def _validate_publication_factreasoner_record(
    record: FactReasonerRecord,
    card: Mapping[str, Any] | None = None,
) -> None:
    if not isinstance(record, FactReasonerRecord):
        raise PublicationValidationError(
            "publication validation requires a typed FactReasoner record"
        )
    record.validate_integrity()
    if record.schema_sha256 != _digest(PUBLICATION_SCHEMA):
        raise PublicationValidationError(
            "FactReasoner record was not produced with the publication schema"
        )
    coverage_paths = tuple(item.field_path for item in record.field_coverage)
    if len(coverage_paths) != len(FIELD_PATHS) or set(coverage_paths) != FIELD_PATH_SET:
        raise PublicationValidationError(
            "FactReasoner record does not account for all 33 publication fields"
        )
    decision_paths = tuple(item.field_path for item in record.field_decisions)
    if any(item not in FIELD_PATH_SET for item in decision_paths):
        raise PublicationValidationError(
            "FactReasoner record contains a non-publication field decision"
        )
    if card is None:
        return
    validate_publication_card(card)
    if record.card_sha256 != _digest(card):
        raise PublicationValidationError(
            "FactReasoner record does not bind the pre-withhold publication card"
        )
    model_id = get_field(card, "identity.model_id", NOT_SPECIFIED)
    version = get_field(card, "identity.version", NOT_SPECIFIED)
    if model_id not in {NOT_SPECIFIED, NOT_APPLICABLE, record.target.model_id}:
        raise PublicationValidationError(
            "publication model_id differs from the FactReasoner target"
        )
    if version not in {NOT_SPECIFIED, NOT_APPLICABLE, record.target.revision}:
        raise PublicationValidationError(
            "publication version differs from the FactReasoner target"
        )


def repair_or_withhold_publication_fields(
    record: FactReasonerRecord,
) -> tuple[str, ...]:
    """Return publication fields with a material repair-or-withhold decision.

    Unavailable ``collect_or_withhold`` decisions are deliberately excluded so
    callers cannot silently turn missing validation capacity into a
    contradiction.
    """

    _validate_publication_factreasoner_record(record)
    return _ordered_field_paths(
        item.field_path
        for item in record.field_decisions
        if item.action is FieldAction.REPAIR_OR_WITHHOLD
    )


def remove_publication_fields(
    card: Mapping[str, Any],
    field_paths: Iterable[str],
) -> dict[str, dict[str, Any]]:
    """Remove the named substantive fields from a validated sparse card."""

    validate_publication_card(card)
    paths = _ordered_field_paths(field_paths)
    output = deepcopy(dict(card))
    for field_path in paths:
        section, field = field_path.split(".", 1)
        exists, value = _raw_field(output, field_path)
        if not _is_substantive(exists, value):
            raise PublicationValidationError(
                f"cannot withhold an absent publication field: {field_path}"
            )
        del output[section][field]
    validate_publication_card(output)
    return output


@dataclass(frozen=True)
class PublicationFieldAuditRecord:
    """One hash-bound field outcome in the 33-field publication audit."""

    field_path: str
    reason: PublicationFieldReason
    source_present: bool
    pre_withhold_value_sha256: str | None
    final_value_sha256: str | None
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.field_path not in FIELD_PATH_SET:
            raise PublicationValidationError("field audit path is not in the contract")
        try:
            object.__setattr__(self, "reason", PublicationFieldReason(self.reason))
        except (TypeError, ValueError) as exc:
            raise PublicationValidationError("field audit reason is invalid") from exc
        if not isinstance(self.source_present, bool):
            raise PublicationValidationError("field audit source_present must be boolean")
        _require_digest(
            self.pre_withhold_value_sha256,
            "pre-withhold field value digest",
            optional=True,
        )
        _require_digest(
            self.final_value_sha256,
            "final field value digest",
            optional=True,
        )
        if self.reason is PublicationFieldReason.PRESENT:
            if (
                not self.source_present
                or self.pre_withhold_value_sha256 is None
                or self.final_value_sha256 != self.pre_withhold_value_sha256
            ):
                raise PublicationValidationError(
                    "present field audit values are inconsistent"
                )
        elif self.reason is PublicationFieldReason.WITHHELD:
            if (
                not self.source_present
                or self.pre_withhold_value_sha256 is None
                or self.final_value_sha256 is not None
            ):
                raise PublicationValidationError(
                    "withheld field audit values are inconsistent"
                )
        elif (
            self.source_present
            or self.pre_withhold_value_sha256 != self.final_value_sha256
        ):
            raise PublicationValidationError(
                "not-found field audit values are inconsistent"
            )
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "reason": self.reason.value,
            "source_present": self.source_present,
            "pre_withhold_value_sha256": self.pre_withhold_value_sha256,
            "final_value_sha256": self.final_value_sha256,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "record_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "PublicationFieldAuditRecord":
        item = _strict(
            value,
            {
                "field_path",
                "reason",
                "source_present",
                "pre_withhold_value_sha256",
                "final_value_sha256",
                "record_sha256",
            },
            "publication field audit record",
        )
        record = cls(
            field_path=item["field_path"],
            reason=item["reason"],
            source_present=item["source_present"],
            pre_withhold_value_sha256=item["pre_withhold_value_sha256"],
            final_value_sha256=item["final_value_sha256"],
        )
        if item["record_sha256"] != record.content_sha256:
            raise PublicationValidationError(
                "publication field audit record digest mismatch"
            )
        return record


def audit_publication_fields(
    pre_withhold_card: Mapping[str, Any],
    final_card: Mapping[str, Any],
) -> tuple[PublicationFieldAuditRecord, ...]:
    """Account for every publication field after deletion-only withholding."""

    validate_publication_card(pre_withhold_card)
    validate_publication_card(final_card)
    records = []
    for field_path in FIELD_PATHS:
        pre_exists, pre_value = _raw_field(pre_withhold_card, field_path)
        final_exists, final_value = _raw_field(final_card, field_path)
        pre_substantive = _is_substantive(pre_exists, pre_value)
        final_substantive = _is_substantive(final_exists, final_value)

        if final_substantive:
            if not pre_substantive or _canonical(final_value) != _canonical(pre_value):
                raise PublicationValidationError(
                    f"final publication field was added or changed: {field_path}"
                )
            reason = PublicationFieldReason.PRESENT
            source_present = True
        elif pre_substantive:
            if final_exists:
                raise PublicationValidationError(
                    f"withheld publication field was replaced instead of removed: {field_path}"
                )
            reason = PublicationFieldReason.WITHHELD
            source_present = True
        else:
            if pre_exists != final_exists or (
                pre_exists and _canonical(pre_value) != _canonical(final_value)
            ):
                raise PublicationValidationError(
                    f"non-substantive publication field changed: {field_path}"
                )
            reason = PublicationFieldReason.NOT_FOUND
            source_present = False

        records.append(
            PublicationFieldAuditRecord(
                field_path=field_path,
                reason=reason,
                source_present=source_present,
                pre_withhold_value_sha256=_value_digest(pre_exists, pre_value),
                final_value_sha256=_value_digest(final_exists, final_value),
            )
        )
    return tuple(records)


@dataclass(frozen=True)
class PublicationValidationReport:
    """Replayable validation and omission report for one final public card."""

    pre_withhold_card_sha256: str
    final_card_sha256: str
    factreasoner_record_sha256: str
    records: tuple[PublicationFieldAuditRecord, ...]
    withheld_field_paths: tuple[str, ...]
    source_present_omissions: tuple[str, ...]
    schema_sha256: str = dataclass_field(default_factory=lambda: _digest(PUBLICATION_SCHEMA))
    report_version: str = PUBLICATION_VALIDATION_VERSION
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.report_version != PUBLICATION_VALIDATION_VERSION:
            raise PublicationValidationError(
                "publication validation report version is not recognized"
            )
        for value, label in (
            (self.schema_sha256, "publication schema digest"),
            (self.pre_withhold_card_sha256, "pre-withhold card digest"),
            (self.final_card_sha256, "final card digest"),
            (self.factreasoner_record_sha256, "FactReasoner record digest"),
        ):
            _require_digest(value, label)
        if self.schema_sha256 != _digest(PUBLICATION_SCHEMA):
            raise PublicationValidationError("publication schema digest is stale")

        records = tuple(self.records)
        if not all(isinstance(item, PublicationFieldAuditRecord) for item in records):
            raise PublicationValidationError(
                "publication validation report contains malformed field records"
            )
        if tuple(item.field_path for item in records) != FIELD_PATHS:
            raise PublicationValidationError(
                "publication validation report must cover all 33 fields in contract order"
            )
        withheld = _ordered_field_paths(self.withheld_field_paths)
        omissions = _ordered_field_paths(self.source_present_omissions)
        expected = tuple(
            item.field_path
            for item in records
            if item.reason is PublicationFieldReason.WITHHELD
        )
        if withheld != expected or omissions != expected:
            raise PublicationValidationError(
                "publication withholding and source-present omission indexes are stale"
            )
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "withheld_field_paths", withheld)
        object.__setattr__(self, "source_present_omissions", omissions)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "schema_sha256": self.schema_sha256,
            "pre_withhold_card_sha256": self.pre_withhold_card_sha256,
            "final_card_sha256": self.final_card_sha256,
            "factreasoner_record_sha256": self.factreasoner_record_sha256,
            "records": [item.to_dict() for item in self.records],
            "withheld_field_paths": list(self.withheld_field_paths),
            "source_present_omissions": list(self.source_present_omissions),
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def validate_integrity(self) -> None:
        if self._content_sha256 != _digest(self._content_payload()):
            raise PublicationValidationError(
                "publication validation report integrity failed"
            )

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "report_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "PublicationValidationReport":
        item = _strict(
            value,
            {
                "report_version",
                "schema_sha256",
                "pre_withhold_card_sha256",
                "final_card_sha256",
                "factreasoner_record_sha256",
                "records",
                "withheld_field_paths",
                "source_present_omissions",
                "report_sha256",
            },
            "publication validation report",
        )
        if not all(
            isinstance(item[name], list)
            for name in ("records", "withheld_field_paths", "source_present_omissions")
        ):
            raise PublicationValidationError(
                "publication validation report arrays are malformed"
            )
        report = cls(
            report_version=item["report_version"],
            schema_sha256=item["schema_sha256"],
            pre_withhold_card_sha256=item["pre_withhold_card_sha256"],
            final_card_sha256=item["final_card_sha256"],
            factreasoner_record_sha256=item["factreasoner_record_sha256"],
            records=tuple(
                PublicationFieldAuditRecord.from_dict(entry)
                for entry in item["records"]
            ),
            withheld_field_paths=tuple(item["withheld_field_paths"]),
            source_present_omissions=tuple(item["source_present_omissions"]),
        )
        if item["report_sha256"] != report.content_sha256:
            raise PublicationValidationError(
                "publication validation report digest mismatch"
            )
        return report


@dataclass(frozen=True)
class PublicationValidationOutcome:
    """The deletion-only final card and its replayable local report."""

    final_card: dict[str, dict[str, Any]]
    report: PublicationValidationReport
    _card_integrity_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.report, PublicationValidationReport):
            raise PublicationValidationError("publication outcome report is malformed")
        validate_publication_card(self.final_card)
        copied = deepcopy(self.final_card)
        if _digest(copied) != self.report.final_card_sha256:
            raise PublicationValidationError(
                "publication outcome card differs from its report"
            )
        object.__setattr__(self, "final_card", copied)
        object.__setattr__(self, "_card_integrity_sha256", _digest(copied))

    def validate_integrity(self) -> None:
        self.report.validate_integrity()
        if _digest(self.final_card) != self._card_integrity_sha256:
            raise PublicationValidationError("publication outcome card integrity failed")


def run_publication_validation(
    pre_withhold_card: Mapping[str, Any],
    factreasoner_record: FactReasonerRecord,
) -> PublicationValidationOutcome:
    """Apply a final public FactReasoner record without recomposition or I/O."""

    validate_publication_card(pre_withhold_card)
    _validate_publication_factreasoner_record(factreasoner_record, pre_withhold_card)
    withheld = repair_or_withhold_publication_fields(factreasoner_record)
    final_card = remove_publication_fields(pre_withhold_card, withheld)
    records = audit_publication_fields(pre_withhold_card, final_card)
    source_present_omissions = tuple(
        item.field_path
        for item in records
        if item.reason is PublicationFieldReason.WITHHELD
    )
    report = PublicationValidationReport(
        pre_withhold_card_sha256=_digest(pre_withhold_card),
        final_card_sha256=_digest(final_card),
        factreasoner_record_sha256=factreasoner_record.content_sha256,
        records=records,
        withheld_field_paths=withheld,
        source_present_omissions=source_present_omissions,
    )
    return PublicationValidationOutcome(final_card=final_card, report=report)


def replay_publication_validation(
    report: PublicationValidationReport,
    pre_withhold_card: Mapping[str, Any],
    factreasoner_record: FactReasonerRecord,
) -> PublicationValidationOutcome:
    """Recompute the report from frozen inputs and reject any divergence."""

    if not isinstance(report, PublicationValidationReport):
        raise PublicationValidationReplayError(
            "publication validation replay requires a typed report"
        )
    try:
        report.validate_integrity()
        replayed = run_publication_validation(
            pre_withhold_card, factreasoner_record
        )
    except PublicationValidationReplayError:
        raise
    except PublicationValidationError as exc:
        raise PublicationValidationReplayError(
            "publication validation replay inputs are inconsistent"
        ) from exc
    if replayed.report.to_dict() != report.to_dict():
        raise PublicationValidationReplayError(
            "publication validation replay diverged from the report"
        )
    return replayed


__all__ = [
    "PUBLICATION_VALIDATION_VERSION",
    "PublicationFieldAuditRecord",
    "PublicationFieldReason",
    "PublicationValidationError",
    "PublicationValidationOutcome",
    "PublicationValidationReplayError",
    "PublicationValidationReport",
    "audit_publication_fields",
    "remove_publication_fields",
    "repair_or_withhold_publication_fields",
    "replay_publication_validation",
    "run_publication_validation",
]
