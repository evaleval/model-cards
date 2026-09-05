"""Run-to-run variance between two runs over the same bundles.

    python scripts/variance.py runs/roster12-a runs/roster12-b

The bundle is frozen bytes and the code is the same, so anything that differs is the
model's own answer. Reports, per card and in aggregate: which fields flipped between
filled and Not specified, which filled fields changed value, and how the score rows,
the withhold counts and the cost moved. Numbers only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model_cards.core.schema import (  # noqa: E402
    NOT_APPLICABLE, NOT_SPECIFIED, PUBLIC_FIELD_PATHS, get_field_value,
)


def load(run: Path) -> dict:
    out = {}
    for path in sorted(run.glob("*.public.json")):
        out[path.name.replace(".public.json", "")] = json.loads(path.read_text())
    return out


def filled(card, path):
    section, field = path.split(".", 1)
    value = (card.get(section) or {}).get(field, NOT_SPECIFIED)
    return value not in (NOT_SPECIFIED, NOT_APPLICABLE, None, [], {})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_a")
    ap.add_argument("run_b")
    args = ap.parse_args()
    a, b = load(Path(args.run_a)), load(Path(args.run_b))
    shared = sorted(set(a) & set(b))
    print(f"cards in both runs: {len(shared)} (A {len(a)}, B {len(b)})")

    flips_by_field, changes_by_field = {}, {}
    rows = []
    for slug in shared:
        flips, changes = [], []
        for path in PUBLIC_FIELD_PATHS:
            fa, fb = filled(a[slug], path), filled(b[slug], path)
            section, field = path.split(".", 1)
            va = a[slug][section][field]
            vb = b[slug][section][field]
            if fa != fb:
                flips.append(path)
                flips_by_field[path] = flips_by_field.get(path, 0) + 1
            elif fa and fb and va != vb:
                changes.append(path)
                changes_by_field[path] = changes_by_field.get(path, 0) + 1
        scores_a = a[slug]["evaluation"]["benchmark_scores"]
        scores_b = b[slug]["evaluation"]["benchmark_scores"]
        rows.append({
            "card": slug,
            "filled_a": sum(filled(a[slug], p) for p in PUBLIC_FIELD_PATHS),
            "filled_b": sum(filled(b[slug], p) for p in PUBLIC_FIELD_PATHS),
            "flips": len(flips), "changed": len(changes),
            "scores_a": len(scores_a) if isinstance(scores_a, list) else 0,
            "scores_b": len(scores_b) if isinstance(scores_b, list) else 0,
            "flip_fields": flips,
        })

    print("\n| card | filled A | filled B | flipped | changed | scores A | scores B |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['card']} | {r['filled_a']} | {r['filled_b']} | {r['flips']} | "
              f"{r['changed']} | {r['scores_a']} | {r['scores_b']} |")
    total_slots = len(shared) * len(PUBLIC_FIELD_PATHS)
    total_flips = sum(r["flips"] for r in rows)
    total_changes = sum(r["changed"] for r in rows)
    print(f"\nfield slots compared: {total_slots}")
    print(f"filled/not-specified flips: {total_flips} ({total_flips / total_slots:.1%})")
    print(f"filled both runs, value differs: {total_changes} ({total_changes / total_slots:.1%})")
    print(f"identical: {total_slots - total_flips - total_changes} "
          f"({(total_slots - total_flips - total_changes) / total_slots:.1%})")
    print("flips by field: " + ", ".join(f"{k} {v}" for k, v in sorted(
        flips_by_field.items(), key=lambda kv: -kv[1])))
    print("value changes by field: " + ", ".join(f"{k} {v}" for k, v in sorted(
        changes_by_field.items(), key=lambda kv: -kv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
