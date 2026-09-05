"""Readout over a run directory of composed card artifacts.

    python scripts/readout.py runs/<run> [--usage-dir runs/<run>]

Fill rate by field, withholds by reason and by field, relations actually used, score
rows by source document, quote verification, and cost per card from the per-card usage
logs the batch runner writes next to each artifact. Writes readout.json into the run
directory and prints the markdown table. Numbers only; no judgement.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_cards.core.review import load_artifact  # noqa: E402
from model_cards.core.schema import NOT_APPLICABLE, NOT_SPECIFIED, CARD_FIELD_PATHS, get_field_value  # noqa: E402


def _cost(usage_path: Path):
    if not usage_path.is_file():
        return None, None
    rows = [json.loads(line) for line in usage_path.read_text().splitlines() if line.strip()]
    return len(rows), round(sum(r.get("cost") or 0.0 for r in rows), 4)


def readout(cards_dir: Path, usage_dir: Path):
    fields = [p for p in CARD_FIELD_PATHS if not p.startswith("provenance_and_quality.")]
    per_card = []
    fill = Counter()
    na = Counter()
    withhold_reasons = Counter()
    withhold_fields = Counter()
    origins = Counter()
    relations = Counter()
    for path in sorted(cards_dir.glob("*.json")):
        # the run directory also holds the published projections and the manifest
        if path.name in ("readout.json", "run-manifest.json") or path.name.endswith(".public.json"):
            continue
        art = load_artifact(path)
        card = art.card
        filled = []
        for p in fields:
            v = get_field_value(card, p)
            if v == NOT_APPLICABLE:
                na[p] += 1
            elif v not in (NOT_SPECIFIED, [NOT_SPECIFIED], None, [], {}):
                fill[p] += 1
                filled.append(p)
        withheld = [b for b in art.bindings if b.verifier_action.value == "withhold"]
        for b in withheld:
            withhold_reasons[b.verifier_reason] += 1
            withhold_fields[b.field_path.split("[", 1)[0]] += 1
        for b in art.bindings:
            if not b.field_path.startswith("provenance_and_quality"):
                origins[(b.assignment_origin.value, b.verifier_action.value)] += 1
                relations[(b.relation_to_target.value, b.verifier_action.value)] += 1
        scores = [b for b in art.bindings if b.field_path.startswith("evaluation.benchmark_scores[")]
        by_src = Counter(b.evidence[0].source_uri.rsplit("/", 1)[-1].split("#")[0][:24] for b in scores
                         if b.verifier_action.value == "accept")
        qv = art.metadata.get("quote_verify", {})
        calls, cost = _cost(usage_dir / f"llm_usage_{path.stem}.jsonl")
        per_card.append({
            "target": art.target.canonical_target, "artifact": path.name,
            "coverage": card["provenance_and_quality"]["coverage_score"],
            "filled": len(filled), "withheld": len(withheld),
            "score_rows": dict(by_src), "quotes": {k: qv.get(k) for k in ("emitted", "verified", "rejected", "gap_calls", "gap_verified")},
            "by_doc": {k: (v.get("emitted"), v.get("verified")) for k, v in (qv.get("by_doc") or {}).items()},
            "rejected_samples": qv.get("rejected_samples", [])[:6],
            "frame": art.metadata.get("frame", {}).get("builder_counts", {}),
            "gates": art.metadata.get("gates", {}), "eav": art.metadata.get("eav", {}),
            "calls": calls, "cost_usd": cost,
        })
    n = len(per_card)
    summary = {
        "cards": n,
        "fill_rate_by_field": {p: {"filled": fill[p], "not_applicable": na[p], "rate": round(fill[p] / n, 3) if n else None} for p in fields},
        "withhold_reasons": dict(withhold_reasons), "withhold_fields": dict(withhold_fields),
        "bindings_by_origin_action": {f"{o}/{a}": c for (o, a), c in origins.items()},
        "bindings_by_relation_action": {f"{r}/{a}": c for (r, a), c in sorted(relations.items())},
        "mean_coverage": round(sum(c["coverage"] for c in per_card) / n, 3) if n else None,
        "total_calls": sum(c["calls"] or 0 for c in per_card), "total_cost_usd": round(sum(c["cost_usd"] or 0 for c in per_card), 4),
        "per_card": per_card,
    }
    return summary


def markdown(summary) -> str:
    n = summary["cards"]
    out = [f"Cards: {n}, mean coverage {summary['mean_coverage']}, calls {summary['total_calls']}, cost ${summary['total_cost_usd']}", "",
           "| field | filled | N/A | rate |", "|---|---|---|---|"]
    for p, v in summary["fill_rate_by_field"].items():
        out.append(f"| {p} | {v['filled']} | {v['not_applicable']} | {v['rate']} |")
    out += ["", "Withholds by reason: " + ", ".join(f"{k} {v}" for k, v in sorted(summary["withhold_reasons"].items())),
            "Withholds by field: " + ", ".join(f"{k} {v}" for k, v in sorted(summary["withhold_fields"].items())),
            "Bindings by origin/action: " + ", ".join(f"{k} {v}" for k, v in sorted(summary["bindings_by_origin_action"].items())),
            "Bindings by relation/action: " + ", ".join(f"{k} {v}" for k, v in sorted(summary["bindings_by_relation_action"].items())), "",
            "| card | coverage | filled | withheld | score rows | quotes emitted/verified | gap | calls | cost |", "|---|---|---|---|---|---|---|---|---|"]
    for c in summary["per_card"]:
        q = c["quotes"]
        out.append(f"| {c['target'].split('@')[0]} | {c['coverage']} | {c['filled']} | {c['withheld']} | {sum(c['score_rows'].values())} "
                   f"| {q.get('emitted')}/{q.get('verified')} | {q.get('gap_verified')} | {c['calls']} | {c['cost_usd']} |")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cards_dir")
    ap.add_argument("--usage-dir", default=None)
    args = ap.parse_args()
    cards = Path(args.cards_dir)
    summary = readout(cards, Path(args.usage_dir) if args.usage_dir else cards)
    (cards / "readout.json").write_text(json.dumps(summary, indent=1))
    print(markdown(summary))


if __name__ == "__main__":
    main()
