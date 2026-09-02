"""Validation and field helpers for the agreed public publication contract."""

from __future__ import annotations

from copy import deepcopy
from importlib.resources import files
import json
import re
from typing import Any, Mapping, MutableMapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from .publication_contract import (
    FIELD_PATHS,
    FIELD_PATH_SET,
    LIST_FIELDS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    PUBLICATION_SECTIONS,
    SECTION_FIELDS,
    build_publication_schema,
)


class PublicationValidationError(ValueError):
    """A value does not conform to the agreed public publication contract."""


def load_publication_schema() -> dict[str, Any]:
    """Load a fresh copy of the seven-section schema shipped in the package."""

    resource = files("model_cards").joinpath("resources", "model-card.schema.json")
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict):  # pragma: no cover - guarded by package tests
        raise RuntimeError("packaged publication schema must be a JSON object")
    return value


PUBLICATION_SCHEMA = load_publication_schema()
try:
    Draft202012Validator.check_schema(PUBLICATION_SCHEMA)
except SchemaError as exc:  # pragma: no cover - guarded by focused schema tests
    raise RuntimeError("publication contract is not valid Draft 2020-12") from exc

_FORMAT_CHECKER = FormatChecker()
_CARD_VALIDATOR = Draft202012Validator(
    PUBLICATION_SCHEMA,
    format_checker=_FORMAT_CHECKER,
)
_PATH_RE = re.compile(
    r"^(?P<base>[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)(?P<index>\[(?:0|[1-9][0-9]*)\])?$"
)


def _error_path(error: ValidationError) -> str:
    if not error.absolute_path:
        return "$"
    return "$" + "".join(
        f"[{item}]" if isinstance(item, int) else f".{item}"
        for item in error.absolute_path
    )


def _raise_validation(error: ValidationError, *, prefix: str = "card") -> None:
    raise PublicationValidationError(
        f"{prefix} violates the publication contract at {_error_path(error)}: {error.message}"
    ) from error


def validate_publication_card(card: Mapping[str, Any]) -> None:
    """Validate one seven-section public Model Card."""

    errors = sorted(
        _CARD_VALIDATOR.iter_errors(card),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    if errors:
        _raise_validation(errors[0])


def validate_field_path(field_path: str) -> str:
    """Return a canonical or one-level list-indexed publication field path."""

    match = _PATH_RE.fullmatch(field_path) if isinstance(field_path, str) else None
    if match is None:
        raise ValueError("field path must be section.field with an optional list index")
    base = match.group("base")
    if base not in FIELD_PATH_SET:
        raise ValueError(f"unknown publication field: {base}")
    if match.group("index") and base not in LIST_FIELDS:
        raise ValueError(f"field is not list-valued: {base}")
    return field_path


def parse_field_path(field_path: str) -> tuple[str, tuple[int, ...]]:
    """Split a validated field path into its canonical base and list index."""

    validate_field_path(field_path)
    match = _PATH_RE.fullmatch(field_path)
    assert match is not None
    index = match.group("index")
    return match.group("base"), (() if index is None else (int(index[1:-1]),))


def canonical_field_path(field_path: str) -> str:
    """Return the non-indexed form of a publication field path."""

    return parse_field_path(field_path)[0]


def _section_definition(section: str) -> dict[str, Any]:
    return PUBLICATION_SCHEMA["$defs"][section]


def _property_schema(base: str) -> dict[str, Any]:
    section, field = base.split(".", 1)
    return _section_definition(section)["properties"][field]


def _list_item_schema(base: str) -> dict[str, Any]:
    for option in _property_schema(base).get("anyOf", []):
        if option.get("type") == "array":
            return option["items"]
    raise RuntimeError(f"publication list metadata is inconsistent for {base}")


def _validator_for(schema: dict[str, Any]) -> Draft202012Validator:
    wrapped = {
        "$schema": PUBLICATION_SCHEMA["$schema"],
        "$defs": PUBLICATION_SCHEMA["$defs"],
        **deepcopy(schema),
    }
    return Draft202012Validator(wrapped, format_checker=_FORMAT_CHECKER)


def validate_field_value(field_path: str, value: Any) -> None:
    """Validate a whole field or an indexed list item against the contract."""

    base, indexes = parse_field_path(field_path)
    schema = _list_item_schema(base) if indexes else _property_schema(base)
    error = next(_validator_for(schema).iter_errors(value), None)
    if error is not None:
        _raise_validation(error, prefix=field_path)


def blank_publication_card(
    *,
    include_unknown_fields: bool = False,
    fill: Any = NOT_SPECIFIED,
) -> dict[str, dict[str, Any]]:
    """Return a fresh publication card with all seven sections.

    Fields are omitted by default so unknown data does not create a wall of
    placeholders.  ``include_unknown_fields=True`` creates the fully expanded
    shape and validates ``fill`` independently for every field.
    """

    card: dict[str, dict[str, Any]] = {
        section: {} for section in PUBLICATION_SECTIONS
    }
    if not include_unknown_fields:
        return card
    for field_path in FIELD_PATHS:
        validate_field_value(field_path, fill)
        section, field = field_path.split(".", 1)
        card[section][field] = deepcopy(fill)
    return card


def set_field(
    card: MutableMapping[str, MutableMapping[str, Any]],
    field_path: str,
    value: Any,
) -> None:
    """Set one publication field, including one append-or-replace list item."""

    base, indexes = parse_field_path(field_path)
    validate_field_value(field_path, value)
    section, field = base.split(".", 1)
    section_value = card.get(section)
    if not isinstance(section_value, MutableMapping):
        raise TypeError(f"publication section is missing or is not an object: {section}")
    if not indexes:
        section_value[field] = deepcopy(value)
        return

    current = section_value.get(field, NOT_SPECIFIED)
    if current in (NOT_SPECIFIED, NOT_APPLICABLE):
        current = []
        section_value[field] = current
    if not isinstance(current, list):
        raise TypeError(f"{field_path} indexes a non-list value")
    index = indexes[0]
    if index < len(current):
        current[index] = deepcopy(value)
    elif index == len(current):
        current.append(deepcopy(value))
    else:
        raise IndexError(f"cannot create a gap before index {index}")


_MISSING = object()


def get_field(
    card: Mapping[str, Mapping[str, Any]],
    field_path: str,
    default: Any = _MISSING,
) -> Any:
    """Return one field value, optionally returning ``default`` when omitted."""

    base, indexes = parse_field_path(field_path)
    section, field = base.split(".", 1)
    try:
        value: Any = card[section][field]
    except KeyError:
        if default is not _MISSING:
            return default
        raise
    for index in indexes:
        if not isinstance(value, list):
            raise TypeError(f"{field_path} indexes a non-list value")
        value = value[index]
    return value


def publication_coverage(card: Mapping[str, Any]) -> float:
    """Return deterministic specified-field coverage over the agreed contract."""

    validate_publication_card(card)
    filled = 0
    for field_path in FIELD_PATHS:
        value = get_field(card, field_path, NOT_SPECIFIED)
        if value not in (NOT_SPECIFIED, NOT_APPLICABLE):
            filled += 1
    return round(filled / len(FIELD_PATHS), 6)
