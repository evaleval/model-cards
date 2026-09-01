"""Bounded, field-local repair and mandatory re-audit records.

Repair is deliberately narrower than composition.  A proposal may replace one
claim candidate, but it cannot change the target or field, draw evidence from a
different field, or become usable merely because a semantic checker approved
it.  The four Claim Support Gate decisions are replayed first.  A gate-eligible
proposal is then accepted only when schema/scope, FactReasoner, omission, risk,
and privacy re-audits all pass against the repaired composition.

The serialized record contains bounded evidence snippets through the existing
``ClaimCandidate`` contract, but never source bodies, prompts, provider traces,
usage ledgers, or local paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from .claim_gate import (
    GATE_ORDER,
    ClaimCandidate,
    ClaimGateRecord,
    ProseCheckerDecision,
    evaluate_claim_gate,
)
from .composer import CompositionResult, verify_composition_result
from .factreasoner import CheckOutcome, FactReasonerRecord, FieldAction
from .findings import (
    FieldAuditStatus,
    FieldAvailabilityHint,
    OmissionAudit,
    OmissionReason,
    verify_omission_audit,
)
from .models import Evidence, SourceDocument, TargetIdentity
from .public_export import SENSITIVE_TEXT, assert_public_projection
from .risk_mapping import MappingStatus, RiskMappingReport
from .schema import CONTENT_FIELD_PATHS, canonical_field_path, get_field, validate_public_card


FIELD_REPAIR_VERSION = "bounded-field-repair/v1"
MAX_SEMANTIC_ATTEMPTS_PER_FIELD = 2
MAX_REPAIR_EVIDENCE_ITEMS = 16
MAX_REPAIR_QUOTE_CHARS = 1_200
MAX_REPAIR_FRAGMENT_JSON_CHARS = 8_000
MAX_REPAIR_PROPOSAL_JSON_CHARS = 32_000

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")


class FieldRepairError(ValueError):
    """Repair material is unsafe, incomplete, stale, or out of scope."""


class FieldRepairReplayError(FieldRepairError):
    """A serialized repair record no longer replays from its frozen inputs."""


class RepairFinding(str, Enum):
    FACTREASONER_REPAIR_OR_WITHHOLD = "factreasoner_repair_or_withhold"
    FACTREASONER_COLLECT_OR_WITHHOLD = "factreasoner_collect_or_withhold"
    SOURCE_PRESENT_OMISSION = "source_present_omission"
    OMITTED_CONFLICT = "omitted_conflict"
    MISSED_BY_COMPOSITION = "missed_by_composition"
    COMPOSITION_CONFLICT = "composition_conflict"


class AttemptDisposition(str, Enum):
    GATE_WITHHELD = "gate_withheld"
    REAUDIT_WITHHELD = "reaudit_withheld"
    ACCEPTED = "accepted"


class RepairOutcome(str, Enum):
    REPAIRED = "repaired"
    WITHHELD = "withheld"


class RepairReason(str, Enum):
    ALL_CHECKS_PASSED = "all_checks_passed"
    FOUR_PART_GATE_WITHHELD = "four_part_gate_withheld"
    DOWNSTREAM_REAUDIT_FAILED = "downstream_reaudit_failed"
    DOWNSTREAM_REAUDIT_UNAVAILABLE = "downstream_reaudit_unavailable"
    SEMANTIC_ATTEMPT_LIMIT_EXHAUSTED = "semantic_attempt_limit_exhausted"
    NO_ACCEPTED_RELEVANT_EVIDENCE = "no_accepted_relevant_evidence"
    EXPLICIT_WITHHOLD = "explicit_withhold"


class ReauditName(str, Enum):
    SCHEMA = "schema"
    FACTREASONER = "factreasoner"
    OMISSION = "omission"
    RISK = "risk"
    PRIVACY = "privacy"


class ReauditStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


REAUDIT_ORDER: tuple[ReauditName, ...] = (
    ReauditName.SCHEMA,
    ReauditName.FACTREASONER,
    ReauditName.OMISSION,
    ReauditName.RISK,
    ReauditName.PRIVACY,
)

_MUTABLE_COMPONENTS = (
    "value",
    "evidence",
    "claim_entity",
    "relation",
    "benchmark_scope",
)


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
        raise FieldRepairError("repair values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise FieldRepairError(f"{label} has an invalid shape")
    return value


def _require_digest(value: Any, label: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise FieldRepairError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _evidence_sha256(evidence: Evidence) -> str:
    if not isinstance(evidence, Evidence):
        raise FieldRepairError("repair evidence must use typed Evidence records")
    payload = evidence.to_dict()
    if evidence.quote is not None and len(evidence.quote) > MAX_REPAIR_QUOTE_CHARS:
        raise FieldRepairError("repair quote exceeds the bounded evidence window")
    if (
        evidence.fragment is not None
        and len(_canonical(evidence.fragment)) > MAX_REPAIR_FRAGMENT_JSON_CHARS
    ):
        raise FieldRepairError("repair fragment exceeds the bounded evidence window")
    if SENSITIVE_TEXT.search(_canonical(payload)):
        raise FieldRepairError("repair evidence contains private or local-path material")
    return _digest(payload)


def _eligible_evidence_sha256(evidence: Evidence) -> str | None:
    try:
        return _evidence_sha256(evidence)
    except FieldRepairError:
        return None


def _inventory_sha256(candidates: Sequence[ClaimCandidate]) -> str:
    return _digest(
        [
            {"candidate_id": item.candidate_id, "sha256": item.content_sha256}
            for item in sorted(candidates, key=lambda item: item.candidate_id)
        ]
    )


def _gate_inventory_sha256(records: Sequence[ClaimGateRecord]) -> str:
    return _digest(
        [
            {
                "candidate_id": item.candidate.candidate_id,
                "sha256": item.content_sha256,
            }
            for item in sorted(records, key=lambda item: item.candidate.candidate_id)
        ]
    )


def _target_from_dict(value: Any) -> TargetIdentity:
    item = _strict(value, {"model_id", "revision"}, "repair target")
    return TargetIdentity.from_dict(item)


def _candidate_equal(left: ClaimCandidate, right: ClaimCandidate) -> bool:
    return _canonical(left.to_dict()) == _canonical(right.to_dict())


@dataclass(frozen=True)
class FieldRepairContext:
    """Source-free summary of the exact field findings and evidence allowlist."""

    field_path: str
    base_field_path: str
    target: TargetIdentity
    predecessor_candidate_id: str
    predecessor_candidate_sha256: str
    composition_result_sha256: str
    omission_audit_sha256: str
    factreasoner_record_sha256: str
    candidate_inventory_sha256: str
    gate_inventory_sha256: str
    allowed_evidence_sha256s: tuple[str, ...]
    findings: tuple[RepairFinding, ...]
    context_version: str = FIELD_REPAIR_VERSION
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.context_version != FIELD_REPAIR_VERSION:
            raise FieldRepairError("repair context version is not recognized")
        if not isinstance(self.target, TargetIdentity):
            raise FieldRepairError("repair context target is malformed")
        try:
            base = canonical_field_path(self.field_path)
        except (TypeError, ValueError) as exc:
            raise FieldRepairError("repair context field is invalid") from exc
        if self.base_field_path != base or base not in CONTENT_FIELD_PATHS:
            raise FieldRepairError("repair context base field is stale")
        if not isinstance(self.predecessor_candidate_id, str) or not _CANDIDATE_RE.fullmatch(
            self.predecessor_candidate_id
        ):
            raise FieldRepairError("repair predecessor candidate id is invalid")
        for name in (
            "predecessor_candidate_sha256",
            "composition_result_sha256",
            "omission_audit_sha256",
            "factreasoner_record_sha256",
            "candidate_inventory_sha256",
            "gate_inventory_sha256",
        ):
            _require_digest(getattr(self, name), name)
        evidence = tuple(self.allowed_evidence_sha256s)
        if evidence != tuple(sorted(set(evidence))) or any(
            not isinstance(item, str) or not _DIGEST_RE.fullmatch(item) for item in evidence
        ):
            raise FieldRepairError("allowed evidence manifest is not canonical")
        findings = tuple(RepairFinding(item) for item in self.findings)
        if not findings or findings != tuple(sorted(set(findings), key=lambda item: item.value)):
            raise FieldRepairError("repair context requires canonical actionable findings")
        object.__setattr__(self, "allowed_evidence_sha256s", evidence)
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "context_version": self.context_version,
            "field_path": self.field_path,
            "base_field_path": self.base_field_path,
            "target": self.target.to_dict(),
            "predecessor_candidate_id": self.predecessor_candidate_id,
            "predecessor_candidate_sha256": self.predecessor_candidate_sha256,
            "composition_result_sha256": self.composition_result_sha256,
            "omission_audit_sha256": self.omission_audit_sha256,
            "factreasoner_record_sha256": self.factreasoner_record_sha256,
            "candidate_inventory_sha256": self.candidate_inventory_sha256,
            "gate_inventory_sha256": self.gate_inventory_sha256,
            "allowed_evidence_sha256s": list(self.allowed_evidence_sha256s),
            "findings": [item.value for item in self.findings],
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "context_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "FieldRepairContext":
        item = _strict(
            value,
            {
                "context_version",
                "field_path",
                "base_field_path",
                "target",
                "predecessor_candidate_id",
                "predecessor_candidate_sha256",
                "composition_result_sha256",
                "omission_audit_sha256",
                "factreasoner_record_sha256",
                "candidate_inventory_sha256",
                "gate_inventory_sha256",
                "allowed_evidence_sha256s",
                "findings",
                "context_sha256",
            },
            "field repair context",
        )
        if not isinstance(item["allowed_evidence_sha256s"], list) or not isinstance(
            item["findings"], list
        ):
            raise FieldRepairError("repair context arrays are malformed")
        context = cls(
            context_version=item["context_version"],
            field_path=item["field_path"],
            base_field_path=item["base_field_path"],
            target=_target_from_dict(item["target"]),
            predecessor_candidate_id=item["predecessor_candidate_id"],
            predecessor_candidate_sha256=item["predecessor_candidate_sha256"],
            composition_result_sha256=item["composition_result_sha256"],
            omission_audit_sha256=item["omission_audit_sha256"],
            factreasoner_record_sha256=item["factreasoner_record_sha256"],
            candidate_inventory_sha256=item["candidate_inventory_sha256"],
            gate_inventory_sha256=item["gate_inventory_sha256"],
            allowed_evidence_sha256s=tuple(item["allowed_evidence_sha256s"]),
            findings=tuple(item["findings"]),
        )
        if item["context_sha256"] != context.content_sha256:
            raise FieldRepairError("repair context digest mismatch")
        return context


def prepare_field_repair(
    *,
    field_path: str,
    predecessor_candidate_id: str,
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    composition_result: CompositionResult,
    omission_audit: OmissionAudit,
    factreasoner_record: FactReasonerRecord,
    availability_hints: Iterable[FieldAvailabilityHint] = (),
) -> FieldRepairContext:
    """Validate one actionable field and build its accepted-evidence allowlist."""

    candidate_values = tuple(candidates)
    gate_values = tuple(gate_records)
    source_values = tuple(sources.values()) if isinstance(sources, Mapping) else tuple(sources)
    hint_values = tuple(availability_hints)
    if not candidate_values or not all(
        isinstance(item, ClaimCandidate) for item in candidate_values
    ):
        raise FieldRepairError("repair candidate inventory is empty or malformed")
    if not all(isinstance(item, ClaimGateRecord) for item in gate_values):
        raise FieldRepairError("repair gate inventory is malformed")
    if not isinstance(composition_result, CompositionResult):
        raise FieldRepairError("repair requires a CompositionResult")
    if not isinstance(omission_audit, OmissionAudit):
        raise FieldRepairError("repair requires an OmissionAudit")
    if not isinstance(factreasoner_record, FactReasonerRecord):
        raise FieldRepairError("repair requires a FactReasonerRecord")
    try:
        base = canonical_field_path(field_path)
    except (TypeError, ValueError) as exc:
        raise FieldRepairError("repair field is invalid") from exc
    if base not in CONTENT_FIELD_PATHS:
        raise FieldRepairError("repair field is outside the public contract")

    verify_composition_result(
        composition_result,
        candidate_values,
        gate_values,
        source_values,
    )
    verify_omission_audit(
        omission_audit,
        candidate_values,
        gate_values,
        composition_result,
        hint_values,
    )
    factreasoner_record.validate_integrity()
    if factreasoner_record.target != composition_result.plan.target:
        raise FieldRepairError("FactReasoner target differs from the composition target")
    if factreasoner_record.card_sha256 != composition_result.card_sha256:
        raise FieldRepairError("FactReasoner record is stale for the composition card")

    by_id = {item.candidate_id: item for item in candidate_values}
    if len(by_id) != len(candidate_values):
        raise FieldRepairError("repair candidate inventory has duplicate identifiers")
    predecessor = by_id.get(predecessor_candidate_id)
    if predecessor is None:
        raise FieldRepairError("repair predecessor is absent from the candidate inventory")
    if predecessor.field_path != field_path:
        raise FieldRepairError("repair predecessor does not belong to the exact field")
    gates_by_id = {item.candidate.candidate_id: item for item in gate_values}
    if len(gates_by_id) != len(gate_values) or set(gates_by_id) != set(by_id):
        raise FieldRepairError("repair candidate/gate inventory is incomplete")
    findings: set[RepairFinding] = set()
    for decision in factreasoner_record.field_decisions:
        if canonical_field_path(decision.field_path) != base:
            continue
        if decision.action is FieldAction.REPAIR_OR_WITHHOLD:
            findings.add(RepairFinding.FACTREASONER_REPAIR_OR_WITHHOLD)
        elif decision.action is FieldAction.COLLECT_OR_WITHHOLD:
            findings.add(RepairFinding.FACTREASONER_COLLECT_OR_WITHHOLD)
    omission_record = next(
        (item for item in omission_audit.records if item.field_path == base), None
    )
    if omission_record is None:  # defensive; OmissionAudit already requires full coverage
        raise FieldRepairError("omission audit does not cover the repair field")
    if omission_record.status is FieldAuditStatus.OMITTED and omission_record.source_present:
        findings.add(RepairFinding.SOURCE_PRESENT_OMISSION)
    if omission_record.reason is OmissionReason.CONFLICTING:
        findings.add(RepairFinding.OMITTED_CONFLICT)
    if omission_record.reason is OmissionReason.MISSED_BY_COMPOSITION:
        findings.add(RepairFinding.MISSED_BY_COMPOSITION)
    if any(
        canonical_field_path(item.field_path) == base
        for item in composition_result.plan.conflicts
    ):
        findings.add(RepairFinding.COMPOSITION_CONFLICT)
    if not findings:
        raise FieldRepairError(
            "field has no actionable FactReasoner, omission, or conflict finding"
        )

    allowed = {
        digest
        for candidate in candidate_values
        if candidate.field_path == field_path
        and gates_by_id[candidate.candidate_id].projection_eligible
        for evidence in candidate.evidence
        for digest in (_eligible_evidence_sha256(evidence),)
        if digest is not None
    }
    return FieldRepairContext(
        field_path=field_path,
        base_field_path=base,
        target=composition_result.plan.target,
        predecessor_candidate_id=predecessor.candidate_id,
        predecessor_candidate_sha256=predecessor.content_sha256,
        composition_result_sha256=composition_result.content_sha256,
        omission_audit_sha256=omission_audit.content_sha256,
        factreasoner_record_sha256=factreasoner_record.content_sha256,
        candidate_inventory_sha256=_inventory_sha256(candidate_values),
        gate_inventory_sha256=_gate_inventory_sha256(gate_values),
        allowed_evidence_sha256s=tuple(sorted(allowed)),
        findings=tuple(sorted(findings, key=lambda item: item.value)),
    )


@dataclass(frozen=True)
class RepairProposal:
    """One immutable semantic proposal, before the gate is run."""

    candidate: ClaimCandidate
    checker_decisions: tuple[ProseCheckerDecision, ...] = ()
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, ClaimCandidate):
            raise FieldRepairError("repair proposal candidate is malformed")
        self.candidate.validate_integrity()
        if len(self.candidate.evidence) > MAX_REPAIR_EVIDENCE_ITEMS:
            raise FieldRepairError("repair proposal exceeds the evidence-item bound")
        for evidence in self.candidate.evidence:
            _evidence_sha256(evidence)
        candidate_json = _canonical(self.candidate.to_dict())
        if len(candidate_json) > MAX_REPAIR_PROPOSAL_JSON_CHARS:
            raise FieldRepairError("repair proposal exceeds the bounded JSON size")
        if SENSITIVE_TEXT.search(candidate_json):
            raise FieldRepairError("repair proposal contains private or local-path material")
        decisions = tuple(self.checker_decisions)
        if not all(isinstance(item, ProseCheckerDecision) for item in decisions):
            raise FieldRepairError("repair proposal checker decisions are malformed")
        if decisions != tuple(
            sorted(decisions, key=lambda item: GATE_ORDER.index(item.gate))
        ):
            raise FieldRepairError("repair proposal checker decisions are not canonical")
        if len({item.gate for item in decisions}) != len(decisions):
            raise FieldRepairError("repair proposal has duplicate checker decisions")
        object.__setattr__(self, "checker_decisions", decisions)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "checker_decisions": [item.to_dict() for item in self.checker_decisions],
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "proposal_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "RepairProposal":
        item = _strict(
            value,
            {"candidate", "checker_decisions", "proposal_sha256"},
            "repair proposal",
        )
        if not isinstance(item["checker_decisions"], list):
            raise FieldRepairError("repair proposal checker_decisions must be an array")
        proposal = cls(
            candidate=ClaimCandidate.from_dict(item["candidate"]),
            checker_decisions=tuple(
                ProseCheckerDecision.from_dict(entry)
                for entry in item["checker_decisions"]
            ),
        )
        if item["proposal_sha256"] != proposal.content_sha256:
            raise FieldRepairError("repair proposal digest mismatch")
        return proposal


@dataclass(frozen=True)
class ReauditCheck:
    name: ReauditName
    status: ReauditStatus
    subject_sha256: str
    artifact_sha256: str | None
    reason: str
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "name", ReauditName(self.name))
            object.__setattr__(self, "status", ReauditStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise FieldRepairError("downstream re-audit enum is invalid") from exc
        _require_digest(self.subject_sha256, "re-audit subject digest")
        _require_digest(self.artifact_sha256, "re-audit artifact digest", optional=True)
        if not isinstance(self.reason, str) or not _CODE_RE.fullmatch(self.reason):
            raise FieldRepairError("downstream re-audit reason is invalid")
        if self.status is ReauditStatus.UNAVAILABLE and self.artifact_sha256 is not None:
            raise FieldRepairError("unavailable re-audit cannot claim an artifact")
        if self.status is not ReauditStatus.UNAVAILABLE and self.artifact_sha256 is None:
            raise FieldRepairError("completed re-audit requires an artifact digest")
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "name": self.name.value,
            "status": self.status.value,
            "subject_sha256": self.subject_sha256,
            "artifact_sha256": self.artifact_sha256,
            "reason": self.reason,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "check_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "ReauditCheck":
        item = _strict(
            value,
            {
                "name",
                "status",
                "subject_sha256",
                "artifact_sha256",
                "reason",
                "check_sha256",
            },
            "downstream re-audit check",
        )
        check = cls(
            name=item["name"],
            status=item["status"],
            subject_sha256=item["subject_sha256"],
            artifact_sha256=item["artifact_sha256"],
            reason=item["reason"],
        )
        if item["check_sha256"] != check.content_sha256:
            raise FieldRepairError("downstream re-audit check digest mismatch")
        return check


@dataclass(frozen=True)
class DownstreamReauditBundle:
    field_path: str
    candidate_id: str
    candidate_sha256: str
    repaired_composition_sha256: str | None
    repaired_card_sha256: str | None
    checks: tuple[ReauditCheck, ...]
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        canonical_field_path(self.field_path)
        if not isinstance(self.candidate_id, str) or not _CANDIDATE_RE.fullmatch(
            self.candidate_id
        ):
            raise FieldRepairError("re-audit candidate id is invalid")
        _require_digest(self.candidate_sha256, "re-audit candidate digest")
        _require_digest(
            self.repaired_composition_sha256,
            "repaired composition digest",
            optional=True,
        )
        _require_digest(self.repaired_card_sha256, "repaired card digest", optional=True)
        if (self.repaired_composition_sha256 is None) != (
            self.repaired_card_sha256 is None
        ):
            raise FieldRepairError("repaired composition/card digests must be paired")
        checks = tuple(self.checks)
        if tuple(item.name for item in checks) != REAUDIT_ORDER:
            raise FieldRepairError("all five downstream checks are required in canonical order")
        subjects = {item.subject_sha256 for item in checks}
        if len(subjects) != 1:
            raise FieldRepairError("downstream checks do not share one repair subject")
        expected_subject = _digest(
            {
                "field_path": self.field_path,
                "candidate_id": self.candidate_id,
                "candidate_sha256": self.candidate_sha256,
                "repaired_composition_sha256": self.repaired_composition_sha256,
                "repaired_card_sha256": self.repaired_card_sha256,
            }
        )
        if subjects != {expected_subject}:
            raise FieldRepairError("downstream re-audit subject binding is stale")
        object.__setattr__(self, "checks", checks)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    @property
    def all_passed(self) -> bool:
        return all(item.status is ReauditStatus.PASSED for item in self.checks)

    def _content_payload(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "candidate_id": self.candidate_id,
            "candidate_sha256": self.candidate_sha256,
            "repaired_composition_sha256": self.repaired_composition_sha256,
            "repaired_card_sha256": self.repaired_card_sha256,
            "checks": [item.to_dict() for item in self.checks],
            "all_passed": self.all_passed,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "reaudit_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "DownstreamReauditBundle":
        item = _strict(
            value,
            {
                "field_path",
                "candidate_id",
                "candidate_sha256",
                "repaired_composition_sha256",
                "repaired_card_sha256",
                "checks",
                "all_passed",
                "reaudit_sha256",
            },
            "downstream re-audit bundle",
        )
        if not isinstance(item["checks"], list) or not isinstance(item["all_passed"], bool):
            raise FieldRepairError("downstream re-audit bundle fields are malformed")
        bundle = cls(
            field_path=item["field_path"],
            candidate_id=item["candidate_id"],
            candidate_sha256=item["candidate_sha256"],
            repaired_composition_sha256=item["repaired_composition_sha256"],
            repaired_card_sha256=item["repaired_card_sha256"],
            checks=tuple(ReauditCheck.from_dict(entry) for entry in item["checks"]),
        )
        if item["all_passed"] != bundle.all_passed:
            raise FieldRepairError("downstream all_passed marker is inconsistent")
        if item["reaudit_sha256"] != bundle.content_sha256:
            raise FieldRepairError("downstream re-audit bundle digest mismatch")
        return bundle


def _subject(
    candidate: ClaimCandidate,
    composition: CompositionResult | None,
) -> tuple[str, str | None, str | None]:
    composition_sha256 = composition.content_sha256 if composition else None
    card_sha256 = composition.card_sha256 if composition else None
    return (
        _digest(
            {
                "field_path": candidate.field_path,
                "candidate_id": candidate.candidate_id,
                "candidate_sha256": candidate.content_sha256,
                "repaired_composition_sha256": composition_sha256,
                "repaired_card_sha256": card_sha256,
            }
        ),
        composition_sha256,
        card_sha256,
    )


def _check(
    name: ReauditName,
    status: ReauditStatus,
    subject_sha256: str,
    artifact_sha256: str | None,
    reason: str,
) -> ReauditCheck:
    return ReauditCheck(name, status, subject_sha256, artifact_sha256, reason)


def evaluate_downstream_reaudits(
    *,
    context: FieldRepairContext,
    candidate: ClaimCandidate,
    repaired_composition: CompositionResult | None,
    factreasoner_record: FactReasonerRecord | None,
    omission_audit: OmissionAudit | None,
    risk_report: RiskMappingReport | None,
    risk_card_sha256: str | None,
    original_composition: CompositionResult,
) -> DownstreamReauditBundle:
    """Derive, rather than merely copy, all mandatory downstream statuses."""

    subject, composition_sha256, card_sha256 = _subject(candidate, repaired_composition)
    if repaired_composition is None:
        checks = tuple(
            _check(
                name,
                ReauditStatus.UNAVAILABLE,
                subject,
                None,
                "repaired_composition_unavailable",
            )
            for name in REAUDIT_ORDER
        )
        return DownstreamReauditBundle(
            field_path=candidate.field_path,
            candidate_id=candidate.candidate_id,
            candidate_sha256=candidate.content_sha256,
            repaired_composition_sha256=None,
            repaired_card_sha256=None,
            checks=checks,
        )

    card = repaired_composition.card
    schema_status = ReauditStatus.PASSED
    schema_reason = "schema_and_field_scope_passed"
    try:
        CompositionResult.from_dict(repaired_composition.to_dict())
        validate_public_card(card)
        if repaired_composition.plan.target != context.target:
            raise FieldRepairError("repaired composition changes the selected target")
        if candidate.candidate_id not in repaired_composition.plan.included_candidate_ids:
            raise FieldRepairError("repaired candidate is not included in the repaired card")
        if get_field(card, candidate.field_path) != candidate.value:
            raise FieldRepairError("repaired card rewrites the candidate value")
        changed_fields = {
            field
            for field in CONTENT_FIELD_PATHS
            if _canonical(get_field(card, field))
            != _canonical(get_field(original_composition.card, field))
        }
        if not changed_fields <= {context.base_field_path}:
            raise FieldRepairError("repair changes more than one content field")
    except Exception as exc:
        schema_status = ReauditStatus.FAILED
        message = str(exc)
        if "more than one" in message:
            schema_reason = "multi_field_change_detected"
        elif "included" in message or "rewrites" in message:
            schema_reason = "field_projection_mismatch"
        elif "target" in message:
            schema_reason = "target_identity_changed"
        else:
            schema_reason = "public_schema_failed"
    checks: list[ReauditCheck] = [
        _check(
            ReauditName.SCHEMA,
            schema_status,
            subject,
            repaired_composition.content_sha256,
            schema_reason,
        )
    ]

    if factreasoner_record is None:
        checks.append(
            _check(
                ReauditName.FACTREASONER,
                ReauditStatus.UNAVAILABLE,
                subject,
                None,
                "factreasoner_unavailable",
            )
        )
    else:
        status = ReauditStatus.PASSED
        reason = "factreasoner_field_supported"
        try:
            factreasoner_record.validate_integrity()
            if factreasoner_record.target != context.target:
                raise FieldRepairError("FactReasoner target mismatch")
            if factreasoner_record.card_sha256 != repaired_composition.card_sha256:
                raise FieldRepairError("FactReasoner card mismatch")
            decision = next(
                (
                    item
                    for item in factreasoner_record.field_decisions
                    if canonical_field_path(item.field_path) == context.base_field_path
                ),
                None,
            )
            if decision is None:
                raise FieldRepairError("FactReasoner field coverage missing")
            if decision.action is not FieldAction.NONE or any(
                item is not CheckOutcome.SUPPORT for item in decision.outcomes
            ):
                raise FieldRepairError("FactReasoner field is not fully supported")
        except Exception as exc:
            status = ReauditStatus.FAILED
            reason = (
                "factreasoner_input_mismatch"
                if "mismatch" in str(exc)
                else "factreasoner_field_not_supported"
            )
        checks.append(
            _check(
                ReauditName.FACTREASONER,
                status,
                subject,
                factreasoner_record.content_sha256,
                reason,
            )
        )

    if omission_audit is None:
        checks.append(
            _check(
                ReauditName.OMISSION,
                ReauditStatus.UNAVAILABLE,
                subject,
                None,
                "omission_reaudit_unavailable",
            )
        )
    else:
        status = ReauditStatus.PASSED
        reason = "repaired_field_present"
        omission_valid = True
        try:
            OmissionAudit.from_dict(omission_audit.to_dict())
        except Exception:
            omission_valid = False
        field_record = next(
            (item for item in omission_audit.records if item.field_path == context.base_field_path),
            None,
        )
        if not omission_valid:
            status = ReauditStatus.FAILED
            reason = "omission_reaudit_integrity_failed"
        elif omission_audit.composition_result_sha256 != repaired_composition.content_sha256:
            status = ReauditStatus.FAILED
            reason = "omission_reaudit_input_mismatch"
        elif field_record is None or field_record.status is not FieldAuditStatus.PRESENT:
            status = ReauditStatus.FAILED
            reason = "repaired_field_still_omitted"
        elif (
            candidate.candidate_id not in field_record.candidate_ids
            or candidate.candidate_id not in field_record.included_candidate_ids
        ):
            status = ReauditStatus.FAILED
            reason = "omission_reaudit_candidate_mismatch"
        checks.append(
            _check(
                ReauditName.OMISSION,
                status,
                subject,
                omission_audit.content_sha256,
                reason,
            )
        )

    if risk_report is None:
        checks.append(
            _check(
                ReauditName.RISK,
                ReauditStatus.UNAVAILABLE,
                subject,
                None,
                "risk_reaudit_unavailable",
            )
        )
    else:
        status = ReauditStatus.PASSED
        reason = "risk_reaudit_completed"
        expected_risk_sha256 = _digest(
            {
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
            }
        )
        if expected_risk_sha256 != risk_report.report_sha256:
            status = ReauditStatus.FAILED
            reason = "risk_reaudit_integrity_failed"
        elif risk_card_sha256 != repaired_composition.card_sha256:
            status = ReauditStatus.FAILED
            reason = "risk_reaudit_input_mismatch"
        elif risk_report.status is MappingStatus.UNAVAILABLE:
            status = ReauditStatus.UNAVAILABLE
            reason = "risk_reaudit_unavailable"
        elif risk_report.status is not MappingStatus.COMPLETED:
            status = ReauditStatus.FAILED
            reason = "risk_reaudit_failed"
        checks.append(
            _check(
                ReauditName.RISK,
                status,
                subject,
                risk_report.report_sha256 if status is not ReauditStatus.UNAVAILABLE else None,
                reason,
            )
        )

    privacy_status = ReauditStatus.PASSED
    privacy_reason = "public_projection_privacy_passed"
    try:
        assert_public_projection(card)
    except Exception:
        privacy_status = ReauditStatus.FAILED
        privacy_reason = "public_projection_privacy_failed"
    checks.append(
        _check(
            ReauditName.PRIVACY,
            privacy_status,
            subject,
            _digest({"checker": "assert_public_projection/v1", "card_sha256": card_sha256}),
            privacy_reason,
        )
    )
    return DownstreamReauditBundle(
        field_path=candidate.field_path,
        candidate_id=candidate.candidate_id,
        candidate_sha256=candidate.content_sha256,
        repaired_composition_sha256=composition_sha256,
        repaired_card_sha256=card_sha256,
        checks=tuple(checks),
    )


@dataclass(frozen=True)
class RepairSubmission:
    """Ephemeral typed inputs for one attempt; not part of the serialized record."""

    proposal: RepairProposal
    repaired_composition: CompositionResult | None = None
    factreasoner_record: FactReasonerRecord | None = None
    omission_audit: OmissionAudit | None = None
    risk_report: RiskMappingReport | None = None
    risk_card_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.proposal, RepairProposal):
            raise FieldRepairError("repair submission proposal is malformed")
        _require_digest(self.risk_card_sha256, "risk card digest", optional=True)
        pairs = (
            (self.repaired_composition, CompositionResult, "repaired composition"),
            (self.factreasoner_record, FactReasonerRecord, "FactReasoner record"),
            (self.omission_audit, OmissionAudit, "omission audit"),
            (self.risk_report, RiskMappingReport, "risk report"),
        )
        for value, expected_type, label in pairs:
            if value is not None and not isinstance(value, expected_type):
                raise FieldRepairError(f"repair submission {label} is malformed")

    @property
    def has_downstream_material(self) -> bool:
        return any(
            item is not None
            for item in (
                self.repaired_composition,
                self.factreasoner_record,
                self.omission_audit,
                self.risk_report,
                self.risk_card_sha256,
            )
        )


def _changed_components(
    predecessor: ClaimCandidate,
    candidate: ClaimCandidate,
) -> tuple[str, ...]:
    values = {
        "value": (predecessor.value, candidate.value),
        "evidence": (
            [item.to_dict() for item in predecessor.evidence],
            [item.to_dict() for item in candidate.evidence],
        ),
        "claim_entity": (predecessor.claim_entity, candidate.claim_entity),
        "relation": (predecessor.relation.value, candidate.relation.value),
        "benchmark_scope": (predecessor.benchmark_scope, candidate.benchmark_scope),
    }
    return tuple(
        name
        for name in _MUTABLE_COMPONENTS
        if _canonical(values[name][0]) != _canonical(values[name][1])
    )


@dataclass(frozen=True)
class RepairAttempt:
    ordinal: int
    predecessor_candidate_id: str
    predecessor_candidate_sha256: str
    proposal: RepairProposal
    changed_components: tuple[str, ...]
    gate_record: ClaimGateRecord
    downstream_reaudit: DownstreamReauditBundle | None
    disposition: AttemptDisposition
    reason: RepairReason
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.ordinal not in range(1, MAX_SEMANTIC_ATTEMPTS_PER_FIELD + 1):
            raise FieldRepairError("repair attempt ordinal exceeds the field limit")
        if not isinstance(self.predecessor_candidate_id, str) or not _CANDIDATE_RE.fullmatch(
            self.predecessor_candidate_id
        ):
            raise FieldRepairError("repair attempt predecessor id is invalid")
        _require_digest(self.predecessor_candidate_sha256, "attempt predecessor digest")
        if not isinstance(self.proposal, RepairProposal) or not isinstance(
            self.gate_record, ClaimGateRecord
        ):
            raise FieldRepairError("repair attempt proposal or gate record is malformed")
        candidate = self.proposal.candidate
        if candidate.previous_candidate_id != self.predecessor_candidate_id:
            raise FieldRepairError("repair candidate lineage is not linked to its predecessor")
        if not _candidate_equal(candidate, self.gate_record.candidate):
            raise FieldRepairError("gate checker changed the repair proposal")
        if self.gate_record.checker_decisions != self.proposal.checker_decisions:
            raise FieldRepairError("gate checker decisions differ from the submitted proposal")
        components = tuple(self.changed_components)
        if not components or components != tuple(
            item for item in _MUTABLE_COMPONENTS if item in set(components)
        ):
            raise FieldRepairError("repair mutation inventory is empty or non-canonical")
        if len(components) != len(set(components)):
            raise FieldRepairError("repair mutation inventory has duplicates")
        object.__setattr__(self, "changed_components", components)
        try:
            object.__setattr__(self, "disposition", AttemptDisposition(self.disposition))
            object.__setattr__(self, "reason", RepairReason(self.reason))
        except (TypeError, ValueError) as exc:
            raise FieldRepairError("repair attempt disposition is invalid") from exc
        eligible = self.gate_record.projection_eligible
        if not eligible:
            if self.downstream_reaudit is not None:
                raise FieldRepairError("gate-withheld attempt cannot claim downstream checks")
            if (
                self.disposition is not AttemptDisposition.GATE_WITHHELD
                or self.reason is not RepairReason.FOUR_PART_GATE_WITHHELD
            ):
                raise FieldRepairError("gate-withheld attempt outcome is inconsistent")
        else:
            if not isinstance(self.downstream_reaudit, DownstreamReauditBundle):
                raise FieldRepairError("gate-eligible attempt requires every downstream status")
            if (
                self.downstream_reaudit.candidate_id != candidate.candidate_id
                or self.downstream_reaudit.candidate_sha256 != candidate.content_sha256
            ):
                raise FieldRepairError("downstream checks belong to another repair candidate")
            if self.downstream_reaudit.all_passed:
                if (
                    self.disposition is not AttemptDisposition.ACCEPTED
                    or self.reason is not RepairReason.ALL_CHECKS_PASSED
                ):
                    raise FieldRepairError("fully passing repair attempt is not accepted")
            else:
                expected_reason = (
                    RepairReason.DOWNSTREAM_REAUDIT_UNAVAILABLE
                    if any(
                        item.status is ReauditStatus.UNAVAILABLE
                        for item in self.downstream_reaudit.checks
                    )
                    else RepairReason.DOWNSTREAM_REAUDIT_FAILED
                )
                if (
                    self.disposition is not AttemptDisposition.REAUDIT_WITHHELD
                    or self.reason is not expected_reason
                ):
                    raise FieldRepairError("failed downstream repair outcome is inconsistent")
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "predecessor_candidate_id": self.predecessor_candidate_id,
            "predecessor_candidate_sha256": self.predecessor_candidate_sha256,
            "proposal": self.proposal.to_dict(),
            "changed_components": list(self.changed_components),
            "gate_record": self.gate_record.to_dict(),
            "downstream_reaudit": (
                self.downstream_reaudit.to_dict() if self.downstream_reaudit else None
            ),
            "disposition": self.disposition.value,
            "reason": self.reason.value,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "attempt_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "RepairAttempt":
        item = _strict(
            value,
            {
                "ordinal",
                "predecessor_candidate_id",
                "predecessor_candidate_sha256",
                "proposal",
                "changed_components",
                "gate_record",
                "downstream_reaudit",
                "disposition",
                "reason",
                "attempt_sha256",
            },
            "repair attempt",
        )
        if not isinstance(item["changed_components"], list):
            raise FieldRepairError("repair attempt changed_components must be an array")
        attempt = cls(
            ordinal=item["ordinal"],
            predecessor_candidate_id=item["predecessor_candidate_id"],
            predecessor_candidate_sha256=item["predecessor_candidate_sha256"],
            proposal=RepairProposal.from_dict(item["proposal"]),
            changed_components=tuple(item["changed_components"]),
            gate_record=ClaimGateRecord.from_dict(item["gate_record"]),
            downstream_reaudit=(
                DownstreamReauditBundle.from_dict(item["downstream_reaudit"])
                if item["downstream_reaudit"] is not None
                else None
            ),
            disposition=item["disposition"],
            reason=item["reason"],
        )
        if item["attempt_sha256"] != attempt.content_sha256:
            raise FieldRepairError("repair attempt digest mismatch")
        return attempt


def _build_attempt(
    *,
    ordinal: int,
    context: FieldRepairContext,
    predecessor: ClaimCandidate,
    submission: RepairSubmission,
    sources: Sequence[SourceDocument],
    original_composition: CompositionResult,
) -> RepairAttempt:
    candidate = submission.proposal.candidate
    if predecessor.candidate_id != candidate.previous_candidate_id:
        raise FieldRepairError("repair proposal does not continue immutable candidate lineage")
    if predecessor.content_sha256 == candidate.content_sha256:
        raise FieldRepairError("repair proposal does not change candidate content")
    if candidate.target != context.target or candidate.target != predecessor.target:
        raise FieldRepairError("repair proposal changes the exact target")
    if candidate.field_path != context.field_path or candidate.field_path != predecessor.field_path:
        raise FieldRepairError("repair proposal changes fields")
    changed = _changed_components(predecessor, candidate)
    if not changed:
        raise FieldRepairError("repair proposal has no explicit mutable-component change")
    allowed = set(context.allowed_evidence_sha256s)
    proposed_evidence = {_evidence_sha256(item) for item in candidate.evidence}
    if not proposed_evidence <= allowed:
        raise FieldRepairError("repair proposal uses evidence outside the accepted field allowlist")

    gate = evaluate_claim_gate(candidate, sources, submission.proposal.checker_decisions)
    if not gate.projection_eligible:
        if submission.has_downstream_material:
            raise FieldRepairError("gate-withheld proposal cannot carry decorative re-audits")
        return RepairAttempt(
            ordinal=ordinal,
            predecessor_candidate_id=predecessor.candidate_id,
            predecessor_candidate_sha256=predecessor.content_sha256,
            proposal=submission.proposal,
            changed_components=changed,
            gate_record=gate,
            downstream_reaudit=None,
            disposition=AttemptDisposition.GATE_WITHHELD,
            reason=RepairReason.FOUR_PART_GATE_WITHHELD,
        )
    downstream = evaluate_downstream_reaudits(
        context=context,
        candidate=candidate,
        repaired_composition=submission.repaired_composition,
        factreasoner_record=submission.factreasoner_record,
        omission_audit=submission.omission_audit,
        risk_report=submission.risk_report,
        risk_card_sha256=submission.risk_card_sha256,
        original_composition=original_composition,
    )
    if downstream.all_passed:
        disposition = AttemptDisposition.ACCEPTED
        reason = RepairReason.ALL_CHECKS_PASSED
    else:
        disposition = AttemptDisposition.REAUDIT_WITHHELD
        reason = (
            RepairReason.DOWNSTREAM_REAUDIT_UNAVAILABLE
            if any(item.status is ReauditStatus.UNAVAILABLE for item in downstream.checks)
            else RepairReason.DOWNSTREAM_REAUDIT_FAILED
        )
    return RepairAttempt(
        ordinal=ordinal,
        predecessor_candidate_id=predecessor.candidate_id,
        predecessor_candidate_sha256=predecessor.content_sha256,
        proposal=submission.proposal,
        changed_components=changed,
        gate_record=gate,
        downstream_reaudit=downstream,
        disposition=disposition,
        reason=reason,
    )


@dataclass(frozen=True)
class FieldRepairRecord:
    context: FieldRepairContext
    attempts: tuple[RepairAttempt, ...]
    outcome: RepairOutcome
    reason: RepairReason
    selected_candidate_id: str | None
    selected_candidate_sha256: str | None
    repair_version: str = FIELD_REPAIR_VERSION
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.repair_version != FIELD_REPAIR_VERSION:
            raise FieldRepairError("field repair version is not recognized")
        if not isinstance(self.context, FieldRepairContext):
            raise FieldRepairError("field repair context is malformed")
        attempts = tuple(self.attempts)
        if len(attempts) > MAX_SEMANTIC_ATTEMPTS_PER_FIELD:
            raise FieldRepairError("field repair exceeds two semantic attempts")
        if not all(isinstance(item, RepairAttempt) for item in attempts):
            raise FieldRepairError("field repair attempts are malformed")
        if tuple(item.ordinal for item in attempts) != tuple(range(1, len(attempts) + 1)):
            raise FieldRepairError("field repair attempt ordinals are not contiguous")
        predecessor_id = self.context.predecessor_candidate_id
        predecessor_sha = self.context.predecessor_candidate_sha256
        for attempt in attempts:
            if (
                attempt.predecessor_candidate_id != predecessor_id
                or attempt.predecessor_candidate_sha256 != predecessor_sha
            ):
                raise FieldRepairError("field repair attempt lineage is discontinuous")
            candidate = attempt.proposal.candidate
            if (
                candidate.field_path != self.context.field_path
                or candidate.target != self.context.target
            ):
                raise FieldRepairError("field repair attempt escapes its field or target")
            predecessor_id = candidate.candidate_id
            predecessor_sha = candidate.content_sha256
        accepted = [item for item in attempts if item.disposition is AttemptDisposition.ACCEPTED]
        if accepted and accepted != [attempts[-1]]:
            raise FieldRepairError("semantic repair continued after a fully accepted attempt")
        try:
            object.__setattr__(self, "outcome", RepairOutcome(self.outcome))
            object.__setattr__(self, "reason", RepairReason(self.reason))
        except (TypeError, ValueError) as exc:
            raise FieldRepairError("field repair outcome is invalid") from exc
        if self.outcome is RepairOutcome.REPAIRED:
            if not accepted or self.reason is not RepairReason.ALL_CHECKS_PASSED:
                raise FieldRepairError("repaired outcome lacks a fully accepted attempt")
            candidate = accepted[0].proposal.candidate
            if (
                self.selected_candidate_id != candidate.candidate_id
                or self.selected_candidate_sha256 != candidate.content_sha256
            ):
                raise FieldRepairError("selected repair candidate is stale")
        else:
            if (
                accepted
                or self.selected_candidate_id is not None
                or self.selected_candidate_sha256 is not None
            ):
                raise FieldRepairError("withheld repair cannot select a candidate")
            expected = (
                RepairReason.SEMANTIC_ATTEMPT_LIMIT_EXHAUSTED
                if len(attempts) == MAX_SEMANTIC_ATTEMPTS_PER_FIELD
                else RepairReason.NO_ACCEPTED_RELEVANT_EVIDENCE
                if not attempts and not self.context.allowed_evidence_sha256s
                else RepairReason.EXPLICIT_WITHHOLD
            )
            if self.reason is not expected:
                raise FieldRepairError("withheld repair reason is inconsistent")
        object.__setattr__(self, "attempts", attempts)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "repair_version": self.repair_version,
            "context": self.context.to_dict(),
            "attempts": [item.to_dict() for item in self.attempts],
            "outcome": self.outcome.value,
            "reason": self.reason.value,
            "selected_candidate_id": self.selected_candidate_id,
            "selected_candidate_sha256": self.selected_candidate_sha256,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "record_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "FieldRepairRecord":
        item = _strict(
            value,
            {
                "repair_version",
                "context",
                "attempts",
                "outcome",
                "reason",
                "selected_candidate_id",
                "selected_candidate_sha256",
                "record_sha256",
            },
            "field repair record",
        )
        if not isinstance(item["attempts"], list):
            raise FieldRepairError("field repair attempts must be an array")
        record = cls(
            repair_version=item["repair_version"],
            context=FieldRepairContext.from_dict(item["context"]),
            attempts=tuple(RepairAttempt.from_dict(entry) for entry in item["attempts"]),
            outcome=item["outcome"],
            reason=item["reason"],
            selected_candidate_id=item["selected_candidate_id"],
            selected_candidate_sha256=item["selected_candidate_sha256"],
        )
        if item["record_sha256"] != record.content_sha256:
            raise FieldRepairError("field repair record digest mismatch")
        return record


def run_field_repair(
    *,
    field_path: str,
    predecessor_candidate_id: str,
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    composition_result: CompositionResult,
    omission_audit: OmissionAudit,
    factreasoner_record: FactReasonerRecord,
    submissions: Iterable[RepairSubmission],
    availability_hints: Iterable[FieldAvailabilityHint] = (),
) -> FieldRepairRecord:
    """Run at most two field-local proposals and withhold on any failed stage."""

    candidate_values = tuple(candidates)
    gate_values = tuple(gate_records)
    source_values = tuple(sources.values()) if isinstance(sources, Mapping) else tuple(sources)
    hint_values = tuple(availability_hints)
    submission_values = tuple(submissions)
    if len(submission_values) > MAX_SEMANTIC_ATTEMPTS_PER_FIELD:
        raise FieldRepairError("at most two semantic repair attempts are permitted per field")
    if not all(isinstance(item, RepairSubmission) for item in submission_values):
        raise FieldRepairError("repair submissions are malformed")
    context = prepare_field_repair(
        field_path=field_path,
        predecessor_candidate_id=predecessor_candidate_id,
        candidates=candidate_values,
        gate_records=gate_values,
        sources=source_values,
        composition_result=composition_result,
        omission_audit=omission_audit,
        factreasoner_record=factreasoner_record,
        availability_hints=hint_values,
    )
    by_id = {item.candidate_id: item for item in candidate_values}
    predecessor = by_id[predecessor_candidate_id]
    attempts: list[RepairAttempt] = []
    for ordinal, submission in enumerate(submission_values, start=1):
        if attempts and attempts[-1].disposition is AttemptDisposition.ACCEPTED:
            raise FieldRepairError("repair submissions continue after a successful repair")
        attempt = _build_attempt(
            ordinal=ordinal,
            context=context,
            predecessor=predecessor,
            submission=submission,
            sources=source_values,
            original_composition=composition_result,
        )
        attempts.append(attempt)
        predecessor = submission.proposal.candidate
    if attempts and attempts[-1].disposition is AttemptDisposition.ACCEPTED:
        candidate = attempts[-1].proposal.candidate
        return FieldRepairRecord(
            context=context,
            attempts=tuple(attempts),
            outcome=RepairOutcome.REPAIRED,
            reason=RepairReason.ALL_CHECKS_PASSED,
            selected_candidate_id=candidate.candidate_id,
            selected_candidate_sha256=candidate.content_sha256,
        )
    reason = (
        RepairReason.SEMANTIC_ATTEMPT_LIMIT_EXHAUSTED
        if len(attempts) == MAX_SEMANTIC_ATTEMPTS_PER_FIELD
        else RepairReason.NO_ACCEPTED_RELEVANT_EVIDENCE
        if not attempts and not context.allowed_evidence_sha256s
        else RepairReason.EXPLICIT_WITHHOLD
    )
    return FieldRepairRecord(
        context=context,
        attempts=tuple(attempts),
        outcome=RepairOutcome.WITHHELD,
        reason=reason,
        selected_candidate_id=None,
        selected_candidate_sha256=None,
    )


def verify_field_repair_record(
    record: FieldRepairRecord,
    *,
    field_path: str,
    predecessor_candidate_id: str,
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    composition_result: CompositionResult,
    omission_audit: OmissionAudit,
    factreasoner_record: FactReasonerRecord,
    submissions: Iterable[RepairSubmission],
    availability_hints: Iterable[FieldAvailabilityHint] = (),
) -> None:
    """Replay the complete bounded repair, including every four-part gate."""

    if not isinstance(record, FieldRepairRecord):
        raise FieldRepairReplayError("repair replay requires a FieldRepairRecord")
    replayed = run_field_repair(
        field_path=field_path,
        predecessor_candidate_id=predecessor_candidate_id,
        candidates=candidates,
        gate_records=gate_records,
        sources=sources,
        composition_result=composition_result,
        omission_audit=omission_audit,
        factreasoner_record=factreasoner_record,
        submissions=submissions,
        availability_hints=availability_hints,
    )
    if _canonical(replayed.to_dict()) != _canonical(record.to_dict()):
        raise FieldRepairReplayError("field repair replay mismatch")


__all__ = [
    "FIELD_REPAIR_VERSION",
    "MAX_REPAIR_EVIDENCE_ITEMS",
    "MAX_REPAIR_FRAGMENT_JSON_CHARS",
    "MAX_REPAIR_PROPOSAL_JSON_CHARS",
    "MAX_REPAIR_QUOTE_CHARS",
    "MAX_SEMANTIC_ATTEMPTS_PER_FIELD",
    "REAUDIT_ORDER",
    "AttemptDisposition",
    "DownstreamReauditBundle",
    "FieldRepairContext",
    "FieldRepairError",
    "FieldRepairRecord",
    "FieldRepairReplayError",
    "ReauditCheck",
    "ReauditName",
    "ReauditStatus",
    "RepairFinding",
    "RepairOutcome",
    "RepairProposal",
    "RepairReason",
    "RepairSubmission",
    "evaluate_downstream_reaudits",
    "prepare_field_repair",
    "run_field_repair",
    "verify_field_repair_record",
]
