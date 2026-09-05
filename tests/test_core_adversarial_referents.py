"""The nine ways a genuine quote lands on the wrong card, one fixture each.

The AAAI evaluation named one error class above the others: a quote that is real, taken
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
    # same scope, different values: no evidence chooses, so neither is published
    accepted, conflicted = reconcile_rows([a, dict(a, score="65.2", source_doc="docling")])
    assert accepted == [] and len(conflicted) == 2
    assert conflicted[0]["withhold_reason"] == "score_conflict_between_sources"
    assert conflicted[0]["conflict"] == ["63.7", "65.2"]


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
