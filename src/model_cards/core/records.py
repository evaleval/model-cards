"""Typed records for evidence binding and review.

These models store source inputs and explicit decisions only.  They have no
field for hidden reasoning or chain-of-thought; deterministic derivations are
represented by named rules and structured inputs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re
from typing import Any, Literal
from uuid import uuid4

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from .derivations import derive_architecture_type, derive_modalities
from .frontmatter import parse_frontmatter
from .schema import (
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    SCHEMA_VERSION,
    blank_card,
    canonical_field_path,
    parse_field_path,
    set_field_value,
    validate_complete_card,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REASON_CODE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_MODEL_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)?$"
)
_SOURCE_URI_SCHEMES = frozenset({"https", "http", "hf", "file", "arxiv", "doi"})
_WHITESPACE_RE = re.compile(r"\s+")
_TYPOGRAPHIC_TRANSLATION = str.maketrans(
    {
        "‘": "'", "’": "'", "‚": "'", "‛": "'", "´": "'", "ʼ": "'",
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "―": "-", "−": "-",
    }
)


class RelationToTarget(str, Enum):
    EXACT_TARGET = "exact_target"
    BASE = "base"
    DERIVATIVE = "derivative"
    SIBLING_OR_COMPARISON = "sibling_or_comparison"
    # A statement made about the family this checkpoint belongs to. It is not the
    # checkpoint's own claim and it is not another model's claim, so it needs its own
    # value: collapsing it into base made every family sentence about a derivative look
    # like an inherited base fact, and collapsing it into unknown lost it entirely.
    FAMILY = "family"
    UNKNOWN = "unknown"


LINEAGE_FIELDS = ("lineage.base_models", "lineage.derivatives")


def lineage_expectations(canonical: str) -> tuple["RelationToTarget", str]:
    """(relation to the target, contract relation word) a lineage row must carry.

    One definition, because two copies of this rule drifted apart: this module moved to
    the published modelReference vocabulary and review.py kept the old words, so every
    card with a base_model tag saved cleanly and then failed to render.
    """
    if canonical == "lineage.base_models":
        return RelationToTarget.BASE, "base_model"
    return RelationToTarget.DERIVATIVE, "derivative_model"


class AssignmentOrigin(str, Enum):
    STRUCTURED_EXPLICIT = "structured_explicit"
    LLM_INFERRED = "llm_inferred"
    HUMAN_CORRECTED = "human_corrected"
    UNRESOLVED = "unresolved"


class VerifierAction(str, Enum):
    ACCEPT = "accept"
    REASSIGN = "reassign"
    WITHHOLD = "withhold"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


def _strip_nonempty(value: str, *, name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{name} must not be empty")
    if any(ord(character) < 32 for character in value):
        raise ValueError(f"{name} must not contain control characters")
    return value


def _canonical_digest(prefix: str, value: Any, *, length: int = 24) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:length]}"


def _validate_repo_id(value: str, *, name: str) -> str:
    value = _strip_nonempty(value, name=name)
    if len(value) > 96 or not _MODEL_ID_RE.fullmatch(value):
        raise ValueError(f"{name} must be a valid Hugging Face repository id")
    if "--" in value or ".." in value or value.endswith(".git"):
        raise ValueError(f"{name} must be a valid Hugging Face repository id")
    return value


def _validate_source_uri(value: str, *, name: str) -> str:
    value = _strip_nonempty(value, name=name)
    if ":" not in value:
        raise ValueError(f"{name} must include a URI scheme")
    scheme = value.split(":", 1)[0].lower()
    if scheme not in _SOURCE_URI_SCHEMES:
        raise ValueError(f"unsupported {name} scheme: {scheme}")
    return value


def _normalize_evidence_text(value: str) -> str:
    """Mirror the pinned composer's documented evidence coordinate space."""

    return _WHITESPACE_RE.sub(" ", value.translate(_TYPOGRAPHIC_TRANSLATION)).strip()


def _resolve_json_pointer(document: Any, pointer: str) -> Any:
    if pointer == "":
        return document
    if not pointer.startswith("/"):
        raise ValueError("structured_pointer must be an absolute JSON Pointer")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if token not in current:
                raise ValueError(f"structured_pointer token is absent: {token}")
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or (len(token) > 1 and token.startswith("0")):
                raise ValueError(f"structured_pointer list index is invalid: {token}")
            index = int(token)
            if index >= len(current):
                raise ValueError(f"structured_pointer list index is out of range: {token}")
            current = current[index]
        else:
            raise ValueError("structured_pointer traverses through a scalar value")
    return current


