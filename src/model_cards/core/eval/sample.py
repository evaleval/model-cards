"""The seeded stratified draw, and the paired design against the deterministic cards.

A sample has to be drawn before anything is judged, from a seed, so the cards that get
read are not the cards that looked interesting. The strata are the three things expected
to move the numbers:

  stage         base or instruct: checkpoint confusion lives in the pair
  sources       source-rich (a paper bound and read) or source-limited (README only,
                which every gated repo is)
  provenance    flagship or community: a technical report and a curated README against
                a merge with an inherited one

The paired half is the point of the comparison: where a deterministic card exists for the
same target, both are drawn together so the judge sees them under the same instrument on
the same day, and the difference is not confounded with anything else.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..schema import NOT_APPLICABLE, NOT_SPECIFIED, PUBLIC_FIELD_PATHS, get_field_value

SOURCE_RICH_MIN_PAPER_CHARS = 2000


def card_strata(artifact, manifest_channels: Optional[Dict[str, Any]] = None,
                stratum: str = "unknown") -> Dict[str, str]:
    """The three stratum keys for one card, read from the artifact and its bundle."""
    from ..model_frame import is_derivative_name

    model_id = artifact.target.model_id
    metadata = artifact.metadata or {}
    frame = (metadata.get("frame") or {}).get("builder_counts") or {}
    stage = "instruct" if is_derivative_name(model_id) or frame.get("base") else "base"
    paper_chars = 0
    for source in artifact.source_bundle.files if artifact.source_bundle else []:
        if source.name == "paper.md":
            paper_chars = len(source.content or "")
    sources = "source_rich" if paper_chars >= SOURCE_RICH_MIN_PAPER_CHARS else "source_limited"
    return {"stage": stage, "sources": sources, "provenance": stratum}


def filled_count(card: Dict[str, Any]) -> int:
    return sum(1 for path in PUBLIC_FIELD_PATHS
               if get_field_value(card, path) not in
               (NOT_SPECIFIED, [NOT_SPECIFIED], NOT_APPLICABLE, None, [], {}))


def draw(population: List[Dict[str, Any]], size: int, seed: int,
         paired_targets: Optional[List[str]] = None) -> Dict[str, Any]:
    """A seeded, proportional draw over the stratum cells, paired half first.

    population entries need "target" and "strata". Proportional allocation keeps a small
    cell from vanishing: every non-empty cell contributes at least one card, and the
    remainder is filled in cell order by size, so the draw is reproducible from the seed
    alone.
    """
    rng = random.Random(seed)
    paired = [row for row in population if paired_targets and row["target"] in set(paired_targets)]
    rest = [row for row in population if row not in paired]

    cells: Dict[str, List[Dict[str, Any]]] = {}
    for row in rest:
        key = "|".join(row["strata"][k] for k in ("stage", "sources", "provenance"))
        cells.setdefault(key, []).append(row)
    for members in cells.values():
        rng.shuffle(members)

    chosen: List[Dict[str, Any]] = []
    for row in paired[:size]:
        chosen.append({**row, "why": "paired_with_deterministic_card"})
    remaining = size - len(chosen)
    if remaining > 0 and cells:
        order = sorted(cells, key=lambda key: (-len(cells[key]), key))
        total = sum(len(cells[key]) for key in order)
        quota = {key: max(1, round(remaining * len(cells[key]) / total)) for key in order}
        for key in order:
            for row in cells[key][: quota[key]]:
                if len(chosen) >= size:
                    break
                chosen.append({**row, "why": f"stratum:{key}"})
        index = 0
        while len(chosen) < size:
            key = order[index % len(order)]
            pool = [row for row in cells[key] if row["target"] not in
                    {c["target"] for c in chosen}]
            if pool:
                chosen.append({**pool[0], "why": f"stratum:{key}:fill"})
            index += 1
            if index > len(order) * 50:
                break
    counts: Dict[str, int] = {}
    for row in chosen:
        for key, value in row["strata"].items():
            counts[f"{key}={value}"] = counts.get(f"{key}={value}", 0) + 1
    return {
        "seed": seed, "requested": size, "drawn": len(chosen),
        "population": len(population), "paired_available": len(paired),
        "cells": {key: len(members) for key, members in sorted(cells.items())},
        "stratum_counts": dict(sorted(counts.items())),
        "sample": chosen,
    }


def population_from_run(run_dir: Path, targets_index: Optional[Dict[str, str]] = None
                        ) -> List[Dict[str, Any]]:
    """Every card in a run directory, with its strata, ready to draw from."""
    from ..review import load_artifact

    rows: List[Dict[str, Any]] = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name.endswith(".public.json") or path.name in ("run-manifest.json",
                                                               "readout.json"):
            continue
        artifact = load_artifact(path)
        target = artifact.target.canonical_target
        provenance = (targets_index or {}).get(artifact.target.model_id, "unknown")
        rows.append({"target": target, "artifact": path.name,
                     "strata": card_strata(artifact, stratum=provenance),
                     "filled": filled_count(artifact.card)})
    return rows


def targets_index(targets_json: Path) -> Dict[str, str]:
    """{model_id: stratum} from the target list the batch was drawn from."""
    data = json.loads(targets_json.read_text(encoding="utf-8"))
    return {row["model_id"]: row["stratum"] for row in data.get("targets", [])}
