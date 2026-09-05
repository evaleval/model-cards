"""The evaluation instruments, offline.

Failure classes:
  instrument_drift           a prompt or schema changes without its id changing
  judge_sees_the_composer    the judge is shown the binding ledger and grades the
                             composer's own reasoning instead of the card
  probe_depends_on_resolver  a probe uses the frame or the relation gates, so it can only
                             confirm the resolver agrees with itself
  sample_not_reproducible    the same seed draws a different sample
  cost_tripwire_missing      a paid runner has no pricing entry and counts zero
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from model_cards.core.eval import judge as J
from model_cards.core.eval import probes as P
from model_cards.core.eval import sample as S
from model_cards.core.eval import screen as SC
from model_cards.core.schema import NOT_SPECIFIED, blank_card, set_field_value

ROOT = Path(__file__).resolve().parents[1]


def test_the_instruments_are_frozen_by_content():
    """instrument_drift."""
    first, second = J.instrument_id(), J.instrument_id()
    assert first == second and len(first) == 32
    original = J.JUDGE_PROMPT
    try:
        J.JUDGE_PROMPT = original + " Be lenient."
        assert J.instrument_id() != first
    finally:
        J.JUDGE_PROMPT = original
    assert J.instrument_id() == first
    assert SC.prompt_prefix_md5() != SC.instrument_id()
    assert set(SC.CATEGORIES) == {
        "wrong-checkpoint", "base-fact-inheritance", "comparison-row-leakage",
        "score-tuple-mismatch", "wrong-paper", "fabricated-fact", "thin", "other"}


def test_the_judge_asks_about_abstention_as_well_as_support():
    """A card that says nothing is perfectly faithful and useless, so the judge has to be
    able to say the sources held the answer and the card missed it."""
    statuses = J.JUDGE_SCHEMA["properties"]["field_verdicts"]["items"][
        "properties"]["status"]["enum"]
    assert set(statuses) == {"supported", "partial", "unsupported", "not_specified"}
    info = J.JUDGE_SCHEMA["properties"]["field_verdicts"]["items"][
        "properties"]["info_in_source"]["enum"]
    assert "yes" in info and "yes_other_entity" in info
    relations = J.JUDGE_SCHEMA["properties"]["field_verdicts"]["items"][
        "properties"]["relation"]["enum"]
    assert {"exact_target", "base", "sibling_or_comparison", "family"} <= set(relations)
    assert "entity, not the wording" in J.JUDGE_PROMPT


def test_the_judge_never_sees_a_binding(tmp_path):
    """judge_sees_the_composer."""
    from model_cards.core import compose_llm as CL
    from tests.test_core_compose_llm import MODEL, REV, _ScriptedLLM, _write_bundle

    root = _write_bundle(tmp_path / "bundles")
    artifact = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(),
                                         allow_unpinned=True)
    payload = J.build_input(artifact)
    blob = json.dumps(payload)
    assert "binding" not in blob and "evidence_id" not in blob
    assert "verifier_reason" not in blob and "relation_to_target" not in blob
    assert set(payload) == {"target", "instrument", "sources", "fields", "source_chars",
                            "sources_truncated"}
    assert payload["fields"] and all(set(f) == {"path", "value", "is_ns"}
                                     for f in payload["fields"])
    # the deterministic Hub fields are not judged: they measure the Hub, not the card
    judged = {f["path"] for f in payload["fields"]}
    assert "access_and_adoption.downloads" not in judged
    assert "identity.summary" in judged


def test_a_probe_uses_no_part_of_the_resolver():
    """probe_depends_on_resolver."""
    import ast

    tree = ast.parse(Path(P.__file__).read_text(encoding="utf-8"))
    tree.body = [node for node in tree.body
                 if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant))]
    code = ast.unparse(tree)
    for forbidden in ("model_frame", "match_mention", "relation_for", "model_gates",
                      "build_model_frame", "aboutness", "referent"):
        assert forbidden not in code, forbidden
    card = blank_card()
    set_field_value(card, "training_context.training_data_size", "15 trillion tokens")
    set_field_value(card, "specifications.context_length", "4,096 tokens")
    sources = {"paper.md": ("Llama-3.1-8B was pretrained on 15 trillion tokens.\n"
                            "OLMo-2-1124-7B uses a 4,096 token context window.\n")}
    found = P.probes_for(card, "allenai/OLMo-2-1124-7B", [], sources)
    assert [p["field"] for p in found] == ["training_context.training_data_size"]
    assert found[0]["lines_about_other_entities"][0]["other_model"] == "Llama-3.1-8B"
    # a value whose line names the target is not a probe
    assert all(p["field"] != "specifications.context_length" for p in found)


def test_a_probe_ignores_a_field_the_structured_channel_owns():
    """A value read out of config.json cannot have been spliced out of a sentence."""
    card = blank_card()
    set_field_value(card, "specifications.context_length", "4,096 tokens")
    sources = {"paper.md": "Llama-3.1-8B uses 4,096 tokens of context.\n"}
    assert P.probes_for(card, "acme/Thing-7B", [], sources)
    assert P.probes_for(card, "acme/Thing-7B", [], sources,
                        structured_fields={"specifications.context_length"}) == []


def test_a_probe_does_not_fire_on_a_common_word():
    """The first pass matched any long word, so "parameters" put a probe on every card."""
    card = blank_card()
    set_field_value(card, "training_context.training_data", "Trained on curated web text.")
    sources = {"paper.md": "Llama-3.1-8B was trained on curated web text and code.\n"}
    found = P.probes_for(card, "acme/Thing-7B", [], sources)
    assert found == []


def test_the_same_seed_draws_the_same_sample():
    """sample_not_reproducible."""
    population = [{"target": f"org/m{i}@{'a' * 40}",
                   "strata": {"stage": "base" if i % 2 else "instruct",
                              "sources": "source_rich" if i % 3 else "source_limited",
                              "provenance": "flagship" if i < 10 else "community"}}
                  for i in range(40)]
    first = S.draw(population, 12, seed=7)
    second = S.draw(population, 12, seed=7)
    other = S.draw(population, 12, seed=8)
    assert [row["target"] for row in first["sample"]] == [row["target"] for row in second["sample"]]
    assert [row["target"] for row in first["sample"]] != [row["target"] for row in other["sample"]]
    assert first["drawn"] == 12
    assert len({row["target"] for row in first["sample"]}) == 12
    # every stratum key is counted, and each drawn card records why it was drawn
    assert set(first["stratum_counts"]) >= {"stage=base", "stage=instruct"}
    assert all(row["why"] for row in first["sample"])


def test_the_paired_targets_come_first():
    """The paired half is the comparison; it cannot be left to chance."""
    population = [{"target": f"org/m{i}@{'a' * 40}",
                   "strata": {"stage": "base", "sources": "source_rich",
                              "provenance": "flagship"}} for i in range(20)]
    paired = [f"org/m{i}@{'a' * 40}" for i in (3, 11)]
    result = S.draw(population, 6, seed=1, paired_targets=paired)
    assert [row["target"] for row in result["sample"][:2]] == paired
    assert all(row["why"] == "paired_with_deterministic_card" for row in result["sample"][:2])
    assert result["paired_available"] == 2


def test_the_paid_runner_refuses_a_model_it_cannot_price():
    """cost_tripwire_missing: a tripwire that silently counts zero is not a tripwire."""
    done = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_eval.py"), "estimate",
         "--inputs", str(ROOT / "eval" / "judge-inputs"), "--model", "some-unpriced-model"],
        capture_output=True, text=True, cwd=str(ROOT))
    assert done.returncode == 2
    assert "no pricing entry" in done.stderr
    text = (ROOT / "scripts" / "run_eval.py").read_text(encoding="utf-8")
    assert "--max-cost-usd" in text and "required=True" in text
    assert "temperature=0" in text


def test_the_target_list_deduplicates_on_the_hubs_canonical_id(tmp_path, monkeypatch):
    """Failure class: duplicate_target_same_bundle. The Every Eval Ever datastore lists
    the same repo under more than one casing (mistralai/Mistral-7B-Instruct-v0.1 and
    mistralai/mistral-7b-instruct-v0.1). The bundle slug is case-insensitive, so both
    targets wrote the same bundle and composed the same card twice."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_targets

    # the two spellings cannot both exist as directories on a case-insensitive
    # filesystem, which is the same reason they share one bundle slug
    (tmp_path / "data" / "hfopenllm_v2").mkdir(parents=True)
    listed = ["mistralai/Mistral-7B-Instruct-v0.1", "mistralai/mistral-7b-instruct-v0.1",
              "acme/Other-7B"]
    monkeypatch.setattr(build_targets, "datastore_models",
                        lambda data_dir, benchmark: list(listed))

    canonical = {"mistralai/Mistral-7B-Instruct-v0.1": "mistralai/Mistral-7B-Instruct-v0.1",
                 "mistralai/mistral-7b-instruct-v0.1": "mistralai/Mistral-7B-Instruct-v0.1",
                 "acme/Other-7B": "acme/Other-7B"}

    def fake_resolve(model_id):
        return {"model_id": canonical[model_id], "requested_as": model_id,
                "revision": "a" * 40, "gated": "false", "downloads": 1, "likes": 1,
                "pipeline_tag": "text-generation", "library_name": "transformers",
                "tags": [], "created_at": None}

    monkeypatch.setattr(build_targets, "resolve", fake_resolve)
    result = build_targets.build(tmp_path / "data", count=10, flagship_count=0, seed=1)
    ids = [row["model_id"] for row in result["targets"]]
    assert ids.count("mistralai/Mistral-7B-Instruct-v0.1") == 1
    assert len(ids) == len(set(ids))
    assert all("@" in row["target"] and row["target"].startswith(row["model_id"])
               for row in result["targets"])
