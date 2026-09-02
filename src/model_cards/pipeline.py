"""Offline, replayable end-to-end Model Card generation kernel.

The kernel starts only from a verified frozen source bundle.  Paid/provider
work is deliberately outside this module: normalized quote batches and checker
decisions are injected, so rerunning the pipeline cannot create another paid
call.  Detailed evidence remains in local run artifacts; the immutable result
contains only identifiers, hashes, counts, and safe relative filenames.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field, replace
from enum import Enum
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterable, Mapping, Protocol, Sequence

from .artifact import CardArtifact, project_card
from .bindings import binding_id_for
from .claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    GateName,
    ProseCheckerDecision,
    evaluate_claim_gate,
)
from .composer import (
    CompositionDerivation,
    CompositionPlan,
    CompositionResult,
    EvidenceOnlyWriter,
    SelectAllEvidenceWriter,
    WriterInput,
    WriterSelection,
    compose_model_card,
)
from .extraction import (
    EXTRACTION_VERSION,
    ExtractionBatch,
    ExtractionResult,
    deterministic_structured_candidates,
    materialize_quote_batch,
)
from .factreasoner import (
    CheckOutcome,
    CheckRequest,
    CheckerResponse,
    FactChecker,
    FactReasonerRecord,
    FieldAction,
    FieldCoverageStatus,
    RetrievalConfig,
    SourceAvailability,
    run_factreasoner,
)
from .field_repair import (
    FieldRepairRecord,
    RepairOutcome,
    run_field_repair,
)
from .findings import (
    FieldAuditStatus,
    FieldAvailabilityHint,
    FieldAvailabilityStatus,
    FieldOmissionRecord,
    OmissionAudit,
    OmissionReason,
    audit_omissions,
)
from .models import (
    Binding,
    BindingOrigin,
    DerivationClaimInput,
    Disposition,
    EvidenceKind,
    LifecycleStatus,
    TargetIdentity,
    TaxonomyRiskDerivation,
    ValidationCheck,
    ValidationCheckStatus,
)
from .policy import decide_binding
from .public_export import PublicExportError, assert_public_projection
from .risk_mapping import (
    ApplicabilityChecker,
    ApplicabilityStatus,
    MappingStatus,
    RiskCatalog,
    RiskDetector,
    RiskMappingError,
    RiskMappingReport,
    UseContext,
    load_pinned_nexus_catalog,
    map_candidate_risks,
    unavailable_risk_report,
)
from .run_state import RunManifest, RunStateError, RunStore
from .schema import (
    CONTENT_FIELD_PATHS,
    CONTRACT_SCHEMA,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    canonical_field_path,
    get_field,
    parse_field_path,
    validate_public_card,
)
from .source_state import SourceStateMode, load_source_state


PIPELINE_VERSION = "offline-model-card-pipeline/v5"
PRIVACY_SCAN_VERSION = "public-card-privacy-scan/v1"
RISK_STAGE_VERSION = "pipeline-risk-stage/v1"
REPAIR_STAGE_VERSION = "pipeline-fact-withholding/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_RUN_RE = re.compile(r"^model_card_run_[0-9a-f]{24}$")
_CARD_RE = re.compile(r"^card_[0-9a-f]{24}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_CONTEXT_FIELDS = frozenset(
    {"use_and_risk.intended_uses", "use_and_risk.out_of_scope_uses"}
)


class PipelineError(RuntimeError):
    """The offline pipeline input, replay state, or output is inconsistent."""


class CompositionStatus(str, Enum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"


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
        raise PipelineError("pipeline values must be finite JSON") from exc


def _canonical_file(value: Any) -> bytes:
    return _canonical(value) + b"\n"


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _file_digest(value: Any) -> str:
    return hashlib.sha256(_canonical_file(value)).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise PipelineError(f"{label} has an invalid closed shape")
    return value


def _require_digest(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise PipelineError(f"{label} is not a SHA-256 digest")
    return value


@dataclass(frozen=True)
class ClaimPipelineReference:
    candidate_id: str
    candidate_sha256: str
    gate_record_sha256: str
    projection_eligible: bool
    included: bool

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CLAIM_RE.fullmatch(
            self.candidate_id
        ):
            raise PipelineError("pipeline claim identifier is invalid")
        _require_digest(self.candidate_sha256, "candidate_sha256")
        _require_digest(self.gate_record_sha256, "gate_record_sha256")
        if not isinstance(self.projection_eligible, bool) or not isinstance(
            self.included, bool
        ):
            raise PipelineError("pipeline claim flags must be boolean")
        if self.included and not self.projection_eligible:
            raise PipelineError("an ineligible claim cannot be included")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_sha256": self.candidate_sha256,
            "gate_record_sha256": self.gate_record_sha256,
            "projection_eligible": self.projection_eligible,
            "included": self.included,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ClaimPipelineReference":
        return cls(
            **_strict(
                value,
                {
                    "candidate_id",
                    "candidate_sha256",
                    "gate_record_sha256",
                    "projection_eligible",
                    "included",
                },
                "pipeline claim reference",
            )
        )


@dataclass(frozen=True)
class PersistedArtifactReference:
    stage: str
    logical_id: str
    status: str
    reason: str
    filename: str
    artifact_sha256: str

    def __post_init__(self) -> None:
        for label, value in (
            ("stage", self.stage),
            ("logical_id", self.logical_id),
            ("reason", self.reason),
        ):
            if not isinstance(value, str) or not _CODE_RE.fullmatch(value):
                raise PipelineError(f"persisted artifact {label} is invalid")
        if self.status not in {"completed", "unavailable", "withheld", "failed"}:
            raise PipelineError("persisted artifact status is invalid")
        if (
            not isinstance(self.filename, str)
            or PurePosixPath(self.filename).name != self.filename
            or self.filename in {"", ".", ".."}
            or "\\" in self.filename
        ):
            raise PipelineError("persisted artifact filename is unsafe")
        _require_digest(self.artifact_sha256, "persisted artifact digest")

    def to_dict(self) -> dict[str, str]:
        return {
            "stage": self.stage,
            "logical_id": self.logical_id,
            "status": self.status,
            "reason": self.reason,
            "filename": self.filename,
            "artifact_sha256": self.artifact_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PersistedArtifactReference":
        return cls(
            **_strict(
                value,
                {
                    "stage",
                    "logical_id",
                    "status",
                    "reason",
                    "filename",
                    "artifact_sha256",
                },
                "persisted artifact reference",
            )
        )


@dataclass(frozen=True)
class PrivacyScanReport:
    scanned_card_sha256: str
    checked: int
    passed: int
    withheld_candidate_ids: tuple[str, ...]
    status: str
    reason: str
    report_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        _require_digest(self.scanned_card_sha256, "privacy scanned card digest")
        if (
            not isinstance(self.checked, int)
            or isinstance(self.checked, bool)
            or not isinstance(self.passed, int)
            or isinstance(self.passed, bool)
            or self.checked < 1
            or self.passed < 0
            or self.passed > self.checked
        ):
            raise PipelineError("privacy scan counts are invalid")
        values = tuple(self.withheld_candidate_ids)
        if values != tuple(sorted(set(values))) or any(
            not isinstance(item, str) or not _CLAIM_RE.fullmatch(item) for item in values
        ):
            raise PipelineError("privacy withheld candidate identifiers are invalid")
        if self.status not in {"completed", "failed"}:
            raise PipelineError("privacy scan status is invalid")
        if not isinstance(self.reason, str) or not _CODE_RE.fullmatch(self.reason):
            raise PipelineError("privacy scan reason is invalid")
        if self.status == "completed" and self.passed + len(values) != self.checked:
            raise PipelineError("privacy scan outcomes are incomplete")
        object.__setattr__(self, "withheld_candidate_ids", values)
        object.__setattr__(self, "report_sha256", _digest(self._payload()))

    @property
    def passed_without_withholding(self) -> bool:
        return self.status == "completed" and not self.withheld_candidate_ids

    def _payload(self) -> dict[str, Any]:
        return {
            "privacy_version": PRIVACY_SCAN_VERSION,
            "scanned_card_sha256": self.scanned_card_sha256,
            "checked": self.checked,
            "passed": self.passed,
            "withheld_candidate_ids": list(self.withheld_candidate_ids),
            "status": self.status,
            "reason": self.reason,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "report_sha256": self.report_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "PrivacyScanReport":
        item = _strict(
            value,
            {
                "privacy_version",
                "scanned_card_sha256",
                "checked",
                "passed",
                "withheld_candidate_ids",
                "status",
                "reason",
                "report_sha256",
            },
            "privacy scan report",
        )
        if item["privacy_version"] != PRIVACY_SCAN_VERSION or not isinstance(
            item["withheld_candidate_ids"], list
        ):
            raise PipelineError("privacy scan report version or array is invalid")
        result = cls(
            scanned_card_sha256=item["scanned_card_sha256"],
            checked=item["checked"],
            passed=item["passed"],
            withheld_candidate_ids=tuple(item["withheld_candidate_ids"]),
            status=item["status"],
            reason=item["reason"],
        )
        if item["report_sha256"] != result.report_sha256:
            raise PipelineError("privacy scan report digest is inconsistent")
        return result


@dataclass(frozen=True)
class RiskStageSummary:
    status: str
    reason: str
    catalog_sha256: str | None
    context_sha256: str
    publisher_context_candidate_ids: tuple[str, ...]
    publisher_reported_risk_candidate_ids: tuple[str, ...]
    taxonomy_candidate_count: int
    taxonomy_included_count: int
    mapping_report_sha256: str | None
    summary_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.status not in {"completed", "unavailable"}:
            raise PipelineError("risk stage status is invalid")
        if not isinstance(self.reason, str) or not _CODE_RE.fullmatch(self.reason):
            raise PipelineError("risk stage reason is invalid")
        _require_digest(self.catalog_sha256, "risk catalog digest", nullable=True)
        _require_digest(self.context_sha256, "risk context digest")
        _require_digest(
            self.mapping_report_sha256,
            "risk mapping report digest",
            nullable=True,
        )
        for name in (
            "publisher_context_candidate_ids",
            "publisher_reported_risk_candidate_ids",
        ):
            values = tuple(getattr(self, name))
            if values != tuple(sorted(set(values))) or any(
                not isinstance(item, str) or not _CLAIM_RE.fullmatch(item)
                for item in values
            ):
                raise PipelineError(f"risk stage {name} is invalid")
            object.__setattr__(self, name, values)
        for value in (self.taxonomy_candidate_count, self.taxonomy_included_count):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise PipelineError("risk stage counts are invalid")
        if self.taxonomy_included_count > self.taxonomy_candidate_count:
            raise PipelineError("risk stage included count exceeds candidates")
        if self.status == "completed" and self.mapping_report_sha256 is None:
            raise PipelineError("completed risk stage requires a mapping report")
        object.__setattr__(self, "summary_sha256", _digest(self._payload()))

    @property
    def passed(self) -> bool:
        return self.status == "completed" and (
            self.taxonomy_candidate_count == self.taxonomy_included_count
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "risk_stage_version": RISK_STAGE_VERSION,
            "status": self.status,
            "reason": self.reason,
            "catalog_sha256": self.catalog_sha256,
            "context_sha256": self.context_sha256,
            "publisher_context_candidate_ids": list(
                self.publisher_context_candidate_ids
            ),
            "publisher_reported_risk_candidate_ids": list(
                self.publisher_reported_risk_candidate_ids
            ),
            "taxonomy_candidate_count": self.taxonomy_candidate_count,
            "taxonomy_included_count": self.taxonomy_included_count,
            "mapping_report_sha256": self.mapping_report_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "summary_sha256": self.summary_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "RiskStageSummary":
        item = _strict(
            value,
            {
                "risk_stage_version",
                "status",
                "reason",
                "catalog_sha256",
                "context_sha256",
                "publisher_context_candidate_ids",
                "publisher_reported_risk_candidate_ids",
                "taxonomy_candidate_count",
                "taxonomy_included_count",
                "mapping_report_sha256",
                "summary_sha256",
            },
            "risk stage summary",
        )
        if item["risk_stage_version"] != RISK_STAGE_VERSION or any(
            not isinstance(item[name], list)
            for name in (
                "publisher_context_candidate_ids",
                "publisher_reported_risk_candidate_ids",
            )
        ):
            raise PipelineError("risk stage summary version or arrays are invalid")
        result = cls(
            status=item["status"],
            reason=item["reason"],
            catalog_sha256=item["catalog_sha256"],
            context_sha256=item["context_sha256"],
            publisher_context_candidate_ids=tuple(
                item["publisher_context_candidate_ids"]
            ),
            publisher_reported_risk_candidate_ids=tuple(
                item["publisher_reported_risk_candidate_ids"]
            ),
            taxonomy_candidate_count=item["taxonomy_candidate_count"],
            taxonomy_included_count=item["taxonomy_included_count"],
            mapping_report_sha256=item["mapping_report_sha256"],
        )
        if item["summary_sha256"] != result.summary_sha256:
            raise PipelineError("risk stage summary digest is inconsistent")
        return result


@dataclass(frozen=True)
class PipelineRepairReport:
    """Canonical bridge from the original fact audit to final reprojection.

    Records contain no semantic submissions when the pipeline has no injected
    field-level repair proposal.  In that case each actionable predecessor is
    explicitly withheld, while any additional list-suffix removals are kept
    separate as deterministic projection-shape dependencies.
    """

    target: TargetIdentity
    original_composition_sha256: str
    original_factreasoner_sha256: str
    original_omission_audit_sha256: str
    post_repair_composition_sha256: str
    records: tuple[FieldRepairRecord, ...]
    structural_withheld_candidate_ids: tuple[str, ...]
    factreasoner_withheld_derivation_ids: tuple[str, ...] = ()
    repair_stage_version: str = REPAIR_STAGE_VERSION
    report_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.repair_stage_version != REPAIR_STAGE_VERSION:
            raise PipelineError("pipeline repair stage version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise PipelineError("pipeline repair target is invalid")
        for name in (
            "original_composition_sha256",
            "original_factreasoner_sha256",
            "original_omission_audit_sha256",
            "post_repair_composition_sha256",
        ):
            _require_digest(getattr(self, name), name)
        records = tuple(self.records)
        if not all(isinstance(item, FieldRepairRecord) for item in records):
            raise PipelineError("pipeline repair records are malformed")
        expected_order = tuple(
            sorted(
                records,
                key=lambda item: (
                    item.context.field_path,
                    item.context.predecessor_candidate_id,
                ),
            )
        )
        if records != expected_order:
            raise PipelineError("pipeline repair records are not canonical")
        predecessor_ids = [
            item.context.predecessor_candidate_id for item in records
        ]
        if len(predecessor_ids) != len(set(predecessor_ids)):
            raise PipelineError("pipeline repair records duplicate a predecessor")
        if any(item.context.target != self.target for item in records):
            raise PipelineError("pipeline repair record target differs")
        if any(
            item.context.composition_result_sha256
            != self.original_composition_sha256
            or item.context.factreasoner_record_sha256
            != self.original_factreasoner_sha256
            or item.context.omission_audit_sha256
            != self.original_omission_audit_sha256
            for item in records
        ):
            raise PipelineError("pipeline repair record inputs differ from the stage")
        structural = tuple(self.structural_withheld_candidate_ids)
        if structural != tuple(sorted(set(structural))) or any(
            not isinstance(item, str) or not _CLAIM_RE.fullmatch(item)
            for item in structural
        ):
            raise PipelineError("structural repair withholding is not canonical")
        if set(structural).intersection(predecessor_ids):
            raise PipelineError("actionable and structural withholding overlap")
        derivations = tuple(self.factreasoner_withheld_derivation_ids)
        if derivations != tuple(sorted(set(derivations))) or any(
            not isinstance(item, str)
            or not re.fullmatch(r"derivation-[0-9a-f]{24}", item)
            for item in derivations
        ):
            raise PipelineError("FactReasoner derivation withholding is not canonical")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "structural_withheld_candidate_ids", structural)
        object.__setattr__(self, "factreasoner_withheld_derivation_ids", derivations)
        object.__setattr__(self, "report_sha256", _digest(self._payload()))

    @property
    def actionable_candidate_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(item.context.predecessor_candidate_id for item in self.records)
        )

    @property
    def semantic_submission_count(self) -> int:
        return sum(len(item.attempts) for item in self.records)

    @property
    def withheld_candidate_ids(self) -> tuple[str, ...]:
        explicit = {
            item.context.predecessor_candidate_id
            for item in self.records
            if item.outcome is RepairOutcome.WITHHELD
        }
        return tuple(sorted(explicit | set(self.structural_withheld_candidate_ids)))

    def _payload(self) -> dict[str, Any]:
        return {
            "repair_stage_version": self.repair_stage_version,
            "target": self.target.to_dict(),
            "original_composition_sha256": self.original_composition_sha256,
            "original_factreasoner_sha256": self.original_factreasoner_sha256,
            "original_omission_audit_sha256": self.original_omission_audit_sha256,
            "post_repair_composition_sha256": self.post_repair_composition_sha256,
            "records": [item.to_dict() for item in self.records],
            "actionable_candidate_ids": list(self.actionable_candidate_ids),
            "structural_withheld_candidate_ids": list(
                self.structural_withheld_candidate_ids
            ),
            "factreasoner_withheld_derivation_ids": list(
                self.factreasoner_withheld_derivation_ids
            ),
            "withheld_candidate_ids": list(self.withheld_candidate_ids),
            "semantic_submission_count": self.semantic_submission_count,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "report_sha256": self.report_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "PipelineRepairReport":
        item = _strict(
            value,
            {
                "repair_stage_version",
                "target",
                "original_composition_sha256",
                "original_factreasoner_sha256",
                "original_omission_audit_sha256",
                "post_repair_composition_sha256",
                "records",
                "actionable_candidate_ids",
                "structural_withheld_candidate_ids",
                "factreasoner_withheld_derivation_ids",
                "withheld_candidate_ids",
                "semantic_submission_count",
                "report_sha256",
            },
            "pipeline repair report",
        )
        if any(
            not isinstance(item[name], list)
            for name in (
                "records",
                "actionable_candidate_ids",
                "structural_withheld_candidate_ids",
                "factreasoner_withheld_derivation_ids",
                "withheld_candidate_ids",
            )
        ) or not isinstance(item["semantic_submission_count"], int):
            raise PipelineError("pipeline repair report arrays or counts are malformed")
        result = cls(
            repair_stage_version=item["repair_stage_version"],
            target=TargetIdentity.from_dict(item["target"]),
            original_composition_sha256=item["original_composition_sha256"],
            original_factreasoner_sha256=item["original_factreasoner_sha256"],
            original_omission_audit_sha256=item["original_omission_audit_sha256"],
            post_repair_composition_sha256=item["post_repair_composition_sha256"],
            records=tuple(FieldRepairRecord.from_dict(x) for x in item["records"]),
            structural_withheld_candidate_ids=tuple(
                item["structural_withheld_candidate_ids"]
            ),
            factreasoner_withheld_derivation_ids=tuple(
                item["factreasoner_withheld_derivation_ids"]
            ),
        )
        if (
            item["actionable_candidate_ids"] != list(result.actionable_candidate_ids)
            or item["withheld_candidate_ids"] != list(result.withheld_candidate_ids)
            or item["semantic_submission_count"] != result.semantic_submission_count
            or item["report_sha256"] != result.report_sha256
        ):
            raise PipelineError("pipeline repair report derived values are inconsistent")
        return result


@dataclass(frozen=True)
class PipelineValidationSummary:
    claim_support_passed: bool
    factreasoner_passed: bool
    schema_passed: bool
    risk_passed: bool
    privacy_passed: bool
    conflicts_clear: bool
    omissions_clear: bool

    def __post_init__(self) -> None:
        if any(
            not isinstance(getattr(self, name), bool)
            for name in self.__dataclass_fields__
        ):
            raise PipelineError("pipeline validation flags must be boolean")

    @property
    def all_passed(self) -> bool:
        return all(self.to_dict().values())

    def to_dict(self) -> dict[str, bool]:
        return {
            "claim_support_passed": self.claim_support_passed,
            "factreasoner_passed": self.factreasoner_passed,
            "schema_passed": self.schema_passed,
            "risk_passed": self.risk_passed,
            "privacy_passed": self.privacy_passed,
            "conflicts_clear": self.conflicts_clear,
            "omissions_clear": self.omissions_clear,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PipelineValidationSummary":
        return cls(
            **_strict(
                value,
                {
                    "claim_support_passed",
                    "factreasoner_passed",
                    "schema_passed",
                    "risk_passed",
                    "privacy_passed",
                    "conflicts_clear",
                    "omissions_clear",
                },
                "pipeline validation summary",
            )
        )


@dataclass(frozen=True)
class PipelineResult:
    target: TargetIdentity
    run_id: str
    source_bundle_id: str
    source_manifest_sha256: str
    source_catalog_sha256: str
    composition_status: CompositionStatus
    composition_sha256: str
    claims: tuple[ClaimPipelineReference, ...]
    conflict_count: int
    omission_audit_sha256: str
    source_present_omission_count: int
    factreasoner_sha256: str
    risk: RiskStageSummary
    privacy: PrivacyScanReport
    validation: PipelineValidationSummary
    lifecycle_status: LifecycleStatus
    artifact_id: str
    artifact_sha256: str
    public_card_sha256: str
    artifacts: tuple[PersistedArtifactReference, ...]
    pipeline_version: str = PIPELINE_VERSION
    result_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.pipeline_version != PIPELINE_VERSION:
            raise PipelineError("pipeline result version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise PipelineError("pipeline result target is invalid")
        if not isinstance(self.run_id, str) or not _RUN_RE.fullmatch(self.run_id):
            raise PipelineError("pipeline result run_id is invalid")
        if not isinstance(self.source_bundle_id, str) or not self.source_bundle_id:
            raise PipelineError("pipeline result source bundle id is invalid")
        for name in (
            "source_manifest_sha256",
            "source_catalog_sha256",
            "composition_sha256",
            "omission_audit_sha256",
            "factreasoner_sha256",
            "artifact_sha256",
            "public_card_sha256",
        ):
            _require_digest(getattr(self, name), name)
        try:
            object.__setattr__(
                self, "composition_status", CompositionStatus(self.composition_status)
            )
            object.__setattr__(
                self, "lifecycle_status", LifecycleStatus(self.lifecycle_status)
            )
        except (TypeError, ValueError) as exc:
            raise PipelineError("pipeline result status is invalid") from exc
        claims = tuple(self.claims)
        if not all(isinstance(item, ClaimPipelineReference) for item in claims):
            raise PipelineError("pipeline result claims are malformed")
        if claims != tuple(sorted(claims, key=lambda item: item.candidate_id)) or len(
            {item.candidate_id for item in claims}
        ) != len(claims):
            raise PipelineError("pipeline result claims are not canonical")
        object.__setattr__(self, "claims", claims)
        for value in (
            self.conflict_count,
            self.source_present_omission_count,
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise PipelineError("pipeline result counts are invalid")
        if not isinstance(self.risk, RiskStageSummary) or not isinstance(
            self.privacy, PrivacyScanReport
        ) or not isinstance(self.validation, PipelineValidationSummary):
            raise PipelineError("pipeline result validation records are malformed")
        if self.privacy.scanned_card_sha256 != self.public_card_sha256:
            raise PipelineError("privacy scan is stale for the public card")
        if not isinstance(self.artifact_id, str) or not _CARD_RE.fullmatch(
            self.artifact_id
        ):
            raise PipelineError("pipeline result artifact id is invalid")
        artifacts = tuple(self.artifacts)
        if not all(isinstance(item, PersistedArtifactReference) for item in artifacts):
            raise PipelineError("pipeline result artifact references are malformed")
        keys = [(item.stage, item.logical_id) for item in artifacts]
        if len(keys) != len(set(keys)):
            raise PipelineError("pipeline result artifact references are duplicated")
        object.__setattr__(self, "artifacts", artifacts)
        if (
            self.lifecycle_status is LifecycleStatus.GENERATED_VALIDATED
            and not self.validation.all_passed
        ):
            raise PipelineError("validated lifecycle requires every pipeline gate")
        object.__setattr__(self, "result_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "pipeline_version": self.pipeline_version,
            "target": self.target.to_dict(),
            "run_id": self.run_id,
            "source_bundle_id": self.source_bundle_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_catalog_sha256": self.source_catalog_sha256,
            "composition_status": self.composition_status.value,
            "composition_sha256": self.composition_sha256,
            "claims": [item.to_dict() for item in self.claims],
            "conflict_count": self.conflict_count,
            "omission_audit_sha256": self.omission_audit_sha256,
            "source_present_omission_count": self.source_present_omission_count,
            "factreasoner_sha256": self.factreasoner_sha256,
            "risk": self.risk.to_dict(),
            "privacy": self.privacy.to_dict(),
            "validation": self.validation.to_dict(),
            "lifecycle_status": self.lifecycle_status.value,
            "artifact_id": self.artifact_id,
            "artifact_sha256": self.artifact_sha256,
            "public_card_sha256": self.public_card_sha256,
            "artifacts": [item.to_dict() for item in self.artifacts],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "result_sha256": self.result_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "PipelineResult":
        item = _strict(
            value,
            {
                "pipeline_version",
                "target",
                "run_id",
                "source_bundle_id",
                "source_manifest_sha256",
                "source_catalog_sha256",
                "composition_status",
                "composition_sha256",
                "claims",
                "conflict_count",
                "omission_audit_sha256",
                "source_present_omission_count",
                "factreasoner_sha256",
                "risk",
                "privacy",
                "validation",
                "lifecycle_status",
                "artifact_id",
                "artifact_sha256",
                "public_card_sha256",
                "artifacts",
                "result_sha256",
            },
            "pipeline result",
        )
        if not isinstance(item["claims"], list) or not isinstance(
            item["artifacts"], list
        ):
            raise PipelineError("pipeline result arrays are invalid")
        result = cls(
            pipeline_version=item["pipeline_version"],
            target=TargetIdentity.from_dict(item["target"]),
            run_id=item["run_id"],
            source_bundle_id=item["source_bundle_id"],
            source_manifest_sha256=item["source_manifest_sha256"],
            source_catalog_sha256=item["source_catalog_sha256"],
            composition_status=item["composition_status"],
            composition_sha256=item["composition_sha256"],
            claims=tuple(ClaimPipelineReference.from_dict(x) for x in item["claims"]),
            conflict_count=item["conflict_count"],
            omission_audit_sha256=item["omission_audit_sha256"],
            source_present_omission_count=item["source_present_omission_count"],
            factreasoner_sha256=item["factreasoner_sha256"],
            risk=RiskStageSummary.from_dict(item["risk"]),
            privacy=PrivacyScanReport.from_dict(item["privacy"]),
            validation=PipelineValidationSummary.from_dict(item["validation"]),
            lifecycle_status=item["lifecycle_status"],
            artifact_id=item["artifact_id"],
            artifact_sha256=item["artifact_sha256"],
            public_card_sha256=item["public_card_sha256"],
            artifacts=tuple(
                PersistedArtifactReference.from_dict(x) for x in item["artifacts"]
            ),
        )
        if item["result_sha256"] != result.result_sha256:
            raise PipelineError("pipeline result digest is inconsistent")
        return result


class _UnavailableFactChecker:
    checker_id = "pipeline/fact_checker_unavailable"
    checker_revision = "offline-v1"

    def check(self, request: CheckRequest) -> CheckerResponse:
        return CheckerResponse(
            outcome=CheckOutcome.UNAVAILABLE,
            reason_code="fact_checker_unavailable",
        )


class _PrivacyFilteringWriter:
    """Withhold unsafe exact values before the public projection is built."""

    def __init__(self, delegate: EvidenceOnlyWriter) -> None:
        self.delegate = delegate
        self.checked = 0
        self.passed = 0
        self.withheld: tuple[str, ...] = ()

    def select(self, writer_input: WriterInput) -> WriterSelection:
        selected = self.delegate.select(writer_input)
        if not isinstance(selected, WriterSelection):
            return selected
        safe = []
        withheld = []
        for choice in selected.choices:
            self.checked += 1
            try:
                assert_public_projection({"candidate_value": choice.value})
            except PublicExportError:
                withheld.append(choice.candidate_id)
            else:
                self.passed += 1
                safe.append(choice)
        self.withheld = tuple(sorted(withheld))
        return WriterSelection(tuple(safe))


def _checker_identity(checker: FactChecker | None) -> tuple[str, str]:
    selected = checker or _UnavailableFactChecker()
    checker_id = getattr(selected, "checker_id", None)
    revision = getattr(selected, "checker_revision", None)
    if not isinstance(checker_id, str) or not isinstance(revision, str):
        raise PipelineError("FactReasoner checker identity is incomplete")
    return checker_id, revision


def _object_identity(value: Any) -> str:
    if value is None:
        return "unavailable"
    return f"{type(value).__module__}.{type(value).__qualname__}"[:512]


def _persist_json(run_root: Path, filename: str, value: Any) -> Path:
    path = run_root / filename
    payload = _canonical_file(value)
    if path.is_symlink() or path.parent.is_symlink():
        raise PipelineError("run artifact path cannot be a symlink")
    if path.exists():
        if not path.is_file() or path.read_bytes() != payload:
            raise PipelineError(f"immutable run artifact differs: {filename}")
        return path
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{filename}.", suffix=".tmp", dir=str(run_root)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        directory = os.open(run_root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    return path


def _record_artifact(
    store: RunStore,
    *,
    stage: str,
    logical_id: str,
    status: str,
    reason: str,
    filename: str,
    value: Any,
    input_sha256s: Sequence[str] = (),
    metrics: Mapping[str, Any] | None = None,
) -> PersistedArtifactReference:
    path = _persist_json(store.root, filename, value)
    event = store.record_stage(
        stage=stage,
        logical_id=logical_id,
        status=status,
        reason=reason,
        artifact_path=path,
        input_sha256s=input_sha256s,
        metrics=metrics,
    )
    return PersistedArtifactReference(
        stage=event.stage,
        logical_id=event.logical_id,
        status=event.status,
        reason=event.reason,
        filename=filename,
        artifact_sha256=event.artifact_sha256 or "",
    )


def _extraction_summary(result: ExtractionResult) -> dict[str, Any]:
    return {
        "extraction_version": result.extraction_version,
        "target": result.target.to_dict(),
        "input_sha256": result.input_sha256,
        "result_sha256": result.result_sha256,
        "candidate_ids": [item.candidate_id for item in result.candidates],
        "candidate_sha256": [item.content_sha256 for item in result.candidates],
        "outcomes": [item.to_dict() for item in result.outcomes],
    }


def _candidate_inventory(
    structured: ExtractionResult, quote_results: Sequence[ExtractionResult]
) -> tuple[ClaimCandidate, ...]:
    by_id: dict[str, ClaimCandidate] = {}
    for result in (structured, *quote_results):
        for candidate in result.candidates:
            previous = by_id.setdefault(candidate.candidate_id, candidate)
            if previous.to_dict() != candidate.to_dict():
                raise PipelineError("candidate identifier collision")
    return tuple(sorted(by_id.values(), key=lambda item: item.candidate_id))


def _group_prose_decisions(
    candidates: Sequence[ClaimCandidate], decisions: Iterable[ProseCheckerDecision]
) -> Mapping[str, tuple[ProseCheckerDecision, ...]]:
    quote_candidates = tuple(
        item for item in candidates if {x.kind for x in item.evidence} == {EvidenceKind.QUOTE}
    )
    grouped: dict[str, list[ProseCheckerDecision]] = {}
    for decision in tuple(decisions):
        if not isinstance(decision, ProseCheckerDecision):
            raise PipelineError("prose checker decisions must be typed")
        matches = []
        for candidate in quote_candidates:
            probe = ProseCheckerDecision.for_candidate(
                candidate,
                gate=decision.gate,
                checker=decision.checker,
                method=decision.method,
                status=decision.status,
                reason=decision.reason,
            )
            if probe.request_sha256 == decision.request_sha256:
                matches.append(candidate.candidate_id)
        if len(matches) != 1:
            raise PipelineError("prose checker decision is unused, stale, or ambiguous")
        values = grouped.setdefault(matches[0], [])
        if any(item.gate is decision.gate for item in values):
            raise PipelineError("duplicate prose checker decision")
        values.append(decision)
    return {
        key: tuple(sorted(values, key=lambda item: item.gate.value))
        for key, values in grouped.items()
    }


def _binding(candidate: ClaimCandidate, target: TargetIdentity) -> Binding:
    kinds = {item.kind for item in candidate.evidence}
    if kinds == {EvidenceKind.QUOTE}:
        origin = BindingOrigin.QUOTED
    elif kinds == {EvidenceKind.STRUCTURED}:
        origin = BindingOrigin.STRUCTURED
    else:
        raise PipelineError("included candidate has mixed evidence kinds")
    disposition, reason = decide_binding(
        target=target,
        field_path=candidate.field_path,
        value=candidate.value,
        claim_entity=candidate.claim_entity,
        relation=candidate.relation,
        origin=origin,
        evidence=candidate.evidence,
    )
    if disposition is not Disposition.ACCEPTED:
        raise PipelineError("included candidate fails binding policy")
    return Binding(
        binding_id=binding_id_for(
            target=target,
            field_path=candidate.field_path,
            value=candidate.value,
            claim_entity=candidate.claim_entity,
            relation=candidate.relation,
            origin=origin,
            evidence=candidate.evidence,
            benchmark_scope=candidate.benchmark_scope,
        ),
        field_path=candidate.field_path,
        value=candidate.value,
        claim_entity=candidate.claim_entity,
        relation=candidate.relation,
        origin=origin,
        evidence=candidate.evidence,
        disposition=disposition,
        reason=reason,
        benchmark_scope=candidate.benchmark_scope,
    )


def _empty_content_card(target: TargetIdentity) -> dict[str, Any]:
    return project_card(CardArtifact(target=target, bindings=()))


def _empty_omission_audit(
    *,
    composition_sha256: str,
    card: Mapping[str, Any],
    availability_hints: Sequence[FieldAvailabilityHint],
) -> OmissionAudit:
    hints = {item.field_path: item for item in availability_hints}
    if len(hints) != len(availability_hints):
        raise PipelineError("duplicate field availability hint")
    records = []
    for field_path in CONTENT_FIELD_PATHS:
        value = get_field(card, field_path)
        hint = hints.get(field_path)
        if value not in (NOT_SPECIFIED, NOT_APPLICABLE):
            status, reason = FieldAuditStatus.PRESENT, None
        elif value == NOT_APPLICABLE or (
            hint is not None
            and hint.status is FieldAvailabilityStatus.NOT_APPLICABLE
        ):
            status, reason = FieldAuditStatus.OMITTED, OmissionReason.NOT_APPLICABLE
        elif hint is not None and hint.status is FieldAvailabilityStatus.SOURCE_UNAVAILABLE:
            status, reason = FieldAuditStatus.OMITTED, OmissionReason.SOURCE_UNAVAILABLE
        elif hint is not None and hint.status is FieldAvailabilityStatus.SOURCE_PRESENT:
            status, reason = FieldAuditStatus.OMITTED, OmissionReason.MISSED_BY_COMPOSITION
        else:
            status, reason = FieldAuditStatus.OMITTED, OmissionReason.NOT_FOUND
        records.append(
            FieldOmissionRecord(
                field_path=field_path,
                status=status,
                reason=reason,
                source_present=(
                    hint is not None
                    and hint.status is FieldAvailabilityStatus.SOURCE_PRESENT
                ),
                candidate_ids=(),
                included_candidate_ids=(),
                conflict_sha256s=(),
                availability_hint_sha256=(hint.content_sha256 if hint else None),
            )
        )
    source_present = tuple(
        item.field_path
        for item in records
        if item.status is FieldAuditStatus.OMITTED and item.source_present
    )
    return OmissionAudit(
        composition_result_sha256=composition_sha256,
        candidate_inventory_sha256=_digest([]),
        gate_inventory_sha256=_digest([]),
        availability_sha256=_digest(
            [item.to_dict() for item in sorted(availability_hints, key=lambda x: x.field_path)]
        ),
        records=tuple(records),
        source_present_omissions=source_present,
    )


def _use_contexts(
    candidates: Sequence[ClaimCandidate], included_ids: set[str]
) -> tuple[UseContext, ...]:
    accumulated: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if candidate.candidate_id not in included_ids:
            continue
        base = canonical_field_path(candidate.field_path)
        if base not in _CONTEXT_FIELDS or not isinstance(candidate.value, dict):
            continue
        value = candidate.value
        if value.get("origin") not in {"publisher_reported", "source_derived"}:
            continue
        context_id = value.get("context_id")
        description = value.get("description")
        refs = value.get("source_refs")
        if not isinstance(context_id, str) or not isinstance(description, str) or not isinstance(
            refs, list
        ):
            raise PipelineError("included publisher context wrapper is malformed")
        slot = accumulated.setdefault(
            context_id,
            {
                "description": description,
                "fields": set(),
                "candidate_ids": set(),
                "source_refs": set(),
            },
        )
        if slot["description"] != description:
            raise PipelineError("publisher context identifier collision")
        slot["fields"].add(candidate.field_path)
        slot["candidate_ids"].add(candidate.candidate_id)
        slot["source_refs"].update(refs)
    return tuple(
        UseContext(
            context_id=context_id,
            description=value["description"],
            supporting_fields=tuple(value["fields"]),
            supporting_candidate_ids=tuple(value["candidate_ids"]),
            source_refs=tuple(value["source_refs"]),
        )
        for context_id, value in sorted(accumulated.items())
    )


def _risk_stage(
    *,
    candidates: Sequence[ClaimCandidate],
    included_ids: set[str],
    catalog: RiskCatalog | None,
    detector: RiskDetector | None,
    checker: ApplicabilityChecker | None,
) -> tuple[RiskStageSummary, RiskMappingReport | None, tuple[UseContext, ...]]:
    contexts = _use_contexts(candidates, included_ids)
    context_digest = _digest([item.to_dict() for item in contexts])
    publisher_context_ids = tuple(
        sorted({cid for item in contexts for cid in item.supporting_candidate_ids})
    )
    publisher_risks = tuple(
        sorted(
            candidate.candidate_id
            for candidate in candidates
            if candidate.candidate_id in included_ids
            and canonical_field_path(candidate.field_path)
            == "use_and_risk.identified_risks"
            and isinstance(candidate.value, dict)
            and candidate.value.get("identification_origin") == "publisher_reported"
        )
    )
    if catalog is None:
        return (
            RiskStageSummary(
                status="unavailable",
                reason="risk_catalog_unavailable",
                catalog_sha256=None,
                context_sha256=context_digest,
                publisher_context_candidate_ids=publisher_context_ids,
                publisher_reported_risk_candidate_ids=publisher_risks,
                taxonomy_candidate_count=0,
                taxonomy_included_count=0,
                mapping_report_sha256=None,
            ),
            None,
            contexts,
        )
    if not contexts:
        # The mapper returns before consulting either provider interface.
        report = map_candidate_risks((), catalog, object(), object())  # type: ignore[arg-type]
    elif detector is None or checker is None:
        report = unavailable_risk_report(contexts, catalog)
    else:
        report = map_candidate_risks(contexts, catalog, detector, checker)
    return (
        RiskStageSummary(
            status=report.status.value,
            reason=report.reason,
            catalog_sha256=report.catalog_sha256,
            context_sha256=report.context_sha256,
            publisher_context_candidate_ids=publisher_context_ids,
            publisher_reported_risk_candidate_ids=publisher_risks,
            taxonomy_candidate_count=len(report.candidates),
            taxonomy_included_count=len(report.included_risks),
            mapping_report_sha256=report.report_sha256,
        ),
        report,
        contexts,
    )


def _taxonomy_risk_derivations(
    *,
    report: RiskMappingReport | None,
    contexts: Sequence[UseContext],
    candidates: Sequence[ClaimCandidate],
    gate_records: Sequence[ClaimGateRecord],
    included_ids: set[str],
    target: TargetIdentity,
    first_index: int,
) -> tuple[TaxonomyRiskDerivation, ...]:
    """Bind accepted taxonomy outputs to their exact immutable inputs."""

    if report is None or report.status is not MappingStatus.COMPLETED:
        return ()
    accepted_pairs = tuple(
        (candidate, decision)
        for candidate, decision in zip(report.candidates, report.decisions)
        if decision.status is ApplicabilityStatus.ACCEPTED
    )
    if len(accepted_pairs) != len(report.included_risks):
        raise PipelineError("risk report accepted outputs are incomplete")
    context_by_id = {item.context_id: item for item in contexts}
    candidate_by_id = {item.candidate_id: item for item in candidates}
    gate_by_id = {item.candidate.candidate_id: item for item in gate_records}
    output: list[TaxonomyRiskDerivation] = []
    for offset, ((risk_candidate, decision), public_value) in enumerate(
        zip(accepted_pairs, report.included_risks)
    ):
        if not isinstance(public_value, dict) or public_value.get("risk_id") != risk_candidate.risk_id:
            raise PipelineError("risk report output differs from its accepted candidate")
        selected_contexts = []
        for context_id in risk_candidate.context_ids:
            try:
                selected_contexts.append(context_by_id[context_id])
            except KeyError as exc:
                raise PipelineError("risk candidate references an unavailable context") from exc
        input_ids = tuple(
            sorted(
                {
                    candidate_id
                    for context in selected_contexts
                    for candidate_id in context.supporting_candidate_ids
                }
            )
        )
        inputs: list[DerivationClaimInput] = []
        for candidate_id in input_ids:
            candidate = candidate_by_id.get(candidate_id)
            gate = gate_by_id.get(candidate_id)
            if (
                candidate is None
                or gate is None
                or candidate_id not in included_ids
                or not gate.projection_eligible
            ):
                raise PipelineError(
                    "taxonomy risk derivation input is not an included accepted claim"
                )
            source_refs = tuple(sorted({item.source_id for item in candidate.evidence}))
            inputs.append(
                DerivationClaimInput(
                    candidate_id=candidate_id,
                    candidate_sha256=candidate.content_sha256,
                    gate_record_sha256=gate.content_sha256,
                    source_refs=source_refs,
                )
            )
        supporting_refs = tuple(
            sorted({ref for item in inputs for ref in item.source_refs})
        )
        if supporting_refs != tuple(sorted(risk_candidate.source_refs)):
            raise PipelineError("risk candidate source refs differ from accepted claim inputs")
        output.append(
            TaxonomyRiskDerivation(
                target=target,
                field_path=f"use_and_risk.identified_risks[{first_index + offset}]",
                value=public_value,
                risk_report_sha256=report.report_sha256,
                risk_catalog_sha256=report.catalog_sha256,
                risk_candidate_id=risk_candidate.candidate_id,
                risk_candidate_sha256=risk_candidate.candidate_sha256,
                applicability_decision_sha256=decision.decision_sha256,
                context_sha256s=tuple(
                    sorted(item.context_sha256 for item in selected_contexts)
                ),
                input_claims=tuple(inputs),
                supporting_source_refs=supporting_refs,
            )
        )
    return tuple(output)


def _apply_taxonomy_derivations_to_audit(
    audit: OmissionAudit,
    derivations: Sequence[TaxonomyRiskDerivation],
) -> OmissionAudit:
    if not derivations:
        return audit
    records = []
    for record in audit.records:
        if record.field_path != "use_and_risk.identified_risks":
            records.append(record)
            continue
        records.append(
            FieldOmissionRecord(
                field_path=record.field_path,
                status=FieldAuditStatus.PRESENT,
                reason=None,
                source_present=True,
                candidate_ids=record.candidate_ids,
                included_candidate_ids=record.included_candidate_ids,
                conflict_sha256s=record.conflict_sha256s,
                availability_hint_sha256=record.availability_hint_sha256,
            )
        )
    source_present_omissions = tuple(
        item.field_path
        for item in records
        if item.status is FieldAuditStatus.OMITTED and item.source_present
    )
    return OmissionAudit(
        composition_result_sha256=audit.composition_result_sha256,
        candidate_inventory_sha256=audit.candidate_inventory_sha256,
        gate_inventory_sha256=audit.gate_inventory_sha256,
        availability_sha256=audit.availability_sha256,
        records=tuple(records),
        source_present_omissions=source_present_omissions,
    )


def _path_contains(candidate_path: str, value_path: str) -> bool:
    """Return whether one atom belongs to the exact candidate/derivation slot."""

    base, indexes = parse_field_path(candidate_path)
    if not indexes:
        return value_path == base or value_path.startswith((base + ".", base + "["))
    return value_path == candidate_path or value_path.startswith(
        (candidate_path + ".", candidate_path + "[")
    )


def _actionable_candidate_ids(
    record: FactReasonerRecord,
    candidates: Sequence[ClaimCandidate],
    included_ids: set[str],
) -> tuple[str, ...]:
    atom_by_id = {item.atom_id: item for item in record.atoms}
    actionable_atoms = tuple(
        atom_by_id[decision.atom_id]
        for decision in record.decisions
        if decision.field_action is FieldAction.REPAIR_OR_WITHHOLD
    )
    return tuple(
        sorted(
            candidate.candidate_id
            for candidate in candidates
            if candidate.candidate_id in included_ids
            and any(
                atom.field_path == canonical_field_path(candidate.field_path)
                and _path_contains(candidate.field_path, atom.value_path)
                for atom in actionable_atoms
            )
        )
    )


def _structural_suffix_withholding(
    candidates: Sequence[ClaimCandidate],
    original_included_ids: set[str],
    actionable_ids: set[str],
) -> tuple[str, ...]:
    """Withhold only list suffixes that would otherwise leave an index gap."""

    remaining = set(original_included_ids) - set(actionable_ids)
    by_base: dict[str, list[tuple[int, str]]] = {}
    by_id = {item.candidate_id: item for item in candidates}
    for candidate_id in remaining:
        candidate = by_id[candidate_id]
        base, indexes = parse_field_path(candidate.field_path)
        if indexes:
            by_base.setdefault(base, []).append((indexes[0], candidate_id))
    structural: set[str] = set()
    for values in by_base.values():
        indexes = {index for index, _ in values}
        if not indexes:
            continue
        missing = next(
            (index for index in range(max(indexes) + 1) if index not in indexes),
            None,
        )
        if missing is None:
            continue
        structural.update(
            candidate_id for index, candidate_id in values if index > missing
        )
    return tuple(sorted(structural))


def _reproject_composition(
    original: CompositionResult,
    candidates: Sequence[ClaimCandidate],
    included_ids: set[str],
    target: TargetIdentity,
) -> CompositionResult:
    """Reproject a recorded selection without replaying pass A or a writer."""

    original_ids = set(original.plan.included_candidate_ids)
    if not included_ids <= original_ids:
        raise PipelineError("post-repair projection adds an unselected candidate")
    by_id = {item.candidate_id: item for item in candidates}
    if not included_ids <= set(by_id):
        raise PipelineError("post-repair projection references an unknown candidate")
    selection = WriterSelection(
        tuple(
            item
            for item in original.plan.writer_selection.choices
            if item.candidate_id in included_ids
        )
    )
    derivations: list[CompositionDerivation] = [original.plan.derivations[0]]
    for derivation in original.plan.derivations[1:]:
        selected = tuple(
            sorted(set(derivation.input_candidate_ids).intersection(included_ids))
        )
        if not selected:
            continue
        derivations.append(
            CompositionDerivation(
                name=derivation.name,
                version=derivation.version,
                output_path=derivation.output_path,
                method=derivation.method,
                input_candidate_ids=selected,
                input_sha256s=tuple(
                    sorted({by_id[item].content_sha256 for item in selected})
                ),
                output_sha256=derivation.output_sha256,
            )
        )
    plan = CompositionPlan(
        target=original.plan.target,
        inventory_sha256=original.plan.inventory_sha256,
        source_snapshot_sha256=original.plan.source_snapshot_sha256,
        schema_sha256=original.plan.schema_sha256,
        inventory_candidate_ids=original.plan.inventory_candidate_ids,
        eligible_candidate_ids=original.plan.eligible_candidate_ids,
        included_candidate_ids=tuple(sorted(included_ids)),
        excluded_candidate_ids=tuple(
            sorted(set(original.plan.inventory_candidate_ids) - included_ids)
        ),
        writer_input=original.plan.writer_input,
        writer_selection=selection,
        conflicts=original.plan.conflicts,
        derivations=tuple(derivations),
    )
    bindings: dict[str, Binding] = {}
    for candidate_id in sorted(included_ids):
        binding = _binding(by_id[candidate_id], target)
        bindings.setdefault(binding.binding_id, binding)
    card = project_card(
        CardArtifact(
            target=target,
            bindings=tuple(sorted(bindings.values(), key=lambda item: item.binding_id)),
        )
    )
    return CompositionResult(plan, card)


def _apply_repair_withholding_to_audit(
    audit: OmissionAudit,
    withheld_candidate_ids: Sequence[str],
) -> OmissionAudit:
    withheld = set(withheld_candidate_ids)
    if not withheld:
        return audit
    records = tuple(
        replace(
            item,
            reason=OmissionReason.WITHHELD,
            source_present=True,
        )
        if item.status is FieldAuditStatus.OMITTED
        and set(item.candidate_ids).intersection(withheld)
        else item
        for item in audit.records
    )
    source_present = tuple(
        item.field_path
        for item in records
        if item.status is FieldAuditStatus.OMITTED and item.source_present
    )
    return OmissionAudit(
        composition_result_sha256=audit.composition_result_sha256,
        candidate_inventory_sha256=audit.candidate_inventory_sha256,
        gate_inventory_sha256=audit.gate_inventory_sha256,
        availability_sha256=audit.availability_sha256,
        records=records,
        source_present_omissions=source_present,
    )


def _actionable_derivation_ids(
    record: FactReasonerRecord,
    derivations: Sequence[TaxonomyRiskDerivation],
) -> tuple[str, ...]:
    atom_by_id = {item.atom_id: item for item in record.atoms}
    actionable_atoms = tuple(
        atom_by_id[item.atom_id]
        for item in record.decisions
        if item.field_action is FieldAction.REPAIR_OR_WITHHOLD
    )
    return tuple(
        sorted(
            derivation.derivation_id
            for derivation in derivations
            if any(
                atom.field_path == canonical_field_path(derivation.field_path)
                and _path_contains(derivation.field_path, atom.value_path)
                for atom in actionable_atoms
            )
        )
    )


def _reindex_taxonomy_derivations(
    derivations: Sequence[TaxonomyRiskDerivation],
    withheld_ids: set[str],
    *,
    first_index: int,
) -> tuple[TaxonomyRiskDerivation, ...]:
    selected = tuple(
        item for item in derivations if item.derivation_id not in withheld_ids
    )
    return tuple(
        replace(
            item,
            field_path=f"use_and_risk.identified_risks[{first_index + offset}]",
        )
        for offset, item in enumerate(selected)
    )


def _privacy_scan_final_projection(
    card: Mapping[str, Any],
    candidates: Sequence[ClaimCandidate],
    included_ids: set[str],
    privacy_withheld_ids: Sequence[str],
) -> PrivacyScanReport:
    withheld = tuple(sorted(set(privacy_withheld_ids)))
    if set(withheld).intersection(included_ids):
        raise PipelineError("privacy-withheld candidate reached final projection")
    by_id = {item.candidate_id: item for item in candidates}
    try:
        for candidate_id in sorted(included_ids):
            assert_public_projection({"candidate_value": by_id[candidate_id].value})
        assert_public_projection(card)
    except (KeyError, PublicExportError) as exc:
        raise PipelineError("post-repair public projection failed the privacy boundary") from exc
    checked = len(included_ids) + len(withheld) + 1
    passed = len(included_ids) + 1
    return PrivacyScanReport(
        scanned_card_sha256=_file_digest(card),
        checked=checked,
        passed=passed,
        withheld_candidate_ids=withheld,
        status="completed",
        reason=(
            "privacy_safe_projection" if not withheld else "unsafe_candidates_withheld"
        ),
    )


def _factreasoner_claim_counts(
    record: FactReasonerRecord,
    candidates: Sequence[ClaimCandidate],
    included_ids: set[str],
) -> tuple[int, int, int, int]:
    del candidates, included_ids  # coverage is defined by the final atom inventory
    checked = len(record.decisions)
    passed = sum(item.outcome is CheckOutcome.SUPPORT for item in record.decisions)
    failed = sum(
        item.outcome in {CheckOutcome.CONTRADICTION, CheckOutcome.NEUTRAL}
        for item in record.decisions
    )
    unavailable = sum(
        item.outcome is CheckOutcome.UNAVAILABLE for item in record.decisions
    )
    return checked, passed, failed, unavailable


def _validation_checks(
    *,
    included_count: int,
    fact_counts: tuple[int, int, int, int],
    risk: RiskStageSummary,
    privacy_checked: int,
    privacy_passed: int,
    privacy_withheld: int,
    omission_audit: OmissionAudit,
    conflict_count: int,
) -> tuple[ValidationCheck, ...]:
    fact_checked, fact_passed, fact_failed, fact_unavailable = fact_counts
    if fact_unavailable:
        fact_status = ValidationCheckStatus.UNAVAILABLE
    elif fact_failed:
        fact_status = ValidationCheckStatus.FAILED
    else:
        fact_status = ValidationCheckStatus.COMPLETED
    risk_checked = max(1, risk.taxonomy_candidate_count)
    risk_passed = (
        risk_checked if risk.passed else risk.taxonomy_included_count
    )
    risk_unavailable = risk_checked if risk.status == "unavailable" else 0
    risk_withheld = (
        risk.taxonomy_candidate_count - risk.taxonomy_included_count
        if risk.status == "completed"
        else 0
    )
    return (
        ValidationCheck(
            check_id="claim_support",
            status=ValidationCheckStatus.COMPLETED,
            checked=included_count,
            passed=included_count,
        ),
        ValidationCheck(
            check_id="factreasoner",
            status=fact_status,
            checked=fact_checked,
            passed=fact_passed,
            failed=fact_failed,
            unavailable=fact_unavailable,
        ),
        ValidationCheck(
            check_id="risk_mapping",
            status=(
                ValidationCheckStatus.COMPLETED
                if risk.status == "completed"
                else ValidationCheckStatus.UNAVAILABLE
            ),
            checked=risk_checked,
            passed=risk_passed,
            withheld=risk_withheld,
            unavailable=risk_unavailable,
        ),
        ValidationCheck(
            check_id="omission_audit",
            status=ValidationCheckStatus.COMPLETED,
            checked=len(omission_audit.records),
            passed=len(omission_audit.records)
            - len(omission_audit.source_present_omissions),
            withheld=len(omission_audit.source_present_omissions),
        ),
        ValidationCheck(
            check_id="conflict_audit",
            status=ValidationCheckStatus.COMPLETED,
            checked=max(1, conflict_count),
            passed=1 if conflict_count == 0 else 0,
            withheld=conflict_count,
        ),
        ValidationCheck(
            check_id="privacy",
            status=ValidationCheckStatus.COMPLETED,
            checked=privacy_checked,
            passed=privacy_passed,
            withheld=privacy_withheld,
        ),
    )


def run_offline_pipeline(
    bundle_directory: str | os.PathLike[str],
    run_directory: str | os.PathLike[str],
    *,
    official_bundle_directory: str | os.PathLike[str] | None = None,
    quote_batches: Iterable[ExtractionBatch] = (),
    prose_checker_decisions: Iterable[ProseCheckerDecision] = (),
    fact_checker: FactChecker | None = None,
    fact_config: RetrievalConfig | None = None,
    risk_catalog: RiskCatalog | None = None,
    risk_detector: RiskDetector | None = None,
    risk_checker: ApplicabilityChecker | None = None,
    availability_hints: Iterable[FieldAvailabilityHint] = (),
    writer: EvidenceOnlyWriter | None = None,
) -> PipelineResult:
    """Run the complete provider-free pipeline from one verified frozen bundle.

    Provider-assisted outputs are injected as immutable normalized records.  A
    second invocation with the same run directory verifies and reuses every
    registered artifact and never performs a provider call.
    """

    source_state = load_source_state(
        bundle_directory,
        official_bundle_directory=official_bundle_directory,
    )
    source_manifest_sha256 = source_state.snapshot_sha256
    catalog = source_state.catalog
    quote_batch_values = tuple(sorted(tuple(quote_batches), key=lambda x: x.batch_sha256))
    if not all(isinstance(item, ExtractionBatch) for item in quote_batch_values):
        raise PipelineError("quote batches must be typed ExtractionBatch records")
    prose_values = tuple(prose_checker_decisions)
    hint_values = tuple(sorted(tuple(availability_hints), key=lambda x: x.field_path))
    if not all(isinstance(item, FieldAvailabilityHint) for item in hint_values):
        raise PipelineError("availability hints must be typed")
    if len({item.field_path for item in hint_values}) != len(hint_values):
        raise PipelineError("availability hints are duplicated")
    if risk_catalog is not None and not isinstance(risk_catalog, RiskCatalog):
        raise PipelineError("risk_catalog must be a typed RiskCatalog")
    if risk_catalog is None:
        try:
            risk_catalog = load_pinned_nexus_catalog()
        except RiskMappingError:
            risk_catalog = None

    checker_id, checker_revision = _checker_identity(fact_checker)
    manifest = RunManifest(
        target=catalog.target,
        source_bundle_id=source_state.active_catalog_bundle_id,
        source_manifest_sha256=source_manifest_sha256,
        configuration={
            "pipeline_version": PIPELINE_VERSION,
            "extraction_version": EXTRACTION_VERSION,
            "source_state_mode": source_state.mode.value,
            "hf_bundle_id": source_state.hf_bundle_id,
            "hf_manifest_sha256": source_state.hf_manifest_sha256,
            "hf_catalog_sha256": source_state.hf_catalog_sha256,
            "official_bundle_id": source_state.official_bundle_id,
            "official_manifest_sha256": source_state.official_manifest_sha256,
            "official_catalog_sha256": source_state.official_catalog_sha256,
            "quote_batch_count": len(quote_batch_values),
            "quote_batch_set_sha256": _digest(
                [item.batch_sha256 for item in quote_batch_values]
            ),
            "prose_decision_count": len(prose_values),
            "prose_decision_set_sha256": _digest(
                sorted(item.content_sha256 for item in prose_values)
            ),
            "fact_checker_id": checker_id,
            "fact_checker_revision": checker_revision,
            "fact_config_sha256": _digest((fact_config or RetrievalConfig()).to_dict()),
            "risk_catalog_sha256": (
                risk_catalog.catalog_sha256 if risk_catalog is not None else "unavailable"
            ),
            "risk_detector": _object_identity(risk_detector),
            "risk_checker": _object_identity(risk_checker),
            "writer": _object_identity(writer or SelectAllEvidenceWriter()),
            "availability_sha256": _digest([item.to_dict() for item in hint_values]),
        },
    )
    root = Path(run_directory)
    store = RunStore.initialize(root, manifest)
    # On resume, drift is detected before any stage work or external interface.
    store.events(verify_artifacts=True)
    artifact_refs: list[PersistedArtifactReference] = []
    artifact_refs.append(
        _record_artifact(
            store,
            stage="collect",
            logical_id="source_state",
            status="completed",
            reason=(
                "hf_and_official_bundles_verified"
                if source_state.mode is SourceStateMode.HF_AND_OFFICIAL
                else "hf_bundle_verified"
            ),
            filename="source-state.json",
            value=source_state.to_dict(),
            input_sha256s=(source_manifest_sha256,),
            metrics={
                "record_count": len(source_state.records),
                "loaded_count": len(source_state.documents),
                "official_source_enabled": (
                    source_state.mode is SourceStateMode.HF_AND_OFFICIAL
                ),
            },
        )
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="collect",
            logical_id="source_catalog",
            status="completed",
            reason="offline_bundle_verified",
            filename="source-catalog.json",
            value=catalog.to_dict(),
            input_sha256s=(source_manifest_sha256,),
            metrics={
                "record_count": len(catalog.records),
                "loaded_count": len(catalog.documents),
            },
        )
    )

    structured = deterministic_structured_candidates(catalog)
    quote_results = tuple(
        materialize_quote_batch(item, catalog) for item in quote_batch_values
    )
    candidates = _candidate_inventory(structured, quote_results)
    extraction_payload = {
        "extraction_version": EXTRACTION_VERSION,
        "target": catalog.target.to_dict(),
        "catalog_sha256": catalog.catalog_sha256,
        "structured": _extraction_summary(structured),
        "quote_batches": [item.to_dict() for item in quote_batch_values],
        "quote_results": [_extraction_summary(item) for item in quote_results],
        "candidates": [item.to_dict() for item in candidates],
    }
    extraction_sha256 = _digest(extraction_payload)
    artifact_refs.append(
        _record_artifact(
            store,
            stage="extract",
            logical_id="candidates",
            status="completed",
            reason="closed_extraction_completed",
            filename="extraction.json",
            value=extraction_payload,
            input_sha256s=(catalog.catalog_sha256,),
            metrics={
                "candidate_count": len(candidates),
                "quote_batch_count": len(quote_batch_values),
                "provider_proposal_rejection_count": sum(
                    len(item.rejections) for item in quote_batch_values
                ),
            },
        )
    )

    grouped_checks = _group_prose_decisions(candidates, prose_values)
    gate_records = tuple(
        evaluate_claim_gate(
            candidate,
            catalog.documents,
            grouped_checks.get(candidate.candidate_id, ()),
        )
        for candidate in candidates
    )
    gate_payload = {
        "target": catalog.target.to_dict(),
        "extraction_sha256": extraction_sha256,
        "records": [item.to_dict() for item in gate_records],
    }
    gate_sha256 = _digest(gate_payload)
    artifact_refs.append(
        _record_artifact(
            store,
            stage="claim_gate",
            logical_id="claims",
            status="completed",
            reason="four_part_gate_completed",
            filename="claim-gates.json",
            value=gate_payload,
            input_sha256s=(catalog.catalog_sha256, extraction_sha256),
            metrics={
                "checked_count": len(gate_records),
                "eligible_count": sum(item.projection_eligible for item in gate_records),
            },
        )
    )

    privacy_writer = _PrivacyFilteringWriter(writer or SelectAllEvidenceWriter())
    if candidates:
        original_composition = compose_model_card(
            candidates, gate_records, catalog.documents, writer=privacy_writer
        )
        composition_status = CompositionStatus.COMPLETED
        original_composition_sha256 = original_composition.content_sha256
        original_card = original_composition.card
        original_included_ids = set(
            original_composition.plan.included_candidate_ids
        )
        original_conflict_count = len(original_composition.plan.conflicts)
        original_composition_payload: dict[str, Any] = original_composition.to_dict()
        original_composition_reason = "evidence_only_composition_completed"
    else:
        original_composition = None
        composition_status = CompositionStatus.UNAVAILABLE
        original_card = _empty_content_card(catalog.target)
        original_composition_sha256 = _digest(
            {
                "pipeline_version": PIPELINE_VERSION,
                "mode": "no_candidate_evidence",
                "target": catalog.target.to_dict(),
                "catalog_sha256": catalog.catalog_sha256,
                "card_sha256": _digest(original_card),
            }
        )
        original_included_ids = set()
        original_conflict_count = 0
        original_composition_payload = {
            "status": "unavailable",
            "reason": "no_candidate_evidence",
            "target": catalog.target.to_dict(),
            "composition_sha256": original_composition_sha256,
            "card": original_card,
        }
        original_composition_reason = "no_candidate_evidence"
    validate_public_card(original_card)
    artifact_refs.append(
        _record_artifact(
            store,
            stage="compose",
            logical_id="original_card_content",
            status=composition_status.value,
            reason=original_composition_reason,
            filename="composition-original.json",
            value=original_composition_payload,
            input_sha256s=(gate_sha256,),
            metrics={
                "included_count": len(original_included_ids),
                "conflict_count": original_conflict_count,
            },
        )
    )

    selected_fact_checker = fact_checker or _UnavailableFactChecker()
    source_availability = tuple(
        SourceAvailability.from_catalog_record(item) for item in catalog.records
    )
    original_fact_record = run_factreasoner(
        original_card,
        CONTRACT_SCHEMA,
        catalog.target,
        catalog.documents,
        selected_fact_checker,
        source_availability=source_availability,
        config=fact_config,
    )
    original_fact_counts = _factreasoner_claim_counts(
        original_fact_record, candidates, original_included_ids
    )
    original_fact_unavailable = bool(original_fact_record.decisions) and all(
        item.outcome is CheckOutcome.UNAVAILABLE
        for item in original_fact_record.decisions
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="factreasoner",
            logical_id="original_claims",
            status="unavailable" if original_fact_unavailable else "completed",
            reason=(
                (
                    "fact_checker_unavailable"
                    if fact_checker is None
                    else "fact_checks_unavailable"
                )
                if original_fact_unavailable
                else "original_factreasoner_completed"
            ),
            filename="factreasoner-original.json",
            value=original_fact_record.to_dict(),
            input_sha256s=(original_composition_sha256, catalog.catalog_sha256),
            metrics={
                "atom_count": len(original_fact_record.atoms),
                "eligible_atom_count": original_fact_counts[0],
                "supported_atom_count": original_fact_counts[1],
                "actionable_atom_count": original_fact_counts[2],
                "unavailable_atom_count": original_fact_counts[3],
            },
        )
    )

    if original_composition is not None:
        original_omission_audit = audit_omissions(
            candidates, gate_records, original_composition, hint_values
        )
    else:
        original_omission_audit = _empty_omission_audit(
            composition_sha256=original_composition_sha256,
            card=original_card,
            availability_hints=hint_values,
        )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="omission_audit",
            logical_id="original_fields",
            status="completed",
            reason="original_field_omission_audit_completed",
            filename="omissions-original.json",
            value=original_omission_audit.to_dict(),
            input_sha256s=(original_composition_sha256, gate_sha256),
            metrics={
                "field_count": len(original_omission_audit.records),
                "source_present_omission_count": len(
                    original_omission_audit.source_present_omissions
                ),
            },
        )
    )

    actionable_ids = _actionable_candidate_ids(
        original_fact_record, candidates, original_included_ids
    )
    repair_records: tuple[FieldRepairRecord, ...] = ()
    if original_composition is not None:
        by_candidate_id = {item.candidate_id: item for item in candidates}
        repair_records = tuple(
            sorted(
                (
                    run_field_repair(
                        field_path=by_candidate_id[candidate_id].field_path,
                        predecessor_candidate_id=candidate_id,
                        candidates=candidates,
                        gate_records=gate_records,
                        sources=catalog.documents,
                        composition_result=original_composition,
                        omission_audit=original_omission_audit,
                        factreasoner_record=original_fact_record,
                        submissions=(),
                        availability_hints=hint_values,
                    )
                    for candidate_id in actionable_ids
                ),
                key=lambda item: (
                    item.context.field_path,
                    item.context.predecessor_candidate_id,
                ),
            )
        )
    structural_withheld_ids = _structural_suffix_withholding(
        candidates, original_included_ids, set(actionable_ids)
    )
    included_ids = original_included_ids - set(actionable_ids) - set(
        structural_withheld_ids
    )
    if original_composition is not None:
        composition = (
            original_composition
            if included_ids == original_included_ids
            else _reproject_composition(
                original_composition, candidates, included_ids, catalog.target
            )
        )
        composition_sha256 = composition.content_sha256
        composition_card = composition.card
        conflict_count = len(composition.plan.conflicts)
        composition_payload: dict[str, Any] = composition.to_dict()
        composition_reason = (
            "evidence_only_composition_completed"
            if included_ids == original_included_ids
            else "factreasoner_withholding_reprojected"
        )
    else:
        composition = None
        composition_sha256 = original_composition_sha256
        composition_card = original_card
        conflict_count = 0
        composition_payload = original_composition_payload
        composition_reason = original_composition_reason
    validate_public_card(composition_card)
    artifact_refs.append(
        _record_artifact(
            store,
            stage="compose",
            logical_id="post_repair_card_content",
            status=composition_status.value,
            reason=composition_reason,
            filename="composition.json",
            value=composition_payload,
            input_sha256s=(
                original_composition_sha256,
                original_fact_record.content_sha256,
                original_omission_audit.content_sha256,
            ),
            metrics={
                "included_count": len(included_ids),
                "fact_withheld_count": len(actionable_ids),
                "structural_withheld_count": len(structural_withheld_ids),
                "conflict_count": conflict_count,
            },
        )
    )

    risk_summary, risk_report, use_contexts = _risk_stage(
        candidates=candidates,
        included_ids=included_ids,
        catalog=risk_catalog,
        detector=risk_detector,
        checker=risk_checker,
    )
    composed_risks = get_field(composition_card, "use_and_risk.identified_risks")
    publisher_risk_count = len(composed_risks) if isinstance(composed_risks, list) else 0
    provisional_derivations = _taxonomy_risk_derivations(
        report=risk_report,
        contexts=use_contexts,
        candidates=candidates,
        gate_records=gate_records,
        included_ids=included_ids,
        target=catalog.target,
        first_index=publisher_risk_count,
    )
    selected_candidates = tuple(
        item for item in candidates if item.candidate_id in included_ids
    )
    bindings_by_id: dict[str, Binding] = {}
    for candidate in selected_candidates:
        binding = _binding(candidate, catalog.target)
        bindings_by_id.setdefault(binding.binding_id, binding)
    provisional_content_artifact = CardArtifact(
        target=catalog.target,
        bindings=tuple(sorted(bindings_by_id.values(), key=lambda item: item.binding_id)),
        derivations=provisional_derivations,
    )
    provisional_content_card = project_card(provisional_content_artifact)
    provisional_fact_record = run_factreasoner(
        provisional_content_card,
        CONTRACT_SCHEMA,
        catalog.target,
        catalog.documents,
        selected_fact_checker,
        source_availability=source_availability,
        config=fact_config,
    )
    late_actionable_ids = _actionable_candidate_ids(
        provisional_fact_record, candidates, included_ids
    )
    if late_actionable_ids:
        raise PipelineError(
            "post-repair FactReasoner produced a new actionable evidence claim"
        )
    fact_withheld_derivation_ids = _actionable_derivation_ids(
        provisional_fact_record, provisional_derivations
    )
    taxonomy_derivations = _reindex_taxonomy_derivations(
        provisional_derivations,
        set(fact_withheld_derivation_ids),
        first_index=publisher_risk_count,
    )
    if fact_withheld_derivation_ids:
        risk_summary = replace(
            risk_summary,
            reason="factreasoner_withheld_taxonomy_claims",
            taxonomy_included_count=len(taxonomy_derivations),
        )
        content_artifact = CardArtifact(
            target=catalog.target,
            bindings=tuple(
                sorted(bindings_by_id.values(), key=lambda item: item.binding_id)
            ),
            derivations=taxonomy_derivations,
        )
        content_card = project_card(content_artifact)
        fact_record = run_factreasoner(
            content_card,
            CONTRACT_SCHEMA,
            catalog.target,
            catalog.documents,
            selected_fact_checker,
            source_availability=source_availability,
            config=fact_config,
        )
    else:
        content_artifact = provisional_content_artifact
        content_card = provisional_content_card
        fact_record = provisional_fact_record
    if any(
        item.field_action is FieldAction.REPAIR_OR_WITHHOLD
        for item in fact_record.decisions
    ):
        raise PipelineError("actionable FactReasoner claim survived final withholding")
    validate_public_card(content_card)

    repair_report = PipelineRepairReport(
        target=catalog.target,
        original_composition_sha256=original_composition_sha256,
        original_factreasoner_sha256=original_fact_record.content_sha256,
        original_omission_audit_sha256=original_omission_audit.content_sha256,
        post_repair_composition_sha256=composition_sha256,
        records=repair_records,
        structural_withheld_candidate_ids=structural_withheld_ids,
        factreasoner_withheld_derivation_ids=fact_withheld_derivation_ids,
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="repair",
            logical_id="factreasoner_fields",
            status=(
                "withheld"
                if repair_report.withheld_candidate_ids
                or repair_report.factreasoner_withheld_derivation_ids
                else "completed"
            ),
            reason=(
                "actionable_claims_withheld"
                if repair_report.withheld_candidate_ids
                or repair_report.factreasoner_withheld_derivation_ids
                else "no_actionable_claims"
            ),
            filename="repairs.json",
            value=repair_report.to_dict(),
            input_sha256s=(
                original_composition_sha256,
                original_fact_record.content_sha256,
                original_omission_audit.content_sha256,
                composition_sha256,
            ),
            metrics={
                "record_count": len(repair_report.records),
                "semantic_submission_count": repair_report.semantic_submission_count,
                "fact_withheld_count": len(repair_report.actionable_candidate_ids),
                "structural_withheld_count": len(
                    repair_report.structural_withheld_candidate_ids
                ),
                "derivation_withheld_count": len(
                    repair_report.factreasoner_withheld_derivation_ids
                ),
                "post_repair_included_count": len(included_ids),
            },
        )
    )

    risk_payload = {
        "summary": risk_summary.to_dict(),
        "use_contexts": [item.to_dict() for item in use_contexts],
        "taxonomy_derivations": [item.to_dict() for item in taxonomy_derivations],
        "factreasoner_withheld_derivation_ids": list(
            fact_withheld_derivation_ids
        ),
        "taxonomy_mapping": (
            None
            if risk_report is None
            else {
                "mapping_version": risk_report.mapping_version,
                "status": risk_report.status.value,
                "catalog_sha256": risk_report.catalog_sha256,
                "context_sha256": risk_report.context_sha256,
                "candidate_ids": [item.candidate_id for item in risk_report.candidates],
                "candidate_sha256": [
                    item.candidate_sha256 for item in risk_report.candidates
                ],
                "decision_sha256": [
                    item.decision_sha256 for item in risk_report.decisions
                ],
                "included_risks": list(risk_report.included_risks),
                "reason": risk_report.reason,
                "report_sha256": risk_report.report_sha256,
            }
        ),
    }
    artifact_refs.append(
        _record_artifact(
            store,
            stage="risk_map",
            logical_id="taxonomy",
            status=risk_summary.status,
            reason=risk_summary.reason,
            filename="risk-mapping.json",
            value=risk_payload,
            input_sha256s=(composition_sha256, repair_report.report_sha256),
            metrics={
                "context_count": len(use_contexts),
                "taxonomy_candidate_count": risk_summary.taxonomy_candidate_count,
                "taxonomy_included_count": risk_summary.taxonomy_included_count,
                "factreasoner_withheld_count": len(fact_withheld_derivation_ids),
            },
        )
    )

    fact_counts = _factreasoner_claim_counts(fact_record, candidates, included_ids)
    fact_stage_unavailable = bool(fact_record.decisions) and all(
        item.outcome is CheckOutcome.UNAVAILABLE for item in fact_record.decisions
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="factreasoner",
            logical_id="post_repair_claims",
            status="unavailable" if fact_stage_unavailable else "completed",
            reason=(
                (
                    "fact_checker_unavailable"
                    if fact_checker is None
                    else "fact_checks_unavailable"
                )
                if fact_stage_unavailable
                else "post_repair_factreasoner_completed"
            ),
            filename="factreasoner.json",
            value=fact_record.to_dict(),
            input_sha256s=(
                composition_sha256,
                risk_summary.summary_sha256,
                repair_report.report_sha256,
                catalog.catalog_sha256,
            ),
            metrics={
                "atom_count": len(fact_record.atoms),
                "eligible_atom_count": fact_counts[0],
                "supported_atom_count": fact_counts[1],
                "actionable_atom_count": fact_counts[2],
                "unavailable_atom_count": fact_counts[3],
            },
        )
    )

    if composition is not None:
        omission_audit = audit_omissions(
            candidates, gate_records, composition, hint_values
        )
    else:
        omission_audit = _empty_omission_audit(
            composition_sha256=composition_sha256,
            card=composition_card,
            availability_hints=hint_values,
        )
    omission_audit = _apply_repair_withholding_to_audit(
        omission_audit, repair_report.withheld_candidate_ids
    )
    omission_audit = _apply_taxonomy_derivations_to_audit(
        omission_audit, taxonomy_derivations
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="omission_audit",
            logical_id="post_repair_fields",
            status="completed",
            reason="post_repair_field_omission_audit_completed",
            filename="omissions.json",
            value=omission_audit.to_dict(),
            input_sha256s=(
                composition_sha256,
                gate_sha256,
                repair_report.report_sha256,
                risk_summary.summary_sha256,
            ),
            metrics={
                "field_count": len(omission_audit.records),
                "source_present_omission_count": len(
                    omission_audit.source_present_omissions
                ),
            },
        )
    )

    privacy_precheck = _privacy_scan_final_projection(
        content_card,
        candidates,
        included_ids,
        privacy_writer.withheld,
    )

    gate_by_id = {item.candidate.candidate_id: item for item in gate_records}
    claim_support_passed = (
        composition_status is CompositionStatus.COMPLETED
        and all(
            gate_by_id[candidate_id].projection_eligible
            for candidate_id in included_ids
        )
    )
    fact_passed = fact_counts[0] == fact_counts[1]
    validation = PipelineValidationSummary(
        claim_support_passed=claim_support_passed,
        factreasoner_passed=fact_passed,
        schema_passed=True,
        risk_passed=risk_summary.passed,
        privacy_passed=privacy_precheck.passed_without_withholding,
        conflicts_clear=conflict_count == 0,
        omissions_clear=not omission_audit.source_present_omissions,
    )
    lifecycle = (
        LifecycleStatus.GENERATED_VALIDATED
        if validation.all_passed
        else LifecycleStatus.GENERATED_UNREVIEWED
    )
    checks = _validation_checks(
        included_count=len(bindings_by_id),
        fact_counts=fact_counts,
        risk=risk_summary,
        privacy_checked=privacy_precheck.checked,
        privacy_passed=privacy_precheck.passed,
        privacy_withheld=len(privacy_precheck.withheld_candidate_ids),
        omission_audit=omission_audit,
        conflict_count=conflict_count,
    )
    artifact = CardArtifact(
        target=catalog.target,
        bindings=tuple(sorted(bindings_by_id.values(), key=lambda item: item.binding_id)),
        validation_checks=checks,
        lifecycle_status=lifecycle,
        derivations=taxonomy_derivations,
    )
    public_card = project_card(artifact)
    for field_path in CONTENT_FIELD_PATHS:
        if get_field(public_card, field_path) != get_field(content_card, field_path):
            raise PipelineError("final artifact content differs from evidence composition")
    validate_public_card(public_card)
    try:
        assert_public_projection(public_card)
    except PublicExportError as exc:  # computed metadata must never reopen the boundary
        raise PipelineError("final public card failed the privacy boundary") from exc

    artifact_payload = artifact.to_dict()
    public_card_sha256 = _file_digest(public_card)
    artifact_sha256 = _file_digest(artifact_payload)
    privacy_report = PrivacyScanReport(
        scanned_card_sha256=public_card_sha256,
        checked=privacy_precheck.checked,
        passed=privacy_precheck.passed,
        withheld_candidate_ids=privacy_precheck.withheld_candidate_ids,
        status=privacy_precheck.status,
        reason=privacy_precheck.reason,
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="privacy",
            logical_id="public_card",
            status="completed",
            reason=privacy_report.reason,
            filename="privacy.json",
            value=privacy_report.to_dict(),
            input_sha256s=(
                composition_sha256,
                repair_report.report_sha256,
                public_card_sha256,
            ),
            metrics={
                "checked_count": privacy_report.checked,
                "passed_count": privacy_report.passed,
                "withheld_count": len(privacy_report.withheld_candidate_ids),
            },
        )
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="export",
            logical_id="local_artifact",
            status="completed",
            reason="local_artifact_persisted",
            filename="card-artifact.json",
            value=artifact_payload,
            input_sha256s=(
                composition_sha256,
                repair_report.report_sha256,
                fact_record.content_sha256,
                omission_audit.content_sha256,
                privacy_report.report_sha256,
                risk_summary.summary_sha256,
            ),
            metrics={
                "binding_count": len(artifact.bindings),
                "derivation_count": len(artifact.derivations),
            },
        )
    )
    artifact_refs.append(
        _record_artifact(
            store,
            stage="export",
            logical_id="public_card",
            status="completed",
            reason="privacy_safe_public_card",
            filename="public-card.json",
            value=public_card,
            input_sha256s=(artifact_sha256, privacy_report.report_sha256),
            metrics={"included_claim_count": len(included_ids)},
        )
    )

    claims = tuple(
        ClaimPipelineReference(
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.content_sha256,
            gate_record_sha256=gate_by_id[candidate.candidate_id].content_sha256,
            projection_eligible=gate_by_id[candidate.candidate_id].projection_eligible,
            included=candidate.candidate_id in included_ids,
        )
        for candidate in candidates
    )
    result = PipelineResult(
        target=catalog.target,
        run_id=manifest.run_id,
        source_bundle_id=catalog.bundle_id,
        source_manifest_sha256=source_manifest_sha256,
        source_catalog_sha256=catalog.catalog_sha256,
        composition_status=composition_status,
        composition_sha256=composition_sha256,
        claims=claims,
        conflict_count=conflict_count,
        omission_audit_sha256=omission_audit.content_sha256,
        source_present_omission_count=len(
            omission_audit.source_present_omissions
        ),
        factreasoner_sha256=fact_record.content_sha256,
        risk=risk_summary,
        privacy=privacy_report,
        validation=validation,
        lifecycle_status=lifecycle,
        artifact_id=artifact.artifact_id,
        artifact_sha256=artifact_sha256,
        public_card_sha256=public_card_sha256,
        artifacts=tuple(artifact_refs),
    )
    result_path = _persist_json(store.root, "pipeline-result.json", result.to_dict())
    store.record_stage(
        stage="complete",
        logical_id="pipeline",
        status="completed",
        reason="offline_pipeline_completed",
        artifact_path=result_path,
        input_sha256s=(
            artifact_sha256,
            public_card_sha256,
            result.result_sha256,
        ),
        metrics={
            "candidate_count": len(candidates),
            "included_count": len(included_ids),
            "lifecycle_status": lifecycle.value,
        },
    )
    return result


def verify_pipeline_result(
    expected: PipelineResult,
    bundle_directory: str | os.PathLike[str],
    run_directory: str | os.PathLike[str],
    **kwargs: Any,
) -> PipelineResult:
    """Idempotently replay a run and reject any result divergence."""

    if not isinstance(expected, PipelineResult):
        raise PipelineError("pipeline replay requires a typed PipelineResult")
    replayed = run_offline_pipeline(
        bundle_directory, run_directory, **kwargs
    )
    if replayed.to_dict() != expected.to_dict():
        raise PipelineError("pipeline replay diverged from the expected result")
    return replayed


__all__ = [
    "PIPELINE_VERSION",
    "REPAIR_STAGE_VERSION",
    "ClaimPipelineReference",
    "CompositionStatus",
    "PersistedArtifactReference",
    "PipelineError",
    "PipelineRepairReport",
    "PipelineResult",
    "PipelineValidationSummary",
    "PrivacyScanReport",
    "RiskStageSummary",
    "run_offline_pipeline",
    "verify_pipeline_result",
]
