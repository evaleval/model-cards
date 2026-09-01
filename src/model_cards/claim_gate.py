"""Fail-closed four-decision Claim Support Gate v1.

The existing :class:`~model_cards.models.Binding` is intentionally left
untouched.  A ``ClaimCandidate`` wraps its claim inputs, and this module emits
an independently replayable record for coordinate integrity, entity scope,
field fit, and complete value support.  No checker in this module rewrites a
claim.  Corrections create a new candidate linked to its predecessor.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field, replace
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Sequence

from .bindings import resolve_json_pointer
from .models import (
    Binding,
    Evidence,
    EvidenceKind,
    JsonValue,
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from .pointer_registry import (
    DEFAULT_POINTER_FIELD_REGISTRY,
    POINTER_REGISTRY_NAME,
    POINTER_REGISTRY_VERSION,
    PointerFieldRegistry,
    PointerLookupStatus,
)
from .quote import normalize_ws
from .schema import canonical_field_path, validate_field_value


CLAIM_GATE_VERSION = "claim-support-gate/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_ID_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_CHECKER_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]{1,127}$")
_METHOD_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])[-+]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?![A-Za-z0-9])")
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")

_GATE_CHECKER = "model-cards/claim-support-gate-v1"
_SCOPE_POLICY = {
    RelationToTarget.EXACT_TARGET.value: "all_except_related_model_scores",
    RelationToTarget.BASE_MODEL.value: ("lineage.base_models",),
    RelationToTarget.SIBLING_CHECKPOINT.value: ("evaluation.related_model_scores",),
    RelationToTarget.COMPARISON_MODEL.value: ("evaluation.related_model_scores",),
    RelationToTarget.MODEL_FAMILY.value: (),
    RelationToTarget.DERIVATIVE_MODEL.value: (),
    RelationToTarget.UNKNOWN.value: (),
}
_CONTEXT_FIELDS = frozenset(
    {
        "use_and_risk.intended_uses",
        "use_and_risk.out_of_scope_uses",
        "use_and_risk.limitations",
        "use_and_risk.known_biases",
    }
)
_WRAPPER_POLICY = {
    "context_statement": {
        "fields": sorted(_CONTEXT_FIELDS),
        "required_keys": ["context_id", "description", "origin", "source_refs"],
        "origins": ["publisher_reported", "source_derived"],
        "supported_leaves": ["description"],
        "id_prefix": "context:",
    },
    "mitigation": {
        "fields": ["use_and_risk.mitigations"],
        "required_keys": ["mitigation_id", "description", "origin", "source_refs"],
        "origins": ["publisher_reported"],
        "supported_leaves": ["description"],
        "id_prefix": "mitigation:",
    },
    "publisher_risk": {
        "fields": ["use_and_risk.identified_risks"],
        "identification_origin": "publisher_reported",
        "taxonomy": None,
        "mapping_method": "source_binding",
        "review_status": "generated_unreviewed",
        "supported_leaves": ["name", "description", "applicability_rationale"],
        "id_prefix": "publisher-risk:",
    },
}


class ClaimGateError(ValueError):
    """Base error for malformed, ambiguous, or stale gate material."""


class ClaimGateReplayError(ClaimGateError):
    """A serialized gate record does not replay against frozen inputs."""


class GateName(str, Enum):
    COORDINATE_INTEGRITY = "coordinate_integrity"
    ENTITY_SCOPE = "entity_scope"
    FIELD_FIT = "field_fit"
    VALUE_SUPPORT = "value_support"


GATE_ORDER: tuple[GateName, ...] = (
    GateName.COORDINATE_INTEGRITY,
    GateName.ENTITY_SCOPE,
    GateName.FIELD_FIT,
    GateName.VALUE_SUPPORT,
)


class DecisionStatus(str, Enum):
    ACCEPTED = "accepted"
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
        raise ClaimGateError("claim gate values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ClaimGateError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        detail = []
        if missing:
            detail.append("missing=" + ",".join(missing))
        if extra:
            detail.append("extra=" + ",".join(extra))
        raise ClaimGateError(f"{label} has an invalid shape ({'; '.join(detail)})")
    return value


def _target_digest(target: TargetIdentity) -> str:
    return _digest(target.to_dict())


def _evidence_digest(evidence: Sequence[Evidence]) -> str:
    return _digest([item.to_dict() for item in evidence])


@dataclass(frozen=True)
class ClaimCandidate:
    """Immutable claim proposed to the gate, separate from its disposition."""

    target: TargetIdentity
    field_path: str
    value: JsonValue
    claim_entity: str
    relation: RelationToTarget
    evidence: tuple[Evidence, ...]
    benchmark_scope: dict[str, JsonValue] | None = None
    previous_candidate_id: str | None = None
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.target, TargetIdentity):
            raise ClaimGateError("candidate target must be a TargetIdentity")
        validate_field_value(self.field_path, self.value)
        object.__setattr__(self, "value", deepcopy(self.value))
        if not isinstance(self.claim_entity, str) or not self.claim_entity.strip():
            raise ClaimGateError("candidate claim_entity must be non-empty")
        try:
            object.__setattr__(self, "relation", RelationToTarget(self.relation))
        except (TypeError, ValueError) as exc:
            raise ClaimGateError("candidate relation is invalid") from exc
        evidence = tuple(self.evidence)
        if not evidence or not all(isinstance(item, Evidence) for item in evidence):
            raise ClaimGateError("candidate requires typed evidence")
        object.__setattr__(self, "evidence", evidence)
        if self.benchmark_scope is not None:
            _canonical(self.benchmark_scope)
            object.__setattr__(self, "benchmark_scope", deepcopy(self.benchmark_scope))
        if canonical_field_path(self.field_path) == "evaluation.benchmark_scores":
            if not isinstance(self.value, dict) or not isinstance(self.benchmark_scope, dict):
                raise ClaimGateError("benchmark score candidates require benchmark_scope")
            for key in ("benchmark", "metric", "setting"):
                if self.value.get(key) != self.benchmark_scope.get(key):
                    raise ClaimGateError(f"benchmark_scope disagrees on {key}")
        if self.previous_candidate_id is not None and (
            not isinstance(self.previous_candidate_id, str)
            or not _CANDIDATE_ID_RE.fullmatch(self.previous_candidate_id)
        ):
            raise ClaimGateError("previous_candidate_id is invalid")
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "target": self.target.to_dict(),
            "field_path": self.field_path,
            "value": deepcopy(self.value),
            "claim_entity": self.claim_entity,
            "relation": self.relation.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "benchmark_scope": deepcopy(self.benchmark_scope),
            "previous_candidate_id": self.previous_candidate_id,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    @property
    def candidate_id(self) -> str:
        return "claim-" + self.content_sha256[:24]

    @property
    def evidence_sha256(self) -> str:
        return _evidence_digest(self.evidence)

    def validate_integrity(self) -> None:
        if self._content_sha256 != _digest(self._content_payload()):
            raise ClaimGateError(f"candidate integrity failed: {self.candidate_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            **self._content_payload(),
            "candidate_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "ClaimCandidate":
        item = _strict_object(
            value,
            {
                "candidate_id",
                "target",
                "field_path",
                "value",
                "claim_entity",
                "relation",
                "evidence",
                "benchmark_scope",
                "previous_candidate_id",
                "candidate_sha256",
            },
            "claim candidate",
        )
        target_value = _strict_object(item["target"], {"model_id", "revision"}, "target")
        if not isinstance(item["evidence"], list) or not item["evidence"]:
            raise ClaimGateError("candidate evidence must be a non-empty array")
        candidate = cls(
            target=TargetIdentity.from_dict(target_value),
            field_path=item["field_path"],
            value=item["value"],
            claim_entity=item["claim_entity"],
            relation=item["relation"],
            evidence=tuple(_strict_evidence(entry) for entry in item["evidence"]),
            benchmark_scope=item["benchmark_scope"],
            previous_candidate_id=item["previous_candidate_id"],
        )
        if item["candidate_id"] != candidate.candidate_id:
            raise ClaimGateError("candidate_id does not match candidate content")
        if item["candidate_sha256"] != candidate.content_sha256:
            raise ClaimGateError("candidate_sha256 does not match candidate content")
        return candidate

    @classmethod
    def from_binding(cls, target: TargetIdentity, binding: Binding) -> "ClaimCandidate":
        if not isinstance(binding, Binding):
            raise ClaimGateError("binding adapter requires a Binding")
        return cls(
            target=target,
            field_path=binding.field_path,
            value=binding.value,
            claim_entity=binding.claim_entity,
            relation=binding.relation,
            evidence=binding.evidence,
            benchmark_scope=binding.benchmark_scope,
        )


def _strict_evidence(value: Any) -> Evidence:
    if not isinstance(value, dict):
        raise ClaimGateError("evidence must be an object")
    common = {
        "kind",
        "source_id",
        "source_uri",
        "source_role",
        "source_revision",
        "source_sha256",
        "source_target",
        "synthetic",
        "verified",
        "section_path",
        "table_id",
    }
    kind = value.get("kind")
    keys = common | (
        {"quote", "char_start", "char_end"}
        if kind == EvidenceKind.QUOTE.value
        else {"pointer", "fragment"}
        if kind == EvidenceKind.STRUCTURED.value
        else set()
    )
    _strict_object(value, keys, "evidence")
    if not keys - common:
        raise ClaimGateError("evidence kind is invalid")
    if value["source_target"] is not None:
        _strict_object(value["source_target"], {"model_id", "revision"}, "source target")
    try:
        return Evidence.from_dict(value)
    except (KeyError, TypeError, ValueError) as exc:
        raise ClaimGateError("evidence is malformed") from exc


def _checker_request_sha256(candidate: ClaimCandidate, gate: GateName) -> str:
    return _digest(
        {
            "gate_version": CLAIM_GATE_VERSION,
            "gate": gate.value,
            "candidate_sha256": candidate.content_sha256,
            "evidence_sha256": candidate.evidence_sha256,
            "field_path": candidate.field_path,
            "value": candidate.value,
            "benchmark_scope": candidate.benchmark_scope,
        }
    )


@dataclass(frozen=True)
class ProseCheckerDecision:
    """Bounded field-fit or value-support attestation for quote evidence."""

    gate: GateName
    checker: str
    method: str
    status: DecisionStatus
    reason: str
    request_sha256: str
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "gate", GateName(self.gate))
            object.__setattr__(self, "status", DecisionStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise ClaimGateError("prose checker decision enum is invalid") from exc
        if self.gate not in {GateName.FIELD_FIT, GateName.VALUE_SUPPORT}:
            raise ClaimGateError("prose checker may decide only field fit or value support")
        if not isinstance(self.checker, str) or not _CHECKER_RE.fullmatch(self.checker):
            raise ClaimGateError("prose checker name is invalid")
        if not isinstance(self.method, str) or not _METHOD_RE.fullmatch(self.method):
            raise ClaimGateError("prose checker method is invalid")
        if not isinstance(self.reason, str) or not _CODE_RE.fullmatch(self.reason):
            raise ClaimGateError("prose checker reason is invalid")
        if not isinstance(self.request_sha256, str) or not _DIGEST_RE.fullmatch(
            self.request_sha256
        ):
            raise ClaimGateError("prose checker request digest is invalid")
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, str]:
        return {
            "gate": self.gate.value,
            "checker": self.checker,
            "method": self.method,
            "status": self.status.value,
            "reason": self.reason,
            "request_sha256": self.request_sha256,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, str]:
        return {**self._content_payload(), "decision_sha256": self.content_sha256}

    @classmethod
    def for_candidate(
        cls,
        candidate: ClaimCandidate,
        *,
        gate: GateName,
        checker: str,
        method: str,
        status: DecisionStatus,
        reason: str,
    ) -> "ProseCheckerDecision":
        gate = GateName(gate)
        return cls(
            gate=gate,
            checker=checker,
            method=method,
            status=status,
            reason=reason,
            request_sha256=_checker_request_sha256(candidate, gate),
        )

    @classmethod
    def from_dict(cls, value: Any) -> "ProseCheckerDecision":
        item = _strict_object(
            value,
            {
                "gate",
                "checker",
                "method",
                "status",
                "reason",
                "request_sha256",
                "decision_sha256",
            },
            "prose checker decision",
        )
        decision = cls(
            gate=item["gate"],
            checker=item["checker"],
            method=item["method"],
            status=item["status"],
            reason=item["reason"],
            request_sha256=item["request_sha256"],
        )
        if item["decision_sha256"] != decision.content_sha256:
            raise ClaimGateError("prose checker decision digest mismatch")
        return decision


@dataclass(frozen=True)
class InputDigest:
    name: str
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not _CODE_RE.fullmatch(self.name):
            raise ClaimGateError("input digest name is invalid")
        if not isinstance(self.sha256, str) or not _DIGEST_RE.fullmatch(self.sha256):
            raise ClaimGateError("input digest is invalid")

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "InputDigest":
        item = _strict_object(value, {"name", "sha256"}, "input digest")
        return cls(name=item["name"], sha256=item["sha256"])


@dataclass(frozen=True)
class GateDecision:
    """One immutable independent gate outcome."""

    gate: GateName
    checker: str
    method: str
    status: DecisionStatus
    reason: str
    input_digests: tuple[InputDigest, ...]
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "gate", GateName(self.gate))
            object.__setattr__(self, "status", DecisionStatus(self.status))
        except (TypeError, ValueError) as exc:
            raise ClaimGateError("gate decision enum is invalid") from exc
        if not isinstance(self.checker, str) or not _CHECKER_RE.fullmatch(self.checker):
            raise ClaimGateError("gate checker name is invalid")
        if not isinstance(self.method, str) or not _METHOD_RE.fullmatch(self.method):
            raise ClaimGateError("gate method is invalid")
        if not isinstance(self.reason, str) or not _CODE_RE.fullmatch(self.reason):
            raise ClaimGateError("gate reason is invalid")
        inputs = tuple(self.input_digests)
        if not inputs or not all(isinstance(item, InputDigest) for item in inputs):
            raise ClaimGateError("gate decision requires typed input digests")
        names = [item.name for item in inputs]
        if len(names) != len(set(names)):
            raise ClaimGateError("gate decision has duplicate input digests")
        if names != sorted(names):
            raise ClaimGateError("gate input digests must be sorted by name")
        object.__setattr__(self, "input_digests", inputs)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "gate": self.gate.value,
            "checker": self.checker,
            "method": self.method,
            "status": self.status.value,
            "reason": self.reason,
            "input_digests": [item.to_dict() for item in self.input_digests],
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "decision_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "GateDecision":
        item = _strict_object(
            value,
            {
                "gate",
                "checker",
                "method",
                "status",
                "reason",
                "input_digests",
                "decision_sha256",
            },
            "gate decision",
        )
        if not isinstance(item["input_digests"], list):
            raise ClaimGateError("gate input_digests must be an array")
        decision = cls(
            gate=item["gate"],
            checker=item["checker"],
            method=item["method"],
            status=item["status"],
            reason=item["reason"],
            input_digests=tuple(InputDigest.from_dict(entry) for entry in item["input_digests"]),
        )
        if item["decision_sha256"] != decision.content_sha256:
            raise ClaimGateError("gate decision digest mismatch")
        return decision


@dataclass(frozen=True)
class ClaimGateRecord:
    """Strictly serializable complete four-decision gate record."""

    candidate: ClaimCandidate
    registry_name: str
    registry_version: str
    registry_sha256: str
    checker_decisions: tuple[ProseCheckerDecision, ...]
    decisions: tuple[GateDecision, ...]
    gate_version: str = CLAIM_GATE_VERSION
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.gate_version != CLAIM_GATE_VERSION:
            raise ClaimGateError("claim gate version is not recognized")
        if not isinstance(self.candidate, ClaimCandidate):
            raise ClaimGateError("gate record candidate is malformed")
        self.candidate.validate_integrity()
        if self.registry_name != POINTER_REGISTRY_NAME:
            raise ClaimGateError("gate record pointer registry name is not recognized")
        if self.registry_version != POINTER_REGISTRY_VERSION:
            raise ClaimGateError("gate record pointer registry version is not recognized")
        if not isinstance(self.registry_sha256, str) or not _DIGEST_RE.fullmatch(
            self.registry_sha256
        ):
            raise ClaimGateError("gate record pointer registry digest is invalid")
        if self.registry_sha256 != DEFAULT_POINTER_FIELD_REGISTRY.sha256:
            raise ClaimGateError("gate record pointer registry content is not recognized")

        checks = tuple(self.checker_decisions)
        if not all(isinstance(item, ProseCheckerDecision) for item in checks):
            raise ClaimGateError("gate record contains malformed checker decisions")
        checker_gates = [item.gate for item in checks]
        if len(checker_gates) != len(set(checker_gates)):
            raise ClaimGateError("duplicate or ambiguous prose checker decisions")
        if checker_gates != sorted(checker_gates, key=lambda item: GATE_ORDER.index(item)):
            raise ClaimGateError("prose checker decisions are not in canonical order")
        for item in checks:
            if item.request_sha256 != _checker_request_sha256(self.candidate, item.gate):
                raise ClaimGateError("stale prose checker decision")
        evidence_kinds = {item.kind for item in self.candidate.evidence}
        if evidence_kinds != {EvidenceKind.QUOTE} and checks:
            raise ClaimGateError("structured gate record cannot carry prose checker decisions")
        object.__setattr__(self, "checker_decisions", checks)

        decisions = tuple(self.decisions)
        if tuple(item.gate for item in decisions) != GATE_ORDER:
            raise ClaimGateError("gate record requires exactly one canonical decision per gate")
        common = {
            "candidate": self.candidate.content_sha256,
            "evidence": self.candidate.evidence_sha256,
            "target": _target_digest(self.candidate.target),
        }
        for decision in decisions:
            values = {item.name: item.sha256 for item in decision.input_digests}
            if any(values.get(key) != digest for key, digest in common.items()):
                raise ClaimGateError(f"stale {decision.gate.value} decision")
            required_extra = {
                GateName.COORDINATE_INTEGRITY: {"replay_sources"},
                GateName.ENTITY_SCOPE: {"scope_policy"},
            }.get(decision.gate, set())
            if not required_extra <= set(values):
                raise ClaimGateError(f"incomplete {decision.gate.value} input digests")
        check_by_gate = {item.gate: item for item in checks}
        decision_by_gate = {item.gate: item for item in decisions}
        for gate, checker_decision in check_by_gate.items():
            inputs = {
                item.name: item.sha256 for item in decision_by_gate[gate].input_digests
            }
            if inputs.get("checker_decision") != checker_decision.content_sha256:
                raise ClaimGateError(f"unused or ambiguous {gate.value} checker decision")
        object.__setattr__(self, "decisions", decisions)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    @property
    def projection_eligible(self) -> bool:
        return all(item.status is DecisionStatus.ACCEPTED for item in self.decisions)

    def _content_payload(self) -> dict[str, Any]:
        return {
            "gate_version": self.gate_version,
            "candidate": self.candidate.to_dict(),
            "registry": {
                "name": self.registry_name,
                "version": self.registry_version,
                "sha256": self.registry_sha256,
            },
            "checker_decisions": [item.to_dict() for item in self.checker_decisions],
            "decisions": [item.to_dict() for item in self.decisions],
            "projection_eligible": self.projection_eligible,
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def validate_integrity(self) -> None:
        self.candidate.validate_integrity()
        if self._content_sha256 != _digest(self._content_payload()):
            raise ClaimGateError("claim gate record integrity failed")

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "record_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "ClaimGateRecord":
        item = _strict_object(
            value,
            {
                "gate_version",
                "candidate",
                "registry",
                "checker_decisions",
                "decisions",
                "projection_eligible",
                "record_sha256",
            },
            "claim gate record",
        )
        registry = _strict_object(
            item["registry"], {"name", "version", "sha256"}, "pointer registry reference"
        )
        if not isinstance(item["checker_decisions"], list):
            raise ClaimGateError("checker_decisions must be an array")
        if not isinstance(item["decisions"], list):
            raise ClaimGateError("decisions must be an array")
        record = cls(
            gate_version=item["gate_version"],
            candidate=ClaimCandidate.from_dict(item["candidate"]),
            registry_name=registry["name"],
            registry_version=registry["version"],
            registry_sha256=registry["sha256"],
            checker_decisions=tuple(
                ProseCheckerDecision.from_dict(entry) for entry in item["checker_decisions"]
            ),
            decisions=tuple(GateDecision.from_dict(entry) for entry in item["decisions"]),
        )
        if not isinstance(item["projection_eligible"], bool):
            raise ClaimGateError("projection_eligible must be boolean")
        if item["projection_eligible"] != record.projection_eligible:
            raise ClaimGateError("projection_eligible disagrees with independent decisions")
        if item["record_sha256"] != record.content_sha256:
            raise ClaimGateError("claim gate record digest mismatch")
        return record


def _inputs(candidate: ClaimCandidate, **extra: str) -> tuple[InputDigest, ...]:
    values = {
        "candidate": candidate.content_sha256,
        "evidence": candidate.evidence_sha256,
        "target": _target_digest(candidate.target),
        **extra,
    }
    return tuple(InputDigest(name, values[name]) for name in sorted(values))


def _decision(
    candidate: ClaimCandidate,
    *,
    gate: GateName,
    checker: str,
    method: str,
    status: DecisionStatus,
    reason: str,
    **extra_inputs: str,
) -> GateDecision:
    return GateDecision(
        gate=gate,
        checker=checker,
        method=method,
        status=status,
        reason=reason,
        input_digests=_inputs(candidate, **extra_inputs),
    )


def _source_input_digest(sources: Sequence[SourceDocument]) -> str:
    values = []
    for source in sources:
        values.append(
            {
                "source_id": source.source_id,
                "source_uri": source.source_uri,
                "role": source.role.value,
                "source_revision": source.source_revision,
                "target": source.target.to_dict() if source.target else None,
                "synthetic": source.synthetic,
                "sha256": source.sha256,
            }
        )
    return _digest(sorted(values, key=_canonical))


def _coordinate_decision(
    candidate: ClaimCandidate, sources: Sequence[SourceDocument]
) -> GateDecision:
    source_digest = _source_input_digest(sources)
    by_id: dict[str, list[SourceDocument]] = {}
    for source in sources:
        if not isinstance(source, SourceDocument):
            raise ClaimGateError("replay sources must be SourceDocument instances")
        by_id.setdefault(source.source_id, []).append(source)

    reason = "coordinates_replayed"
    status = DecisionStatus.ACCEPTED
    for evidence in candidate.evidence:
        matches = by_id.get(evidence.source_id, [])
        if not matches:
            status, reason = DecisionStatus.WITHHELD, "replay_source_missing"
            break
        if len(matches) != 1:
            status, reason = DecisionStatus.WITHHELD, "replay_source_ambiguous"
            break
        source = matches[0]
        if (
            source.source_uri != evidence.source_uri
            or source.role is not evidence.source_role
            or source.source_revision != evidence.source_revision
            or source.target != evidence.source_target
            or source.synthetic != evidence.synthetic
            or source.sha256 != evidence.source_sha256
        ):
            status, reason = DecisionStatus.WITHHELD, "replay_source_identity_mismatch"
            break
        if evidence.kind is EvidenceKind.QUOTE:
            if source.text is None or not evidence.verified:
                status, reason = DecisionStatus.WITHHELD, "quote_coordinates_unverified"
                break
            normalized = normalize_ws(source.text)
            start, end = evidence.char_start, evidence.char_end
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start < 0
                or end <= start
                or normalized[start:end] != evidence.quote
            ):
                status, reason = DecisionStatus.WITHHELD, "quote_coordinate_mismatch"
                break
        else:
            if source.data is None or not evidence.verified:
                status, reason = DecisionStatus.WITHHELD, "pointer_coordinates_unverified"
                break
            try:
                replayed = resolve_json_pointer(source.data, evidence.pointer or "")
            except (KeyError, IndexError, TypeError, ValueError):
                status, reason = DecisionStatus.WITHHELD, "pointer_replay_failed"
                break
            if _canonical(replayed) != _canonical(evidence.fragment):
                status, reason = DecisionStatus.WITHHELD, "pointer_fragment_mismatch"
                break
    return _decision(
        candidate,
        gate=GateName.COORDINATE_INTEGRITY,
        checker=_GATE_CHECKER,
        method="offline_frozen_source_replay",
        status=status,
        reason=reason,
        replay_sources=source_digest,
    )


def _split_entity(entity: str) -> tuple[str, str | None]:
    if "@" not in entity:
        return entity, None
    model_id, revision = entity.rsplit("@", 1)
    return model_id, revision if _REVISION_RE.fullmatch(revision) else None


def _entity_scope_decision(candidate: ClaimCandidate) -> GateDecision:
    base = canonical_field_path(candidate.field_path)
    relation = candidate.relation
    status = DecisionStatus.ACCEPTED
    reason = "entity_scope_exact"

    if relation is RelationToTarget.EXACT_TARGET:
        if base == "evaluation.related_model_scores":
            status, reason = DecisionStatus.WITHHELD, "relation_not_permitted_for_field"
        elif candidate.claim_entity != f"{candidate.target.model_id}@{candidate.target.revision}":
            status, reason = DecisionStatus.WITHHELD, "claim_entity_target_mismatch"
        elif any(item.source_target != candidate.target for item in candidate.evidence):
            status, reason = DecisionStatus.WITHHELD, "source_target_not_exact"
        elif any(
            item.source_role
            in {SourceRole.HUGGING_FACE_METADATA, SourceRole.HUGGING_FACE_SNAPSHOT}
            and item.source_revision != candidate.target.revision
            for item in candidate.evidence
        ):
            status, reason = DecisionStatus.WITHHELD, "source_revision_not_exact"
    elif relation is RelationToTarget.BASE_MODEL:
        model_id, _ = _split_entity(candidate.claim_entity)
        value_id = candidate.value.get("model_id") if isinstance(candidate.value, dict) else None
        if base != "lineage.base_models":
            status, reason = DecisionStatus.WITHHELD, "relation_not_permitted_for_field"
        elif not value_id or model_id != value_id:
            status, reason = DecisionStatus.WITHHELD, "base_claim_entity_mismatch"
        elif any(item.source_target != candidate.target for item in candidate.evidence):
            status, reason = DecisionStatus.WITHHELD, "base_relation_source_not_target_manifest"
        else:
            reason = "explicit_base_relation"
    elif relation in {
        RelationToTarget.SIBLING_CHECKPOINT,
        RelationToTarget.COMPARISON_MODEL,
    }:
        model_id, revision = _split_entity(candidate.claim_entity)
        if base != "evaluation.related_model_scores":
            status, reason = DecisionStatus.WITHHELD, "relation_not_permitted_for_field"
        elif revision is None:
            status, reason = DecisionStatus.WITHHELD, "related_revision_unresolved"
        elif not isinstance(candidate.value, dict) or candidate.value.get("model_id") != model_id:
            status, reason = DecisionStatus.WITHHELD, "related_claim_entity_mismatch"
        elif any(
            item.source_target is None
            or item.source_target.model_id != model_id
            or item.source_target.revision != revision
            for item in candidate.evidence
        ):
            status, reason = DecisionStatus.WITHHELD, "related_source_target_mismatch"
        else:
            reason = "explicit_related_model_relation"
    else:
        status, reason = DecisionStatus.WITHHELD, "relation_not_projection_eligible"

    return _decision(
        candidate,
        gate=GateName.ENTITY_SCOPE,
        checker=_GATE_CHECKER,
        method="closed_relation_scope_policy",
        status=status,
        reason=reason,
        scope_policy=_digest(_SCOPE_POLICY),
    )


def _checker_for(
    checker_decisions: Mapping[GateName, ProseCheckerDecision], gate: GateName
) -> ProseCheckerDecision | None:
    return checker_decisions.get(gate)


def _field_fit_decision(
    candidate: ClaimCandidate,
    registry: PointerFieldRegistry,
    checker_decisions: Mapping[GateName, ProseCheckerDecision],
) -> GateDecision:
    kinds = {item.kind for item in candidate.evidence}
    if len(kinds) != 1:
        return _decision(
            candidate,
            gate=GateName.FIELD_FIT,
            checker=_GATE_CHECKER,
            method="closed_evidence_kind_dispatch",
            status=DecisionStatus.WITHHELD,
            reason="mixed_evidence_kinds",
            registry=registry.sha256,
        )
    if kinds == {EvidenceKind.STRUCTURED}:
        status = DecisionStatus.ACCEPTED
        reason = "registered_pointer_field_fit"
        reason_by_status = {
            PointerLookupStatus.UNREGISTERED: "structured_pointer_unregistered",
            PointerLookupStatus.WRONG_FIELD: "structured_pointer_wrong_field",
            PointerLookupStatus.SHAPE_MISMATCH: "structured_fragment_shape_mismatch",
            PointerLookupStatus.AMBIGUOUS: "structured_pointer_ambiguous",
        }
        for evidence in candidate.evidence:
            lookup = registry.lookup(
                source_role=evidence.source_role,
                pointer=evidence.pointer or "",
                field_path=candidate.field_path,
                fragment=evidence.fragment,
            )
            if lookup.status is not PointerLookupStatus.MATCHED:
                status = DecisionStatus.WITHHELD
                reason = reason_by_status[lookup.status]
                break
        return _decision(
            candidate,
            gate=GateName.FIELD_FIT,
            checker=_GATE_CHECKER,
            method="closed_pointer_field_registry",
            status=status,
            reason=reason,
            registry=registry.sha256,
        )

    checker = _checker_for(checker_decisions, GateName.FIELD_FIT)
    if checker is None:
        return _decision(
            candidate,
            gate=GateName.FIELD_FIT,
            checker=_GATE_CHECKER,
            method="bounded_prose_checker_availability",
            status=DecisionStatus.WITHHELD,
            reason="prose_field_checker_unavailable",
            checker_request=_checker_request_sha256(candidate, GateName.FIELD_FIT),
        )
    return _decision(
        candidate,
        gate=GateName.FIELD_FIT,
        checker=checker.checker,
        method=checker.method,
        status=checker.status,
        reason=checker.reason,
        checker_decision=checker.content_sha256,
    )


def _leaf_values(value: Any) -> list[Any]:
    if isinstance(value, dict):
        result: list[Any] = []
        for key in sorted(value):
            result.extend(_leaf_values(value[key]))
        return result
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(_leaf_values(item))
        return result
    return [value]


def _source_refs(evidence: Iterable[Evidence]) -> list[str]:
    return sorted({item.source_id for item in evidence})


def _wrapper_id(
    *,
    prefix: str,
    field_path: str,
    description: str,
    origin: str,
    source_refs: Sequence[str],
) -> str:
    content = {
        "policy": "claim-support-gate-wrapper/v1",
        "field_path": canonical_field_path(field_path),
        "description": description,
        "origin": origin,
        "source_refs": list(source_refs),
    }
    return prefix + _digest(content)[:24]


def make_context_statement_value(
    *,
    field_path: str,
    description: str,
    origin: str,
    evidence: Iterable[Evidence],
) -> dict[str, JsonValue]:
    """Build the only deterministic quote-bound contextStatement wrapper."""

    base = canonical_field_path(field_path)
    if base not in _CONTEXT_FIELDS:
        raise ClaimGateError("contextStatement wrapper is not permitted for this field")
    if not isinstance(description, str) or not description:
        raise ClaimGateError("contextStatement description must be non-empty")
    if origin not in {"publisher_reported", "source_derived"}:
        raise ClaimGateError("quote-bound contextStatement origin is not permitted")
    evidence_items = tuple(evidence)
    if not evidence_items or not all(isinstance(item, Evidence) for item in evidence_items):
        raise ClaimGateError("contextStatement wrapper requires typed evidence")
    refs = _source_refs(evidence_items)
    return {
        "context_id": _wrapper_id(
            prefix="context:",
            field_path=base,
            description=description,
            origin=origin,
            source_refs=refs,
        ),
        "description": description,
        "origin": origin,
        "source_refs": refs,
    }


def make_mitigation_value(
    *,
    description: str,
    evidence: Iterable[Evidence],
    origin: str = "publisher_reported",
) -> dict[str, JsonValue]:
    """Build the only deterministic quote-bound mitigation wrapper."""

    if not isinstance(description, str) or not description:
        raise ClaimGateError("mitigation description must be non-empty")
    if origin != "publisher_reported":
        raise ClaimGateError("quote-bound mitigation origin must be publisher_reported")
    evidence_items = tuple(evidence)
    if not evidence_items or not all(isinstance(item, Evidence) for item in evidence_items):
        raise ClaimGateError("mitigation wrapper requires typed evidence")
    refs = _source_refs(evidence_items)
    field_path = "use_and_risk.mitigations"
    return {
        "mitigation_id": _wrapper_id(
            prefix="mitigation:",
            field_path=field_path,
            description=description,
            origin=origin,
            source_refs=refs,
        ),
        "description": description,
        "origin": origin,
        "source_refs": refs,
    }


def make_publisher_risk_value(
    *,
    name: str,
    description: str,
    applicability_rationale: str,
    evidence: Iterable[Evidence],
    mitigation_refs: Iterable[str] = (),
) -> dict[str, JsonValue]:
    """Build the closed source-bound wrapper for a publisher-reported risk.

    Taxonomy-identified risks deliberately cannot use this constructor; they
    require a separate taxonomy applicability derivation.
    """

    substantive = {
        "name": name,
        "description": description,
        "applicability_rationale": applicability_rationale,
    }
    if any(not isinstance(value, str) or not value for value in substantive.values()):
        raise ClaimGateError("publisher risk substantive values must be non-empty")
    evidence_items = tuple(evidence)
    if not evidence_items or not all(isinstance(item, Evidence) for item in evidence_items):
        raise ClaimGateError("publisher risk wrapper requires typed evidence")
    refs = _source_refs(evidence_items)
    raw_mitigations = tuple(mitigation_refs)
    if any(
        not isinstance(item, str)
        or not re.fullmatch(r"mitigation:[a-z0-9][a-z0-9._-]*", item)
        for item in raw_mitigations
    ):
        raise ClaimGateError("publisher risk mitigation_refs are invalid")
    if raw_mitigations:
        raise ClaimGateError(
            "publisher risk mitigation links require a separate validated link derivation"
        )
    mitigations: tuple[str, ...] = ()
    id_payload = {
        "policy": "publisher-reported-risk-wrapper/v1",
        **substantive,
        "source_refs": refs,
        "mitigation_refs": list(mitigations),
    }
    return {
        "risk_id": "publisher-risk:" + _digest(id_payload)[:24],
        "identification_origin": "publisher_reported",
        "taxonomy": None,
        "name": name,
        "description": description,
        "applicability_rationale": applicability_rationale,
        "grounds": [
            {
                "kind": "card_field",
                "ref": "use_and_risk.identified_risks",
                "relevance": "Direct publisher evidence supports this risk.",
            }
        ],
        "source_refs": refs,
        "mapping_provenance": {
            "method": "source_binding",
            "tool_version": CLAIM_GATE_VERSION,
            "inference_model": None,
            "inference_config_sha256": None,
        },
        "review_status": "generated_unreviewed",
        "mitigation_assessment": "none_identified",
        "mitigation_refs": list(mitigations),
    }


def _bounded_prose_leaves(candidate: ClaimCandidate) -> tuple[list[Any], str | None]:
    """Return supported prose leaves after exact field-scoped wrapper checks."""

    base = canonical_field_path(candidate.field_path)
    if base in _CONTEXT_FIELDS:
        if not isinstance(candidate.value, dict):  # guarded by contract; keep fail-closed
            return [], "deterministic_wrapper_metadata_invalid"
        description = candidate.value.get("description")
        origin = candidate.value.get("origin")
        if not isinstance(description, str) or not isinstance(origin, str):
            return [], "deterministic_wrapper_metadata_invalid"
        try:
            expected = make_context_statement_value(
                field_path=base,
                description=description,
                origin=origin,
                evidence=candidate.evidence,
            )
        except ClaimGateError:
            return [], "deterministic_wrapper_metadata_invalid"
        if _canonical(candidate.value) != _canonical(expected):
            return [], "deterministic_wrapper_metadata_invalid"
        return [description], None
    if base == "use_and_risk.mitigations":
        if not isinstance(candidate.value, dict):
            return [], "deterministic_wrapper_metadata_invalid"
        description = candidate.value.get("description")
        origin = candidate.value.get("origin")
        if not isinstance(description, str) or not isinstance(origin, str):
            return [], "deterministic_wrapper_metadata_invalid"
        try:
            expected = make_mitigation_value(
                description=description,
                origin=origin,
                evidence=candidate.evidence,
            )
        except ClaimGateError:
            return [], "deterministic_wrapper_metadata_invalid"
        if _canonical(candidate.value) != _canonical(expected):
            return [], "deterministic_wrapper_metadata_invalid"
        return [description], None
    if base == "use_and_risk.identified_risks":
        if not isinstance(candidate.value, dict):
            return [], "deterministic_wrapper_metadata_invalid"
        try:
            expected = make_publisher_risk_value(
                name=candidate.value["name"],
                description=candidate.value["description"],
                applicability_rationale=candidate.value["applicability_rationale"],
                evidence=candidate.evidence,
                mitigation_refs=candidate.value["mitigation_refs"],
            )
        except (ClaimGateError, KeyError, TypeError):
            return [], "deterministic_wrapper_metadata_invalid"
        if _canonical(candidate.value) != _canonical(expected):
            return [], "deterministic_wrapper_metadata_invalid"
        return [
            candidate.value["name"],
            candidate.value["description"],
            candidate.value["applicability_rationale"],
        ], None
    return _leaf_values(candidate.value), None


def _number_supported(value: int | float, corpus: str) -> bool:
    try:
        expected = Decimal(str(value))
    except InvalidOperation:
        return False
    for token in _NUMBER_RE.findall(corpus):
        try:
            if Decimal(token) == expected:
                return True
        except InvalidOperation:
            continue
    return False


def _leaf_supported(value: Any, corpus: str) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return str(value).casefold() in corpus.casefold()
    if isinstance(value, (int, float)):
        return _number_supported(value, corpus)
    if isinstance(value, str):
        normalized = normalize_ws(value)
        return bool(normalized) and normalized.casefold() in corpus.casefold()
    return False


def _license_conflict(candidate: ClaimCandidate, corpus: str) -> bool:
    if canonical_field_path(candidate.field_path) != "identity.license":
        return False
    patterns = {
        "mit": r"\bmit\b",
        "apache-2.0": r"\bapache(?:[- ]2(?:\.0)?)?\b",
        "gpl": r"\bgpl(?:v?[23])?\b",
        "bsd": r"\bbsd(?:[- ][23][ -]clause)?\b",
        "cc-by": r"\bcc[- ]by\b",
    }
    observed = {name for name, pattern in patterns.items() if re.search(pattern, corpus, re.I)}
    return len(observed) > 1


def _value_support_decision(
    candidate: ClaimCandidate,
    checker_decisions: Mapping[GateName, ProseCheckerDecision],
) -> GateDecision:
    kinds = {item.kind for item in candidate.evidence}
    if len(kinds) != 1:
        return _decision(
            candidate,
            gate=GateName.VALUE_SUPPORT,
            checker=_GATE_CHECKER,
            method="closed_evidence_kind_dispatch",
            status=DecisionStatus.WITHHELD,
            reason="mixed_evidence_kinds",
        )
    if candidate.value in ("Not specified", "Not applicable"):
        return _decision(
            candidate,
            gate=GateName.VALUE_SUPPORT,
            checker=_GATE_CHECKER,
            method="exact_complete_value_replay",
            status=DecisionStatus.WITHHELD,
            reason="absence_value_not_supported",
        )

    if kinds == {EvidenceKind.STRUCTURED}:
        fragments = [_canonical(item.fragment) for item in candidate.evidence]
        if len(set(fragments)) > 1:
            status, reason = DecisionStatus.WITHHELD, "conflicting_evidence_values"
        elif any(fragment != _canonical(candidate.value) for fragment in fragments):
            status, reason = DecisionStatus.WITHHELD, "structured_value_not_exact"
        else:
            status, reason = DecisionStatus.ACCEPTED, "complete_structured_value_supported"
        return _decision(
            candidate,
            gate=GateName.VALUE_SUPPORT,
            checker=_GATE_CHECKER,
            method="exact_structured_value_equality",
            status=status,
            reason=reason,
        )

    checker = _checker_for(checker_decisions, GateName.VALUE_SUPPORT)
    if checker is None:
        return _decision(
            candidate,
            gate=GateName.VALUE_SUPPORT,
            checker=_GATE_CHECKER,
            method="bounded_prose_checker_availability",
            status=DecisionStatus.WITHHELD,
            reason="prose_value_checker_unavailable",
            checker_request=_checker_request_sha256(candidate, GateName.VALUE_SUPPORT),
        )
    if checker.status is DecisionStatus.WITHHELD:
        return _decision(
            candidate,
            gate=GateName.VALUE_SUPPORT,
            checker=checker.checker,
            method=checker.method,
            status=checker.status,
            reason=checker.reason,
            checker_decision=checker.content_sha256,
        )

    corpus = " ".join(item.quote or "" for item in candidate.evidence)
    proposed, wrapper_error = _bounded_prose_leaves(candidate)
    if candidate.benchmark_scope is not None:
        proposed.extend(_leaf_values(candidate.benchmark_scope))
    if wrapper_error is not None:
        status, reason = DecisionStatus.WITHHELD, wrapper_error
    elif _license_conflict(candidate, corpus):
        status, reason = DecisionStatus.WITHHELD, "conflicting_evidence_values"
    elif not proposed or any(not _leaf_supported(item, corpus) for item in proposed):
        status, reason = DecisionStatus.WITHHELD, "complete_value_not_in_evidence"
    else:
        status, reason = DecisionStatus.ACCEPTED, "complete_prose_value_supported"
    return _decision(
        candidate,
        gate=GateName.VALUE_SUPPORT,
        checker=_GATE_CHECKER,
        method="exact_leaf_coverage_after_bounded_checker",
        status=status,
        reason=reason,
        checker_decision=checker.content_sha256,
        wrapper_policy=_digest(_WRAPPER_POLICY),
    )


def evaluate_claim_gate(
    candidate: ClaimCandidate,
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    checker_decisions: Iterable[ProseCheckerDecision] = (),
    *,
    registry: PointerFieldRegistry = DEFAULT_POINTER_FIELD_REGISTRY,
) -> ClaimGateRecord:
    """Evaluate all four decisions independently and return an immutable record."""

    if not isinstance(candidate, ClaimCandidate):
        raise ClaimGateError("evaluate_claim_gate requires a ClaimCandidate")
    candidate.validate_integrity()
    if not isinstance(registry, PointerFieldRegistry):
        raise ClaimGateError("registry must be a PointerFieldRegistry")
    if (
        registry.name != POINTER_REGISTRY_NAME
        or registry.version != POINTER_REGISTRY_VERSION
        or registry.sha256 != DEFAULT_POINTER_FIELD_REGISTRY.sha256
    ):
        raise ClaimGateError("registry is not the closed Claim Support Gate v1 registry")
    source_values = tuple(sources.values()) if isinstance(sources, Mapping) else tuple(sources)
    checks = tuple(checker_decisions)
    if not all(isinstance(item, ProseCheckerDecision) for item in checks):
        raise ClaimGateError("checker decisions are malformed")
    check_map: dict[GateName, ProseCheckerDecision] = {}
    for item in checks:
        if item.gate in check_map:
            raise ClaimGateError("duplicate or ambiguous checker decision")
        if item.request_sha256 != _checker_request_sha256(candidate, item.gate):
            raise ClaimGateError("stale checker decision")
        check_map[item.gate] = item
    kinds = {item.kind for item in candidate.evidence}
    if kinds != {EvidenceKind.QUOTE} and checks:
        raise ClaimGateError("structured candidates cannot carry prose checker decisions")
    canonical_checks = tuple(check_map[gate] for gate in GATE_ORDER if gate in check_map)

    decisions = (
        _coordinate_decision(candidate, source_values),
        _entity_scope_decision(candidate),
        _field_fit_decision(candidate, registry, check_map),
        _value_support_decision(candidate, check_map),
    )
    return ClaimGateRecord(
        candidate=candidate,
        registry_name=registry.name,
        registry_version=registry.version,
        registry_sha256=registry.sha256,
        checker_decisions=canonical_checks,
        decisions=decisions,
    )


def verify_claim_gate_record(
    record: ClaimGateRecord,
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    *,
    registry: PointerFieldRegistry = DEFAULT_POINTER_FIELD_REGISTRY,
) -> None:
    """Strictly replay a record; raise on source drift or any changed decision."""

    if not isinstance(record, ClaimGateRecord):
        raise ClaimGateReplayError("record must be a ClaimGateRecord")
    record.validate_integrity()
    if (
        record.registry_name != registry.name
        or record.registry_version != registry.version
        or record.registry_sha256 != registry.sha256
    ):
        raise ClaimGateReplayError("pointer registry is stale or mismatched")
    replayed = evaluate_claim_gate(
        record.candidate,
        sources,
        record.checker_decisions,
        registry=registry,
    )
    if _canonical(replayed.to_dict()) != _canonical(record.to_dict()):
        raise ClaimGateReplayError("claim gate decision replay mismatch")


_UNCHANGED = object()


def correct_candidate(
    prior: ClaimCandidate,
    *,
    field_path: str | object = _UNCHANGED,
    value: JsonValue | object = _UNCHANGED,
    claim_entity: str | object = _UNCHANGED,
    relation: RelationToTarget | str | object = _UNCHANGED,
    evidence: Iterable[Evidence] | object = _UNCHANGED,
    benchmark_scope: dict[str, JsonValue] | None | object = _UNCHANGED,
) -> ClaimCandidate:
    """Create a linked replacement candidate; never mutate or reassign ``prior``."""

    if not isinstance(prior, ClaimCandidate):
        raise ClaimGateError("correction requires a ClaimCandidate")
    corrected = ClaimCandidate(
        target=prior.target,
        field_path=prior.field_path if field_path is _UNCHANGED else field_path,
        value=prior.value if value is _UNCHANGED else value,
        claim_entity=prior.claim_entity if claim_entity is _UNCHANGED else claim_entity,
        relation=prior.relation if relation is _UNCHANGED else relation,
        evidence=prior.evidence if evidence is _UNCHANGED else tuple(evidence),
        benchmark_scope=(
            prior.benchmark_scope if benchmark_scope is _UNCHANGED else benchmark_scope
        ),
        previous_candidate_id=prior.candidate_id,
    )
    comparison = replace(corrected, previous_candidate_id=prior.previous_candidate_id)
    if comparison.content_sha256 == prior.content_sha256:
        raise ClaimGateError("correction must change candidate content")
    return corrected


__all__ = [
    "CLAIM_GATE_VERSION",
    "ClaimCandidate",
    "ClaimGateError",
    "ClaimGateRecord",
    "ClaimGateReplayError",
    "DecisionStatus",
    "GATE_ORDER",
    "GateDecision",
    "GateName",
    "InputDigest",
    "ProseCheckerDecision",
    "correct_candidate",
    "evaluate_claim_gate",
    "make_context_statement_value",
    "make_mitigation_value",
    "make_publisher_risk_value",
    "verify_claim_gate_record",
]
