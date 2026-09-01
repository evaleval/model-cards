from __future__ import annotations

import json
from pathlib import Path

from model_cards.bindings import build_artifact


ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_INPUT = ROOT / "examples" / "synthetic-input.json"


def synthetic_specification() -> dict:
    return json.loads(SYNTHETIC_INPUT.read_text(encoding="utf-8"))


def synthetic_artifact():
    return build_artifact(synthetic_specification())
