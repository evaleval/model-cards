"""Append-only review operations over immutable generated bindings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .artifact import CardArtifact
from .models import RelationToTarget, ReviewAction, ReviewEvent
from .render import render_json


def append_review(
    artifact: CardArtifact,
    *,
    binding_id: str,
    action: ReviewAction | str,
    reason: str,
    field_path: str | None = None,
    relation: RelationToTarget | str | None = None,
    corrected_value: Any = None,
) -> CardArtifact:
    """Return a new artifact with one event appended; never mutate the input."""

    artifact.binding(binding_id)
    event = ReviewEvent(
        sequence=len(artifact.reviews) + 1,
        binding_id=binding_id,
        action=action,
        reason=reason,
        field_path=field_path,
        relation=relation,
        corrected_value=corrected_value,
    )
    return CardArtifact(
        target=artifact.target,
        bindings=artifact.bindings,
        reviews=artifact.reviews + (event,),
        schema_version=artifact.schema_version,
    )


def accept_binding(artifact: CardArtifact, binding_id: str, *, reason: str) -> CardArtifact:
    return append_review(
        artifact,
        binding_id=binding_id,
        action=ReviewAction.ACCEPT,
        reason=reason,
    )


def withhold_binding(artifact: CardArtifact, binding_id: str, *, reason: str) -> CardArtifact:
    return append_review(
        artifact,
        binding_id=binding_id,
        action=ReviewAction.WITHHOLD,
        reason=reason,
    )


def reassign_binding(
    artifact: CardArtifact,
    binding_id: str,
    *,
    field_path: str,
    relation: RelationToTarget | str,
    corrected_value: Any,
    reason: str,
) -> CardArtifact:
    return append_review(
        artifact,
        binding_id=binding_id,
        action=ReviewAction.REASSIGN,
        reason=reason,
        field_path=field_path,
        relation=relation,
        corrected_value=corrected_value,
    )


def load_artifact(path: str | Path) -> CardArtifact:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("artifact root must be an object")
    return CardArtifact.from_dict(value)


def save_artifact(artifact: CardArtifact, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_json(artifact), encoding="utf-8")
    return destination
