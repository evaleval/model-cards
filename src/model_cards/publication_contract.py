"""Canonical schema builder for the agreed public Model Card shape.

This module deliberately describes only the evaluation-focused fields agreed
for publication, plus the risks section added on 2026-09-06: AI Risk Atlas
entries selected for the checkpoint from what the card itself says, the way
the benchmark cards carry possible_risks.  Evidence, validation, lifecycle and
environmental records belong to local audit artifacts rather than this public
contract.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


NOT_SPECIFIED = "Not specified"
NOT_APPLICABLE = "Not applicable"

SECTION_FIELDS: dict[str, tuple[str, ...]] = {
    "identity": (
        "model_id",
        "name",
        "developed_by",
        "model_type",
        "license",
        "release_date",
        "version",
        "summary",
    ),
    "lineage": (
        "base_models",
        "model_family",
        "derivatives",
    ),
    "specifications": (
        "architecture_type",
        "num_parameters",
        "context_length",
        "precision",
        "model_size",
        "input_output",
    ),
    "training_context": (
        "training_data",
        "training_data_size",
        "data_cutoff",
        "adaptations",
    ),
    "access_and_adoption": (
        "access_type",
        "downloads",
        "likes",
    ),
    "evaluation": (
        "results_summary",
        "benchmark_scores",
        "human_evals",
        "safety_evals",
    ),
    "links": (
        "model_card",
        "system_card",
        "tech_report",
        "code_repository",
        "citation",
    ),
    "risks": (
        "possible_risks",
    ),
}

PUBLICATION_SECTIONS: tuple[str, ...] = tuple(SECTION_FIELDS)
FIELD_PATHS: tuple[str, ...] = tuple(
    f"{section}.{field}"
    for section, fields in SECTION_FIELDS.items()
    for field in fields
)
FIELD_PATH_SET = frozenset(FIELD_PATHS)
LIST_FIELDS = frozenset(
    {
        "lineage.base_models",
        "lineage.derivatives",
        "specifications.input_output",
        "evaluation.benchmark_scores",
        "risks.possible_risks",
    }
)

if len(FIELD_PATHS) != 34:  # pragma: no cover - protects the agreed boundary
    raise RuntimeError("the agreed publication contract must contain exactly 34 fields")


def _absence_or(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "anyOf": [
            {"enum": [NOT_SPECIFIED, NOT_APPLICABLE]},
            deepcopy(schema),
        ]
    }


def _text() -> dict[str, Any]:
    return _absence_or({"type": "string", "minLength": 1, "pattern": "\\S"})


def _link() -> dict[str, Any]:
    return _absence_or({"type": "string", "format": "uri", "minLength": 1})


def _list(item_schema: dict[str, Any]) -> dict[str, Any]:
    return _absence_or(
        {
            "type": "array",
            "items": deepcopy(item_schema),
            "minItems": 1,
            "uniqueItems": True,
        }
    )


def _section(
    fields: tuple[str, ...],
    properties: dict[str, Any],
) -> dict[str, Any]:
    if set(fields) != set(properties):
        raise RuntimeError("publication section fields and properties diverged")
    return {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }


def build_publication_schema() -> dict[str, Any]:
    """Build the neutral Draft 2020-12 public publication schema."""

    model_id = {
        "type": "string",
        "pattern": "^[^/@\\s]+(?:/[^/@\\s]+)+$",
    }
    model_reference = {
        "type": "object",
        "required": ["model_id", "relation"],
        "properties": {
            "model_id": deepcopy(model_id),
            "relation": {"enum": ["base_model", "derivative_model"]},
            "kind": {"type": "string", "minLength": 1, "pattern": "\\S"},
            "version": {"type": "string", "minLength": 1, "pattern": "\\S"},
        },
        "additionalProperties": False,
    }
    possible_risk = {
        "type": "object",
        "required": ["category", "description"],
        "properties": {
            "category": {"type": "string", "minLength": 1, "pattern": "\\S"},
            "description": {"type": "string", "minLength": 1, "pattern": "\\S"},
            "url": {
                "anyOf": [
                    {"type": "string", "format": "uri", "minLength": 1},
                    {"type": "null"},
                ]
            },
            "justification": {"type": "string", "minLength": 1, "pattern": "\\S"},
        },
        "additionalProperties": False,
    }
    benchmark_score = {
        "type": "object",
        "required": ["benchmark", "metric", "score", "setting"],
        "properties": {
            "benchmark": {"type": "string", "minLength": 1, "pattern": "\\S"},
            "metric": {"type": "string", "minLength": 1, "pattern": "\\S"},
            "score": {
                "anyOf": [
                    {"type": "number"},
                    {"type": "string", "minLength": 1, "pattern": "\\S"},
                ]
            },
            # Keep the publication boundary closed.  A free-form object here
            # would let arbitrary audit structures hide below an otherwise
            # schema-valid benchmark row.
            "setting": {"type": "string", "minLength": 1, "pattern": "\\S"},
            "split": {"type": "string", "minLength": 1, "pattern": "\\S"},
        },
        "additionalProperties": False,
    }

    definitions: dict[str, Any] = {
        "modelReference": model_reference,
        "baseModelReference": {
            "allOf": [
                {"$ref": "#/$defs/modelReference"},
                {"properties": {"relation": {"const": "base_model"}}},
            ]
        },
        "derivativeModelReference": {
            "allOf": [
                {"$ref": "#/$defs/modelReference"},
                {"properties": {"relation": {"const": "derivative_model"}}},
            ]
        },
        "benchmarkScore": benchmark_score,
        "possibleRisk": possible_risk,
        "identity": _section(
            SECTION_FIELDS["identity"],
            {
                "model_id": _absence_or(model_id),
                "name": _text(),
                "developed_by": _text(),
                "model_type": _text(),
                "license": _text(),
                "release_date": _text(),
                "version": _text(),
                "summary": _text(),
            },
        ),
        "lineage": _section(
            SECTION_FIELDS["lineage"],
            {
                "base_models": _list({"$ref": "#/$defs/baseModelReference"}),
                "model_family": _text(),
                "derivatives": _list({"$ref": "#/$defs/derivativeModelReference"}),
            },
        ),
        "specifications": _section(
            SECTION_FIELDS["specifications"],
            {
                "architecture_type": _text(),
                "num_parameters": _text(),
                "context_length": _text(),
                "precision": _text(),
                "model_size": _text(),
                "input_output": _list(
                    {"type": "string", "minLength": 1, "pattern": "\\S"}
                ),
            },
        ),
        "training_context": _section(
            SECTION_FIELDS["training_context"],
            {field: _text() for field in SECTION_FIELDS["training_context"]},
        ),
        "access_and_adoption": _section(
            SECTION_FIELDS["access_and_adoption"],
            {field: _text() for field in SECTION_FIELDS["access_and_adoption"]},
        ),
        "evaluation": _section(
            SECTION_FIELDS["evaluation"],
            {
                "results_summary": _text(),
                "benchmark_scores": _list({"$ref": "#/$defs/benchmarkScore"}),
                "human_evals": _text(),
                "safety_evals": _text(),
            },
        ),
        "links": _section(
            SECTION_FIELDS["links"],
            {
                "model_card": _link(),
                "system_card": _link(),
                "tech_report": _link(),
                "code_repository": _link(),
                "citation": _text(),
            },
        ),
        "risks": _section(
            SECTION_FIELDS["risks"],
            {"possible_risks": _list({"$ref": "#/$defs/possibleRisk"})},
        ),
    }

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://raw.githubusercontent.com/evaleval/model-cards/main/schema/model-card.schema.json",
        "title": "Evaluation-focused Model Card publication contract",
        "description": (
            "The eight-section public Model Card agreed for evaluation context: the seven "
            "sections of the July contract plus a risks section holding AI Risk Atlas entries "
            "selected for the checkpoint. Private evidence, validation, lifecycle and "
            "environmental records are excluded."
        ),
        "type": "object",
        "required": list(PUBLICATION_SECTIONS),
        "properties": {
            section: {"$ref": f"#/$defs/{section}"}
            for section in PUBLICATION_SECTIONS
        },
        "additionalProperties": False,
        "$defs": definitions,
    }
