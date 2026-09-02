"""Deterministic Markdown rendering for agreed public Model Cards.

The renderer consumes only the seven-section publication projection.  It does
not inspect or render local evidence, validation, lifecycle, environmental, or
risk artifacts.
"""

from __future__ import annotations

from html import escape as _html_escape
import json
from pathlib import PurePosixPath
import re
from typing import Any, Mapping
from urllib.parse import quote, urlsplit

from .public_export import assert_public_projection
from .publication_contract import (
    FIELD_PATHS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    SECTION_FIELDS,
)
from .publication_schema import validate_publication_card


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MARKDOWN_SPECIAL_RE = re.compile(r"([\\`*_{}\[\]()#+.!|>\-])")
_SECTION_TITLES = {
    "identity": "Identity",
    "lineage": "Lineage",
    "specifications": "Specifications",
    "training_context": "Training Context",
    "access_and_adoption": "Access and Adoption",
    "evaluation": "Evaluation",
    "links": "Links",
}
_FIELD_TITLES = {
    "model_id": "Model ID",
    "input_output": "Input / output",
    "human_evals": "Human evaluations",
    "safety_evals": "Safety evaluations",
    "tech_report": "Technical report",
}
_LINK_FIELDS = frozenset(
    {
        "links.model_card",
        "links.system_card",
        "links.tech_report",
        "links.code_repository",
    }
)


def _markdown_text(value: Any) -> str:
    """Render one untrusted scalar without enabling Markdown or raw HTML."""

    if not isinstance(value, str):
        value = json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    escaped = _html_escape(value, quote=True)
    escaped = _MARKDOWN_SPECIAL_RE.sub(r"\\\1", escaped)
    return escaped.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def _field_title(field: str) -> str:
    return _FIELD_TITLES.get(field, field.replace("_", " ").capitalize())


def _safe_http_link(value: str) -> str | None:
    """Return a Markdown-safe HTTP(S) destination or ``None``."""

    parsed = urlsplit(value)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        return None
    # Angle-delimited Markdown destinations permit ordinary URI punctuation.
    # Encoding brackets, parentheses, whitespace, HTML delimiters, and slashes
    # in user info keeps the destination structurally inert.
    return quote(value, safe=":/?#@!$&',;=+%-._~")


def _link_value(value: str) -> str:
    label = _markdown_text(value)
    destination = _safe_http_link(value)
    if destination is None:
        return label
    return f"[{label}](<{destination}>)"


def _model_reference(value: Mapping[str, Any]) -> str:
    parts = [_markdown_text(value["model_id"])]
    relation = str(value["relation"]).replace("_", " ")
    details = [_markdown_text(relation)]
    for key in ("kind", "version"):
        if key in value:
            details.append(f"{_field_title(key)}: {_markdown_text(value[key])}")
    return f"{parts[0]} ({'; '.join(details)})"


def _regular_value(field_path: str, value: Any) -> str:
    if value == NOT_APPLICABLE:
        return _markdown_text(value)
    if field_path in _LINK_FIELDS and isinstance(value, str):
        return _link_value(value)
    if field_path in {"lineage.base_models", "lineage.derivatives"}:
        return "<br>".join(_model_reference(item) for item in value)
    if isinstance(value, list):
        return "<br>".join(_markdown_text(item) for item in value)
    return _markdown_text(value)


