"""End-to-end LLM composition on a synthetic bundle with a scripted model.

Failure classes pinned here:
  1. The card is exactly the projection of accepted bindings (withheld values never
     show), and every filled value carries an exact-span or structured binding.
  2. Base-fact inheritance and comparison rows are withheld with typed relations and
     stay inspectable in the ledger.
  3. The structured channel (config.json, model_info, tags) lands as established
     values with file-backed evidence the artifact validator accepts.
  4. A score row is on the card only when a table row whose label IS the target
     carries it (deterministic, row-anchored); a prose-only score row stays withheld.
  5. Duplicate base_model tags (plain and kind-qualified) yield one lineage row.
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

from model_cards.core import compose_llm as CL
from model_cards.core import spans as SP
from model_cards.core.review import load_artifact, save_artifact
from model_cards.core.records import VerifierAction


REV = "7df9a82518afdecae4e8c026b27adccc8c1f0032"
MODEL = "allenai/OLMo-2-1124-7B"
README = ("---\nlicense: apache-2.0\nbase_model: []\n---\n# OLMo-2-1124-7B\n"
          "OLMo 2 7B is a fully open language model trained on 4 trillion tokens. "
          "It is an instruction-free base model released under Apache 2.0. "
          "OLMo 2 7B scores 63.7 on MMLU (5-shot). Code: https://github.com/allenai/OLMo-core\n"
          "The pretraining corpus is the [Dolma web mix](https://huggingface.co/datasets/allenai/dolma).\n"
          "```bibtex\n@article{olmo2,\n  title={2 OLMo 2 Furious}\n}\n```\n")
PAPER = ("2 OLMo 2 Furious\n\n## 1 Introduction\nWe present OLMo 2, a family of fully open models. "
         "OLMo 2 7B and OLMo 2 13B are trained on up to 5 trillion tokens.\n\n"
         "## 4 Results\n| Model | MMLU |\n|---|---|\n| OLMo 2 7B | 63.7 |\n| Llama 3.1 8B | 66.7 |\n"
         "Llama 3.1 8B was pretrained on 15 trillion tokens.\n")
CONFIG = {"architectures": ["Olmo2ForCausalLM"], "model_type": "olmo2", "max_position_embeddings": 4096}


def _file(name, uri, content, media="text/markdown"):
    raw = content.encode("utf-8")
    return {"name": name, "source_uri": uri, "sha256": hashlib.sha256(raw).hexdigest(),
            "size_bytes": len(raw), "media_type": media, "content": content}


def _write_bundle(root: Path):
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    base = root / slug
    (base / "tool_output" / "hf").mkdir(parents=True)
    (base / "tool_output" / "paper_resolver").mkdir(parents=True)
    (base / "tool_output" / "docling").mkdir(parents=True)
    (base / "tool_output" / "eee").mkdir(parents=True)
    (base / "tool_output" / "extras").mkdir(parents=True)
    (base / "source_bundle").mkdir(parents=True)
    hf = {"id": MODEL, "author": "allenai", "sha": REV, "tags": ["arxiv:2501.00656", "license:apache-2.0"],
          "downloads": 84552, "likes": 5, "gated": False, "pipeline_tag": "text-generation",
          "safetensors": {"parameters": {"F32": 7298617344}, "total": 7298617344},
          "readme_markdown": README, "config": CONFIG, "base_model_tags": [], "model_index": None,
          "resolved_revision": REV}
    (base / "tool_output" / "hf" / f"{slug}.json").write_text(json.dumps(hf))
    (base / "tool_output" / "paper_resolver" / "paper-verification.json").write_text(json.dumps(
        {"resolved_url": "https://arxiv.org/abs/2501.00656", "binding": {"tier": "introduces_target"}}))
    (base / "tool_output" / "docling" / f"{slug}.json").write_text(json.dumps(
        {"success": True, "filtered_text": PAPER, "metadata": {"title": "2 OLMo 2 Furious"}}))
    (base / "tool_output" / "eee" / f"{slug}.json").write_text(json.dumps({"tier": "none", "benchmarks": {}}))
    (base / "tool_output" / "extras" / f"{slug}.json").write_text(json.dumps(
        {"safetensors_bytes": 29194510544, "readme_frontmatter": {"license": "apache-2.0"},
         "bibtex_blocks": ["@article{olmo2,\n  title={2 OLMo 2 Furious}\n}"]}))
    sb = {"target": {"model_id": MODEL, "requested_revision": REV, "resolved_revision": REV},
          "repo_type": "model", "snapshot_path": "/fake/snapshot",
          "metadata": {"model_id": MODEL, "requested_revision": REV, "resolved_revision": REV, "repo_type": "model",
                       "available_files": ["README.md", "config.json"]},
          "files": [_file("README.md", f"https://huggingface.co/{MODEL}/blob/{REV}/README.md", README),
                    _file("config.json", f"https://huggingface.co/{MODEL}/blob/{REV}/config.json",
                          json.dumps(CONFIG), "application/json")],
          "retrieved_at": "2026-08-27T18:00:00+00:00", "offline": True}
    (base / "source_bundle" / "source-bundle.json").write_text(json.dumps(sb))
    return root


class _ScriptedLLM:
    """Answers each composer prompt from its wording; records what it saw."""
    model_name = "scripted-test-model"

    def __init__(self):
        self.prompts = []

    def generate(self, prompt, response_format=None):
        self.prompts.append(prompt)
        if "You are indexing documentation about the model checkpoint" in prompt:
            return json.dumps({"siblings": ["OLMo 2 13B"], "comparisons": ["Llama 3.1 8B"], "family_aliases": []})
        if "You are a careful auditor" in prompt:
            return json.dumps({"verdicts": []})
        if "SOURCE TEXT (model card README)" in prompt:
            return json.dumps({"evidence": [
                {"field": "identity.summary", "quote": "OLMo 2 7B is a fully open language model trained on 4 trillion tokens.", "referent": "target", "claim_role": "primary_result"},
                {"field": "identity.summary", "quote": "OLMo 2 7B is a fully open model trained on four trillion tokens.", "referent": "target", "claim_role": "primary_result"},
                {"field": "identity.model_type", "quote": "It is an instruction-free base model released under Apache 2.0.", "referent": "target", "claim_role": "primary_result"},
                {"field": "evaluation.benchmark_scores", "quote": "OLMo 2 7B scores 63.7 on MMLU (5-shot).", "referent": "target", "claim_role": "primary_result"},
            ]})
        if "SOURCE TEXT (research paper)" in prompt:
            return json.dumps({"evidence": [
                {"field": "training_context.training_data_size", "quote": "OLMo 2 7B and OLMo 2 13B are trained on up to 5 trillion tokens.", "referent": "target", "claim_role": "primary_result"},
                {"field": "training_context.training_data", "quote": "Llama 3.1 8B was pretrained on 15 trillion tokens.", "referent": "comparison:llama-3-1-8b", "claim_role": "secondary"},
            ]})
        return "{}"

    def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
        # Every call the pipeline makes is capped, so it arrives here; the frame, EAV
        # and Stage-A prompts keep their own scripted replies.
        if ("You are indexing documentation about the model checkpoint" in prompt
                or "You are a careful auditor" in prompt
                or "SOURCE TEXT (" in prompt):
            return self.generate(prompt, response_format), "stop"
        self.prompts.append(prompt)
        ids = {}
        for line in prompt.splitlines():
            if line.startswith("- [E") and "]" in line:
                eid = line[3:line.index("]")]
                field = line.split("(", 1)[1].split(" |", 1)[0]
                ids.setdefault(field, []).append(eid)
        if "identity, lineage" in prompt:
            out = {"identity": {"model_id": MODEL, "name": "OLMo 2 7B", "developed_by": "Not specified",
                                "model_type": "An instruction-free base language model.", "license": "apache-2.0",
                                "release_date": "Not specified",
                                "version": REV, "summary": "A fully open 7B language model trained on 4 trillion tokens.",
                                "provenance": {"summary": {"source": "hf_readme", "evidence": "q", "evidence_ids": ids.get("identity.summary", [])},
                                               "model_type": {"source": "hf_readme", "evidence": "q", "evidence_ids": ids.get("identity.model_type", [])}}},
                   "lineage": {"base_models": "Not specified", "model_family": "Not specified", "derivatives": "Not specified", "provenance": {}}}
        elif "specifications, training_context" in prompt:
            out = {"specifications": {"architecture_type": "dense decoder-only",
                                      "num_parameters": "7,298,617,344 parameters (safetensors metadata)",
                                      "context_length": "4,096 tokens (config.json max_position_embeddings)",
                                      "precision": "F32 (safetensors weight dtype)",
                                      "model_size": "Not specified", "input_output": ["text"],
                                      "provenance": {"input_output": {"source": "hf_readme", "evidence": "q", "evidence_ids": ids.get("identity.summary", [])}}},
                   "training_context": {"training_data": "Not specified",
                                        "training_data_size": "Up to 5 trillion tokens.", "data_cutoff": "Not specified",
                                        "adaptations": "Not specified",
                                        "provenance": {"training_data_size": {"source": "docling", "evidence": "q", "evidence_ids": ids.get("training_context.training_data_size", [])}}},
                   "access_and_adoption": {"access_type": "open-weight",
                                           "downloads": "84,552 downloads (Hub 30-day window, as of 2026-08-27)",
                                           "likes": "Not specified", "provenance": {}}}
        else:
            out = {"evaluation": {"results_summary": "Not specified",
                                  "benchmark_scores": [{"benchmark": "MMLU", "metric": "accuracy", "score": "63.7", "setting": "5-shot"}],
                                  "human_evals": "Not specified", "safety_evals": "Not specified",
                                  "provenance": {"benchmark_scores": {"source": "hf_readme", "evidence": "q", "evidence_ids": ids.get("evaluation.benchmark_scores", [])}}},
                   "links": {"model_card": f"https://huggingface.co/{MODEL}", "system_card": "Not specified",
                             "tech_report": "https://arxiv.org/abs/2501.00656", "code_repository": "Not specified",
                             "citation": "Not specified", "provenance": {}}}
        return json.dumps(out), "stop"


def test_compose_llm_end_to_end(tmp_path):
    root = _write_bundle(tmp_path / "bundles")
    llm = _ScriptedLLM()
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, llm, allow_unpinned=True)

    card = art.card
    # structured channel established and bound
    assert card["identity"]["model_id"] == MODEL and card["identity"]["version"] == REV
    assert card["specifications"]["architecture_type"] == "dense decoder-only"
    assert card["specifications"]["context_length"].startswith("4,096 tokens")
    assert card["specifications"]["num_parameters"].startswith("7,298,617,344")
    assert card["access_and_adoption"]["access_type"] == "open-weight"
    assert card["identity"]["license"] == "apache-2.0"
    assert card["links"]["tech_report"] == "https://arxiv.org/abs/2501.00656"
    # LLM-bound exact-target values are on the card with exact spans
    assert card["identity"]["summary"].startswith("A fully open 7B")
    assert card["identity"]["model_type"] == "An instruction-free base language model."
    assert card["training_context"]["training_data_size"] == "Up to 5 trillion tokens."
    # the paper table row labelled "OLMo 2 7B" becomes the score row, row-anchored,
    # scoped to its column; the Llama row in the same table never appears
    assert card["evaluation"]["benchmark_scores"] == [
        {"benchmark": "MMLU", "metric": "Not specified", "score": "63.7", "setting": "Not specified"}]
    score = next(b for b in art.bindings if b.field_path == "evaluation.benchmark_scores[0]")
    assert score.verifier_reason == "structured_table_row_names_target"
    assert score.evidence[0].row_anchor == "| OLMo 2 7B | 63.7 |"
    assert score.evidence[0].table_header == ("Model", "MMLU")
    assert score.benchmark_scope.benchmark_id == "MMLU"
    assert not any("Llama" in (s.exact_text or "") for b in art.bindings
                   if b.field_path.startswith("evaluation.benchmark_scores") for s in b.evidence)
    # structured identity facts from the Hub manifest, repo name and README title
    assert card["identity"]["name"] == "OLMo-2-1124-7B"
    name = next(b for b in art.bindings if b.field_path == "identity.name")
    assert name.assignment_origin.value == "structured_explicit" and name.evidence[0].exact_text == "# OLMo-2-1124-7B"
    assert name.evidence[0].source_uri.endswith("/README.md")
    assert card["identity"]["developed_by"] == "allenai (Hub organization)"
    assert card["lineage"]["model_family"] == "OLMo 2"
    assert card["specifications"]["input_output"] == ["input: text", "output: text"]
    # the comparison-model sentence never became training_data
    assert card["training_context"]["training_data"] == "Not specified"
    # quality section computed from the ledger
    assert card["provenance_and_quality"]["coverage_score"] > 0
    # the artifact round-trips through the validator (spans, hashes, projection equality)
    out = tmp_path / "card.json"
    save_artifact(art, out)
    loaded = load_artifact(out)
    assert loaded.artifact_id == art.artifact_id
    spans = [s for b in art.bindings for s in b.evidence if s.exact_text]
    assert any(s.source_uri.endswith("/README.md#plain") and "4 trillion tokens" in s.exact_text for s in spans)
    assert any(s.source_uri == "https://arxiv.org/abs/2501.00656" for s in spans)
    assert art.metadata["llm"] == "scripted-test-model"
    # the paraphrased quote was rejected and its head is recorded for the read
    qv = art.metadata["quote_verify"]
    assert qv["rejected"] >= 1
    assert {"doc": "hf_readme", "field": "identity.summary",
            "quote": "OLMo 2 7B is a fully open model trained on four trillion tokens."} in qv["rejected_samples"]


def test_prose_score_without_a_target_table_row_is_withheld(tmp_path):
    # the paper table names only comparison models: the README's prose score has no
    # table anchor, so the card shows NS and the ledger keeps the withheld row
    root = _write_bundle(tmp_path / "bundles")
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    doc_path = root / slug / "tool_output" / "docling" / f"{slug}.json"
    doc = json.loads(doc_path.read_text())
    doc["filtered_text"] = PAPER.replace("| OLMo 2 7B | 63.7 |", "| OLMo 2 7B-Instruct | 63.7 |")
    doc_path.write_text(json.dumps(doc))
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    assert art.card["evaluation"]["benchmark_scores"] == "Not specified"
    withheld = [b for b in art.bindings if b.verifier_action is VerifierAction.WITHHOLD]
    assert any(b.field_path == "evaluation.benchmark_scores[0]" and b.verifier_reason == "score_row_without_table_anchor"
               for b in withheld)
    assert "evaluation.benchmark_scores" in art.card["provenance_and_quality"]["flagged_fields"]


def test_base_model_tags_with_relation_prefix_become_lineage_rows(tmp_path):
    # OLMo-2-1124-7B-Instruct carries base_model:finetune:allenai/OLMo-2-1124-7B-DPO; the
    # prefix is the lineage kind, never part of the claim entity's repo id.
    root = _write_bundle(tmp_path / "bundles")
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    hf_path = root / slug / "tool_output" / "hf" / f"{slug}.json"
    hf = json.loads(hf_path.read_text())
    # the DPO base appears twice on the Hub (plain and kind-qualified): one row, kind kept
    hf["tags"] += ["base_model:allenai/OLMo-2-1124-7B-DPO", "base_model:finetune:allenai/OLMo-2-1124-7B-DPO",
                   "base_model:allenai/OLMo-2-1124-7B-SFT"]
    hf["base_model_tags"] = ["allenai/OLMo-2-1124-7B-DPO", "finetune:allenai/OLMo-2-1124-7B-DPO",
                             "allenai/OLMo-2-1124-7B-SFT"]
    hf_path.write_text(json.dumps(hf))
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    rows = art.card["lineage"]["base_models"]
    assert rows == [{"model_id": "allenai/OLMo-2-1124-7B-DPO", "relation": "base_model", "kind": "finetune"},
                    {"model_id": "allenai/OLMo-2-1124-7B-SFT", "relation": "base_model", "kind": "base"}]
    lineage = [b for b in art.bindings if b.field_path.startswith("lineage.base_models[")]
    assert [b.claim_entity.model_id for b in lineage] == ["allenai/OLMo-2-1124-7B-DPO", "allenai/OLMo-2-1124-7B-SFT"]
    assert all(b.relation_to_target.value == "base" and b.verifier_action.value == "accept" for b in lineage)


def test_gap_pass_asks_only_open_fields_and_binds_its_verified_quotes(tmp_path):
    # failure class: Stage A recall variance (the OLMo smoke verified 25 quotes in one
    # run and 10 in the next on identical sources, training_data flipped to NS); the
    # gap pass re-asks each productive source for the schema's gap fields still open
    root = _write_bundle(tmp_path / "bundles")

    class _GapLLM(_ScriptedLLM):
        def generate(self, prompt, response_format=None):
            if "SOURCE TEXT (model card README excerpts)" in prompt:
                self.prompts.append(prompt)
                return json.dumps({"evidence": [
                    {"field": "training_context.training_data", "quote": "The pretraining corpus is the Dolma web mix.",
                     "referent": "target", "claim_role": "primary_result"}]})
            if "SOURCE TEXT (research paper excerpts)" in prompt:
                self.prompts.append(prompt)
                return json.dumps({"evidence": []})
            return super().generate(prompt, response_format)

        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            out, stop = super().generate_with_meta(prompt, response_format, max_completion_tokens)
            data = json.loads(out)
            if "training_context" in data:
                # cite the gap quote only; citing the Llama comparison item as well
                # would (correctly) withhold the field as sibling_or_comparison
                ids = [line[3:line.index("]")] for line in prompt.splitlines()
                       if line.startswith("- [E") and "training_context.training_data " in line and "Dolma" in line]
                if ids:
                    data["training_context"]["training_data"] = "Pretrained on the Dolma web mix."
                    data["training_context"]["provenance"]["training_data"] = {
                        "source": "hf_readme", "evidence": "q", "evidence_ids": ids}
            return json.dumps(data), stop

    llm = _GapLLM()
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, llm, allow_unpinned=True)
    gap_prompts = [p for p in llm.prompts if "still missing evidence" in p]
    assert len(gap_prompts) == 2                       # one per productive source, never a second sweep
    readme_gap = next(p for p in gap_prompts if "model card README excerpts" in p)
    # only open gap fields the README may carry are listed: summary and model_stage
    # were already verified, benchmark_scores too; training_data and adaptations are open
    assert "- training_context.training_data:" in readme_gap and "- training_context.adaptations:" in readme_gap
    assert "- identity.summary:" not in readme_gap and "- specifications.model_stage:" not in readme_gap
    assert "- evaluation.benchmark_scores:" not in readme_gap
    assert readme_gap.rstrip().endswith("or emit nothing for it.")
    assert art.card["training_context"]["training_data"] == "Pretrained on the Dolma web mix."
    assert art.metadata["quote_verify"]["gap_calls"] == 2 and art.metadata["quote_verify"]["gap_verified"] == 1
    # the quote dropped the markdown link; it verifies against the recorded plain view
    # of the README, and the span points at that derived file, the raw README kept
    span = next(b for b in art.bindings if b.field_path == "training_context.training_data").evidence[0]
    assert span.source_uri.endswith("/README.md#plain") and span.exact_text == "The pretraining corpus is the Dolma web mix."
    assert "README.plain.md" in art.metadata["source_hashes"] and "README.md" in art.metadata["source_hashes"]
    assert art.metadata["derived_views"]["README.plain.md"] == {"from": "README.md", "rule": "markdown_plain_v1"}


def test_readme_only_gated_bundle_without_paper_composes(tmp_path):
    # failure class: a gated roster target (Llama-3.1, gemma-3) has README.md only,
    # no config.json, and its wrong arXiv tag was dropped, so there is no docling
    # text and no GitHub README; the composer must still produce a card with the
    # config-derived fields honestly NS and the README-only sources bound
    root = _write_bundle(tmp_path / "bundles")
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    base = root / slug
    (base / "tool_output" / "docling" / f"{slug}.json").unlink()
    sidecar = base / "tool_output" / "paper_resolver" / "paper-verification.json"
    sidecar.write_text(json.dumps({"resolved_url": None, "resolved_from": "hf_arxiv_tag",
                                   "binding": {"tier": "unrelated_tag", "verdict": "dropped",
                                               "paper_url": "https://arxiv.org/abs/2204.05149",
                                               "reason": "no family token in title or abstract"}}))
    sb_path = base / "source_bundle" / "source-bundle.json"
    sb = json.loads(sb_path.read_text())
    sb["files"] = [f for f in sb["files"] if f["name"] == "README.md"]
    sb["metadata"]["available_files"] = ["README.md"]
    sb["metadata"]["config"] = {}
    sb["metadata"]["gated_files_unavailable"] = ["config.json"]
    sb_path.write_text(json.dumps(sb))
    hf_path = base / "tool_output" / "hf" / f"{slug}.json"
    hf = json.loads(hf_path.read_text())
    hf["config"] = {}
    hf_path.write_text(json.dumps(hf))

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    card = art.card
    assert card["specifications"]["architecture_type"] == "Not specified"
    assert card["specifications"]["context_length"] == "Not specified"
    assert card["links"]["tech_report"] == "Not specified"          # dropped tag never becomes a link
    assert card["specifications"]["num_parameters"].startswith("7,298,617,344")   # safetensors still there
    assert card["identity"]["summary"].startswith("A fully open 7B")            # README quote bound
    assert card["evaluation"]["benchmark_scores"] == "Not specified"            # prose score, no table
    assert not any(s.source_uri.endswith("config.json") for b in art.bindings for s in b.evidence)
    assert "paper.md" not in art.metadata["source_hashes"]
    out = tmp_path / "gated.json"
    save_artifact(art, out)
    assert load_artifact(out).artifact_id == art.artifact_id


def test_span_builder_cleans_empty_header_cells_and_anchors_table_rows(tmp_path):
    from model_cards.core.bridge import load_composer_bridge
    from model_cards.core.records import SourceBundle, TargetIdentity
    from model_cards.core.compose_llm import _span_for_item, DOC_README

    readme = ("# OLMo 2\n\n| | **OLMo 2 7B** | **OLMo 2 13B** |\n|---|---|---|\n"
              "| MMLU | 63.7 | 67.5 |\n\nPlain sentence after the table.\n")
    bridge = load_composer_bridge(allow_unpinned=True)
    f = _file("README.md", f"https://huggingface.co/{MODEL}/blob/{REV}/README.md", readme)
    bundle = SourceBundle(target=TargetIdentity(model_id=MODEL, requested_revision=REV, resolved_revision=REV),
                          snapshot_path="/fake", files=[f], retrieved_at="2026-08-27T18:00:00+00:00", offline=True)
    src = bundle.files[0]
    norm = bridge.normalize_ws(readme)
    row = "| MMLU | 63.7 | 67.5 |"
    start = norm.index(row)
    span = _span_for_item(bundle, bridge, {DOC_README: src},
                          {"doc": DOC_README, "quote": row, "char_start": start, "table_id": "t1"}, None)
    assert span.table_header == ("**OLMo 2 7B**", "**OLMo 2 13B**")   # empty corner cell dropped
    assert span.row_anchor == row
    sentence = "Plain sentence after the table."
    span2 = _span_for_item(bundle, bridge, {DOC_README: src},
                           {"doc": DOC_README, "quote": sentence, "char_start": norm.index(sentence)}, None)
    assert span2.row_anchor is None and span2.table_header is None


def test_every_stage_call_is_structured_and_capped(tmp_path):
    """Failure class: unbounded_stage_call. On the pinned route an uncapped Stage-A gap
    call ran to the engine's 16,384-token ceiling (148 s and USD 0.0048 of a USD 0.0103
    card) and produced nothing, because a reply cut off mid-JSON parses to zero items."""
    from model_cards.core.calls import EAV_MAX_TOKENS, STAGE_A_MAX_TOKENS
    from model_cards.core.model_frame import FRAME_MAX_TOKENS

    root = _write_bundle(tmp_path / "bundles")
    seen = []

    class _Recording(_ScriptedLLM):
        def generate(self, prompt, response_format=None):  # pragma: no cover
            raise AssertionError("an uncapped generate() call reached the route")

        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            seen.append({"cap": max_completion_tokens, "schema": response_format,
                         "kind": ("frame" if "You are indexing documentation" in prompt
                                  else "eav" if "You are a careful auditor" in prompt
                                  else "stage_a" if "SOURCE TEXT (" in prompt else "stage_b")})
            return _ScriptedLLM.generate_with_meta(self, prompt, response_format,
                                                   max_completion_tokens)

    CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _Recording(), allow_unpinned=True)
    assert seen, "no calls were made"
    caps = {"frame": FRAME_MAX_TOKENS, "eav": EAV_MAX_TOKENS, "stage_a": STAGE_A_MAX_TOKENS}
    for call in seen:
        assert call["schema"], f"{call['kind']} call ran without a response schema"
        if call["kind"] in caps:
            assert call["cap"] == caps[call["kind"]], f"{call['kind']} cap drifted"
    assert {c["kind"] for c in seen} >= {"frame", "stage_a", "stage_b"}


def test_a_truncated_stage_a_call_is_recorded_not_swallowed(tmp_path):
    """Failure class: silent_truncation. A call that stops on "length" yields nothing;
    the card must say so instead of reading as an empty source."""
    root = _write_bundle(tmp_path / "bundles")

    class _Truncating(_ScriptedLLM):
        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            text, stop = _ScriptedLLM.generate_with_meta(self, prompt, response_format,
                                                         max_completion_tokens)
            if "SOURCE TEXT (research paper)" in prompt:
                return text, "length"
            return text, stop

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _Truncating(), allow_unpinned=True)
    truncated = art.metadata["quote_verify"].get("truncated_calls") or {}
    assert truncated.get("stage_a:docling") == 1, truncated


def test_the_same_refused_quote_is_one_binding_not_two(tmp_path):
    """Failure class: duplicate_binding_id. binding_id is content-derived, so two records
    with identical content are one binding; emitting both makes the artifact invalid and
    the whole card is lost at save time (seen on Qwen3-8B, 2026-09-04)."""
    root = _write_bundle(tmp_path / "bundles")

    class _Repeating(_ScriptedLLM):
        def generate(self, prompt, response_format=None):
            if "SOURCE TEXT (model card README)" in prompt:
                item = {"field": "evaluation.benchmark_scores",
                        "quote": "It is an instruction-free base model released under Apache 2.0.",
                        "referent": "target", "claim_role": "primary_result"}
                return json.dumps({"evidence": [item, dict(item)]})
            return _ScriptedLLM.generate(self, prompt, response_format)

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _Repeating(), allow_unpinned=True)
    refused = [b for b in art.bindings
               if b.verifier_reason == "score_row_does_not_name_the_target"]
    assert len(refused) == 1
    assert len({b.binding_id for b in art.bindings}) == len(art.bindings)


def test_model_size_and_citation_land_from_the_structured_channel(tmp_path):
    """Failure class: unvalidatable_derivation. The artifact validator re-derives only the
    two config-backed rules it knows, so a third file-backed derivation trace made every
    card invalid at save time (seen on Qwen3 and both DeepSeek targets, 2026-09-04)."""
    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    size = art.card["specifications"]["model_size"]
    assert size.startswith("27.2 GiB of safetensors weights (29,194,510,544 bytes)")
    binding = next(b for b in art.bindings if b.field_path == "specifications.model_size")
    assert binding.derivation_trace is None
    assert binding.evidence[0].structured_pointer == "/safetensors_bytes"
    assert binding.evidence[0].structured_fragment == 29194510544
    assert art.card["links"]["citation"].startswith("@article{olmo2")
    # the artifact round-trips through the validator that rejected the derivation
    save_artifact(art, tmp_path / "card.json")
    assert load_artifact(tmp_path / "card.json").artifact_id == art.artifact_id


def test_an_unsupported_leaf_is_withheld_with_a_code_and_a_recorded_detail(tmp_path):
    """Failure class: unparseable_reason_code (end to end). The reason must stay a code
    and the offending leaves must still be recoverable from the artifact."""
    root = _write_bundle(tmp_path / "bundles")

    class _Fabricating(_ScriptedLLM):
        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            text, stop = _ScriptedLLM.generate_with_meta(self, prompt, response_format,
                                                         max_completion_tokens)
            if "identity, lineage" in prompt:
                out = json.loads(text)
                out["identity"]["summary"] = "A fully open 99B language model."
                return json.dumps(out), stop
            return text, stop

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _Fabricating(), allow_unpinned=True)
    assert art.card["identity"]["summary"] == "Not specified"
    refused = next(b for b in art.bindings if b.field_path == "identity.summary"
                   and b.verifier_action is VerifierAction.WITHHOLD)
    assert refused.verifier_reason == "leaf_value_not_in_cited_evidence"
    detail = next(d for d in art.metadata["leaf_support"] if d["field"] == "identity.summary")
    assert "9.9e+10" in detail["unsupported"] or "99" in detail["unsupported"]
    save_artifact(art, tmp_path / "card.json")
    assert load_artifact(tmp_path / "card.json").card["identity"]["summary"] == "Not specified"


def test_stage_b_cannot_author_a_structured_field_the_channel_did_not_fill(tmp_path):
    """Failure class: established_field_authored_by_stage_b. lineage.derivatives needs the
    Hub model tree, which nothing collects, so Stage B filling it from prose produced a
    string where the ledger requires a typed lineage row and lost the whole card
    (seen on OLMo-2-1124-7B-Instruct and Qwen3-8B, 2026-09-04). The same guard keeps a
    gated repo's README prose from posing as a config-derived context length."""
    root = _write_bundle(tmp_path / "bundles")

    class _Overreaching(_ScriptedLLM):
        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            text, stop = _ScriptedLLM.generate_with_meta(self, prompt, response_format,
                                                         max_completion_tokens)
            if "identity, lineage" in prompt:
                out = json.loads(text)
                ids = out["identity"]["provenance"]["summary"]["evidence_ids"]
                out["lineage"]["derivatives"] = "Many models derive from OLMo 2 7B."
                out["lineage"]["provenance"] = {
                    "derivatives": {"source": "hf_readme", "evidence": "q", "evidence_ids": ids}}
                return json.dumps(out), stop
            return text, stop

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _Overreaching(), allow_unpinned=True)
    assert art.card["lineage"]["derivatives"] == "Not specified"
    refused = next(b for b in art.bindings if b.field_path == "lineage.derivatives")
    assert refused.verifier_action is VerifierAction.WITHHOLD
    assert refused.verifier_reason == "established_field_without_structured_source"
    save_artifact(art, tmp_path / "card.json")
    assert load_artifact(tmp_path / "card.json").card["lineage"]["derivatives"] == "Not specified"


