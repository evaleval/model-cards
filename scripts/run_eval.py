"""Prepare and run the model-card evaluation instruments.

    python scripts/run_eval.py prepare-judge  --run runs/roster12-a --out eval/judge-inputs
    python scripts/run_eval.py prepare-screen --run runs/roster12-a --out eval/screen-inputs
    python scripts/run_eval.py probes         --run runs/roster12-a --out eval/probes.jsonl
    python scripts/run_eval.py sample --run runs/batch250 --targets eval/targets-250.json \
        --size 60 --seed 20260910 --out eval/sample.json
    python scripts/run_eval.py estimate --inputs eval/judge-inputs --model claude-sonnet-5
    python scripts/run_eval.py judge   --inputs eval/judge-inputs --out eval/judge-results \
        --model claude-sonnet-5 --max-cost-usd 5
    python scripts/run_eval.py screen  --inputs eval/screen-inputs --out eval/screen-results \
        --model claude-sonnet-5 --max-cost-usd 5 --max-searches 8

prepare, probes, sample and estimate are free and offline. `judge` and `screen` are the
paid commands: one Anthropic call per card, the model's own decoding (claude-sonnet-5
rejects an explicit temperature), a pinned model, a per-run cost
ceiling they refuse to cross, and the instrument id recorded in every result. The screen
additionally uses server-side web search, capped per card, because its question is
whether the card matches the public record and the frozen bundle cannot answer that.
Estimate first, and post the estimate before running either.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_cards.core.eval import judge as J  # noqa: E402
from model_cards.core.eval import probes as P  # noqa: E402
from model_cards.core.eval import sample as S  # noqa: E402
from model_cards.core.eval import screen as SC  # noqa: E402
from model_cards.core.review import load_artifact  # noqa: E402

# USD per million tokens. A model missing here hard-stops the paid path: a cost tripwire
# that silently counts zero is not a tripwire.
PRICING_USD_PER_MTOK = {
    "claude-sonnet-5": {"input": 3.0, "output": 15.0},
    "claude-opus-5": {"input": 5.0, "output": 25.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
}


def artifacts_in(run: Path):
    for path in sorted(run.glob("*.json")):
        if path.name.endswith(".public.json") or path.name in ("run-manifest.json",
                                                               "readout.json"):
            continue
        yield path, load_artifact(path)


def cmd_prepare_judge(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    for path, artifact in artifacts_in(Path(args.run)):
        payload = J.build_input(artifact)
        (out / f"{path.stem}.json").write_text(
            json.dumps(payload, indent=1, ensure_ascii=False), encoding="utf-8")
        written += 1
    print(json.dumps({"inputs": written, "instrument": J.instrument_id(),
                      "version": J.JUDGE_PROMPT_VERSION, "out": str(out)}, indent=1))
    return 0


def cmd_prepare_screen(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    for path, artifact in artifacts_in(Path(args.run)):
        (out / f"{path.stem}.json").write_text(
            json.dumps(SC.build_input(artifact), indent=1, ensure_ascii=False),
            encoding="utf-8")
        written += 1
    print(json.dumps({"inputs": written, "instrument": SC.instrument_id(),
                      "prompt_prefix_md5": SC.prompt_prefix_md5(), "out": str(out)}, indent=1))
    return 0


def cmd_probes(args) -> int:
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    from model_cards.core.public import public_projection
    from model_cards.core.review import export_reviewed_card

    lines, cards = [], 0
    for _path, artifact in artifacts_in(Path(args.run)):
        sources = {f.name: (f.content or "")
                   for f in (artifact.source_bundle.files if artifact.source_bundle else [])}
        card = public_projection(export_reviewed_card(artifact))
        base_tags, structured = [], set()
        for binding in artifact.bindings:
            if binding.field_path.startswith("lineage.base_models") and isinstance(
                    binding.proposed_value, dict):
                base_tags.append(binding.proposed_value.get("model_id", ""))
            if (binding.verifier_action.value == "accept"
                    and binding.assignment_origin.value == "structured_explicit"):
                structured.add(binding.field_path.split("[", 1)[0])
        cards += 1
        for probe in P.probes_for(card, artifact.target.model_id, base_tags, sources,
                                  structured_fields=structured):
            lines.append(json.dumps({"target": artifact.target.canonical_target, **probe},
                                    ensure_ascii=False))
    out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    print(json.dumps({"cards": cards, "probes": len(lines), "out": str(out),
                      "predicate": "surface_token_match_nearest_declared_name"}, indent=1))
    return 0


def cmd_sample(args) -> int:
    index = S.targets_index(Path(args.targets)) if args.targets else {}
    population = S.population_from_run(Path(args.run), index)
    paired = json.loads(Path(args.paired).read_text()) if args.paired else None
    result = S.draw(population, args.size, args.seed, paired)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("seed", "requested", "drawn", "population",
                                             "paired_available", "stratum_counts")},
                     indent=1))
    print(args.out)
    return 0


def _estimate_tokens(path: Path) -> int:
    """Characters over four is the usual rough token count; it is an upper-bound guide,
    not a billing figure."""
    return len(path.read_text(encoding="utf-8")) // 4


def cmd_estimate(args) -> int:
    inputs = sorted(Path(args.inputs).glob("*.json"))
    if args.model not in PRICING_USD_PER_MTOK:
        print(f"no pricing entry for {args.model}", file=sys.stderr)
        return 2
    price = PRICING_USD_PER_MTOK[args.model]
    tokens_in = sum(_estimate_tokens(p) for p in inputs)
    tokens_out = len(inputs) * args.max_tokens
    cost = tokens_in / 1e6 * price["input"] + tokens_out / 1e6 * price["output"]
    print(json.dumps({
        "cards": len(inputs), "model": args.model,
        "estimated_input_tokens": tokens_in,
        "assumed_output_tokens": tokens_out,
        "upper_bound_usd": round(cost, 2),
        "note": "output is assumed at the full cap for every card, so this is an upper bound",
    }, indent=1))
    return 0


def cmd_judge(args) -> int:
    import anthropic

    if args.model not in PRICING_USD_PER_MTOK:
        print(f"no pricing entry for {args.model}; add one before spending", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2
    price = PRICING_USD_PER_MTOK[args.model]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic(timeout=float(args.timeout), max_retries=2)
    tool = {"name": "record_verdict", "description": "Record the faithfulness verdict.",
            "input_schema": J.JUDGE_SCHEMA}
    spent, done, failed = 0.0, 0, 0
    for path in sorted(Path(args.inputs).glob("*.json")):
        result_path = out / path.name
        if args.resume and result_path.is_file():
            continue
        if spent >= args.max_cost_usd:
            print(f"stopping: spent USD {spent:.4f} of the USD {args.max_cost_usd:.2f} cap")
            break
        payload = json.loads(path.read_text(encoding="utf-8"))
        message = (J.JUDGE_PROMPT + "\n\nINPUT:\n"
                   + json.dumps(payload, ensure_ascii=False))
        started = time.monotonic()
        try:
            # no temperature: claude-sonnet-5 rejects the parameter outright
            # ("`temperature` is deprecated for this model", 400, seen 2026-09-07), so
            # the recorded decoding for this instrument is the model's own default.
            reply = client.messages.create(
                model=args.model, max_tokens=args.max_tokens,
                tools=[tool], tool_choice={"type": "tool", "name": "record_verdict"},
                messages=[{"role": "user", "content": message}])
        except Exception as exc:
            failed += 1
            print(f"{path.stem}: {type(exc).__name__}: {exc}"[:200], file=sys.stderr)
            continue
        verdict = next((block.input for block in reply.content
                        if getattr(block, "type", "") == "tool_use"), None)
        cost = (reply.usage.input_tokens / 1e6 * price["input"]
                + reply.usage.output_tokens / 1e6 * price["output"])
        spent += cost
        done += 1
        result_path.write_text(json.dumps({
            "target": payload["target"], "instrument": payload["instrument"],
            "judge_model": args.model, "verdict": verdict,
            "summary": J.summarize((verdict or {}).get("field_verdicts") or []),
            "usage": {"input_tokens": reply.usage.input_tokens,
                      "output_tokens": reply.usage.output_tokens,
                      "cost_usd": round(cost, 6),
                      "wall_s": round(time.monotonic() - started, 2)},
        }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"judged": done, "failed": failed, "spent_usd": round(spent, 4),
                      "cap_usd": args.max_cost_usd, "out": str(out)}, indent=1))
    return 1 if failed else 0


def cmd_screen(args) -> int:
    import anthropic

    if args.model not in PRICING_USD_PER_MTOK:
        print(f"no pricing entry for {args.model}; add one before spending", file=sys.stderr)
        return 2
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set", file=sys.stderr)
        return 2
    price = PRICING_USD_PER_MTOK[args.model]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic(timeout=float(args.timeout), max_retries=2)
    tools = [
        {"type": "web_search_20250305", "name": "web_search",
         "max_uses": args.max_searches},
        {"name": "record_screen", "description": "Record the audit verdict.",
         "input_schema": SC.SCREEN_SCHEMA},
    ]
    spent, done, failed = 0.0, 0, 0
    for path in sorted(Path(args.inputs).glob("*.json")):
        result_path = out / path.name
        if args.resume and result_path.is_file():
            continue
        if spent >= args.max_cost_usd:
            print(f"stopping: spent USD {spent:.4f} of the USD {args.max_cost_usd:.2f} cap")
            break
        payload = json.loads(path.read_text(encoding="utf-8"))
        message = (payload["prompt"] + "\n\nThe card under audit, and where it came from:\n"
                   + json.dumps({"target": payload["target"], "hub_url": payload["hub_url"],
                                 "card": payload["card"]}, ensure_ascii=False))
        started = time.monotonic()
        try:
            reply = client.messages.create(
                model=args.model, max_tokens=args.max_tokens,
                tools=tools, messages=[{"role": "user", "content": message}])
        except Exception as exc:
            failed += 1
            print(f"{path.stem}: {type(exc).__name__}: {exc}"[:200], file=sys.stderr)
            continue
        verdict = next((block.input for block in reply.content
                        if getattr(block, "type", "") == "tool_use"
                        and getattr(block, "name", "") == "record_screen"), None)
        searches = sum(1 for block in reply.content
                       if getattr(block, "type", "") == "server_tool_use")
        cost = (reply.usage.input_tokens / 1e6 * price["input"]
                + reply.usage.output_tokens / 1e6 * price["output"])
        spent += cost
        done += 1
        result_path.write_text(json.dumps({
            "target": payload["target"], "instrument": payload["instrument"],
            "screen_model": args.model, "verdict": verdict, "web_searches": searches,
            "usage": {"input_tokens": reply.usage.input_tokens,
                      "output_tokens": reply.usage.output_tokens,
                      "cost_usd": round(cost, 6),
                      "wall_s": round(time.monotonic() - started, 2)},
        }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"screened": done, "failed": failed, "spent_usd": round(spent, 4),
                      "cap_usd": args.max_cost_usd,
                      "note": "web search is billed separately from tokens", "out": str(out)},
                     indent=1))
    return 1 if failed else 0


def cmd_summarize(args) -> int:
    """Aggregate a directory of judge or screen results. Free and offline."""
    results = [json.loads(p.read_text(encoding="utf-8"))
               for p in sorted(Path(args.results).glob("*.json"))]
    results = [r for r in results if isinstance(r, dict) and "verdict" in r]
    if not results:
        print("no result files here: a result carries a 'verdict'; this looks like an "
              "inputs directory", file=sys.stderr)
        return 2
    instruments = sorted({r["instrument"]["id"] for r in results if r.get("instrument")})
    if len(instruments) > 1:
        # a reworded prompt is a different instrument, and pooling the two would report a
        # number that answers no single question
        print(f"refusing to pool {len(instruments)} instruments: {instruments}",
              file=sys.stderr)
        return 2
    if any("field_verdicts" in (r.get("verdict") or {}) for r in results):
        merged = [v for r in results for v in (r["verdict"] or {}).get("field_verdicts", [])]
        summary = {"kind": "judge", "cards": len(results), **J.summarize(merged)}
    else:
        summary = {"kind": "screen",
                   **SC.summarize([r["verdict"] for r in results if r.get("verdict")])}
    summary["instrument"] = instruments[0] if instruments else None
    summary["total_cost_usd"] = round(sum((r.get("usage") or {}).get("cost_usd", 0.0)
                                          for r in results), 6)
    print(json.dumps(summary, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    for name, handler in (("prepare-judge", cmd_prepare_judge),
                          ("prepare-screen", cmd_prepare_screen)):
        p = sub.add_parser(name)
        p.add_argument("--run", required=True)
        p.add_argument("--out", required=True)
        p.set_defaults(handler=handler)

    p = sub.add_parser("probes")
    p.add_argument("--run", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(handler=cmd_probes)

    p = sub.add_parser("sample")
    p.add_argument("--run", required=True)
    p.add_argument("--targets")
    p.add_argument("--paired", help="json list of targets that also have a deterministic card")
    p.add_argument("--size", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(handler=cmd_sample)

    p = sub.add_parser("estimate")
    p.add_argument("--inputs", required=True)
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--max-tokens", type=int, default=8000)
    p.set_defaults(handler=cmd_estimate)

    p = sub.add_parser("screen")
    p.add_argument("--inputs", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--max-tokens", type=int, default=16000)
    p.add_argument("--max-searches", type=int, default=8)
    p.add_argument("--max-cost-usd", type=float, required=True)
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--resume", action="store_true")
    p.set_defaults(handler=cmd_screen)

    p = sub.add_parser("summarize")
    p.add_argument("--results", required=True)
    p.set_defaults(handler=cmd_summarize)

    p = sub.add_parser("judge")
    p.add_argument("--inputs", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--max-tokens", type=int, default=8000)
    p.add_argument("--max-cost-usd", type=float, required=True)
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--resume", action="store_true")
    p.set_defaults(handler=cmd_judge)

    args = ap.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
