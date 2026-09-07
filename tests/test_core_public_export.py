"""The public export is the contract, and nothing from the sources rides along.

Failure classes:
  private_section_leaks       the ledger or the quality block reaches the public JSON
  invalid_public_json         the export does not validate against the published schema
  source_excerpt_leaks        a prose field is a run lifted out of a frozen source
  markdown_render_drift       the Markdown companion stops matching the public renderer
"""

from __future__ import annotations

import hashlib
import json

import pytest

from model_cards.core.public import (
    PublicationError,
    assert_no_source_excerpt,
    assert_public_projection,
    public_projection,
    validate_public_card,
)
from model_cards.core.public_markdown import render_public_markdown
from model_cards.core.schema import NOT_SPECIFIED, blank_card, set_field_value


def _card():
    card = blank_card()
    set_field_value(card, "identity.model_id", "allenai/OLMo-2-1124-7B")
    set_field_value(card, "identity.name", "OLMo-2-1124-7B")
    set_field_value(card, "identity.summary", "A fully open seven billion parameter model.")
    set_field_value(card, "links.tech_report", "https://arxiv.org/abs/2501.00656")
    set_field_value(card, "lineage.base_models",
                    [{"model_id": "allenai/OLMo-2-1124-7B-DPO", "relation": "base_model",
                      "kind": "finetune"}])
    set_field_value(card, "evaluation.benchmark_scores",
                    [{"benchmark": "MMLU", "metric": "accuracy", "score": "63.7",
                      "setting": "5-shot"}])
    set_field_value(card, "provenance_and_quality.coverage_score", 0.7)
    return card


def test_the_projection_drops_the_private_section_and_validates():
    """private_section_leaks, invalid_public_json."""
    projection = public_projection(_card())
    assert "provenance_and_quality" not in projection
    assert not any("provenance" in section for section in projection.values())
    assert_public_projection(projection)
    validate_public_card(projection)


def test_a_projection_with_an_extra_key_is_refused():
    """private_section_leaks."""
    projection = public_projection(_card())
    projection["identity"]["provenance"] = {"summary": {"evidence_ids": ["E1"]}}
    with pytest.raises(PublicationError, match="field set for identity"):
        assert_public_projection(projection)
    projection["identity"].pop("provenance")
    projection["provenance_and_quality"] = {"coverage_score": 0.7}
    with pytest.raises(PublicationError, match="sections do not match"):
        assert_public_projection(projection)


def test_a_value_that_breaks_the_published_schema_is_refused():
    """invalid_public_json."""
    projection = public_projection(_card())
    projection["evaluation"]["benchmark_scores"] = [{"benchmark": "MMLU", "score": "63.7"}]
    with pytest.raises(PublicationError, match="published schema"):
        validate_public_card(projection)
    projection = public_projection(_card())
    projection["lineage"]["base_models"][0]["relation"] = "base"
    with pytest.raises(PublicationError, match="published schema"):
        validate_public_card(projection)


def test_twelve_words_of_a_frozen_source_are_refused_in_prose():
    """source_excerpt_leaks."""
    source = ("OLMo 2 is a family of fully open language models trained on up to five "
              "trillion tokens of curated web data.")
    projection = public_projection(_card())
    projection["identity"]["summary"] = (
        "OLMo 2 is a family of fully open language models trained on up to five trillion "
        "tokens.")
    with pytest.raises(PublicationError, match="identity.summary"):
        assert_no_source_excerpt(projection, [source])
    # a genuine synthesis of the same source passes
    projection["identity"]["summary"] = "A fully open model family trained on curated web text."
    assert_no_source_excerpt(projection, [source]) is None
    # and a field with no source at all is not guarded into failure
    assert_no_source_excerpt(projection, []) is None


def test_a_script_without_word_spaces_is_guarded_by_character_run():
    """source_excerpt_leaks: the Qwen and DeepSeek sources are partly Chinese, where a
    whole sentence is one whitespace-delimited word."""
    source = "通义千问是阿里巴巴集团推出的大规模语言模型系列，支持多语言理解与生成任务。"
    projection = public_projection(_card())
    projection["evaluation"]["results_summary"] = source[:30]
    with pytest.raises(PublicationError, match="evaluation.results_summary"):
        assert_no_source_excerpt(projection, [source])


def test_the_markdown_companion_renders_the_contract():
    """markdown_render_drift."""
    projection = public_projection(_card())
    payload = json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    text = render_public_markdown(projection, json_filename="card.json", json_sha256=digest)
    assert text.startswith("# Model Card: OLMo")
    assert "automated candidate generated from public sources" in text
    assert f"SHA-256: `{digest}`" in text
    assert "| Benchmark | Metric | Score | Setting | Split |" in text
    assert "| MMLU | accuracy | 63\\.7 | 5\\-shot | Not reported |" in text
    assert "base model; Kind: finetune" in text
    assert "`evaluation.safety_evals`" in text          # unavailable fields are named
    assert "<script" not in text
    with pytest.raises(ValueError):
        render_public_markdown(projection, json_filename="../escape.json", json_sha256=digest)
