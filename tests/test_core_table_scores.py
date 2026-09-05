"""Deterministic score rows: only the row whose label is the target, never a comparison."""

from model_cards.core.table_scores import target_score_rows


README = """# OLMo 2

| Model | MMLU (5-shot) | GSM8K | HumanEval |
|---|---|---|---|
| **OLMo 2 7B** | 63.7 | 67.5 | 20.1 |
| Llama 3.1 8B | 66.7 | 56.0 | 33.5 |
| OLMo 2 13B | 67.5 | 75.1 | 28.0 |

| | Avg |
|---|---|
| OLMo-2-1124-7B-Instruct | 61.2 |
"""


def test_only_the_target_row_yields_scores():
    rows = target_score_rows(README, ["OLMo-2-1124-7B", "OLMo 2 7B", "allenai/OLMo-2-1124-7B"], "hf_readme")
    assert [(r["benchmark"], r["score"], r["setting"]) for r in rows] == [
        ("MMLU", "63.7", "5-shot"), ("GSM8K", "67.5", "Not specified"), ("HumanEval", "20.1", "Not specified")]
    assert rows[0]["row_text"] == "| **OLMo 2 7B** | 63.7 | 67.5 | 20.1 |"
    assert rows[0]["header"] == ["Model", "MMLU (5-shot)", "GSM8K", "HumanEval"]
    # the 13B sibling and the Llama comparison never match, and the Instruct table's
    # row belongs to a different checkpoint
    assert not any("Llama" in r["row_text"] or "13B" in r["row_text"] or "Instruct" in r["row_text"] for r in rows)


def test_instruct_alias_matches_its_own_row_only():
    rows = target_score_rows(README, ["OLMo-2-1124-7B-Instruct", "OLMo 2 7B Instruct"], "hf_readme")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("Avg", "61.2")]


def test_training_cost_table_is_not_a_results_table():
    # the OLMo 2 paper's compute table: GPU hours, power, carbon; the row names the
    # target and every cell is numeric, yet none of it is a benchmark score
    cost = ("| Model | GPU Power Consumption (MWh) | Power Usage Effectiveness | Carbon Intensity "
            "(kg CO2e/KWh) | GPU Hours | Carbon Emissions (tCO2eq) | Water (L) |\n"
            "|---|---|---|---|---|---|---|\n| OLMo 2 7B | 131 | 1.2 | 0.332 | 52 | 1.29 | 202 |\n")
    assert target_score_rows(cost, ["OLMo 2 7B"], "docling") == []
    from model_cards.core.table_scores import header_is_results_table
    assert header_is_results_table(["Model", "MMLU", "GSM8K"]) is True
    assert header_is_results_table(["Model", "Training FLOPs", "Average", "ARC/C"]) is True   # FLOPs column beside scores
    assert header_is_results_table(["Model", "Params", "Context Length", "Release Date"]) is False
    assert header_is_results_table(["", "Tokens", "Steps"]) is False


def test_non_numeric_cells_and_empty_headers_are_skipped():
    text = "| Model | Notes | Score |\n|---|---|---|\n| Zorb | fine | 88.5% |\n"
    rows = target_score_rows(text, ["Zorb"], "docling")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("Score", "88.5%")]


def test_a_benchmark_major_table_is_read_down_the_targets_column():
    """Failure class: transposed_table_unreadable. A technical report writes one row per
    benchmark and one column per model. Reading only model-major tables returned no
    scores at all for three of the six 2026-09-04 acceptance targets, including every
    number in the Qwen3 and DeepSeek-V3 reports."""
    from model_cards.core.table_scores import target_score_rows

    table = (
        "Table 5: results in the thinking mode\n"
        "| Benchmark | Qwen3-8B | Qwen3-14B | Llama-3.1-8B |\n"
        "|---|---|---|---|\n"
        "| MMLU-Redux | 87.5 | 89.1 | 66.7 |\n"
        "| GPQA-Diamond (pass@1) | 62.0 | 64.0 | 32.8 |\n"
        "| # Total Params | 8B | 14B | 8B |\n"
        "| Architecture | dense | dense | dense |\n"
    )
    rows = target_score_rows(table, ["Qwen3-8B", "Qwen3 8B"], "docling")
    assert [(r["benchmark"], r["score"]) for r in rows] == [
        ("MMLU-Redux", "87.5"), ("GPQA-Diamond", "62.0")]
    assert all(r["orientation"] == "benchmark_major" for r in rows)
    # the metric and setting still travel with the score
    assert rows[1]["metric"] == "pass@1"
    assert rows[0]["setting"] == "thinking"
    # a sibling's column and a comparison model's column are never read
    assert not any(r["score"] in {"89.1", "66.7", "64.0", "32.8"} for r in rows)
    # the row anchor is the line the number came from
    assert rows[0]["row_text"] == "| MMLU-Redux | 87.5 | 89.1 | 66.7 |"


def test_a_model_major_table_is_still_read_across_the_targets_row():
    from model_cards.core.table_scores import target_score_rows

    table = ("| Model | MMLU | HumanEval (pass@1) |\n|---|---|---|\n"
             "| OLMo 2 7B | 63.7 | 22.0 |\n| Llama 3.1 8B | 66.7 | 37.8 |\n")
    rows = target_score_rows(table, ["OLMo 2 7B"], "hf_readme")
    assert [(r["benchmark"], r["score"], r["orientation"]) for r in rows] == [
        ("MMLU", "63.7", "model_major"), ("HumanEval", "22.0", "model_major")]


def test_a_column_header_that_is_a_sibling_is_not_the_targets_column():
    """The base and the instruct checkpoint sit in neighbouring columns of one table."""
    from model_cards.core.table_scores import target_score_rows

    table = ("| Benchmark | DeepSeek-V3-Base | DeepSeek-V3 |\n|---|---|---|\n"
             "| MMLU (EM) | 87.1 | 88.5 |\n")
    base = target_score_rows(table, ["DeepSeek-V3-Base", "DeepSeek V3 Base"], "docling")
    assert [(r["benchmark"], r["score"], r["metric"]) for r in base] == [
        ("MMLU", "87.1", "exact match")]
    instruct = target_score_rows(table, ["DeepSeek-V3", "DeepSeek V3"], "docling")
    assert [r["score"] for r in instruct] == ["88.5"]


def test_an_architecture_table_is_not_a_results_table():
    """Failure class: config_row_read_as_a_score. A report's architecture table has one
    column per model too, and its rows are configuration, not results."""
    from model_cards.core.table_scores import target_score_rows

    table = ("| | Qwen3-8B | Qwen3-14B |\n|---|---|---|\n"
             "| Layers | 36 | 40 |\n| Hidden Size | 4096 | 5120 |\n"
             "| # KV Heads | 8 | 8 |\n| Context Length | 32768 | 32768 |\n"
             "| Vocab Size | 151936 | 151936 |\n| MMLU | 76.89 | 81.05 |\n")
    rows = target_score_rows(table, ["Qwen3-8B"], "docling")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "76.89")]
