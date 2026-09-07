"""The nine ways a genuine quote lands on the wrong card, one fixture each.

The earlier evaluation of generated benchmark cards named one error class above the others: a quote that is real, taken
from a real source, and assigned to the wrong field, entity, checkpoint, table row or
evaluation setting. Each test below is one shape of that error, with the failure class
it guards named in its docstring. They run against the gates, the referent repair, the
table reader and the leaf-support check directly, so a regression names its own cause.
"""

from __future__ import annotations

import json

import pytest

from model_cards.core import model_frame as MF
from model_cards.core import model_gates as MG
from model_cards.core.support import unsupported_leaves
from model_cards.core import table_scores as TS
from model_cards.core.table_scores import read_metric, read_setting, reconcile_rows, target_score_rows

REV = "7df9a82518afdecae4e8c026b27adccc8c1f0032"


class _LLM:
    """A frame pass that proposes exactly the names the fixture needs."""

    def __init__(self, siblings=(), comparisons=(), aliases=()):
        self._reply = json.dumps({"siblings": list(siblings), "comparisons": list(comparisons),
                                  "family_aliases": list(aliases)})

    def generate(self, prompt, response_format=None):
        return self._reply


def _hf(model_id, readme="", base_tags=(), tags=()):
    return {"id": model_id, "sha": REV, "tags": list(tags), "readme_markdown": readme,
            "base_model_tags": list(base_tags), "model_index": None, "card_data": {}}


def _frame(model_id, *, readme="", paper="", base_tags=(), tier="introduces_target", llm=None):
    return MF.build_model_frame(model_id, REV, _hf(model_id, readme, base_tags),
                                paper_text=paper, paper_tier=tier, llm_handler=llm)


def _rec(field, quote, referent, doc="docling"):
    return {"field": field, "quote": quote, "referent": referent, "doc": doc}


def _gate(frame, records):
    repaired = MG.resolve_model_referents(records, frame)
    return MG.apply_model_gates(repaired, frame)


# 1 ------------------------------------------------------------------------------------
def test_base_fact_does_not_land_on_the_instruct_card():
    """Failure class: base_fact_inheritance. A fine-tune README copies the base card
    wholesale, so its pretraining sentence is right there in the target's own source."""
    frame = _frame("allenai/OLMo-2-1124-7B-Instruct",
                   base_tags=["allenai/OLMo-2-1124-7B", "finetune:allenai/OLMo-2-1124-7B"],
                   tier="family_reference")
    kept, withheld = _gate(frame, [
        _rec("training_context.training_data",
             "OLMo-2-1124-7B was pretrained on 4 trillion tokens of Dolma.",
             "base:allenai-olmo-2-1124-7b"),
        _rec("training_context.training_data_size", "4 trillion tokens",
             "base:allenai-olmo-2-1124-7b"),
    ])
    # the prose fact stays, visibly relation base; the number never poses as the target's
    assert [(r["field"], r["relation"]) for r in kept] == [
        ("training_context.training_data", "base")]
    assert [(r["field"], r["withhold_reason"]) for r in withheld] == [
        ("training_context.training_data_size", "numeric_value_of_base_not_this_checkpoint")]


# 2 ------------------------------------------------------------------------------------
def test_instruct_score_does_not_land_on_the_base_card():
    """Failure class: sibling_score_on_the_base_card. The base repo's README shows the
    whole family's result table, instruct rows included."""
    readme = ("| Model | AVG |\n|---|---|\n| OLMo-2-1124-7B | 41.2 |\n"
              "| OLMo-2-1124-7B-Instruct | 54.8 |\n")
    frame = _frame("allenai/OLMo-2-1124-7B", readme=readme,
                   llm=_LLM(siblings=["OLMo-2-1124-7B-Instruct"]))
    target = next(n for n in frame["nodes"] if n["id"] == "target")
    rows = target_score_rows(readme, [target["name"], *target["aliases"]], "hf_readme")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("AVG", "41.2")]
    # and the instruct row is refused even if the extractor proposes it as the target's
    kept, withheld = _gate(frame, [
        _rec("evaluation.benchmark_scores", "| OLMo-2-1124-7B-Instruct | 54.8 |", "target",
             doc="hf_readme")])
    assert kept == []
    assert withheld[0]["withhold_reason"] == "score_of_sibling_or_comparison_not_this_checkpoint"


# 3 ------------------------------------------------------------------------------------
def test_comparison_row_does_not_leak_into_the_target_scores():
    """Failure class: comparison_row_leakage."""
    paper = ("## Results\n| Model | MMLU |\n|---|---|\n| OLMo 2 7B | 63.7 |\n"
             "| Llama 3.1 8B | 66.7 |\n")
    frame = _frame("allenai/OLMo-2-1124-7B", paper=paper, llm=_LLM(comparisons=["Llama 3.1 8B"]))
    target = next(n for n in frame["nodes"] if n["id"] == "target")
    rows = target_score_rows(paper, [target["name"], *target["aliases"]], "docling")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "63.7")]
    kept, withheld = _gate(frame, [
        _rec("evaluation.benchmark_scores", "| Llama 3.1 8B | 66.7 |", "target")])
    assert kept == [] and withheld[0]["relation"] == "sibling_or_comparison"


