"""The final-claim pass: the card's own prose, checked against the frozen bundle.

Everything upstream checks that a quote is real and that it is about the right entity.
This checks the last step, the one Stage B does on its own: whether the sentence the
writer produced is entailed by the evidence it cited. FactReasoner does that with an NLI
extractor and a probabilistic layer over the atoms of each claim.

It is non-blocking by construction. A contradiction flags the field it belongs to; a
neutral or unsupported atom is recorded and nothing else; and when the pass cannot run at
all, the card records that it did not run and why, because a validation step that is
silently absent reads exactly like one that passed.

Availability is checked, never assumed. The pass needs the fact_reasoner package, the
merlin binary, and a serving route that returns token logprobs, because without them
every atom sits at 0.5 and the layer reports nothing. The composer's own route has none,
so the pass runs on its own route (FACTREASONER_MODEL, FACTREASONER_PROVIDER) and only
when MODELCARDS_FACTCHECK is set; otherwise the card records that it did not run.
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
        "provider": os.environ.get("FACTREASONER_PROVIDER", ""),
        "has_key": bool(os.environ.get("FACTREASONER_API_KEY")),
    }


def provider_body(provider: str) -> Dict[str, Any]:
    """OpenRouter provider preferences that make the router honour `logprobs`."""
    order = [x.strip() for x in (provider or "").split(",") if x.strip()]
    if not order:
        return {}
    return {"provider": {"order": order, "allow_fallbacks": False}}


PROBE_RETRIES = 4
PROBE_BACKOFF_S = 3.0


def probe_logprobs(model: str, api_base: str, api_key: str, timeout: float = 60.0,
                   provider: str = "") -> Tuple[bool, str]:
    """One tiny call: does this route return token logprobs?

    Without a pinned provider OpenRouter answers from whichever endpoint is cheapest,
    and most of them drop `logprobs` silently; the 2026-09-05 probes of four models
    all came back empty for that reason, not because no provider has them."""
    try:
        import time

        import httpx
        from openai import OpenAI, RateLimitError

        client = OpenAI(api_key=api_key, base_url=api_base,
                        timeout=httpx.Timeout(timeout, connect=10.0), max_retries=1)
        reply = None
        for attempt in range(PROBE_RETRIES):
            try:
                reply = client.chat.completions.create(
                    model=model, messages=[{"role": "user", "content": "Reply with one word: yes"}],
                    max_tokens=4, temperature=0, logprobs=True, top_logprobs=2,
                    extra_body=provider_body(provider) or None)
                break
            except RateLimitError:
                if attempt == PROBE_RETRIES - 1:
                    raise
                time.sleep(PROBE_BACKOFF_S * (2 ** attempt))
        choice = reply.choices[0]
        content = getattr(choice, "logprobs", None)
        if content is None or not getattr(content, "content", None):
            return False, "the route accepted the request but returned no logprobs"
        return True, "logprobs available"
    except Exception as exc:
        return False, f"logprobs probe failed: {type(exc).__name__}: {exc}"[:200]


def merlin_path() -> str:
    """The merlin binary FactReasoner's probabilistic layer shells out to, or ""."""
    merlin = os.environ.get("MERLIN_BIN")
    if not merlin:
        try:
            from auto_benchmarkcard.config import Config

            merlin = str(Config.MERLIN_BIN)
        except Exception:
            merlin = ""
    return merlin if merlin and Path(merlin).is_file() else ""


def cache_dir() -> str:
    """FactReasoner's NLI cache; the library default is a path relative to the cwd."""
    import tempfile

    return os.environ.get("FACTREASONER_CACHE_DIR") or str(
        Path(tempfile.gettempdir()) / "model_cards_core_factreasoner_cache")


def availability(*, probe: bool = True) -> Tuple[bool, str]:
    """Whether the final-claim pass can run here, and the reason when it cannot."""
    try:
        import fact_reasoner  # noqa: F401
    except Exception as exc:
        return False, f"fact_reasoner is not importable: {type(exc).__name__}"
    if not merlin_path():
        return False, "the merlin binary is not present"
    route = route_from_env()
    if not (route["model"] and route["api_base"] and route["has_key"]):
        return False, ("no FactReasoner route configured (FACTREASONER_MODEL, "
                       "FACTREASONER_API_BASE, FACTREASONER_API_KEY)")
    if not probe:
        return True, "route configured, logprobs not probed"
    ok, reason = probe_logprobs(route["model"], route["api_base"],
                                os.environ["FACTREASONER_API_KEY"],
                                provider=route["provider"])
    if ok and route["provider"]:
        reason = f"logprobs available from {route['provider']}"
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
        # the library defaults are paths relative to the cwd ("merlin/bin/merlin",
        # "factreasoner_cache"), which is wherever the batch happened to be started
        results = None
        for attempt in range(PROBE_RETRIES):
            try:
                results = evaluate_factuality_two_tier(
                    formatted_rag_results=claims,
                    source_text="\n\n".join(source_texts.values()),
                    model=route["model"],
                    merlin_path=merlin_path(),
                    cache_dir=cache_dir())
                break
            except Exception as exc:  # noqa: BLE001
                if "429" not in str(exc) or attempt == PROBE_RETRIES - 1:
                    raise
                import time

                time.sleep(PROBE_BACKOFF_S * (2 ** attempt))
    except Exception as exc:
        logger.warning("final-claim pass failed: %s", exc)
        return {**base, "status": "failed", "reason": f"{type(exc).__name__}: {exc}"[:200]}

    return {**base, **read_outcomes(claims, results), "status": "ok", "reason": reason}


CONTRADICTED_BELOW = 0.3


def read_outcomes(claims: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, Any]:
    """Per-atom outcomes from FactReasoner's result, keyed back to the card fields.

    The composer tool returns {"results": {counts}, "marginals": [{"variable",
    "probabilities", "p_true"}], "escalation": {...}, ...}. The first version of this
    reader iterated "results" as if it were the atom list and died on the first key,
    which is what the 2026-09-05 integration audit flagged and the first end-to-end run
    on 2026-09-06 confirmed. An atom is contradicted below CONTRADICTED_BELOW, neutral at
    exactly 0.5 (no informative relation, after escalation "not in the source"),
    supported above 0.5, and uncertain in between.
    """

    by_id = {atom["id"]: atom for atom in claims["atoms"]}
    outcomes, contradicted = [], []
    for entry in results.get("marginals") or []:
        atom_id = str(entry.get("variable") or "")
        field = (by_id.get(atom_id) or {}).get("field")
        p_true = entry.get("p_true")
        if not isinstance(p_true, (int, float)):
            label = "unscored"
        elif p_true < CONTRADICTED_BELOW:
            label = "contradicted"
        elif p_true == 0.5:
            label = "neutral"
        elif p_true > 0.5:
            label = "supported"
        else:
            label = "uncertain"
        outcomes.append({"field": field, "atom": atom_id, "label": label,
                         "p_true": p_true, "text": (by_id.get(atom_id) or {}).get("text")})
        if field and label == "contradicted":
            contradicted.append(field)
    summary = results.get("results") or {}
    return {"atoms": outcomes,
            "contradicted_fields": sorted(set(contradicted)),
            "factuality_score": summary.get("factuality_score"),
            "escalation": results.get("escalation"),
            "label_counts": {label: sum(1 for o in outcomes if o["label"] == label)
                             for label in ("supported", "neutral", "uncertain",
                                           "contradicted", "unscored")}}
