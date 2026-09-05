"""Exact-id EEE join with a recorded tier; no fuzzy matching."""

import json

from model_cards.core.eee_join import find_eee_records


def _write(root, benchmark, developer, model, uuid, results):
    d = root / benchmark / developer / model
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{uuid}.json").write_text(json.dumps({
        "model_info": {"id": f"{developer}/{model}", "developer": developer},
        "evaluation_results": [
            {"evaluation_name": name, "metric_config": {"metric_name": "Accuracy", "metric_id": "acc"},
             "score_details": {"score": score}, "source_data": {"hf_repo": "x/y"},
             "evaluation_result_id": f"{benchmark}/{developer}_{model}/1#{name}"}
            for name, score in results]}))


def test_exact_join_collects_all_benchmarks(tmp_path):
    _write(tmp_path, "hfopenllm_v2", "allenai", "OLMo-7B-hf", "u1", [("IFEval", 0.27), ("BBH", 0.31)])
    _write(tmp_path, "helm_lite", "allenai", "OLMo-7B-hf", "u2", [("MMLU", 0.5)])
    out = find_eee_records("allenai/OLMo-7B-hf", str(tmp_path))
    assert out["tier"] == "exact" and out["matched_id"] == "allenai/OLMo-7B-hf"
    assert sorted(out["benchmarks"]) == ["helm_lite", "hfopenllm_v2"]
    assert [r["evaluation_name"] for r in out["benchmarks"]["hfopenllm_v2"]] == ["IFEval", "BBH"]
    assert out["benchmarks"]["helm_lite"][0]["score"] == 0.5
    assert len(out["record_files"]) == 2


def test_case_insensitive_tier_is_recorded(tmp_path):
    _write(tmp_path, "hfopenllm_v2", "allenai", "OLMo-7B-hf", "u1", [("IFEval", 0.27)])
    out = find_eee_records("allenai/olmo-7b-hf", str(tmp_path))
    assert out["tier"] == "case_insensitive" and out["matched_id"] == "allenai/OLMo-7B-hf"
    assert out["benchmarks"]["hfopenllm_v2"][0]["score"] == 0.27


def test_no_fuzzy_join(tmp_path):
    _write(tmp_path, "hfopenllm_v2", "allenai", "OLMo-7B-hf", "u1", [("IFEval", 0.27)])
    out = find_eee_records("allenai/OLMo-7B", str(tmp_path))
    assert out["tier"] == "none" and out["benchmarks"] == {} and out["matched_id"] is None
    assert find_eee_records("not-a-hub-id", str(tmp_path))["tier"] == "none"
