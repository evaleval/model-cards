"""Readable Markdown and a self-contained static HTML inspector.

The inspector's point is that no value on the card is a bare assertion. Every field row
links to the bindings that produced it, each binding carries its relation to the target
and the reason it was accepted, and every field that had something withheld says so and
links to it. A reader who wants to know where a number came from clicks it and lands on
the exact quote, its offsets, and the file hash it was verified against. There is no
script in the page, so it survives being emailed, archived or opened offline.
"""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

from .records import CardArtifact, EvidenceSpan, VerifierAction
from .review import effective_binding, export_reviewed_card, review_history
from .schema import CARD_SECTIONS


def _json(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(value, ensure_ascii=False, indent=indent, sort_keys=True)


def _inline_value(value: Any) -> str:
    if isinstance(value, str) and "\n" not in value:
        return value
    return _json(value)


def _quote_markdown(text: str) -> list[str]:
    return [f"> {line}" if line else ">" for line in text.splitlines()]


def _evidence_markdown(evidence: EvidenceSpan) -> list[str]:
    lines = [
        f"- Source: <{evidence.source_uri}>",
        f"  - Revision: `{evidence.source_revision}`",
        f"  - SHA-256: `{evidence.source_sha256}`",
    ]
    if evidence.section_path:
        lines.append(f"  - Section: {' / '.join(evidence.section_path)}")
    if evidence.exact_text is not None:
        lines.append(
            "  - Exact whitespace-normalized offsets: "
            f"`{evidence.start_offset}:{evidence.end_offset}`"
        )
        lines.append("  - Exact text:")
        lines.extend(f"    {line}" for line in _quote_markdown(evidence.exact_text))
    if evidence.table_caption is not None:
        lines.append(f"  - Table caption: {evidence.table_caption}")
    if evidence.table_header is not None:
        lines.append(f"  - Table header: {_inline_value(list(evidence.table_header))}")
    if evidence.row_anchor is not None:
        lines.append(f"  - Row anchor: `{evidence.row_anchor}`")
    if evidence.structured_pointer is not None:
        lines.append(f"  - Structured pointer: `{evidence.structured_pointer}`")
        lines.append(
            f"  - Structured fragment: `{_inline_value(evidence.structured_fragment)}`"
        )
    if evidence.context_before is not None:
        lines.append(f"  - Context before: `{evidence.context_before}`")
    if evidence.context_after is not None:
        lines.append(f"  - Context after: `{evidence.context_after}`")
    if evidence.surrounding_context is not None:
        lines.append(f"  - Surrounding context: `{evidence.surrounding_context}`")
    return lines


def render_markdown(artifact: CardArtifact, *, reviewed: bool = True) -> str:
    """Render the card, bindings, evidence, and append-only review history."""

    card = export_reviewed_card(artifact) if reviewed else artifact.card
    effective = [
        effective_binding(artifact, binding.binding_id) for binding in artifact.bindings
    ]
    counts = {
        action: sum(item.action is action for item in effective)
        for action in VerifierAction
    }

    lines = [
        f"# Model Card: {artifact.target.model_id}",
        "",
        f"- Exact target: `{artifact.target.canonical_target}`",
        f"- Requested target: `{artifact.target.requested_target}`",
        f"- Schema: v{artifact.schema_version}",
        f"- Artifact ID: `{artifact.artifact_id}`",
        f"- View: {'reviewed projection' if reviewed else 'generation-time card'}",
        (
            "- Binding dispositions: "
            f"{counts[VerifierAction.ACCEPT]} accepted, "
            f"{counts[VerifierAction.REASSIGN]} reassigned, "
            f"{counts[VerifierAction.WITHHOLD]} withheld"
        ),
        "",
        "## Card",
        "",
    ]

    by_field = _bindings_by_field(artifact, {b.binding_id: e
                                             for b, e in zip(artifact.bindings, effective,
                                                             strict=True)})
    for section, fields in CARD_SECTIONS.items():
        lines.extend((f"### {section.replace('_', ' ').title()}", ""))
        for field in fields:
            path = f"{section}.{field}"
            accepted, withheld_here = by_field.get(path, ([], []))
            marks = sorted({i.relation_to_target.value for _, i in accepted})
            suffix = f"  [{', '.join(marks)}]" if marks else ""
            if withheld_here:
                suffix += f"  [{len(withheld_here)} withheld]"
            lines.append(f"- `{path}`: {_inline_value(card[section][field])}{suffix}")
        lines.append("")

    withheld_rows = [(path, b, i) for path, (_, items) in sorted(by_field.items())
                     for b, i in items]
    if withheld_rows:
        lines.extend(("## Withheld", "",
                      "Values found in the sources and not published, with the reason.", ""))
        for path, binding, item in withheld_rows:
            lines.append(f"- `{path}` ({item.relation_to_target.value}, "
                         f"`{item.reason_code}`): {_short(binding.proposed_value)} "
                         f"[`{binding.binding_id}`]")
        lines.append("")

    if artifact.source_bundle is not None:
        bundle = artifact.source_bundle
        lines.extend(
            (
                "## Frozen source bundle",
                "",
                f"- Snapshot: `{bundle.snapshot_path}`",
                f"- Retrieved: `{bundle.retrieved_at.isoformat()}`",
                f"- Offline: `{str(bundle.offline).lower()}`",
                "- Files:",
            )
        )
        for source_file in bundle.files:
            lines.append(
                f"  - `{source_file.name}` — `{source_file.sha256}`, "
                f"{source_file.size_bytes} bytes, `{source_file.media_type}`"
            )
        lines.append("")

    lines.extend(("## Evidence bindings", ""))
    if not artifact.bindings:
        lines.extend(("No binding records.", ""))

    for binding, item in zip(artifact.bindings, effective, strict=True):
        lines.extend(
            (
                f"### `{binding.field_path}` — {item.action.value}",
                "",
                f"- Binding ID: `{binding.binding_id}`",
                f"- Effective field: `{item.field_path}`",
                f"- Proposed value: `{_inline_value(binding.proposed_value)}`",
                f"- Effective value: `{_inline_value(item.value)}`",
                f"- Claim entity: `{item.claim_entity.display_name}`",
                f"- Relation to target: `{item.relation_to_target.value}`",
                f"- Assignment origin: `{item.assignment_origin.value}`",
                f"- Latest reason: `{item.reason_code}`",
            )
        )
        if item.benchmark_scope is not None:
            lines.append(
                "- Benchmark scope: `"
                + _inline_value(item.benchmark_scope.model_dump(mode="json"))
                + "`"
            )
        if binding.derivation_trace is not None:
            lines.extend(
                (
                    f"- Derivation rule: `{binding.derivation_trace.rule}`",
                    "- Derivation inputs: `"
                    + _inline_value(binding.derivation_trace.inputs)
                    + "`",
                    "- Derivation output: `"
                    + _inline_value(binding.derivation_trace.output)
                    + "`",
                )
            )
        lines.extend(("", "#### Evidence", ""))
        for evidence in binding.evidence:
            lines.extend(_evidence_markdown(evidence))
        lines.extend(("", "#### Review history", ""))
        history = review_history(artifact, binding.binding_id)
        if not history:
            lines.append("No appended review events; the generation-time disposition applies.")
        for event in history:
            correction = ""
            if event.action is VerifierAction.REASSIGN:
                changed = []
                if event.field_path is not None:
                    changed.append(f"field={event.field_path}")
                if event.corrected_value_set:
                    changed.append(f"value={_inline_value(event.corrected_value)}")
                if event.claim_entity is not None:
                    changed.append(f"entity={event.claim_entity.display_name}")
                if event.relation_to_target is not None:
                    changed.append(f"relation={event.relation_to_target.value}")
                if event.benchmark_scope is not None:
                    changed.append(
                        "scope="
                        + _inline_value(event.benchmark_scope.model_dump(mode="json"))
                    )
                correction = "; correction: " + ", ".join(changed)
            note = f"; note: {event.note}" if event.note else ""
            lines.append(
                f"- `{event.created_at.isoformat()}` `{event.event_id}` — "
                f"**{event.action.value}** by {event.actor}; "
                f"reason `{event.reason_code}`{correction}{note}"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _html_value(value: Any) -> str:
    return escape(_json(value, indent=2) if not isinstance(value, str) else value)


def _short(value: Any, cap: int = 120) -> str:
    text = value if isinstance(value, str) else _json(value)
    text = " ".join(text.split())
    return text if len(text) <= cap else text[: cap - 1] + "\u2026"


def _bindings_by_field(artifact: CardArtifact, effective: dict) -> dict:
    """{canonical field path: (accepted, withheld)} of (binding, effective) pairs."""
    out: dict = {}
    for binding in artifact.bindings:
        item = effective[binding.binding_id]
        path = (item.field_path or binding.field_path).split("[", 1)[0]
        accepted, withheld = out.setdefault(path, ([], []))
        (withheld if item.action is VerifierAction.WITHHOLD else accepted).append((binding, item))
    return out


def _field_links_html(entry) -> str:
    """The click-through cell for one field: one link per binding, with its relation."""
    accepted, withheld = entry
    if not accepted and not withheld:
        return '<span class="meta">no binding</span>'
    bits = []
    for binding, item in accepted:
        bits.append(
            f'<a href="#{escape(binding.binding_id, quote=True)}">'
            f"{escape(_evidence_label(binding))}</a> "
            f'<span class="pill">{escape(item.relation_to_target.value)}</span>')
    if withheld:
        first = withheld[0][0]
        bits.append(f'<a class="wh" href="#{escape(first.binding_id, quote=True)}">'
                    f"{len(withheld)} withheld</a>")
    return "<br>".join(bits)


def _evidence_label(binding) -> str:
    """What the reader clicks: the span's own anchor, shortened."""
    first = binding.evidence[0]
    if first.row_anchor is not None:
        return _short(first.row_anchor, 60)
    if first.exact_text is not None:
        return _short(first.exact_text, 60)
    if first.structured_pointer is not None:
        return first.structured_pointer
    return first.source_uri


def _evidence_html(evidence: EvidenceSpan) -> str:
    parts = [
        '<article class="evidence">',
        f'<p><strong>Source:</strong> <a href="{escape(evidence.source_uri, quote=True)}">'
        f"{escape(evidence.source_uri)}</a></p>",
        f"<p><strong>Revision:</strong> <code>{escape(evidence.source_revision)}</code><br>",
        f"<strong>SHA-256:</strong> <code>{escape(evidence.source_sha256)}</code></p>",
    ]
    if evidence.section_path:
        parts.append(
            f"<p><strong>Section:</strong> {escape(' / '.join(evidence.section_path))}</p>"
        )
    if evidence.exact_text is not None:
        parts.append(
            f"<p><strong>Exact whitespace-normalized offsets:</strong> "
            f"<code>{evidence.start_offset}:"
            f"{evidence.end_offset}</code></p>"
        )
        parts.append(f"<blockquote>{escape(evidence.exact_text)}</blockquote>")
    table_bits = []
    if evidence.table_caption is not None:
        table_bits.append(f"caption={evidence.table_caption}")
    if evidence.table_header is not None:
        table_bits.append(f"header={_json(list(evidence.table_header))}")
    if evidence.row_anchor is not None:
        table_bits.append(f"row={evidence.row_anchor}")
    if table_bits:
        parts.append(f"<p><strong>Table anchor:</strong> {escape('; '.join(table_bits))}</p>")
    if evidence.structured_pointer is not None:
        parts.append(
            f"<p><strong>Structured pointer:</strong> "
            f"<code>{escape(evidence.structured_pointer)}</code></p>"
        )
        parts.append(
            f"<pre>{_html_value(evidence.structured_fragment)}</pre>"
        )
    if (
        evidence.context_before is not None
        or evidence.context_after is not None
        or evidence.surrounding_context is not None
    ):
        context = {
            "before": evidence.context_before,
            "after": evidence.context_after,
            "surrounding": evidence.surrounding_context,
        }
        parts.append(f"<details><summary>Bounded context</summary><pre>{_html_value(context)}</pre></details>")
    parts.append("</article>")
    return "".join(parts)


def render_html(artifact: CardArtifact, *, reviewed: bool = True) -> str:
    """Render a self-contained, script-free static inspector."""

    card = export_reviewed_card(artifact) if reviewed else artifact.card
    effective = {
        binding.binding_id: effective_binding(artifact, binding.binding_id)
        for binding in artifact.bindings
    }
    counts = {
        action: sum(item.action is action for item in effective.values())
        for action in VerifierAction
    }

    parts = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        f"<title>Model Card — {escape(artifact.target.model_id)}</title>",
        "<style>",
        "body{font:16px/1.5 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18202a}",
        "h1,h2,h3{line-height:1.2}code,pre{font-family:ui-monospace,monospace}code{overflow-wrap:anywhere}",
        "pre,blockquote,.evidence{background:#f5f7fa;border:1px solid #d8dee8;border-radius:.4rem;padding:.8rem;white-space:pre-wrap;overflow-wrap:anywhere}",
        "table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;border-bottom:1px solid #d8dee8;padding:.45rem}",
        ".binding{border:1px solid #c9d2df;border-left:.35rem solid #607d9d;border-radius:.5rem;padding:1rem;margin:1rem 0}",
        ".accept{border-left-color:#27864b}.reassign{border-left-color:#a06a00}.withhold{border-left-color:#a53a3a}",
        ".meta{color:#4d5c6d}.pill{display:inline-block;border-radius:1rem;background:#edf1f6;padding:.15rem .55rem;margin-right:.35rem;font-size:.85em}",
        "td a{color:#22527d}a.wh{color:#a53a3a}tbody tr:target{background:#fff6d8}section.binding:target{background:#fff6d8}",
        "</style></head><body>",
        f"<h1>Model Card: {escape(artifact.target.model_id)}</h1>",
        f'<p class="meta"><strong>Exact target:</strong> <code>{escape(artifact.target.canonical_target)}</code><br>',
        f"<strong>Requested:</strong> <code>{escape(artifact.target.requested_target)}</code><br>",
        f"<strong>Artifact:</strong> <code>{escape(artifact.artifact_id)}</code> · schema v{artifact.schema_version} · ",
        f"{'reviewed projection' if reviewed else 'generation-time card'}</p>",
        '<p><span class="pill">'
        f"{counts[VerifierAction.ACCEPT]} accepted</span>"
        '<span class="pill">'
        f"{counts[VerifierAction.REASSIGN]} reassigned</span>"
        '<span class="pill">'
        f"{counts[VerifierAction.WITHHOLD]} withheld</span></p>",
        "<h2>Card</h2>",
    ]

    by_field = _bindings_by_field(artifact, effective)
    for section, fields in CARD_SECTIONS.items():
        parts.append(f"<h3>{escape(section.replace('_', ' ').title())}</h3><table>")
        parts.append("<thead><tr><th>Field</th><th>Value</th><th>Source</th></tr>"
                     "</thead><tbody>")
        for field in fields:
            path = f"{section}.{field}"
            parts.append(
                f'<tr id="field-{escape(path, quote=True)}">'
                f"<td><code>{escape(path)}</code></td>"
                f"<td><pre>{_html_value(card[section][field])}</pre></td>"
                f"<td>{_field_links_html(by_field.get(path, ([], [])))}</td></tr>"
            )
        parts.append("</tbody></table>")

    withheld = [(path, items) for path, (_, items) in sorted(by_field.items()) if items]
    parts.append("<h2>Withheld</h2>")
    if not withheld:
        parts.append("<p>Nothing was withheld for this card.</p>")
    else:
        parts.append("<p>Values the pipeline found in the sources and decided not to "
                     "publish, with the reason. They are in the ledger, not on the card.</p>")
        parts.append("<table><thead><tr><th>Field</th><th>Value</th><th>Relation</th>"
                     "<th>Reason</th></tr></thead><tbody>")
        for path, items in withheld:
            for binding, item in items:
                parts.append(
                    f"<tr><td><code>{escape(path)}</code></td>"
                    f'<td><a href="#{escape(binding.binding_id, quote=True)}">'
                    f"{escape(_short(binding.proposed_value))}</a></td>"
                    f"<td><code>{escape(item.relation_to_target.value)}</code></td>"
                    f"<td><code>{escape(item.reason_code)}</code></td></tr>")
        parts.append("</tbody></table>")

    if artifact.source_bundle is not None:
        parts.append("<h2>Frozen source bundle</h2><ul>")
        for source_file in artifact.source_bundle.files:
            parts.append(
                f"<li><code>{escape(source_file.name)}</code> — "
                f"<code>{escape(source_file.sha256)}</code>, {source_file.size_bytes} bytes, "
                f"<code>{escape(source_file.media_type)}</code></li>"
            )
        parts.append("</ul>")

    parts.append("<h2>Evidence bindings</h2>")
    if not artifact.bindings:
        parts.append("<p>No binding records.</p>")
    for binding in artifact.bindings:
        item = effective[binding.binding_id]
        parts.append(f'<section class="binding {escape(item.action.value)}" '
                     f'id="{escape(binding.binding_id, quote=True)}">')
        parts.append(
            f"<h3><code>{escape(binding.field_path)}</code> - {escape(item.action.value)} "
            f'<span class="pill">{escape(item.relation_to_target.value)}</span>'
            f'<span class="pill">{escape(item.reason_code)}</span></h3>')
        summary = {
            "binding_id": binding.binding_id,
            "effective_field": item.field_path,
            "proposed_value": binding.proposed_value,
            "effective_value": item.value,
            "claim_entity": item.claim_entity.display_name,
            "relation_to_target": item.relation_to_target.value,
            "assignment_origin": item.assignment_origin.value,
            "latest_reason": item.reason_code,
            "benchmark_scope": (
                item.benchmark_scope.model_dump(mode="json")
                if item.benchmark_scope is not None
                else None
            ),
        }
        parts.append(f"<pre>{_html_value(summary)}</pre>")
        if binding.derivation_trace is not None:
            parts.append("<h4>Deterministic derivation</h4>")
            parts.append(
                f"<pre>{_html_value(binding.derivation_trace.model_dump(mode='json'))}</pre>"
            )
        parts.append("<h4>Evidence</h4>")
        parts.extend(_evidence_html(evidence) for evidence in binding.evidence)
        parts.append("<h4>Review history</h4><ol>")
        history = review_history(artifact, binding.binding_id)
        if not history:
            parts.append("<li>No appended events; generation-time disposition applies.</li>")
        for event in history:
            parts.append(
                "<li><code>"
                + escape(event.created_at.isoformat())
                + "</code> <strong>"
                + escape(event.action.value)
                + "</strong> by "
                + escape(event.actor)
                + "; reason <code>"
                + escape(event.reason_code)
                + "</code><pre>"
                + _html_value(event.model_dump(mode="json", exclude_none=True))
                + "</pre></li>"
            )
        parts.append("</ol></section>")

    parts.append("</body></html>\n")
    return "".join(parts)


render_static_html = render_html


def save_markdown(
    artifact: CardArtifact, path: str | Path, *, reviewed: bool = True
) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_markdown(artifact, reviewed=reviewed), encoding="utf-8")
    return destination


def save_html(artifact: CardArtifact, path: str | Path, *, reviewed: bool = True) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_html(artifact, reviewed=reviewed), encoding="utf-8")
    return destination
