"""Evidence spans over a frozen source bundle.

Every binding points at bytes that are in the bundle: a normalized text span with its
offsets and structural anchor, or a JSON Pointer into a structured file with the exact
fragment it resolves to. Both are re-checkable from the artifact alone, which is what
makes a card inspectable rather than merely annotated.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

from .bridge import ComposerBridge
from .records import EvidenceSpan, SourceBundle, SourceFile, structured_document


class CompositionError(RuntimeError):
    """The source bundle cannot be projected honestly into the card contract."""


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_context(normalized: str, start: int, end: int, cap: int = 180) -> tuple[str, str]:
    return normalized[max(0, start - cap):start], normalized[end:end + cap]


def resolve_pointer(document: Any, pointer: str) -> Any:
    """Resolve an RFC 6901 JSON Pointer, raising KeyError if it does not exist."""

    if pointer in ("", "/"):
        return document
    if not pointer.startswith("/"):
        raise KeyError(pointer)
    current = document
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise KeyError(pointer)
            current = current[int(token)]
        elif isinstance(current, dict):
            if token not in current:
                raise KeyError(pointer)
            current = current[token]
        else:
            raise KeyError(pointer)
    return current


def _structured_evidence(
    bundle: SourceBundle,
    source: SourceFile,
    pointer: str,
    fragment: Any,
) -> EvidenceSpan:
    """Structured evidence whose pointer resolves in the file it names.

    A pointer written against an internal wrapper view rather than the stored file
    ("/config/architectures" for a config.json whose own root holds "architectures")
    yields a correct value with an anchor that no reader can follow. Click-through is
    the point of the pointer, so the anchor is resolved here, against the frozen bytes,
    before the span exists.
    """

    if source.content is None:
        raise CompositionError(f"source content is unavailable: {source.name}")
    try:
        document = structured_document(source.name, source.content)
    except ValueError as exc:
        raise CompositionError(str(exc)) from exc
    try:
        found = resolve_pointer(document, pointer)
    except KeyError as exc:
        raise CompositionError(
            f"structured pointer {pointer} does not resolve in {source.name}"
        ) from exc
    if found != fragment:
        raise CompositionError(
            f"structured pointer {pointer} in {source.name} resolves to a different value"
        )
    return EvidenceSpan(
        source_uri=source.source_uri,
        source_revision=bundle.target.resolved_revision,
        source_sha256=source.sha256,
        structured_pointer=pointer,
        structured_fragment=fragment,
    )


def _target_manifest_evidence(bundle: SourceBundle, pointer: str, fragment: Any) -> EvidenceSpan:
    exact = _stable_json(fragment)
    return EvidenceSpan(
        source_uri=(
            f"hf://model/{bundle.target.model_id}@{bundle.target.resolved_revision}"
        ),
        source_revision=bundle.target.resolved_revision,
        source_sha256=_digest_text(exact),
        structured_pointer=pointer,
        structured_fragment=fragment,
    )


def _text_evidence(
    bundle: SourceBundle,
    source: SourceFile,
    exact_text: str,
    bridge: ComposerBridge,
    *,
    row_anchor: str | None = None,
    verified_span: tuple[int, int] | None = None,
    table_header_override: Iterable[str] | None = None,
) -> EvidenceSpan:
    if source.content is None:
        raise CompositionError(f"source content is unavailable: {source.name}")
    normalized = bridge.normalize_ws(source.content)
    normalized_exact = bridge.normalize_ws(exact_text)
    if verified_span is None:
        start, end = bridge.verify_span(exact_text, source.content)
    else:
        start, end = verified_span
        if normalized[start:end] != normalized_exact:
            raise CompositionError("preverified evidence span does not match source")
    before, after = _bounded_context(normalized, start, end)
    anchor = bridge.structural_anchor(source.content, start)
    table_header = (
        tuple(table_header_override)
        if table_header_override is not None
        else tuple(anchor["table_header"])
    )
    return EvidenceSpan(
        source_uri=source.source_uri,
        source_revision=bundle.target.resolved_revision,
        source_sha256=source.sha256,
        exact_text=bridge.normalize_ws(exact_text),
        start_offset=start,
        end_offset=end,
        section_path=tuple(anchor["section_path"]),
        table_caption=anchor["table_caption"] or None,
        table_header=table_header or None,
        row_anchor=row_anchor,
        context_before=before,
        context_after=after,
    )
