"""The public Model Card contract, as data.

The published contract is eight sections and 34 fields
(`schema/model-card.schema.json` in the public repository): the seven sections and 33
fields agreed in July, plus `risks.possible_risks` added on 2026-09-06 so the AI Risk
Atlas material the benchmark cards carry has a place on model cards too. The card the pipeline
carries internally adds one private section, `provenance_and_quality`, which holds the
generation-time ledger summary and never leaves through the public export.

Kept as data rather than a second set of Pydantic fields so the published paths stay
visible, ordered and easy to diff against the contract document.

This replaces the earlier internal schema v5. The differences, all of them contract
decisions, not code preferences: `specifications.modalities` became `input_output`;
`specifications.model_size`, `access_and_adoption.likes` and `links.citation` were
added; `specifications.model_stage`, `evaluation.related_model_scores` and
`evaluation.evaluation_sources` were dropped. The Every Eval Ever links that
`evaluation_sources` used to carry now live in the run manifest.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Mapping, MutableMapping, Sequence


SCHEMA_VERSION = "1"
NOT_SPECIFIED = "Not specified"
NOT_APPLICABLE = "Not applicable"


# One definition of the published contract, imported rather than restated. Two copies of
# a rule drifted apart twice during this build, and the contract is the one place where a
# drift is guaranteed to be invisible until a card fails to publish.
from ..publication_contract import SECTION_FIELDS as PUBLIC_SECTIONS  # noqa: E402

PRIVATE_SECTIONS: dict[str, tuple[str, ...]] = {
    "provenance_and_quality": (
        "provenance",
        "flagged_fields",
        "missing_fields",
        "coverage_score",
        "card_info",
    ),
}

CARD_SECTIONS: dict[str, tuple[str, ...]] = {**PUBLIC_SECTIONS, **PRIVATE_SECTIONS}

PUBLIC_FIELD_PATHS: tuple[str, ...] = tuple(
    f"{section}.{field}"
    for section, fields in PUBLIC_SECTIONS.items()
    for field in fields
)

CARD_FIELD_PATHS: tuple[str, ...] = tuple(
    f"{section}.{field}"
    for section, fields in CARD_SECTIONS.items()
    for field in fields
)

FIELD_PATHS = CARD_FIELD_PATHS
FIELD_PATH_SET = frozenset(CARD_FIELD_PATHS)

if len(PUBLIC_FIELD_PATHS) != 34:  # pragma: no cover - import-time invariant
    raise RuntimeError("the public contract must contain exactly 34 fields")
if len(PUBLIC_SECTIONS) != 8:  # pragma: no cover - import-time invariant
    raise RuntimeError("the public contract must contain exactly 8 sections")


_INDEXED_PATH_RE = re.compile(
    r"^(?P<base>[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)(?P<indexes>(?:\[[0-9]+\])*)$"
)
_INDEX_RE = re.compile(r"\[([0-9]+)\]")


def blank_card(*, fill: Any = NOT_SPECIFIED) -> dict[str, dict[str, Any]]:
    """Return a fresh, complete card (the seven public sections plus the private one).

    Every invocation deep-copies ``fill`` so mutable placeholder objects never
    become shared state.  The default is deliberately honest: no field is
    silently assigned a type-specific empty value that might be mistaken for a
    sourced assertion.
    """

    return {
        section: {field: deepcopy(fill) for field in fields}
        for section, fields in CARD_SECTIONS.items()
    }


def flatten_card(card: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Flatten a complete or partial nested card to canonical dotted paths."""

    flattened: dict[str, Any] = {}
    for section, fields in card.items():
        if not isinstance(fields, Mapping):
            raise TypeError(f"card section {section!r} must be a mapping")
        for field, value in fields.items():
            flattened[f"{section}.{field}"] = value
    return flattened


def validate_complete_card(card: Mapping[str, Mapping[str, Any]]) -> None:
    """Raise ``ValueError`` unless ``card`` has exactly the contract's fields."""

    if not isinstance(card, Mapping):
        raise ValueError("card must be a mapping")

    actual_sections = tuple(card)
    expected_sections = tuple(CARD_SECTIONS)
    if set(actual_sections) != set(expected_sections):
        missing = sorted(set(expected_sections) - set(actual_sections))
        extra = sorted(set(actual_sections) - set(expected_sections))
        raise ValueError(f"card sections do not match the contract; missing={missing}, extra={extra}")

    actual_paths = set(flatten_card(card))
    missing_paths = sorted(FIELD_PATH_SET - actual_paths)
    extra_paths = sorted(actual_paths - FIELD_PATH_SET)
    if missing_paths or extra_paths:
        raise ValueError(
            "card fields do not match the contract; "
            f"missing={missing_paths}, extra={extra_paths}"
        )


