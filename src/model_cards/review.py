"""Append-only review operations over immutable generated bindings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .artifact import CardArtifact, project_card
from .claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    ProseCheckerDecision,
    correct_candidate,
    evaluate_claim_gate,
)
from .models import (
    LifecycleStatus,
    RelationToTarget,
    ReviewAction,
    ReviewEvent,
    SourceDocument,
)
from .render import render_json
from .publication import project_publication_card
from .schema import NOT_SPECIFIED


def _current_review_candidate(
    artifact: CardArtifact, binding_id: str
) -> ClaimCandidate:
    """Return the immutable candidate at the tip of one review lineage."""

    binding = artifact.binding(binding_id)
    current = ClaimCandidate.from_binding(artifact.target, binding)
    by_sha256 = {
        record.content_sha256: record for record in artifact.review_gate_records
    }
    for event in artifact.reviews:
        if event.binding_id != binding_id or event.action is not ReviewAction.REASSIGN:
            continue
        record = by_sha256.get(event.gate_record_sha256 or "")
        if record is None or record.candidate.previous_candidate_id != current.candidate_id:
            raise ValueError("review candidate lineage is incomplete")
        current = record.candidate
    return current


def append_review(
    artifact: CardArtifact,
    *,
    binding_id: str,
    action: ReviewAction | str,
    reason: str,
    field_path: str | None = None,
    relation: RelationToTarget | str | None = None,
    corrected_value: Any = None,
    gate_record: ClaimGateRecord | None = None,
) -> CardArtifact:
    """Return a new artifact with one event appended; never mutate the input."""

    artifact.binding(binding_id)
    replacement_candidate_id = None
    replacement_candidate_sha256 = None
    gate_record_sha256 = None
    retained_gate_records = artifact.review_gate_records
    if ReviewAction(action) is ReviewAction.REASSIGN:
        if not isinstance(gate_record, ClaimGateRecord):
            raise ValueError("reassign requires a retained four-part claim-gate record")
        gate_record.validate_integrity()
        prior = _current_review_candidate(artifact, binding_id)
        expected = correct_candidate(
            prior,
            field_path=field_path,
            value=corrected_value,
            relation=relation,
        )
        if gate_record.candidate.to_dict() != expected.to_dict():
            raise ValueError("reassign gate record does not match the corrected candidate")
        if not gate_record.projection_eligible:
            raise ValueError("reassign candidate did not pass all four claim gates")
        replacement_candidate_id = expected.candidate_id
        replacement_candidate_sha256 = expected.content_sha256
        gate_record_sha256 = gate_record.content_sha256
        retained_gate_records = retained_gate_records + (gate_record,)
    elif gate_record is not None:
        raise ValueError("only reassign may retain a claim-gate record")
    event = ReviewEvent(
        sequence=len(artifact.reviews) + 1,
        binding_id=binding_id,
        action=action,
        reason=reason,
        field_path=field_path,
        relation=relation,
        corrected_value=corrected_value,
        replacement_candidate_id=replacement_candidate_id,
        replacement_candidate_sha256=replacement_candidate_sha256,
        gate_record_sha256=gate_record_sha256,
    )
    invalidated_candidate_id = _current_review_candidate(
        artifact, binding_id
    ).candidate_id
    retained_derivations = artifact.derivations
    if ReviewAction(action) is not ReviewAction.ACCEPT:
        retained_derivations = tuple(
            item
            for item in retained_derivations
            if not any(
                claim.candidate_id == invalidated_candidate_id
                for claim in item.input_claims
            )
            and not (
                ReviewAction(action) is ReviewAction.REASSIGN
                and item.field_path == field_path
            )
        )
    reviewed = CardArtifact(
        target=artifact.target,
        bindings=artifact.bindings,
        reviews=artifact.reviews + (event,),
        review_gate_records=retained_gate_records,
        # Any changed effective binding invalidates all card-level semantic,
        # omission, risk, and privacy results.  A separate re-audit must recreate
        # them; carrying the old status would be a false validation claim.
        validation_checks=(),
        lifecycle_status=LifecycleStatus.GENERATED_UNREVIEWED,
        generated_at=artifact.generated_at,
        validated_at=NOT_SPECIFIED,
        contract_version=artifact.contract_version,
        derivations=retained_derivations,
    )
    if artifact.publication_card is None:
        return reviewed
    before = project_publication_card(project_card(artifact))
    after = project_publication_card(project_card(reviewed))
    if before != after:
        return reviewed
    # A review that leaves the effective publication projection unchanged may
    # retain the immutable source-bound snapshot.  Changed projections still
    # fail closed and require a fresh publication rerun.
    return CardArtifact(
        target=reviewed.target,
        bindings=reviewed.bindings,
        reviews=reviewed.reviews,
        review_gate_records=reviewed.review_gate_records,
        validation_checks=reviewed.validation_checks,
        lifecycle_status=reviewed.lifecycle_status,
        generated_at=reviewed.generated_at,
        validated_at=reviewed.validated_at,
        contract_version=reviewed.contract_version,
        derivations=reviewed.derivations,
        publication_card=artifact.publication_card,
        publication_provenance=artifact.publication_provenance,
        publication_withheld_fields=artifact.publication_withheld_fields,
        publication_source_catalog_sha256=(
            artifact.publication_source_catalog_sha256
        ),
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
    sources: Iterable[SourceDocument] | Mapping[str, SourceDocument],
    checker_decisions: Iterable[ProseCheckerDecision] = (),
) -> CardArtifact:
    prior = _current_review_candidate(artifact, binding_id)
    corrected = correct_candidate(
        prior,
        field_path=field_path,
        value=corrected_value,
        relation=relation,
    )
    gate_record = evaluate_claim_gate(
        corrected,
        sources,
        checker_decisions,
    )
    return append_review(
        artifact,
        binding_id=binding_id,
        action=ReviewAction.REASSIGN,
        reason=reason,
        field_path=field_path,
        relation=relation,
        corrected_value=corrected_value,
        gate_record=gate_record,
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
