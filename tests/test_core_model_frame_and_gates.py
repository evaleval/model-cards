"""Model frame and relation gates.

Failure classes pinned here:
  1. Base-fact inheritance: a derivative's family/base statements must carry relation
     base (or unknown), never exact_target.
  2. Comparison-row leakage: a score row naming another model never reaches
     benchmark_scores; a family-level score never reaches a derivative's scores.
  3. Numeric withholding on unknown relations.
"""

import json

from model_cards.core import model_frame as MF
from model_cards.core import model_gates as MG


REV = "7df9a82518afdecae4e8c026b27adccc8c1f0032"


def _hf(model_id="allenai/OLMo-2-1124-7B", base_tags=(), model_index=None,
        readme="---\nlicense: apache-2.0\n---\n# OLMo-2-1124-7B\nOLMo 2 is a family of open models.\n"):
    return {"id": model_id, "readme_markdown": readme, "base_model_tags": list(base_tags),
            "model_index": model_index}


class _LLM:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def generate(self, prompt, response_format=None):
        self.prompts.append(prompt)
        return self.reply


def test_family_name_and_derivative_detection():
    assert MF.family_name("allenai/OLMo-2-1124-7B") == "OLMo 2"
    assert MF.family_name("meta-llama/Llama-3.1-8B-Instruct") == "Llama 3.1"
    assert MF.family_name("Qwen/Qwen3-8B-Base") == "Qwen3"
    assert MF.family_name("mistralai/Mixtral-8x7B-Instruct-v0.1") == "Mixtral"
    assert MF.is_derivative_name("meta-llama/Llama-3.1-8B-Instruct") is True
    assert MF.is_derivative_name("allenai/OLMo-2-1124-7B") is False


def test_deterministic_nodes_from_structured_sources():
    mi = [{"name": "OLMo-2-1124-7B", "results": [{"dataset": {"name": "MMLU"},
                                                  "metrics": [{"name": "accuracy", "value": 0.63}]}]}]
    eee = {"tier": "exact", "benchmarks": {"hfopenllm_v2": [{"evaluation_name": "IFEval"}]}}
    fr = MF.build_model_frame("allenai/OLMo-2-1124-7B", REV, _hf(model_index=mi,
                              base_tags=["allenai/OLMo-2-1124-7B-stage1"]), eee=eee,
                              paper_tier="introduces_target")
    ids = [n["id"] for n in fr["nodes"]]
    assert ids[:2] == ["target", "family:olmo-2"]
    assert "base:allenai-olmo-2-1124-7b-stage1" in ids
    assert "benchmark:mmlu" in ids and "benchmark:hfopenllm-v2" in ids and "metric:accuracy" in ids
    target = fr["nodes"][0]
    assert "allenai/OLMo-2-1124-7B" in target["aliases"] and "OLMo 2 1124 7B" in target["aliases"]
    assert "OLMo-2-1124-7B" == target["name"]
    assert fr["meta"]["is_base_checkpoint"] is False        # a base_model tag makes it a derivative
    assert fr["meta"]["default_referent"]["docling"] == "family:olmo-2"
    assert fr["telemetry"]["llm_pass"] == "skipped"


def test_llm_pass_literal_guard_for_siblings_and_comparisons():
    paper = "We release OLMo 2 7B and OLMo 2 13B. Compared to Llama 3.1 8B and Qwen 2.5 7B, OLMo 2 7B is competitive."
    llm = _LLM(json.dumps({"siblings": ["OLMo 2 13B", "OLMo 2 70B"],
                           "comparisons": ["Llama 3.1 8B", "Qwen 2.5 7B", "Phantom-9B"],
                           "family_aliases": ["OLMo 2", "OLMo-Two"]}))
    fr = MF.build_model_frame("allenai/OLMo-2-1124-7B", REV, _hf(), paper_text=paper,
                              paper_tier="introduces_target", llm_handler=llm)
    ids = {n["id"] for n in fr["nodes"]}
    assert "sibling:olmo-2-13b" in ids and "sibling:olmo-2-70b" not in ids      # 70B not literal
    assert "comparison:llama-3-1-8b" in ids and "comparison:phantom-9b" not in ids
    assert fr["telemetry"]["builder_counts"]["siblings_llm"] == 1
    assert fr["telemetry"]["builder_counts"]["comparisons_llm"] == 2
    assert fr["meta"]["is_base_checkpoint"] is True