def _section_rows(
    section: str,
    values: Mapping[str, Any],
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for field in SECTION_FIELDS[section]:
        if section == "evaluation" and field == "benchmark_scores":
            continue
        value = values.get(field, NOT_SPECIFIED)
        if value == NOT_SPECIFIED:
            continue
        rows.append(
            (
                _field_title(field),
                _regular_value(f"{section}.{field}", value),
            )
        )
    return rows


def _render_field_table(rows: list[tuple[str, str]]) -> list[str]:
    if not rows:
        return ["_No specified fields are available in the publication data._"]
    rendered = ["| Field | Value |", "| --- | --- |"]
    rendered.extend(f"| {label} | {value} |" for label, value in rows)
    return rendered


def _render_benchmark_scores(value: Any) -> list[str]:
    if value == NOT_SPECIFIED:
        return []
    if value == NOT_APPLICABLE:
        return ["### Benchmark Scores", "", "Not applicable."]

    rendered = [
        "### Benchmark Scores",
        "",
        "| Benchmark | Metric | Score | Setting | Split |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in value:
        setting = row["setting"]
        if isinstance(setting, Mapping):
            setting = json.dumps(
                setting,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        rendered.append(
            "| "
            + " | ".join(
                (
                    _markdown_text(row["benchmark"]),
                    _markdown_text(row["metric"]),
                    _markdown_text(row["score"]),
                    _markdown_text(setting),
                    _markdown_text(row.get("split", "Not reported")),
                )
            )
            + " |"
        )
    return rendered


def _unavailable_fields(card: Mapping[str, Mapping[str, Any]]) -> list[str]:
    unavailable: list[str] = []
    for field_path in FIELD_PATHS:
        section, field = field_path.split(".", 1)
        if card[section].get(field, NOT_SPECIFIED) == NOT_SPECIFIED:
            unavailable.append(field_path)
    return unavailable


def _validate_json_filename(json_filename: str) -> str:
    if not isinstance(json_filename, str) or not json_filename:
        raise ValueError("json_filename must be a non-empty string")
    if any(ord(character) < 32 for character in json_filename):
        raise ValueError("json_filename cannot contain control characters")
    path = PurePosixPath(json_filename)
    if (
        path.is_absolute()
        or len(path.parts) != 1
        or path.name != json_filename
        or "\\" in json_filename
        or not json_filename.casefold().endswith(".json")
    ):
        raise ValueError("json_filename must name a sibling JSON file")
    return json_filename


def render_public_markdown(
    card: Mapping[str, Any],
    *,
    json_filename: str,
    json_sha256: str,
) -> str:
    """Render a source-clean publication card as deterministic Markdown.

    ``json_sha256`` must be computed by the caller from the exact bytes written
    to the sibling JSON file.  Requiring it here avoids silently hashing a
    different serialization.
    """

    validate_publication_card(card)
    assert_public_projection(card)
    filename = _validate_json_filename(json_filename)
    if not isinstance(json_sha256, str) or _SHA256_RE.fullmatch(json_sha256) is None:
        raise ValueError("json_sha256 must be a lowercase hexadecimal SHA-256")

    identity = card["identity"]
    title_value = identity.get("name", identity.get("model_id", "Model Card"))
    if title_value in {NOT_SPECIFIED, NOT_APPLICABLE}:
        title_value = identity.get("model_id", "Model Card")
    if title_value in {NOT_SPECIFIED, NOT_APPLICABLE}:
        title_value = "Model Card"

    paired_href = "./" + quote(filename, safe="-._~")
    lines = [
        f"# Model Card: {_markdown_text(title_value)}",
        "",
        (
            "> This is an automated candidate generated from public sources. "
            "It has not been human-reviewed or released as an official model card."
        ),
        "",
        f"Paired JSON: [{_markdown_text(filename)}](<{paired_href}>)<br>",
        f"SHA-256: `{json_sha256}`",
    ]

    for section in SECTION_FIELDS:
        lines.extend(["", f"## {_SECTION_TITLES[section]}", ""])
        lines.extend(_render_field_table(_section_rows(section, card[section])))
        if section == "evaluation":
            benchmark_scores = card[section].get("benchmark_scores", NOT_SPECIFIED)
            benchmark_lines = _render_benchmark_scores(benchmark_scores)
            if benchmark_lines:
                lines.extend(["", *benchmark_lines])

    unavailable = _unavailable_fields(card)
    lines.extend(["", "---", ""])
    if unavailable:
        rendered_paths = ", ".join(f"`{field_path}`" for field_path in unavailable)
        lines.append(
            "Unavailable agreed fields (not specified in the publication data): "
            + rendered_paths
            + "."
        )
    else:
        lines.append("Unavailable agreed fields: none.")
    return "\n".join(lines) + "\n"


__all__ = ["render_public_markdown"]
