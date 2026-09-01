"""Canonical evaluation-focused Model Card schema, version 5."""

from __future__ import annotations

from copy import deepcopy
import math
import re
from typing import Any, Mapping, MutableMapping


SCHEMA_VERSION = "5"
NOT_SPECIFIED = "Not specified"
NOT_APPLICABLE = "Not applicable"

SCHEMA_V5_SECTIONS: dict[str, tuple[str, ...]] = {
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
        "modalities",
        "model_stage",
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
    ),
    "evaluation": (
        "results_summary",
        "benchmark_scores",
        "related_model_scores",
        "human_evals",
        "safety_evals",
        "evaluation_sources",
    ),
    "links": (
        "model_card",
        "system_card",
        "tech_report",
        "code_repository",
    ),
    "provenance_and_quality": (
        "provenance",
        "flagged_fields",
        "missing_fields",
        "coverage_score",
        "card_info",
    ),
}

SCHEMA_V5_FIELD_PATHS: tuple[str, ...] = tuple(
    f"{section}.{field}"
    for section, fields in SCHEMA_V5_SECTIONS.items()
    for field in fields
)
FIELD_PATH_SET = frozenset(SCHEMA_V5_FIELD_PATHS)
CONTENT_FIELD_PATHS = tuple(
    path for path in SCHEMA_V5_FIELD_PATHS if not path.startswith("provenance_and_quality.")
)
LIST_FIELDS = frozenset(
    {
        "lineage.base_models",
        "specifications.modalities",
        "evaluation.benchmark_scores",
        "evaluation.related_model_scores",
        "evaluation.evaluation_sources",
    }
)

if len(SCHEMA_V5_FIELD_PATHS) != 38:  # pragma: no cover
    raise RuntimeError("schema v5 must contain exactly 38 fields")

_PATH_RE = re.compile(
    r"^(?P<base>[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)(?P<indexes>(?:\[(?:0|[1-9][0-9]*)\])*)$"
)
_INDEX_RE = re.compile(r"\[([0-9]+)\]")


def validate_field_path(field_path: str) -> str:
    """Return a canonical or list-indexed path, or raise if it is unknown."""

    match = _PATH_RE.fullmatch(field_path) if isinstance(field_path, str) else None
    if match is None:
        raise ValueError("field path must be section.field with optional list indexes")
    if match.group("base") not in FIELD_PATH_SET:
        raise ValueError(f"unknown schema-v5 field: {match.group('base')}")
    indexes = _INDEX_RE.findall(match.group("indexes"))
    if indexes and match.group("base") not in LIST_FIELDS:
        raise ValueError(f"field is not list-valued: {match.group('base')}")
    if len(indexes) > 1:
        raise ValueError("schema-v5 list items use exactly one index")
    return field_path


def parse_field_path(field_path: str) -> tuple[str, tuple[int, ...]]:
    """Split a validated field path into its canonical base and list indexes."""

    validate_field_path(field_path)
    match = _PATH_RE.fullmatch(field_path)
    assert match is not None
    return match.group("base"), tuple(int(value) for value in _INDEX_RE.findall(field_path))


def canonical_field_path(field_path: str) -> str:
    return parse_field_path(field_path)[0]


def blank_card(*, fill: Any = NOT_SPECIFIED) -> dict[str, dict[str, Any]]:
    """Return a complete fresh schema-v5 card."""

    return {
        section: {field: deepcopy(fill) for field in fields}
        for section, fields in SCHEMA_V5_SECTIONS.items()
    }


def _validate_list_item(field_path: str, value: Any) -> None:
    if value in (NOT_SPECIFIED, NOT_APPLICABLE):
        raise ValueError("absence sentinels apply to a whole field, not a list item")
    if field_path == "lineage.base_models":
        if not isinstance(value, dict) or set(value) != {"model_id", "relation"}:
            raise ValueError("base model items must contain model_id and relation")
        if not isinstance(value["model_id"], str) or value["model_id"].count("/") != 1:
            raise ValueError("base model item has an invalid model_id")
        if value["relation"] != "base":
            raise ValueError("base model item relation must be base")
    elif field_path == "specifications.modalities":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("modality items must be non-empty strings")
    elif field_path == "evaluation.benchmark_scores":
        if not isinstance(value, dict):
            raise ValueError("benchmark score items must be objects")
        for key in ("benchmark", "metric"):
            if not isinstance(value.get(key), str) or not value[key].strip():
                raise ValueError(f"benchmark score requires a non-empty {key}")
        score = value.get("score")
        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not math.isfinite(float(score))
        ):
            raise ValueError("benchmark score must be numeric")
        if "setting" not in value:
            raise ValueError("benchmark score requires an explicit setting")
        setting = value["setting"]
        if not (
            (isinstance(setting, str) and setting.strip())
            or (isinstance(setting, dict) and setting)
        ):
            raise ValueError("benchmark score setting must be a non-empty string or object")
    elif field_path == "evaluation.related_model_scores":
        if not isinstance(value, dict):
            raise ValueError("related model items must be objects")
    elif field_path == "evaluation.evaluation_sources":
        if not isinstance(value, str) or not value.strip():
            raise ValueError("evaluation source items must be non-empty strings")