def test_a_sentence_naming_another_model_first_is_a_comparison():
    """Failure class: comparison_row_leakage (prose form). The target is in the sentence,
    so a row-anchor rule alone would pass it; it is still not the target's own claim."""
    paper = "Llama 3.1 8B outperforms OLMo 2 7B on MMLU with 66.7 against 63.7."
    frame = _frame("allenai/OLMo-2-1124-7B", paper=paper, llm=_LLM(comparisons=["Llama 3.1 8B"]))
    kept, withheld = _gate(frame, [
        _rec("evaluation.benchmark_scores", paper, "target"),
        _rec("specifications.num_parameters", paper, "target"),
    ])
    assert kept == []
    assert {r["withhold_reason"] for r in withheld} == {
        "comparison_sentence_names_another_model_first"}
    # the same claim with the target as the subject is the target's own
    own = "OLMo 2 7B reaches 63.7 on MMLU, ahead of Llama 3.1 8B at 66.7."
    kept, _ = _gate(frame, [_rec("evaluation.benchmark_scores", own, "target")])
    assert len(kept) == 1 and kept[0].get("comparison") is False


# 4 ------------------------------------------------------------------------------------
def test_family_paper_number_is_not_stamped_on_a_derivative():
    """Failure class: family_number_on_a_derivative. The family paper's token count is a
    statement about the family; on a post-trained checkpoint it is not this model's."""
    deriv = _frame("allenai/OLMo-2-1124-7B-Instruct",
                   base_tags=["allenai/OLMo-2-1124-7B"], tier="family_reference")
    kept, withheld = _gate(deriv, [
        _rec("training_context.training_data_size", "OLMo 2 is trained on 5 trillion tokens.",
             "family:olmo-2")])
    assert kept == []
    assert withheld[0]["withhold_reason"] == "family_statement_not_this_checkpoint"
    # on the base checkpoint whose own paper introduces the family it is allowed, and the
    # binding keeps relation family so the scope stays visible
    base = _frame("allenai/OLMo-2-1124-7B", tier="introduces_target")
    kept, withheld = _gate(base, [
        _rec("training_context.training_data_size", "OLMo 2 is trained on 5 trillion tokens.",
             "family:olmo-2")])
    assert withheld == [] and kept[0]["relation"] == "family"
    # but never on a field the family policy does not cover
    kept, withheld = _gate(base, [
        _rec("specifications.num_parameters", "OLMo 2 models range from 7B to 13B.",
             "family:olmo-2")])
    assert kept == []
    assert withheld[0]["withhold_reason"] == "family_statement_not_allowed_for_this_field"


# 5 ------------------------------------------------------------------------------------
def test_the_evaluation_setting_travels_with_the_score():
    """Failure class: wrong_setting. 63.7 at 5-shot and 63.7 at 0-shot are two different
    measurements, and a row without its setting silently merges them."""
    readme = ("Table 2: Accuracy (%) in the 5-shot setting\n"
              "| Model | MMLU | HumanEval (pass@1) |\n|---|---|---|\n"
              "| OLMo 2 7B | 63.7 | 22.0 |\n")
    frame = _frame("allenai/OLMo-2-1124-7B")
    target = next(n for n in frame["nodes"] if n["id"] == "target")
    rows = target_score_rows(readme, [target["name"], *target["aliases"]], "hf_readme")
    by_bench = {r["benchmark"]: r for r in rows}
    assert by_bench["MMLU"]["setting"] == "5-shot"
    assert by_bench["MMLU"]["metric"] == "accuracy"
    assert by_bench["HumanEval"]["metric"] == "pass@1"
    assert read_setting("(0-shot CoT)") == "0-shot CoT"
    assert read_setting("MMLU") == "Not specified"
    assert read_metric("Exact Match") == "exact match"

    # two sources, same benchmark, different settings: both survive, each with its own
    a = dict(benchmark="MMLU", score="63.7", metric="accuracy", setting="5-shot",
             source_doc="hf_readme", row_text="r1", header=[])
    b = dict(a, setting="0-shot", score="58.1", source_doc="docling", row_text="r2")
    accepted, conflicted = reconcile_rows([a, b])
    assert len(accepted) == 2 and conflicted == []
    # same benchmark, same setting, same value: one row that records both sources
    accepted, conflicted = reconcile_rows([a, dict(a, source_doc="docling", row_text="r3")])
    assert len(accepted) == 1 and accepted[0]["source_docs"] == ["hf_readme", "docling"]
    assert conflicted == []
    # two sources, same scope, different values: no evidence chooses, neither is published
    accepted, conflicted = reconcile_rows([a, dict(a, score="65.2", source_doc="docling")])
    assert accepted == [] and len(conflicted) == 2
    assert conflicted[0]["withhold_reason"] == "score_conflict_between_sources"
    assert conflicted[0]["conflict"] == ["63.7", "65.2"]


def test_two_tables_in_one_readme_are_not_a_contradiction():
    """Failure class: same_source_rows_read_as_a_conflict. A README carries several
    results tables (thinking and non-thinking mode, per-language breakdowns, a headline
    table and a detailed one) whose rows share a benchmark name and state no setting.
    Treating those as one claim withheld 279 real score rows across the 2026-09-05 batch,
    including twenty-three per-language CER rows collapsed into one contradiction."""
    rows = [dict(benchmark="CER", score=score, metric="Not specified",
                 setting="Not specified", source_doc="hf_readme", row_text=f"r{i}",
                 header=[], caption=f"Table {i}")
            for i, score in enumerate(("0.032", "0.041", "0.056"))]
    accepted, conflicted = reconcile_rows(rows)
    assert conflicted == []
    assert sorted(r["score"] for r in accepted) == ["0.032", "0.041", "0.056"]
    # an exact repeat within one source is still one row
    accepted, _ = reconcile_rows(rows + [dict(rows[0], row_text="again")])
    assert len(accepted) == 3


