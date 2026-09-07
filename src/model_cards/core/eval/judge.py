"""The model-card faithfulness judge: is each value in the frozen bundle?

One prompt, one schema, both frozen by md5 and recorded with every result. The judge
sees the card's 33 fields and the frozen source bundle, and nothing else: no binding
ledger, no quote the composer chose, no telemetry. It is asked the two questions that
matter separately.

  For a filled field: is the VALUE supported by the sources? supported / partial /
  unsupported. This measures whether the card says true things.
  For a Not specified field: do the sources actually contain what the field would hold?
  info_in_source yes / no. This measures whether abstention was honest, and it is the
  only way a recall number can mean anything: a card that says nothing is perfectly
  faithful and useless.

The referent question is asked explicitly, because it is the error class this pipeline
exists to fix: a value can be word-for-word in the sources and still be wrong, because
the sentence was about the base model, a sibling checkpoint or a comparison model.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from ..schema import NOT_APPLICABLE, NOT_SPECIFIED, PUBLIC_FIELD_PATHS, get_field_value

JUDGE_PROMPT_VERSION = "model-card-judge-v2"

# Fields whose value is copied from a machine-readable field of the snapshot, not read
# out of prose. Judging them measures the Hub's own metadata, not the card.
JUDGE_SKIP = frozenset({
    "identity.model_id", "identity.version", "links.model_card",
    "access_and_adoption.downloads", "access_and_adoption.likes",
    "specifications.model_size",
    # selected from a taxonomy by what the card says, not read out of a source
    "risks.possible_risks",
})

JUDGE_PROMPT = """You are a careful faithfulness judge for an AI model card.
You are NOT the model that wrote the card. Judge ONLY against the provided sources.

The input JSON has: target (the exact model_id@revision this card documents), sources
(the frozen documents the card was written from, each with a name), and fields (the card
fields to judge, each with path, value and is_ns).

For EACH field:

  If is_ns is true (the value is "Not specified"): set status='not_specified' and
  relation='na'. Set info_in_source='yes' when the sources DO contain what this field
  would hold for THIS EXACT checkpoint, so the card missed it; 'yes_other_entity' when
  the sources contain it only for a different entity (the base model, another size, a
  sibling or a comparison model), which is a correct abstention; else 'no'. Say where in
  note.

  If is_ns is false: judge the VALUE against the sources.
    status='supported' when the sources fully back it FOR THIS EXACT CHECKPOINT;
    'partial' when partly backed, or backed but overreaching;
    'unsupported' when no source backs it or a source contradicts it.
  Then set relation, which is what the supporting sentence is really about:
    'exact_target' the sentence is about this checkpoint;
    'base' about the model this one was derived from;
    'sibling_or_comparison' about another size, variant or a model being compared;
    'family' about the family or series as a whole, not this checkpoint;
    'none' no supporting sentence was found.
  A value can be word-for-word in the sources and still be wrong, because the sentence
  was about a different entity. Judge the entity, not the wording.
  Quote the evidence in note, or say what is missing.

Be strict. A plausible claim with no source support is 'unsupported'. Do not reward
fluency, and do not credit a value for being well written. Return the structured verdict
and cover every field you were given."""

JUDGE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["target", "field_verdicts"],
    "properties": {
        "target": {"type": "string"},
        "field_verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "status", "relation", "info_in_source", "note"],
                "properties": {
                    "path": {"type": "string"},
                    "status": {"type": "string",
                               "enum": ["supported", "partial", "unsupported",
                                        "not_specified"]},
                    "relation": {"type": "string",
                                 "enum": ["exact_target", "base", "sibling_or_comparison",
                                          "family", "none", "na"]},
                    "info_in_source": {"type": "string",
                                       "enum": ["yes", "yes_other_entity", "no", "na"]},
                    "note": {"type": "string"},
                },
            },
        },
    },
}

# Bundle files the judge does not see: the datastore join and the risk taxonomy are not
# sources a card value is read from. config.json, model_info.json and extras.json ARE:
# the first screen (2026-09-06) held text sources only and called 121 structured-channel
# values unsupported (release_date, precision, num_parameters, architecture_type,
# context_length) that a reader of the JSON would have confirmed in one look.
JUDGE_SOURCE_SKIP = frozenset({"eee.json", "risk-atlas.json"})

SOURCE_CAP = 280_000  # characters, about 70k tokens; bounds the largest full-paper bundle


def instrument_id() -> str:
    """The md5 of the prompt and the schema together. Two results are comparable only
    when this matches: a reworded prompt is a different instrument."""
    blob = json.dumps({"version": JUDGE_PROMPT_VERSION, "prompt": JUDGE_PROMPT,
                       "schema": JUDGE_SCHEMA, "skip": sorted(JUDGE_SKIP)},
                      sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.md5(blob).hexdigest()


def judge_fields(card: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The fields the judge is asked about, in contract order."""
    out = []
    for path in PUBLIC_FIELD_PATHS:
        if path in JUDGE_SKIP:
            continue
        value = get_field_value(card, path)
        if value == NOT_APPLICABLE:
            continue
        is_ns = value in (NOT_SPECIFIED, [NOT_SPECIFIED], None, [], {})
        out.append({"path": path, "value": value, "is_ns": is_ns})
    return out


def build_input(artifact, *, source_cap: int = SOURCE_CAP) -> Dict[str, Any]:
    """One judge input: the card's fields and the frozen sources, nothing else.

    The binding ledger is deliberately absent. A judge that can see which quote the
    composer chose is grading the composer's own reasoning, not the card.
    """
    from ..public import public_projection
    from ..review import export_reviewed_card

    card = export_reviewed_card(artifact)
    sources, used = [], 0
    for source in artifact.source_bundle.files if artifact.source_bundle else []:
        text = (source.content or "").strip()
        if not text or source.name in JUDGE_SOURCE_SKIP:
            continue
        room = source_cap - used
        if room <= 0:
            break
        sources.append({"name": source.name, "text": text[:room]})
        used += min(len(text), room)
    return {
        "target": artifact.target.canonical_target,
        "instrument": {"version": JUDGE_PROMPT_VERSION, "id": instrument_id()},
        "sources": sources,
        "fields": judge_fields(public_projection(card)),
        "source_chars": used,
        "sources_truncated": used >= source_cap,
    }


def summarize(verdicts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts a paper can quote, over one card's verdicts."""
    status: Dict[str, int] = {}
    relation: Dict[str, int] = {}
    info: Dict[str, int] = {}
    for verdict in verdicts:
        status[verdict["status"]] = status.get(verdict["status"], 0) + 1
        if verdict["status"] != "not_specified":
            relation[verdict["relation"]] = relation.get(verdict["relation"], 0) + 1
        else:
            info[verdict["info_in_source"]] = info.get(verdict["info_in_source"], 0) + 1
    filled = sum(count for key, count in status.items() if key != "not_specified")
    supported = status.get("supported", 0)
    wrong_entity = sum(count for key, count in relation.items()
                       if key in ("base", "sibling_or_comparison", "family"))
    return {
        "fields_judged": len(verdicts), "filled": filled,
        "status": status, "relation": relation, "info_in_source": info,
        "supported_rate": round(supported / filled, 4) if filled else None,
        "wrong_entity_rate": round(wrong_entity / filled, 4) if filled else None,
        "missed_rate": (round(info.get("yes", 0) / status["not_specified"], 4)
                        if status.get("not_specified") else None),
    }