def test_replaying_one_bundle_twice_yields_the_same_bindings(tmp_path):
    """Failure class: unreplayable_composition. A bundle is frozen bytes, so two runs of
    the same code over it must differ only where the model's own answer differs and where
    the run records its own time. Anything else means a value depends on something the
    artifact does not record, and the card cannot be audited from its own contents."""
    root = _write_bundle(tmp_path / "bundles")
    first = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    second = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)

    def comparable(artifact):
        return [(b.field_path, b.proposed_value, b.relation_to_target.value,
                 b.verifier_action.value, b.verifier_reason,
                 tuple((e.source_uri, e.start_offset, e.end_offset, e.exact_text)
                       for e in b.evidence))
                for b in artifact.bindings
                if b.field_path != "provenance_and_quality.card_info"]

    assert comparable(first) == comparable(second)
    assert first.card == second.card or (
        # only the generation timestamp may differ
        {k: v for k, v in first.card["provenance_and_quality"]["card_info"].items()
         if k != "generated_at"}
        == {k: v for k, v in second.card["provenance_and_quality"]["card_info"].items()
            if k != "generated_at"})
    assert first.metadata["source_hashes"] == second.metadata["source_hashes"]


def test_a_card_round_trips_through_export_validate_and_render(tmp_path):
    """Failure class: export_round_trip_break. The card the pipeline writes has to survive
    save, load, the published schema, the source-excerpt guard and both renderers."""
    from model_cards.core.public import export_public, validate_public_card
    from model_cards.core.public_markdown import render_public_markdown
    from model_cards.core.render import render_html, render_markdown

    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    save_artifact(art, tmp_path / "card.json")
    reloaded = load_artifact(tmp_path / "card.json")
    assert reloaded.artifact_id == art.artifact_id

    projection = export_public(reloaded, reviewed=True)
    validate_public_card(projection)
    assert set(projection) == {"identity", "lineage", "specifications", "training_context",
                               "access_and_adoption", "evaluation", "links", "risks"}
    assert projection["identity"]["model_id"] == MODEL

    payload = json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    markdown = render_public_markdown(projection, json_filename="card.public.json",
                                      json_sha256=digest)
    assert markdown.startswith("# Model Card:") and digest in markdown
    assert "<script" not in render_html(reloaded, reviewed=True).lower()
    internal = render_markdown(reloaded, reviewed=True)
    assert "## Evidence bindings" in internal and "### Identity" in internal
    # the Withheld section appears exactly when something was withheld
    withheld = any(b.verifier_action is VerifierAction.WITHHOLD for b in reloaded.bindings)
    assert ("## Withheld" in internal) is withheld


