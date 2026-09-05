"""The roster readout instrument: numbers from artifacts and usage logs, nothing else."""

import importlib.util
import json
from pathlib import Path

from model_cards.core import compose_llm as CL
from model_cards.core.review import save_artifact

from tests.test_core_compose_llm import MODEL, REV, _ScriptedLLM, _write_bundle


def _load_readout():
    spec = importlib.util.spec_from_file_location(
        "readout", Path(__file__).resolve().parents[1] / "scripts" / "readout.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_readout_counts_fill_withholds_scores_and_cost(tmp_path):
    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    cards = tmp_path / "cards"
    cards.mkdir()
    save_artifact(art, cards / "card-a.json")
    (cards / "llm_usage_card-a.jsonl").write_text(
        json.dumps({"cost": 0.004, "provider": "Baidu"}) + "\n" + json.dumps({"cost": 0.006, "provider": "Baidu"}) + "\n")
    R = _load_readout()
    summary = R.readout(cards, cards)
    assert summary["cards"] == 1
    assert summary["fill_rate_by_field"]["identity.model_id"] == {"filled": 1, "not_applicable": 0, "rate": 1.0}
    assert summary["fill_rate_by_field"]["links.system_card"]["filled"] == 0
    assert summary["per_card"][0]["calls"] == 2 and summary["per_card"][0]["cost_usd"] == 0.01
    assert summary["per_card"][0]["score_rows"] == {"2501.00656": 1}          # the paper table row
    assert summary["total_cost_usd"] == 0.01
    assert summary["mean_coverage"] == round(art.card["provenance_and_quality"]["coverage_score"], 3)
    assert "structured_explicit/accept" in summary["bindings_by_origin_action"]
    md = R.markdown(summary)
    assert "| identity.model_id | 1 | 0 | 1.0 |" in md and "| allenai/OLMo-2-1124-7B |" in md
