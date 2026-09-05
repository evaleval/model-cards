"""Leaf-value support: every number and every identifier in a value must be in its evidence.

Stage B writes prose, so it may rephrase. It may not introduce a number or a model,
dataset or benchmark identifier that no cited quote contains. That is the cheapest
detector for the error class the AAAI evaluation named, because a spliced value almost
always shows up as a number or a name that is in the sources but not in the quotes this
particular value cited: "the quote said 73.5 and the card says 99.0" and "the quote is
about OLMo-2-13B and the card says OLMo-2-7B" are both caught here, without a model call.

Numbers are compared on their value, not their spelling, so 4,096 and 4096 match, 63.70
and 63.7 match, and 4 trillion matches 4T. Identifiers are compared case-insensitively
with separators removed, so OLMo-2-1124-7B matches "OLMo 2 1124 7B".
"""

from __future__ import annotations

import re
from typing import Any, Iterable, List, Set

_NUMBER_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)\s*(%|[KMBT]\b|billion|million|"
                        r"trillion|thousand)?", re.IGNORECASE)
_SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6,
          "b": 1e9, "billion": 1e9, "t": 1e12, "trillion": 1e12}
# An identifier is a token that NAMES something. An English compound does not: enumerating
# "mid-trained" and "Transformer-style" as stopwords is a losing game, so the shape has to
# do the work. A candidate qualifies when it is a repo id (a slash), or carries a digit
# (OLMo-2-1124-7B, GSM8K, Llama-3.1-8B, Dolmino-Mix-1124), or has a capital after its first
# character (MMLU-Pro, OpenAI). "mid-trained" and "Transformer-style" have none of those.
_CANDIDATE_RE = re.compile(r"\b(?:[A-Za-z0-9][\w.]*/[\w.\-]+"
                           r"|[A-Za-z][\w.]*(?:[-_][A-Za-z0-9][\w.]*)+"
                           r"|[A-Za-z]+\d[\w.]*)\b")
_HAS_DIGIT_RE = re.compile(r"\d")
_INNER_CAPITAL_RE = re.compile(r"(?<=.)[A-Z]")


def _is_identifier(token: str) -> bool:
    if len(token) < 3:
        return False
    if "/" in token:
        return True
    if _HAS_DIGIT_RE.search(token):
        return True
    return bool(_INNER_CAPITAL_RE.search(token.replace("-", "").replace("_", "")[1:] or ""))


def _canonical_number(digits: str, unit: str | None) -> str:
    try:
        value = float(digits.replace(",", ""))
    except ValueError:
        return digits
    unit = (unit or "").strip().lower()
    if unit == "%":
        return f"pct:{value:.10g}"
    if unit in _SCALE:
        value *= _SCALE[unit]
    return f"{value:.10g}"


def numbers_in(text: str) -> Set[str]:
    """Every number in the text, canonicalized so spelling does not matter."""
    out: Set[str] = set()
    for m in _NUMBER_RE.finditer(text or ""):
        digits, unit = m.group(1), m.group(2)
        out.add(_canonical_number(digits, unit))
        if unit:                       # also record it unscaled, for "7B" against "7"
            out.add(_canonical_number(digits, None))
        elif "," in digits:            # and the plain form, for "4,096" against "4096"
            out.add(_canonical_number(digits, None))
    return out


def _fold(token: str) -> str:
    return re.sub(r"[^a-z0-9/]", "", token.lower())


def identifiers_in(text: str) -> Set[str]:
    """Every entity-shaped identifier in the text, folded for comparison."""
    out: Set[str] = set()
    for m in _CANDIDATE_RE.finditer(text or ""):
        token = m.group(0)
        if not _is_identifier(token):
            continue
        folded = _fold(token)
        if folded and not folded.isdigit():
            out.add(folded)
    return out


def _leaf_strings(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float)):
        return [str(value)]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _leaf_strings(v)]
    if isinstance(value, (list, tuple)):
        return [s for v in value for s in _leaf_strings(v)]
    return []


def unsupported_leaves(value: Any, evidence_texts: Iterable[str],
                       established: Iterable[str] = ()) -> List[str]:
    """The numbers and identifiers in `value` that nothing supports.

    Support is the cited quotes plus `established`: the values the structured channel
    already fixed for this card and the target's own names. A summary that says "the 7B
    model" is not fabricating when the target is a 7B checkpoint, even if the particular
    quote it cited does not repeat the size.

    An empty result means every leaf is traceable. The check is one directional on
    purpose: the evidence may say more than the value does.
    """
    support = " \n ".join(list(t for t in evidence_texts if t) + list(established))
    if not support:
        return sorted(numbers_in(" ".join(_leaf_strings(value)))
                      | identifiers_in(" ".join(_leaf_strings(value))))
    have_numbers = numbers_in(support)
    have_idents = identifiers_in(support)
    text = " ".join(_leaf_strings(value))
    missing = [n for n in sorted(numbers_in(text)) if n not in have_numbers]
    for ident in sorted(identifiers_in(text)):
        if ident in have_idents:
            continue
        # a folded identifier may appear inside a longer one in the evidence
        # (olmo21124 7b inside allenai/olmo21124 7binstruct)
        if any(ident in h for h in have_idents):
            continue
        missing.append(ident)
    return missing
