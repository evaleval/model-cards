"""Fail-closed bridge from model-family prose to Nexus use contexts.

Family-scoped publisher prose is not evidence about an exact checkpoint.  The
ordinary claim gate therefore continues to withhold every ``MODEL_FAMILY``
candidate from card projection.  This module defines the separate, private
authorization chain needed before such a candidate may be used as *context*
for risk discovery:

1. an accepted exact-target claim records membership in the named family; and
2. an independent decision records that the particular family statement is
   applicable to the exact checkpoint.

The bridge never rewrites the candidate relation, never creates a card
binding, and retains the original quote candidate (including source revision
and character coordinates) in its authorization record.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable

from .claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    DecisionStatus,
    GateName,
    make_context_statement_value,
)
from .models import EvidenceKind, RelationToTarget, TargetIdentity
from .model_family import (
    CONFIG_MODEL_FAMILY_REGISTRY_VERSION,
    ModelFamilyDerivationError,
    derive_config_model_family_from_evidence,
)
from .risk_mapping import UseContext
from .schema import canonical_field_path


FAMILY_RISK_BRIDGE_VERSION = "model-family-risk-bridge/v1"
FAMILY_RISK_AUTHORIZATION_REPORT_VERSION = "family-risk-authorization-report/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FAMILY_ID_RE = re.compile(r"^[a-z][a-z0-9._-]{1,127}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9._:-]{1,127}$")
_CHECKER_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]{1,127}$")
_METHOD_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_MEMBERSHIP_FIELDS = frozenset({"lineage.model_family"})
_CORE_FIELDS = frozenset(
    {"use_and_risk.intended_uses", "use_and_risk.out_of_scope_uses"}
)
_QUALIFIER_FIELDS = frozenset(
    {"use_and_risk.limitations", "use_and_risk.known_biases"}
)
_CONTEXT_FIELDS = _CORE_FIELDS | _QUALIFIER_FIELDS
_LABELS = {
    "use_and_risk.intended_uses": "intended use",
    "use_and_risk.out_of_scope_uses": "out-of-scope use",
    "use_and_risk.limitations": "limitation",
    "use_and_risk.known_biases": "known bias",
}


class FamilyRiskBridgeError(ValueError):
    """Family evidence or an authorization decision failed closed."""


class FamilyDecisionStatus(str, Enum):
    ACCEPTED = "accepted"
    WITHHELD = "withheld"
    UNAVAILABLE = "unavailable"


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
        raise FamilyRiskBridgeError(
            "family-risk values must be finite JSON"
        ) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise FamilyRiskBridgeError(f"{label} has an invalid closed shape")
    return value


def _validate_decision_text(
    *, checker: str, method: str, reason: str, rationale: str
) -> None:
    if not isinstance(checker, str) or not _CHECKER_RE.fullmatch(checker):
        raise FamilyRiskBridgeError("family decision checker is invalid")
    if not isinstance(method, str) or not _METHOD_RE.fullmatch(method):
        raise FamilyRiskBridgeError("family decision method is invalid")
    if not isinstance(reason, str) or not _CODE_RE.fullmatch(reason):
        raise FamilyRiskBridgeError("family decision reason is invalid")
    if (
        not isinstance(rationale, str)
        or rationale != rationale.strip()
        or len(rationale) < 20
    ):
        raise FamilyRiskBridgeError(
            "family decision rationale must be substantive"
        )


def _gate_decisions(record: ClaimGateRecord) -> dict[GateName, Any]:
    record.validate_integrity()
    return {item.gate: item for item in record.decisions}


def _validate_membership_gate(
    record: ClaimGateRecord, family_id: str
) -> ClaimCandidate:
    if not isinstance(record, ClaimGateRecord):
        raise FamilyRiskBridgeError("family membership gate must be typed")
    if not isinstance(family_id, str) or not _FAMILY_ID_RE.fullmatch(family_id):
        raise FamilyRiskBridgeError("family identifier is invalid")
    record.validate_integrity()
    candidate = record.candidate
    if (
        candidate.relation is not RelationToTarget.EXACT_TARGET
        or canonical_field_path(candidate.field_path) not in _MEMBERSHIP_FIELDS
        or not isinstance(candidate.value, str)
        or candidate.value.casefold() != family_id.casefold()
        or not record.projection_eligible
    ):
        raise FamilyRiskBridgeError(
            "family membership requires an accepted exact-target family claim"
        )
    if any(
        item.source_target != candidate.target
        or item.source_revision != candidate.target.revision
        for item in candidate.evidence
    ):
        raise FamilyRiskBridgeError(
            "family membership evidence is not revision-bound to the target"
        )
    return candidate


def _validate_family_context_gate(record: ClaimGateRecord) -> ClaimCandidate:
    if not isinstance(record, ClaimGateRecord):
        raise FamilyRiskBridgeError("family context gate must be typed")
    decisions = _gate_decisions(record)
    candidate = record.candidate
    if candidate.relation is not RelationToTarget.MODEL_FAMILY:
        raise FamilyRiskBridgeError(
            "family prose must retain the MODEL_FAMILY relation"
        )
    if canonical_field_path(candidate.field_path) not in _CONTEXT_FIELDS:
        raise FamilyRiskBridgeError(
            "family bridge accepts only use or risk-context statements"
        )
    if candidate.claim_entity == (
        f"{candidate.target.model_id}@{candidate.target.revision}"
    ):
        raise FamilyRiskBridgeError(
            "family prose cannot claim the exact checkpoint as its entity"
        )
    if any(
        item.kind is not EvidenceKind.QUOTE
        or not item.verified
        or item.source_target != candidate.target
        or item.source_revision != candidate.target.revision
        for item in candidate.evidence
    ):
        raise FamilyRiskBridgeError(
            "family prose requires verified revision-bound quote evidence"
        )
    if (
        decisions[GateName.COORDINATE_INTEGRITY].status
        is not DecisionStatus.ACCEPTED
        or decisions[GateName.FIELD_FIT].status is not DecisionStatus.ACCEPTED
        or decisions[GateName.VALUE_SUPPORT].status is not DecisionStatus.ACCEPTED
        or decisions[GateName.ENTITY_SCOPE].status
        is not DecisionStatus.WITHHELD
        or decisions[GateName.ENTITY_SCOPE].reason
        != "relation_not_projection_eligible"
    ):
        raise FamilyRiskBridgeError(
            "family prose did not pass the non-scope claim checks exactly"
        )
    checker_by_gate = {item.gate: item for item in record.checker_decisions}
    if set(checker_by_gate) != {
        GateName.ENTITY_SCOPE,
        GateName.FIELD_FIT,
        GateName.VALUE_SUPPORT,
    } or any(
        checker_by_gate[gate].status is not DecisionStatus.ACCEPTED
        for gate in checker_by_gate
    ):
        raise FamilyRiskBridgeError(
            "family prose requires explicit accepted semantic checks"
        )
    value = candidate.value
    if not isinstance(value, dict):
        raise FamilyRiskBridgeError("family context wrapper is malformed")
    description = value.get("description")
    origin = value.get("origin")
    if not isinstance(description, str) or not isinstance(origin, str):
        raise FamilyRiskBridgeError("family context wrapper is incomplete")
    expected = make_context_statement_value(
        field_path=candidate.field_path,
        description=description,
        origin=origin,
        evidence=candidate.evidence,
    )
    if _canonical(value) != _canonical(expected):
        raise FamilyRiskBridgeError("family context wrapper is not canonical")
    return candidate


def validate_family_context_gate(record: ClaimGateRecord) -> ClaimCandidate:
    """Validate one family-scoped use-context gate without authorizing it."""

    return _validate_family_context_gate(record)


@dataclass(frozen=True)
class FamilyMembershipDecision:
    """Independent decision binding exact-target evidence to one family."""

    target: TargetIdentity
    family_id: str
    membership_candidate_id: str
    membership_candidate_sha256: str
    membership_gate_sha256: str
    status: FamilyDecisionStatus
    checker: str
    method: str
    reason: str
    rationale: str
    request_sha256: str = dataclass_field(init=False)
    decision_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.target, TargetIdentity):
            raise FamilyRiskBridgeError("family membership target is invalid")
        if not isinstance(self.family_id, str) or not _FAMILY_ID_RE.fullmatch(
            self.family_id
        ):
            raise FamilyRiskBridgeError("family membership identifier is invalid")
        if not re.fullmatch(
            r"claim-[0-9a-f]{24}", self.membership_candidate_id
        ):
            raise FamilyRiskBridgeError(
                "family membership candidate identifier is invalid"
            )
        for value in (
            self.membership_candidate_sha256,
            self.membership_gate_sha256,
        ):
            if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
                raise FamilyRiskBridgeError(
                    "family membership input digest is invalid"
                )
        try:
            object.__setattr__(
                self, "status", FamilyDecisionStatus(self.status)
            )
        except (TypeError, ValueError) as exc:
            raise FamilyRiskBridgeError(
                "family membership status is invalid"
            ) from exc
        _validate_decision_text(
            checker=self.checker,
            method=self.method,
            reason=self.reason,
            rationale=self.rationale,
        )
        request_sha256 = _digest(self._request_payload())
        object.__setattr__(self, "request_sha256", request_sha256)
        object.__setattr__(self, "decision_sha256", _digest(self._payload()))

    def _request_payload(self) -> dict[str, Any]:
        return {
            "bridge_version": FAMILY_RISK_BRIDGE_VERSION,
            "decision": "family_membership",
            "target": self.target.to_dict(),
            "family_id": self.family_id,
            "membership_candidate_id": self.membership_candidate_id,
            "membership_candidate_sha256": self.membership_candidate_sha256,
            "membership_gate_sha256": self.membership_gate_sha256,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            **self._request_payload(),
            "status": self.status.value,
            "checker": self.checker,
            "method": self.method,
            "reason": self.reason,
            "rationale": self.rationale,
            "request_sha256": self.request_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "decision_sha256": self.decision_sha256}

    @classmethod
    def for_gate(
        cls,
        record: ClaimGateRecord,
        *,
        family_id: str,
        status: FamilyDecisionStatus,
        checker: str,
        method: str,
        reason: str,
        rationale: str,
    ) -> "FamilyMembershipDecision":
        candidate = _validate_membership_gate(record, family_id)
        return cls(
            target=candidate.target,
            family_id=family_id,
            membership_candidate_id=candidate.candidate_id,
            membership_candidate_sha256=candidate.content_sha256,
            membership_gate_sha256=record.content_sha256,
            status=status,
            checker=checker,
            method=method,
            reason=reason,
            rationale=rationale,
        )

    @classmethod
    def from_dict(cls, value: Any) -> "FamilyMembershipDecision":
        item = _strict(
            value,
            {
                "bridge_version",
                "decision",
                "target",
                "family_id",
                "membership_candidate_id",
                "membership_candidate_sha256",
                "membership_gate_sha256",
                "status",
                "checker",
                "method",
                "reason",
                "rationale",
                "request_sha256",
                "decision_sha256",
            },
            "family membership decision",
        )
        if (
            item["bridge_version"] != FAMILY_RISK_BRIDGE_VERSION
            or item["decision"] != "family_membership"
        ):
            raise FamilyRiskBridgeError(
                "family membership decision version is invalid"
            )
        result = cls(
            target=TargetIdentity.from_dict(item["target"]),
            family_id=item["family_id"],
            membership_candidate_id=item["membership_candidate_id"],
            membership_candidate_sha256=item["membership_candidate_sha256"],
            membership_gate_sha256=item["membership_gate_sha256"],
            status=item["status"],
            checker=item["checker"],
            method=item["method"],
            reason=item["reason"],
            rationale=item["rationale"],
        )
        if (
            item["request_sha256"] != result.request_sha256
            or item["decision_sha256"] != result.decision_sha256
        ):
            raise FamilyRiskBridgeError(
                "family membership decision digest is inconsistent"
            )
        return result


def verify_family_membership_decision(
    decision: FamilyMembershipDecision, record: ClaimGateRecord
) -> None:
    if not isinstance(decision, FamilyMembershipDecision):
        raise FamilyRiskBridgeError("family membership decision must be typed")
    candidate = _validate_membership_gate(record, decision.family_id)
    if (
        decision.target != candidate.target
        or decision.membership_candidate_id != candidate.candidate_id
        or decision.membership_candidate_sha256 != candidate.content_sha256
        or decision.membership_gate_sha256 != record.content_sha256
    ):
        raise FamilyRiskBridgeError("family membership decision is stale")


@dataclass(frozen=True)
class FamilyContextApplicabilityDecision:
    """Separate family-statement applicability decision for one checkpoint."""

    target: TargetIdentity
    family_id: str
    family_candidate_id: str
    family_candidate_sha256: str
    family_gate_sha256: str
    membership_decision_sha256: str
    status: FamilyDecisionStatus
    checker: str
    method: str
    reason: str
    rationale: str
    request_sha256: str = dataclass_field(init=False)
    decision_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.target, TargetIdentity):
            raise FamilyRiskBridgeError(
                "family applicability target is invalid"
            )
        if not isinstance(self.family_id, str) or not _FAMILY_ID_RE.fullmatch(
            self.family_id
        ):
            raise FamilyRiskBridgeError(
                "family applicability identifier is invalid"
            )
        if not re.fullmatch(r"claim-[0-9a-f]{24}", self.family_candidate_id):
            raise FamilyRiskBridgeError(
                "family context candidate identifier is invalid"
            )
        for value in (
            self.family_candidate_sha256,
            self.family_gate_sha256,
            self.membership_decision_sha256,
        ):
            if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
                raise FamilyRiskBridgeError(
                    "family applicability input digest is invalid"
                )
        try:
            object.__setattr__(
                self, "status", FamilyDecisionStatus(self.status)
            )
        except (TypeError, ValueError) as exc:
            raise FamilyRiskBridgeError(
                "family applicability status is invalid"
            ) from exc
        _validate_decision_text(
            checker=self.checker,
            method=self.method,
            reason=self.reason,
            rationale=self.rationale,
        )
        request_sha256 = _digest(self._request_payload())
        object.__setattr__(self, "request_sha256", request_sha256)
        object.__setattr__(self, "decision_sha256", _digest(self._payload()))

    def _request_payload(self) -> dict[str, Any]:
        return {
            "bridge_version": FAMILY_RISK_BRIDGE_VERSION,
            "decision": "family_to_checkpoint_applicability",
            "target": self.target.to_dict(),
            "family_id": self.family_id,
            "family_candidate_id": self.family_candidate_id,
            "family_candidate_sha256": self.family_candidate_sha256,
            "family_gate_sha256": self.family_gate_sha256,
            "membership_decision_sha256": self.membership_decision_sha256,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            **self._request_payload(),
            "status": self.status.value,
            "checker": self.checker,
            "method": self.method,
            "reason": self.reason,
            "rationale": self.rationale,
            "request_sha256": self.request_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "decision_sha256": self.decision_sha256}

    @classmethod
    def for_gate(
        cls,
        record: ClaimGateRecord,
        membership: FamilyMembershipDecision,
        membership_gate: ClaimGateRecord,
        *,
        status: FamilyDecisionStatus,
        checker: str,
        method: str,
        reason: str,
        rationale: str,
    ) -> "FamilyContextApplicabilityDecision":
        candidate = _validate_family_context_gate(record)
        verify_family_membership_decision(membership, membership_gate)
        if membership.target != candidate.target:
            raise FamilyRiskBridgeError(
                "family context and membership target differ"
            )
        chosen = FamilyDecisionStatus(status)
        if (
            chosen is FamilyDecisionStatus.ACCEPTED
            and membership.status is not FamilyDecisionStatus.ACCEPTED
        ):
            raise FamilyRiskBridgeError(
                "family applicability cannot outrun membership"
            )
        return cls(
            target=candidate.target,
            family_id=membership.family_id,
            family_candidate_id=candidate.candidate_id,
            family_candidate_sha256=candidate.content_sha256,
            family_gate_sha256=record.content_sha256,
            membership_decision_sha256=membership.decision_sha256,
            status=chosen,
            checker=checker,
            method=method,
            reason=reason,
            rationale=rationale,
        )

    @classmethod
    def from_dict(cls, value: Any) -> "FamilyContextApplicabilityDecision":
        item = _strict(
            value,
            {
                "bridge_version",
                "decision",
                "target",
                "family_id",
                "family_candidate_id",
                "family_candidate_sha256",
                "family_gate_sha256",
                "membership_decision_sha256",
                "status",
                "checker",
                "method",
                "reason",
                "rationale",
                "request_sha256",
                "decision_sha256",
            },
            "family applicability decision",
        )
        if (
            item["bridge_version"] != FAMILY_RISK_BRIDGE_VERSION
            or item["decision"] != "family_to_checkpoint_applicability"
        ):
            raise FamilyRiskBridgeError(
                "family applicability decision version is invalid"
            )
        result = cls(
            target=TargetIdentity.from_dict(item["target"]),
            family_id=item["family_id"],
            family_candidate_id=item["family_candidate_id"],
            family_candidate_sha256=item["family_candidate_sha256"],
            family_gate_sha256=item["family_gate_sha256"],
            membership_decision_sha256=item["membership_decision_sha256"],
            status=item["status"],
            checker=item["checker"],
            method=item["method"],
            reason=item["reason"],
            rationale=item["rationale"],
        )
        if (
            item["request_sha256"] != result.request_sha256
            or item["decision_sha256"] != result.decision_sha256
        ):
            raise FamilyRiskBridgeError(
                "family applicability decision digest is inconsistent"
            )
        return result


def verify_family_applicability_decision(
    decision: FamilyContextApplicabilityDecision,
    record: ClaimGateRecord,
    membership: FamilyMembershipDecision,
    membership_gate: ClaimGateRecord,
) -> None:
    if not isinstance(decision, FamilyContextApplicabilityDecision):
        raise FamilyRiskBridgeError(
            "family applicability decision must be typed"
        )
    candidate = _validate_family_context_gate(record)
    verify_family_membership_decision(membership, membership_gate)
    if (
        decision.target != candidate.target
        or decision.target != membership.target
        or decision.family_id != membership.family_id
        or decision.family_candidate_id != candidate.candidate_id
        or decision.family_candidate_sha256 != candidate.content_sha256
        or decision.family_gate_sha256 != record.content_sha256
        or decision.membership_decision_sha256 != membership.decision_sha256
    ):
        raise FamilyRiskBridgeError("family applicability decision is stale")
    if (
        decision.status is FamilyDecisionStatus.ACCEPTED
        and membership.status is not FamilyDecisionStatus.ACCEPTED
    ):
        raise FamilyRiskBridgeError(
            "accepted family applicability lacks accepted membership"
        )


@dataclass(frozen=True)
class AuthorizedFamilyContext:
    """Private, replayable authorization for one family-scoped statement."""

    family_gate: ClaimGateRecord
    membership_gate: ClaimGateRecord
    membership: FamilyMembershipDecision
    applicability: FamilyContextApplicabilityDecision
    authorization_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.family_gate, ClaimGateRecord) or not isinstance(
            self.membership_gate, ClaimGateRecord
        ):
            raise FamilyRiskBridgeError(
                "authorized family context gates are invalid"
            )
        if (
            not isinstance(self.membership, FamilyMembershipDecision)
            or not isinstance(
                self.applicability, FamilyContextApplicabilityDecision
            )
            or self.membership.status is not FamilyDecisionStatus.ACCEPTED
            or self.applicability.status is not FamilyDecisionStatus.ACCEPTED
        ):
            raise FamilyRiskBridgeError(
                "authorized family context decision chain is incomplete"
            )
        verify_family_applicability_decision(
            self.applicability,
            self.family_gate,
            self.membership,
            self.membership_gate,
        )
        object.__setattr__(
            self, "authorization_sha256", _digest(self._payload())
        )

    @property
    def candidate(self) -> ClaimCandidate:
        return self.family_gate.candidate

    @property
    def description(self) -> str:
        value = self.candidate.value
        assert isinstance(value, dict)
        description = value.get("description")
        assert isinstance(description, str)
        return description

    @property
    def source_refs(self) -> tuple[str, ...]:
        return tuple(sorted({item.source_id for item in self.candidate.evidence}))

    def _payload(self) -> dict[str, Any]:
        return {
            "bridge_version": FAMILY_RISK_BRIDGE_VERSION,
            "relation": RelationToTarget.MODEL_FAMILY.value,
            "family_gate": self.family_gate.to_dict(),
            "membership_gate": self.membership_gate.to_dict(),
            "membership": self.membership.to_dict(),
            "applicability": self.applicability.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "authorization_sha256": self.authorization_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "AuthorizedFamilyContext":
        item = _strict(
            value,
            {
                "bridge_version",
                "relation",
                "family_gate",
                "membership_gate",
                "membership",
                "applicability",
                "authorization_sha256",
            },
            "authorized family context",
        )
        if (
            item["bridge_version"] != FAMILY_RISK_BRIDGE_VERSION
            or item["relation"] != RelationToTarget.MODEL_FAMILY.value
        ):
            raise FamilyRiskBridgeError(
                "authorized family context version or relation is invalid"
            )
        result = cls(
            family_gate=ClaimGateRecord.from_dict(item["family_gate"]),
            membership_gate=ClaimGateRecord.from_dict(
                item["membership_gate"]
            ),
            membership=FamilyMembershipDecision.from_dict(item["membership"]),
            applicability=FamilyContextApplicabilityDecision.from_dict(
                item["applicability"]
            ),
        )
        if item["authorization_sha256"] != result.authorization_sha256:
            raise FamilyRiskBridgeError(
                "authorized family context digest is inconsistent"
            )
        return result


def authorize_family_context(
    record: ClaimGateRecord,
    membership: FamilyMembershipDecision,
    membership_gate: ClaimGateRecord,
    applicability: FamilyContextApplicabilityDecision,
) -> AuthorizedFamilyContext:
    """Authorize one statement only after both independent decisions accept."""

    verify_family_applicability_decision(
        applicability, record, membership, membership_gate
    )
    if (
        membership.status is not FamilyDecisionStatus.ACCEPTED
        or applicability.status is not FamilyDecisionStatus.ACCEPTED
    ):
        raise FamilyRiskBridgeError(
            "family context is withheld until both decisions accept"
        )
    return AuthorizedFamilyContext(
        family_gate=record,
        membership_gate=membership_gate,
        membership=membership,
        applicability=applicability,
    )


@dataclass(frozen=True)
class AuthorizedFamilyUseContext:
    """One Nexus-ready context plus the authorizations that produced it."""

    context: UseContext
    authorization_sha256s: tuple[str, ...]
    relation: RelationToTarget = RelationToTarget.MODEL_FAMILY
    record_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.context, UseContext):
            raise FamilyRiskBridgeError(
                "authorized family Nexus context is invalid"
            )
        try:
            object.__setattr__(
                self, "relation", RelationToTarget(self.relation)
            )
        except (TypeError, ValueError) as exc:
            raise FamilyRiskBridgeError(
                "authorized family context relation is invalid"
            ) from exc
        if self.relation is not RelationToTarget.MODEL_FAMILY:
            raise FamilyRiskBridgeError(
                "authorized family Nexus context cannot be relabeled"
            )
        values = tuple(sorted(set(self.authorization_sha256s)))
        if not values or any(not _DIGEST_RE.fullmatch(item) for item in values):
            raise FamilyRiskBridgeError(
                "authorized family context requires authorization digests"
            )
        object.__setattr__(self, "authorization_sha256s", values)
        object.__setattr__(self, "record_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "bridge_version": FAMILY_RISK_BRIDGE_VERSION,
            "relation": self.relation.value,
            "context": self.context.to_dict(),
            "authorization_sha256s": list(self.authorization_sha256s),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "record_sha256": self.record_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "AuthorizedFamilyUseContext":
        item = _strict(
            value,
            {
                "bridge_version",
                "relation",
                "context",
                "authorization_sha256s",
                "record_sha256",
            },
            "authorized family use context",
        )
        if item["bridge_version"] != FAMILY_RISK_BRIDGE_VERSION:
            raise FamilyRiskBridgeError(
                "authorized family use-context version is invalid"
            )
        if not isinstance(item["authorization_sha256s"], list):
            raise FamilyRiskBridgeError(
                "authorized family use-context digests are invalid"
            )
        result = cls(
            context=UseContext.from_dict(item["context"]),
            authorization_sha256s=tuple(item["authorization_sha256s"]),
            relation=item["relation"],
        )
        if item["record_sha256"] != result.record_sha256:
            raise FamilyRiskBridgeError(
                "authorized family use-context digest is inconsistent"
            )
        return result


def derive_authorized_family_use_contexts(
    authorizations: Iterable[AuthorizedFamilyContext],
) -> tuple[AuthorizedFamilyUseContext, ...]:
    """Build Nexus inputs from accepted family statements, never raw claims.

    A family intended/out-of-scope use is mandatory. Family limitations and
    biases can only qualify one unambiguous family core, using the same
    source-local rule as the exact-target lane.
    """

    values = tuple(authorizations)
    if not all(isinstance(item, AuthorizedFamilyContext) for item in values):
        raise FamilyRiskBridgeError("family authorizations must be typed")
    candidate_ids = [item.candidate.candidate_id for item in values]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise FamilyRiskBridgeError("family authorizations are duplicated")
    if not values:
        return ()
    target = values[0].candidate.target
    family_id = values[0].membership.family_id
    if any(
        item.candidate.target != target
        or item.membership.family_id != family_id
        for item in values
    ):
        raise FamilyRiskBridgeError(
            "family Nexus context cannot mix targets or families"
        )

    cores = [
        item
        for item in values
        if canonical_field_path(item.candidate.field_path) in _CORE_FIELDS
    ]
    qualifiers = [
        item
        for item in values
        if canonical_field_path(item.candidate.field_path) in _QUALIFIER_FIELDS
    ]
    result: list[AuthorizedFamilyUseContext] = []
    for core in sorted(cores, key=lambda item: item.candidate.candidate_id):
        linked: list[AuthorizedFamilyContext] = []
        for qualifier in qualifiers:
            overlaps = [
                candidate_core
                for candidate_core in cores
                if set(candidate_core.source_refs).intersection(
                    qualifier.source_refs
                )
            ]
            if len(cores) == 1 or (
                len(overlaps) == 1 and overlaps[0] is core
            ):
                linked.append(qualifier)
        inputs = (core, *sorted(
            linked, key=lambda item: item.candidate.candidate_id
        ))
        descriptions = []
        for item in inputs:
            base = canonical_field_path(item.candidate.field_path)
            descriptions.append(
                "Publisher-reported model-family "
                f"{_LABELS[base]}, separately accepted as applicable to "
                f"{target.model_id}@{target.revision}: {item.description}"
            )
        context_payload = {
            "bridge_version": FAMILY_RISK_BRIDGE_VERSION,
            "target": target.to_dict(),
            "family_id": family_id,
            "authorization_sha256s": sorted(
                item.authorization_sha256 for item in inputs
            ),
        }
        context = UseContext(
            context_id="family-context-" + _digest(context_payload)[:24],
            description="\n".join(descriptions),
            supporting_fields=tuple(
                item.candidate.field_path for item in inputs
            ),
            supporting_candidate_ids=tuple(
                item.candidate.candidate_id for item in inputs
            ),
            source_refs=tuple(
                ref for item in inputs for ref in item.source_refs
            ),
        )
        result.append(
            AuthorizedFamilyUseContext(
                context=context,
                authorization_sha256s=tuple(
                    item.authorization_sha256 for item in inputs
                ),
            )
        )
    return tuple(sorted(result, key=lambda item: item.context.context_id))


def authorized_nexus_inputs(
    contexts: Iterable[AuthorizedFamilyUseContext],
    authorizations: Iterable[AuthorizedFamilyContext],
) -> tuple[UseContext, ...]:
    """Expose only contexts that replay from the supplied authorization chain."""

    values = tuple(contexts)
    if not all(isinstance(item, AuthorizedFamilyUseContext) for item in values):
        raise FamilyRiskBridgeError(
            "Nexus family inputs require authorization records"
        )
    replayed = derive_authorized_family_use_contexts(authorizations)
    if values != replayed:
        raise FamilyRiskBridgeError(
            "family Nexus inputs do not replay from their authorizations"
        )
    context_ids = [item.context.context_id for item in values]
    if context_ids != sorted(context_ids) or len(context_ids) != len(
        set(context_ids)
    ):
        raise FamilyRiskBridgeError(
            "authorized family Nexus inputs are not canonical"
        )
    return tuple(item.context for item in values)


def select_config_family_membership(
    gate_records: Iterable[ClaimGateRecord],
) -> tuple[ClaimGateRecord, FamilyMembershipDecision] | None:
    """Select one unambiguous allowlisted config-family membership claim.

    This automatic lane deliberately ignores quoted membership assertions and
    generic architecture candidates.  Only a projection-eligible
    ``lineage.model_family`` claim whose exact config or pinned metadata
    ``model_type`` evidence replays through the closed publisher/model-id
    registry can authorize family prose.
    """

    matches: list[tuple[ClaimGateRecord, str]] = []
    for record in tuple(gate_records):
        if not isinstance(record, ClaimGateRecord):
            raise FamilyRiskBridgeError("family membership inventory is malformed")
        candidate = record.candidate
        if (
            candidate.relation is not RelationToTarget.EXACT_TARGET
            or canonical_field_path(candidate.field_path) not in _MEMBERSHIP_FIELDS
            or not record.projection_eligible
            or not candidate.evidence
            or any(item.kind is not EvidenceKind.STRUCTURED for item in candidate.evidence)
        ):
            continue
        family_ids = set()
        try:
            for evidence in candidate.evidence:
                derivation = derive_config_model_family_from_evidence(
                    candidate.target, evidence
                )
                if derivation is None:
                    family_ids.clear()
                    break
                family_ids.add(derivation.family_id)
        except ModelFamilyDerivationError as exc:
            raise FamilyRiskBridgeError(
                "config family membership derivation failed closed"
            ) from exc
        if (
            len(family_ids) == 1
            and isinstance(candidate.value, str)
            and candidate.value in family_ids
        ):
            matches.append((record, candidate.value))
    if not matches:
        return None
    family_ids = {family_id for _record, family_id in matches}
    if len(family_ids) != 1:
        return None
    record, family_id = sorted(
        matches, key=lambda item: item[0].candidate.candidate_id
    )[0]
    decision = FamilyMembershipDecision.for_gate(
        record,
        family_id=family_id,
        status=FamilyDecisionStatus.ACCEPTED,
        checker="model-cards/config-model-family-registry",
        method="closed_publisher_target_model_type_registry",
        reason="config_family_membership_allowlisted",
        rationale=(
            "The exact revision-pinned config evidence and publisher model identifier match "
            f"the closed {CONFIG_MODEL_FAMILY_REGISTRY_VERSION} registry."
        ),
    )
    return record, decision


@dataclass(frozen=True)
class FamilyRiskAuthorizationReport:
    """Self-contained private record of family-context authorization and replay."""

    target: TargetIdentity
    family_gates: tuple[ClaimGateRecord, ...]
    membership_gate: ClaimGateRecord | None
    membership: FamilyMembershipDecision | None
    applicability_decisions: tuple[FamilyContextApplicabilityDecision, ...]
    authorizations: tuple[AuthorizedFamilyContext, ...]
    use_contexts: tuple[AuthorizedFamilyUseContext, ...]
    ineligible_candidate_ids: tuple[str, ...]
    report_version: str = FAMILY_RISK_AUTHORIZATION_REPORT_VERSION
    report_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.report_version != FAMILY_RISK_AUTHORIZATION_REPORT_VERSION:
            raise FamilyRiskBridgeError(
                "family authorization report version is invalid"
            )
        if not isinstance(self.target, TargetIdentity):
            raise FamilyRiskBridgeError("family authorization target is invalid")
        gates = tuple(sorted(
            self.family_gates,
            key=lambda item: item.candidate.candidate_id,
        ))
        if not all(isinstance(item, ClaimGateRecord) for item in gates):
            raise FamilyRiskBridgeError("family authorization gates are malformed")
        gate_ids = [item.candidate.candidate_id for item in gates]
        if len(gate_ids) != len(set(gate_ids)) or any(
            item.candidate.target != self.target for item in gates
        ):
            raise FamilyRiskBridgeError("family authorization gates are not canonical")
        object.__setattr__(self, "family_gates", gates)

        if (self.membership_gate is None) != (self.membership is None):
            raise FamilyRiskBridgeError(
                "family authorization membership chain is incomplete"
            )
        if self.membership_gate is not None and self.membership is not None:
            if self.membership.target != self.target:
                raise FamilyRiskBridgeError(
                    "family authorization membership target differs"
                )
            verify_family_membership_decision(
                self.membership, self.membership_gate
            )

        decisions = tuple(sorted(
            self.applicability_decisions,
            key=lambda item: item.family_candidate_id,
        ))
        if not all(
            isinstance(item, FamilyContextApplicabilityDecision)
            for item in decisions
        ) or len({item.family_candidate_id for item in decisions}) != len(decisions):
            raise FamilyRiskBridgeError(
                "family applicability decisions are not canonical"
            )
        object.__setattr__(self, "applicability_decisions", decisions)

        by_id = {item.candidate.candidate_id: item for item in gates}
        if decisions and (self.membership_gate is None or self.membership is None):
            raise FamilyRiskBridgeError(
                "family applicability decisions lack membership"
            )
        if self.membership_gate is not None and self.membership is not None:
            for decision in decisions:
                record = by_id.get(decision.family_candidate_id)
                if record is None:
                    raise FamilyRiskBridgeError(
                        "family applicability decision has no gate"
                    )
                verify_family_applicability_decision(
                    decision,
                    record,
                    self.membership,
                    self.membership_gate,
                )

        authorizations = tuple(sorted(
            self.authorizations,
            key=lambda item: item.candidate.candidate_id,
        ))
        if not all(
            isinstance(item, AuthorizedFamilyContext)
            for item in authorizations
        ):
            raise FamilyRiskBridgeError(
                "family authorization records are malformed"
            )
        accepted_ids = {
            item.family_candidate_id
            for item in decisions
            if item.status is FamilyDecisionStatus.ACCEPTED
        }
        if {item.candidate.candidate_id for item in authorizations} != accepted_ids:
            raise FamilyRiskBridgeError(
                "family authorizations differ from accepted applicability decisions"
            )
        object.__setattr__(self, "authorizations", authorizations)

        contexts = tuple(sorted(
            self.use_contexts,
            key=lambda item: item.context.context_id,
        ))
        replayed = derive_authorized_family_use_contexts(authorizations)
        if contexts != replayed:
            raise FamilyRiskBridgeError(
                "family use contexts do not replay from their authorizations"
            )
        object.__setattr__(self, "use_contexts", contexts)

        ineligible = tuple(sorted(set(self.ineligible_candidate_ids)))
        if any(
            not isinstance(item, str) or not re.fullmatch(r"claim-[0-9a-f]{24}", item)
            for item in ineligible
        ) or not set(ineligible).issubset(set(gate_ids)):
            raise FamilyRiskBridgeError(
                "family ineligible candidate identifiers are invalid"
            )
        decided_ids = {item.family_candidate_id for item in decisions}
        if decided_ids.intersection(ineligible) or decided_ids.union(ineligible) != set(
            gate_ids
        ):
            raise FamilyRiskBridgeError(
                "family authorization candidate coverage is incomplete"
            )
        object.__setattr__(self, "ineligible_candidate_ids", ineligible)
        object.__setattr__(self, "report_sha256", _digest(self._payload()))

    @property
    def nexus_inputs(self) -> tuple[UseContext, ...]:
        return authorized_nexus_inputs(self.use_contexts, self.authorizations)

    def _payload(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "target": self.target.to_dict(),
            "family_gates": [item.to_dict() for item in self.family_gates],
            "membership_gate": (
                None if self.membership_gate is None else self.membership_gate.to_dict()
            ),
            "membership": (
                None if self.membership is None else self.membership.to_dict()
            ),
            "applicability_decisions": [
                item.to_dict() for item in self.applicability_decisions
            ],
            "authorizations": [item.to_dict() for item in self.authorizations],
            "use_contexts": [item.to_dict() for item in self.use_contexts],
            "ineligible_candidate_ids": list(self.ineligible_candidate_ids),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "report_sha256": self.report_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "FamilyRiskAuthorizationReport":
        item = _strict(
            value,
            {
                "report_version",
                "target",
                "family_gates",
                "membership_gate",
                "membership",
                "applicability_decisions",
                "authorizations",
                "use_contexts",
                "ineligible_candidate_ids",
                "report_sha256",
            },
            "family authorization report",
        )
        for name in (
            "family_gates",
            "applicability_decisions",
            "authorizations",
            "use_contexts",
            "ineligible_candidate_ids",
        ):
            if not isinstance(item[name], list):
                raise FamilyRiskBridgeError(
                    "family authorization report arrays are malformed"
                )
        if (item["membership_gate"] is None) != (item["membership"] is None):
            raise FamilyRiskBridgeError(
                "family authorization report membership is malformed"
            )
        result = cls(
            report_version=item["report_version"],
            target=TargetIdentity.from_dict(item["target"]),
            family_gates=tuple(
                ClaimGateRecord.from_dict(entry) for entry in item["family_gates"]
            ),
            membership_gate=(
                None
                if item["membership_gate"] is None
                else ClaimGateRecord.from_dict(item["membership_gate"])
            ),
            membership=(
                None
                if item["membership"] is None
                else FamilyMembershipDecision.from_dict(item["membership"])
            ),
            applicability_decisions=tuple(
                FamilyContextApplicabilityDecision.from_dict(entry)
                for entry in item["applicability_decisions"]
            ),
            authorizations=tuple(
                AuthorizedFamilyContext.from_dict(entry)
                for entry in item["authorizations"]
            ),
            use_contexts=tuple(
                AuthorizedFamilyUseContext.from_dict(entry)
                for entry in item["use_contexts"]
            ),
            ineligible_candidate_ids=tuple(item["ineligible_candidate_ids"]),
        )
        if item["report_sha256"] != result.report_sha256:
            raise FamilyRiskBridgeError(
                "family authorization report digest is inconsistent"
            )
        return result


def build_family_risk_authorization_report(
    gate_records: Iterable[ClaimGateRecord],
    applicability_decisions: Iterable[FamilyContextApplicabilityDecision] = (),
    *,
    target: TargetIdentity | None = None,
) -> FamilyRiskAuthorizationReport:
    """Build a complete report; missing semantic decisions stay unavailable."""

    records = tuple(gate_records)
    if not all(isinstance(item, ClaimGateRecord) for item in records):
        raise FamilyRiskBridgeError("family authorization gate inventory is malformed")
    targets = {item.candidate.target for item in records}
    if target is not None:
        if not isinstance(target, TargetIdentity):
            raise FamilyRiskBridgeError(
                "family authorization target override is malformed"
            )
        targets.add(target)
    if len(targets) != 1:
        raise FamilyRiskBridgeError(
            "family authorization inventory must have exactly one target"
        )
    selected_target = next(iter(targets))
    family_gates = tuple(
        item
        for item in records
        if item.candidate.relation is RelationToTarget.MODEL_FAMILY
        and canonical_field_path(item.candidate.field_path) in _CONTEXT_FIELDS
    )
    supplied = tuple(applicability_decisions)
    if not all(
        isinstance(item, FamilyContextApplicabilityDecision) for item in supplied
    ) or len({item.family_candidate_id for item in supplied}) != len(supplied):
        raise FamilyRiskBridgeError(
            "supplied family applicability decisions are malformed or duplicated"
        )
    membership_pair = select_config_family_membership(records)
    if membership_pair is None:
        if supplied:
            raise FamilyRiskBridgeError(
                "family applicability decisions were supplied without membership"
            )
        return FamilyRiskAuthorizationReport(
            target=selected_target,
            family_gates=family_gates,
            membership_gate=None,
            membership=None,
            applicability_decisions=(),
            authorizations=(),
            use_contexts=(),
            ineligible_candidate_ids=tuple(
                item.candidate.candidate_id for item in family_gates
            ),
        )
    membership_gate, membership = membership_pair
    eligible: dict[str, ClaimGateRecord] = {}
    ineligible = []
    for record in family_gates:
        try:
            _validate_family_context_gate(record)
        except FamilyRiskBridgeError:
            ineligible.append(record.candidate.candidate_id)
        else:
            eligible[record.candidate.candidate_id] = record
    supplied_by_id = {item.family_candidate_id: item for item in supplied}
    if not set(supplied_by_id).issubset(set(eligible)):
        raise FamilyRiskBridgeError(
            "supplied family applicability decision is unused or stale"
        )
    decisions = []
    authorizations = []
    for candidate_id, record in sorted(eligible.items()):
        decision = supplied_by_id.get(candidate_id)
        if decision is None:
            decision = FamilyContextApplicabilityDecision.for_gate(
                record,
                membership,
                membership_gate,
                status=FamilyDecisionStatus.UNAVAILABLE,
                checker="model-cards/provider-availability-v1",
                method="recorded_provider_response_availability",
                reason="family_applicability_unavailable",
                rationale=(
                    "No independent checkpoint applicability decision was supplied."
                ),
            )
        else:
            verify_family_applicability_decision(
                decision, record, membership, membership_gate
            )
        decisions.append(decision)
        if decision.status is FamilyDecisionStatus.ACCEPTED:
            authorizations.append(
                authorize_family_context(
                    record, membership, membership_gate, decision
                )
            )
    authorization_values = tuple(authorizations)
    contexts = derive_authorized_family_use_contexts(authorization_values)
    return FamilyRiskAuthorizationReport(
        target=selected_target,
        family_gates=family_gates,
        membership_gate=membership_gate,
        membership=membership,
        applicability_decisions=tuple(decisions),
        authorizations=authorization_values,
        use_contexts=contexts,
        ineligible_candidate_ids=tuple(ineligible),
    )


__all__ = [
    "FAMILY_RISK_BRIDGE_VERSION",
    "FAMILY_RISK_AUTHORIZATION_REPORT_VERSION",
    "AuthorizedFamilyContext",
    "AuthorizedFamilyUseContext",
    "FamilyContextApplicabilityDecision",
    "FamilyDecisionStatus",
    "FamilyMembershipDecision",
    "FamilyRiskAuthorizationReport",
    "FamilyRiskBridgeError",
    "authorize_family_context",
    "authorized_nexus_inputs",
    "build_family_risk_authorization_report",
    "derive_authorized_family_use_contexts",
    "select_config_family_membership",
    "validate_family_context_gate",
    "verify_family_applicability_decision",
    "verify_family_membership_decision",
]
