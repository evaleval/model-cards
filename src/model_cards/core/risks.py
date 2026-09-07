"""The risk stage: AI Risk Atlas entries selected for THIS checkpoint.

Mirrors the benchmark card's possible_risks. The card's own accepted values become a
use-case text, the Risk Atlas Nexus detector retrieves candidate risks from the frozen
taxonomy, and one structured call picks at most MAX_SELECTED_RISKS of them with a
justification each that has to name concrete card content. Nothing is inherited from a
base model or a family: the use case is built from the card as gated, and a field whose
accepted binding is family-scope is labelled so in the text the selector reads.

Evidence: every selected risk binds to its entry in the frozen taxonomy file that the
bundle carries (risk-atlas.json), by JSON pointer, so the click-through lands on the
definition the card is citing. The justification is the selector's prose and is recorded
on the value and in the stage telemetry, never as evidence.
"""

from __future__ import annotations

import json
import logging
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .calls import capped_generate

logger = logging.getLogger(__name__)

TAXONOMY = "ibm-risk-atlas"
TAXONOMY_URI = "https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas"
TAXONOMY_FILE = "risk-atlas.json"
RISK_CANDIDATE_COUNT = 12
MAX_SELECTED_RISKS = 5
SELECTION_MAX_TOKENS = 1536
JUSTIFICATION_MAX_CHARS = 300

_EMPTY = {"not specified", "not applicable", ""}

# The card fields the use case is built from, in the order they are written.
USECASE_FIELDS: Tuple[Tuple[str, str], ...] = (
    ("identity.name", "{v} is a model"),
    ("identity.summary", "{v}"),
    ("identity.model_type", "Primary task: {v}"),
    ("specifications.input_output", "Modalities: {v}"),
    ("specifications.architecture_type", "Architecture: {v}"),
    ("training_context.training_data", "Training data: {v}"),
    ("training_context.adaptations", "Post-training or adaptation: {v}"),
    ("training_context.data_cutoff", "Data cutoff: {v}"),
    ("access_and_adoption.access_type", "Access: {v}"),
    ("identity.license", "License: {v}"),
    ("evaluation.results_summary", "Reported results: {v}"),
    ("evaluation.safety_evals", "Reported safety evaluations: {v}"),
    ("evaluation.human_evals", "Reported human evaluations: {v}"),
    ("lineage.model_family", "Family: {v}"),
)

SELECTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["selected"],
    "properties": {
        "selected": {
            "type": "array",
            "maxItems": MAX_SELECTED_RISKS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "justification"],
                "properties": {
                    "id": {"type": "string"},
                    "justification": {"type": "string", "maxLength": JUSTIFICATION_MAX_CHARS},
                },
            },
        }
    },
}

SELECTION_PROMPT = """You are reviewing the documentation card of an AI model checkpoint. From a fixed candidate list of AI risks, select the risks that THIS checkpoint plausibly raises.

MODEL CARD SUMMARY (only what the card itself states; a line marked [family-scope] describes the model family rather than this exact checkpoint):
{card_summary}

CANDIDATE RISKS (one per line, format: id | name | description):
{candidate_block}

Select between 0 and {max_risk} risks from the candidate list.
Rules:
- Select a risk only if you can justify it from concrete content of the card summary (its task, modalities, training data, adaptation, access type, reported evaluations, or license).
- For each selected risk write a one-line checkpoint-specific justification that references that concrete content, for example: "open-weight chat model with no reported safety evaluation -> jailbreaking".
- A family-scope line justifies a risk only if the summary says the same of this checkpoint; a base model does not inherit a post-training risk from its instruct sibling and an instruct model does not inherit a pretraining-data risk that its own card does not state.
- Selecting nothing is a valid and expected answer. Padding the list with generic risks that would apply to any model is worse than returning fewer risks or none.
- Never select a risk that is not in the candidate list."""


def nexus_version() -> str:
    try:
        return metadata.version("ai-atlas-nexus")
    except metadata.PackageNotFoundError:
        return "unknown"