class TargetIdentity(_FrozenModel):
    """An exact repository target, retaining the user's requested revision."""

    model_id: str
    requested_revision: str
    resolved_revision: str

    @field_validator("model_id")
    @classmethod
    def _validate_model_id(cls, value: str) -> str:
        return _validate_repo_id(value, name="model_id")

    @field_validator("requested_revision")
    @classmethod
    def _validate_requested_revision(cls, value: str) -> str:
        value = _strip_nonempty(value, name="requested_revision")
        if "@" in value:
            raise ValueError("requested_revision must not contain '@'")
        return value

    @field_validator("resolved_revision", mode="before")
    @classmethod
    def _validate_resolved_revision(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("resolved_revision must be a string")
        value = value.strip().lower()
        if not COMMIT_SHA_RE.fullmatch(value):
            raise ValueError("resolved_revision must be an exact 40-character commit SHA")
        return value

    @property
    def requested_target(self) -> str:
        return f"{self.model_id}@{self.requested_revision}"

    @property
    def canonical_target(self) -> str:
        return f"{self.model_id}@{self.resolved_revision}"

    def __str__(self) -> str:
        return self.canonical_target

    @classmethod
    def from_spec(
        cls,
        target: str,
        *,
        resolved_revision: str | None = None,
    ) -> "TargetIdentity":
        """Parse ``model_id@requested`` and attach its resolved commit."""

        if "@" not in target:
            raise ValueError("target must have the form model_id@revision")
        model_id, requested_revision = target.rsplit("@", 1)
        return cls(
            model_id=model_id,
            requested_revision=requested_revision,
            resolved_revision=resolved_revision or requested_revision,
        )

    parse = from_spec


class ClaimEntity(_FrozenModel):
    """The entity a claim describes, including unresolved comparison labels."""

    model_id: str | None = None
    revision: str | None = None
    label: str | None = None

    @field_validator("model_id")
    @classmethod
    def _validate_optional_model_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_repo_id(value, name="claim_entity.model_id")

    @field_validator("revision", "label")
    @classmethod
    def _validate_optional_text(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return _strip_nonempty(value, name=f"claim_entity.{info.field_name}")

    @model_validator(mode="after")
    def _require_identity(self) -> "ClaimEntity":
        if self.model_id is None and self.label is None:
            raise ValueError("claim entity requires model_id or an exact source label")
        if self.revision is not None and self.model_id is None:
            raise ValueError("claim entity revision requires model_id")
        return self

    @property
    def display_name(self) -> str:
        if self.model_id is not None:
            return f"{self.model_id}@{self.revision}" if self.revision else self.model_id
        assert self.label is not None
        return self.label


class BenchmarkScope(_FrozenModel):
    """The benchmark variant and reported evaluation setting for a value."""

    benchmark_id: str = Field(
        validation_alias=AliasChoices(
            "benchmark_id", "benchmark_identity", "identity", "benchmark"
        )
    )
    version: str | None = None
    subset: str | None = None
    split: str | None = None
    setting: str | dict[str, JsonValue] | None = Field(
        default=None,
        validation_alias=AliasChoices("setting", "evaluation_setting"),
    )

    @field_validator("benchmark_id")
    @classmethod
    def _validate_benchmark_id(cls, value: str) -> str:
        return _strip_nonempty(value, name="benchmark_id")

    @field_validator("version", "subset", "split")
    @classmethod
    def _validate_scope_text(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return _strip_nonempty(value, name=f"benchmark_scope.{info.field_name}")

    @field_validator("setting")
    @classmethod
    def _validate_setting(
        cls, value: str | dict[str, JsonValue] | None
    ) -> str | dict[str, JsonValue] | None:
        if isinstance(value, str):
            return _strip_nonempty(value, name="benchmark_scope.setting")
        if isinstance(value, dict) and not value:
            raise ValueError("benchmark_scope.setting mapping must not be empty")
        return value

    @property
    def identity(self) -> str:
        return self.benchmark_id

    @property
    def evaluation_setting(self) -> str | dict[str, JsonValue] | None:
        return self.setting


class EvidenceSpan(_FrozenModel):
    """Exact textual or structured evidence with document/table anchors.

    Text and offsets use the pinned composer's deterministic whitespace-
    normalized coordinate space.  File-backed source hashes cover the original
    UTF-8 bytes; artifact-internal target manifests and derivations hash their
    canonical structured source. Consumers can reproduce text coordinates with
    the bridge revision stored in the artifact metadata.
    """

    source_uri: str
    source_revision: str
    source_sha256: str = Field(
        validation_alias=AliasChoices("source_sha256", "source_hash")
    )
    exact_text: str | None = Field(
        default=None,
        validation_alias=AliasChoices("exact_text", "exact_span", "quote"),
    )
    start_offset: int | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("start_offset", "start_char"),
    )
    end_offset: int | None = Field(
        default=None,
        ge=1,
        validation_alias=AliasChoices("end_offset", "end_char"),
    )
    section_path: tuple[str, ...] = ()
    table_caption: str | None = None
    table_header: tuple[str, ...] | None = None
    row_anchor: str | None = Field(
        default=None,
        validation_alias=AliasChoices("row_anchor", "table_row_anchor"),
    )
    context_before: str | None = None
    context_after: str | None = None
    surrounding_context: str | None = Field(
        default=None,
        validation_alias=AliasChoices("surrounding_context", "context"),
    )
    structured_pointer: str | None = None
    structured_fragment: JsonValue | None = None

    @field_validator("source_uri", "source_revision")
    @classmethod
    def _validate_source_text(cls, value: str, info: Any) -> str:
        if info.field_name == "source_uri":
            return _validate_source_uri(value, name="source_uri")
        return _strip_nonempty(value, name=info.field_name)

    @field_validator("source_sha256", mode="before")
    @classmethod
    def _validate_source_sha256(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("source_sha256 must be a string")
        value = value.strip().lower()
        if not SHA256_RE.fullmatch(value):
            raise ValueError("source_sha256 must contain 64 hexadecimal characters")
        return value

    @field_validator(
        "exact_text",
        "table_caption",
        "row_anchor",
        "structured_pointer",
    )
    @classmethod
    def _validate_optional_nonempty(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        return _strip_nonempty(value, name=info.field_name)

    @field_validator("section_path")
    @classmethod
    def _validate_section_path(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(_strip_nonempty(part, name="section_path item") for part in value)

    @field_validator("table_header")
    @classmethod
    def _validate_table_header(
        cls, value: tuple[str, ...] | None
    ) -> tuple[str, ...] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("table_header must not be empty")
        return tuple(_strip_nonempty(item, name="table_header item") for item in value)

    @field_validator("context_before", "context_after", "surrounding_context")
    @classmethod
    def _bound_context(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        if len(value) > 2_000:
            raise ValueError(f"{info.field_name} must be bounded to 2,000 characters")
        return value

    @model_validator(mode="after")
    def _validate_span(self) -> "EvidenceSpan":
        has_start = self.start_offset is not None
        has_end = self.end_offset is not None
        if has_start != has_end:
            raise ValueError("start_offset and end_offset must be supplied together")
        has_pointer = self.structured_pointer is not None
        has_fragment = self.structured_fragment is not None
        if has_pointer != has_fragment:
            raise ValueError(
                "structured evidence requires both structured_pointer and structured_fragment"
            )
        if self.exact_text is None and not has_pointer:
            raise ValueError(
                "evidence requires exact_text or a structured pointer/fragment pair"
            )
        if self.exact_text is not None:
            if not has_start:
                raise ValueError("textual evidence requires exact start and end offsets")
            assert self.start_offset is not None and self.end_offset is not None
            if self.exact_text != _normalize_evidence_text(self.exact_text):
                raise ValueError("exact_text must use normalized evidence coordinates")
            if self.end_offset <= self.start_offset:
                raise ValueError("end_offset must be greater than start_offset")
            if self.end_offset - self.start_offset != len(self.exact_text):
                raise ValueError("offset range must have the same length as exact_text")
        elif has_start:
            raise ValueError("offsets cannot be supplied without exact_text")
        if self.row_anchor is not None and self.table_header is None:
            raise ValueError("row_anchor requires the table header it is anchored under")
        return self


class DerivationTrace(_FrozenModel):
    """A deterministic rule application, without hidden semantic reasoning."""

    rule: str
    inputs: dict[str, JsonValue]
    output: JsonValue | None = None

    @field_validator("rule")
    @classmethod
    def _validate_rule(cls, value: str) -> str:
        return _strip_nonempty(value, name="derivation rule")

    @field_validator("inputs")
    @classmethod
    def _validate_inputs(cls, value: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if not value:
            raise ValueError("derivation inputs must not be empty")
        return value


class SourceFile(_FrozenModel):
    """One byte-accounted UTF-8 file in a frozen source bundle."""

    name: str
    source_uri: str
    sha256: str
    size_bytes: int = Field(ge=0)
    media_type: str
    content: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        value = _strip_nonempty(value, name="source file name")
        if value.startswith("/") or ".." in value.split("/"):
            raise ValueError("source file name must be a safe relative path")
        return value

    @field_validator("source_uri", "media_type")
    @classmethod
    def _validate_file_text(cls, value: str, info: Any) -> str:
        if info.field_name == "source_uri":
            return _validate_source_uri(value, name="source_file.source_uri")
        return _strip_nonempty(value, name=f"source_file.{info.field_name}")

    @field_validator("sha256", mode="before")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("sha256 must be a string")
        value = value.strip().lower()
        if not SHA256_RE.fullmatch(value):
            raise ValueError("sha256 must contain 64 hexadecimal characters")
        return value

    @model_validator(mode="after")
    def _verify_content(self) -> "SourceFile":
        encoded = self.content.encode("utf-8")
        if len(encoded) != self.size_bytes:
            raise ValueError("size_bytes does not match the UTF-8 source content")
        if hashlib.sha256(encoded).hexdigest() != self.sha256:
            raise ValueError("sha256 does not match the UTF-8 source content")
        return self


class SourceBundle(_FrozenModel):
    """Frozen, hashed source inputs for one exact target snapshot."""

    target: TargetIdentity
    repo_type: Literal["model"] = "model"
    snapshot_path: str
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    files: tuple[SourceFile, ...] = Field(min_length=1)
    retrieved_at: datetime
    offline: bool

    @field_validator("snapshot_path")
    @classmethod
    def _validate_snapshot_path(cls, value: str) -> str:
        return _strip_nonempty(value, name="snapshot_path")

    @field_validator("retrieved_at")
    @classmethod
    def _require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieved_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _unique_files(self) -> "SourceBundle":
        names = [source_file.name for source_file in self.files]
        if len(names) != len(set(names)):
            raise ValueError("source bundle file names must be unique")
        source_uris = [source_file.source_uri for source_file in self.files]
        if len(source_uris) != len(set(source_uris)):
            raise ValueError("source bundle file URIs must be unique")
        for source_file in self.files:
            if source_file.name not in {"README.md", "config.json"}:
                continue
            expected_uris = {
                (
                    f"https://huggingface.co/{self.target.model_id}/blob/"
                    f"{self.target.resolved_revision}/{source_file.name}"
                ),
                (
                    f"hf://{self.target.model_id}@{self.target.resolved_revision}/"
                    f"{source_file.name}"
                ),
            }
            if source_file.source_uri not in expected_uris:
                raise ValueError(
                    "snapshot source URI does not match target model, commit, and file name"
                )

        expected_metadata = {
            "model_id": self.target.model_id,
            "requested_revision": self.target.requested_revision,
            "resolved_revision": self.target.resolved_revision,
            "repo_type": self.repo_type,
        }
        for key, expected in expected_metadata.items():
            if key in self.metadata and self.metadata[key] != expected:
                raise ValueError(f"source bundle metadata {key} does not match its target")
        if "available_files" in self.metadata:
            available = self.metadata["available_files"]
            if not isinstance(available, list) or available != names:
                raise ValueError("source bundle metadata available_files does not match files")
        return self

    def file(self, name: str) -> SourceFile:
        for source_file in self.files:
            if source_file.name == name:
                return source_file
        raise KeyError(name)


class BindingRecord(_FrozenModel):
    """An immutable proposal, its binding decision, and its exact support."""

    binding_id: str = ""
    field_path: str
    proposed_value: JsonValue
    target: TargetIdentity = Field(
        validation_alias=AliasChoices("target", "target_identity")
    )
    claim_entity: ClaimEntity
    relation_to_target: RelationToTarget = Field(
        validation_alias=AliasChoices("relation_to_target", "relation")
    )
    benchmark_scope: BenchmarkScope | None = None
    assignment_origin: AssignmentOrigin
    evidence: tuple[EvidenceSpan, ...] = Field(min_length=1)
    derivation_trace: DerivationTrace | None = None
    verifier_action: VerifierAction
    verifier_reason: str

    @field_validator("field_path")
    @classmethod
    def _validate_field_path(cls, value: str) -> str:
        parse_field_path(value)
        return value

    @field_validator("claim_entity", mode="before")
    @classmethod
    def _coerce_claim_entity(cls, value: Any) -> Any:
        if isinstance(value, str):
            return {"model_id": value}
        return value

    @field_validator("verifier_reason")
    @classmethod
    def _validate_reason(cls, value: str) -> str:
        value = _strip_nonempty(value, name="verifier_reason")
        if not REASON_CODE_RE.fullmatch(value):
            raise ValueError("verifier_reason must be a machine-readable reason code")
        return value

    @model_validator(mode="after")
    def _validate_binding(self) -> "BindingRecord":
        if (
            self.derivation_trace is not None
            and self.derivation_trace.output != self.proposed_value
        ):
            raise ValueError("derivation trace output must match proposed value")
        if self.relation_to_target is RelationToTarget.UNKNOWN:
            if self.verifier_action is not VerifierAction.WITHHOLD:
                raise ValueError("unknown target relation must be withheld")
        if self.assignment_origin is AssignmentOrigin.UNRESOLVED:
            if self.verifier_action is not VerifierAction.WITHHOLD:
                raise ValueError("unresolved assignment must be withheld")

        if self.relation_to_target is RelationToTarget.EXACT_TARGET:
            if self.claim_entity.model_id != self.target.model_id:
                raise ValueError("exact_target claim entity must match target model_id")
            claim_revision = self.claim_entity.revision
            if claim_revision is None:
                raise ValueError("exact_target claim entity must name the target commit")
            if claim_revision.lower() != self.target.resolved_revision:
                raise ValueError("exact_target claim revision does not match target commit")

        if self.relation_to_target in {
            RelationToTarget.BASE,
            RelationToTarget.DERIVATIVE,
        } and self.claim_entity.model_id == self.target.model_id:
            distinct_revision = (
                self.claim_entity.revision is not None
                and self.claim_entity.revision.lower() != self.target.resolved_revision
            )
            if not distinct_revision and self.verifier_action is not VerifierAction.WITHHOLD:
                raise ValueError(
                    "self-referential base/derivative relation requires a distinct checkpoint"
                )

        canonical = canonical_field_path(self.field_path)
        if self.verifier_action is not VerifierAction.WITHHOLD:
            if canonical == "identity.model_id" and self.proposed_value != self.target.model_id:
                raise ValueError("identity.model_id must equal the artifact target model_id")
            if (
                canonical == "identity.version"
                and self.proposed_value != self.target.resolved_revision
            ):
                raise ValueError("identity.version must equal the artifact target commit")
        if (
            canonical == "evaluation.benchmark_scores"
            and self.verifier_action is not VerifierAction.WITHHOLD
        ):
            if self.benchmark_scope is None:
                raise ValueError("accepted benchmark scores require benchmark_scope")
            if not any(
                span.row_anchor is not None or span.structured_pointer is not None
                for span in self.evidence
            ):
                raise ValueError("accepted benchmark scores require a row or structured anchor")
            if (
                self.relation_to_target is RelationToTarget.EXACT_TARGET
                and self.benchmark_scope.benchmark_id.startswith("unresolved_")
            ):
                raise ValueError("accepted exact-target benchmark score requires resolved scope")
            if isinstance(self.proposed_value, dict):
                scope_values = {
                    "benchmark_id": self.benchmark_scope.benchmark_id,
                    "version": self.benchmark_scope.version,
                    "subset": self.benchmark_scope.subset,
                    "split": self.benchmark_scope.split,
                    "setting": self.benchmark_scope.setting,
                }
                for key, expected in scope_values.items():
                    if key in self.proposed_value and self.proposed_value[key] != expected:
                        raise ValueError(
                            f"benchmark score {key} contradicts typed benchmark scope"
                        )

        if self.verifier_action is not VerifierAction.WITHHOLD and canonical in LINEAGE_FIELDS:
            expected_relation, expected_value_relation = lineage_expectations(canonical)
            if self.relation_to_target is not expected_relation:
                raise ValueError(f"{canonical} requires relation {expected_relation.value}")
            if (
                not isinstance(self.proposed_value, dict)
                or self.proposed_value.get("model_id") != self.claim_entity.model_id
                or self.proposed_value.get("relation") != expected_value_relation
            ):
                raise ValueError("lineage value must match claim entity and typed relation")

        digest_payload = self.model_dump(
            mode="json", exclude={"binding_id"}, exclude_none=False
        )
        expected_id = _canonical_digest("bnd", digest_payload)
        if self.binding_id and self.binding_id != expected_id:
            raise ValueError(
                f"binding_id is content-derived; expected {expected_id}, got {self.binding_id}"
            )
        object.__setattr__(self, "binding_id", expected_id)
        return self


class ReviewEvent(_FrozenModel):
    """One append-only verifier action against an immutable BindingRecord."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    binding_id: str = Field(validation_alias=AliasChoices("binding_id", "record_id"))
    action: VerifierAction
    reason_code: str
    actor: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    note: str | None = None
    field_path: str | None = None
    corrected_value: JsonValue | None = None
    corrected_value_set: bool = False
    claim_entity: ClaimEntity | None = None
    relation_to_target: RelationToTarget | None = None
    benchmark_scope: BenchmarkScope | None = None
    assignment_origin: AssignmentOrigin | None = None
    supersedes_event_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _mark_explicit_corrected_value(cls, value: Any) -> Any:
        # ``None`` can itself be a deliberate replacement.  The companion flag
        # makes that distinguishable from an omitted value and remains stable
        # through ordinary JSON serialization, where optional nulls are present.
        if isinstance(value, dict):
            value = dict(value)
            if "corrected_value" in value and "corrected_value_set" not in value:
                value["corrected_value_set"] = True
        return value

    @field_validator("binding_id", "actor", "event_id")
    @classmethod
    def _validate_event_text(cls, value: str, info: Any) -> str:
        return _strip_nonempty(value, name=info.field_name)

    @field_validator("reason_code")
    @classmethod
    def _validate_reason_code(cls, value: str) -> str:
        value = _strip_nonempty(value, name="reason_code")
        if not REASON_CODE_RE.fullmatch(value):
            raise ValueError("reason_code must be machine-readable")
        return value

    @field_validator("created_at")
    @classmethod
    def _validate_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return value

    @field_validator("field_path")
    @classmethod
    def _validate_optional_field_path(cls, value: str | None) -> str | None:
        if value is not None:
            parse_field_path(value)
        return value

    @model_validator(mode="after")
    def _validate_correction(self) -> "ReviewEvent":
        supplied = any(
            value is not None
            for value in (
                self.field_path,
                self.claim_entity,
                self.relation_to_target,
                self.benchmark_scope,
            )
        ) or self.corrected_value_set
        if self.action is VerifierAction.REASSIGN:
            if not supplied:
                raise ValueError("reassign event must record at least one corrected assignment")
            if self.assignment_origin not in (None, AssignmentOrigin.HUMAN_CORRECTED):
                raise ValueError("reassign event origin must be human_corrected")
            object.__setattr__(self, "assignment_origin", AssignmentOrigin.HUMAN_CORRECTED)
        else:
            if supplied:
                raise ValueError("only reassign events may carry corrected assignment fields")
            if self.corrected_value is not None:
                raise ValueError("corrected_value requires corrected_value_set")
            if self.assignment_origin is not None:
                raise ValueError("accept/withhold events do not change assignment origin")
        return self

    @property
    def record_id(self) -> str:
        return self.binding_id


class CardArtifact(_FrozenModel):
    """A complete card plus its immutable bindings and append-only review log."""

    artifact_id: str = ""
    schema_version: Literal["1"] = SCHEMA_VERSION
    target: TargetIdentity
    card: dict[str, dict[str, JsonValue]]
    bindings: tuple[BindingRecord, ...] = ()
    metadata: dict[str, JsonValue] = Field(default_factory=dict)
    review_events: tuple[ReviewEvent, ...] = ()
    source_bundle: SourceBundle | None = None

    @model_validator(mode="after")
    def _validate_artifact(self) -> "CardArtifact":
        validate_complete_card(self.card)

        binding_ids = [binding.binding_id for binding in self.bindings]
        if len(binding_ids) != len(set(binding_ids)):
            raise ValueError("binding IDs must be unique within an artifact")
        for binding in self.bindings:
            if binding.target != self.target:
                raise ValueError("every binding target must equal the artifact target")
        if self.source_bundle is not None and self.source_bundle.target != self.target:
            raise ValueError("source bundle target must equal the artifact target")
        if self.source_bundle is not None:
            source_files = {
                source_file.source_uri: source_file for source_file in self.source_bundle.files
            }
            readme_source = next(
                (item for item in self.source_bundle.files if item.name == "README.md"),
                None,
            )
            config_source = next(
                (item for item in self.source_bundle.files if item.name == "config.json"),
                None,
            )
            card_data = (
                parse_frontmatter(readme_source.content) if readme_source is not None else {}
            )
            config_data: dict[str, Any] = {}
            if config_source is not None:
                try:
                    parsed_config = json.loads(config_source.content)
                except ValueError as exc:
                    raise ValueError("source bundle config.json is not valid JSON") from exc
                if not isinstance(parsed_config, dict):
                    raise ValueError("source bundle config.json must contain an object")
                config_data = parsed_config
            target_manifest_uri = (
                f"hf://model/{self.target.model_id}@{self.target.resolved_revision}"
            )
            derivation_uri = f"file:///derivations/{self.target.canonical_target}"
            composer_commit = self.metadata.get("composer_bridge_commit")
            for binding in self.bindings:
                if binding.derivation_trace is not None and any(
                    evidence.source_uri in source_files for evidence in binding.evidence
                ):
                    if binding.derivation_trace.rule == "architecture_type_v1":
                        expected_output, expected_inputs = derive_architecture_type(
                            config_data
                        )
                    elif (
                        binding.derivation_trace.rule
                        == "modalities_from_explicit_pipeline_or_architecture_v1"
                    ):
                        expected_output, expected_inputs = derive_modalities(
                            card_data, config_data
                        )
                    else:
                        raise ValueError(
                            "unrecognized file-backed deterministic derivation rule"
                        )
                    if binding.derivation_trace.inputs != expected_inputs:
                        raise ValueError(
                            "file-backed derivation inputs do not match frozen sources"
                        )
                    if binding.derivation_trace.output != expected_output:
                        raise ValueError(
                            "file-backed derivation output does not match frozen sources"
                        )
                for evidence in binding.evidence:
                    source_file = source_files.get(evidence.source_uri)
                    if source_file is not None:
                        if evidence.source_revision != self.target.resolved_revision:
                            raise ValueError(
                                "file-backed evidence revision does not match target commit"
                            )
                        if evidence.source_sha256 != source_file.sha256:
                            raise ValueError(
                                "file-backed evidence hash does not match source bundle"
                            )
                        if evidence.exact_text is not None:
                            assert evidence.start_offset is not None
                            assert evidence.end_offset is not None
                            normalized_source = _normalize_evidence_text(source_file.content)
                            if (
                                normalized_source[
                                    evidence.start_offset:evidence.end_offset
                                ]
                                != evidence.exact_text
                            ):
                                raise ValueError(
                                    "file-backed exact evidence span does not match source content"
                                )
                        if evidence.structured_pointer is not None:
                            if source_file.name == "README.md":
                                structured_document: Any = {
                                    "card_data": parse_frontmatter(source_file.content)
                                }
                            elif source_file.name == "config.json":
                                try:
                                    config_document = json.loads(source_file.content)
                                except ValueError as exc:
                                    raise ValueError(
                                        "structured config evidence requires valid JSON"
                                    ) from exc
                                structured_document = {"config": config_document}
                            elif source_file.name == "extras.json":
                                # the collector's own JSON sidecar: the revision's
                                # safetensors bytes and README frontmatter, which
                                # model_info does not return. It is a plain document, so
                                # its pointers resolve against it directly.
                                try:
                                    structured_document = json.loads(source_file.content)
                                except ValueError as exc:
                                    raise ValueError(
                                        "structured extras evidence requires valid JSON"
                                    ) from exc
                            else:
                                raise ValueError(
                                    "structured file evidence is supported only for README.md "
                                    "frontmatter, config.json and extras.json"
                                )
                            resolved_fragment = _resolve_json_pointer(
                                structured_document, evidence.structured_pointer
                            )
                            if resolved_fragment != evidence.structured_fragment:
                                raise ValueError(
                                    "structured evidence fragment does not match frozen source "
                                    f"for {binding.field_path} at "
                                    f"{evidence.structured_pointer}"
                                )
                        continue
                    if evidence.source_uri == target_manifest_uri:
                        if evidence.source_revision != self.target.resolved_revision:
                            raise ValueError(
                                "target-manifest evidence revision does not match target commit"
                            )
                        target_fragments: dict[str, Any] = {
                            "/target": self.target.model_dump(mode="json"),
                            "/target/model_id": self.target.model_id,
                            "/target/requested_revision": self.target.requested_revision,
                            "/target/resolved_revision": self.target.resolved_revision,
                            "/target/repository_name": self.target.model_id.rsplit("/", 1)[-1],
                        }
                        if evidence.structured_pointer not in target_fragments:
                            raise ValueError("unsupported target-manifest evidence pointer")
                        if (
                            evidence.structured_fragment
                            != target_fragments[evidence.structured_pointer]
                        ):
                            raise ValueError(
                                "target-manifest evidence fragment does not match target"
                            )
                    elif evidence.source_uri == derivation_uri:
                        if not isinstance(composer_commit, str):
                            raise ValueError(
                                "derivation evidence requires a composer bridge commit"
                            )
                        if evidence.source_revision != composer_commit:
                            raise ValueError(
                                "derivation evidence revision does not match composer bridge"
                            )
                        expected_pointer = (
                            f"/derivations/{binding.field_path.replace('.', '/')}"
                        )
                        if evidence.structured_pointer != expected_pointer:
                            raise ValueError(
                                "derivation evidence pointer does not match binding field"
                            )
                        fragment = evidence.structured_fragment
                        if not isinstance(fragment, dict):
                            raise ValueError("derivation evidence fragment must be an object")
                        if fragment.get("path") != binding.field_path:
                            raise ValueError(
                                "derivation evidence path does not match binding field"
                            )
                        if fragment.get("output") != binding.proposed_value:
                            raise ValueError(
                                "derivation evidence output does not match proposed value"
                            )
                        if binding.derivation_trace is None:
                            raise ValueError(
                                "derivation evidence requires a deterministic derivation trace"
                            )
                        if fragment.get("inputs") != binding.derivation_trace.inputs:
                            raise ValueError(
                                "derivation evidence inputs do not match derivation trace"
                            )
                    else:
                        raise ValueError(
                            "binding evidence URI is not present in the frozen source bundle"
                        )
                    assert evidence.structured_fragment is not None
                    fragment_payload = json.dumps(
                        evidence.structured_fragment,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                    if hashlib.sha256(fragment_payload).hexdigest() != evidence.source_sha256:
                        raise ValueError(
                            "synthetic structured evidence hash does not match its fragment"
                        )

        known_bindings = set(binding_ids)
        event_ids: set[str] = set()
        latest_by_binding: dict[str, ReviewEvent] = {}
        previous_created_at: datetime | None = None
        for event in self.review_events:
            if event.event_id in event_ids:
                raise ValueError("review event IDs must be unique")
            event_ids.add(event.event_id)
            if event.binding_id not in known_bindings:
                raise ValueError(f"review event references unknown binding {event.binding_id}")
            if previous_created_at is not None and event.created_at < previous_created_at:
                raise ValueError("review events must be stored in append-time order")
            previous_created_at = event.created_at
            previous = latest_by_binding.get(event.binding_id)
            expected_previous = previous.event_id if previous else None
            if event.supersedes_event_id != expected_previous:
                raise ValueError("supersedes_event_id must name the prior event for the binding")
            latest_by_binding[event.binding_id] = event

        def project(*, reviewed: bool) -> dict[str, dict[str, JsonValue]]:
            events_by_binding: dict[str, list[ReviewEvent]] = {}
            if reviewed:
                for review_event in self.review_events:
                    events_by_binding.setdefault(review_event.binding_id, []).append(
                        review_event
                    )

            grouped: dict[str, list[tuple[tuple[int, ...], JsonValue]]] = {}
            for binding in self.bindings:
                field_path = binding.field_path
                value = binding.proposed_value
                action = binding.verifier_action
                for review_event in events_by_binding.get(binding.binding_id, []):
                    action = review_event.action
                    if review_event.action is VerifierAction.REASSIGN:
                        if review_event.field_path is not None:
                            field_path = review_event.field_path
                        if review_event.corrected_value_set:
                            value = review_event.corrected_value
                if action is VerifierAction.WITHHOLD:
                    continue
                canonical, indexes = parse_field_path(field_path)
                grouped.setdefault(canonical, []).append((indexes, value))

            projection = blank_card()
            for canonical, assignments in grouped.items():
                whole = [(indexes, value) for indexes, value in assignments if not indexes]
                indexed = [(indexes, value) for indexes, value in assignments if indexes]
                if whole and indexed:
                    raise ValueError(
                        f"{canonical} has both whole-field and indexed included bindings"
                    )
                if whole:
                    first = whole[0][1]
                    if any(value != first for _, value in whole[1:]):
                        raise ValueError(f"{canonical} has conflicting included bindings")
                    set_field_value(projection, canonical, first)
                    continue
                if all(len(indexes) == 1 for indexes, _ in indexed):
                    by_index: dict[int, JsonValue] = {}
                    for indexes, value in indexed:
                        index = indexes[0]
                        if index in by_index and by_index[index] != value:
                            raise ValueError(
                                f"{canonical}[{index}] has conflicting included bindings"
                            )
                        by_index[index] = value
                    set_field_value(
                        projection,
                        canonical,
                        [by_index[index] for index in sorted(by_index)],
                    )
                    continue
                for indexes, value in sorted(indexed, key=lambda item: item[0]):
                    indexed_path = canonical + "".join(f"[{index}]" for index in indexes)
                    try:
                        set_field_value(
                            projection, indexed_path, value, create_missing=True
                        )
                    except (IndexError, TypeError) as exc:
                        raise ValueError(
                            f"cannot project sparse indexed binding {indexed_path}"
                        ) from exc
            return projection

        generation_projection = project(reviewed=False)
        reviewed_projection = project(reviewed=True)
        if self.card not in (generation_projection, reviewed_projection):
            filled = []
            for section, fields in self.card.items():
                for field, value in fields.items():
                    if value not in (None, NOT_SPECIFIED, NOT_APPLICABLE, [], {}):
                        filled.append(f"{section}.{field}")
            raise ValueError(
                "card is not the generation-time or reviewed BindingRecord projection; "
                f"filled fields: {', '.join(filled) or 'none'}"
            )

        artifact_payload = self.model_dump(
            mode="json", exclude={"artifact_id"}, exclude_none=False
        )
        expected_id = _canonical_digest("card", artifact_payload)
        if self.artifact_id and self.artifact_id != expected_id:
            raise ValueError(
                f"artifact_id is content-derived; expected {expected_id}, got {self.artifact_id}"
            )
        object.__setattr__(self, "artifact_id", expected_id)
        return self

    def binding(self, binding_id: str) -> BindingRecord:
        for binding in self.bindings:
            if binding.binding_id == binding_id:
                return binding
        raise KeyError(binding_id)
