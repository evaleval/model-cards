"""Typed records for sources, evidence, bindings, and review events."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Union

from .schema import (
    canonical_field_path,
    parse_field_path,
    validate_field_path,
    validate_field_value,
)


JsonValue = Union[None, bool, int, float, str, list["JsonValue"], dict[str, "JsonValue"]]

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._:-]{1,127}$")
_CHECK_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_TABLE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_PUBLIC_SOURCE_URI_RE = re.compile(
    r"^(?:https://(?!(?:localhost|127\.0\.0\.1)(?::|/|$))[^\s]+|"
    r"hf://[^\s]+|doi:[^\s]+|arxiv:[0-9.]+|urn:sha256:[0-9a-f]{64})$"
)
TAXONOMY_RISK_DERIVATION_VERSION = "taxonomy-risk-derivation/v1"
_CLAIM_ID_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_RISK_CANDIDATE_ID_RE = re.compile(r"^risk-candidate-[0-9a-f]{24}$")
_DERIVATION_ID_RE = re.compile(r"^derivation-[0-9a-f]{24}$")


def _require_json(value: Any, *, name: str) -> JsonValue:
    try:
        json.dumps(value, allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite JSON value") from exc
    return value


def _enum(enum_type: type[Enum], value: Any, *, name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise ValueError(f"{name} must be one of: {allowed}") from exc


def _json_equal(left: Any, right: Any) -> bool:
    def canonical(value: Any) -> str:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    return canonical(left) == canonical(right)


class SourceRole(str, Enum):
    """Allowed authority roles for this exact-target baseline."""

    HUGGING_FACE_METADATA = "hugging_face_metadata"
    HUGGING_FACE_SNAPSHOT = "hugging_face_snapshot"
    DEVELOPER_REPORT = "developer_report"
    DEVELOPER_CODE = "developer_code"
    EEE_INDEX = "eee_index"


class RelationToTarget(str, Enum):
    """How the claim entity relates to the exact target checkpoint."""

    EXACT_TARGET = "exact_target"
    BASE_MODEL = "base_model"
    DERIVATIVE_MODEL = "derivative_model"
    MODEL_FAMILY = "model_family"
    SIBLING_CHECKPOINT = "sibling_checkpoint"
    COMPARISON_MODEL = "comparison_model"
    UNKNOWN = "unknown"


class EvidenceKind(str, Enum):
    QUOTE = "quote"
    STRUCTURED = "structured"


class BindingOrigin(str, Enum):
    QUOTED = "quoted"
    STRUCTURED = "structured"


class Disposition(str, Enum):
    ACCEPTED = "accepted"
    WITHHELD = "withheld"
    REJECTED = "rejected"


class ReviewAction(str, Enum):
    ACCEPT = "accept"
    WITHHOLD = "withhold"
    REASSIGN = "reassign"


class LifecycleStatus(str, Enum):
    """Honest automated candidate states exposed by the public contract."""

    GENERATED_UNREVIEWED = "generated_unreviewed"
    GENERATED_VALIDATED = "generated_validated"


class ValidationCheckStatus(str, Enum):
    NOT_RUN = "not_run"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ValidationCheck:
    """Closed summary of one automated validation gate."""

    check_id: str
    status: ValidationCheckStatus
    checked: int = 0
    passed: int = 0
    withheld: int = 0
    failed: int = 0
    unavailable: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.check_id, str) or not _CHECK_ID_RE.fullmatch(self.check_id):
            raise ValueError("validation check_id is invalid")
        object.__setattr__(
            self,
            "status",
            _enum(ValidationCheckStatus, self.status, name="validation check status"),
        )
        counts = (self.checked, self.passed, self.withheld, self.failed, self.unavailable)
        if any(not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in counts):
            raise ValueError("validation check counts must be non-negative integers")
        if self.passed + self.withheld + self.failed + self.unavailable > self.checked:
            raise ValueError("validation check outcomes cannot exceed checked items")
        if self.status is ValidationCheckStatus.NOT_RUN and any(counts):
            raise ValueError("a not-run validation check cannot report counts")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "check_id": self.check_id,
            "status": self.status.value,
            "checked": self.checked,
            "passed": self.passed,
            "withheld": self.withheld,
            "failed": self.failed,
            "unavailable": self.unavailable,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ValidationCheck":
        return cls(
            check_id=value["check_id"],
            status=value["status"],
            checked=value.get("checked", 0),
            passed=value.get("passed", 0),
            withheld=value.get("withheld", 0),
            failed=value.get("failed", 0),
            unavailable=value.get("unavailable", 0),
        )


@dataclass(frozen=True)
class TargetIdentity:
    model_id: str
    revision: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.model_id, str)
            or self.model_id.count("/") != 1
            or any(part.strip() != part or not part for part in self.model_id.split("/"))
        ):
            raise ValueError("model_id must be a non-empty namespace/name")
        if not isinstance(self.revision, str) or not _COMMIT_RE.fullmatch(self.revision):
            raise ValueError("revision must be a resolved 40-character lowercase commit")

    def to_dict(self) -> dict[str, str]:
        return {"model_id": self.model_id, "revision": self.revision}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TargetIdentity":
        return cls(model_id=value["model_id"], revision=value["revision"])


@dataclass(frozen=True)
class SourceDocument:
    """One in-memory source used to build bindings; source content is not exported."""

    source_id: str
    source_uri: str
    role: SourceRole
    source_revision: str
    target: TargetIdentity | None = None
    text: str | None = None
    data: JsonValue | None = None
    synthetic: bool = False
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not _ID_RE.fullmatch(self.source_id):
            raise ValueError("source_id must be a stable lowercase identifier")
        if not isinstance(self.source_uri, str) or not _PUBLIC_SOURCE_URI_RE.fullmatch(
            self.source_uri
        ):
            raise ValueError("source_uri must be a portable public source URI")
        object.__setattr__(self, "role", _enum(SourceRole, self.role, name="source role"))
        if not isinstance(self.source_revision, str) or not self.source_revision.strip():
            raise ValueError("source_revision must be non-empty")
        if (self.text is None) == (self.data is None):
            raise ValueError("a source must contain exactly one of text or data")
        if self.text is not None and (not isinstance(self.text, str) or not self.text):
            raise ValueError("source text must be non-empty")
        if self.data is not None:
            _require_json(self.data, name="source data")
            object.__setattr__(self, "data", deepcopy(self.data))
        if not isinstance(self.synthetic, bool):
            raise ValueError("synthetic must be boolean")
        if self.content_sha256 is not None and (
            not isinstance(self.content_sha256, str)
            or not _DIGEST_RE.fullmatch(self.content_sha256)
        ):
            raise ValueError("source content_sha256 must be a lowercase SHA-256 digest")

    @property
    def sha256(self) -> str:
        if self.content_sha256 is not None:
            return self.content_sha256
        if self.text is not None:
            payload = self.text.encode("utf-8")
        else:
            payload = json.dumps(
                self.data,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class Evidence:
    kind: EvidenceKind
    source_id: str
    source_uri: str
    source_role: SourceRole
    source_revision: str
    source_sha256: str
    source_target: TargetIdentity | None
    synthetic: bool
    verified: bool
    quote: str | None = None
    char_start: int | None = None
    char_end: int | None = None
    pointer: str | None = None
    fragment: JsonValue | None = None
    section_path: tuple[str, ...] = ()
    table_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _enum(EvidenceKind, self.kind, name="evidence kind"))
        object.__setattr__(
            self, "source_role", _enum(SourceRole, self.source_role, name="source role")
        )
        if not isinstance(self.source_id, str) or not _ID_RE.fullmatch(self.source_id):
            raise ValueError("evidence source_id is invalid")
        if not isinstance(self.source_uri, str) or not _PUBLIC_SOURCE_URI_RE.fullmatch(
            self.source_uri
        ):
            raise ValueError("evidence source_uri is not a portable public URI")
        if not isinstance(self.source_revision, str) or not self.source_revision.strip():
            raise ValueError("evidence source_revision must be non-empty")
        if not isinstance(self.source_sha256, str) or not _DIGEST_RE.fullmatch(self.source_sha256):
            raise ValueError("evidence source_sha256 must be a lowercase SHA-256 digest")
        if not isinstance(self.synthetic, bool) or not isinstance(self.verified, bool):
            raise ValueError("evidence flags must be boolean")
        section_path = tuple(self.section_path)
        if any(
            not isinstance(item, str)
            or not item.strip()
            or item != item.strip()
            or len(item) > 256
            or any(ord(char) < 32 for char in item)
            for item in section_path
        ):
            raise ValueError("evidence section_path contains an invalid heading")
        object.__setattr__(self, "section_path", section_path)
        if self.table_id is not None and (
            not isinstance(self.table_id, str)
            or not _TABLE_ID_RE.fullmatch(self.table_id)
        ):
            raise ValueError("evidence table_id is invalid")

        if self.kind is EvidenceKind.QUOTE:
            if not isinstance(self.quote, str) or not self.quote:
                raise ValueError("quote evidence must retain the proposed normalized quote")
            if self.pointer is not None or self.fragment is not None:
                raise ValueError("quote evidence cannot contain a structured pointer")
            offsets = (self.char_start, self.char_end)
            if self.verified:
                if not all(isinstance(item, int) for item in offsets):
                    raise ValueError("verified quote evidence requires offsets")
                if self.char_start < 0 or self.char_end <= self.char_start:
                    raise ValueError("quote offsets are invalid")
            elif offsets != (None, None):
                raise ValueError("unverified quote evidence cannot claim offsets")
        else:
            if not self.verified:
                raise ValueError("structured evidence must be verified before binding")
            if not isinstance(self.pointer, str) or not self.pointer.startswith("/"):
                raise ValueError("structured evidence requires a JSON Pointer")
            if self.quote is not None or self.char_start is not None or self.char_end is not None:
                raise ValueError("structured evidence cannot contain quote coordinates")
            _require_json(self.fragment, name="structured evidence fragment")
            object.__setattr__(self, "fragment", deepcopy(self.fragment))

    def to_dict(self) -> dict[str, JsonValue]:
        value: dict[str, JsonValue] = {
            "kind": self.kind.value,
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "source_role": self.source_role.value,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "source_target": self.source_target.to_dict() if self.source_target else None,
            "synthetic": self.synthetic,
            "verified": self.verified,
            "section_path": list(self.section_path),
            "table_id": self.table_id,
        }
        if self.kind is EvidenceKind.QUOTE:
            value.update(
                {
                    "quote": self.quote,
                    "char_start": self.char_start,
                    "char_end": self.char_end,
                }
            )
        else:
            value.update({"pointer": self.pointer, "fragment": deepcopy(self.fragment)})
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Evidence":
        source_target = value.get("source_target")
        return cls(
            kind=value["kind"],
            source_id=value["source_id"],
            source_uri=value["source_uri"],
            source_role=value["source_role"],
            source_revision=value["source_revision"],
            source_sha256=value["source_sha256"],
            source_target=TargetIdentity.from_dict(source_target) if source_target else None,
            synthetic=value["synthetic"],
            verified=value["verified"],
            quote=value.get("quote"),
            char_start=value.get("char_start"),
            char_end=value.get("char_end"),
            pointer=value.get("pointer"),
            fragment=value.get("fragment"),
            section_path=tuple(value.get("section_path", ())),
            table_id=value.get("table_id"),
        )


@dataclass(frozen=True)
class Binding:
    binding_id: str
    field_path: str
    value: JsonValue
    claim_entity: str
    relation: RelationToTarget
    origin: BindingOrigin
    evidence: tuple[Evidence, ...]
    disposition: Disposition
    reason: str
    benchmark_scope: dict[str, JsonValue] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence", tuple(self.evidence))
        if not isinstance(self.binding_id, str) or not self.binding_id.startswith("binding-"):
            raise ValueError("binding_id must be a deterministic binding-* identifier")
        validate_field_value(self.field_path, self.value)
        object.__setattr__(self, "value", deepcopy(self.value))
        if not isinstance(self.claim_entity, str) or not self.claim_entity.strip():
            raise ValueError("claim_entity must be non-empty")
        object.__setattr__(
            self, "relation", _enum(RelationToTarget, self.relation, name="relation")
        )
        object.__setattr__(self, "origin", _enum(BindingOrigin, self.origin, name="origin"))
        object.__setattr__(
            self, "disposition", _enum(Disposition, self.disposition, name="disposition")
        )
        if not self.evidence or not all(isinstance(item, Evidence) for item in self.evidence):
            raise ValueError("a binding requires at least one typed evidence item")
        if self.origin is BindingOrigin.QUOTED:
            if any(item.kind is not EvidenceKind.QUOTE for item in self.evidence):
                raise ValueError("quoted bindings require only quote evidence")
        else:
            if any(item.kind is not EvidenceKind.STRUCTURED for item in self.evidence):
                raise ValueError("structured bindings require only structured evidence")
            if any(not _json_equal(item.fragment, self.value) for item in self.evidence):
                raise ValueError("structured binding value must equal every evidence fragment")
        if not isinstance(self.reason, str) or not _REASON_RE.fullmatch(self.reason):
            raise ValueError("binding reason must be a stable lowercase reason code")
        if self.benchmark_scope is not None:
            _require_json(self.benchmark_scope, name="benchmark scope")
            object.__setattr__(self, "benchmark_scope", deepcopy(self.benchmark_scope))
        if canonical_field_path(self.field_path) == "evaluation.benchmark_scores":
            if not isinstance(self.value, dict) or not isinstance(self.benchmark_scope, dict):
                raise ValueError("benchmark score bindings require a typed benchmark scope")
            for key in ("benchmark", "metric", "setting"):
                if key not in self.value or key not in self.benchmark_scope:
                    raise ValueError(f"benchmark row and scope require key: {key}")
                if self.value.get(key) != self.benchmark_scope.get(key):
                    raise ValueError(f"benchmark scope does not match row key: {key}")

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "binding_id": self.binding_id,
            "field_path": self.field_path,
            "value": deepcopy(self.value),
            "claim_entity": self.claim_entity,
            "relation": self.relation.value,
            "origin": self.origin.value,
            "evidence": [item.to_dict() for item in self.evidence],
            "disposition": self.disposition.value,
            "reason": self.reason,
            "benchmark_scope": deepcopy(self.benchmark_scope),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Binding":
        return cls(
            binding_id=value["binding_id"],
            field_path=value["field_path"],
            value=value["value"],
            claim_entity=value["claim_entity"],
            relation=value["relation"],
            origin=value["origin"],
            evidence=tuple(Evidence.from_dict(item) for item in value["evidence"]),
            disposition=value["disposition"],
            reason=value["reason"],
            benchmark_scope=value.get("benchmark_scope"),
        )


@dataclass(frozen=True)
class DerivationClaimInput:
    """One accepted claim-gate input to a deterministic public derivation."""

    candidate_id: str
    candidate_sha256: str
    gate_record_sha256: str
    source_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CLAIM_ID_RE.fullmatch(
            self.candidate_id
        ):
            raise ValueError("derivation input candidate_id is invalid")
        for name in ("candidate_sha256", "gate_record_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
                raise ValueError(f"derivation input {name} is invalid")
        refs = tuple(self.source_refs)
        if refs != tuple(sorted(set(refs))) or not refs or any(
            not isinstance(item, str) or not _ID_RE.fullmatch(item) for item in refs
        ):
            raise ValueError("derivation input source_refs are invalid")
        object.__setattr__(self, "source_refs", refs)

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_sha256": self.candidate_sha256,
            "gate_record_sha256": self.gate_record_sha256,
            "source_refs": list(self.source_refs),
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DerivationClaimInput":
        if not isinstance(value, dict) or set(value) != {
            "candidate_id",
            "candidate_sha256",
            "gate_record_sha256",
            "source_refs",
        }:
            raise ValueError("derivation claim input has an invalid closed shape")
        if not isinstance(value["source_refs"], list):
            raise ValueError("derivation claim source_refs must be an array")
        return cls(
            candidate_id=value["candidate_id"],
            candidate_sha256=value["candidate_sha256"],
            gate_record_sha256=value["gate_record_sha256"],
            source_refs=tuple(value["source_refs"]),
        )


@dataclass(frozen=True)
class TaxonomyRiskDerivation:
    """Closed deterministic projection of one accepted taxonomy risk mapping.

    This is deliberately not a quote or structured evidence binding.  The
    value originates in a pinned taxonomy mapping and independent
    applicability decision; accepted exact-target use-context claims are its
    inputs, not direct evidence for the taxonomy prose.
    """

    target: TargetIdentity
    field_path: str
    value: dict[str, JsonValue]
    risk_report_sha256: str
    risk_catalog_sha256: str
    risk_candidate_id: str
    risk_candidate_sha256: str
    applicability_decision_sha256: str
    context_sha256s: tuple[str, ...]
    input_claims: tuple[DerivationClaimInput, ...]
    supporting_source_refs: tuple[str, ...]
    derivation_version: str = TAXONOMY_RISK_DERIVATION_VERSION
    derivation_id: str = dataclass_field(init=False)
    content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.derivation_version != TAXONOMY_RISK_DERIVATION_VERSION:
            raise ValueError("taxonomy risk derivation version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise ValueError("taxonomy risk derivation target is invalid")
        validate_field_path(self.field_path)
        base, indexes = parse_field_path(self.field_path)
        if base != "use_and_risk.identified_risks" or len(indexes) != 1:
            raise ValueError("taxonomy risk derivation requires one identified-risk index")
        validate_field_value(self.field_path, self.value)
        value = deepcopy(self.value)
        if value.get("identification_origin") != "taxonomy_identified":
            raise ValueError("taxonomy derivation output must be taxonomy_identified")
        if value.get("review_status") != "generated_unreviewed":
            raise ValueError("taxonomy derivation output cannot claim review or release")
        taxonomy = value.get("taxonomy")
        provenance = value.get("mapping_provenance")
        if not isinstance(taxonomy, dict) or not isinstance(provenance, dict):
            raise ValueError("taxonomy derivation output lacks taxonomy provenance")
        if (
            provenance.get("method") != "ai_atlas_nexus"
            or provenance.get("tool_version") != "1.2.4"
            or provenance.get("inference_model")
            != "deepseek/deepseek-v4-flash-0731"
            or not isinstance(provenance.get("inference_config_sha256"), str)
            or not _DIGEST_RE.fullmatch(provenance["inference_config_sha256"])
        ):
            raise ValueError("taxonomy derivation output is not from the pinned mapper")
        grounds = value.get("grounds")
        if not isinstance(grounds, list) or not grounds:
            raise ValueError("taxonomy derivation output requires specific grounds")
        kinds = {
            item.get("kind") for item in grounds if isinstance(item, dict)
        }
        if not {"card_field", "use_context"}.issubset(kinds):
            raise ValueError("taxonomy derivation requires use-context and field grounds")
        object.__setattr__(self, "value", value)
        for name in (
            "risk_report_sha256",
            "risk_catalog_sha256",
            "risk_candidate_sha256",
            "applicability_decision_sha256",
        ):
            digest = getattr(self, name)
            if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
                raise ValueError(f"taxonomy risk derivation {name} is invalid")
        if not isinstance(self.risk_candidate_id, str) or not _RISK_CANDIDATE_ID_RE.fullmatch(
            self.risk_candidate_id
        ):
            raise ValueError("taxonomy risk derivation candidate id is invalid")
        contexts = tuple(self.context_sha256s)
        if contexts != tuple(sorted(set(contexts))) or not contexts or any(
            not isinstance(item, str) or not _DIGEST_RE.fullmatch(item)
            for item in contexts
        ):
            raise ValueError("taxonomy risk derivation context digests are invalid")
        object.__setattr__(self, "context_sha256s", contexts)
        claims = tuple(self.input_claims)
        if not claims or not all(isinstance(item, DerivationClaimInput) for item in claims):
            raise ValueError("taxonomy risk derivation requires typed input claims")
        if claims != tuple(sorted(claims, key=lambda item: item.candidate_id)) or len(
            {item.candidate_id for item in claims}
        ) != len(claims):
            raise ValueError("taxonomy risk derivation input claims are not canonical")
        object.__setattr__(self, "input_claims", claims)
        refs = tuple(self.supporting_source_refs)
        expected_refs = tuple(
            sorted({ref for item in claims for ref in item.source_refs})
        )
        if refs != expected_refs or not refs:
            raise ValueError("taxonomy risk derivation source refs differ from claim inputs")
        if tuple(sorted(value.get("source_refs", ()))) != refs:
            raise ValueError("taxonomy risk output source refs differ from derivation inputs")
        object.__setattr__(self, "supporting_source_refs", refs)
        digest = hashlib.sha256(
            json.dumps(
                self._content_payload(),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "content_sha256", digest)
        object.__setattr__(self, "derivation_id", "derivation-" + digest[:24])

    def _content_payload(self) -> dict[str, JsonValue]:
        return {
            "derivation_version": self.derivation_version,
            "target": self.target.to_dict(),
            "field_path": self.field_path,
            "value": deepcopy(self.value),
            "risk_report_sha256": self.risk_report_sha256,
            "risk_catalog_sha256": self.risk_catalog_sha256,
            "risk_candidate_id": self.risk_candidate_id,
            "risk_candidate_sha256": self.risk_candidate_sha256,
            "applicability_decision_sha256": self.applicability_decision_sha256,
            "context_sha256s": list(self.context_sha256s),
            "input_claims": [item.to_dict() for item in self.input_claims],
            "supporting_source_refs": list(self.supporting_source_refs),
        }

    def validate_integrity(self) -> None:
        digest = hashlib.sha256(
            json.dumps(
                self._content_payload(),
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        if digest != self.content_sha256 or self.derivation_id != "derivation-" + digest[:24]:
            raise ValueError("taxonomy risk derivation integrity failed")

    def public_reference(self) -> dict[str, JsonValue]:
        """Return source-clean provenance for the public computed section."""

        return {
            "derivation_id": self.derivation_id,
            "derivation_version": self.derivation_version,
            "output_sha256": hashlib.sha256(
                json.dumps(
                    self.value,
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest(),
            "risk_report_sha256": self.risk_report_sha256,
            "risk_catalog_sha256": self.risk_catalog_sha256,
            "risk_candidate_sha256": self.risk_candidate_sha256,
            "applicability_decision_sha256": self.applicability_decision_sha256,
            "context_sha256s": list(self.context_sha256s),
            "input_claims": [item.to_dict() for item in self.input_claims],
            "supporting_source_refs": list(self.supporting_source_refs),
        }

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            **self._content_payload(),
            "derivation_id": self.derivation_id,
            "content_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TaxonomyRiskDerivation":
        expected = {
            "derivation_version",
            "derivation_id",
            "target",
            "field_path",
            "value",
            "risk_report_sha256",
            "risk_catalog_sha256",
            "risk_candidate_id",
            "risk_candidate_sha256",
            "applicability_decision_sha256",
            "context_sha256s",
            "input_claims",
            "supporting_source_refs",
            "content_sha256",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("taxonomy risk derivation has an invalid closed shape")
        if any(
            not isinstance(value[name], list)
            for name in ("context_sha256s", "input_claims", "supporting_source_refs")
        ):
            raise ValueError("taxonomy risk derivation arrays are malformed")
        result = cls(
            derivation_version=value["derivation_version"],
            target=TargetIdentity.from_dict(value["target"]),
            field_path=value["field_path"],
            value=value["value"],
            risk_report_sha256=value["risk_report_sha256"],
            risk_catalog_sha256=value["risk_catalog_sha256"],
            risk_candidate_id=value["risk_candidate_id"],
            risk_candidate_sha256=value["risk_candidate_sha256"],
            applicability_decision_sha256=value["applicability_decision_sha256"],
            context_sha256s=tuple(value["context_sha256s"]),
            input_claims=tuple(
                DerivationClaimInput.from_dict(item) for item in value["input_claims"]
            ),
            supporting_source_refs=tuple(value["supporting_source_refs"]),
        )
        if (
            value["derivation_id"] != result.derivation_id
            or value["content_sha256"] != result.content_sha256
        ):
            raise ValueError("taxonomy risk derivation digest is inconsistent")
        return result


@dataclass(frozen=True)
class ReviewEvent:
    sequence: int
    binding_id: str
    action: ReviewAction
    reason: str
    field_path: str | None = None
    relation: RelationToTarget | None = None
    corrected_value: JsonValue | None = None
    replacement_candidate_id: str | None = None
    replacement_candidate_sha256: str | None = None
    gate_record_sha256: str | None = None
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.sequence, int) or self.sequence < 1:
            raise ValueError("review sequence must be positive")
        if not isinstance(self.binding_id, str) or not self.binding_id.startswith("binding-"):
            raise ValueError("review binding_id is invalid")
        object.__setattr__(self, "action", _enum(ReviewAction, self.action, name="review action"))
        if not isinstance(self.reason, str) or not _REASON_RE.fullmatch(self.reason):
            raise ValueError("review reason must be a stable lowercase reason code")
        if self.action is ReviewAction.REASSIGN:
            if (
                self.field_path is None
                or self.relation is None
                or self.corrected_value is None
                or self.replacement_candidate_id is None
                or self.replacement_candidate_sha256 is None
                or self.gate_record_sha256 is None
            ):
                raise ValueError(
                    "reassign requires a corrected value and a complete claim-gate reference"
                )
            validate_field_path(self.field_path)
            object.__setattr__(
                self,
                "relation",
                _enum(RelationToTarget, self.relation, name="review relation"),
            )
            validate_field_value(self.field_path, self.corrected_value)
            object.__setattr__(self, "corrected_value", deepcopy(self.corrected_value))
            if not _CLAIM_ID_RE.fullmatch(self.replacement_candidate_id):
                raise ValueError("review replacement candidate_id is invalid")
            for name in ("replacement_candidate_sha256", "gate_record_sha256"):
                value = getattr(self, name)
                if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
                    raise ValueError(f"review {name} is invalid")
        elif any(
            item is not None
            for item in (
                self.field_path,
                self.relation,
                self.corrected_value,
                self.replacement_candidate_id,
                self.replacement_candidate_sha256,
                self.gate_record_sha256,
            )
        ):
            raise ValueError("only reassign may carry corrected claim-gate material")
        object.__setattr__(self, "_content_sha256", self._computed_sha256())

    @property
    def event_id(self) -> str:
        return f"review-{self.sequence:04d}"

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def _computed_sha256(self) -> str:
        payload = {
            "sequence": self.sequence,
            "binding_id": self.binding_id,
            "action": self.action.value,
            "reason": self.reason,
            "field_path": self.field_path,
            "relation": self.relation.value if self.relation else None,
            "corrected_value": self.corrected_value,
        }
        # Preserve the digest of legacy accept/withhold events.  The additional
        # lineage material is meaningful only for a reassign event; old reassign
        # events intentionally fail closed because they lack a replayed gate.
        if self.action is ReviewAction.REASSIGN:
            payload.update(
                {
                    "replacement_candidate_id": self.replacement_candidate_id,
                    "replacement_candidate_sha256": self.replacement_candidate_sha256,
                    "gate_record_sha256": self.gate_record_sha256,
                }
            )
        canonical = json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def validate_integrity(self) -> None:
        if self._content_sha256 != self._computed_sha256():
            raise ValueError(f"review event integrity check failed: {self.event_id}")

    def to_dict(self) -> dict[str, JsonValue]:
        value: dict[str, JsonValue] = {
            "event_id": self.event_id,
            "sequence": self.sequence,
            "binding_id": self.binding_id,
            "action": self.action.value,
            "reason": self.reason,
            "event_sha256": self.content_sha256,
        }
        if self.action is ReviewAction.REASSIGN:
            value.update(
                {
                    "field_path": self.field_path,
                    "relation": self.relation.value if self.relation else None,
                    "corrected_value": deepcopy(self.corrected_value),
                    "replacement_candidate_id": self.replacement_candidate_id,
                    "replacement_candidate_sha256": self.replacement_candidate_sha256,
                    "gate_record_sha256": self.gate_record_sha256,
                }
            )
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ReviewEvent":
        event = cls(
            sequence=value["sequence"],
            binding_id=value["binding_id"],
            action=value["action"],
            reason=value["reason"],
            field_path=value.get("field_path"),
            relation=value.get("relation"),
            corrected_value=value.get("corrected_value"),
            replacement_candidate_id=value.get("replacement_candidate_id"),
            replacement_candidate_sha256=value.get("replacement_candidate_sha256"),
            gate_record_sha256=value.get("gate_record_sha256"),
        )
        if value.get("event_id") != event.event_id:
            raise ValueError("serialized review event_id is inconsistent")
        if value.get("event_sha256") != event.content_sha256:
            raise ValueError("serialized review event digest is inconsistent")
        return event