def test_prose_that_copies_its_source_is_withheld_and_the_card_survives(tmp_path):
    """Failure class: copied_prose_loses_the_card. The writer is told to paraphrase and
    sometimes does not: on the 2026-09-05 roster seven of twelve cards carried a
    twelve-word run lifted verbatim out of a README, a paper or a developer blog page.
    Refusing the whole public export over one field lost eleven good fields with it."""
    from model_cards.core.public import export_public

    root = _write_bundle(tmp_path / "bundles")
    lifted = "OLMo 2 7B is a fully open language model trained on 4 trillion tokens."

    class _Copying(_ScriptedLLM):
        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            text, stop = _ScriptedLLM.generate_with_meta(self, prompt, response_format,
                                                         max_completion_tokens)
            if "identity, lineage" in prompt:
                out = json.loads(text)
                out["identity"]["summary"] = lifted
                return json.dumps(out), stop
            return text, stop

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _Copying(), allow_unpinned=True)
    assert art.card["identity"]["summary"] == "Not specified"
    refused = next(b for b in art.bindings if b.field_path == "identity.summary"
                   and b.verifier_reason == "prose_reproduces_source_excerpt")
    assert refused.verifier_action is VerifierAction.WITHHOLD
    assert "identity.summary" in art.metadata["source_excerpts"]
    # the rest of the card publishes
    projection = export_public(art, reviewed=False)
    assert projection["identity"]["model_id"] == MODEL
    assert projection["specifications"]["context_length"].startswith("4,096 tokens")


