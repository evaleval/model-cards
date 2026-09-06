"""The card the pipeline emits is the published contract, and nothing else.

Failure classes:
  contract_drift          a field is added, renamed or dropped without the contract moving
  private_section_leaks   provenance_and_quality reaches the public JSON
  invalid_public_json     a composed card does not validate against the published schema
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from model_cards.core.composer_schema import field_paths, model_card_schema
from model_cards.core.schema import (
    CARD_FIELD_PATHS,
    NOT_SPECIFIED,
    PUBLIC_FIELD_PATHS,
    PUBLIC_SECTIONS,
    blank_card,
)

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "model-card.schema.json"


def published_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_the_card_carries_exactly_the_published_fields():
    """contract_drift."""
    doc = published_schema()
    assert list(doc["properties"]) == list(PUBLIC_SECTIONS)
    published = [f"{section}.{field}"
                 for section in doc["properties"]
                 for field in doc["$defs"][section]["properties"]]
    assert list(PUBLIC_FIELD_PATHS) == published
    assert len(published) == 34 and len(doc["properties"]) == 8
    # the composer schema carries the same paths plus the one private section
    assert tuple(field_paths(model_card_schema())) == CARD_FIELD_PATHS
    assert set(CARD_FIELD_PATHS) - set(PUBLIC_FIELD_PATHS) == {
        f"provenance_and_quality.{f}" for f in
        ("provenance", "flagged_fields", "missing_fields", "coverage_score", "card_info")}


def test_a_blank_card_validates_against_the_published_schema():
    """invalid_public_json, private_section_leaks."""
    card = blank_card()
    public = {section: dict(card[section]) for section in PUBLIC_SECTIONS}
    for section in public.values():
        section.pop("provenance", None)
    jsonschema.validate(public, published_schema())
    assert "provenance_and_quality" not in public


@pytest.mark.parametrize("path,value", [
    ("specifications.model_size", "16.1 GiB of safetensors weights (17,314,942,976 bytes) in BF16"),
    ("specifications.input_output", ["input: text", "output: text"]),
    ("access_and_adoption.likes", "1,204 likes on the Hub (as of 2026-09-04)"),
    ("links.citation", "@misc{olmo2, title={2 OLMo 2 Furious} }"),
])
def test_the_new_contract_fields_validate(path, value):
    """contract_drift: the four fields the earlier internal schema did not have."""
    section, field = path.split(".")
    card = blank_card()
    card[section][field] = value
    public = {s: {k: v for k, v in card[s].items() if k != "provenance"} for s in PUBLIC_SECTIONS}
    jsonschema.validate(public, published_schema())


def test_the_dropped_fields_are_gone():
    """contract_drift: model_stage, related_model_scores and evaluation_sources were dropped."""
    for gone in ("specifications.model_stage", "evaluation.related_model_scores",
                 "evaluation.evaluation_sources", "specifications.modalities"):
        assert gone not in CARD_FIELD_PATHS
    assert model_card_schema().curator_fields.get("specifications.model_stage") is None


def test_lineage_rows_use_the_contract_relation_vocabulary():
    """contract_drift: the published modelReference relation is base_model, not base."""
    doc = published_schema()
    assert doc["$defs"]["modelReference"]["properties"]["relation"]["enum"] == [
        "base_model", "derivative_model"]
    card = blank_card()
    card["lineage"]["base_models"] = [
        {"model_id": "allenai/OLMo-2-1124-7B-DPO", "relation": "base_model", "kind": "finetune"}]
    public = {s: {k: v for k, v in card[s].items() if k != "provenance"} for s in PUBLIC_SECTIONS}
    jsonschema.validate(public, published_schema())
    assert NOT_SPECIFIED == "Not specified"
