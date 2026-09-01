"""Deterministic JSON and self-contained HTML renderers."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

from .artifact import CardArtifact, project_card
from .models import EvidenceKind
from .schema import CONTRACT_VERSION, SECTION_FIELDS


def render_json(artifact: CardArtifact) -> str:
    return json.dumps(
        artifact.to_dict(),
        allow_nan=False,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _inline(value: Any) -> str:
    if isinstance(value, str):
        return escape(value)
    return escape(json.dumps(value, ensure_ascii=False, sort_keys=True))


def _binding_evidence(binding) -> str:
    rendered: list[str] = []
    for evidence in binding.evidence:
        source = (
            f"{escape(evidence.source_id)} · {escape(evidence.source_role.value)} · "
            f"{escape(evidence.source_revision)}"
        )
        if evidence.kind is EvidenceKind.QUOTE:
            coordinates = (
                f"characters {evidence.char_start}–{evidence.char_end}"
                if evidence.verified
                else "not verified"
            )
            rendered.append(
                f'<div class="evidence"><div class="source">{source} · {coordinates}</div>'
                f"<blockquote>{escape(evidence.quote or '')}</blockquote></div>"
            )
        else:
            rendered.append(
                f'<div class="evidence"><div class="source">{source} · '
                f"{escape(evidence.pointer or '')}</div>"
                f"<pre>{_inline(evidence.fragment)}</pre></div>"
            )
    return "".join(rendered)


def render_html(artifact: CardArtifact) -> str:
    """Render a standalone inspection page with card, bindings, and reviews."""

    card = project_card(artifact)
    section_blocks: list[str] = []
    for section, fields in SECTION_FIELDS.items():
        rows = "".join(
            "<tr>"
            f"<th>{escape(field)}</th>"
            f"<td>{_inline(card[section][field])}</td>"
            "</tr>"
            for field in fields
        )
        section_blocks.append(
            f'<section><h2>{escape(section.replace("_", " ").title())}</h2>'
            f"<table>{rows}</table></section>"
        )

    effective = {item.binding_id: item for item in artifact.effective_bindings()}
    binding_blocks: list[str] = []
    for original in artifact.bindings:
        current = effective[original.binding_id]
        changed = (
            original.field_path != current.field_path
            or original.value != current.value
            or original.relation is not current.relation
            or original.disposition is not current.disposition
            or original.reason != current.reason
        )
        generated_state = ""
        if changed:
            generated_state = (
                "<details><summary>Generated state</summary>"
                f"<p><strong>{escape(original.field_path)}</strong> ← "
                f"{escape(original.claim_entity)} ({escape(original.relation.value)})</p>"
                f"<pre>{_inline(original.value)}</pre>"
                f'<p class="reason">{escape(original.disposition.value)} · '
                f"{escape(original.reason)}</p></details>"
            )
        binding_blocks.append(
            f'<article class="binding {escape(current.disposition.value)}">'
            f'<div class="binding-head"><code>{escape(current.binding_id)}</code>'
            f'<span class="pill">{escape(current.disposition.value)}</span></div>'
            f"<p><strong>{escape(current.field_path)}</strong> ← "
            f"{escape(current.claim_entity)} ({escape(current.relation.value)})</p>"
            f"<pre>{_inline(current.value)}</pre>"
            f'<p class="reason">{escape(current.reason)}</p>'
            f"{generated_state}{_binding_evidence(current)}</article>"
        )

    review_rows_list: list[str] = []
    for event in artifact.reviews:
        details = "—"
        if event.action.value == "reassign":
            details = (
                f"{escape(event.field_path or '')} · {escape(event.relation.value if event.relation else '')}"
                f"<pre>{_inline(event.corrected_value)}</pre>"
            )
        review_rows_list.append(
            "<tr>"
            f"<td>{escape(event.event_id)}</td>"
            f"<td>{escape(event.binding_id)}</td>"
            f"<td>{escape(event.action.value)}</td>"
            f"<td>{escape(event.reason)}</td>"
            f"<td>{details}</td>"
            "</tr>"
        )
    review_rows = "".join(review_rows_list)
    if not review_rows:
        review_rows = '<tr><td colspan="5">No review events</td></tr>'

    title = f"Model Card · {artifact.target.model_id}"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ margin: 0 auto; max-width: 1120px; padding: 32px 24px 80px; color: #17202a; }}
    h1 {{ margin-bottom: 6px; }} h2 {{ margin-top: 34px; text-transform: capitalize; }}
    .target {{ color: #52606d; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border-top: 1px solid #d8dee4; padding: 9px 10px; text-align: left; vertical-align: top; }}
    th {{ width: 24%; color: #34495e; }} td {{ overflow-wrap: anywhere; }}
    .binding {{ border: 1px solid #d8dee4; border-left-width: 5px; border-radius: 7px; padding: 14px; margin: 12px 0; }}
    .binding.accepted {{ border-left-color: #218739; }}
    .binding.withheld {{ border-left-color: #c47d09; }}
    .binding.rejected {{ border-left-color: #c0392b; }}
    .binding-head {{ display: flex; justify-content: space-between; gap: 12px; }}
    .pill {{ border: 1px solid #9aa5b1; border-radius: 999px; padding: 2px 8px; font-size: 0.8rem; }}
    pre, blockquote {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #f6f8fa; margin: 8px 0; padding: 9px; }}
    blockquote {{ border-left: 3px solid #9aa5b1; }}
    .source, .reason {{ color: #52606d; font-size: 0.9rem; }}
    code {{ overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    <div class="target">Exact revision: {escape(artifact.target.revision)} · Contract {escape(CONTRACT_VERSION)} · {escape(artifact.lifecycle_status.value)}</div>
  </header>
  {''.join(section_blocks)}
  <section><h2>Evidence bindings</h2>{''.join(binding_blocks)}</section>
  <section><h2>Review history</h2>
    <table><thead><tr><th>Event</th><th>Binding</th><th>Action</th><th>Reason</th><th>Details</th></tr></thead>
    <tbody>{review_rows}</tbody></table>
  </section>
</body>
</html>
"""


def save_json(artifact: CardArtifact, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_json(artifact), encoding="utf-8")
    return destination


def save_html(artifact: CardArtifact, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_html(artifact), encoding="utf-8")
    return destination