def test_a_mixture_of_experts_config_is_not_called_dense(tmp_path):
    """Failure class: moe_read_as_dense. DeepSeek-V3's config declares 256 routed experts
    and 8 per token, and the card called it a dense decoder-only model, one field away
    from an identity.model_type that said 671B total and 37B activated."""
    from model_cards.core.derivations import derive_architecture_type

    for config in ({"architectures": ["DeepseekV3ForCausalLM"], "model_type": "deepseek_v3",
                    "n_routed_experts": 256, "num_experts_per_tok": 8},
                   {"architectures": ["MixtralForCausalLM"], "num_local_experts": 8},
                   {"architectures": ["Qwen3MoeForCausalLM"], "moe_intermediate_size": 768}):
        assert derive_architecture_type(config)[0] == "mixture-of-experts"
    assert derive_architecture_type(
        {"architectures": ["Olmo2ForCausalLM"], "model_type": "olmo2"})[0] == "dense decoder-only"
    # a config that merely mentions experts with a falsy value is not a mixture
    assert derive_architecture_type(
        {"architectures": ["LlamaForCausalLM"], "num_local_experts": 0})[0] == "dense decoder-only"


def test_the_display_name_is_the_readme_title_or_the_repo_name(tmp_path):
    """Failure class: description_as_display_name. Left to the writer, identity.name came
    out as "Model Card for Mistral-7B-v0.3", "google/gemma-3-4b-it" and a comma-separated
    alias list. It is deterministic now: the README's own title when it names this repo,
    with the document boilerplate trimmed, otherwise the repo name."""
    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    assert art.card["identity"]["name"] == "OLMo-2-1124-7B"
    name = next(b for b in art.bindings if b.field_path == "identity.name")
    assert name.assignment_origin.value == "structured_explicit"

    # "# Model Card for OLMo 2 7B" titles the document, not the model
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    bundle_path = tmp_path / "bundles" / slug / "source_bundle" / "source-bundle.json"
    sb = json.loads(bundle_path.read_text())
    readme = README.replace("# OLMo-2-1124-7B", "# Model Card for OLMo-2-1124-7B")
    sb["files"][0] = _file("README.md", sb["files"][0]["source_uri"], readme)
    bundle_path.write_text(json.dumps(sb))
    hf_path = tmp_path / "bundles" / slug / "tool_output" / "hf" / f"{slug}.json"
    hf = json.loads(hf_path.read_text())
    hf["readme_markdown"] = readme
    hf_path.write_text(json.dumps(hf))
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    assert art.card["identity"]["name"] == "OLMo-2-1124-7B"


