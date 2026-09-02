"""Runtime access to the richer private audit-card contract.

The seven-section publication contract lives in :mod:`publication_schema`.
This module remains the internal evidence-pipeline dialect so validation,
provenance, lifecycle, risk, and experimental fields do not leak into the
public Model Card schema.
"""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
import json
import re
from typing import Any, Mapping, MutableMapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from .contract import (
    CONTRACT_VERSION,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    build_contract_schema,
)


class ContractValidationError(ValueError):
    """A value does not conform to the local Model Card audit contract."""


def load_contract_schema() -> dict[str, Any]:
    """Load a fresh copy of the JSON Schema shipped inside the package."""

    resource = files("model_cards").joinpath("resources", "audit-card.schema.json")
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict):  # pragma: no cover - guarded by package tests
        raise RuntimeError("packaged Model Card contract must be a JSON object")
    return value


CONTRACT_SCHEMA = build_contract_schema()
try:
    Draft202012Validator.check_schema(CONTRACT_SCHEMA)
except SchemaError as exc:  # pragma: no cover - exercised by schema generation tests
    raise RuntimeError("packaged Model Card contract is not valid Draft 2020-12") from exc

_FORMAT_CHECKER = FormatChecker()
_CARD_VALIDATOR = Draft202012Validator(CONTRACT_SCHEMA, format_checker=_FORMAT_CHECKER)
_METADATA = CONTRACT_SCHEMA["x-model-card"]
PUBLIC_SECTIONS: tuple[str, ...] = tuple(
    key for key in CONTRACT_SCHEMA["required"] if key != "contract_version"
)
BINDABLE_SECTIONS: tuple[str, ...] = tuple(_METADATA["bindable_sections"])
COMPUTED_SECTIONS: tuple[str, ...] = tuple(_METADATA["computed_sections"])
LIST_FIELDS = frozenset(_METADATA["list_fields"])


def _section_definition(section: str) -> dict[str, Any]:
    reference = CONTRACT_SCHEMA["properties"][section]["$ref"]
    return CONTRACT_SCHEMA["$defs"][reference.rsplit("/", 1)[-1]]


SECTION_FIELDS: dict[str, tuple[str, ...]] = {
    section: tuple(_section_definition(section)["required"])
    for section in PUBLIC_SECTIONS
}
FIELD_PATHS: tuple[str, ...] = tuple(
    f"{section}.{field}"
    for section in BINDABLE_SECTIONS
    for field in SECTION_FIELDS[section]
)
FIELD_PATH_SET = frozenset(FIELD_PATHS)
CONTENT_FIELD_PATHS = FIELD_PATHS

if CONTRACT_VERSION != _METADATA["contract_version"]:
    raise RuntimeError("contract version metadata is inconsistent")
if set(BINDABLE_SECTIONS).intersection(COMPUTED_SECTIONS):
    raise RuntimeError("bindable and computed contract sections overlap")
if set(PUBLIC_SECTIONS) != set(BINDABLE_SECTIONS).union(COMPUTED_SECTIONS):
    raise RuntimeError("contract section metadata is incomplete")

_PATH_RE = re.compile(
    r"^(?P<base>[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)(?P<indexes>(?:\[(?:0|[1-9][0-9]*)\])*)$"
)
_INDEX_RE = re.compile(r"\[([0-9]+)\]")


def _error_path(error: ValidationError) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(
        f"[{item}]" if isinstance(item, int) else f".{item}"
        for item in error.absolute_path
    )


def _raise_validation(error: ValidationError, *, prefix: str = "card") -> None:
    raise ContractValidationError(
        f"{prefix} violates the Model Card contract at {_error_path(error)}: {error.message}"
    ) from error


