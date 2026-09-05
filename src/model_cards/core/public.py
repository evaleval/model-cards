"""The public projection: what leaves this pipeline, and the checks it has to pass.

A card artifact carries the seven published sections plus the private
provenance_and_quality section and the whole binding ledger. The public export is the
seven sections and nothing else, validated against the published JSON Schema, with two
guards the contract asks for:

  the projection carries no provenance keys and no private section;
  no guarded prose field reproduces a long run of a frozen source, so a "summary" that
  is really twelve words lifted out of the README is refused rather than published.

The excerpt rule is the public repository's own, ported so a card exported here is a card
that repository would accept: twelve consecutive normalized words for space-delimited
scripts, and twenty-four compact characters for scripts that do not delimit words with
whitespace, which is what the Qwen and DeepSeek sources are written in.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .schema import NOT_APPLICABLE, NOT_SPECIFIED, PUBLIC_FIELD_PATHS, PUBLIC_SECTIONS

# the packaged copy, which is what an installed wheel has
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "resources" / "model-card.schema.json"

SOURCE_EXCERPT_MIN_WORDS = 12
SOURCE_EXCERPT_MIN_COMPACT_CHARS = 24
_MIN_COMPACT_SCRIPT_CHARS = 12
GUARDED_FIELDS = frozenset({
    "identity.summary", "training_context.training_data", "training_context.adaptations",
    "evaluation.results_summary", "evaluation.human_evals", "evaluation.safety_evals",
})
_COMPACT_SCRIPT_RANGES = (
    (0x0E00, 0x0E7F), (0x0E80, 0x0EFF), (0x1000, 0x109F), (0x1100, 0x11FF),
    (0x1780, 0x17FF), (0x3040, 0x30FF), (0x3130, 0x318F), (0x31F0, 0x31FF),
    (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0xAC00, 0xD7AF), (0xF900, 0xFAFF),
)


class PublicationError(ValueError):
    """The projection cannot be published as it stands."""


def published_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def public_projection(card: Mapping[str, Mapping[str, Any]]) -> dict:
    """The seven published sections, without provenance keys or the private section."""
    return {section: {field: card[section][field] for field in fields}
            for section, fields in PUBLIC_SECTIONS.items()}


def assert_public_projection(card: Mapping[str, Any]) -> None:
    """The projection is exactly the contract: no private section, no provenance key."""
    if set(card) != set(PUBLIC_SECTIONS):
        extra = sorted(set(card) - set(PUBLIC_SECTIONS))
        missing = sorted(set(PUBLIC_SECTIONS) - set(card))
        raise PublicationError(
            f"public projection sections do not match the contract; extra={extra}, "
            f"missing={missing}")
    for section, fields in PUBLIC_SECTIONS.items():
        actual = set(card[section])
        if actual != set(fields):
            raise PublicationError(
                f"public projection field set for {section} does not match the contract; "
                f"extra={sorted(actual - set(fields))}, missing={sorted(set(fields) - actual)}")


def validate_public_card(card: Mapping[str, Any]) -> None:
    """Validate against schema/model-card.schema.json, the published contract."""
    import jsonschema

    try:
        jsonschema.validate(card, published_schema())
    except jsonschema.ValidationError as exc:
        path = ".".join(str(p) for p in exc.absolute_path) or "<root>"
        raise PublicationError(f"public card fails the published schema at {path}: "
                               f"{exc.message}") from exc


def _normalized(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "").casefold()


def _words(value: str) -> tuple:
    out, current = [], []
    for ch in _normalized(value):
        if ch.isalnum() or (current and unicodedata.category(ch).startswith("M")):
            current.append(ch)
        elif current:
            out.append("".join(current))
            current = []
    if current:
        out.append("".join(current))
    return tuple(out)


def _compact(value: str) -> str:
    out, accepts_mark = [], False
    for ch in _normalized(value):
        if ch.isalnum():
            out.append(ch)
            accepts_mark = True
        elif accepts_mark and unicodedata.category(ch).startswith("M"):
            out.append(ch)
        else:
            accepts_mark = False
    return "".join(out)


def _is_compact_script(ch: str) -> bool:
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _COMPACT_SCRIPT_RANGES)


def _compact_needles(value: str):
    compact = _compact(value)
    for offset in range(len(compact) - SOURCE_EXCERPT_MIN_COMPACT_CHARS + 1):
        needle = compact[offset:offset + SOURCE_EXCERPT_MIN_COMPACT_CHARS]
        if sum(_is_compact_script(ch) for ch in needle) >= _MIN_COMPACT_SCRIPT_CHARS:
            yield needle


def source_excerpts(card: Mapping[str, Any], source_texts: Iterable[str]) -> Dict[str, str]:
    """{guarded field: the run it reproduces} for every field that copies a source.

    Returns rather than raises, so composition can withhold the offending field and keep
    the card. assert_no_source_excerpt is the gate for a card that is already final.
    """
    found: Dict[str, str] = {}
    texts = [t for t in source_texts if t]
    if not texts:
        return found
    word_streams = [" " + " ".join(_words(t)) + " " for t in texts]
    compact_streams = [_compact(t) for t in texts]
    for path in sorted(GUARDED_FIELDS):
        section, field = path.split(".", 1)
        value = (card.get(section) or {}).get(field, NOT_SPECIFIED)
        if not isinstance(value, str) or value in (NOT_SPECIFIED, NOT_APPLICABLE):
            continue
        words = _words(value)
        for offset in range(len(words) - SOURCE_EXCERPT_MIN_WORDS + 1):
            needle = " " + " ".join(words[offset:offset + SOURCE_EXCERPT_MIN_WORDS]) + " "
            if any(needle in stream for stream in word_streams):
                found[path] = needle.strip()
                break
        if path in found:
            continue
        for needle in _compact_needles(value):
            if any(needle in stream for stream in compact_streams):
                found[path] = needle
                break
    return found


def assert_no_source_excerpt(card: Mapping[str, Any], source_texts: Iterable[str]) -> None:
    """Refuse public prose that reproduces a long run of a frozen source."""
    found = source_excerpts(card, source_texts)
    if found:
        path = sorted(found)[0]
        raise PublicationError(f"{path} reproduces a frozen-source excerpt")


def export_public(artifact, *, reviewed: bool = True) -> dict:
    """The validated, source-clean public projection of one card artifact."""
    from .review import export_reviewed_card

    card = export_reviewed_card(artifact) if reviewed else artifact.card
    projection = public_projection(card)
    assert_public_projection(projection)
    validate_public_card(projection)
    bundle = artifact.source_bundle
    assert_no_source_excerpt(projection, [f.content for f in bundle.files] if bundle else [])
    return projection


__all__ = ["PublicationError", "assert_no_source_excerpt", "assert_public_projection",
           "export_public", "public_projection", "published_schema", "source_excerpts",
           "validate_public_card"]