def test_the_licence_comes_from_the_hub_or_the_frontmatter_never_from_prose(tmp_path):
    """Failure class: badge_fragment_as_licence. With no license tag anywhere, the writer
    gave DeepSeek-V3 the licence "Model_License-Model_Agreement", read off a README badge.
    A GitHub README states the licence of the CODE, which is a different thing again."""
    root = _write_bundle(tmp_path / "bundles")
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    hf_path = tmp_path / "bundles" / slug / "tool_output" / "hf" / f"{slug}.json"
    hf = json.loads(hf_path.read_text())
    hf["tags"] = [t for t in hf["tags"] if not t.startswith("license:")]
    hf_path.write_text(json.dumps(hf))

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    # the README frontmatter still declares it, so the structured channel still has it
    assert art.card["identity"]["license"] == "apache-2.0"
    binding = next(b for b in art.bindings if b.field_path == "identity.license")
    assert binding.evidence[0].structured_pointer == "/readme_frontmatter/license"

    # with neither tag nor frontmatter, the honest value is Not specified
    extras_path = tmp_path / "bundles" / slug / "tool_output" / "extras" / f"{slug}.json"
    extras = json.loads(extras_path.read_text())
    extras["readme_frontmatter"] = {}
    extras_path.write_text(json.dumps(extras))
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    assert art.card["identity"]["license"] == "Not specified"


