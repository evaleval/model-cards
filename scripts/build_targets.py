"""Build the evaluation target list from the EEE datastore and the Hub.

    python scripts/build_targets.py --out eval/targets-250.json --count 250

Two strata, drawn with a fixed seed so the list is reproducible:

  flagship   checkpoints from the organizations that publish the models the field
             actually compares against, taken as base/instruct pairs wherever both
             members exist, because a pair is where checkpoint confusion happens;
  community  models from the hfopenllm_v2 stratum of the datastore, which is what the
             open leaderboard is mostly made of: merges, fine-tunes and re-uploads.

Every candidate is checked against the Hub API: it has to exist, and its resolved commit
is recorded so the target is a revision and not a moving branch. Gating is recorded, not
excluded: a gated repo degrades to README-only and that degradation is worth measuring.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional

FLAGSHIP_ORGS = (
    "meta-llama", "Qwen", "google", "mistralai", "deepseek-ai", "allenai", "microsoft",
    "HuggingFaceTB", "ibm-granite", "tiiuae", "CohereLabs", "CohereForAI", "nvidia",
    "openai", "Zyphra", "LGAI-EXAONE", "upstage", "01-ai", "internlm", "THUDM",
    "stabilityai", "EleutherAI", "bigscience", "facebook", "BAAI", "moonshotai",
    "MiniMaxAI", "utter-project", "OpenGVLab", "rinna", "sarvamai", "inclusionAI",
)
# The stage a repo name declares. A pair is the same stem with and without one of these.
_STAGE_SUFFIX_RE = re.compile(
    r"-(instruct|it|chat|sft|dpo|rlhf|instruct-v0\.[0-9]+|thinking|reasoning)$",
    re.IGNORECASE)


def datastore_models(data_dir: Path, benchmark: str) -> List[str]:
    """owner/name for every model directory under one benchmark of the snapshot."""
    root = data_dir / benchmark
    if not root.is_dir():
        return []
    out = []
    for owner in sorted(p for p in root.iterdir() if p.is_dir()):
        for model in sorted(p for p in owner.iterdir() if p.is_dir()):
            out.append(f"{owner.name}/{model.name}")
    return out


def pair_stem(model_id: str) -> str:
    return _STAGE_SUFFIX_RE.sub("", model_id)


def resolve(model_id: str) -> Optional[Dict[str, Any]]:
    """The Hub's view of one model, or None when it does not exist here."""
    from huggingface_hub import HfApi

    try:
        info = HfApi().model_info(model_id)
    except Exception as exc:
        return {"model_id": model_id, "error": f"{type(exc).__name__}: {exc}"[:160]}
    return {
        # the id the Hub itself reports, which is the canonical spelling: the datastore
        # lists the same repo under more than one casing, and a case-insensitive bundle
        # slug then makes two targets write the same card
        "model_id": info.id or model_id, "requested_as": model_id, "revision": info.sha,
        "gated": str(info.gated) if info.gated else "false",
        "downloads": info.downloads, "likes": info.likes,
        "pipeline_tag": info.pipeline_tag, "library_name": info.library_name,
        "tags": [t for t in (info.tags or []) if t.startswith(("arxiv:", "base_model:",
                                                              "license:"))][:12],
        "created_at": info.created_at.isoformat() if info.created_at else None,
    }


def resolve_many(model_ids: List[str], workers: int = 8) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(resolve, mid): mid for mid in model_ids}
        for fut in as_completed(futures):
            row = fut.result()
            if row:
                out[row["model_id"]] = row
    return out


def build(data_dir: Path, count: int, flagship_count: int, seed: int) -> Dict[str, Any]:
    rng = random.Random(seed)
    everything = sorted({m for bench in (p.name for p in data_dir.iterdir() if p.is_dir())
                         for m in datastore_models(data_dir, bench)})
    community_pool = sorted(set(datastore_models(data_dir, "hfopenllm_v2")))
    flagship_pool = [m for m in everything if m.split("/", 1)[0] in FLAGSHIP_ORGS]

    # flagship: pairs first, so base and instruct of the same stem travel together
    by_stem: Dict[str, List[str]] = defaultdict(list)
    for model in flagship_pool:
        by_stem[pair_stem(model)].append(model)
    paired = [stem for stem, members in by_stem.items() if len(members) >= 2]
    rng.shuffle(paired)
    flagship: List[str] = []
    # over-draw both strata: a datastore id can name a repo that has since been renamed,
    # made private or deleted, and the list has to reach its size after those drop out
    for stem in paired:
        if len(flagship) >= flagship_count * 2:
            break
        flagship.extend(sorted(by_stem[stem])[:2])
    singles = [m for m in flagship_pool if m not in set(flagship)]
    rng.shuffle(singles)
    while len(flagship) < flagship_count * 2 and singles:
        flagship.append(singles.pop())

    community = [m for m in community_pool if m not in set(flagship)]
    rng.shuffle(community)
    community = community[: max(0, count - flagship_count) * 2]

    resolved = resolve_many(flagship + community)
    targets: List[Dict[str, Any]] = []
    seen_stems: set = set()
    seen_ids: set = set()
    quota = {"flagship": flagship_count, "community": count - flagship_count}
    for stratum, pool in (("flagship", flagship), ("community", community)):
        for model_id in pool:
            row = resolved.get(model_id) or {}
            if row.get("error") or not row.get("revision"):
                continue
            canonical = (row["model_id"], row["revision"])
            if canonical in seen_ids:
                continue
            if len([t for t in targets if t["stratum"] == stratum]) >= quota[stratum]:
                break
            seen_ids.add(canonical)
            if stratum == "community":
                # one member per family in the community stratum, so 150 targets are 150
                # different models rather than a handful of merge lineages
                stem = pair_stem(model_id).lower()
                if stem in seen_stems:
                    continue
                seen_stems.add(stem)
            targets.append({**row, "stratum": stratum,
                            "pair_stem": pair_stem(row["model_id"]),
                            "target": f"{row['model_id']}@{row['revision']}"})
    return {
        "snapshot": data_dir.parent.name, "seed": seed, "requested": count,
        "flagship_requested": flagship_count,
        "pool_sizes": {"datastore_models": len(everything),
                       "flagship_candidates": len(flagship_pool),
                       "hfopenllm_v2": len(community_pool)},
        "resolution": {"attempted": len(flagship) + len(community),
                       "resolved": sum(1 for r in resolved.values() if r.get("revision")),
                       "missing": sorted(m for m, r in resolved.items() if r.get("error"))[:40]},
        "duplicates_dropped": len(seen_ids) - len(targets) if len(seen_ids) > len(targets) else 0,
        "counts": {"total": len(targets),
                   "flagship": sum(1 for t in targets if t["stratum"] == "flagship"),
                   "community": sum(1 for t in targets if t["stratum"] == "community"),
                   "gated": sum(1 for t in targets if t["gated"] != "false")},
        "targets": targets,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="EEE datastore snapshot data/ directory")
    ap.add_argument("--out", required=True)
    ap.add_argument("--count", type=int, default=250)
    ap.add_argument("--flagship-count", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20260904)
    args = ap.parse_args()
    result = build(Path(args.data_dir), args.count, args.flagship_count, args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    out.with_suffix(".txt").write_text(
        "\n".join(t["target"] for t in result["targets"]) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("snapshot", "seed", "pool_sizes", "resolution",
                                             "counts")}, indent=1)[:1200])
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
