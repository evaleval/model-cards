"""The public-source screen: a card read against the live public record.

The judge asks whether a value is in the frozen bundle. The screen asks a different
question that the bundle cannot answer: is the card RIGHT. A reviewer with the Hugging
Face page at the pinned revision, the config, the technical report and the Every Eval
Ever record in front of them checks the card and names what is wrong by category.

The categories are the error classes this pipeline was built to fix, so the screen can
report whether it fixed them:

  wrong-checkpoint        a value that belongs to a different checkpoint of this family
  base-fact-inheritance   a base model's fact presented as this derivative's
  comparison-row-leakage  a comparison model's number on this card
  score-tuple-mismatch    a real score under the wrong benchmark, metric or setting
  wrong-paper             the card is bound to a report that does not introduce it
  fabricated-fact         a claim no source supports
  thin                    a value so generic it says nothing about this model
  other                   anything real that none of the above names

The prompt prefix is hashed and recorded, because a screen run against a reworded prompt
is a different measurement and must not be pooled with an earlier one.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

SCREEN_PROMPT_VERSION = "model-card-screen-v1"

CATEGORIES = ("wrong-checkpoint", "base-fact-inheritance", "comparison-row-leakage",
              "score-tuple-mismatch", "wrong-paper", "fabricated-fact", "thin", "other")

SCREEN_PROMPT = """You are auditing one automatically generated model card against the
public record. You did not write the card and you have no stake in it.

The card documents an EXACT checkpoint: {target}. That exactness is the point of the
audit. A statement that is true of the base model, of another size in the same family, of
the instruct variant when this is the base one, or of a model the developer compares
against, is WRONG on this card even though it is true somewhere.

Check the card against the public record: the Hugging Face page at this exact revision
and its config, the technical report the card cites, the developer's own posts, and the
Every Eval Ever record where one exists. Use web search as needed. Do not accept the
card's own citations as proof; go and look.

For every problem you find, name it with one category:
  wrong-checkpoint       a value that belongs to a different checkpoint of this family
  base-fact-inheritance  a base model's fact presented as this derivative's own
  comparison-row-leakage a comparison model's number reported as this model's
  score-tuple-mismatch   a real score under the wrong benchmark, metric or setting
  wrong-paper            the card cites a report that does not introduce this model
  fabricated-fact        a claim no source supports
  thin                   a value so generic it says nothing about THIS model
  other                  a real problem none of the above names

Also judge separately:
  paper_assessment      is the cited technical report the right one for this checkpoint
  identity_assessment   do the card's identity and lineage fields describe this exact
                        checkpoint, or another one
  scores_assessment     are the reported scores this checkpoint's own

Withheld values are NOT problems. A card that says "Not specified" where the public
record has the answer is a MISS, which you record as category 'other' with severity
'note', never as a fabrication. Judge what the card asserts.

Return the structured verdict. Be specific: quote the card value and say what the public
record says instead."""

SCREEN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["target", "verdict", "paper_assessment", "identity_assessment",
                 "scores_assessment", "findings"],
    "properties": {
        "target": {"type": "string"},
        "verdict": {"type": "string", "enum": ["clean", "minor", "needs-fix"]},
        "paper_assessment": {"type": "string",
                             "enum": ["correct", "wrong", "missing-should-exist",
                                      "correctly-absent", "unverified"]},
        "identity_assessment": {"type": "string",
                                "enum": ["exact-checkpoint", "wrong-checkpoint",
                                         "ambiguous", "unverified"]},
        "scores_assessment": {"type": "string",
                              "enum": ["this-checkpoint", "mixed", "another-model",
                                       "none-reported", "unverified"]},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["field", "category", "severity", "card_value",
                             "public_record", "note"],
                "properties": {
                    "field": {"type": "string"},
                    "category": {"type": "string", "enum": list(CATEGORIES)},
                    "severity": {"type": "string", "enum": ["needs-fix", "minor", "note"]},
                    "card_value": {"type": "string"},
                    "public_record": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
        },
    },
}


def instrument_id() -> str:
    blob = json.dumps({"version": SCREEN_PROMPT_VERSION, "prompt": SCREEN_PROMPT,
                       "schema": SCREEN_SCHEMA}, sort_keys=True,
                      ensure_ascii=False).encode("utf-8")
    return hashlib.md5(blob).hexdigest()


def prompt_prefix_md5() -> str:
    """The hash of the wording alone, which is what a pooled comparison depends on."""
    return hashlib.md5(SCREEN_PROMPT.encode("utf-8")).hexdigest()


def build_input(artifact) -> Dict[str, Any]:
    """One screen input: the published projection and the target, no sources.

    The screen is deliberately not given the frozen bundle. Its job is to check the card
    against the record as it stands, which is the check the bundle cannot perform.
    """
    from ..public import public_projection
    from ..review import export_reviewed_card

    target = artifact.target.canonical_target
    return {
        "target": target,
        "hub_url": f"https://huggingface.co/{artifact.target.model_id}"
                   f"/tree/{artifact.target.resolved_revision}",
        "instrument": {"version": SCREEN_PROMPT_VERSION, "id": instrument_id(),
                       "prompt_prefix_md5": prompt_prefix_md5()},
        "prompt": SCREEN_PROMPT.format(target=target),
        "card": public_projection(export_reviewed_card(artifact)),
    }


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Counts across screened cards: verdicts, and findings by category and severity."""
    verdicts: Dict[str, int] = {}
    by_category: Dict[str, int] = {}
    needs_fix_by_category: Dict[str, int] = {}
    for result in results:
        verdicts[result["verdict"]] = verdicts.get(result["verdict"], 0) + 1
        for finding in result.get("findings") or []:
            by_category[finding["category"]] = by_category.get(finding["category"], 0) + 1
            if finding["severity"] == "needs-fix":
                needs_fix_by_category[finding["category"]] = (
                    needs_fix_by_category.get(finding["category"], 0) + 1)
    cards = len(results) or 1
    return {
        "cards": len(results), "verdicts": verdicts,
        "findings_by_category": by_category,
        "needs_fix_by_category": needs_fix_by_category,
        "needs_fix_cards": verdicts.get("needs-fix", 0),
        "needs_fix_rate": round(verdicts.get("needs-fix", 0) / cards, 4),
        "findings_per_card": round(sum(by_category.values()) / cards, 3),
    }
