"""The final-claim pass: the card's own prose, checked against the frozen bundle.

Everything upstream checks that a quote is real and that it is about the right entity.
This checks the last step, the one Stage B does on its own: whether the sentence the
writer produced is entailed by the evidence it cited. FactReasoner does that with an NLI
extractor and a probabilistic layer over the atoms of each claim.

It is non-blocking by construction. A contradiction withholds the field it belongs to; a
neutral or unsupported atom is recorded and nothing else; and when the pass cannot run at
all, the card records that it did not run and why, because a validation step that is
silently absent reads exactly like one that passed.

Availability is checked, never assumed. The pass needs the fact_reasoner package, the
merlin binary, and a serving route that returns token logprobs, because without them
every atom sits at 0.5 and the layer reports nothing. Probed 2026-09-04: the pinned route
(deepseek/deepseek-v4-flash-0731 on Together) returns no logprobs, and the Hugging Face
router refuses this token, so the recorded outcome on every card today is unavailable.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# The fields whose value is prose the writer composed rather than a value it copied.
PROSE_FIELDS = (
    "identity.summary",
    "identity.model_type",
    "training_context.training_data",
    "training_context.adaptations",
    "evaluation.results_summary",
    "evaluation.human_evals",
    "evaluation.safety_evals",
)
CONTEXT_WINDOW = 1200


def route_from_env() -> Dict[str, str]:
    """The FactReasoner serving route, from the environment, with the composer's own
    generic OpenAI-compatible variables so no code has to change to move it."""
    return {
        "model": os.environ.get("FACTREASONER_MODEL", ""),
        "api_base": os.environ.get("FACTREASONER_API_BASE", ""),
        "has_key": bool(os.environ.get("FACTREASONER_API_KEY")),
    }


def probe_logprobs(model: str, api_base: str, api_key: str, timeout: float = 60.0
                   ) -> Tuple[bool, str]:
    """One tiny call: does this route return token logprobs?"""
    try:
        import httpx
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=api_base,
                        timeout=httpx.Timeout(timeout, connect=10.0), max_retries=1)
        reply = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Reply with one word: yes"}],
            max_tokens=4, temperature=0, logprobs=True, top_logprobs=2)
        choice = reply.choices[0]
        content = getattr(choice, "logprobs", None)
        if content is None or not getattr(content, "content", None):
            return False, "the route accepted the request but returned no logprobs"
        return True, "logprobs available"
    except Exception as exc:
        return False, f"logprobs probe failed: {type(exc).__name__}: {exc}"[:200]


def availability(*, probe: bool = True) -> Tuple[bool, str]:
    """Whether the final-claim pass can run here, and the reason when it cannot."""
    try:
        import fact_reasoner  # noqa: F401
    except Exception as exc:
        return False, f"fact_reasoner is not importable: {type(exc).__name__}"
    merlin = os.environ.get("MERLIN_BIN")
    if not merlin:
        try:
            from auto_benchmarkcard.config import Config

            merlin = str(Config.MERLIN_BIN)
        except Exception:
            merlin = ""
    if not merlin or not Path(merlin).is_file():
        return False, "the merlin binary is not present"
    route = route_from_env()
    if not (route["model"] and route["api_base"] and route["has_key"]):
        return False, ("no FactReasoner route configured (FACTREASONER_MODEL, "
                       "FACTREASONER_API_BASE, FACTREASONER_API_KEY)")
    if not probe:
        return True, "route configured, logprobs not probed"
    ok, reason = probe_logprobs(route["model"], route["api_base"],
                                os.environ["FACTREASONER_API_KEY"])
    return ok, reason


def _window(text: str, start: Optional[int], end: Optional[int]) -> str:
    if not text:
        return ""
    if start is None or end is None:
        return text[:CONTEXT_WINDOW]
    lo = max(0, start - CONTEXT_WINDOW // 2)
    return text[lo:max(end, lo) + CONTEXT_WINDOW // 2]


def build_claims(card: Dict[str, Any], bindings, source_texts: Dict[str, str],
                 topic: str) -> Dict[str, Any]:
    """The FactReasoner input for one card: one atom per prose field, its contexts being
    the cited quote and the surrounding run of the frozen source it came from."""
    from .records import VerifierAction
    from .schema import NOT_APPLICABLE, NOT_SPECIFIED, get_field_value

    atoms: List[Dict[str, Any]] = []
    contexts: List[Dict[str, Any]] = []
    by_field: Dict[str, list] = {}
    for binding in bindings:
        if binding.verifier_action is not VerifierAction.ACCEPT:
            continue
        by_field.setdefault(binding.field_path.split("[", 1)[0], []).append(binding)

    for index, path in enumerate(PROSE_FIELDS):
        try:
            value = get_field_value(card, path)
        except KeyError:
            continue
        if not isinstance(value, str) or value in (NOT_SPECIFIED, NOT_APPLICABLE):
            continue
        cited = by_field.get(path) or []
        if not cited:
            continue
        atom_id = f"a{index}"
        context_ids = []
        for binding in cited:
            for span_index, span in enumerate(binding.evidence):
                context_id = f"c_{atom_id}_{len(context_ids)}"
                body = span.exact_text or ""
                source = source_texts.get(span.source_uri, "")
                window = _window(source, span.start_offset, span.end_offset)
                text = window if len(window) > len(body) else body
                if not text.strip():
                    continue
                context_ids.append(context_id)
                contexts.append({"id": context_id, "title": topic, "text": text})
        if not context_ids:
            continue
        atoms.append({"id": atom_id, "text": value, "original": value, "label": "S",
                      "contexts": context_ids, "field": path})
    return {"input": f"Question: Tell me about the model {topic}",
            "output": " ".join(a["text"] for a in atoms), "topic": topic,
            "cat": ["model", topic], "atoms": atoms, "contexts": contexts}


def final_claim_pass(card: Dict[str, Any], bindings, source_texts: Dict[str, str],
                     topic: str, *, probe: bool = True) -> Dict[str, Any]:
    """Run the pass when it can run; always return what happened.

    The result is {"status", "reason", "atoms", "contradicted_fields"}. status is "ok",
    "unavailable" (the route or a dependency is missing) or "failed" (it ran and raised).
    Nothing here raises: a validation step must not be able to lose a card.
    """
    claims = build_claims(card, bindings, source_texts, topic)
    base = {"atoms": [], "contradicted_fields": [], "claims_built": len(claims["atoms"])}
    if not claims["atoms"]:
        return {**base, "status": "skipped", "reason": "no prose field carries a bound value"}
    ok, reason = availability(probe=probe)
    if not ok:
        return {**base, "status": "unavailable", "reason": reason}
    try:
        from auto_benchmarkcard.tools.factreasoner.factreasoner_tool import (
            evaluate_factuality_two_tier,
        )

        route = route_from_env()
        results = evaluate_factuality_two_tier(
            formatted_rag_results=claims,
            source_text="\n\n".join(source_texts.values()),
            model=route["model"])
    except Exception as exc:
        logger.warning("final-claim pass failed: %s", exc)
        return {**base, "status": "failed", "reason": f"{type(exc).__name__}: {exc}"[:200]}

    by_id = {atom["id"]: atom for atom in claims["atoms"]}
    outcomes, contradicted = [], []
    for entry in results.get("results", results.get("atoms", [])) or []:
        atom_id = str(entry.get("id") or entry.get("atom_id") or "")
        field = (by_id.get(atom_id) or {}).get("field")
        label = str(entry.get("label") or entry.get("decision") or "").lower()
        outcomes.append({"field": field, "atom": atom_id, "label": label,
                         "score": entry.get("score") or entry.get("probability")})
        if field and "contradict" in label:
            contradicted.append(field)
    return {"status": "ok", "reason": reason, "atoms": outcomes,
            "contradicted_fields": sorted(set(contradicted)),
            "claims_built": len(claims["atoms"])}