# 6 ------------------------------------------------------------------------------------
def test_a_value_may_not_carry_a_number_its_quote_does_not():
    """Failure class: fabricated_number. The quote is genuine and says 73.5; the value
    says 99.0. Nothing upstream can see that, because the quote verifies."""
    quote = "OLMo 2 7B scores 73.5 on MMLU (5-shot)."
    assert unsupported_leaves("The model scores 99.0 on MMLU.", [quote]) == ["99"]
    assert unsupported_leaves("The model scores 73.5 on MMLU.", [quote]) == []
    # rephrasing is fine, and so is a differently spelled number
    assert unsupported_leaves("Its MMLU accuracy is 73.50.", [quote]) == []
    assert unsupported_leaves("A 4,096 token window", ["a context window of 4096 tokens"]) == []
    assert unsupported_leaves("4T training tokens", ["trained on 4 trillion tokens"]) == []


# 7 ------------------------------------------------------------------------------------
def test_a_sibling_size_is_not_the_targets_size():
    """Failure class: sibling_size_confusion. 7B and 13B are one character apart in the
    same sentence of the same paper."""
    paper = "We release OLMo 2 7B and OLMo 2 13B; OLMo 2 13B has 13.7 billion parameters."
    frame = _frame("allenai/OLMo-2-1124-7B", paper=paper, llm=_LLM(siblings=["OLMo 2 13B"]))
    kept, withheld = _gate(frame, [
        _rec("specifications.num_parameters", "OLMo 2 13B has 13.7 billion parameters.",
             "sibling:olmo-2-13b")])
    assert kept == []
    assert withheld[0]["withhold_reason"] == "numeric_value_of_sibling_or_comparison_not_this_checkpoint"
    # and the leaf check catches it even if the referent were wrong
    assert unsupported_leaves("13.7 billion parameters",
                              ["OLMo 2 7B has 7.3 billion parameters."]) != []


# 8 ------------------------------------------------------------------------------------
def test_a_quantized_re_upload_is_its_own_target_not_the_original():
    """Failure class: quantized_reupload_as_target. A GGUF or AWQ re-upload declares the
    original as its base; every number in its README is the original's."""
    frame = _frame("TheBloke/OLMo-2-1124-7B-AWQ",
                   base_tags=["quantized:allenai/OLMo-2-1124-7B"], tier="family_reference")
    assert MF.is_derivative_name("TheBloke/OLMo-2-1124-7B-AWQ") is True
    assert frame["meta"]["is_base_checkpoint"] is False
    kept, withheld = _gate(frame, [
        _rec("specifications.num_parameters", "OLMo-2-1124-7B has 7,298,617,344 parameters.",
             "base:allenai-olmo-2-1124-7b"),
        _rec("training_context.training_data", "Pretrained on the Dolma corpus.",
             "base:allenai-olmo-2-1124-7b"),
    ])
    assert [r["withhold_reason"] for r in withheld] == [
        "numeric_value_of_base_not_this_checkpoint"]
    assert [(r["field"], r["relation"]) for r in kept] == [
        ("training_context.training_data", "base")]


# 9 ------------------------------------------------------------------------------------
def test_the_code_repository_license_is_not_the_weights_license():
    """Failure class: code_repo_license_as_weights_license. The GitHub README states the
    code licence; the weights carry their own, and only the Hub tag says which."""
    frame = _frame("allenai/OLMo-2-1124-7B", tier="introduces_target")
    kept, withheld = _gate(frame, [
        _rec("identity.license", "This repository is licensed under the MIT License.",
             "family:olmo-2", doc="github_readme")])
    assert kept == []
    assert withheld[0]["withhold_reason"] == "family_statement_not_allowed_for_this_field"
    assert "identity.license" not in MG.FAMILY_ALLOWED_FIELDS


# the deictic guard -------------------------------------------------------------------
def test_a_deictic_subject_never_rebinds_to_the_model_it_is_compared_against():
    """Failure class: deictic_rebinding. "Our model outperforms Llama 3.1 8B" names
    exactly one model, so a bare mention rule hands the whole sentence to Llama."""
    paper = "Our model outperforms Llama 3.1 8B on every benchmark we report."
    frame = _frame("allenai/OLMo-2-1124-7B", paper=paper, llm=_LLM(comparisons=["Llama 3.1 8B"]))
    telem = {}
    repaired = MG.resolve_model_referents(
        [_rec("evaluation.results_summary", paper, "comparison:llama-3-1-8b")], frame, telem)
    assert repaired[0]["referent"] == frame["meta"]["default_referent"]["docling"]
    assert repaired[0]["referent_resolution"] == "model_deictic_default"
    assert telem["counts"]["deictic_to_default"] == 1
    # the README's default is the target, so the same sentence there is the target's
    readme_frame = _frame("allenai/OLMo-2-1124-7B", readme=paper)
    repaired = MG.resolve_model_referents(
        [_rec("identity.summary", "This model was trained on 4 trillion tokens.", "target",
              doc="hf_readme")], readme_frame)
    assert repaired[0]["referent"] == "target"


def test_a_model_named_before_the_deictic_keeps_the_sentence():
    """Failure class: deictic_rebinding (over-correction). "Llama 3.1 8B, unlike our
    model, was trained on 15T tokens" is genuinely about Llama."""
    paper = "Llama 3.1 8B, unlike our model, was pretrained on 15 trillion tokens."
    frame = _frame("allenai/OLMo-2-1124-7B", paper=paper, llm=_LLM(comparisons=["Llama 3.1 8B"]))
    repaired = MG.resolve_model_referents(
        [_rec("training_context.training_data", paper, "comparison:llama-3-1-8b")], frame)
    assert repaired[0]["referent"] == "comparison:llama-3-1-8b"


