"""Exact-id join from a model target to its Every Eval Ever records.

The EEE datastore snapshot is laid out data/<benchmark>/<developer>/<model>/<uuid>.json,
so a clean Hugging Face model id is a directory lookup. The join tier is recorded with
the result: exact (the id matches a directory verbatim), case_insensitive (only the
casing differs), none. Nothing fuzzier: 62% of the snapshot sits under developer
"unknown" and free-text alphaxiv names, and resolving those is Jenny's registry's job,
not this card's.
"""

from __future__ import annotations

import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def default_datastore_dir() -> Optional[str]:
    """The newest local EEE datastore snapshot's data/ directory, or None."""
    env = os.environ.get("EEE_DATASTORE_DIR")
    if env and os.path.isdir(env):
        return env
    home = Path.home()
    pattern = str(home / ".cache/huggingface/hub/datasets--evaleval--EEE_datastore/snapshots/*/data")
    hits = sorted(glob.glob(pattern), key=os.path.getmtime)
    return hits[-1] if hits else None


def _record_summary(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path) as f:
            rec = json.load(f)
    except Exception:
        return []
    out = []
    for r in rec.get("evaluation_results") or []:
        if not isinstance(r, dict):
            continue
        metric = r.get("metric_config") or {}
        out.append({
            "evaluation_name": r.get("evaluation_name"),
            "metric_name": metric.get("metric_name"),
            "metric_id": metric.get("metric_id"),
            "score": (r.get("score_details") or {}).get("score"),
            "hf_repo": (r.get("source_data") or {}).get("hf_repo"),
            "evaluation_result_id": r.get("evaluation_result_id"),
            "source_file": path,
        })
    return out


def find_eee_records(model_id: str, datastore_dir: Optional[str] = None) -> Dict[str, Any]:
    """Records for a model id, keyed by benchmark directory, with the join tier.

    Returns {"model_id", "tier", "matched_id", "benchmarks": {<benchmark>: [rows]},
    "record_files": [...]}. tier is "exact", "case_insensitive", or "none".
    """
    root = datastore_dir or default_datastore_dir()
    result: Dict[str, Any] = {"model_id": model_id, "tier": "none", "matched_id": None,
                              "benchmarks": {}, "record_files": []}
    if not root or "/" not in model_id:
        return result
    developer, model = model_id.split("/", 1)
    # glob is case-insensitive on macOS, so an "exact" hit is confirmed against the real
    # directory names before it earns the exact tier
    exact_dirs = [d for d in sorted(glob.glob(os.path.join(root, "*", developer, model)))
                  if model in os.listdir(os.path.dirname(d))
                  and developer in os.listdir(os.path.dirname(os.path.dirname(d)))]
    matched_id = model_id
    tier = "exact" if exact_dirs else "none"
    dirs = exact_dirs
    if not dirs:
        wanted = model_id.lower()
        for bench_dir in sorted(glob.glob(os.path.join(root, "*"))):
            for dev_dir in glob.glob(os.path.join(bench_dir, "*")):
                for model_dir in glob.glob(os.path.join(dev_dir, "*")):
                    candidate = f"{os.path.basename(dev_dir)}/{os.path.basename(model_dir)}"
                    if candidate.lower() == wanted:
                        dirs.append(model_dir)
                        matched_id = candidate
        if dirs:
            tier = "case_insensitive"
    for d in dirs:
        benchmark = os.path.basename(os.path.dirname(os.path.dirname(d)))
        for path in sorted(glob.glob(os.path.join(d, "*.json"))):
            result["record_files"].append(path)
            result["benchmarks"].setdefault(benchmark, []).extend(_record_summary(path))
    result["tier"] = tier if dirs else "none"
    result["matched_id"] = matched_id if dirs else None
    return result
