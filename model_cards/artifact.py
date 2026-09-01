"""Immutable card artifacts and deterministic projection from binding state."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any

from .bindings import binding_id_for
from .models import (
    Binding,
    Disposition,
    ReviewAction,
    ReviewEvent,
    TargetIdentity,
)
from .policy import decide_binding
from .schema import (
    CONTENT_FIELD_PATHS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    SCHEMA_VERSION,
    blank_card,
    canonical_field_path,
    get_field,
    parse_field_path,
    set_field,
    validate_core_card,
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def fold_binding(
    target: TargetIdentity,
    binding: Binding,
    events: tuple[ReviewEvent, ...],
) -> Binding:
    """Fold ordered review events over one immutable generated binding."""

    current = binding
    for event in events:
        if event.binding_id != binding.binding_id:
            continue
        if event.action is ReviewAction.WITHHOLD:
            current = replace(
                current,
                disposition=Disposition.WITHHELD,
                reason=event.reason,
            )
        elif event.action is ReviewAction.REASSIGN:
            assert event.field_path is not None
            assert event.relation is not None
            disposition, policy_reason = decide_binding(
                target=target,
                field_path=event.field_path,
                value=event.corrected_value,
                claim_entity=current.claim_entity,
                relation=event.relation,
                origin=current.origin,
                evidence=current.evidence,
            )
            current = replace(
                current,
                field_path=event.field_path,
                value=event.corrected_value,
                relation=event.relation,
                disposition=disposition,
                reason=policy_reason,
            )
        else:
            disposition, policy_reason = decide_binding(
                target=target,
                field_path=current.field_path,
                value=current.value,
                claim_entity=current.claim_entity,
                relation=current.relation,
                origin=current.origin,
                evidence=current.evidence,
            )
            if disposition is not Disposition.ACCEPTED:
                raise ValueError(
                    f"{event.event_id} cannot accept a binding that still fails policy: "
                    f"{policy_reason}"
                )
            current = replace(
                current,
                disposition=Disposition.ACCEPTED,
                reason=event.reason,
            )
    return current


@dataclass(frozen=True)
class CardArtifact:
    target: TargetIdentity
    bindings: tuple[Binding, ...]
    reviews: tuple[ReviewEvent, ...] = ()
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "bindings", tuple(self.bindings))
        object.__setattr__(self, "reviews", tuple(self.reviews))
        if not isinstance(self.target, TargetIdentity):
            raise ValueError("artifact target must be a TargetIdentity")
        if not all(isinstance(item, Binding) for item in self.bindings):
            raise ValueError("artifact bindings must be Binding records")
        if not all(isinstance(item, ReviewEvent) for item in self.reviews):
            raise ValueError("artifact reviews must be ReviewEvent records")
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"only schema version {SCHEMA_VERSION} is supported")
        identifiers = [binding.binding_id for binding in self.bindings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("binding identifiers must be unique")
        expected_sequences = list(range(1, len(self.reviews) + 1))
        if [event.sequence for event in self.reviews] != expected_sequences:
            raise ValueError("review events must form one append-only sequence")
        known = set(identifiers)
        if any(event.binding_id not in known for event in self.reviews):
            raise ValueError("review event references an unknown binding")
        for event in self.reviews:
            event.validate_integrity()

        for binding in self.bindings:
            expected_id = binding_id_for(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
                benchmark_scope=binding.benchmark_scope,
            )
            if binding.binding_id != expected_id:
                raise ValueError(f"binding identifier does not match its content: {binding.binding_id}")
            disposition, reason = decide_binding(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
            )
            if (binding.disposition, binding.reason) != (disposition, reason):
                raise ValueError(f"binding policy state is inconsistent: {binding.binding_id}")
            fold_binding(self.target, binding, self.reviews)

    def binding(self, binding_id: str) -> Binding:
        for binding in self.bindings:
            if binding.binding_id == binding_id:
                return binding
        raise KeyError(f"unknown binding: {binding_id}")

    def effective_bindings(self) -> tuple[Binding, ...]:
        self.validate_integrity()
        return tuple(fold_binding(self.target, binding, self.reviews) for binding in self.bindings)

    def validate_integrity(self) -> None:
        """Detect mutation of nested values before projection or export."""

        identifiers = [binding.binding_id for binding in self.bindings]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("binding identifiers must be unique")
        if [event.sequence for event in self.reviews] != list(range(1, len(self.reviews) + 1)):
            raise ValueError("review events must form one append-only sequence")
        known = set(identifiers)
        if any(event.binding_id not in known for event in self.reviews):
            raise ValueError("review event references an unknown binding")
        for binding in self.bindings:
            expected_id = binding_id_for(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
                benchmark_scope=binding.benchmark_scope,
            )
            if binding.binding_id != expected_id:
                raise ValueError(f"binding integrity check failed: {binding.binding_id}")
            disposition, reason = decide_binding(
                target=self.target,
                field_path=binding.field_path,
                value=binding.value,
                claim_entity=binding.claim_entity,
                relation=binding.relation,
                origin=binding.origin,
                evidence=binding.evidence,
            )
            if (binding.disposition, binding.reason) != (disposition, reason):
                raise ValueError(f"binding policy state changed: {binding.binding_id}")
            if binding.origin.value == "structured":
                if any(_canonical(item.fragment) != _canonical(binding.value) for item in binding.evidence):
                    raise ValueError(f"structured evidence mismatch: {binding.binding_id}")
        for event in self.reviews:
            event.validate_integrity()
        for binding in self.bindings:
            fold_binding(self.target, binding, self.reviews)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "target": self.target.to_dict(),
            "card": project_card(self),
            "bindings": [binding.to_dict() for binding in self.bindings],
            "reviews": [event.to_dict() for event in self.reviews],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CardArtifact":
        artifact = cls(
            schema_version=value["schema_version"],
            target=TargetIdentity.from_dict(value["target"]),
            bindings=tuple(Binding.from_dict(item) for item in value.get("bindings", [])),
            reviews=tuple(ReviewEvent.from_dict(item) for item in value.get("reviews", [])),
        )
        if "card" in value:
            validate_core_card(value["card"])
            if value["card"] != project_card(artifact):
                raise ValueError("serialized card does not match its binding projection")
        return artifact


def project_card(artifact: CardArtifact) -> dict[str, dict[str, Any]]:
    """Project accepted effective bindings once, then compute the five quality fields."""

    card = blank_card()
    effective = artifact.effective_bindings()
    accepted: dict[str, list[Binding]] = {}
    flagged: dict[str, list[dict[str, str]]] = {}

    def flag(binding: Binding, reason: str | None = None) -> None:
        flagged.setdefault(binding.field_path, []).append(
            {
                "binding_id": binding.binding_id,
                "disposition": binding.disposition.value,
                "relation": binding.relation.value,
                "reason": reason or binding.reason,
            }
        )

    for binding in effective:
        if binding.disposition is Disposition.ACCEPTED:
            accepted.setdefault(binding.field_path, []).append(binding)
        else:
            flag(binding)

    provenance: dict[str, dict[str, Any]] = {}
    blocked_bases: set[str] = set()
    shape_by_base: dict[str, set[bool]] = {}
    for field_path in accepted:
        base, indexes = parse_field_path(field_path)
        shape_by_base.setdefault(base, set()).add(bool(indexes))
    for base, shapes in shape_by_base.items():
        if len(shapes) > 1:
            blocked_bases.add(base)
            for field_path, bindings in accepted.items():
                if canonical_field_path(field_path) == base:
                    for binding in bindings:
                        flag(binding, "projection_shape_conflict")

    def path_order(item: tuple[str, list[Binding]]) -> tuple[str, tuple[int, ...]]:
        return parse_field_path(item[0])

    for field_path, bindings in sorted(accepted.items(), key=path_order):
        if canonical_field_path(field_path) in blocked_bases:
            continue
        values = {_canonical(binding.value) for binding in bindings}
        if len(values) != 1:
            for binding in bindings:
                flag(binding, "conflicting_accepted_values")
            continue
        try:
            set_field(card, field_path, bindings[0].value)
        except (IndexError, TypeError):
            for binding in bindings:
                flag(binding, "projection_index_conflict")
            continue
        provenance[field_path] = {
            "binding_ids": [binding.binding_id for binding in bindings],
            "source_ids": sorted(
                {
                    evidence.source_id
                    for binding in bindings
                    for evidence in binding.evidence
                }
            ),
        }

    missing = [path for path in CONTENT_FIELD_PATHS if get_field(card, path) == NOT_SPECIFIED]
    applicable = [path for path in CONTENT_FIELD_PATHS if get_field(card, path) != NOT_APPLICABLE]
    filled = len(applicable) - len(missing)
    coverage = round(filled / len(applicable), 4) if applicable else 1.0

    set_field(card, "provenance_and_quality.provenance", provenance)
    set_field(card, "provenance_and_quality.flagged_fields", flagged)
    set_field(card, "provenance_and_quality.missing_fields", missing)
    set_field(card, "provenance_and_quality.coverage_score", coverage)
    set_field(
        card,
        "provenance_and_quality.card_info",
        {
            "schema_version": SCHEMA_VERSION,
            "target": artifact.target.to_dict(),
            "binding_count": len(artifact.bindings),
            "review_count": len(artifact.reviews),
        },
    )
    validate_core_card(card)
    return card