# defects the first three-pair acceptance run found -----------------------------------
def test_a_score_reported_as_70_and_70_0_is_not_a_conflict():
    """Failure class: false_score_conflict. DeepSeek-V3's README writes 70 where its
    paper writes 70.0; withholding both loses a score that both sources agree on."""
    a = dict(benchmark="MMLU-Pro", score="70", metric="accuracy", setting="Not specified",
             source_doc="hf_readme", row_text="r1", header=[])
    accepted, conflicted = reconcile_rows([a, dict(a, score="70.0", source_doc="docling")])
    assert conflicted == [] and len(accepted) == 1
    assert accepted[0]["source_docs"] == ["hf_readme", "docling"]
    # a real disagreement is still a conflict
    accepted, conflicted = reconcile_rows([a, dict(a, score="70.5", source_doc="docling")])
    assert accepted == [] and len(conflicted) == 2


def test_reason_codes_stay_machine_readable():
    """Failure class: unparseable_reason_code. The ledger's reason is a code, and a code
    with the offending values interpolated into it does not validate, so the whole card
    is lost at save time."""
    import re

    from model_cards.core.records import REASON_CODE_RE

    for reason in ("leaf_value_not_in_cited_evidence", "score_conflict_between_sources",
                   "family_statement_not_this_checkpoint",
                   "numeric_value_of_sibling_or_comparison_not_this_checkpoint",
                   "comparison_sentence_names_another_model_first",
                   "score_row_does_not_name_the_target",
                   "family_statement_not_allowed_for_this_field",
                   "lineage_is_structured_channel_only"):
        assert REASON_CODE_RE.fullmatch(reason), reason
    for gate_reason in (f"score_of_{r}_not_this_checkpoint" for r in MF.RELATIONS):
        assert REASON_CODE_RE.fullmatch(gate_reason), gate_reason
    for gate_reason in (f"numeric_value_of_{r}_not_this_checkpoint" for r in MF.RELATIONS):
        assert REASON_CODE_RE.fullmatch(gate_reason), gate_reason


# 10 -----------------------------------------------------------------------------------
def test_a_family_roster_sentence_is_not_the_first_listed_checkpoint_s_own_fact():
    """Failure class: family_roster_sentence_as_a_checkpoint_fact. The Qwen2-0.5B card of
    2026-09-05 published identity.model_type = "Pretrained and instruction-tuned models
    of 5 sizes, including Qwen2-0.5B, Qwen2-1.5B, Qwen2-7B, Qwen2-57B-A14B, and
    Qwen2-72B", relation exact_target. The comparison rule could not catch it: the target
    is the FIRST name in the list, so target_at < others_at read as target-is-subject.
    An enumeration of three or more models is about the family however it is ordered."""
    roster = ("Pretrained and instruction-tuned models of 5 sizes, including Qwen2-0.5B, "
              "Qwen2-1.5B, Qwen2-7B, and Qwen2-72B")
    frame = _frame("Qwen/Qwen2-0.5B", readme=roster,
                   llm=_LLM(siblings=["Qwen2-1.5B", "Qwen2-7B", "Qwen2-72B"],
                            aliases=["Qwen2"]))
    kept, withheld = _gate(frame, [_rec("identity.model_type", roster, "target")])

    assert kept == []
    assert [(r["field"], r["withhold_reason"]) for r in withheld] == [
        ("identity.model_type", "roster_sentence_enumerates_the_family")]
    # and it is visible in the ledger, not dropped to a counter
    assert withheld[0]["quote"] == roster


def test_two_models_named_is_still_the_ordinary_comparison_rule():
    """Failure class: family_roster_sentence_as_a_checkpoint_fact. The roster rule must
    not swallow the two-model case, where word order does decide the subject."""
    frame = _frame("allenai/OLMo-2-1124-7B", readme="OLMo-2-1124-7B outperforms Llama-3.1-8B.",
                   llm=_LLM(comparisons=["Llama-3.1-8B"]))
    repaired = MG.resolve_model_referents(
        [_rec("evaluation.results_summary",
              "OLMo-2-1124-7B outperforms Llama-3.1-8B on MMLU.", "target")], frame)
    assert repaired[0].get("comparison") is False
    assert repaired[0]["referent"] == "target"


# 11 -----------------------------------------------------------------------------------
def test_a_base_checkpoint_never_carries_its_post_trained_sibling_s_name():
    """Failure class: base_alias_manufactures_the_sibling_name. Qwen3-8B-Base's alias set
    contained the literal string "Qwen3-8B", because the suffix builder used only the
    post-training stage tokens and "base" is not one. table_scores._label_matches then
    matched the sibling's column truthfully, and the base card of 2026-09-05 published 42
    of its 57 rows from the post-trained model, 22 of them with setting "Thinking", which
    a base checkpoint does not have."""
    base = MF._target_node("Qwen/Qwen3-8B-Base", REV, {"readme_markdown": ""})
    derivative = MF._target_node("Qwen/Qwen3-8B", REV, {"readme_markdown": ""})

    assert "Qwen3-8B" not in base["aliases"]
    assert "Qwen3 8B" not in base["aliases"]
    assert "Qwen3-8B-Base" in base["aliases"]
    # and the two alias sets no longer intersect, which is the invariant that matters
    assert not set(base["aliases"]) & set(derivative["aliases"])

    # the same for a pt / it pair, whose stage token is spelled differently
    pt = MF._target_node("google/gemma-3-4b-pt", REV, {"readme_markdown": ""})
    it = MF._target_node("google/gemma-3-4b-it", REV, {"readme_markdown": ""})
    assert not set(pt["aliases"]) & set(it["aliases"])


