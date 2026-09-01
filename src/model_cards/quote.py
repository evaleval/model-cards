"""Small MIT-licensed Composer kernel for exact quote verification.

The normalization and substring verifier are adapted from the public EvalEval
Auto-BenchmarkCards Composer evidence module. The repository license and
NOTICE retain the applicable copyright and license terms.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


_WS_RE = re.compile(r"\s+")
_TYPOGRAPHIC = {
    "‘": "'",
    "’": "'",
    "‚": "'",
    "‛": "'",
    "“": '"',
    "”": '"',
    "„": '"',
    "‟": '"',
    "´": "'",
    "ʼ": "'",
    "‐": "-",
    "‑": "-",
    "‒": "-",
    "–": "-",
    "—": "-",
    "―": "-",
    "−": "-",
}
_TYPO_RE = re.compile("|".join(re.escape(char) for char in _TYPOGRAPHIC))


def normalize_ws(text: str) -> str:
    """Fold typographic punctuation and whitespace without folding case."""

    if not isinstance(text, str):
        raise TypeError("quote inputs must be strings")
    normalized = _TYPO_RE.sub(lambda match: _TYPOGRAPHIC[match.group(0)], text)
    return _WS_RE.sub(" ", normalized).strip()


def verify_quote(norm_quote: str, norm_source: str) -> int | None:
    """Return the normalized start offset for an exact substring, else None."""

    if not norm_quote:
        return None
    index = norm_source.find(norm_quote)
    return index if index >= 0 else None


@dataclass(frozen=True)
class QuoteMatch:
    quote: str
    char_start: int
    char_end: int


def match_quote(quote: str, source_text: str) -> QuoteMatch | None:
    """Normalize both inputs and return a verified span in normalized text."""

    normalized_quote = normalize_ws(quote)
    normalized_source = normalize_ws(source_text)
    start = verify_quote(normalized_quote, normalized_source)
    if start is None:
        return None
    return QuoteMatch(
        quote=normalized_quote,
        char_start=start,
        char_end=start + len(normalized_quote),
    )
