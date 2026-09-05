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
from .records import EvidenceSpan, SourceBundle, SourceFile


class CompositionError(RuntimeError):
    """The source bundle cannot be projected honestly into the card contract."""


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _bounded_context(normalized: str, start: int, end: int, cap: int = 180) -> tuple[str, str]:
    return normalized[max(0, start - cap):start], normalized[end:end + cap]


def _structured_evidence(
    bundle: SourceBundle,
    source: SourceFile,
    pointer: str,
    fragment: Any,
) -> EvidenceSpan:
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
