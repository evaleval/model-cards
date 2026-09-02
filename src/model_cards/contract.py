"""Canonical source for the public Model Card contract.

The two checked-in JSON Schema files are generated from this module.  Runtime
code loads the packaged copy and tests require byte-for-byte parity with this
source and the repository-level public schema.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CONTRACT_VERSION = "1"
NOT_SPECIFIED = "Not specified"
NOT_APPLICABLE = "Not applicable"

BINDABLE_SECTIONS: dict[str, tuple[str, ...]] = {
    "identity": (
        "model_id",
        "name",
        "developed_by",
        "model_type",
        "license",
        "release_date",
        "revision",
        "summary",
    ),
    "lineage": ("base_models", "model_family", "derivatives"),
    "model_details": (
        "architecture_type",
        "num_parameters",
        "context_length",
        "precision",
        "model_size",
        "modalities",
        "model_stage",
        "access_type",
        "downloads",
        "likes",
        "model_card",
        "system_card",
        "technical_report",
        "code_repository",
        "citation",
    ),
    "training": ("training_data", "training_data_size", "data_cutoff", "adaptations"),
    "evaluation": (
        "results_summary",
        "benchmark_scores",
        "related_model_scores",
        "human_evals",
        "safety_evals",
        "evaluation_sources",
    ),
    "environmental_information": (
        "hardware",
        "training_time",
        "energy_consumption",
        "carbon_emissions",
        "measurement_method",
    ),
    "use_and_risk": (
        "intended_uses",
        "out_of_scope_uses",
        "limitations",
        "known_biases",
        "identified_risks",
        "mitigations",
    ),
}

COMPUTED_SECTIONS: dict[str, tuple[str, ...]] = {
    "provenance": ("source_manifest", "field_references", "generator"),
    "validation": (
        "overall_status",
        "checks",
        "flagged_fields",
        "missing_fields",
        "coverage_score",
    ),
    "lifecycle": ("status", "generated_at", "validated_at"),
}

SECTION_FIELDS = {**BINDABLE_SECTIONS, **COMPUTED_SECTIONS}
FIELD_PATHS = tuple(
    f"{section}.{field}"
    for section, fields in BINDABLE_SECTIONS.items()
    for field in fields
)
LIST_FIELDS = (
    "lineage.base_models",
    "lineage.derivatives",
    "model_details.modalities",
    "evaluation.benchmark_scores",
    "evaluation.related_model_scores",
    "evaluation.evaluation_sources",
    "use_and_risk.intended_uses",
    "use_and_risk.out_of_scope_uses",
    "use_and_risk.limitations",
    "use_and_risk.known_biases",
    "use_and_risk.identified_risks",
    "use_and_risk.mitigations",
)


def _absence_or(schema: dict[str, Any], *, default: Any = NOT_SPECIFIED) -> dict[str, Any]:
    return {
        "anyOf": [
            {"enum": [NOT_SPECIFIED, NOT_APPLICABLE]},
            deepcopy(schema),
        ],
        "default": deepcopy(default),
    }


def _text(*, default: str = NOT_SPECIFIED) -> dict[str, Any]:
    return _absence_or({"type": "string", "minLength": 1}, default=default)


def _section(
    fields: tuple[str, ...],
    properties: dict[str, Any],
) -> dict[str, Any]:
    if set(fields) != set(properties):
        raise RuntimeError("contract section fields and properties diverged")
    return {
        "type": "object",
        "required": list(fields),
        "properties": properties,
        "additionalProperties": False,
    }


def build_contract_schema() -> dict[str, Any]:
    """Build the neutral Draft 2020-12 public contract."""

    relation_values = [
        "exact_target",
        "base_model",
        "derivative_model",
        "model_family",
        "sibling_checkpoint",
        "comparison_model",
        "unknown",
    ]
    source_roles = [
        "hugging_face_metadata",
        "hugging_face_snapshot",
        "developer_report",
        "developer_code",
        "eee_index",
    ]

    identity = _section(
        BINDABLE_SECTIONS["identity"],
        {
            "model_id": {
                "type": "string",
                "pattern": "^[^/@\\s]+/[^/@\\s]+$",
                "default": NOT_SPECIFIED,
            },
            "name": _text(),
            "developed_by": _text(),
            "model_type": _text(),
            "license": _text(),
            "release_date": _text(),
            "revision": {
                "type": "string",
                "pattern": "^[0-9a-f]{40}$",
                "default": NOT_SPECIFIED,
            },
            "summary": _text(),
        },
    )
    lineage = _section(
        BINDABLE_SECTIONS["lineage"],
        {
            "base_models": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/baseModel"}, "uniqueItems": True}
            ),
            "model_family": _text(),
            "derivatives": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/modelReference"}, "uniqueItems": True}
            ),
        },
    )
    model_details = _section(
        BINDABLE_SECTIONS["model_details"],
        {
            "architecture_type": _text(),
            "num_parameters": _text(),
            "context_length": _text(),
            "precision": _text(),
            "model_size": _text(),
            "modalities": _absence_or(
                {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True}
            ),
            "model_stage": _text(),
            "access_type": _text(),
            "downloads": _text(),
            "likes": _text(),
            "model_card": _text(),
            "system_card": _text(),
            "technical_report": _text(),
            "code_repository": _text(),
            "citation": _text(),
        },
    )
    training = _section(
        BINDABLE_SECTIONS["training"],
        {field: _text() for field in BINDABLE_SECTIONS["training"]},
    )
    evaluation = _section(
        BINDABLE_SECTIONS["evaluation"],
        {
            "results_summary": _text(),
            "benchmark_scores": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/benchmarkScore"}, "uniqueItems": True}
            ),
            "related_model_scores": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/relatedModel"}, "uniqueItems": True}
            ),
            "human_evals": _text(),
            "safety_evals": _text(),
            "evaluation_sources": _absence_or(
                {"type": "array", "items": {"type": "string", "minLength": 1}, "uniqueItems": True}
            ),
        },
    )
    environmental = _section(
        BINDABLE_SECTIONS["environmental_information"],
        {field: _text() for field in BINDABLE_SECTIONS["environmental_information"]},
    )
    use_and_risk = _section(
        BINDABLE_SECTIONS["use_and_risk"],
        {
            "intended_uses": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/contextStatement"}, "uniqueItems": True}
            ),
            "out_of_scope_uses": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/contextStatement"}, "uniqueItems": True}
            ),
            "limitations": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/contextStatement"}, "uniqueItems": True}
            ),
            "known_biases": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/contextStatement"}, "uniqueItems": True}
            ),
            "identified_risks": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/risk"}, "uniqueItems": True}
            ),
            "mitigations": _absence_or(
                {"type": "array", "items": {"$ref": "#/$defs/mitigation"}, "uniqueItems": True}
            ),
        },
    )

    provenance = _section(
        COMPUTED_SECTIONS["provenance"],
        {
            "source_manifest": {
                "type": "object",
                "propertyNames": {"pattern": "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"},
                "additionalProperties": {"$ref": "#/$defs/publicSourceReference"},
                "default": {},
            },
            "field_references": {
                "type": "object",
                "propertyNames": {"$ref": "#/$defs/fieldPath"},
                "additionalProperties": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/fieldReference"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "default": {},
            },
            "generator": {"$ref": "#/$defs/generator", "default": {"name": "evaleval-model-cards"}},
        },
    )
    # Deterministic derivation provenance is additive for v1 cards: legacy
    # source-only cards remain valid, while generated taxonomy risks must
    # expose this closed record when present.
    provenance["properties"]["derivations"] = {
        "type": "object",
        "propertyNames": {
            "pattern": "^use_and_risk\\.identified_risks\\[(?:0|[1-9][0-9]*)\\]$"
        },
        "additionalProperties": {
            "type": "array",
            "items": {"$ref": "#/$defs/taxonomyRiskDerivationReference"},
            "minItems": 1,
            "maxItems": 1,
        },
    }
    validation = _section(
        COMPUTED_SECTIONS["validation"],
        {
            "overall_status": {
                "enum": ["not_run", "partial", "passed", "failed", "unavailable"],
                "default": "not_run",
            },
            "checks": {
                "type": "object",
                "propertyNames": {"pattern": "^[a-z][a-z0-9_]{1,63}$"},
                "additionalProperties": {"$ref": "#/$defs/checkSummary"},
                "default": {},
            },
            "flagged_fields": {
                "type": "object",
                "propertyNames": {"$ref": "#/$defs/fieldPath"},
                "additionalProperties": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/fieldFinding"},
                    "minItems": 1,
                },
                "default": {},
            },
            "missing_fields": {
                "type": "array",
                "items": {"$ref": "#/$defs/baseFieldPath"},
                "uniqueItems": True,
                "default": [],
            },
            "coverage_score": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.0},
        },
    )
    lifecycle = _section(
        COMPUTED_SECTIONS["lifecycle"],
        {
            "status": {
                "enum": ["generated_unreviewed", "generated_validated"],
                "default": "generated_unreviewed",
            },
            "generated_at": _absence_or({"type": "string", "format": "date-time"}),
            "validated_at": _absence_or({"type": "string", "format": "date-time"}),
        },
    )

    definitions: dict[str, Any] = {
        "baseFieldPath": {"enum": list(FIELD_PATHS)},
        "fieldPath": {
            "anyOf": [
                {"$ref": "#/$defs/baseFieldPath"},
                {
                    "type": "string",
                    "pattern": "^(?:" + "|".join(path.replace(".", "\\.") for path in LIST_FIELDS) + ")\\[(?:0|[1-9][0-9]*)\\]$",
                },
            ]
        },
        "modelReference": {
            "type": "object",
            "required": ["model_id", "relation"],
            "properties": {
                "model_id": {"type": "string", "pattern": "^[^/@\\s]+/[^/@\\s]+$"},
                "relation": {"enum": relation_values},
                "kind": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
        "baseModel": {
            "type": "object",
            "required": ["model_id", "relation"],
            "properties": {
                "model_id": {"type": "string", "pattern": "^[^/@\\s]+/[^/@\\s]+$"},
                "relation": {"const": "base_model"},
                "kind": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
        "benchmarkScore": {
            "type": "object",
            "required": ["benchmark", "metric", "score", "setting"],
            "properties": {
                "benchmark": {"type": "string", "minLength": 1},
                "metric": {"type": "string", "minLength": 1},
                "score": {"anyOf": [{"type": "number"}, {"type": "string", "minLength": 1}]},
                "setting": {
                    "anyOf": [
                        {"type": "string", "minLength": 1},
                        {"type": "object", "minProperties": 1},
                    ]
                },
                "split": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
        "relatedModel": {
            "type": "object",
            "required": ["model_id", "link"],
            "properties": {
                "model_id": {"type": "string", "pattern": "^[^/@\\s]+/[^/@\\s]+$"},
                "link": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
        "contextStatement": {
            "type": "object",
            "required": ["context_id", "description", "origin", "source_refs"],
            "properties": {
                "context_id": {"type": "string", "pattern": "^[a-z][a-z0-9._:-]{1,127}$"},
                "description": {"type": "string", "minLength": 1},
                "origin": {"enum": ["publisher_reported", "source_derived", "operator_defined"]},
                "source_refs": {"$ref": "#/$defs/sourceRefs"},
            },
            "additionalProperties": False,
        },
        "risk": {
            "type": "object",
            "required": [
                "risk_id",
                "identification_origin",
                "taxonomy",
                "name",
                "description",
                "applicability_rationale",
                "grounds",
                "source_refs",
                "mapping_provenance",
                "review_status",
                "mitigation_assessment",
                "mitigation_refs",
            ],
            "properties": {
                "risk_id": {"type": "string", "minLength": 1, "maxLength": 256},
                "identification_origin": {"enum": ["publisher_reported", "taxonomy_identified"]},
                "taxonomy": {"anyOf": [{"$ref": "#/$defs/taxonomyReference"}, {"type": "null"}]},
                "name": {"type": "string", "minLength": 1},
                "description": {"type": "string", "minLength": 1},
                "applicability_rationale": {"type": "string", "minLength": 1},
                "grounds": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/riskGround"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "source_refs": {"$ref": "#/$defs/sourceRefs"},
                "mapping_provenance": {"$ref": "#/$defs/mappingProvenance"},
                "review_status": {
                    "enum": ["generated_unreviewed", "generated_validated", "rejected"]
                },
                "mitigation_assessment": {"enum": ["linked", "none_identified", "not_applicable"]},
                "mitigation_refs": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^mitigation:[a-z0-9][a-z0-9._-]*$"},
                    "uniqueItems": True,
                },
            },
            "additionalProperties": False,
        },
        "riskGround": {
            "type": "object",
            "required": ["kind", "ref", "relevance"],
            "properties": {
                "kind": {"enum": ["card_field", "use_context"]},
                "ref": {"type": "string", "minLength": 1},
                "relevance": {"type": "string", "minLength": 1},
            },
            "additionalProperties": False,
        },
        "taxonomyReference": {
            "type": "object",
            "required": ["taxonomy_id", "name", "version", "source_url", "snapshot_sha256"],
            "properties": {
                "taxonomy_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9._-]*$"},
                "name": {"type": "string", "minLength": 1},
                "version": {"type": "string", "minLength": 1},
                "source_url": {"type": "string", "format": "uri"},
                "snapshot_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            },
            "additionalProperties": False,
        },
        "mappingProvenance": {
            "type": "object",
            "required": ["method", "tool_version", "inference_model", "inference_config_sha256"],
            "properties": {
                "method": {"enum": ["source_binding", "ai_atlas_nexus"]},
                "tool_version": {"type": ["string", "null"]},
                "inference_model": {"type": ["string", "null"]},
                "inference_config_sha256": {
                    "anyOf": [{"type": "string", "pattern": "^[0-9a-f]{64}$"}, {"type": "null"}]
                },
            },
            "additionalProperties": False,
        },
        "mitigation": {
            "type": "object",
            "required": ["mitigation_id", "description", "origin", "source_refs"],
            "properties": {
                "mitigation_id": {"type": "string", "pattern": "^mitigation:[a-z0-9][a-z0-9._-]*$"},
                "description": {"type": "string", "minLength": 1},
                "origin": {
                    "enum": [
                        "publisher_reported",
                        "taxonomy_recommended",
                        "project_recommended",
                        "operator_defined",
                    ]
                },
                "source_refs": {"$ref": "#/$defs/sourceRefs"},
            },
            "additionalProperties": False,
        },
        "sourceRefs": {
            "type": "array",
            "items": {"type": "string", "minLength": 1},
            "uniqueItems": True,
        },
        "derivationClaimInput": {
            "type": "object",
            "required": [
                "candidate_id",
                "candidate_sha256",
                "gate_record_sha256",
                "source_refs",
            ],
            "properties": {
                "candidate_id": {
                    "type": "string",
                    "pattern": "^claim-[0-9a-f]{24}$",
                },
                "candidate_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "gate_record_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "source_refs": {"$ref": "#/$defs/sourceRefs"},
            },
            "additionalProperties": False,
        },
        "taxonomyRiskDerivationReference": {
            "type": "object",
            "required": [
                "derivation_id",
                "derivation_version",
                "output_sha256",
                "risk_report_sha256",
                "risk_catalog_sha256",
                "risk_candidate_sha256",
                "applicability_decision_sha256",
                "context_sha256s",
                "input_claims",
                "supporting_source_refs",
            ],
            "properties": {
                "derivation_id": {
                    "type": "string",
                    "pattern": "^derivation-[0-9a-f]{24}$",
                },
                "derivation_version": {
                    "const": "taxonomy-risk-derivation/v1"
                },
                "output_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "risk_report_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "risk_catalog_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "risk_candidate_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "applicability_decision_sha256": {
                    "type": "string",
                    "pattern": "^[0-9a-f]{64}$",
                },
                "context_sha256s": {
                    "type": "array",
                    "items": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                    "minItems": 1,
                    "uniqueItems": True,
                },
                "input_claims": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/derivationClaimInput"},
                    "minItems": 1,
                },
                "supporting_source_refs": {"$ref": "#/$defs/sourceRefs"},
            },
            "additionalProperties": False,
        },
        "fieldReference": {
            "type": "object",
            "required": [
                "source_id",
                "source_uri",
                "source_role",
                "source_revision",
                "source_sha256",
                "locator",
                "claimed_entity",
                "relation",
            ],
            "properties": {
                "source_id": {"type": "string", "pattern": "^[a-z0-9][a-z0-9._:-]{1,127}$"},
                "source_uri": {"$ref": "#/$defs/publicSourceUri"},
                "source_role": {"enum": source_roles},
                "source_revision": {"type": "string", "minLength": 1},
                "source_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                "locator": {"$ref": "#/$defs/locator"},
                "claimed_entity": {"type": "string", "minLength": 1},
                "relation": {"enum": relation_values},
            },
            "additionalProperties": False,
        },
        "publicSourceReference": {
            "type": "object",
            "required": ["source_uri", "source_role", "source_revision", "source_sha256"],
            "properties": {
                "source_uri": {"$ref": "#/$defs/publicSourceUri"},
                "source_role": {"enum": source_roles},
                "source_revision": {"type": "string", "minLength": 1},
                "source_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            },
            "additionalProperties": False,
        },
        "publicSourceUri": {
            "type": "string",
            "format": "uri",
            "maxLength": 2048,
            "pattern": (
                "^(?:https://(?!(?:localhost|127\\.0\\.0\\.1)(?::|/|$))[^\\s]+|"
                "hf://[^\\s]+|doi:[^\\s]+|arxiv:[0-9.]+|urn:sha256:[0-9a-f]{64})$"
            ),
        },
        "locator": {
            "oneOf": [
                {
                    "type": "object",
                    "required": ["kind", "start", "end"],
                    "properties": {
                        "kind": {"const": "exact_span"},
                        "start": {"type": "integer", "minimum": 0},
                        "end": {"type": "integer", "minimum": 1},
                    },
                    "additionalProperties": False,
                },
                {
                    "type": "object",
                    "required": ["kind", "pointer"],
                    "properties": {
                        "kind": {"const": "json_pointer"},
                        "pointer": {"type": "string", "pattern": "^/(?:[^~\\r\\n]|~[01])*$"},
                    },
                    "additionalProperties": False,
                },
            ]
        },
        "generator": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9._-]{1,127}$"},
                "commit": {
                    "anyOf": [
                        {"type": "string", "pattern": "^[0-9a-f]{40}$"},
                        {"const": NOT_SPECIFIED},
                    ]
                },
                "model": {"anyOf": [{"type": "string", "minLength": 1}, {"type": "null"}]},
            },
            "additionalProperties": False,
        },
        "checkSummary": {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": {"enum": ["not_run", "completed", "partial", "failed", "unavailable"]},
                "checked": {"type": "integer", "minimum": 0},
                "passed": {"type": "integer", "minimum": 0},
                "withheld": {"type": "integer", "minimum": 0},
                "failed": {"type": "integer", "minimum": 0},
                "unavailable": {"type": "integer", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "completedGateSummary": {
            "allOf": [
                {"$ref": "#/$defs/checkSummary"},
                {
                    "type": "object",
                    "required": [
                        "status",
                        "checked",
                        "passed",
                        "withheld",
                        "failed",
                        "unavailable",
                    ],
                    "properties": {
                        "status": {"const": "completed"},
                        "failed": {"const": 0},
                        "unavailable": {"const": 0},
                    },
                },
            ]
        },
        "fieldFinding": {
            "type": "object",
            "required": ["reason"],
            "properties": {
                "binding_id": {"type": "string", "pattern": "^binding-[0-9a-f]{24}$"},
                "disposition": {"enum": ["accepted", "withheld", "rejected"]},
                "relation": {"enum": relation_values},
                "reason": {"type": "string", "pattern": "^[a-z][a-z0-9._:-]{1,127}$"},
            },
            "additionalProperties": False,
        },
    }

    properties = {
        "contract_version": {"const": CONTRACT_VERSION},
        **{
            section: {"$ref": f"#/$defs/{section}"}
            for section in SECTION_FIELDS
        },
    }
    definitions.update(
        {
            "identity": identity,
            "lineage": lineage,
            "model_details": model_details,
            "training": training,
            "evaluation": evaluation,
            "environmental_information": environmental,
            "use_and_risk": use_and_risk,
            "provenance": provenance,
            "validation": validation,
            "lifecycle": lifecycle,
        }
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "urn:evaleval:model-cards:local-audit-card:v1",
        "title": "Local Model Card audit contract",
        "description": (
            "Private evidence-pipeline contract for generated Model Card audit artifacts; "
            "this is not the seven-section publication schema."
        ),
        "$comment": (
            "Source bodies, evidence text, prompts, provider traces, review history, and local paths "
            "remain outside the public card. Application validators enforce cross-reference and privacy rules."
        ),
        "x-model-card": {
            "contract_version": CONTRACT_VERSION,
            "bindable_sections": list(BINDABLE_SECTIONS),
            "computed_sections": list(COMPUTED_SECTIONS),
            "list_fields": list(LIST_FIELDS),
        },
        "type": "object",
        "required": ["contract_version", *SECTION_FIELDS],
        "properties": properties,
        "additionalProperties": False,
        "allOf": [
            {
                "if": {
                    "properties": {
                        "lifecycle": {
                            "properties": {"status": {"const": "generated_validated"}},
                            "required": ["status"],
                        }
                    },
                    "required": ["lifecycle"],
                },
                "then": {
                    "properties": {
                        "validation": {
                            "properties": {
                                "overall_status": {"const": "passed"},
                                "checks": {
                                    "required": ["claim_support", "privacy"],
                                    "properties": {
                                        "claim_support": {
                                            "$ref": "#/$defs/completedGateSummary"
                                        },
                                        "privacy": {
                                            "$ref": "#/$defs/completedGateSummary"
                                        },
                                    },
                                },
                            }
                        }
                    }
                },
            },
            {
                "if": {
                    "properties": {
                        "lifecycle": {
                            "properties": {"status": {"const": "generated_unreviewed"}},
                            "required": ["status"],
                        }
                    },
                    "required": ["lifecycle"],
                },
                "then": {
                    "properties": {
                        "validation": {
                            "properties": {"overall_status": {"not": {"const": "passed"}}}
                        }
                    }
                },
            },
        ],
        "$defs": definitions,
    }
