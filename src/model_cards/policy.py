"""Fail-closed field, relation, and source-role policy."""

from __future__ import annotations

import re
from typing import Any

from .models import (
    BindingOrigin,
    Disposition,
    Evidence,
    RelationToTarget,
    SourceRole,
    TargetIdentity,
)
from .schema import canonical_field_path


_COMPUTED_PREFIX = "provenance_and_quality."
_STRUCTURED_IDENTITY = frozenset({"identity.model_id", "identity.version"})
_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")


def _claim_target(claim_entity: str) -> tuple[str, str | None]:
    if "@" not in claim_entity:
        return claim_entity, None
    model_id, revision = claim_entity.rsplit("@", 1)
    return model_id, revision if _REVISION_RE.fullmatch(revision) else None


def _valid_related_link(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"model_id", "link"}:
        return False
    model_id = value.get("model_id")
    link = value.get("link")
    return (
        isinstance(model_id, str)
        and model_id.count("/") == 1
        and isinstance(link, str)
        and link.startswith(("https://", "http://"))
    )


def _valid_score_row(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if not isinstance(value.get("benchmark"), str) or not value["benchmark"].strip():
        return False
    if not isinstance(value.get("metric"), str) or not value["metric"].strip():
        return False
    score = value.get("score")
    setting = value.get("setting")
    return (
        isinstance(score, (int, float))
        and not isinstance(score, bool)
        and (
            (isinstance(setting, str) and bool(setting.strip()))
            or (isinstance(setting, dict) and bool(setting))
        )
    )


def decide_binding(
    *,
    target: TargetIdentity,
    field_path: str,
    value: Any,
    claim_entity: str,
    relation: RelationToTarget,
    origin: BindingOrigin,
    evidence: tuple[Evidence, ...],
) -> tuple[Disposition, str]:
    """Return the binding disposition and stable reason code."""

    base = canonical_field_path(field_path)
    if base.startswith(_COMPUTED_PREFIX):
        return Disposition.REJECTED, "computed_field_not_bindable"
    if any(not item.verified for item in evidence):
        return Disposition.REJECTED, "quote_not_verified"
    if value in ("Not specified", "Not applicable"):
        return Disposition.REJECTED, "absence_value_not_bindable"
    if base in _STRUCTURED_IDENTITY and origin is not BindingOrigin.STRUCTURED:
        return Disposition.REJECTED, "identity_requires_structured_evidence"
    if base == "identity.model_id" and value != target.model_id:
        return Disposition.REJECTED, "target_model_id_mismatch"
    if base == "identity.version" and value != target.revision:
        return Disposition.REJECTED, "target_revision_mismatch"
    if base == "evaluation.benchmark_scores" and not _valid_score_row(value):
        return Disposition.REJECTED, "invalid_benchmark_row"

    exact_source = all(item.source_target == target for item in evidence)
    source_roles = {item.source_role for item in evidence}
    for item in evidence:
        if item.source_role in {
            SourceRole.HUGGING_FACE_METADATA,
            SourceRole.HUGGING_FACE_SNAPSHOT,
        } and item.source_revision != target.revision:
            return Disposition.REJECTED, "source_revision_mismatch"
        if (
            item.source_role is SourceRole.DEVELOPER_CODE
            and not _REVISION_RE.fullmatch(item.source_revision)
        ):
            return Disposition.REJECTED, "developer_code_revision_unresolved"

    if relation is RelationToTarget.EXACT_TARGET:
        if claim_entity != f"{target.model_id}@{target.revision}":
            return Disposition.REJECTED, "claim_entity_target_mismatch"
    elif relation is RelationToTarget.BASE_MODEL and isinstance(value, dict):
        claim_model_id, _ = _claim_target(claim_entity)
        if claim_model_id != value.get("model_id"):
            return Disposition.REJECTED, "base_claim_entity_mismatch"

    if base == "evaluation.related_model_scores" and relation is RelationToTarget.EXACT_TARGET:
        return Disposition.WITHHELD, "related_model_requires_comparison"

    if relation is RelationToTarget.EXACT_TARGET:
        if not exact_source:
            return Disposition.WITHHELD, "source_scope_not_exact"
        if SourceRole.EEE_INDEX in source_roles and base not in {
            "evaluation.evaluation_sources",
            "evaluation.related_model_scores",
        }:
            return Disposition.WITHHELD, "index_not_field_authority"
        return Disposition.ACCEPTED, "exact_target_supported"

    if relation is RelationToTarget.BASE_MODEL:
        if (
            base == "lineage.base_models"
            and origin is BindingOrigin.STRUCTURED
            and exact_source
        ):
            return Disposition.ACCEPTED, "explicit_base_relation"
        return Disposition.WITHHELD, "base_scope_not_target"

    if relation in {
        RelationToTarget.SIBLING_CHECKPOINT,
        RelationToTarget.COMPARISON_MODEL,
    }:
        if base == "evaluation.related_model_scores" and _valid_related_link(value):
            claim_model_id, claim_revision = _claim_target(claim_entity)
            if claim_model_id != value["model_id"]:
                return Disposition.REJECTED, "related_claim_entity_mismatch"
            for item in evidence:
                if item.source_role is SourceRole.EEE_INDEX:
                    if item.source_target is None or item.source_target.model_id != value["model_id"]:
                        return Disposition.REJECTED, "related_source_target_mismatch"
                    if claim_revision and item.source_target.revision != claim_revision:
                        return Disposition.REJECTED, "related_source_revision_mismatch"
            if source_roles <= {SourceRole.DEVELOPER_REPORT, SourceRole.EEE_INDEX}:
                return Disposition.ACCEPTED, "related_model_link"
        return Disposition.WITHHELD, "comparison_scope_not_target"

    if relation is RelationToTarget.MODEL_FAMILY:
        return Disposition.WITHHELD, "family_scope_not_target"
    if relation is RelationToTarget.DERIVATIVE_MODEL:
        return Disposition.WITHHELD, "derivative_scope_not_target"
    return Disposition.WITHHELD, "target_scope_unresolved"