def test_the_post_trained_column_is_not_the_base_card_s_row():
    """Failure class: base_alias_manufactures_the_sibling_name, end to end through the
    table reader with the Qwen3 report's own two tables."""
    paper = (
        "## 3.3 Pre-training Evaluation\n"
        "| | Llama-3-8B Base | Qwen2.5-7B Base | Qwen3-8B Base |\n"
        "| --- | --- | --- | --- |\n"
        "| MMLU | 66.60 | 74.16 | 76.89 |\n"
        "\n"
        "## 4.6 Post-training Evaluation\n"
        "| | DeepSeek-R1-Distill-Qwen-14B | Qwen3-4B | Qwen3-8B |\n"
        "| --- | --- | --- | --- |\n"
        "| MMLU-Redux | 84.1 | 83.7 | 87.5 |\n"
    )
    base = MF._target_node("Qwen/Qwen3-8B-Base", REV, {"readme_markdown": ""})
    rows = target_score_rows(paper, [base["name"], *base["aliases"]], "docling")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "76.89")]

    derivative = MF._target_node("Qwen/Qwen3-8B", REV, {"readme_markdown": ""})
    rows = target_score_rows(paper, [derivative["name"], *derivative["aliases"]], "docling")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU-Redux", "87.5")]


# 12 -----------------------------------------------------------------------------------
def test_a_base_model_table_is_not_the_chat_card_s_table():
    """Failure class: table_section_scope_ignored. The DeepSeek-V3 report labels a column
    "DeepSeek-V3" in BOTH its base-model table and its chat-model table; only the section
    heading tells them apart. Reading the column alone published five pre-training rows on
    the chat card of 2026-09-05. The section path was already recorded on the evidence."""
    paper = (
        "We pretrain DeepSeek-V3-Base and then post-train it into DeepSeek-V3.\n"
        "# 4. Evaluation Results\n"
        "## Base Model\n"
        "### Standard Benchmarks\n"
        "| Benchmark (Metric) | # Shots | DeepSeek-V2 | DeepSeek-V3 |\n"
        "| --- | --- | --- | --- |\n"
        "| MMLU (Acc.) | 5-shot | 78.4 | 87.1 |\n"
        "\n"
        "## Chat Model\n"
        "### Standard Benchmarks\n"
        "| Benchmark (Metric) | DeepSeek V2.5 | DeepSeek-V3 |\n"
        "| --- | --- | --- |\n"
        "| MMLU (Acc.) | 80.6 | 88.5 |\n"
    )
    chat = MF._target_node("deepseek-ai/DeepSeek-V3", REV, {"readme_markdown": ""})
    rows = target_score_rows(paper, [chat["name"], *chat["aliases"]], "docling",
                             TS.target_stage("deepseek-ai/DeepSeek-V3", paper))
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "88.5")]

    base = MF._target_node("deepseek-ai/DeepSeek-V3-Base", REV, {"readme_markdown": ""})
    rows = target_score_rows(paper, [base["name"], *base["aliases"], "DeepSeek-V3"],
                             "docling", TS.target_stage("deepseek-ai/DeepSeek-V3-Base"))
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "87.1")]


def test_a_target_with_no_stage_in_its_name_reads_every_table():
    """Failure class: table_section_scope_ignored. The scope rule must not silence a
    checkpoint whose name declares no stage, which is most community models."""
    paper = ("## Base Model\n"
             "| Benchmark | Mistral-7B-v0.3 |\n| --- | --- |\n| MMLU | 62.5 |\n")
    node = MF._target_node("mistralai/Mistral-7B-v0.3", REV, {"readme_markdown": ""})
    rows = target_score_rows(paper, [node["name"], *node["aliases"]], "docling",
                             TS.target_stage("mistralai/Mistral-7B-v0.3"))
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "62.5")]


# 13 -----------------------------------------------------------------------------------
def test_a_table_row_supports_only_the_target_s_own_column():
    """Failure class: number_lifted_from_another_model_s_column. The Tulu 3 70B DPO card
    of 2026-09-06 published "a Safety (6 task avg.) score of 94.4 for this model". The
    cited quote was the whole row "Safety (6 task avg.) | 94.4 | 89.0 | 88.3 | ..." under
    a header naming seven models; 94.4 is the SFT sibling's column, 89.0 is the DPO
    model's. Leaf support passed 94.4 because it was in the quote. A row quote now
    reduces to the target's cell, and to the label alone when the target has no column."""
    header = ["Benchmark (eval)", "Tülu 3 70B SFT", "Tülu 3 DPO 70B", "Tülu 3 70B",
              "Llama 3.1 70B Instruct"]
    row = "Safety (6 task avg.) | 94.4 | 89.0 | 88.3 | 76.5 |"
    dpo = ["Llama-3.1-Tulu-3-70B-DPO", "Tülu 3 DPO 70B", "Tulu 3 70B DPO"]
    assert TS.row_quote_for_target(row, header, dpo) == "Safety (6 task avg.) | 89.0"
    final = ["Llama-3.1-Tulu-3-70B", "Tülu 3 70B"]
    assert TS.row_quote_for_target(row, header, final) == "Safety (6 task avg.) | 88.3"
    # no column for the target: the row supports no number
    assert TS.row_quote_for_target(row, header, ["Qwen3-8B"]) == "Safety (6 task avg.)"
    # not a table row, or no header: untouched
    assert TS.row_quote_for_target("It scores 94.4.", None, dpo) == "It scores 94.4."
    # the reduced quote is what the leaf-support check sees
    assert unsupported_leaves("a Safety score of 94.4",
                              [TS.row_quote_for_target(row, header, dpo)]) == ["94.4"]
    assert unsupported_leaves("a Safety score of 89.0",
                              [TS.row_quote_for_target(row, header, dpo)]) == []


