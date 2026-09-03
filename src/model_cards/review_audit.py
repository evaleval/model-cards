"""Replay-bound audit of an artifact after append-only review events.

Review actions are not allowed to inherit the generated artifact's validation
status.  This lane replays every corrected candidate through its retained
four-part Claim Support Gate, projects the effective card, validates the
schema, and recomputes field-level omission state while preserving any prior
source-availability classification.  Downstream closure is optional and
fail-closed: a reviewed candidate is sealed only when typed publication,
FactReasoner, risk, and privacy artifacts bind the current effective card.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping

from .artifact import CardArtifact, project_card
from .bindings import verify_artifact_sources
from .claim_gate import ClaimCandidate, ClaimGateRecord, verify_claim_gate_record
from .factreasoner import (
    IBM_FACTREASONER_UPSTREAM_REVISION,
    CheckOutcome,
    FactReasonerRecord,
    FieldAction,
)
from .findings import OmissionAudit
from .models import (
    Disposition,
    ReviewAction,
    SourceDocument,
    TaxonomyRiskDerivation,
)
from .pipeline import (
    PrivacyScanReport,
    RiskStageSummary,
    _model_use_contexts,
    _privacy_scan_final_projection,
)
from .publication_validation import (
    PublicationValidationReport,
    replay_publication_validation,
    run_publication_validation,
)
from .publication import project_publication_card
from .publication_schema import validate_publication_card
from .publication_sources import enrich_publication_card
from .risk_mapping import (
    RiskCatalog,
    RiskMappingReport,
    UseContext,
    replay_risk_mapping,
)
from .schema import (
    CONTENT_FIELD_PATHS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    canonical_field_path,
    get_field,
    validate_public_card,
)
from .source_documents import SourceDocumentCatalog


REVIEW_AUDIT_VERSION = "reviewed-candidate-audit/v2"
PROVISIONAL_VERDICT = "reviewed_candidate_requires_downstream_revalidation"
CLOSED_VERDICT = "reviewed_candidate_closed"

_CHECK_NAMES = (
    "artifact_integrity",
    "claim_support",
    "factreasoner",
    "omissions",
    "privacy",
    "public_schema",
    "publication",
    "review_history",
    "review_reassignment_gates",
    "risk",
)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9._-]{1,127}$")
_PINNED_FACTREASONER_CHECKER_ID = "ibm/factreasoner-fr1"


class ReviewAuditError(ValueError):
    """A reviewed candidate cannot be replayed or audited safely."""


class ReviewAuditStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


class ReviewedOmissionReason(str, Enum):
    WITHHELD = "withheld"
    REASSIGNED = "reassigned"
    PRIOR_SOURCE_STATE = "prior_source_state"
    NOT_FOUND = "not_found"


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
        raise ReviewAuditError("review audit values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReviewAuditCheck:
    name: str
    status: ReviewAuditStatus
    reason: str
    artifact_sha256: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _CODE_RE.fullmatch(self.name):
            raise ReviewAuditError("review audit check name is invalid")
        try:
            object.__setattr__(self, "status", ReviewAuditStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise ReviewAuditError("review audit check status is invalid") from exc
        if not isinstance(self.reason, str) or not _CODE_RE.fullmatch(self.reason):
            raise ReviewAuditError("review audit check reason is invalid")
        if self.status in {ReviewAuditStatus.PASSED, ReviewAuditStatus.FAILED}:
            if not isinstance(self.artifact_sha256, str) or not _DIGEST_RE.fullmatch(
                self.artifact_sha256
            ):
                raise ReviewAuditError(
                    "available review audit check result requires a digest"
                )
        elif self.artifact_sha256 is not None and not _DIGEST_RE.fullmatch(
            self.artifact_sha256
        ):
            raise ReviewAuditError("review audit check digest is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "reason": self.reason,
            "artifact_sha256": self.artifact_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ReviewAuditCheck":
        if not isinstance(value, dict) or set(value) != {
            "name",
            "status",
            "reason",
            "artifact_sha256",
        }:
            raise ReviewAuditError("review audit check has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class ReviewedFieldState:
    field_path: str
    present: bool
    source_present: bool
    reason: ReviewedOmissionReason | None

    def __post_init__(self) -> None:
        if self.field_path not in CONTENT_FIELD_PATHS:
            raise ReviewAuditError("reviewed field state path is invalid")
        if not isinstance(self.present, bool) or not isinstance(self.source_present, bool):
            raise ReviewAuditError("reviewed field state booleans are invalid")
        if self.reason is not None:
            try:
                object.__setattr__(self, "reason", ReviewedOmissionReason(self.reason))
            except (TypeError, ValueError) as exc:
                raise ReviewAuditError("reviewed omission reason is invalid") from exc
        if self.present and self.reason is not None:
            raise ReviewAuditError("present reviewed fields cannot have an omission reason")
        if not self.present and self.reason is None:
            raise ReviewAuditError("omitted reviewed fields require a reason")

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "present": self.present,
            "source_present": self.source_present,
            "reason": None if self.reason is None else self.reason.value,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ReviewedFieldState":
        if not isinstance(value, dict) or set(value) != {
            "field_path",
            "present",
            "source_present",
            "reason",
        }:
            raise ReviewAuditError("reviewed field state has an invalid shape")
        return cls(**value)


@dataclass(frozen=True)
class ReviewClosureEvidence:
    """Typed downstream records offered for an explicit sealed audit."""

    claim_gate_records: tuple[ClaimGateRecord, ...]
    publication_catalog: SourceDocumentCatalog
    publication_factreasoner: FactReasonerRecord
    publication_validation: PublicationValidationReport
    final_factreasoner: FactReasonerRecord
    risk_catalog: RiskCatalog
    risk_mapping: dict[str, Any]
    privacy: PrivacyScanReport

    def __post_init__(self) -> None:
        records = tuple(self.claim_gate_records)
        if not records or not all(isinstance(item, ClaimGateRecord) for item in records):
            raise ReviewAuditError("closure claim-gate inventory is invalid")
        if len({item.candidate.candidate_id for item in records}) != len(records):
            raise ReviewAuditError("closure claim-gate inventory has duplicates")
        object.__setattr__(self, "claim_gate_records", records)
        if not isinstance(self.publication_catalog, SourceDocumentCatalog):
            raise ReviewAuditError("closure publication catalog is invalid")
        if not isinstance(self.publication_factreasoner, FactReasonerRecord):
            raise ReviewAuditError("closure publication FactReasoner record is invalid")
        if not isinstance(self.publication_validation, PublicationValidationReport):
            raise ReviewAuditError("closure publication validation report is invalid")
        if not isinstance(self.final_factreasoner, FactReasonerRecord):
            raise ReviewAuditError("closure final FactReasoner record is invalid")
        if not isinstance(self.risk_catalog, RiskCatalog):
            raise ReviewAuditError("closure risk catalog is invalid")
        if not isinstance(self.privacy, PrivacyScanReport):
            raise ReviewAuditError("closure privacy report is invalid")
        if not isinstance(self.risk_mapping, dict):
            raise ReviewAuditError("closure risk mapping must be an object")
        # Freeze a finite-JSON copy so later caller mutation cannot alter the audit.
        object.__setattr__(
            self,
            "risk_mapping",
            json.loads(_canonical(self.risk_mapping)),
        )


@dataclass(frozen=True)
class ReviewedCandidateAudit:
    artifact_id: str
    target: dict[str, str]
    source_snapshot_sha256: str
    prior_omission_audit_sha256: str | None
    review_event_sha256s: tuple[str, ...]
    review_gate_record_sha256s: tuple[str, ...]
    fields: tuple[ReviewedFieldState, ...]
    source_present_omissions: tuple[str, ...]
    checks: tuple[ReviewAuditCheck, ...]
    verdict: str = PROVISIONAL_VERDICT
    audit_version: str = REVIEW_AUDIT_VERSION
    audit_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.audit_version != REVIEW_AUDIT_VERSION:
            raise ReviewAuditError("review audit version is unsupported")
        if self.verdict not in {PROVISIONAL_VERDICT, CLOSED_VERDICT}:
            raise ReviewAuditError("review audit verdict is unsupported")
        if not isinstance(self.artifact_id, str) or not self.artifact_id.startswith("card_"):
            raise ReviewAuditError("review audit artifact id is invalid")
        if set(self.target) != {"model_id", "revision"}:
            raise ReviewAuditError("review audit target is invalid")
        if not _DIGEST_RE.fullmatch(self.source_snapshot_sha256):
            raise ReviewAuditError("review audit source snapshot is invalid")
        if self.prior_omission_audit_sha256 is not None and not _DIGEST_RE.fullmatch(
            self.prior_omission_audit_sha256
        ):
            raise ReviewAuditError("review audit prior omission digest is invalid")
        for values in (
            self.review_event_sha256s,
            self.review_gate_record_sha256s,
        ):
            if any(not _DIGEST_RE.fullmatch(item) for item in values):
                raise ReviewAuditError("review audit history digest is invalid")
        if self.fields != tuple(
            sorted(self.fields, key=lambda item: CONTENT_FIELD_PATHS.index(item.field_path))
        ) or tuple(item.field_path for item in self.fields) != CONTENT_FIELD_PATHS:
            raise ReviewAuditError("review audit must cover every content field once")
        if self.source_present_omissions != tuple(sorted(set(self.source_present_omissions))):
            raise ReviewAuditError("review audit source-present omissions are invalid")
        if not all(isinstance(item, ReviewAuditCheck) for item in self.checks):
            raise ReviewAuditError("review audit checks are invalid")
        if tuple(item.name for item in self.checks) != _CHECK_NAMES:
            raise ReviewAuditError("review audit checks are incomplete or non-canonical")
        expected_verdict = (
            CLOSED_VERDICT
            if self.review_event_sha256s
            and all(item.status is ReviewAuditStatus.PASSED for item in self.checks)
            else PROVISIONAL_VERDICT
        )
        if self.verdict != expected_verdict:
            raise ReviewAuditError("review audit verdict disagrees with its checks")
        object.__setattr__(self, "audit_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "audit_version": self.audit_version,
            "artifact_id": self.artifact_id,
            "target": self.target,
            "source_snapshot_sha256": self.source_snapshot_sha256,
            "prior_omission_audit_sha256": self.prior_omission_audit_sha256,
            "review_event_sha256s": list(self.review_event_sha256s),
            "review_gate_record_sha256s": list(self.review_gate_record_sha256s),
            "fields": [item.to_dict() for item in self.fields],
            "source_present_omissions": list(self.source_present_omissions),
            "checks": [item.to_dict() for item in self.checks],
            "verdict": self.verdict,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "audit_sha256": self.audit_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "ReviewedCandidateAudit":
        expected = {
            "audit_version",
            "artifact_id",
            "target",
            "source_snapshot_sha256",
            "prior_omission_audit_sha256",
            "review_event_sha256s",
            "review_gate_record_sha256s",
            "fields",
            "source_present_omissions",
            "checks",
            "verdict",
            "audit_sha256",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ReviewAuditError("reviewed candidate audit has an invalid shape")
        for name in (
            "review_event_sha256s",
            "review_gate_record_sha256s",
            "fields",
            "source_present_omissions",
            "checks",
        ):
            if not isinstance(value[name], list):
                raise ReviewAuditError("reviewed candidate audit arrays are malformed")
        audit = cls(
            audit_version=value["audit_version"],
            artifact_id=value["artifact_id"],
            target=value["target"],
            source_snapshot_sha256=value["source_snapshot_sha256"],
            prior_omission_audit_sha256=value["prior_omission_audit_sha256"],
            review_event_sha256s=tuple(value["review_event_sha256s"]),
            review_gate_record_sha256s=tuple(value["review_gate_record_sha256s"]),
            fields=tuple(ReviewedFieldState.from_dict(item) for item in value["fields"]),
            source_present_omissions=tuple(value["source_present_omissions"]),
            checks=tuple(ReviewAuditCheck.from_dict(item) for item in value["checks"]),
            verdict=value["verdict"],
        )
        if value["audit_sha256"] != audit.audit_sha256:
            raise ReviewAuditError("reviewed candidate audit digest mismatch")
        return audit


def _source_snapshot(sources: tuple[SourceDocument, ...]) -> str:
    return _digest(
        sorted(
            (
                {
                    "source_id": source.source_id,
                    "source_uri": source.source_uri,
                    "source_revision": source.source_revision,
                    "source_sha256": source.sha256,
                    "target": None if source.target is None else source.target.to_dict(),
                }
                for source in sources
            ),
            key=lambda item: _canonical(item),
        )
    )


def _effective_review_candidates(
    artifact: CardArtifact,
) -> tuple[tuple[ClaimCandidate, ...], set[str]]:
    """Return lineage-preserving candidates and the currently included ids."""

    current = {
        binding.binding_id: ClaimCandidate.from_binding(artifact.target, binding)
        for binding in artifact.bindings
    }
    gates = {
        record.content_sha256: record for record in artifact.review_gate_records
    }
    for event in artifact.reviews:
        if event.action is not ReviewAction.REASSIGN:
            continue
        gate = gates.get(event.gate_record_sha256 or "")
        if gate is None:
            raise ReviewAuditError("review candidate lineage has no retained gate")
        current[event.binding_id] = gate.candidate
    effective = {
        binding.binding_id: binding for binding in artifact.effective_bindings()
    }
    candidates = tuple(sorted(current.values(), key=lambda item: item.candidate_id))
    included = {
        current[binding_id].candidate_id
        for binding_id, binding in effective.items()
        if binding.disposition is Disposition.ACCEPTED
    }
    return candidates, included


def _check(
    name: str,
    status: ReviewAuditStatus,
    reason: str,
    value: Any | None = None,
) -> ReviewAuditCheck:
    return ReviewAuditCheck(
        name=name,
        status=status,
        reason=reason,
        artifact_sha256=None if value is None else _digest(value),
    )


def _factreasoner_check(
    evidence: ReviewClosureEvidence,
    *,
    target: Any,
    final_card: Mapping[str, Any],
) -> ReviewAuditCheck:
    payload = {
        "publication_factreasoner_sha256": (
            evidence.publication_factreasoner.content_sha256
        ),
        "final_factreasoner_sha256": evidence.final_factreasoner.content_sha256,
        "final_card_sha256": _digest(final_card),
    }
    records = (
        evidence.publication_factreasoner,
        evidence.final_factreasoner,
    )
    if any(
        record.checker_id != _PINNED_FACTREASONER_CHECKER_ID
        or record.checker_revision != IBM_FACTREASONER_UPSTREAM_REVISION
        for record in records
    ):
        return _check(
            "factreasoner",
            ReviewAuditStatus.FAILED,
            "factreasoner_checker_identity_mismatch",
            payload,
        )
    try:
        if (
            evidence.publication_factreasoner.target != target
            or evidence.final_factreasoner.target != target
        ):
            raise ReviewAuditError("FactReasoner target mismatch")
        replayed = run_publication_validation(
            final_card, evidence.final_factreasoner
        )
        if replayed.final_card != dict(final_card):
            raise ReviewAuditError("final FactReasoner requires withholding")
    except (TypeError, ValueError, RuntimeError):
        return _check(
            "factreasoner",
            ReviewAuditStatus.FAILED,
            "factreasoner_record_mismatch",
            payload,
        )

    # The first record may legitimately identify fields for deletion.  The
    # replayed publication report accounts for those removals; sealing depends
    # on the final record fully supporting the retained card.
    decisions = evidence.final_factreasoner.decisions
    field_decisions = evidence.final_factreasoner.field_decisions
    if any(
        item.outcome in {CheckOutcome.CONTRADICTION, CheckOutcome.NEUTRAL}
        or item.field_action is FieldAction.REPAIR_OR_WITHHOLD
        for item in decisions
    ):
        return _check(
            "factreasoner",
            ReviewAuditStatus.FAILED,
            "factreasoner_support_failed",
            payload,
        )
    if any(
        item.outcome is CheckOutcome.UNAVAILABLE
        or item.field_action is FieldAction.COLLECT_OR_WITHHOLD
        for item in decisions
    ) or any(item.action is FieldAction.COLLECT_OR_WITHHOLD for item in field_decisions):
        return _check(
            "factreasoner",
            ReviewAuditStatus.UNAVAILABLE,
            "factreasoner_checks_unavailable",
            payload,
        )
    # FactReasonerRecord intentionally carries only the outer checker identity.
    # It does not retain IBM inference traces or the injected NLI provider/model
    # receipts, so matching the public identity is necessary but not proof that
    # the pinned implementation executed.  Keep closure unavailable until a
    # retained, replayable execution binding is part of the closure contract.
    return _check(
        "factreasoner",
        ReviewAuditStatus.UNAVAILABLE,
        "factreasoner_execution_binding_unavailable",
        payload,
    )


def _claim_support_check(
    evidence: ReviewClosureEvidence,
    *,
    artifact: CardArtifact,
    sources: tuple[SourceDocument, ...],
    candidates: tuple[ClaimCandidate, ...],
    included_ids: set[str],
) -> ReviewAuditCheck:
    records = evidence.claim_gate_records + artifact.review_gate_records
    payload = [item.to_dict() for item in records]
    try:
        by_id: dict[str, ClaimGateRecord] = {}
        for record in records:
            if record.candidate.target != artifact.target:
                raise ReviewAuditError("claim-gate target mismatch")
            verify_claim_gate_record(record, sources)
            existing = by_id.setdefault(record.candidate.candidate_id, record)
            if existing.to_dict() != record.to_dict():
                raise ReviewAuditError("claim-gate candidate is ambiguous")
        current = {item.candidate_id: item for item in candidates}
        for candidate_id in included_ids:
            record = by_id.get(candidate_id)
            if (
                record is None
                or not record.projection_eligible
                or record.candidate.to_dict() != current[candidate_id].to_dict()
            ):
                raise ReviewAuditError("included candidate lacks a current claim gate")
    except (KeyError, TypeError, ValueError):
        return _check(
            "claim_support",
            ReviewAuditStatus.FAILED,
            "claim_support_replay_mismatch",
            payload,
        )
    return _check(
        "claim_support",
        ReviewAuditStatus.PASSED,
        "effective_claim_gates_replayed",
        payload,
    )


@dataclass(frozen=True)
class _ReviewSourceCatalog:
    documents: tuple[SourceDocument, ...]


def _privacy_check(
    evidence: ReviewClosureEvidence,
    *,
    final_card: Mapping[str, Any],
    candidates: tuple[ClaimCandidate, ...],
    included_ids: set[str],
    sources: tuple[SourceDocument, ...],
) -> ReviewAuditCheck:
    try:
        replayed = _privacy_scan_final_projection(
            final_card,
            candidates,
            included_ids,
            (),
            _ReviewSourceCatalog(sources),
        )
    except (TypeError, ValueError, RuntimeError):
        return _check(
            "privacy",
            ReviewAuditStatus.FAILED,
            "privacy_execution_replay_failed",
            evidence.privacy.to_dict(),
        )
    if replayed.to_dict() != evidence.privacy.to_dict():
        return _check(
            "privacy",
            ReviewAuditStatus.FAILED,
            "privacy_execution_replay_mismatch",
            evidence.privacy.to_dict(),
        )
    return _check(
        "privacy",
        ReviewAuditStatus.PASSED,
        "privacy_execution_replayed",
        replayed.to_dict(),
    )


def _risk_check(
    evidence: ReviewClosureEvidence,
    artifact: CardArtifact,
    candidates: tuple[ClaimCandidate, ...],
    included_ids: set[str],
) -> ReviewAuditCheck:
    value = evidence.risk_mapping
    try:
        if set(value) != {
            "summary",
            "use_contexts",
            "taxonomy_derivations",
            "factreasoner_withheld_derivation_ids",
            "taxonomy_mapping",
        }:
            raise ReviewAuditError("risk artifact shape mismatch")
        summary = RiskStageSummary.from_dict(value["summary"])
        if not all(
            isinstance(value[name], list)
            for name in (
                "use_contexts",
                "taxonomy_derivations",
                "factreasoner_withheld_derivation_ids",
            )
        ):
            raise ReviewAuditError("risk artifact arrays are malformed")
        contexts = tuple(UseContext.from_dict(item) for item in value["use_contexts"])
        if contexts != tuple(sorted(contexts, key=lambda item: item.context_id)):
            raise ReviewAuditError("risk contexts are non-canonical")
        expected_contexts = _model_use_contexts(candidates, included_ids)
        if tuple(item.to_dict() for item in contexts) != tuple(
            item.to_dict() for item in expected_contexts
        ):
            raise ReviewAuditError("risk contexts do not match reviewed candidates")
        if summary.context_sha256 != _digest([item.to_dict() for item in contexts]):
            raise ReviewAuditError("risk context digest mismatch")

        core_paths = {
            "use_and_risk.intended_uses",
            "use_and_risk.out_of_scope_uses",
        }
        core_ids = {
            item.candidate_id
            for item in candidates
            if item.candidate_id in included_ids
            and canonical_field_path(item.field_path) in core_paths
        }
        publisher_context_ids = tuple(
            sorted(
                {
                    candidate_id
                    for context in contexts
                    for candidate_id in context.supporting_candidate_ids
                    if candidate_id in core_ids
                }
            )
        )
        publisher_risk_ids = tuple(
            sorted(
                item.candidate_id
                for item in candidates
                if item.candidate_id in included_ids
                and canonical_field_path(item.field_path)
                == "use_and_risk.identified_risks"
                and isinstance(item.value, dict)
                and item.value.get("identification_origin") == "publisher_reported"
            )
        )
        if (
            summary.publisher_context_candidate_ids != publisher_context_ids
            or summary.publisher_reported_risk_candidate_ids != publisher_risk_ids
        ):
            raise ReviewAuditError("risk candidate indexes are stale")

        withheld = tuple(value["factreasoner_withheld_derivation_ids"])
        if withheld != tuple(sorted(set(withheld))) or withheld:
            raise ReviewAuditError("risk derivations remain withheld")
        derivations = tuple(
            TaxonomyRiskDerivation.from_dict(item)
            for item in value["taxonomy_derivations"]
        )
        candidate_by_id = {item.candidate_id: item for item in candidates}
        for derivation in derivations:
            if derivation.target != artifact.target:
                raise ReviewAuditError("risk derivation target is stale")
            for claim in derivation.input_claims:
                candidate = candidate_by_id.get(claim.candidate_id)
                if (
                    candidate is None
                    or claim.candidate_id not in included_ids
                    or claim.candidate_sha256 != candidate.content_sha256
                ):
                    raise ReviewAuditError("risk derivation input is stale")

        mapping = value["taxonomy_mapping"]
        if mapping is None:
            if (
                summary.status != "unavailable"
                or summary.catalog_sha256 is not None
                or summary.mapping_report_sha256 is not None
                or derivations
            ):
                raise ReviewAuditError("missing risk mapping disagrees with summary")
            return _check(
                "risk",
                ReviewAuditStatus.UNAVAILABLE,
                "risk_revalidation_unavailable",
                value,
            )
        typed_mapping = RiskMappingReport.from_dict(mapping)
        replayed_mapping = replay_risk_mapping(
            contexts, evidence.risk_catalog, typed_mapping
        )
        if (
            typed_mapping.to_dict() != mapping
            or replayed_mapping.to_dict() != mapping
            or typed_mapping.catalog_sha256 != summary.catalog_sha256
            or typed_mapping.context_sha256 != summary.context_sha256
            or typed_mapping.report_sha256 != summary.mapping_report_sha256
            or typed_mapping.status.value != summary.status
            or typed_mapping.reason != summary.reason
            or len(typed_mapping.candidates) != summary.taxonomy_candidate_count
            or len(typed_mapping.included_risks)
            != summary.taxonomy_included_count
            or len(derivations) != summary.taxonomy_included_count
            or evidence.risk_catalog.catalog_sha256 != summary.catalog_sha256
        ):
            raise ReviewAuditError("risk summary and mapping disagree")
        if summary.status == "unavailable":
            return _check(
                "risk",
                ReviewAuditStatus.UNAVAILABLE,
                "risk_revalidation_unavailable",
                value,
            )
        if not summary.passed:
            raise ReviewAuditError("completed risk mapping did not pass")
        if contexts:
            # The typed record proves that the retained selections and decisions
            # still bind the reviewed contexts and pinned catalog.  Closure also
            # needs proof that those semantic decisions came from the admitted
            # provider execution; that receipt is not yet part of this artifact.
            return _check(
                "risk",
                ReviewAuditStatus.UNAVAILABLE,
                "risk_execution_replay_unavailable",
                value,
            )
        if derivations:
            raise ReviewAuditError("empty-context risk replay retained derivations")
    except (KeyError, TypeError, ValueError):
        return _check(
            "risk",
            ReviewAuditStatus.FAILED,
            "risk_revalidation_mismatch",
            value,
        )
    return _check(
        "risk",
        ReviewAuditStatus.PASSED,
        "risk_execution_replayed",
        value,
    )


def audit_reviewed_candidate(
    artifact: CardArtifact,
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    *,
    prior_omission_audit: OmissionAudit | None = None,
    closure_evidence: ReviewClosureEvidence | None = None,
) -> ReviewedCandidateAudit:
    """Replay a reviewed artifact and return a body-free, content-addressed audit."""

    if not isinstance(artifact, CardArtifact):
        raise ReviewAuditError("review audit requires a CardArtifact")
    artifact.validate_integrity()
    source_values = tuple(sources.values()) if isinstance(sources, Mapping) else tuple(sources)
    if not source_values or not all(
        isinstance(item, SourceDocument) for item in source_values
    ):
        raise ReviewAuditError("review audit requires typed replay sources")
    verify_artifact_sources(artifact, source_values)
    if prior_omission_audit is not None:
        OmissionAudit.from_dict(prior_omission_audit.to_dict())
    for record in artifact.review_gate_records:
        verify_claim_gate_record(record, source_values)
    card = project_card(artifact)
    validate_public_card(card)

    prior_by_field = (
        {}
        if prior_omission_audit is None
        else {item.field_path: item for item in prior_omission_audit.records}
    )
    original_by_id = {item.binding_id: item for item in artifact.bindings}
    effective = artifact.effective_bindings()
    effective_by_base: dict[str, list[Any]] = {}
    for binding in effective:
        effective_by_base.setdefault(canonical_field_path(binding.field_path), []).append(
            binding
        )
    moved_from: set[str] = set()
    for event in artifact.reviews:
        if event.action is not ReviewAction.REASSIGN or event.field_path is None:
            continue
        original = original_by_id[event.binding_id]
        old_base = canonical_field_path(original.field_path)
        if old_base != canonical_field_path(event.field_path):
            moved_from.add(old_base)

    fields: list[ReviewedFieldState] = []
    for field_path in CONTENT_FIELD_PATHS:
        value = get_field(card, field_path)
        present = value not in (NOT_SPECIFIED, NOT_APPLICABLE)
        bindings = effective_by_base.get(field_path, ())
        if present:
            state = ReviewedFieldState(field_path, True, bool(bindings), None)
        elif any(item.disposition is not Disposition.ACCEPTED for item in bindings):
            state = ReviewedFieldState(
                field_path,
                False,
                True,
                ReviewedOmissionReason.WITHHELD,
            )
        elif field_path in moved_from:
            state = ReviewedFieldState(
                field_path,
                False,
                True,
                ReviewedOmissionReason.REASSIGNED,
            )
        elif field_path in prior_by_field:
            prior = prior_by_field[field_path]
            state = ReviewedFieldState(
                field_path,
                False,
                prior.source_present,
                ReviewedOmissionReason.PRIOR_SOURCE_STATE,
            )
        else:
            state = ReviewedFieldState(
                field_path,
                False,
                False,
                ReviewedOmissionReason.NOT_FOUND,
            )
        fields.append(state)

    source_present = tuple(
        sorted(
            item.field_path
            for item in fields
            if not item.present and item.source_present
        )
    )
    snapshot = _source_snapshot(source_values)
    candidates, included_ids = _effective_review_candidates(artifact)
    checks: list[ReviewAuditCheck] = [
        _check(
            "artifact_integrity",
            ReviewAuditStatus.PASSED,
            "artifact_and_sources_replayed",
            artifact.to_dict(),
        ),
        _check(
            "review_reassignment_gates",
            ReviewAuditStatus.PASSED,
            "review_reassignment_gates_replayed",
            [item.to_dict() for item in artifact.review_gate_records],
        ),
        _check(
            "omissions",
            ReviewAuditStatus.PASSED,
            "effective_omissions_recomputed",
            {
                "artifact_sha256": _digest(artifact.to_dict()),
                "fields": [item.to_dict() for item in fields],
                "effective_candidate_sha256s": [
                    item.content_sha256
                    for item in candidates
                    if item.candidate_id in included_ids
                ],
            },
        ),
        _check(
            "public_schema",
            ReviewAuditStatus.PASSED,
            "effective_card_schema_valid",
            card,
        ),
        (
            _check(
                "review_history",
                ReviewAuditStatus.PASSED,
                "review_history_present",
                [item.to_dict() for item in artifact.reviews],
            )
            if artifact.reviews
            else _check(
                "review_history",
                ReviewAuditStatus.UNAVAILABLE,
                "review_history_empty",
            )
        ),
    ]
    if closure_evidence is None:
        checks.extend(
            (
                _check(
                    "claim_support",
                    ReviewAuditStatus.UNAVAILABLE,
                    "original_claim_gates_not_supplied",
                ),
                _check(
                    "factreasoner",
                    ReviewAuditStatus.UNAVAILABLE,
                    "factreasoner_revalidation_not_supplied",
                ),
                _check(
                    "privacy",
                    ReviewAuditStatus.UNAVAILABLE,
                    "privacy_revalidation_not_supplied",
                ),
                _check(
                    "publication",
                    ReviewAuditStatus.UNAVAILABLE,
                    "publication_revalidation_not_supplied",
                ),
                _check(
                    "risk",
                    ReviewAuditStatus.UNAVAILABLE,
                    "risk_revalidation_not_supplied",
                ),
            )
        )
    else:
        checks.append(
            _claim_support_check(
                closure_evidence,
                artifact=artifact,
                sources=source_values,
                candidates=candidates,
                included_ids=included_ids,
            )
        )
        pre_publication: Mapping[str, Any] | None = None
        publication_catalog_sha256: str | None = None
        publication_provenance_sha256: str | None = None
        final_publication: Mapping[str, Any] | None = None
        try:
            publication_catalog = closure_evidence.publication_catalog
            if publication_catalog.target != artifact.target:
                raise ReviewAuditError("publication catalog target mismatch")
            available_sources = {item.source_id: item for item in source_values}
            if any(
                available_sources.get(document.source_id) != document
                for document in publication_catalog.documents
            ):
                raise ReviewAuditError(
                    "publication catalog is not bound to the replay sources"
                )
            enrichment = enrich_publication_card(
                publication_catalog,
                project_publication_card(card),
            )
            pre_publication = enrichment.card
            publication_catalog_sha256 = publication_catalog.catalog_sha256
            publication_provenance_sha256 = _digest(
                enrichment.provenance_dict()
            )
            if (
                closure_evidence.publication_factreasoner.target != artifact.target
            ):
                raise ReviewAuditError("publication FactReasoner target mismatch")
            publication_outcome = replay_publication_validation(
                closure_evidence.publication_validation,
                pre_publication,
                closure_evidence.publication_factreasoner,
            )
            final_publication = publication_outcome.final_card
        except (TypeError, ValueError):
            checks.append(
                _check(
                    "publication",
                    ReviewAuditStatus.FAILED,
                    "publication_revalidation_mismatch",
                    {
                        "effective_card_sha256": _digest(card),
                        "report_sha256": (
                            closure_evidence.publication_validation.content_sha256
                        ),
                    },
                )
            )
        else:
            checks.append(
                _check(
                    "publication",
                    ReviewAuditStatus.PASSED,
                    "publication_revalidation_replayed",
                    {
                        "effective_card_sha256": _digest(card),
                        "publication_catalog_sha256": publication_catalog_sha256,
                        "publication_provenance_sha256": publication_provenance_sha256,
                        "publication_snapshot_sha256": _digest(pre_publication),
                        "pre_publication_card_sha256": _digest(pre_publication),
                        "final_publication_card_sha256": _digest(final_publication),
                        "report_sha256": (
                            closure_evidence.publication_validation.content_sha256
                        ),
                    },
                )
            )

        if final_publication is None:
            checks.append(
                _check(
                    "factreasoner",
                    ReviewAuditStatus.FAILED,
                    "factreasoner_publication_unavailable",
                    {
                        "publication_factreasoner_sha256": (
                            closure_evidence.publication_factreasoner.content_sha256
                        ),
                        "final_factreasoner_sha256": (
                            closure_evidence.final_factreasoner.content_sha256
                        ),
                    },
                )
            )
            checks.append(
                _check(
                    "privacy",
                    ReviewAuditStatus.FAILED,
                    "privacy_publication_unavailable",
                    closure_evidence.privacy.to_dict(),
                )
            )
        else:
            checks.append(
                _factreasoner_check(
                    closure_evidence,
                    target=artifact.target,
                    final_card=final_publication,
                )
            )
            checks.append(
                _privacy_check(
                    closure_evidence,
                    final_card=final_publication,
                    candidates=candidates,
                    included_ids=included_ids,
                    sources=source_values,
                )
            )
        checks.append(
            _risk_check(
                closure_evidence,
                artifact,
                candidates,
                included_ids,
            )
        )

    checks_tuple = tuple(sorted(checks, key=lambda item: item.name))
    verdict = (
        CLOSED_VERDICT
        if artifact.reviews
        and all(item.status is ReviewAuditStatus.PASSED for item in checks_tuple)
        else PROVISIONAL_VERDICT
    )
    return ReviewedCandidateAudit(
        artifact_id=artifact.artifact_id,
        target=artifact.target.to_dict(),
        source_snapshot_sha256=snapshot,
        prior_omission_audit_sha256=(
            None
            if prior_omission_audit is None
            else prior_omission_audit.content_sha256
        ),
        review_event_sha256s=tuple(
            event.content_sha256 for event in artifact.reviews
        ),
        review_gate_record_sha256s=tuple(
            record.content_sha256 for record in artifact.review_gate_records
        ),
        fields=tuple(fields),
        source_present_omissions=source_present,
        checks=checks_tuple,
        verdict=verdict,
    )


def verify_reviewed_candidate_audit(
    audit: ReviewedCandidateAudit,
    artifact: CardArtifact,
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    *,
    prior_omission_audit: OmissionAudit | None = None,
    closure_evidence: ReviewClosureEvidence | None = None,
) -> None:
    """Recompute the complete review audit and reject any drift."""

    if not isinstance(audit, ReviewedCandidateAudit):
        raise ReviewAuditError("review audit replay requires a typed audit")
    replayed = audit_reviewed_candidate(
        artifact,
        sources,
        prior_omission_audit=prior_omission_audit,
        closure_evidence=closure_evidence,
    )
    if _canonical(audit.to_dict()) != _canonical(replayed.to_dict()):
        raise ReviewAuditError("reviewed candidate audit replay mismatch")


__all__ = [
    "CLOSED_VERDICT",
    "PROVISIONAL_VERDICT",
    "REVIEW_AUDIT_VERSION",
    "ReviewClosureEvidence",
    "ReviewAuditCheck",
    "ReviewAuditError",
    "ReviewAuditStatus",
    "ReviewedCandidateAudit",
    "ReviewedFieldState",
    "ReviewedOmissionReason",
    "audit_reviewed_candidate",
    "verify_reviewed_candidate_audit",
]