def test_a_link_field_that_is_not_a_url_is_withheld(tmp_path):
    """Failure class: prose_in_a_link_field. On Mistral-7B-Instruct-v0.2 the writer filled
    links.code_repository with "The instructed model can be downloaded here." That is a
    true sentence from the README, in a field that is supposed to be clickable, and the
    published schema accepts any non-empty string there, so nothing downstream caught it."""
    root = _write_bundle(tmp_path / "bundles")

    class _Prosey(_ScriptedLLM):
        def generate(self, prompt, response_format=None):
            if "SOURCE TEXT (model card README)" in prompt:
                return json.dumps({"evidence": [
                    {"field": "links.code_repository",
                     "quote": "Code: https://github.com/allenai/OLMo-core",
                     "referent": "target", "claim_role": "primary_result"}]})
            return _ScriptedLLM.generate(self, prompt, response_format)

        def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
            text, stop = _ScriptedLLM.generate_with_meta(self, prompt, response_format,
                                                         max_completion_tokens)
            if "evaluation, links" in prompt:
                out = json.loads(text)
                ids = {}
                for line in prompt.splitlines():
                    if line.startswith("- [E") and "]" in line:
                        ids.setdefault(line.split("(", 1)[1].split(" |", 1)[0], []).append(
                            line[3:line.index("]")])
                out["links"]["code_repository"] = "The model can be downloaded here."
                out["links"]["provenance"] = {"code_repository": {
                    "source": "hf_readme", "evidence": "q",
                    "evidence_ids": ids.get("links.code_repository", [])}}
                return json.dumps(out), stop
            return text, stop

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _Prosey(), allow_unpinned=True)
    assert art.card["links"]["code_repository"] == "Not specified"
    refused = next(b for b in art.bindings
                   if b.verifier_reason == "link_field_is_not_a_url")
    assert refused.field_path == "links.code_repository"
    assert refused.verifier_action is VerifierAction.WITHHOLD
    assert CL.is_url("https://github.com/allenai/OLMo") is True
    assert CL.is_url("see the repo") is False
    assert CL.is_url("github.com/allenai/OLMo") is False