def validate_field_value(field_path: str, value: Any) -> None:
    """Validate the concrete shape of one canonical field or indexed item."""

    base, indexes = parse_field_path(field_path)
    if indexes:
        _validate_list_item(base, value)
        return
    if value in (NOT_SPECIFIED, NOT_APPLICABLE):
        return
    if base in LIST_FIELDS:
        if not isinstance(value, list):
            raise ValueError(f"{base} must be a list or an absence sentinel")
        for item in value:
            _validate_list_item(base, item)
        return
    if base == "provenance_and_quality.provenance":
        if not isinstance(value, dict):
            raise ValueError("provenance must be an object")
        return
    if base == "provenance_and_quality.flagged_fields":
        if not isinstance(value, dict):
            raise ValueError("flagged_fields must be an object")
        return
    if base == "provenance_and_quality.missing_fields":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise ValueError("missing_fields must be a list of field paths")
        return
    if base == "provenance_and_quality.coverage_score":
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or not 0.0 <= float(value) <= 1.0
        ):
            raise ValueError("coverage_score must be between zero and one")
        return
    if base == "provenance_and_quality.card_info":
        if not isinstance(value, dict):
            raise ValueError("card_info must be an object")
        return
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{base} must be a non-empty string or an absence sentinel")


def set_field(
    card: MutableMapping[str, MutableMapping[str, Any]],
    field_path: str,
    value: Any,
) -> None:
    """Set one canonical field on an existing card."""

    base, indexes = parse_field_path(field_path)
    validate_field_value(field_path, value)
    section, field = base.split(".", 1)
    if not indexes:
        card[section][field] = deepcopy(value)
        return

    current = card[section][field]
    if current in (NOT_SPECIFIED, NOT_APPLICABLE):
        current = []
        card[section][field] = current
    for depth, index in enumerate(indexes):
        if not isinstance(current, list):
            raise TypeError(f"{field_path} indexes a non-list value")
        last = depth == len(indexes) - 1
        if index < len(current):
            if last:
                current[index] = deepcopy(value)
                return
            current = current[index]
            continue
        if index != len(current):
            raise IndexError(f"cannot create a gap before index {index}")
        if last:
            current.append(deepcopy(value))
            return
        child: list[Any] = []
        current.append(child)
        current = child


def get_field(card: Mapping[str, Mapping[str, Any]], field_path: str) -> Any:
    """Return one canonical field value."""

    base, indexes = parse_field_path(field_path)
    section, field = base.split(".", 1)
    value: Any = card[section][field]
    for index in indexes:
        if not isinstance(value, list):
            raise TypeError(f"{field_path} indexes a non-list value")
        value = value[index]
    return value


def validate_complete_card(card: Mapping[str, Mapping[str, Any]]) -> None:
    """Raise unless a card contains exactly the 38 schema-v5 fields.

    Schema v5 freezes the section and field vocabulary. Value profiles are checked
    separately because the full research generator and this lean binding core do not
    currently emit identical value shapes for every field.
    """

    if not isinstance(card, Mapping):
        raise ValueError("card must be a mapping")
    if set(card) != set(SCHEMA_V5_SECTIONS):
        raise ValueError("card sections do not match schema v5")
    for section, fields in SCHEMA_V5_SECTIONS.items():
        actual = card.get(section)
        if not isinstance(actual, Mapping) or set(actual) != set(fields):
            raise ValueError(f"card fields do not match schema v5 section {section}")


def validate_core_card(card: Mapping[str, Mapping[str, Any]]) -> None:
    """Validate the complete card and the lean core's binding value profile."""

    validate_complete_card(card)
    for section, fields in SCHEMA_V5_SECTIONS.items():
        actual = card[section]
        for field in fields:
            validate_field_value(f"{section}.{field}", actual[field])
