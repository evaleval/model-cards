"""Total the LLM spend recorded under one or more run directories.

    python scripts/spend.py runs

Reads every llm_usage_*.jsonl it finds and reports calls, tokens, cost and the providers
observed, per run and in total. The usage records are written by the handler itself, so
this is a read of what was billed, not an estimate.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def totals_for(paths):
    calls = tokens_in = tokens_out = 0
    cost = 0.0
    providers = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            calls += 1
            tokens_in += row.get("input_tokens") or 0
            tokens_out += row.get("output_tokens") or 0
            cost += row.get("cost") or 0.0
            if row.get("provider"):
                providers.add(row["provider"])
    return {"calls": calls, "input_tokens": tokens_in, "output_tokens": tokens_out,
            "cost_usd": round(cost, 8), "providers": sorted(providers)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("roots", nargs="+")
    args = ap.parse_args()
    by_run = defaultdict(list)
    for root in args.roots:
        for path in sorted(Path(root).rglob("llm_usage*.jsonl")):
            by_run[str(path.parent)].append(path)
    grand = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}
    providers = set()
    for run, paths in sorted(by_run.items()):
        t = totals_for(paths)
        print(f"{run:44s} calls {t['calls']:5d}  in {t['input_tokens']:8d}  "
              f"out {t['output_tokens']:7d}  USD {t['cost_usd']:.6f}  {','.join(t['providers'])}")
        for k in ("calls", "input_tokens", "output_tokens", "cost_usd"):
            grand[k] += t[k]
        providers |= set(t["providers"])
    grand["cost_usd"] = round(grand["cost_usd"], 8)
    print(f"{'TOTAL':44s} calls {grand['calls']:5d}  in {grand['input_tokens']:8d}  "
          f"out {grand['output_tokens']:7d}  USD {grand['cost_usd']:.6f}  {','.join(sorted(providers))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