def test_a_repository_with_no_readme_still_yields_a_card(tmp_path):
    """Failure class: no_readme_no_card. ontocord/wide_3b_sft_stage1.2-ss1-expert_fictional_lyrical
    has a config.json and four safetensors shards and no model card at all. Requiring a
    README refused it outright, and a repository with weights and a config is still a
    model: its card is the config and the Hub manifest."""
    root = _write_bundle(tmp_path / "bundles")
    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    bundle_path = tmp_path / "bundles" / slug / "source_bundle" / "source-bundle.json"
    sb = json.loads(bundle_path.read_text())
    sb["files"] = [f for f in sb["files"] if f["name"] != "README.md"]
    sb["metadata"]["available_files"] = ["config.json"]
    sb["metadata"]["card_data"] = {}
    bundle_path.write_text(json.dumps(sb))
    hf_path = tmp_path / "bundles" / slug / "tool_output" / "hf" / f"{slug}.json"
    hf = json.loads(hf_path.read_text())
    hf["readme_markdown"] = ""
    hf_path.write_text(json.dumps(hf))

    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    card = art.card
    assert card["identity"]["model_id"] == MODEL
    assert card["identity"]["name"] == "OLMo-2-1124-7B"          # the repo name
    assert card["specifications"]["architecture_type"] == "dense decoder-only"
    assert card["specifications"]["context_length"].startswith("4,096 tokens")
    assert card["access_and_adoption"]["downloads"].startswith("84,552")
    save_artifact(art, tmp_path / "card.json")
    assert load_artifact(tmp_path / "card.json").artifact_id == art.artifact_id


def test_a_family_name_has_to_be_one_the_sources_use(tmp_path):
    """Failure class: repo_name_leftover_as_a_family. Deriving the family from the repo
    name unconditionally gave jaspionjader/f-6-8b the family "f 6" and
    JayHyeon/Qwen_0.5-IRPO_3e-6-2ep_1alp_0lam the family "Qwen 0.5 IRPO 3e 6 2ep 1alp
    0lam", on 98.8% of the 2026-09-05 batch: noise presented as a fact. The build brief is
    explicit that a family is a developer-stated name."""
    from model_cards.core.compose_llm import family_is_developer_stated as stated

    readme = "# OLMo 2\nWe present OLMo 2, a family of fully open models."
    assert stated("OLMo 2", readme.lower()) is True
    assert stated("Mistral v0.3", "model card for mistral-7b-v0.3") is True
    assert stated("RomboUltima", "romboultima-32b is a merged model") is True
    # a leftover of the repo name that nothing calls a family
    assert stated("f 6", "") is False
    assert stated("BiBo v0.3", "") is False
    assert stated("Qwen 0.5 IRPO 3e 6 2ep 1alp 0lam", "qwen") is False
    assert stated("qwen continued v2.1", "") is False

    # end to end: the OLMo README names the family, so the card keeps it
    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    assert art.card["lineage"]["model_family"] == "OLMo 2"

    # strip every mention, in any casing (the BibTeX key is lowercase), and the field
    # becomes Not specified rather than a repo-name leftover
    import re as _re

    slug = "allenai-olmo-2-1124-7b-7df9a82518af"
    bundle_path = tmp_path / "bundles" / slug / "source_bundle" / "source-bundle.json"
    sb = json.loads(bundle_path.read_text())
    strip = lambda text: _re.sub(r"olmo", "Thing", text, flags=_re.IGNORECASE)
    stripped = strip(README)
    sb["files"][0] = _file("README.md", sb["files"][0]["source_uri"], stripped)
    bundle_path.write_text(json.dumps(sb))
    docling = (tmp_path / "bundles" / slug / "tool_output" / "docling" / f"{slug}.json")
    docling.write_text(json.dumps({"success": True, "filtered_text": strip(PAPER),
                                   "metadata": {}}))
    hf_path = tmp_path / "bundles" / slug / "tool_output" / "hf" / f"{slug}.json"
    hf = json.loads(hf_path.read_text())
    hf["readme_markdown"] = stripped
    hf_path.write_text(json.dumps(hf))
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    assert art.card["lineage"]["model_family"] == "Not specified"


