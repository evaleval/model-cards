"""Project the private audit card into the agreed seven-section publication.

The generation pipeline keeps richer evidence, validation, lifecycle, risk, and
experimental fields in local artifacts.  This module is the only allowlisted
bridge from that internal projection to the public Model Card agreed in the
schema discussion.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .publication_contract import NOT_APPLICABLE, NOT_SPECIFIED
from .publication_schema import (
    blank_publication_card,
    publication_coverage,
    validate_publication_card,
)
from .schema import validate_public_card as validate_audit_card


_DIRECT_FIELDS: dict[str, str] = {
    "identity.model_id": "identity.model_id",
    "identity.name": "identity.name",
    "identity.developed_by": "identity.developed_by",
    "identity.model_type": "identity.model_type",
    "identity.license": "identity.license",
    "identity.release_date": "identity.release_date",
    "identity.revision": "identity.version",
    "identity.summary": "identity.summary",
    "lineage.base_models": "lineage.base_models",
    "lineage.model_family": "lineage.model_family",
    "lineage.derivatives": "lineage.derivatives",
    "model_details.num_parameters": "specifications.num_parameters",
    "model_details.context_length": "specifications.context_length",
    "model_details.model_size": "specifications.model_size",
    "training.training_data": "training_context.training_data",
    "training.training_data_size": "training_context.training_data_size",
    "training.data_cutoff": "training_context.data_cutoff",
    "training.adaptations": "training_context.adaptations",
    "model_details.access_type": "access_and_adoption.access_type",
    "model_details.downloads": "access_and_adoption.downloads",
    "model_details.likes": "access_and_adoption.likes",
    "evaluation.results_summary": "evaluation.results_summary",
    "evaluation.benchmark_scores": "evaluation.benchmark_scores",
    "evaluation.human_evals": "evaluation.human_evals",
    "evaluation.safety_evals": "evaluation.safety_evals",
    "model_details.model_card": "links.model_card",
    "model_details.system_card": "links.system_card",
    "model_details.technical_report": "links.tech_report",
    "model_details.code_repository": "links.code_repository",
    "model_details.citation": "links.citation",
}


def _get(card: Mapping[str, Any], field_path: str) -> Any:
    section, field = field_path.split(".", 1)
    section_value = card.get(section)
    if not isinstance(section_value, Mapping):
        return NOT_SPECIFIED
    return section_value.get(field, NOT_SPECIFIED)


def _put(card: dict[str, dict[str, Any]], field_path: str, value: Any) -> None:
    if value == NOT_SPECIFIED:
        return
    section, field = field_path.split(".", 1)
    card[section][field] = deepcopy(value)


def _input_output(audit_card: Mapping[str, Any]) -> list[str] | str | None:
    modalities = _get(audit_card, "model_details.modalities")
    stage = _get(audit_card, "model_details.model_stage")
    values: list[str] = []
    if isinstance(modalities, list):
        values.extend(str(item) for item in modalities if str(item).strip())
    elif modalities == NOT_APPLICABLE:
        return NOT_APPLICABLE
    if isinstance(stage, str) and stage not in {NOT_SPECIFIED, NOT_APPLICABLE}:
        values.append(f"model stage: {stage}")
    if values:
        return list(dict.fromkeys(values))
    if stage == NOT_APPLICABLE:
        return NOT_APPLICABLE
    return None


def project_publication_card(audit_card: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the exact agreed public shape from one validated local audit card.

    Unknown fields are omitted instead of expanded into dozens of placeholders.
    No audit-only top-level section can cross this allowlist.
    """

    validate_audit_card(audit_card)
    publication = blank_publication_card()
    for source_path, destination_path in _DIRECT_FIELDS.items():
        _put(publication, destination_path, _get(audit_card, source_path))
    input_output = _input_output(audit_card)
    if input_output is not None:
        _put(publication, "specifications.input_output", input_output)
    validate_publication_card(publication)
    return publication


def publication_record(card: Mapping[str, Any]) -> dict[str, Any]:
    """Return non-card display metadata computed from the agreed field set."""

    validate_publication_card(card)
    return {
        "coverage_score": publication_coverage(card),
        "field_count": 33,
        "specified_field_count": round(publication_coverage(card) * 33),
    }


__all__ = ["project_publication_card", "publication_record"]