def test_llm_pass_never_turns_the_targets_own_name_into_another_node():
    # seen on the OLMo-2 Instruct smoke: the LLM listed the target's own name as a
    # family alias, every exact mention ("# OLMo-2-1124-7B-Instruct") then resolved
    # to the family, which reads as base on a derivative, and the name was withheld
    readme = "---\nlicense: apache-2.0\n---\n# OLMo-2-1124-7B-Instruct\nOLMo 2 7B Instruct is a post-trained variant.\n"
    llm = _LLM(json.dumps({"siblings": ["OLMo-2-1124-7B-Instruct", "OLMo 2 7B Instruct", "OLMo-2-1124-13B-Instruct"],
                           "comparisons": ["olmo 2 1124 7b instruct"],
                           "family_aliases": ["OLMo-2-1124-7B-Instruct", "OLMo 2"]}))
    fr = MF.build_model_frame("allenai/OLMo-2-1124-7B-Instruct", REV,
                              _hf("allenai/OLMo-2-1124-7B-Instruct", base_tags=["allenai/OLMo-2-1124-7B-DPO"], readme=readme),
                              paper_text="OLMo-2-1124-13B-Instruct is the larger sibling.", paper_tier="introduces_target",
                              llm_handler=llm)
    target = fr["nodes"][0]
    family = next(n for n in fr["nodes"] if n["type"] == "family")
    assert target["name"] == "OLMo-2-1124-7B-Instruct"
    assert "OLMo-2-1124-7B-Instruct" not in family["aliases"]
    assert not any(n["type"] in ("sibling", "comparison") and MF._norm_key(n["name"]) == MF._norm_key(target["name"])
                   for n in fr["nodes"])
    assert "sibling:olmo-2-1124-13b-instruct" in {n["id"] for n in fr["nodes"]}
    assert fr["telemetry"]["builder_counts"]["own_name_dropped"] == 4
    # an exact mention of the target now binds to the target, not the family
    from auto_benchmarkcard.tools.composer import frame as frame_mod
    hits = frame_mod.match_mention(fr, "# OLMo-2-1124-7B-Instruct")
    assert hits and hits[0] == "target"          # longest alias first: the target, not the family


def test_target_aliases_cover_the_swapped_size_and_date_order():
    node = MF._target_node("allenai/OLMo-2-1124-7B-Instruct", REV, _hf("allenai/OLMo-2-1124-7B-Instruct"))
    assert "OLMo-2-7B-1124-Instruct" in node["aliases"] and "OLMo 2 7B 1124 Instruct" in node["aliases"]
    from model_cards.core.table_scores import target_score_rows
    readme = "| Model | AVG | BBH |\n|---|---|---|\n| **OLMo-2-7B-1124-Instruct** | 54.8 | 46.6 |\n| OLMo-2-7B-1124-DPO | 52.1 | 45.0 |\n"
    rows = target_score_rows(readme, [node["name"], *node["aliases"]], "hf_readme")
    assert [(r["benchmark"], r["score"]) for r in rows] == [("AVG", "54.8"), ("BBH", "46.6")]
    plain = MF._target_node("Qwen/Qwen3-8B-Base", REV, _hf("Qwen/Qwen3-8B-Base"))
    assert not any("Base-8B" in a for a in plain["aliases"])     # no date token, no swap


def test_relation_rule_base_vs_derivative():
    """relation_for reports what the referent IS; the gates decide what a field may take."""
    base_fr = MF.build_model_frame("allenai/OLMo-2-1124-7B", REV, _hf(), paper_tier="introduces_target")
    assert MF.relation_for("target", base_fr) == "exact_target"
    assert MF.relation_for("family:olmo-2", base_fr) == "family"
    deriv_fr = MF.build_model_frame("allenai/OLMo-2-1124-7B-Instruct", REV,
                                    _hf("allenai/OLMo-2-1124-7B-Instruct", base_tags=["allenai/OLMo-2-1124-7B"]),
                                    paper_tier="family_reference")
    assert MF.relation_for("family:olmo-2", deriv_fr) == "family"
    assert MF.relation_for("base:allenai-olmo-2-1124-7b", deriv_fr) == "base"
    assert MF.relation_for("nonexistent:x", deriv_fr) == "unknown"
    # the family policy, not the relation, is what differs between these frames
    assert MG.apply_model_gates([_rec("training_context.training_data", "q", "family:olmo-2")],
                                base_fr)[0] != []
    assert MG.apply_model_gates([_rec("training_context.training_data", "q", "family:olmo-2")],
                                deriv_fr)[0] == []
    other_fr = MF.build_model_frame("allenai/OLMo-2-1124-7B", REV, _hf(), paper_tier="family_reference")
    kept, withheld = MG.apply_model_gates(
        [_rec("training_context.training_data", "q", "family:olmo-2")], other_fr)
    assert kept == [] and withheld[0]["withhold_reason"] == "family_statement_not_this_checkpoint"


def _rec(field, quote, referent, doc="docling"):
    return {"field": field, "quote": quote, "referent": referent, "doc": doc}