# 14 -----------------------------------------------------------------------------------
def test_a_sentence_about_the_other_stage_is_not_this_checkpoint_s_fact():
    """Failure class: other_stage_sentence_on_this_checkpoint. Four base cards of
    2026-09-06 (Llama 3.2 1B and 3B, Llama 3.1 8B, Qwen1.5 7B) published as their own
    results_summary a sentence the README says of "the Llama 3.2 instruction-tuned text
    only models". No model name, so the comparison rule had nothing to see; a stage word
    is enough to know the sentence is about the other member of the pair."""
    readme = ("Llama-3.2-1B and Llama-3.2-1B-Instruct are released together. "
              "The Llama 3.2 instruction-tuned text only models are optimized for multilingual "
              "dialogue use cases. They outperform many of the available open source and closed "
              "chat models on common industry benchmarks.")
    base = _frame("meta-llama/Llama-3.2-1B", readme=readme)
    assert any(n["name"] == "Llama-3.2-1B-Instruct" for n in base["nodes"])
    kept, withheld = _gate(base, [
        _rec("evaluation.results_summary",
             "The Llama 3.2 instruction-tuned text only models are optimized for multilingual "
             "dialogue use cases.", "target", doc="hf_readme")])
    assert kept == []
    assert [(r["field"], r["withhold_reason"]) for r in withheld] == [
        ("evaluation.results_summary", "sentence_about_the_other_stage")]

    # on the instruct checkpoint the guard stays silent: whatever the family policy then
    # decides, the sentence is not refused for being about the other stage
    instruct = _frame("meta-llama/Llama-3.2-1B-Instruct", readme=readme)
    assert any(n["name"] == "Llama-3.2-1B" for n in instruct["nodes"])
    kept, withheld = _gate(instruct, [
        _rec("evaluation.results_summary",
             "The Llama 3.2 instruction-tuned text only models are optimized for multilingual "
             "dialogue use cases.", "target", doc="hf_readme")])
    assert "sentence_about_the_other_stage" not in [r.get("withhold_reason") for r in withheld]

    # and a sentence about pretrained models is not the instruct checkpoint's
    kept, withheld = _gate(instruct, [
        _rec("training_context.training_data",
             "The pretrained models were trained on 9 trillion tokens.", "target", doc="hf_readme")])
    assert kept == [] and withheld[0]["withhold_reason"] == "sentence_about_the_other_stage"


# 15 -----------------------------------------------------------------------------------
def test_the_sentence_above_a_table_scopes_it_even_without_a_caption():
    """Failure class: table_section_scope_ignored (lead-in form). The Gemma 4 26B A4B
    base card of 2026-09-06 took all 15 rows of a README table whose introduction two
    lines above read "Evaluation results marked in the table are for instruction-tuned
    models." There was no "Table N" caption, so the caption reader saw nothing."""
    readme = ("## Benchmark Results\n\n"
              "These models were evaluated against a large collection of datasets. "
              "Evaluation results marked in the table are for instruction-tuned models.\n\n"
              "| | Gemma 4 31B | Gemma 4 26B A4B |\n| --- | --- | --- |\n| MMLU | 91.2 | 86.4 |\n")
    aliases = ["gemma-4-26b-a4b", "Gemma 4 26B A4B", "gemma 4 26b a4b"]
    base_rows = target_score_rows(readme, aliases, "hf_readme", "base")
    assert base_rows == []
    inst_rows = target_score_rows(readme, aliases, "hf_readme", "post")
    assert [(r["benchmark"], r["score"]) for r in inst_rows] == [("MMLU", "86.4")]
    unknown_rows = target_score_rows(readme, aliases, "hf_readme", None)
    assert len(unknown_rows) == 1



# 16 -----------------------------------------------------------------------------------
def test_a_family_identity_statement_is_allowed_on_every_member():
    """Failure class: family_identity_withheld_on_every_derivative. identity.summary was
    Not specified on 45 of 74 cards (2026-09-06) and the ledger said why 63 times:
    family_statement_not_this_checkpoint. The README's one-line description is a family
    sentence on nearly every instruct and derivative card. What the family is, who made
    it, what it does and what it is called are identity, not inheritance, so they are
    allowed on any member at relation family. Training data and results still are not."""
    readme = ("Qwen2 is a language model series including decoder language models of different "
              "sizes. Qwen2 was pretrained on 7 trillion tokens.")
    instruct = _frame("Qwen/Qwen2-0.5B-Instruct", readme=readme, tier="family_reference",
                      llm=_LLM(aliases=["Qwen2"]))
    kept, withheld = _gate(instruct, [
        _rec("identity.summary",
             "Qwen2 is a language model series including decoder language models of different sizes.",
             "family:qwen2", doc="hf_readme"),
        _rec("training_context.training_data_size", "Qwen2 was pretrained on 7 trillion tokens.",
             "family:qwen2", doc="hf_readme"),
    ])
    assert [(r["field"], r["relation"]) for r in kept] == [("identity.summary", "family")]
    assert [(r["field"], r["withhold_reason"]) for r in withheld] == [
        ("training_context.training_data_size", "family_statement_not_this_checkpoint")]