def test_structured_pointers_resolve_in_the_file_they_name(tmp_path):
    """Failure class: structured_pointer_into_a_derived_wrapper. The config-backed
    anchors were written as /config/architectures and /config/max_position_embeddings,
    paths into the composer's internal view, not into the config.json they cite. The
    values were right and the click-through was dead: 409 spans over the 247-card batch
    of 2026-09-05 pointed at a key the named file does not have."""
    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    files = {f.source_uri: f for f in art.source_bundle.files}

    checked = 0
    for binding in art.bindings:
        for span in binding.evidence:
            pointer = span.structured_pointer
            source = files.get(span.source_uri)
            if not pointer or source is None or source.content is None:
                continue
            document = json.loads(source.content)
            assert SP.resolve_pointer(document, pointer) == span.structured_fragment, (
                f"{binding.field_path}: {pointer} does not resolve in {source.name}"
            )
            checked += 1
    assert checked >= 3

    arch = next(b for b in art.bindings
                if b.field_path == "specifications.architecture_type")
    assert arch.evidence[0].structured_pointer == "/architectures"
    ctx = next(b for b in art.bindings if b.field_path == "specifications.context_length")
    assert ctx.evidence[0].structured_pointer == "/max_position_embeddings"


def test_a_pointer_that_misses_the_file_is_refused_at_construction(tmp_path):
    """Failure class: structured_pointer_into_a_derived_wrapper. The guard lives where
    the span is built, so no caller can mint an anchor that does not resolve."""
    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    config = next(f for f in art.source_bundle.files if f.name == "config.json")

    with pytest.raises(SP.CompositionError, match="does not resolve"):
        SP._structured_evidence(art.source_bundle, config, "/config/architectures",
                                json.loads(config.content)["architectures"])
    with pytest.raises(SP.CompositionError, match="different value"):
        SP._structured_evidence(art.source_bundle, config, "/architectures", ["Wrong"])


class _FamilyRescopingLLM(_ScriptedLLM):
    """Stage A finds a family-scope post-training sentence; Stage B writes it as a fact
    about this checkpoint, which is what the writer did on Qwen3-8B-Base."""

    def __init__(self, phrasing):
        super().__init__()
        self.phrasing = phrasing

    def generate(self, prompt, response_format=None):
        if "SOURCE TEXT (research paper)" in prompt:
            self.prompts.append(prompt)
            return json.dumps({"evidence": [
                {"field": "training_context.adaptations",
                 "quote": "OLMo 2 models are post-trained with supervised finetuning, DPO and RLVR.",
                 "referent": "family:olmo-2", "claim_role": "primary_result"},
            ]})
        return super().generate(prompt, response_format)

    def generate_with_meta(self, prompt, response_format=None, max_completion_tokens=None):
        reply, stop = super().generate_with_meta(prompt, response_format, max_completion_tokens)
        if "specifications, training_context" in prompt:
            out = json.loads(reply)
            ids = [line[3:line.index("]")] for line in prompt.splitlines()
                   if line.startswith("- [E") and "training_context.adaptations" in line]
            out["training_context"]["adaptations"] = self.phrasing
            out["training_context"]["provenance"]["adaptations"] = {
                "source": "docling", "evidence": "q", "evidence_ids": ids}
            reply = json.dumps(out)
        return reply, stop


def test_a_family_statement_written_as_this_checkpoint_is_withheld(tmp_path, monkeypatch):
    """Failure class: family_statement_written_as_the_checkpoint. The gates let a family
    statement onto training_context.adaptations of a base checkpoint, at relation family,
    and the ledger said so. The writer then opened the sentence with "This checkpoint is",
    so the public card asserted of Qwen3-8B-Base that it was "produced through the
    Strong-to-Weak Distillation pipeline", a post-training stage its siblings went through
    and it did not (2026-09-06). The FactReasoner pass scored the sentence 0.9998
    supported, because the source says exactly that about the family; NLI cannot see
    the referent. Family-scope prose has to read as family-scope prose."""
    monkeypatch.setattr(sys.modules[__name__], "PAPER",
                        PAPER + " OLMo 2 models are post-trained with supervised finetuning, DPO and RLVR.")
    root = _write_bundle(tmp_path / "bundles")

    art = CL.compose_model_card_llm(
        f"{MODEL}@{REV}", root,
        _FamilyRescopingLLM("This checkpoint is post-trained with supervised finetuning, DPO and RLVR."),
        allow_unpinned=True)
    assert art.card["training_context"]["adaptations"] == "Not specified"
    withheld = [b for b in art.bindings if b.field_path == "training_context.adaptations"
                and b.verifier_action == VerifierAction.WITHHOLD]
    assert [b.verifier_reason for b in withheld] == ["family_statement_written_as_the_checkpoint"]
    assert withheld[0].relation_to_target.value == "family"
    assert withheld[0].proposed_value.startswith("This checkpoint")

    # the same statement phrased at family scope is allowed, still at relation family
    art = CL.compose_model_card_llm(
        f"{MODEL}@{REV}", root,
        _FamilyRescopingLLM("The OLMo 2 family is post-trained with supervised finetuning, DPO and RLVR."),
        allow_unpinned=True)
    assert art.card["training_context"]["adaptations"].startswith("The OLMo 2 family")
    accepted = next(b for b in art.bindings if b.field_path == "training_context.adaptations"
                    and b.verifier_action == VerifierAction.ACCEPT)
    assert accepted.relation_to_target.value == "family"


def test_a_final_claim_contradiction_flags_the_field_instead_of_withholding_it(tmp_path, monkeypatch):
    """Failure class: nli_contradiction_on_a_true_fragment. The first roster with the pass
    on (2026-09-06) produced two contradictions and both were false: "Mixture-of-Experts
    (MoE) language model" on DeepSeek-V3-Base at p_true 0.05 and "A Transformer-style
    dense autoregressive language model" on OLMo-2-7B at 0.16. A noun-phrase atom
    scored by NLI is not a reason to lose a value its quote supports; the field stays and
    is flagged where a reader looks."""
    root = _write_bundle(tmp_path / "bundles")
    monkeypatch.setattr(CL, "_run_final_claim_pass", lambda card, bindings, bundle, model_id: {
        "status": "ok", "reason": "test", "claims_built": 1, "atoms": [],
        "contradicted_fields": ["identity.model_type"]})
    art = CL.compose_model_card_llm(f"{MODEL}@{REV}", root, _ScriptedLLM(), allow_unpinned=True)
    assert art.card["identity"]["model_type"] == "An instruction-free base language model."
    assert "identity.model_type (final-claim pass contradiction)" in \
        art.card["provenance_and_quality"]["flagged_fields"]
    assert not any(b.verifier_reason == "final_claim_pass_contradiction" for b in art.bindings)