def test_gates_drop_comparison_rows_and_withhold_unknown_numbers():
    paper = "OLMo 2 7B scores 63.7 on MMLU. Llama 3.1 8B scores 66.7 on MMLU. The models use 4096 context."
    llm = _LLM(json.dumps({"siblings": [], "comparisons": ["Llama 3.1 8B"], "family_aliases": []}))
    fr = MF.build_model_frame("allenai/OLMo-2-1124-7B", REV, _hf(), paper_text=paper,
                              paper_tier="introduces_target", llm_handler=llm)
    records = [
        {"field": "evaluation.benchmark_scores", "quote": "OLMo 2 7B scores 63.7 on MMLU.", "referent": "target"},
        {"field": "evaluation.benchmark_scores", "quote": "Llama 3.1 8B scores 66.7 on MMLU.", "referent": "comparison:llama-3-1-8b"},
        {"field": "evaluation.benchmark_scores", "quote": "63.7 on MMLU for the 7B.", "referent": "target"},
        {"field": "specifications.context_length", "quote": "The models use 4096 context.", "referent": "benchmark:mmlu"},
        {"field": "training_context.training_data", "quote": "pretrained on 4T tokens", "referent": "family:olmo-2"},
        {"field": "lineage.base_models", "quote": "built on top of X", "referent": "target"},
    ]
    telem = {}
    kept, withheld = MG.apply_model_gates(records, fr, telem)
    fields = [(r["field"], r["relation"]) for r in kept]
    assert fields == [("evaluation.benchmark_scores", "exact_target"),
                      ("training_context.training_data", "family")]
    # nothing is dropped to a counter: every refusal comes back with its reason
    assert sorted((r["field"], r["withhold_reason"]) for r in withheld) == sorted([
        ("evaluation.benchmark_scores", "score_of_sibling_or_comparison_not_this_checkpoint"),
        ("evaluation.benchmark_scores", "score_row_does_not_name_the_target"),
        ("specifications.context_length", "numeric_value_of_unknown_not_this_checkpoint"),
        ("lineage.base_models", "lineage_is_structured_channel_only"),
    ])
    assert telem["summary"]["score_relation"]["withhold"] == 1     # the Llama row
    assert telem["summary"]["score_row_anchor"]["withhold"] == 1   # no target name in the row
    assert telem["summary"]["numeric_relation"]["withhold"] == 1   # unknown referent on a number
    assert telem["summary"]["structured_only"]["withhold"] == 1
    assert telem["family_facts_allowed"] is True


def test_gates_keep_base_relation_visible_on_prose_fields():
    fr = MF.build_model_frame("acme/Tulu-8B-DPO", REV, _hf("acme/Tulu-8B-DPO", base_tags=["meta-llama/Llama-3.1-8B"]),
                              paper_tier="family_reference")
    records = [{"field": "training_context.training_data", "quote": "Llama 3.1 was pretrained on 15T tokens.",
                "referent": "base:meta-llama-llama-3-1-8b"},
               {"field": "training_context.training_data_size", "quote": "15T tokens", "referent": "base:meta-llama-llama-3-1-8b"}]
    telem = {}
    kept, withheld = MG.apply_model_gates(records, fr, telem)
    assert [(r["field"], r["relation"]) for r in kept] == [("training_context.training_data", "base")]
    assert telem["summary"]["relation"]["annotate"] == 1
    assert telem["summary"]["numeric_relation"]["withhold"] == 1
    assert [(r["field"], r["withhold_reason"]) for r in withheld] == [
        ("training_context.training_data_size", "numeric_value_of_base_not_this_checkpoint")]


def test_frame_pass_runs_with_a_schema_and_a_token_cap():
    """Failure class: frame_call_unstructured. An extraction call without a server-enforced
    schema and a token cap let a reasoning model answer with an unbounded think trace; the
    first composition attempt on 2026-09-04 blocked for over ten minutes on one README."""
    from model_cards.core import model_frame as mf

    seen = {}

    class _Handler:
        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            seen["response_format"] = response_format
            seen["max_completion_tokens"] = max_completion_tokens
            return '{"siblings": [], "comparisons": [], "family_aliases": []}', "stop"

        def generate(self, prompt, response_format=None):  # pragma: no cover
            raise AssertionError("the capped per-call path must be preferred")

    mf.build_model_frame("acme/Thing-7B", "a" * 40, {"readme_markdown": "# Thing-7B\nA model."},
                         llm_handler=_Handler())
    assert seen["max_completion_tokens"] == mf.FRAME_MAX_TOKENS
    assert seen["response_format"] == mf.FRAME_SCHEMA
    assert seen["response_format"]["required"] == ["siblings", "comparisons", "family_aliases"]


def test_frame_pass_falls_back_to_plain_generate_with_the_same_schema():
    """Failure class: frame_call_unstructured (handler without a per-call token cap)."""
    from model_cards.core import model_frame as mf

    seen = {}

    class _Handler:
        def generate(self, prompt, response_format=None):
            seen["response_format"] = response_format
            return '{"siblings": [], "comparisons": [], "family_aliases": []}'

    mf.build_model_frame("acme/Thing-7B", "a" * 40, {"readme_markdown": "# Thing-7B\nA model."},
                         llm_handler=_Handler())
    assert seen["response_format"] == mf.FRAME_SCHEMA