def taxonomy_entries() -> List[Dict[str, Any]]:
    """The taxonomy as plain rows, from the installed package, sorted by id."""
    from ai_atlas_nexus import AIAtlasNexus

    rows = []
    for risk in AIAtlasNexus().get_all_risks(TAXONOMY):
        rows.append({
            "id": getattr(risk, "id", None),
            "name": getattr(risk, "name", None),
            "description": getattr(risk, "description", None),
            "url": getattr(risk, "url", None) or None,
            "tag": getattr(risk, "tag", None),
            "type": getattr(risk, "type", None),
            "concern": getattr(risk, "concern", None),
        })
    rows.sort(key=lambda r: str(r["id"]))
    return rows


def frozen_taxonomy(bundle_root: str | Path) -> str:
    """The taxonomy text every card in bundle_root binds to; written once, then read.

    Package data, not a network fetch, so it is written the first time a bundle root
    needs it and reused after, the way the paper cache is.
    """
    path = Path(bundle_root) / "_risk_atlas" / f"{TAXONOMY}.json"
    if path.is_file():
        return path.read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"taxonomy": TAXONOMY, "source": TAXONOMY_URI, "nexus_version": nexus_version(),
               "risks": sorted(taxonomy_entries(), key=lambda r: str(r.get("id")))}
    text = json.dumps(payload, indent=1, ensure_ascii=False, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    return text


def _specified(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in _EMPTY
    if isinstance(value, list):
        return bool(value) and not (len(value) == 1 and isinstance(value[0], str)
                                    and value[0].strip().lower() in _EMPTY)
    return bool(value)


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def usecase_from_card(card: Dict[str, Any], relations: Optional[Dict[str, str]] = None,
                      frame: Optional[Dict[str, Any]] = None) -> Tuple[str, List[str]]:
    """(use-case text, the field paths it was built from).

    relations maps a field path to the relation of its accepted binding; a family-scope
    value is marked so the selector cannot read it as a checkpoint fact.
    """
    relations = relations or {}
    parts, used = [], []
    for path, template in USECASE_FIELDS:
        section, field = path.split(".", 1)
        value = (card.get(section) or {}).get(field)
        if not _specified(value):
            continue
        line = template.format(v=_as_text(value)).rstrip(".")
        if relations.get(path) == "family":
            line += " [family-scope]"
        parts.append(line)
        used.append(path)
    if frame and isinstance(frame, dict):
        names = [n.get("name") for n in frame.get("nodes", [])
                 if isinstance(n, dict) and n.get("type") in ("target", "base", "family") and n.get("name")]
        if names:
            parts.append("Named entities around the model: " + ", ".join(dict.fromkeys(names)))
    if not parts:
        return "", []
    text = ". ".join(p.rstrip(".") for p in parts) + "."
    return text, used


DETECTOR_DRAWS = 3


def detect_candidates(usecase: str, engine: Any, entries: List[Dict[str, Any]],
                      count: int = RISK_CANDIDATE_COUNT,
                      telemetry: Optional[Dict[str, Any]] = None) -> List[str]:
    """Candidate risk ids from the Nexus detector, the union of a few draws.

    The detector is one enum-constrained list call. On the pinned route, at temperature
    0, four identical calls on the same use case returned 12, 1, 0 and 0 names
    (2026-09-06): the constrained list is where this route is not deterministic. One
    empty draw is therefore not "no candidate". Up to DETECTOR_DRAWS draws are taken and
    their union kept in first-seen order, each draw recorded, and the selector still
    decides what stays. Replaceable in tests.
    """
    from ai_atlas_nexus import AIAtlasNexus
    from ai_atlas_nexus.blocks.risk_detector import BenchmarkRiskDetector

    wanted = {e["id"] for e in entries}
    risks = [r for r in AIAtlasNexus().get_all_risks(TAXONOMY) if getattr(r, "id", None) in wanted]
    detector = BenchmarkRiskDetector(risks=risks, inference_engine=engine, max_risk=count)
    ids: List[str] = []
    draws: List[int] = []
    for _ in range(DETECTOR_DRAWS):
        found = detector.detect([usecase])
        names = [getattr(r, "id", None) for r in (found[0] if found else [])]
        draws.append(len(names))
        for rid in names:
            if rid and rid not in ids:
                ids.append(rid)
        if len(ids) >= count:
            break
    if isinstance(telemetry, dict):
        telemetry["draws"] = draws
    return ids[:count]


def select_risks(llm, usecase: str, candidates: List[Dict[str, Any]],
                 telemetry: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], int]:
    """One structured call; (selected rows, invalid item count)."""
    block = "\n".join(f"{c['id']} | {c['name']} | {c['description']}" for c in candidates)
    prompt = SELECTION_PROMPT.format(card_summary=usecase, candidate_block=block,
                                     max_risk=MAX_SELECTED_RISKS)
    raw = capped_generate(llm, prompt, response_format=SELECTION_SCHEMA,
                          max_tokens=SELECTION_MAX_TOKENS, telemetry=telemetry, label="risk_selection")
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except ValueError:
        return [], -1
    items = parsed.get("selected") if isinstance(parsed, dict) else None
    if not isinstance(items, list):
        return [], -1
    by_id = {c["id"]: c for c in candidates}
    selected, seen, invalid = [], set(), 0
    for item in items:
        if len(selected) >= MAX_SELECTED_RISKS:
            break
        rid = item.get("id") if isinstance(item, dict) else None
        cand = by_id.get(rid)
        if cand is None or rid in seen:
            invalid += 1
            continue
        seen.add(rid)
        just = item.get("justification")
        just = " ".join(just.split())[:JUSTIFICATION_MAX_CHARS] if isinstance(just, str) else ""
        selected.append({"entry": cand, "justification": just})
    return selected, invalid


def run_risk_stage(card: Dict[str, Any], relations: Dict[str, str], frame: Optional[Dict[str, Any]],
                   llm, taxonomy_text: str,
                   detector: Callable[..., List[str]] = detect_candidates) -> Dict[str, Any]:
    """The whole stage; never raises. Returns {"status", "reason", "rows", "pointers", ...}.

    rows are the public possible_risks rows; pointers are the matching JSON pointers into
    the frozen taxonomy file, one per row, for the evidence spans.
    """
    telemetry: Dict[str, Any] = {"status": "skipped", "reason": None, "usecase_fields": [],
                                 "draws": [], "candidate_count": 0, "candidates": [], "selected_count": 0,
                                 "invalid_selection_items": 0, "rows": [], "pointers": []}
    try:
        taxonomy = json.loads(taxonomy_text)
    except ValueError:
        telemetry.update(status="failed", reason="frozen taxonomy is not JSON")
        return telemetry
    entries = taxonomy.get("risks") or []
    index = {e["id"]: (i, e) for i, e in enumerate(entries)}
    usecase, used = usecase_from_card(card, relations, frame)
    telemetry["usecase_fields"] = used
    telemetry["usecase"] = usecase
    if not usecase:
        telemetry.update(reason="no specified field to build a use case from")
        return telemetry
    engine = getattr(llm, "engine", None)
    if engine is None:
        telemetry.update(status="unavailable", reason="the handler exposes no inference engine")
        return telemetry
    try:
        ids = (detector(usecase, engine, entries, telemetry=telemetry)
               if detector is detect_candidates else detector(usecase, engine, entries))
    except Exception as exc:  # noqa: BLE001
        telemetry.update(status="failed", reason=f"detector: {type(exc).__name__}: {exc}"[:200])
        return telemetry
    candidates = [index[i][1] for i in ids if i in index]
    telemetry["candidate_count"] = len(candidates)
    telemetry["candidates"] = [c["id"] for c in candidates]
    if not candidates:
        telemetry.update(status="ok", reason="the detector returned no candidate")
        return telemetry
    try:
        selected, invalid = select_risks(llm, usecase, candidates, telemetry)
    except Exception as exc:  # noqa: BLE001
        telemetry.update(status="failed", reason=f"selection: {type(exc).__name__}: {exc}"[:200])
        return telemetry
    telemetry["invalid_selection_items"] = invalid
    rows, pointers = [], []
    for item in selected:
        entry = item["entry"]
        row = {"category": entry["name"], "description": entry["description"], "url": entry.get("url")}
        if item["justification"]:
            row["justification"] = item["justification"]
        rows.append(row)
        pointers.append((f"/risks/{index[entry['id']][0]}", entry))
    telemetry.update(status="ok", reason=f"{len(rows)} of {len(candidates)} candidates selected",
                     selected_count=len(rows), rows=rows, pointers=pointers)
    return telemetry


__all__ = ["TAXONOMY", "TAXONOMY_URI", "TAXONOMY_FILE", "frozen_taxonomy", "usecase_from_card",
           "detect_candidates", "select_risks", "run_risk_stage", "MAX_SELECTED_RISKS"]
