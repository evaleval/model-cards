"""The risk stage: Risk Atlas entries selected for this checkpoint, bound to a frozen taxonomy.

Failure classes:
  risk_inherited_from_family     a family-scope value feeds a checkpoint risk unmarked
  risk_without_taxonomy_evidence a selected risk has no pointer into the frozen taxonomy
  risk_selected_outside_list     the selector names a risk that was not a candidate
  risk_stage_loses_the_card      the stage raises and the composition dies with it
"""

from __future__ import annotations

import json
from pathlib import Path

from model_cards.core import risks as R
from model_cards.core.records import structured_document
from model_cards.core.spans import resolve_pointer

ENTRIES = [
    {"id": "atlas-jailbreaking", "name": "Jailbreaking", "description": "Prompts that bypass safety.",
     "url": "https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/jailbreaking.html",
     "tag": "jailbreaking", "type": "Risk", "concern": None},
    {"id": "atlas-data-contamination", "name": "Data contamination", "description": "Evaluation data in training data.",
     "url": None, "tag": "data-contamination", "type": "Risk", "concern": None},
    {"id": "atlas-hallucination", "name": "Hallucination", "description": "Plausible but false output.",
     "url": "https://example.org/hallucination", "tag": "hallucination", "type": "Risk", "concern": None},
]
TAXONOMY_TEXT = json.dumps({"taxonomy": "ibm-risk-atlas", "source": R.TAXONOMY_URI,
                            "nexus_version": "test", "risks": ENTRIES})


def _card():
    return {
        "identity": {"name": "Qwen3-8B-Base", "summary": "A base language model.",
                     "model_type": "Causal language model", "license": "apache-2.0"},
        "specifications": {"input_output": ["text"], "architecture_type": "dense decoder-only"},
        "training_context": {"training_data": "Not specified",
                             "adaptations": "The Qwen3 family is post-trained with RL.",
                             "data_cutoff": "Not specified"},
        "access_and_adoption": {"access_type": "open-weight"},
        "evaluation": {"results_summary": "Not specified", "safety_evals": "Not specified",
                       "human_evals": "Not specified"},
        "lineage": {"model_family": "Qwen3"},
        "links": {}, "risks": {"possible_risks": "Not specified"},
    }


class _Engine:
    pass


class _LLM:
    engine = _Engine()

    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
        self.prompts.append(prompt)
        return json.dumps(self.reply), "stop"


def test_the_use_case_marks_family_scope_and_skips_unspecified_fields():
    """risk_inherited_from_family."""
    text, used = R.usecase_from_card(_card(), {"training_context.adaptations": "family",
                                               "identity.summary": "exact_target"})
    assert "Qwen3-8B-Base is a model" in text
    assert "Post-training or adaptation: The Qwen3 family is post-trained with RL [family-scope]" in text
    assert "Training data" not in text and "Reported results" not in text
    assert "training_context.training_data" not in used
    assert "training_context.adaptations" in used


def test_the_selector_only_keeps_candidates_and_binds_each_to_the_taxonomy():
    """risk_selected_outside_list, risk_without_taxonomy_evidence."""
    llm = _LLM({"selected": [
        {"id": "atlas-jailbreaking", "justification": "open-weight chat model, no safety evals reported"},
        {"id": "atlas-not-a-candidate", "justification": "made up"},
        {"id": "atlas-jailbreaking", "justification": "duplicate"},
    ]})
    detector = lambda usecase, engine, entries: ["atlas-jailbreaking", "atlas-hallucination"]
    out = R.run_risk_stage(_card(), {}, None, llm, TAXONOMY_TEXT, detector=detector)
    assert out["status"] == "ok"
    assert out["candidates"] == ["atlas-jailbreaking", "atlas-hallucination"]
    assert out["invalid_selection_items"] == 2
    assert [r["category"] for r in out["rows"]] == ["Jailbreaking"]
    assert out["rows"][0]["justification"].startswith("open-weight")
    # the pointer resolves in the frozen taxonomy to exactly the entry it binds
    pointer, entry = out["pointers"][0]
    document = structured_document(R.TAXONOMY_FILE, TAXONOMY_TEXT)
    assert resolve_pointer(document, pointer) == entry
    assert entry["id"] == "atlas-jailbreaking"
    # the selector saw the candidate block and an unmarked summary
    assert "atlas-hallucination | Hallucination" in llm.prompts[0]
    assert "Primary task: Causal language model" in llm.prompts[0]
    assert "Causal language model [family-scope]" not in llm.prompts[0]


def test_the_stage_never_raises_and_records_why_it_did_not_run():
    """risk_stage_loses_the_card."""
    class _NoEngine:
        def generate_with_meta(self, *a, **k):
            return "{}", "stop"

    out = R.run_risk_stage(_card(), {}, None, _NoEngine(), TAXONOMY_TEXT)
    assert out["status"] == "unavailable" and "engine" in out["reason"]
    assert out["rows"] == []

    def boom(usecase, engine, entries):
        raise RuntimeError("nexus down")

    out = R.run_risk_stage(_card(), {}, None, _LLM({"selected": []}), TAXONOMY_TEXT, detector=boom)
    assert out["status"] == "failed" and "nexus down" in out["reason"]

    out = R.run_risk_stage(_card(), {}, None, _LLM({"selected": []}), TAXONOMY_TEXT,
                           detector=lambda *a: ["atlas-jailbreaking"])
    assert out["status"] == "ok" and out["rows"] == [] and out["selected_count"] == 0

    empty = {s: {f: "Not specified" for f in fs} for s, fs in
             {"identity": ("name", "summary", "model_type", "license"), "risks": ("possible_risks",)}.items()}
    out = R.run_risk_stage(empty, {}, None, _LLM({"selected": []}), TAXONOMY_TEXT)
    assert out["status"] == "skipped"


def test_the_frozen_taxonomy_is_written_once_and_reread(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "taxonomy_entries", lambda: ENTRIES)
    first = R.frozen_taxonomy(tmp_path)
    path = tmp_path / "_risk_atlas" / "ibm-risk-atlas.json"
    assert path.is_file()
    monkeypatch.setattr(R, "taxonomy_entries", lambda: [])
    assert R.frozen_taxonomy(tmp_path) == first
    assert json.loads(first)["risks"][0]["id"] == "atlas-data-contamination"  # sorted by id