# 17 -----------------------------------------------------------------------------------
def test_the_bare_family_name_is_the_base_checkpoint_under_a_base_model_heading():
    """Failure class: base_column_named_without_its_suffix. The DeepSeek-V3 report labels
    the base model's column "DeepSeek-V3" in its "Base Model" tables, and the chat model's
    column "DeepSeek-V3" in its "Chat Model" tables. DeepSeek-V3-Base matched nothing
    (0 rows, 2026-09-06). Under a heading that says base, the bare name is the base."""
    paper = ("# 4. Evaluation Results\n## Base Model\n### Standard Benchmarks\n"
             "| Benchmark (Metric) | # Shots | DeepSeek-V2 | DeepSeek-V3 |\n| --- | --- | --- | --- |\n"
             "| MMLU (Acc.) | 5-shot | 78.4 | 87.1 |\n\n"
             "## Chat Model\n### Standard Benchmarks\n"
             "| Benchmark (Metric) | DeepSeek V2.5 | DeepSeek-V3 |\n| --- | --- | --- |\n"
             "| MMLU (Acc.) | 80.6 | 88.5 |\n")
    base = MF._target_node("deepseek-ai/DeepSeek-V3-Base", REV, {"readme_markdown": ""})
    rows = target_score_rows(paper, [base["name"], *base["aliases"]], "docling", "base")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "87.1")]
    # and never the chat table, whose heading says the other stage
    assert all(r["score"] != "88.5" for r in rows)
    assert TS.bare_base_names(["DeepSeek-V3-Base", "DeepSeek V3 Base", "gemma-3-4b-pt"]) == [
        "DeepSeek-V3", "DeepSeek V3", "gemma-3-4b"]


# 18 -----------------------------------------------------------------------------------
def test_a_sentence_that_names_both_stages_is_not_about_the_other_one():
    """Failure class: both_stages_sentence_refused_as_other_stage. The other-stage rule
    of 2026-09-06 reads "instruction-tuned variants" on a base card as a sentence about
    the sibling. The Gemma 2 README describes the release with both members in one
    sentence, and refusing it left google/gemma-2-9b with no model_type and no
    adaptations at all (2026-09-07). A sentence that names this checkpoint's stage as
    well is about the release."""
    readme = ("Gemma is a family of lightweight models.\n"
              "They are text-to-text, decoder-only large language models, available in English, "
              "with open weights for both pre-trained variants and instruction-tuned variants.\n"
              "gemma-2-9b-it is the instruction-tuned version.\n")
    frame = _frame("google/gemma-2-9b", readme=readme, tier="none")
    assert MG._stage_of(frame) == "base"
    both = ("They are text-to-text, decoder-only large language models, available in English, "
            "with open weights for both pre-trained variants and instruction-tuned variants.")
    kept, withheld = _gate(frame, [_rec("identity.model_type", both, "target", doc="hf_readme")])
    assert [r["field"] for r in kept] == ["identity.model_type"]
    assert withheld == []
    # the one-stage sentence of 2026-09-06 is still refused
    only_other = ("The Llama 3.2 instruction-tuned text only models are optimized for "
                  "multilingual dialogue use cases.")
    kept, withheld = _gate(frame, [_rec("evaluation.results_summary", only_other, "target",
                                        doc="hf_readme")])
    assert kept == []
    assert [r["withhold_reason"] for r in withheld] == ["sentence_about_the_other_stage"]
    assert MG.names_both_stages("the pretrained and instruction-tuned checkpoints") is True
    assert MG.names_both_stages("the instruction-tuned models") is False


# 19 -----------------------------------------------------------------------------------
def test_the_technology_a_family_was_built_from_is_not_the_referent():
    """Failure class: technology_source_steals_the_referent. "Gemma is a family of
    lightweight, state-of-the-art open models from Google, built from the same research
    and technology used to create the Gemini models" names exactly one model, Gemini, so
    the sole-other-model rule rebound the sentence to Gemini and identity.summary was
    withheld as a comparison model's fact on every Gemma card (2026-09-07). A model named
    as the technology this one came out of is not the subject of the sentence."""
    readme = ("Gemma is a family of lightweight, state-of-the-art open models from Google, "
              "built from the same research and technology used to create the Gemini models.\n")
    frame = _frame("google/gemma-2-9b", readme=readme, tier="none",
                   llm=_LLM(comparisons=["Gemini"]))
    quote = ("Gemma is a family of lightweight, state-of-the-art open models from Google, "
             "built from the same research and technology used to create the Gemini models.")
    repaired = MG.resolve_model_referents([_rec("identity.summary", quote, "target",
                                                doc="hf_readme")], frame)
    assert repaired[0]["referent"] == "target"
    assert repaired[0]["referent_resolution"] == "technology_source_named_not_the_subject"
    # the ordinary sole-other-model rule is untouched: a plain sentence about Gemini is
    # Gemini's, not this checkpoint's
    plain = "Gemini is a multimodal model trained on a large corpus."
    repaired = MG.resolve_model_referents([_rec("identity.summary", plain, "target",
                                                doc="hf_readme")], frame)
    assert repaired[0]["referent"] == "comparison:gemini"


