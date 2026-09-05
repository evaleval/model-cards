"""One tiny structured-output call against the pinned OpenRouter route.

Asserts the observed provider matches the pin and prints latency, tokens and cost from
the handler's own usage record. The credential is read from the environment and never
printed. Run once per session before any generation spend.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_cards.core.route import build_llm, load_env, route  # noqa: E402


def main() -> int:
    load_env()
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("OPENROUTER_API_KEY is not set", file=sys.stderr)
        return 2
    cfg = route()
    llm = build_llm()
    from auto_benchmarkcard.llm_handler import set_usage_log_path

    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "probe.jsonl"
        set_usage_log_path(str(log))
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}},
                  "required": ["ok"], "additionalProperties": False}
        t0 = time.monotonic()
        text, stop = llm.generate_with_meta('Reply with {"ok": true} and nothing else.',
                                            response_format=schema, max_completion_tokens=64)
        elapsed = time.monotonic() - t0
        usage = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1]) if log.is_file() else {}
        set_usage_log_path(None)

    record = {"pin": cfg, "observed_provider": usage.get("provider"),
              "response_format": usage.get("response_format"),
              "latency_s": round(elapsed, 2), "stop_reason": stop,
              "input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens"),
              "cost_usd": usage.get("cost"), "response": (text or "")[:80]}
    print(json.dumps(record, indent=1, sort_keys=True))

    expected = cfg["provider_order"][0]
    if not usage.get("provider") or usage["provider"].lower() != expected.lower():
        print(f"provider mismatch: expected {expected}, got {usage.get('provider')}", file=sys.stderr)
        return 1
    if usage.get("response_format") != "json_schema":
        print("structured output was not requested as json_schema", file=sys.stderr)
        return 1
    try:
        if json.loads(text).get("ok") is not True:
            print("structured output did not return ok=true", file=sys.stderr)
            return 1
    except ValueError:
        print("structured output was not valid JSON", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
