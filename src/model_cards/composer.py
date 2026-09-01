"""Two-pass, evidence-only Model Card composition.

Pass A replays a complete candidate/gate inventory against frozen sources.
Pass B exposes only accepted values and public evidence references to an
optional selector, then projects exact selected values through the public
schema.  Source bodies never enter writer input, plans, or results.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field as dataclass_field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping, Protocol, Sequence

from .artifact import CardArtifact, project_card
from .bindings import binding_id_for
from .claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    verify_claim_gate_record,
)
from .models import (
    Binding,
    BindingOrigin,
    Disposition,
    EvidenceKind,
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from .policy import decide_binding
from .schema import (
    CONTENT_FIELD_PATHS,
    CONTRACT_VERSION,
    LIST_FIELDS,
    NOT_SPECIFIED,
    canonical_field_path,
    get_field,
    parse_field_path,
    validate_field_value,
    validate_public_card,
)


COMPOSER_VERSION = "evidence-only-composer/v1"
TARGET_DERIVATION_NAME = "exact-target-consensus"
TARGET_DERIVATION_VERSION = "v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9_.:-]{1,127}$")
_SPAN_RE = re.compile(r"^(?:0|[1-9][0-9]*):(?:[1-9][0-9]*)$")
_SCHEMA_PAYLOAD = {
    "contract_version": CONTRACT_VERSION,
    "content_field_paths": list(CONTENT_FIELD_PATHS),
    "list_fields": sorted(LIST_FIELDS),
}


class ComposerError(ValueError):
    """Composition inputs are incomplete, inconsistent, or inventive."""


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
        raise ComposerError("composition values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _strict(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ComposerError(f"{label} has an invalid shape")
    return value


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise ComposerError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _source_snapshot(sources: Sequence[SourceDocument]) -> str:
    payload = []
    for source in sources:
        if not isinstance(source, SourceDocument):
            raise ComposerError("composition sources must be SourceDocument records")
        content = (
            hashlib.sha256(source.text.encode("utf-8")).hexdigest()
            if source.text is not None
            else _digest(source.data)
        )
        payload.append(
            {
                "source_id": source.source_id,
                "source_uri": source.source_uri,
                "role": source.role.value,
                "source_revision": source.source_revision,
                "source_sha256": source.sha256,
                "semantic_content_sha256": content,
                "target": source.target.to_dict() if source.target else None,
                "synthetic": source.synthetic,
            }
        )
    return _digest(sorted(payload, key=_canonical))


@dataclass(frozen=True)
class PublicEvidenceReference:
    source_id: str
    source_uri: str
    source_role: str
    source_revision: str
    source_sha256: str
    locator_kind: str
    locator: str
    section_path: tuple[str, ...] = ()
    table_id: str | None = None

    def __post_init__(self) -> None:
        if not all(
            isinstance(item, str) and item
            for item in (
                self.source_id,
                self.source_uri,
                self.source_role,
                self.source_revision,
                self.locator_kind,
                self.locator,
            )
        ):
            raise ComposerError("public evidence reference contains an empty identifier")
        _require_digest(self.source_sha256, "source_sha256")
        if self.locator_kind not in {"exact_span", "json_pointer"}:
            raise ComposerError("public evidence locator kind is invalid")
        try:
            SourceRole(self.source_role)
        except (TypeError, ValueError) as exc:
            raise ComposerError("public evidence source role is invalid") from exc
        if self.locator_kind == "exact_span":
            if not _SPAN_RE.fullmatch(self.locator):
                raise ComposerError("public exact-span locator is invalid")
            start, end = (int(item) for item in self.locator.split(":"))
            if end <= start:
                raise ComposerError("public exact-span locator is empty")
        elif not self.locator.startswith("/"):
            raise ComposerError("public JSON Pointer locator is invalid")
        path = tuple(self.section_path)
        if any(not isinstance(item, str) or not item for item in path):
            raise ComposerError("public evidence section_path is invalid")
        object.__setattr__(self, "section_path", path)
        if self.table_id is not None and (
            not isinstance(self.table_id, str) or not self.table_id
        ):
            raise ComposerError("public evidence table_id is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_uri": self.source_uri,
            "source_role": self.source_role,
            "source_revision": self.source_revision,
            "source_sha256": self.source_sha256,
            "locator_kind": self.locator_kind,
            "locator": self.locator,
            "section_path": list(self.section_path),
            "table_id": self.table_id,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "PublicEvidenceReference":
        item = _strict(
            value,
            {
                "source_id",
                "source_uri",
                "source_role",
                "source_revision",
                "source_sha256",
                "locator_kind",
                "locator",
                "section_path",
                "table_id",
            },
            "public evidence reference",
        )
        if not isinstance(item["section_path"], list):
            raise ComposerError("public evidence section_path must be an array")
        return cls(
            source_id=item["source_id"],
            source_uri=item["source_uri"],
            source_role=item["source_role"],
            source_revision=item["source_revision"],
            source_sha256=item["source_sha256"],
            locator_kind=item["locator_kind"],
            locator=item["locator"],
            section_path=tuple(item["section_path"]),
            table_id=item["table_id"],
        )


def _references(candidate: ClaimCandidate) -> tuple[PublicEvidenceReference, ...]:
    references = []
    for evidence in candidate.evidence:
        if evidence.kind is EvidenceKind.QUOTE:
            locator_kind = "exact_span"
            locator = f"{evidence.char_start}:{evidence.char_end}"
        else:
            locator_kind = "json_pointer"
            locator = evidence.pointer or ""
        references.append(
            PublicEvidenceReference(
                source_id=evidence.source_id,
                source_uri=evidence.source_uri,
                source_role=evidence.source_role.value,
                source_revision=evidence.source_revision,
                source_sha256=evidence.source_sha256,
                locator_kind=locator_kind,
                locator=locator,
                section_path=evidence.section_path,
                table_id=evidence.table_id,
            )
        )
    return tuple(sorted(references, key=lambda item: _canonical(item.to_dict())))


@dataclass(frozen=True)
class CandidateSummary:
    """The only candidate material exposed to an optional writer."""

    candidate_id: str
    candidate_sha256: str
    gate_record_sha256: str
    field_path: str
    relation: RelationToTarget
    value_json: str
    references: tuple[PublicEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CANDIDATE_RE.fullmatch(
            self.candidate_id
        ):
            raise ComposerError("candidate summary id is invalid")
        _require_digest(self.candidate_sha256, "candidate_sha256")
        _require_digest(self.gate_record_sha256, "gate_record_sha256")
        try:
            object.__setattr__(self, "relation", RelationToTarget(self.relation))
            value = json.loads(self.value_json)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ComposerError("candidate summary is malformed") from exc
        if self.value_json != _canonical(value):
            raise ComposerError("candidate summary value is not canonical JSON")
        validate_field_value(self.field_path, value)
        refs = tuple(self.references)
        if not refs or not all(isinstance(item, PublicEvidenceReference) for item in refs):
            raise ComposerError("candidate summary requires public references")
        if refs != tuple(sorted(refs, key=lambda item: _canonical(item.to_dict()))):
            raise ComposerError("candidate references are not in canonical order")
        object.__setattr__(self, "references", refs)

    @property
    def value(self) -> Any:
        return json.loads(self.value_json)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_sha256": self.candidate_sha256,
            "gate_record_sha256": self.gate_record_sha256,
            "field_path": self.field_path,
            "relation": self.relation.value,
            "value": self.value,
            "references": [item.to_dict() for item in self.references],
        }

    @classmethod
    def from_dict(cls, value: Any) -> "CandidateSummary":
        item = _strict(
            value,
            {
                "candidate_id",
                "candidate_sha256",
                "gate_record_sha256",
                "field_path",
                "relation",
                "value",
                "references",
            },
            "candidate summary",
        )
        if not isinstance(item["references"], list):
            raise ComposerError("candidate references must be an array")
        return cls(
            candidate_id=item["candidate_id"],
            candidate_sha256=item["candidate_sha256"],
            gate_record_sha256=item["gate_record_sha256"],
            field_path=item["field_path"],
            relation=item["relation"],
            value_json=_canonical(item["value"]),
            references=tuple(PublicEvidenceReference.from_dict(x) for x in item["references"]),
        )


@dataclass(frozen=True)
class WriterInput:
    target: TargetIdentity
    accepted_candidates: tuple[CandidateSummary, ...]
    schema_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.target, TargetIdentity):
            raise ComposerError("writer input target is invalid")
        _require_digest(self.schema_sha256, "schema_sha256")
        summaries = tuple(self.accepted_candidates)
        if not all(isinstance(item, CandidateSummary) for item in summaries):
            raise ComposerError("writer input candidate summary is malformed")
        if summaries != tuple(sorted(summaries, key=lambda item: item.candidate_id)):
            raise ComposerError("writer input candidates are not in canonical order")
        if len({item.candidate_id for item in summaries}) != len(summaries):
            raise ComposerError("writer input contains duplicate candidates")
        object.__setattr__(self, "accepted_candidates", summaries)

    @property
    def content_sha256(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.to_dict(),
            "accepted_candidates": [item.to_dict() for item in self.accepted_candidates],
            "schema_sha256": self.schema_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "WriterInput":
        item = _strict(
            value, {"target", "accepted_candidates", "schema_sha256"}, "writer input"
        )
        target = _strict(item["target"], {"model_id", "revision"}, "writer target")
        if not isinstance(item["accepted_candidates"], list):
            raise ComposerError("accepted_candidates must be an array")
        return cls(
            target=TargetIdentity.from_dict(target),
            accepted_candidates=tuple(
                CandidateSummary.from_dict(x) for x in item["accepted_candidates"]
            ),
            schema_sha256=item["schema_sha256"],
        )


@dataclass(frozen=True)
class WriterChoice:
    candidate_id: str
    value_json: str

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CANDIDATE_RE.fullmatch(
            self.candidate_id
        ):
            raise ComposerError("writer choice candidate_id is invalid")
        try:
            value = json.loads(self.value_json)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ComposerError("writer choice value is invalid JSON") from exc
        if self.value_json != _canonical(value):
            raise ComposerError("writer choice value is not canonical JSON")

    @property
    def value(self) -> Any:
        return json.loads(self.value_json)

    @classmethod
    def create(cls, candidate_id: str, value: Any) -> "WriterChoice":
        return cls(candidate_id=candidate_id, value_json=_canonical(value))

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, "value": self.value}

    @classmethod
    def from_dict(cls, value: Any) -> "WriterChoice":
        item = _strict(value, {"candidate_id", "value"}, "writer choice")
        return cls.create(item["candidate_id"], item["value"])


@dataclass(frozen=True)
class WriterSelection:
    choices: tuple[WriterChoice, ...]

    def __post_init__(self) -> None:
        choices = tuple(self.choices)
        if not all(isinstance(item, WriterChoice) for item in choices):
            raise ComposerError("writer selection contains malformed choices")
        if choices != tuple(sorted(choices, key=lambda item: item.candidate_id)):
            raise ComposerError("writer choices are not in canonical order")
        if len({item.candidate_id for item in choices}) != len(choices):
            raise ComposerError("writer selection contains duplicate candidate ids")
        object.__setattr__(self, "choices", choices)

    def to_dict(self) -> dict[str, Any]:
        return {"choices": [item.to_dict() for item in self.choices]}

    @classmethod
    def from_dict(cls, value: Any) -> "WriterSelection":
        item = _strict(value, {"choices"}, "writer selection")
        if not isinstance(item["choices"], list):
            raise ComposerError("writer choices must be an array")
        return cls(tuple(WriterChoice.from_dict(x) for x in item["choices"]))


class EvidenceOnlyWriter(Protocol):
    def select(self, writer_input: WriterInput) -> WriterSelection:
        """Select exact candidate IDs and values without receiving sources."""


class SelectAllEvidenceWriter:
    def select(self, writer_input: WriterInput) -> WriterSelection:
        return WriterSelection(
            tuple(
                WriterChoice.create(item.candidate_id, item.value)
                for item in writer_input.accepted_candidates
            )
        )


class ConflictReason(str, Enum):
    DISTINCT_ELIGIBLE_VALUES = "distinct_eligible_values"
    PROJECTION_SHAPE_CONFLICT = "projection_shape_conflict"
    LIST_INDEX_GAP = "list_index_gap"


@dataclass(frozen=True)
class CompositionConflict:
    field_path: str
    reason: ConflictReason
    candidate_ids: tuple[str, ...]
    value_sha256s: tuple[str, ...]

    def __post_init__(self) -> None:
        canonical_field_path(self.field_path)
        try:
            object.__setattr__(self, "reason", ConflictReason(self.reason))
        except (TypeError, ValueError) as exc:
            raise ComposerError("composition conflict reason is invalid") from exc
        ids = tuple(self.candidate_ids)
        if not ids or ids != tuple(sorted(set(ids))):
            raise ComposerError("composition conflict candidate ids are invalid")
        if any(not _CANDIDATE_RE.fullmatch(item) for item in ids):
            raise ComposerError("composition conflict candidate id is invalid")
        values = tuple(self.value_sha256s)
        if values != tuple(sorted(set(values))) or any(
            not _DIGEST_RE.fullmatch(item) for item in values
        ):
            raise ComposerError("composition conflict value digests are invalid")
        object.__setattr__(self, "candidate_ids", ids)
        object.__setattr__(self, "value_sha256s", values)

    @property
    def content_sha256(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_path": self.field_path,
            "reason": self.reason.value,
            "candidate_ids": list(self.candidate_ids),
            "value_sha256s": list(self.value_sha256s),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "CompositionConflict":
        item = _strict(
            value,
            {"field_path", "reason", "candidate_ids", "value_sha256s"},
            "composition conflict",
        )
        if not isinstance(item["candidate_ids"], list) or not isinstance(
            item["value_sha256s"], list
        ):
            raise ComposerError("composition conflict arrays are malformed")
        return cls(
            field_path=item["field_path"],
            reason=item["reason"],
            candidate_ids=tuple(item["candidate_ids"]),
            value_sha256s=tuple(item["value_sha256s"]),
        )


@dataclass(frozen=True)
class CompositionDerivation:
    name: str
    version: str
    output_path: str
    method: str
    input_candidate_ids: tuple[str, ...]
    input_sha256s: tuple[str, ...]
    output_sha256: str

    def __post_init__(self) -> None:
        if not all(
            isinstance(item, str) and _CODE_RE.fullmatch(item)
            for item in (self.name, self.version, self.method)
        ):
            raise ComposerError("composition derivation identifier is invalid")
        if self.output_path != "$target":
            canonical_field_path(self.output_path)
        ids = tuple(self.input_candidate_ids)
        digests = tuple(self.input_sha256s)
        if ids != tuple(sorted(set(ids))) or any(not _CANDIDATE_RE.fullmatch(x) for x in ids):
            raise ComposerError("composition derivation candidate ids are invalid")
        if digests != tuple(sorted(set(digests))) or any(
            not _DIGEST_RE.fullmatch(x) for x in digests
        ):
            raise ComposerError("composition derivation input digests are invalid")
        _require_digest(self.output_sha256, "derivation output_sha256")
        object.__setattr__(self, "input_candidate_ids", ids)
        object.__setattr__(self, "input_sha256s", digests)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "output_path": self.output_path,
            "method": self.method,
            "input_candidate_ids": list(self.input_candidate_ids),
            "input_sha256s": list(self.input_sha256s),
            "output_sha256": self.output_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "CompositionDerivation":
        item = _strict(
            value,
            {
                "name",
                "version",
                "output_path",
                "method",
                "input_candidate_ids",
                "input_sha256s",
                "output_sha256",
            },
            "composition derivation",
        )
        if not isinstance(item["input_candidate_ids"], list) or not isinstance(
            item["input_sha256s"], list
        ):
            raise ComposerError("composition derivation arrays are malformed")
        return cls(
            name=item["name"],
            version=item["version"],
            output_path=item["output_path"],
            method=item["method"],
            input_candidate_ids=tuple(item["input_candidate_ids"]),
            input_sha256s=tuple(item["input_sha256s"]),
            output_sha256=item["output_sha256"],
        )


@dataclass(frozen=True)
class ValidatedCompositionInventory:
    """Private pass-A output; contains sources and is never sent to a writer."""

    target: TargetIdentity
    candidates: tuple[ClaimCandidate, ...]
    gate_records: tuple[ClaimGateRecord, ...]
    sources: tuple[SourceDocument, ...]
    source_snapshot_sha256: str
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.target, TargetIdentity):
            raise ComposerError("validated inventory target is invalid")
        candidates = tuple(self.candidates)
        records = tuple(self.gate_records)
        sources = tuple(self.sources)
        if candidates != tuple(sorted(candidates, key=lambda item: item.candidate_id)):
            raise ComposerError("validated candidates are not in canonical order")
        if records != tuple(sorted(records, key=lambda item: item.candidate.candidate_id)):
            raise ComposerError("validated gate records are not in canonical order")
        _require_digest(self.source_snapshot_sha256, "source snapshot")
        if _source_snapshot(sources) != self.source_snapshot_sha256:
            raise ComposerError("validated source snapshot is stale")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "gate_records", records)
        object.__setattr__(self, "sources", sources)
        object.__setattr__(
            self,
            "_content_sha256",
            _digest(
                {
                    "target": self.target.to_dict(),
                    "candidates": [item.content_sha256 for item in candidates],
                    "gate_records": [item.content_sha256 for item in records],
                    "source_snapshot_sha256": self.source_snapshot_sha256,
                }
            ),
        )

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def validate_integrity(self) -> None:
        if _source_snapshot(self.sources) != self.source_snapshot_sha256:
            raise ComposerError("source snapshot changed after pass A")
        expected = _digest(
            {
                "target": self.target.to_dict(),
                "candidates": [item.content_sha256 for item in self.candidates],
                "gate_records": [item.content_sha256 for item in self.gate_records],
                "source_snapshot_sha256": self.source_snapshot_sha256,
            }
        )
        if expected != self.content_sha256:
            raise ComposerError("validated inventory integrity failed")
        for candidate in self.candidates:
            candidate.validate_integrity()
        for record in self.gate_records:
            record.validate_integrity()
            verify_claim_gate_record(record, self.sources)


@dataclass(frozen=True)
class CompositionPlan:
    target: TargetIdentity
    inventory_sha256: str
    source_snapshot_sha256: str
    schema_sha256: str
    inventory_candidate_ids: tuple[str, ...]
    eligible_candidate_ids: tuple[str, ...]
    included_candidate_ids: tuple[str, ...]
    excluded_candidate_ids: tuple[str, ...]
    writer_input: WriterInput
    writer_selection: WriterSelection
    conflicts: tuple[CompositionConflict, ...]
    derivations: tuple[CompositionDerivation, ...]
    composer_version: str = COMPOSER_VERSION
    _content_sha256: str = dataclass_field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.composer_version != COMPOSER_VERSION:
            raise ComposerError("composer version is not recognized")
        if not isinstance(self.target, TargetIdentity):
            raise ComposerError("composition plan target is invalid")
        for name, digest in (
            ("inventory_sha256", self.inventory_sha256),
            ("source_snapshot_sha256", self.source_snapshot_sha256),
            ("schema_sha256", self.schema_sha256),
        ):
            _require_digest(digest, name)
        if self.schema_sha256 != _digest(_SCHEMA_PAYLOAD):
            raise ComposerError("composition plan schema parameters are stale")
        groups = []
        for name in (
            "inventory_candidate_ids",
            "eligible_candidate_ids",
            "included_candidate_ids",
            "excluded_candidate_ids",
        ):
            values = tuple(getattr(self, name))
            if values != tuple(sorted(set(values))) or any(
                not _CANDIDATE_RE.fullmatch(item) for item in values
            ):
                raise ComposerError(f"{name} is not a canonical candidate-id set")
            object.__setattr__(self, name, values)
            groups.append(values)
        inventory, eligible, included, excluded = map(set, groups)
        if not included <= eligible <= inventory:
            raise ComposerError("composition candidate sets are inconsistent")
        if excluded != inventory - included:
            raise ComposerError("excluded candidates do not complement included candidates")
        if not isinstance(self.writer_input, WriterInput) or not isinstance(
            self.writer_selection, WriterSelection
        ):
            raise ComposerError("composition writer records are malformed")
        if self.writer_input.target != self.target:
            raise ComposerError("writer input target does not match plan target")
        choices = {item.candidate_id for item in self.writer_selection.choices}
        if choices != included:
            raise ComposerError("writer selection and included candidate ids disagree")
        summaries = {item.candidate_id for item in self.writer_input.accepted_candidates}
        if not choices <= summaries <= eligible:
            raise ComposerError("writer input is not limited to eligible candidates")
        summary_by_id = {
            item.candidate_id: item for item in self.writer_input.accepted_candidates
        }
        for choice in self.writer_selection.choices:
            if choice.value_json != summary_by_id[choice.candidate_id].value_json:
                raise ComposerError("writer selection rewrites an accepted value")
        conflicts = tuple(self.conflicts)
        if conflicts != tuple(
            sorted(conflicts, key=lambda item: (item.field_path, item.reason.value))
        ):
            raise ComposerError("composition conflicts are not in canonical order")
        conflicted = {cid for item in conflicts for cid in item.candidate_ids}
        if not conflicted <= eligible:
            raise ComposerError("composition conflict references an ineligible candidate")
        if included & conflicted:
            raise ComposerError("conflicted candidates cannot be included")
        derivations = tuple(self.derivations)
        if not derivations or derivations[0].output_path != "$target":
            raise ComposerError("composition plan lacks the target derivation")
        if derivations != tuple(
            sorted(
                derivations,
                key=lambda item: (item.output_path != "$target", item.output_path, item.name),
            )
        ):
            raise ComposerError("composition derivations are not in canonical order")
        target_derivation = derivations[0]
        if (
            target_derivation.name != TARGET_DERIVATION_NAME
            or target_derivation.version != TARGET_DERIVATION_VERSION
            or target_derivation.method != "unanimous_candidate_target_identity"
            or target_derivation.input_candidate_ids != self.inventory_candidate_ids
            or target_derivation.input_sha256s != (_digest(self.target.to_dict()),)
            or target_derivation.output_sha256 != _digest(self.target.to_dict())
        ):
            raise ComposerError("target identity derivation is incomplete or stale")
        field_derivations = derivations[1:]
        derived_id_list = [
            cid for item in field_derivations for cid in item.input_candidate_ids
        ]
        if set(derived_id_list) != included or len(derived_id_list) != len(included):
            raise ComposerError("field derivations do not cover included candidates exactly")
        for derivation in field_derivations:
            if (
                derivation.name != "exact-evidence-value-projection"
                or derivation.version != "v1"
                or derivation.method != "exact_candidate_value_coalescence"
            ):
                raise ComposerError("field value derivation is not recognized")
            selected = [summary_by_id[cid] for cid in derivation.input_candidate_ids]
            if not selected or {item.field_path for item in selected} != {
                derivation.output_path
            }:
                raise ComposerError("field derivation inputs do not match its output path")
            values = {item.value_json for item in selected}
            if len(values) != 1 or derivation.output_sha256 != _digest(
                json.loads(next(iter(values)))
            ):
                raise ComposerError("field derivation rewrites or conflates values")
        object.__setattr__(self, "conflicts", conflicts)
        object.__setattr__(self, "derivations", derivations)
        object.__setattr__(self, "_content_sha256", _digest(self._content_payload()))

    def _content_payload(self) -> dict[str, Any]:
        return {
            "composer_version": self.composer_version,
            "target": self.target.to_dict(),
            "inventory_sha256": self.inventory_sha256,
            "source_snapshot_sha256": self.source_snapshot_sha256,
            "schema_sha256": self.schema_sha256,
            "inventory_candidate_ids": list(self.inventory_candidate_ids),
            "eligible_candidate_ids": list(self.eligible_candidate_ids),
            "included_candidate_ids": list(self.included_candidate_ids),
            "excluded_candidate_ids": list(self.excluded_candidate_ids),
            "writer_input": self.writer_input.to_dict(),
            "writer_selection": self.writer_selection.to_dict(),
            "conflicts": [item.to_dict() for item in self.conflicts],
            "derivations": [item.to_dict() for item in self.derivations],
        }

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {**self._content_payload(), "plan_sha256": self.content_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "CompositionPlan":
        item = _strict(
            value,
            {
                "composer_version",
                "target",
                "inventory_sha256",
                "source_snapshot_sha256",
                "schema_sha256",
                "inventory_candidate_ids",
                "eligible_candidate_ids",
                "included_candidate_ids",
                "excluded_candidate_ids",
                "writer_input",
                "writer_selection",
                "conflicts",
                "derivations",
                "plan_sha256",
            },
            "composition plan",
        )
        target = _strict(item["target"], {"model_id", "revision"}, "plan target")
        arrays = (
            "inventory_candidate_ids",
            "eligible_candidate_ids",
            "included_candidate_ids",
            "excluded_candidate_ids",
            "conflicts",
            "derivations",
        )
        if any(not isinstance(item[name], list) for name in arrays):
            raise ComposerError("composition plan array is malformed")
        plan = cls(
            composer_version=item["composer_version"],
            target=TargetIdentity.from_dict(target),
            inventory_sha256=item["inventory_sha256"],
            source_snapshot_sha256=item["source_snapshot_sha256"],
            schema_sha256=item["schema_sha256"],
            inventory_candidate_ids=tuple(item["inventory_candidate_ids"]),
            eligible_candidate_ids=tuple(item["eligible_candidate_ids"]),
            included_candidate_ids=tuple(item["included_candidate_ids"]),
            excluded_candidate_ids=tuple(item["excluded_candidate_ids"]),
            writer_input=WriterInput.from_dict(item["writer_input"]),
            writer_selection=WriterSelection.from_dict(item["writer_selection"]),
            conflicts=tuple(CompositionConflict.from_dict(x) for x in item["conflicts"]),
            derivations=tuple(CompositionDerivation.from_dict(x) for x in item["derivations"]),
        )
        if item["plan_sha256"] != plan.content_sha256:
            raise ComposerError("composition plan digest mismatch")
        return plan


@dataclass(frozen=True, init=False)
class CompositionResult:
    plan: CompositionPlan
    _card_json: str = dataclass_field(repr=False)
    _content_sha256: str = dataclass_field(repr=False)

    def __init__(self, plan: CompositionPlan, card: Mapping[str, Any]) -> None:
        if not isinstance(plan, CompositionPlan):
            raise ComposerError("composition result plan is malformed")
        copied = deepcopy(dict(card))
        validate_public_card(copied)
        if (
            copied["identity"]["model_id"] != plan.target.model_id
            or copied["identity"]["revision"] != plan.target.revision
        ):
            raise ComposerError("composition card target differs from target derivation")
        summaries = {
            item.candidate_id: item for item in plan.writer_input.accepted_candidates
        }
        for choice in plan.writer_selection.choices:
            summary = summaries[choice.candidate_id]
            if get_field(copied, summary.field_path) != choice.value:
                raise ComposerError("composition card rewrites a selected candidate value")
        for conflict in plan.conflicts:
            if get_field(copied, canonical_field_path(conflict.field_path)) != NOT_SPECIFIED:
                raise ComposerError("composition card projects a conflicted field")
        card_json = _canonical(copied)
        object.__setattr__(self, "plan", plan)
        object.__setattr__(self, "_card_json", card_json)
        object.__setattr__(
            self,
            "_content_sha256",
            _digest(
                {
                    "composer_version": COMPOSER_VERSION,
                    "plan_sha256": plan.content_sha256,
                    "card_sha256": hashlib.sha256(card_json.encode("utf-8")).hexdigest(),
                }
            ),
        )

    @property
    def card(self) -> dict[str, Any]:
        return json.loads(self._card_json)

    @property
    def card_sha256(self) -> str:
        return hashlib.sha256(self._card_json.encode("utf-8")).hexdigest()

    @property
    def content_sha256(self) -> str:
        return self._content_sha256

    def to_dict(self) -> dict[str, Any]:
        return {
            "composer_version": COMPOSER_VERSION,
            "plan": self.plan.to_dict(),
            "card": self.card,
            "card_sha256": self.card_sha256,
            "result_sha256": self.content_sha256,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "CompositionResult":
        item = _strict(
            value,
            {"composer_version", "plan", "card", "card_sha256", "result_sha256"},
            "composition result",
        )
        if item["composer_version"] != COMPOSER_VERSION:
            raise ComposerError("composition result version is not recognized")
        result = cls(CompositionPlan.from_dict(item["plan"]), item["card"])
        if item["card_sha256"] != result.card_sha256:
            raise ComposerError("composition card digest mismatch")
        if item["result_sha256"] != result.content_sha256:
            raise ComposerError("composition result digest mismatch")
        return result


def compose_pass_a(
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
) -> ValidatedCompositionInventory:
    """Validate and replay one complete candidate/gate inventory."""

    candidate_values = tuple(candidates)
    record_values = tuple(gate_records)
    source_values = tuple(sources.values()) if isinstance(sources, Mapping) else tuple(sources)
    if not candidate_values:
        raise ComposerError("composition requires at least one candidate")
    if not all(isinstance(item, ClaimCandidate) for item in candidate_values):
        raise ComposerError("candidate inventory contains malformed records")
    if not all(isinstance(item, ClaimGateRecord) for item in record_values):
        raise ComposerError("gate inventory contains malformed records")
    candidate_by_id: dict[str, ClaimCandidate] = {}
    for candidate in candidate_values:
        candidate.validate_integrity()
        if candidate.candidate_id in candidate_by_id:
            raise ComposerError("candidate inventory contains a duplicate candidate id")
        candidate_by_id[candidate.candidate_id] = candidate
    record_by_id: dict[str, ClaimGateRecord] = {}
    for record in record_values:
        record.validate_integrity()
        cid = record.candidate.candidate_id
        if cid in record_by_id:
            raise ComposerError("gate inventory contains duplicate or ambiguous records")
        record_by_id[cid] = record
    if set(candidate_by_id) != set(record_by_id):
        missing = sorted(set(candidate_by_id) - set(record_by_id))
        extra = sorted(set(record_by_id) - set(candidate_by_id))
        raise ComposerError(f"candidate/gate inventory is incomplete: missing={missing}, extra={extra}")
    targets = {(_canonical(item.target.to_dict())) for item in candidate_values}
    if len(targets) != 1:
        raise ComposerError("composition inventory mixes exact targets")
    target = candidate_values[0].target
    for cid, candidate in candidate_by_id.items():
        record = record_by_id[cid]
        if _canonical(record.candidate.to_dict()) != _canonical(candidate.to_dict()):
            raise ComposerError(f"gate record candidate differs from inventory: {cid}")
        verify_claim_gate_record(record, source_values)
    ordered_candidates = tuple(sorted(candidate_values, key=lambda item: item.candidate_id))
    ordered_records = tuple(
        sorted(record_values, key=lambda item: item.candidate.candidate_id)
    )
    snapshot = _source_snapshot(source_values)
    return ValidatedCompositionInventory(
        target=target,
        candidates=ordered_candidates,
        gate_records=ordered_records,
        sources=source_values,
        source_snapshot_sha256=snapshot,
    )


def _summary(candidate: ClaimCandidate, record: ClaimGateRecord) -> CandidateSummary:
    return CandidateSummary(
        candidate_id=candidate.candidate_id,
        candidate_sha256=candidate.content_sha256,
        gate_record_sha256=record.content_sha256,
        field_path=candidate.field_path,
        relation=candidate.relation,
        value_json=_canonical(candidate.value),
        references=_references(candidate),
    )


def _conflicts(
    summaries: Sequence[CandidateSummary],
) -> tuple[tuple[CompositionConflict, ...], set[str]]:
    by_base: dict[str, list[CandidateSummary]] = {}
    for summary in summaries:
        by_base.setdefault(canonical_field_path(summary.field_path), []).append(summary)
    conflicts: list[CompositionConflict] = []
    blocked: set[str] = set()
    for base, base_items in sorted(by_base.items()):
        shapes = {bool(parse_field_path(item.field_path)[1]) for item in base_items}
        if len(shapes) > 1:
            ids = tuple(sorted(item.candidate_id for item in base_items))
            conflicts.append(
                CompositionConflict(
                    field_path=base,
                    reason=ConflictReason.PROJECTION_SHAPE_CONFLICT,
                    candidate_ids=ids,
                    value_sha256s=tuple(sorted({_digest(item.value) for item in base_items})),
                )
            )
            blocked.update(ids)
            continue
        by_path: dict[str, list[CandidateSummary]] = {}
        for item in base_items:
            by_path.setdefault(item.field_path, []).append(item)
        path_conflict = False
        for field_path, path_items in sorted(by_path.items()):
            values = {_canonical(item.value) for item in path_items}
            if len(values) > 1:
                ids = tuple(sorted(item.candidate_id for item in path_items))
                conflicts.append(
                    CompositionConflict(
                        field_path=field_path,
                        reason=ConflictReason.DISTINCT_ELIGIBLE_VALUES,
                        candidate_ids=ids,
                        value_sha256s=tuple(sorted(_digest(json.loads(x)) for x in values)),
                    )
                )
                path_conflict = True
        if path_conflict:
            blocked.update(item.candidate_id for item in base_items)
            continue
        if shapes == {True}:
            indexes = sorted({parse_field_path(item.field_path)[1][0] for item in base_items})
            if indexes != list(range(len(indexes))):
                ids = tuple(sorted(item.candidate_id for item in base_items))
                conflicts.append(
                    CompositionConflict(
                        field_path=base,
                        reason=ConflictReason.LIST_INDEX_GAP,
                        candidate_ids=ids,
                        value_sha256s=tuple(
                            sorted({_digest(item.value) for item in base_items})
                        ),
                    )
                )
                blocked.update(ids)
    return (
        tuple(sorted(conflicts, key=lambda item: (item.field_path, item.reason.value))),
        blocked,
    )


def _binding(candidate: ClaimCandidate, target: TargetIdentity) -> Binding:
    kinds = {item.kind for item in candidate.evidence}
    if kinds == {EvidenceKind.QUOTE}:
        origin = BindingOrigin.QUOTED
    elif kinds == {EvidenceKind.STRUCTURED}:
        origin = BindingOrigin.STRUCTURED
    else:
        raise ComposerError("eligible candidate mixes evidence kinds")
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
        raise ComposerError(
            f"eligible gate record fails projection relation policy: {candidate.candidate_id}: {reason}"
        )
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


def compose_pass_b(
    inventory: ValidatedCompositionInventory,
    writer: EvidenceOnlyWriter | None = None,
) -> CompositionResult:
    """Project exact eligible values; never expose sources to the writer."""

    if not isinstance(inventory, ValidatedCompositionInventory):
        raise ComposerError("pass B requires a validated pass-A inventory")
    inventory.validate_integrity()
    record_by_id = {
        item.candidate.candidate_id: item for item in inventory.gate_records
    }
    eligible_candidates = tuple(
        item
        for item in inventory.candidates
        if record_by_id[item.candidate_id].projection_eligible
    )
    for candidate in eligible_candidates:
        base = canonical_field_path(candidate.field_path)
        if base == "identity.model_id" and candidate.value != inventory.target.model_id:
            raise ComposerError("eligible identity.model_id disagrees with target derivation")
        if base == "identity.revision" and candidate.value != inventory.target.revision:
            raise ComposerError("eligible identity.revision disagrees with target derivation")
    all_summaries = tuple(
        sorted(
            (_summary(item, record_by_id[item.candidate_id]) for item in eligible_candidates),
            key=lambda item: item.candidate_id,
        )
    )
    conflicts, blocked = _conflicts(all_summaries)
    safe_summaries = tuple(item for item in all_summaries if item.candidate_id not in blocked)
    writer_input = WriterInput(
        target=inventory.target,
        accepted_candidates=safe_summaries,
        schema_sha256=_digest(_SCHEMA_PAYLOAD),
    )
    selection = (writer or SelectAllEvidenceWriter()).select(writer_input)
    if not isinstance(selection, WriterSelection):
        raise ComposerError("writer must return a WriterSelection")
    summary_by_id = {item.candidate_id: item for item in safe_summaries}
    for choice in selection.choices:
        summary = summary_by_id.get(choice.candidate_id)
        if summary is None:
            raise ComposerError("writer selected an unknown or ineligible candidate")
        if choice.value_json != summary.value_json:
            raise ComposerError("writer invented or rewrote a candidate value")
    selected_ids = {item.candidate_id for item in selection.choices}
    selected_candidates = tuple(
        item for item in eligible_candidates if item.candidate_id in selected_ids
    )
    # A selector may omit a list entirely or choose a contiguous prefix, but
    # it cannot create an unprojectable gap.
    selected_by_base: dict[str, set[int]] = {}
    for candidate in selected_candidates:
        base, indexes = parse_field_path(candidate.field_path)
        if indexes:
            selected_by_base.setdefault(base, set()).add(indexes[0])
    for base, indexes in selected_by_base.items():
        ordered = sorted(indexes)
        if ordered != list(range(len(ordered))):
            raise ComposerError(f"writer selection creates a list index gap: {base}")

    binding_by_id: dict[str, Binding] = {}
    for candidate in selected_candidates:
        binding = _binding(candidate, inventory.target)
        binding_by_id.setdefault(binding.binding_id, binding)
    artifact = CardArtifact(
        target=inventory.target,
        bindings=tuple(sorted(binding_by_id.values(), key=lambda item: item.binding_id)),
    )
    card = project_card(artifact)
    for candidate in selected_candidates:
        if get_field(card, candidate.field_path) != candidate.value:
            raise ComposerError(
                f"projected card did not preserve accepted value: {candidate.candidate_id}"
            )
    for conflict in conflicts:
        base = canonical_field_path(conflict.field_path)
        if get_field(card, base) != NOT_SPECIFIED:
            raise ComposerError(f"conflicted field unexpectedly projected: {base}")

    derivations = [
        CompositionDerivation(
            name=TARGET_DERIVATION_NAME,
            version=TARGET_DERIVATION_VERSION,
            output_path="$target",
            method="unanimous_candidate_target_identity",
            input_candidate_ids=tuple(item.candidate_id for item in inventory.candidates),
            input_sha256s=tuple(
                sorted({_digest(item.target.to_dict()) for item in inventory.candidates})
            ),
            output_sha256=_digest(inventory.target.to_dict()),
        )
    ]
    selected_by_path: dict[str, list[ClaimCandidate]] = {}
    for candidate in selected_candidates:
        selected_by_path.setdefault(candidate.field_path, []).append(candidate)
    for field_path, items in sorted(selected_by_path.items()):
        derivations.append(
            CompositionDerivation(
                name="exact-evidence-value-projection",
                version="v1",
                output_path=field_path,
                method="exact_candidate_value_coalescence",
                input_candidate_ids=tuple(sorted(item.candidate_id for item in items)),
                input_sha256s=tuple(sorted({item.content_sha256 for item in items})),
                output_sha256=_digest(items[0].value),
            )
        )
    derivation_values = tuple(
        sorted(
            derivations,
            key=lambda item: (item.output_path != "$target", item.output_path, item.name),
        )
    )
    inventory_ids = tuple(item.candidate_id for item in inventory.candidates)
    eligible_ids = tuple(sorted(item.candidate_id for item in eligible_candidates))
    included_ids = tuple(sorted(selected_ids))
    plan = CompositionPlan(
        target=inventory.target,
        inventory_sha256=inventory.content_sha256,
        source_snapshot_sha256=inventory.source_snapshot_sha256,
        schema_sha256=_digest(_SCHEMA_PAYLOAD),
        inventory_candidate_ids=inventory_ids,
        eligible_candidate_ids=eligible_ids,
        included_candidate_ids=included_ids,
        excluded_candidate_ids=tuple(sorted(set(inventory_ids) - set(included_ids))),
        writer_input=writer_input,
        writer_selection=selection,
        conflicts=conflicts,
        derivations=derivation_values,
    )
    return CompositionResult(plan, card)


def compose_model_card(
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    *,
    writer: EvidenceOnlyWriter | None = None,
) -> CompositionResult:
    """Run both deterministic composition passes."""

    return compose_pass_b(compose_pass_a(candidates, gate_records, sources), writer)


class _RecordedWriter:
    def __init__(self, selection: WriterSelection) -> None:
        self._selection = selection

    def select(self, writer_input: WriterInput) -> WriterSelection:
        return self._selection


def verify_composition_result(
    result: CompositionResult,
    candidates: Iterable[ClaimCandidate],
    gate_records: Iterable[ClaimGateRecord],
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
) -> None:
    """Strictly replay a result from candidates, gates, sources, and recorded selection."""

    if not isinstance(result, CompositionResult):
        raise ComposerError("composition replay requires a CompositionResult")
    replayed = compose_model_card(
        candidates,
        gate_records,
        sources,
        writer=_RecordedWriter(result.plan.writer_selection),
    )
    if _canonical(replayed.to_dict()) != _canonical(result.to_dict()):
        raise ComposerError("composition result replay mismatch")


__all__ = [
    "COMPOSER_VERSION",
    "CandidateSummary",
    "ComposerError",
    "CompositionConflict",
    "CompositionDerivation",
    "CompositionPlan",
    "CompositionResult",
    "ConflictReason",
    "EvidenceOnlyWriter",
    "PublicEvidenceReference",
    "SelectAllEvidenceWriter",
    "TARGET_DERIVATION_NAME",
    "TARGET_DERIVATION_VERSION",
    "ValidatedCompositionInventory",
    "WriterChoice",
    "WriterInput",
    "WriterSelection",
    "compose_model_card",
    "compose_pass_a",
    "compose_pass_b",
    "verify_composition_result",
]