# 20 -----------------------------------------------------------------------------------
def test_a_column_label_in_the_developers_own_shorthand_is_the_targets_column():
    """Failure class: stage_token_order_and_omitted_version_in_column_labels. The Gemma 2
    README labels its columns "Gemma PT 9B" and "Gemma 2 IT 9B". String equality against
    the repo name matched neither, so google/gemma-2-9b and google/gemma-2-9b-it were
    published with no benchmark scores and no safety evaluations at all (2026-09-07),
    the largest single gap on both cards."""
    pt = ("| Benchmark | Metric | Gemma PT 9B | Gemma PT 27B |\n"
          "| --- | --- | --- | --- |\n"
          "| MMLU | 5-shot, top-1 | 71.3 | 75.2 |\n")
    it = ("| Benchmark | Metric | Gemma 2 IT 9B | Gemma 2 IT 27B |\n"
          "| --- | --- | --- | --- |\n"
          "| RealToxicity | average | 8.25 | 8.84 |\n")
    base = MF._target_node("google/gemma-2-9b", REV, {"readme_markdown": ""})
    base_aliases = [base["name"], *base["aliases"]]
    rows = target_score_rows(pt, base_aliases, "hf_readme", "base", own_readme=True)
    assert [(r["benchmark"], r["score"], r["setting"]) for r in rows] == [
        ("MMLU", "71.3", "5-shot")]
    # the 27B sibling's column is never the 9B's, and the instruction-tuned table is not
    # the base card's table
    assert all(r["score"] != "75.2" for r in rows)
    assert target_score_rows(it, base_aliases, "hf_readme", "base", own_readme=True) == []

    inst = MF._target_node("google/gemma-2-9b-it", REV, {"readme_markdown": ""})
    inst_aliases = [inst["name"], *inst["aliases"]]
    rows = target_score_rows(it, inst_aliases, "hf_readme", "post", own_readme=True)
    assert [(r["benchmark"], r["score"]) for r in rows] == [("RealToxicity", "8.25")]
    assert target_score_rows(pt, inst_aliases, "hf_readme", "post", own_readme=True) == []
    # the version may only be left out in the checkpoint's own README, and only when the
    # sources say which stage this checkpoint is
    assert target_score_rows(pt, base_aliases, "docling", "base") == []
    assert target_score_rows(pt, base_aliases, "hf_readme", None, own_readme=True) == []


# 21 -----------------------------------------------------------------------------------
def test_the_category_column_is_not_the_benchmark():
    """Failure class: category_column_read_as_benchmark. The Llama 3.2 README puts a
    Category column before the Benchmark column and leaves it empty on every continuation
    row. The reader took the first cell, so meta-llama/Llama-3.2-3B published a benchmark
    called "General" with MMLU's number and lost every row whose category cell was blank
    (2026-09-07). The DeepSeek-V3 card published four the same way: English, Code, Math,
    Chinese."""
    readme = ("| Category | Benchmark | \\# Shots | Metric | Llama 3.2 1B | Llama 3.2 3B |\n"
              "| ----- | ----- | :---: | :---: | :---: | :---: |\n"
              "| General | MMLU | 5 | macro\\_avg/acc\\_char | 32.2 | 58 |\n"
              "|  | AGIEval English | 3-5 | average/acc\\_char | 23.3 | 39.2 |\n"
              "| Reading comprehension | SQuAD | 1 | em | 49.2 | 67.7 |\n")
    node = MF._target_node("meta-llama/Llama-3.2-3B", REV, {"readme_markdown": ""})
    rows = target_score_rows(readme, [node["name"], *node["aliases"]], "hf_readme", "base",
                             own_readme=True)
    assert [(r["benchmark"], r["score"], r["setting"], r["metric"]) for r in rows] == [
        ("MMLU", "58", "5-shot", "accuracy"),
        ("AGIEval English", "39.2", "3-5 shot", "accuracy"),
        ("SQuAD", "67.7", "1-shot", "exact match")]
    assert all(r["benchmark"] not in ("General", "Reading comprehension") for r in rows)


# 22 -----------------------------------------------------------------------------------
def test_the_instruction_tuned_table_belongs_to_the_instruction_tuned_card():
    """Failure classes: precision_decoration_in_column_label and
    instruct_table_read_by_the_base_card. The Llama 3.2 README puts its instruct results
    under "Instruction Tuned Models" and labels the unquantized column "Llama 3.2 3B
    bf16" beside the quantized SpinQuant and QLoRA columns. The instruct card read none
    of it; the base card, whose name and README never mention a sibling, read thirteen
    rows of it (2026-09-07). Under a heading that says instruction-tuned, the bare name
    is the instruct model, bf16 is its serving precision, and a quantized re-upload is
    still a different checkpoint. A base checkpoint that declares no base model of its
    own does not read that section at all."""
    readme = ("## Benchmarks\n### Instruction Tuned Models\n"
              "| Benchmark | Llama 3.2 3B bf16 | Llama 3.2 3B Spin Quant | Llama 3.2 3B QLoRA |\n"
              "| --- | --- | --- | --- |\n"
              "| MMLU | 63.4 | 60.0 | 62.4 |\n")
    node = MF._target_node("meta-llama/Llama-3.2-3B-Instruct", REV, {"readme_markdown": ""})
    rows = target_score_rows(readme, [node["name"], *node["aliases"]], "hf_readme", "post",
                             own_readme=True)
    assert [(r["benchmark"], r["score"]) for r in rows] == [("MMLU", "63.4")]
    assert all(r["score"] not in ("60.0", "62.4") for r in rows)
    # the base checkpoint of the same release: no stage token in its name, no base model
    # tag, and its README never spells the sibling out
    assert TS.target_stage("meta-llama/Llama-3.2-3B", readme, []) == "base"
    base = MF._target_node("meta-llama/Llama-3.2-3B", REV, {"readme_markdown": ""})
    assert target_score_rows(readme, [base["name"], *base["aliases"]], "hf_readme", "base",
                             own_readme=True) == []
    assert TS.bare_post_names(["Llama-3.2-3B-Instruct", "Llama 3.2 3B Instruct"]) == [
        "Llama-3.2-3B", "Llama 3.2 3B"]