def parse_field_path(field_path: str) -> tuple[str, tuple[int, ...]]:
    """Parse a canonical path with optional list indexes.

    Examples are ``identity.name`` and ``evaluation.benchmark_scores[2]``.
    Indexing is kept outside the canonical path vocabulary: the canonical path
    names the field and indexes name values within that field.
    """

    if not isinstance(field_path, str):
        raise TypeError("field_path must be a string")
    match = _INDEXED_PATH_RE.fullmatch(field_path)
    if match is None:
        raise ValueError(
            "field_path must be a canonical dotted card path with optional "
            "non-negative indexes, e.g. evaluation.benchmark_scores[0]"
        )
    base = match.group("base")
    if base not in FIELD_PATH_SET:
        raise ValueError(f"unknown card field path: {base}")
    indexes = tuple(int(value) for value in _INDEX_RE.findall(match.group("indexes")))
    return base, indexes


def canonical_field_path(field_path: str) -> str:
    """Return the canonical (unindexed) card path."""

    return parse_field_path(field_path)[0]


def get_field_value(card: Mapping[str, Mapping[str, Any]], field_path: str) -> Any:
    """Read a canonical or indexed value from ``card``."""

    base, indexes = parse_field_path(field_path)
    section, field = base.split(".", 1)
    try:
        value: Any = card[section][field]
    except (KeyError, TypeError) as exc:
        raise KeyError(f"card does not contain {base}") from exc
    for index in indexes:
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise TypeError(f"{field_path} indexes a non-list value")
        value = value[index]
    return value


def set_field_value(
    card: MutableMapping[str, MutableMapping[str, Any]],
    field_path: str,
    value: Any,
    *,
    create_missing: bool = False,
) -> MutableMapping[str, MutableMapping[str, Any]]:
    """Set a canonical or indexed value and return the mutated ``card``.

    With ``create_missing=True``, an honest placeholder may become a list and
    an index exactly at the current list length may be appended.  Gaps are
    rejected, which prevents an export from silently inventing anonymous rows.
    """

    base, indexes = parse_field_path(field_path)
    section, field = base.split(".", 1)
    if section not in card or field not in card[section]:
        raise KeyError(f"card does not contain {base}")

    if not indexes:
        card[section][field] = deepcopy(value)
        return card

    current: Any = card[section][field]
    if current in (NOT_SPECIFIED, NOT_APPLICABLE) and create_missing:
        current = []
        card[section][field] = current

    for depth, index in enumerate(indexes):
        if not isinstance(current, list):
            raise TypeError(f"{field_path} indexes a non-list value")
        last = depth == len(indexes) - 1
        if index < len(current):
            if last:
                current[index] = deepcopy(value)
                return card
            current = current[index]
            continue
        if index != len(current) or not create_missing:
            raise IndexError(
                f"cannot create index {index} at depth {depth}; next valid index is {len(current)}"
            )
        if last:
            current.append(deepcopy(value))
            return card
        child: list[Any] = []
        current.append(child)
        current = child

    return card  # pragma: no cover - indexes is known non-empty


def remove_field_value(
    card: MutableMapping[str, MutableMapping[str, Any]],
    field_path: str,
    *,
    placeholder: Any = NOT_SPECIFIED,
) -> MutableMapping[str, MutableMapping[str, Any]]:
    """Remove an indexed value or reset a whole field to ``placeholder``."""

    base, indexes = parse_field_path(field_path)
    section, field = base.split(".", 1)
    if not indexes:
        card[section][field] = deepcopy(placeholder)
        return card

    parent: Any = card[section][field]
    for index in indexes[:-1]:
        if not isinstance(parent, list):
            raise TypeError(f"{field_path} indexes a non-list value")
        parent = parent[index]
    if not isinstance(parent, list):
        raise TypeError(f"{field_path} indexes a non-list value")
    parent.pop(indexes[-1])
    if not indexes[:-1] and not parent:
        card[section][field] = deepcopy(placeholder)
    return card

