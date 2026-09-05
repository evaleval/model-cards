"""Append-only review operations and reviewed-card materialization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import os
import tempfile
from typing import Any

from .records import (
    AssignmentOrigin,
    BenchmarkScope,
    BindingRecord,
    CardArtifact,
    ClaimEntity,
    LINEAGE_FIELDS,
    RelationToTarget,
    ReviewEvent,
    VerifierAction,
    lineage_expectations,
)
from .model_gates import FAMILY_ALLOWED_FIELDS
from .schema import (
    CARD_FIELD_PATHS,
    blank_card,
    canonical_field_path,
    parse_field_path,
    set_field_value,
)


class ReviewError(ValueError):
    """Raised when a review action would create an invalid audit state."""


class ReviewConflictError(ReviewError):
    """Raised when accepted bindings project incompatible values."""


@dataclass(frozen=True)
class EffectiveBinding:
    """A BindingRecord after folding its append-only review history."""

    binding: BindingRecord
    field_path: str
    value: Any
    claim_entity: ClaimEntity
    relation_to_target: RelationToTarget
    benchmark_scope: BenchmarkScope | None
    assignment_origin: AssignmentOrigin
    action: VerifierAction
    reason_code: str
    latest_event: ReviewEvent | None

    @property
    def included(self) -> bool:
        return self.action is not VerifierAction.WITHHOLD


_UNSET = object()


def load_artifact(path: str | Path) -> CardArtifact:
    """Load and fully validate a serialized artifact."""

    return CardArtifact.model_validate_json(Path(path).read_text(encoding="utf-8"))


def _atomic_write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return path


def save_artifact(artifact: CardArtifact, path: str | Path) -> Path:
    """Atomically save a complete artifact as stable, readable JSON."""

    serialized = artifact.model_dump_json(indent=2) + "\n"
    return _atomic_write(Path(path), serialized)


def latest_event(artifact: CardArtifact, binding_id: str) -> ReviewEvent | None:
    """Return the most recently appended event for ``binding_id``."""

    artifact.binding(binding_id)  # validates the requested primary key
    for event in reversed(artifact.review_events):
        if event.binding_id == binding_id:
            return event
    return None


def review_history(artifact: CardArtifact, binding_id: str) -> tuple[ReviewEvent, ...]:
    artifact.binding(binding_id)
    return tuple(
        event for event in artifact.review_events if event.binding_id == binding_id
    )


def effective_binding(artifact: CardArtifact, binding_id: str) -> EffectiveBinding:
    """Fold review events without mutating or replacing the original binding."""

    binding = artifact.binding(binding_id)
    field_path = binding.field_path
    value: Any = binding.proposed_value
    claim_entity = binding.claim_entity
    relation = binding.relation_to_target
    benchmark_scope = binding.benchmark_scope
    origin = binding.assignment_origin
    action = binding.verifier_action
    reason = binding.verifier_reason
    last_event: ReviewEvent | None = None

    for event in artifact.review_events:
        if event.binding_id != binding_id:
            continue
        action = event.action
        reason = event.reason_code
        last_event = event
        if event.action is VerifierAction.REASSIGN:
            if event.field_path is not None:
                field_path = event.field_path
            if event.corrected_value_set:
                value = event.corrected_value
            if event.claim_entity is not None:
                claim_entity = event.claim_entity
            if event.relation_to_target is not None:
                relation = event.relation_to_target
            if event.benchmark_scope is not None:
                benchmark_scope = event.benchmark_scope
            origin = AssignmentOrigin.HUMAN_CORRECTED

    effective = EffectiveBinding(
        binding=binding,
        field_path=field_path,
        value=value,
        claim_entity=claim_entity,
        relation_to_target=relation,
        benchmark_scope=benchmark_scope,
        assignment_origin=origin,
        action=action,
        reason_code=reason,
        latest_event=last_event,
    )
    _validate_effective_binding(effective)
    return effective


def _validate_effective_binding(effective: EffectiveBinding) -> None:
    if not effective.included:
        return
    if effective.relation_to_target is RelationToTarget.UNKNOWN:
        raise ReviewError("an unknown relation cannot be accepted or exported")
    if effective.assignment_origin is AssignmentOrigin.UNRESOLVED:
        raise ReviewError("an unresolved assignment cannot be accepted or exported")
    if effective.relation_to_target is RelationToTarget.EXACT_TARGET:
        target = effective.binding.target
        entity = effective.claim_entity
        if entity.model_id != target.model_id:
            raise ReviewError("exact_target entity does not match the artifact target")
        if entity.revision is None:
            raise ReviewError("exact_target entity does not identify the target checkpoint")
        if entity.revision.lower() != target.resolved_revision:
            raise ReviewError("exact_target entity identifies a different checkpoint")

    target = effective.binding.target
    entity = effective.claim_entity
    if effective.relation_to_target in {
        RelationToTarget.BASE,
        RelationToTarget.DERIVATIVE,
    } and entity.model_id == target.model_id:
        distinct_revision = (
            entity.revision is not None
            and entity.revision.lower() != target.resolved_revision
        )
        if not distinct_revision:
            raise ReviewError(
                "self-referential base/derivative relation requires a distinct checkpoint"
            )

    canonical = canonical_field_path(effective.field_path)
    if canonical == "identity.model_id" and effective.value != target.model_id:
        raise ReviewError("identity.model_id must equal the artifact target model_id")
    if canonical == "identity.version" and effective.value != target.resolved_revision:
        raise ReviewError("identity.version must equal the artifact target commit")
    if canonical in LINEAGE_FIELDS:
        expected_relation, expected_value_relation = lineage_expectations(canonical)
        if effective.relation_to_target is not expected_relation:
            raise ReviewError(f"{canonical} requires relation {expected_relation.value}")
        if (
            not isinstance(effective.value, dict)
            or effective.value.get("model_id") != entity.model_id
            or effective.value.get("relation") != expected_value_relation
        ):
            raise ReviewError("lineage value must match claim entity and typed relation")
    if canonical == "evaluation.benchmark_scores":
        if effective.benchmark_scope is None:
            raise ReviewError("exported benchmark score has no benchmark scope")
        if not any(
            evidence.row_anchor is not None or evidence.structured_pointer is not None
            for evidence in effective.binding.evidence
        ):
            raise ReviewError("exported benchmark score has no row or structured anchor")
        if (
            effective.relation_to_target is RelationToTarget.EXACT_TARGET
            and effective.benchmark_scope.benchmark_id.startswith("unresolved_")
        ):
            raise ReviewError("exact-target benchmark score requires resolved scope")
        if isinstance(effective.value, dict):
            scope_values = {
                "benchmark_id": effective.benchmark_scope.benchmark_id,
                "version": effective.benchmark_scope.version,
                "subset": effective.benchmark_scope.subset,
                "split": effective.benchmark_scope.split,
                "setting": effective.benchmark_scope.setting,
            }
            for key, expected in scope_values.items():
                if key in effective.value and effective.value[key] != expected:
                    raise ReviewError(
                        f"benchmark score {key} contradicts typed benchmark scope"
                    )


def append_review_event(artifact: CardArtifact, event: ReviewEvent) -> CardArtifact:
    """Append one event, returning a newly validated immutable artifact."""

    artifact.binding(event.binding_id)
    if any(existing.event_id == event.event_id for existing in artifact.review_events):
        raise ReviewError(f"duplicate review event id: {event.event_id}")
    if artifact.review_events and event.created_at < artifact.review_events[-1].created_at:
        raise ReviewError("review event timestamp predates the append-only log tail")

    previous = latest_event(artifact, event.binding_id)
    expected_previous = previous.event_id if previous else None
    if event.supersedes_event_id is None and expected_previous is not None:
        event = event.model_copy(update={"supersedes_event_id": expected_previous})
    elif event.supersedes_event_id != expected_previous:
        raise ReviewError("event does not supersede the latest event for its binding")

    candidate = artifact.model_copy(
        update={
            "artifact_id": "",
            "review_events": artifact.review_events + (event,),
        }
    )
    # model_copy is intentionally cheap and does not revalidate in Pydantic v2.
    # Round-tripping here makes the append boundary the audit validation boundary.
    validated = CardArtifact.model_validate(candidate.model_dump(mode="python"))
    effective_binding(validated, event.binding_id)
    # A successful review command must leave an artifact that the default
    # reviewed inspector/export can actually project.
    export_reviewed_card(validated)
    return validated


def accept_binding(
    artifact: CardArtifact,
    binding_id: str,
    *,
    reason_code: str,
    actor: str = "reviewer",
    note: str | None = None,
    created_at: datetime | None = None,
) -> CardArtifact:
    """Append an accept event after checking the effective assignment."""

    current = effective_binding(artifact, binding_id)
    if current.relation_to_target is RelationToTarget.UNKNOWN:
        raise ReviewError("reassign the unknown relation before accepting it")
    if current.assignment_origin is AssignmentOrigin.UNRESOLVED:
        raise ReviewError("reassign the unresolved assignment before accepting it")
    event_data: dict[str, Any] = {
        "binding_id": binding_id,
        "action": VerifierAction.ACCEPT,
        "reason_code": reason_code,
        "actor": actor,
        "note": note,
    }
    if created_at is not None:
        event_data["created_at"] = created_at
    return append_review_event(artifact, ReviewEvent(**event_data))


def reassign_binding(
    artifact: CardArtifact,
    binding_id: str,
    *,
    reason_code: str,
    actor: str = "reviewer",
    field_path: str | None = None,
    corrected_value: Any = _UNSET,
    claim_entity: ClaimEntity | dict[str, Any] | str | None = None,
    relation_to_target: RelationToTarget | str | None = None,
    benchmark_scope: BenchmarkScope | dict[str, Any] | None = None,
    note: str | None = None,
    created_at: datetime | None = None,
) -> CardArtifact:
    """Append a human correction and make it the effective assignment."""

    artifact.binding(binding_id)
    event_data: dict[str, Any] = {
        "binding_id": binding_id,
        "action": VerifierAction.REASSIGN,
        "reason_code": reason_code,
        "actor": actor,
        "note": note,
    }
    if field_path is not None:
        event_data["field_path"] = field_path
    if corrected_value is not _UNSET:
        event_data["corrected_value"] = corrected_value
    if claim_entity is not None:
        if isinstance(claim_entity, str):
            event_data["claim_entity"] = {"model_id": claim_entity}
        else:
            event_data["claim_entity"] = claim_entity
    if relation_to_target is not None:
        event_data["relation_to_target"] = relation_to_target
    if benchmark_scope is not None:
        event_data["benchmark_scope"] = benchmark_scope
    if created_at is not None:
        event_data["created_at"] = created_at

    updated = append_review_event(artifact, ReviewEvent(**event_data))
    # A reassign is itself an includable disposition.  Reject a partial
    # correction that would still leak an unknown or unscoped assignment.
    effective_binding(updated, binding_id)
    return updated


def withhold_binding(
    artifact: CardArtifact,
    binding_id: str,
    *,
    reason_code: str,
    actor: str = "reviewer",
    note: str | None = None,
    created_at: datetime | None = None,
) -> CardArtifact:
    """Append an explicit abstention for a binding."""

    artifact.binding(binding_id)
    event_data: dict[str, Any] = {
        "binding_id": binding_id,
        "action": VerifierAction.WITHHOLD,
        "reason_code": reason_code,
        "actor": actor,
        "note": note,
    }
    if created_at is not None:
        event_data["created_at"] = created_at
    return append_review_event(artifact, ReviewEvent(**event_data))


def latest_disposition(artifact: CardArtifact, binding_id: str) -> VerifierAction:
    return effective_binding(artifact, binding_id).action


def _group_effective_bindings(
    artifact: CardArtifact,
) -> dict[str, list[EffectiveBinding]]:
    grouped: dict[str, list[EffectiveBinding]] = {}
    for binding in artifact.bindings:
        effective = effective_binding(artifact, binding.binding_id)
        if effective.included:
            canonical = canonical_field_path(effective.field_path)
            # Which non-target relations a field may carry. The family entry is the
            # composition gates' own policy, imported rather than restated: two copies of
            # this rule drifted before, and a reviewed export that refuses what generation
            # accepted means the card cannot be rendered or published at all.
            allowed_non_target_fields = {
                RelationToTarget.BASE: {
                    "lineage.base_models",
                },
                RelationToTarget.DERIVATIVE: {
                    "lineage.derivatives",
                },
                RelationToTarget.FAMILY: FAMILY_ALLOWED_FIELDS,
            }
            if (
                effective.relation_to_target is not RelationToTarget.EXACT_TARGET
                and canonical
                not in allowed_non_target_fields.get(effective.relation_to_target, set())
            ):
                raise ReviewError(
                    f"{effective.relation_to_target.value} assignment cannot be exported "
                    f"as target field {canonical}; reassign it to a compatible field or withhold it"
                )
            grouped.setdefault(canonical_field_path(effective.field_path), []).append(effective)
    return grouped


def reviewed_projection_paths(artifact: CardArtifact) -> dict[str, str]:
    """Map included binding IDs to their paths in the compact reviewed card."""

    grouped = _group_effective_bindings(artifact)
    paths: dict[str, str] = {}
    for canonical, bindings in grouped.items():
        parsed = [
            (effective, parse_field_path(effective.field_path)[1])
            for effective in bindings
        ]
        if parsed and all(len(indexes) == 1 for _, indexes in parsed):
            for projected_index, (effective, _) in enumerate(
                sorted(parsed, key=lambda item: item[1])
            ):
                paths[effective.binding.binding_id] = f"{canonical}[{projected_index}]"
        else:
            for effective, _ in parsed:
                paths[effective.binding.binding_id] = effective.field_path
    return paths


def _materialize_group(
    card: dict[str, dict[str, Any]],
    canonical: str,
    bindings: list[EffectiveBinding],
) -> None:
    parsed = [(effective, parse_field_path(effective.field_path)[1]) for effective in bindings]
    whole_values = [(effective, indexes) for effective, indexes in parsed if not indexes]
    indexed_values = [(effective, indexes) for effective, indexes in parsed if indexes]
    if whole_values and indexed_values:
        raise ReviewConflictError(
            f"{canonical} has both whole-field and indexed accepted bindings"
        )

    if whole_values:
        first = whole_values[0][0].value
        if any(effective.value != first for effective, _ in whole_values[1:]):
            raise ReviewConflictError(f"{canonical} has conflicting accepted values")
        set_field_value(card, canonical, first)
        return

    # A one-dimensional index names positions in the proposal.  Withheld rows
    # are compacted in the reviewed projection while the ledger retains their
    # original indexes, so an accepted row never leaves an invented null hole.
    if all(len(indexes) == 1 for _, indexes in indexed_values):
        by_index: dict[int, Any] = {}
        for effective, indexes in indexed_values:
            index = indexes[0]
            if index in by_index and by_index[index] != effective.value:
                raise ReviewConflictError(
                    f"{canonical}[{index}] has conflicting accepted values"
                )
            by_index[index] = effective.value
        set_field_value(card, canonical, [by_index[index] for index in sorted(by_index)])
        return

    # Nested indexes are uncommon but deterministic.  Unlike top-level score
    # rows, their shape is semantically meaningful, so gaps remain an error.
    for effective, indexes in sorted(indexed_values, key=lambda item: item[1]):
        try:
            set_field_value(card, effective.field_path, effective.value, create_missing=True)
        except (IndexError, TypeError) as exc:
            raise ReviewConflictError(
                f"cannot materialize sparse indexed path {effective.field_path}"
            ) from exc


def export_reviewed_card(artifact: CardArtifact) -> dict[str, dict[str, Any]]:
    """Project only accepted/reassigned bindings into a fresh blank v5 card."""

    reviewed = blank_card()
    grouped = _group_effective_bindings(artifact)
    order = {field_path: index for index, field_path in enumerate(CARD_FIELD_PATHS)}
    for canonical in sorted(grouped, key=order.__getitem__):
        _materialize_group(reviewed, canonical, grouped[canonical])
    if reviewed["identity"]["model_id"] != artifact.target.model_id:
        raise ReviewError("reviewed identity.model_id must equal the artifact target")
    if reviewed["identity"]["version"] != artifact.target.resolved_revision:
        raise ReviewError("reviewed identity.version must equal the artifact target commit")
    return reviewed


def export_reviewed_artifact(artifact: CardArtifact) -> CardArtifact:
    """Return the same auditable ledger with its reviewed card projection."""

    candidate = artifact.model_copy(
        update={"artifact_id": "", "card": export_reviewed_card(artifact)}
    )
    return CardArtifact.model_validate(candidate.model_dump(mode="python"))


def save_reviewed_artifact(artifact: CardArtifact, path: str | Path) -> Path:
    return save_artifact(export_reviewed_artifact(artifact), path)
