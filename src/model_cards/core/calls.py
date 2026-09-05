"""Bounded, structured LLM calls, with truncation recorded instead of swallowed.

Every call the pipeline makes runs with a server-enforced JSON schema and a per-call
completion-token cap. Two things made this necessary on the pinned route (measured
2026-09-04 on allenai/OLMo-2-1124-7B-Instruct):

  * an unstructured frame call never returned within ten minutes;
  * a structured Stage-A gap call ran to the engine's full 16,384-token cap, which was
    148 s of the card's 214 s and USD 0.0048 of its USD 0.0103, and produced nothing,
    because a reply cut off mid-JSON parses to zero evidence items.

A call that stops on "length" is therefore counted in the telemetry under
"truncated_calls" and named there, so a silent zero-yield call is visible on the card.
Caps are generous against the observed distribution (Stage A emitted 7 to 1158 output
tokens on the same card); they exist to bound a runaway, not to shape an answer.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

# Generous against the observed distribution (7 to 1,464 output tokens on the roster),
# because a truncated extraction is a near-total loss: the composer salvages the complete
# items but the tail is gone. 6,144 cut the OLMo-2-1124-7B-Instruct README call and the
# card lost its whole training_context section.
STAGE_A_MAX_TOKENS = 12288
EAV_MAX_TOKENS = 4096

EAV_VERDICT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "about_ok": {"type": "boolean"},
                    "field_ok": {"type": "boolean"},
                    "referent": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "about_ok", "field_ok", "referent", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def note_truncation(telemetry: Optional[Dict[str, Any]], label: str) -> None:
    if telemetry is None:
        return
    bucket = telemetry.setdefault("truncated_calls", {})
    bucket[label] = bucket.get(label, 0) + 1


def capped_generate(llm, prompt: str, *, response_format: Dict[str, Any], max_tokens: int,
                    telemetry: Optional[Dict[str, Any]] = None, label: str = "call") -> str:
    """One structured call with a completion-token cap; truncation is recorded."""
    if hasattr(llm, "generate_with_meta"):
        text, stop = llm.generate_with_meta(prompt, response_format=response_format,
                                            max_completion_tokens=max_tokens)
        if stop == "length":
            note_truncation(telemetry, label)
        return text
    return llm.generate(prompt, response_format=response_format)


class SchemaBoundHandler:
    """A handler wrapper for a call site that cannot pass a schema of its own.

    The composer's EAV auditor calls ``llm_handler.generate(prompt)`` with no response
    format. Wrapping the handler gives that call the same structured, capped treatment as
    every other call without editing the pinned composer.
    """

    def __init__(self, inner, response_format: Dict[str, Any], max_tokens: int,
                 telemetry: Optional[Dict[str, Any]] = None, label: str = "eav") -> None:
        self._inner = inner
        self._response_format = response_format
        self._max_tokens = max_tokens
        self._telemetry = telemetry
        self._label = label

    def generate(self, prompt: str, response_format: Optional[Dict[str, Any]] = None) -> str:
        return capped_generate(self._inner, prompt,
                               response_format=response_format or self._response_format,
                               max_tokens=self._max_tokens, telemetry=self._telemetry,
                               label=self._label)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)