def validate_audit_card(card: Mapping[str, Any]) -> None:
    """Validate one complete local audit card with the Draft 2020-12 contract."""

    errors = sorted(
        _CARD_VALIDATOR.iter_errors(card),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        _raise_validation(errors[0])
    if card["lifecycle"]["status"] == "generated_validated":
        checks = card["validation"]["checks"]
        for check_id in ("claim_support", "privacy"):
            check = checks[check_id]
            if check["passed"] + check["withheld"] != check["checked"]:
                raise ContractValidationError(
                    f"card lifecycle gate {check_id} outcomes do not cover checked items"
                )
        claim_support = checks["claim_support"]
        if claim_support["passed"] != claim_support["checked"] or claim_support["withheld"]:
            raise ContractValidationError(
                "card lifecycle gate claim_support must pass every included claim"
            )
        privacy = checks["privacy"]
        if privacy["checked"] < 1 or privacy["passed"] < 1:
            raise ContractValidationError(
                "card lifecycle gate privacy must report at least one passing check"
            )


def validate_public_card(card: Mapping[str, Any]) -> None:
    """Backward-compatible alias for :func:`validate_audit_card`.

    Public seven-section cards must be validated with
    :func:`model_cards.publication_schema.validate_publication_card`.
    """

    validate_audit_card(card)


def validate_complete_card(card: Mapping[str, Any]) -> None:
    """Backward-compatible name for complete local audit-card validation."""

    validate_audit_card(card)


def validate_core_card(card: Mapping[str, Any]) -> None:
    """Validate a projected local card against the same audit contract."""

    validate_audit_card(card)


def validate_field_path(field_path: str) -> str:
    """Return a canonical or one-level list-indexed bindable path."""

    match = _PATH_RE.fullmatch(field_path) if isinstance(field_path, str) else None
    if match is None:
        raise ValueError("field path must be section.field with an optional list index")
    base = match.group("base")
    if base not in FIELD_PATH_SET:
        raise ValueError(f"unknown Model Card field: {base}")
    indexes = _INDEX_RE.findall(match.group("indexes"))
    if indexes and base not in LIST_FIELDS:
        raise ValueError(f"field is not list-valued: {base}")
    if len(indexes) > 1:
        raise ValueError("Model Card list items use exactly one index")
    return field_path


def parse_field_path(field_path: str) -> tuple[str, tuple[int, ...]]:
    validate_field_path(field_path)
    match = _PATH_RE.fullmatch(field_path)
    assert match is not None
    return match.group("base"), tuple(int(value) for value in _INDEX_RE.findall(field_path))


def canonical_field_path(field_path: str) -> str:
    return parse_field_path(field_path)[0]


def _property_schema(base: str) -> dict[str, Any]:
    section, field = base.split(".", 1)
    return _section_definition(section)["properties"][field]


def _list_item_schema(base: str) -> dict[str, Any]:
    property_schema = _property_schema(base)
    for option in property_schema.get("anyOf", []):
        if option.get("type") == "array":
            return option["items"]
    raise RuntimeError(f"contract list metadata is inconsistent for {base}")


def _validator_for(schema: dict[str, Any]) -> Draft202012Validator:
    wrapped = {
        "$schema": CONTRACT_SCHEMA["$schema"],
        "$defs": CONTRACT_SCHEMA["$defs"],
        **deepcopy(schema),
    }
    return Draft202012Validator(wrapped, format_checker=_FORMAT_CHECKER)


def validate_field_value(field_path: str, value: Any) -> None:
    """Validate a whole bindable field or one indexed list item from the contract."""

    base, indexes = parse_field_path(field_path)
    schema = _list_item_schema(base) if indexes else _property_schema(base)
    error = next(_validator_for(schema).iter_errors(value), None)
    if error is not None:
        _raise_validation(error, prefix=field_path)


def blank_card(*, fill: Any = NOT_SPECIFIED) -> dict[str, Any]:
    """Return a fresh card-shaped projection using schema-declared defaults."""

    card: dict[str, Any] = {"contract_version": CONTRACT_VERSION}
    for section in PUBLIC_SECTIONS:
        definition = _section_definition(section)
        values: dict[str, Any] = {}
        for field in SECTION_FIELDS[section]:
            property_schema = definition["properties"][field]
            if fill == NOT_SPECIFIED and "default" in property_schema:
                values[field] = deepcopy(property_schema["default"])
            else:
                values[field] = deepcopy(fill)
        card[section] = values
    return card


def set_field(
    card: MutableMapping[str, Any],
    field_path: str,
    value: Any,
) -> None:
    """Set one bindable field on an existing card-shaped mapping."""

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
    index = indexes[0]
    if not isinstance(current, list):
        raise TypeError(f"{field_path} indexes a non-list value")
    if index < len(current):
        current[index] = deepcopy(value)
    elif index == len(current):
        current.append(deepcopy(value))
    else:
        raise IndexError(f"cannot create a gap before index {index}")


def get_field(card: Mapping[str, Any], field_path: str) -> Any:
    """Return one bindable field value."""

    base, indexes = parse_field_path(field_path)
    section, field = base.split(".", 1)
    value: Any = card[section][field]
    for index in indexes:
        if not isinstance(value, list):
            raise TypeError(f"{field_path} indexes a non-list value")
        value = value[index]
    return value
