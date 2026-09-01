"""Typed records for sources, evidence, bindings, and review events."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Union

from .schema import canonical_field_path, validate_field_path, validate_field_value


JsonValue = Union[None, bool, int, float, str, list["JsonValue"], dict[str, "JsonValue"]]

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._:-]{1,127}$")


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
    role: SourceRole
    source_revision: str
    target: TargetIdentity | None = None
    text: str | None = None
    data: JsonValue | None = None
    synthetic: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not _ID_RE.fullmatch(self.source_id):
            raise ValueError("source_id must be a stable lowercase identifier")
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

    @property
    def sha256(self) -> str:
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _enum(EvidenceKind, self.kind, name="evidence kind"))
        object.__setattr__(
            self, "source_role", _enum(SourceRole, self.source_role, name="source role")
        )
        if not isinstance(self.source_id, str) or not _ID_RE.fullmatch(self.source_id):
            raise ValueError("evidence source_id is invalid")
        if not isinstance(self.source_revision, str) or not self.source_revision.strip():
            raise ValueError("evidence source_revision must be non-empty")
        if not isinstance(self.source_sha256, str) or not _DIGEST_RE.fullmatch(self.source_sha256):
            raise ValueError("evidence source_sha256 must be a lowercase SHA-256 digest")
        if not isinstance(self.synthetic, bool) or not isinstance(self.verified, bool):
            raise ValueError("evidence flags must be boolean")

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
            "source_role": self.source_role.value,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "source_target": self.source_target.to_dict() if self.source_target else None,
            "synthetic": self.synthetic,
            "verified": self.verified,
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
class ReviewEvent:
    sequence: int
    binding_id: str
    action: ReviewAction
    reason: str
    field_path: str | None = None
    relation: RelationToTarget | None = None
    corrected_value: JsonValue | None = None
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
            if self.field_path is None or self.relation is None or self.corrected_value is None:
                raise ValueError("reassign requires field_path, relation, and corrected_value")
            validate_field_path(self.field_path)
            object.__setattr__(
                self,
                "relation",
                _enum(RelationToTarget, self.relation, name="review relation"),
            )
            validate_field_value(self.field_path, self.corrected_value)
            object.__setattr__(self, "corrected_value", deepcopy(self.corrected_value))
        elif any(
            item is not None for item in (self.field_path, self.relation, self.corrected_value)
        ):
            raise ValueError("only reassign may change field, relation, or value")
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
        )
        if value.get("event_id") != event.event_id:
            raise ValueError("serialized review event_id is inconsistent")
        if value.get("event_sha256") != event.content_sha256:
            raise ValueError("serialized review event digest is inconsistent")
        return event
