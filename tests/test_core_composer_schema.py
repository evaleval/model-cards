"""The v5 CardSchema must carry exactly the frozen 38 paths and drive the composer's
prompt builders and validator without any benchmark wording leaking in."""

import json

from model_cards.core import composer_schema as CS
from model_cards.core.schema import CARD_FIELD_PATHS, blank_card

from auto_benchmarkcard.tools.composer import composer_tool as C
from auto_benchmarkcard.tools.composer import evidence as E
from auto_benchmarkcard.tools.composer import validator as V


def test_v5_schema_has_exactly_the_frozen_paths():
    sch = CS.model_card_schema()
    assert tuple(CS.field_paths(sch)) == CARD_FIELD_PATHS
    assert len(CARD_FIELD_PATHS) == 38
    assert sch.composed_sections == ["identity", "lineage", "specifications", "training_context",
                                     "access_and_adoption", "evaluation", "links"]
    sch.assert_groups_cover()
    # every curator field and every cap names a real v5 path
    assert set(sch.curator_fields) <= set(CARD_FIELD_PATHS)
    assert set(sch.field_caps) <= set(CARD_FIELD_PATHS)
    assert set(sch.established_fields) <= set(CARD_FIELD_PATHS)


def test_routing_classes():
    sch = CS.model_card_schema()
    assert sch.field_class("specifications.architecture_type") == "enum"
    assert sch.field_class("identity.model_id") == "established"
    assert sch.field_class("evaluation.benchmark_scores") == "structured"
    assert sch.field_class("training_context.training_data") == "prose"
    assert sch.enum_vocab("access_and_adoption.access_type") == {"open-weight", "gated", "api-only"}
    assert sch.enum_vocab("specifications.model_size") is None
    assert sch.not_applicable == "Not applicable"


def test_extraction_prompt_names_the_checkpoint_not_a_benchmark():
    sch = CS.model_card_schema()
    fields = E.fields_for_source("paper", sch)
    assert "training_context.training_data" in fields and "identity.model_id" not in fields
    prompt = E.build_extraction_prompt("research paper", fields, "OLMo-2-1124-7B",
                                       source_text="OLMo 2 7B was trained on 4 trillion tokens.",
                                       schema=sch)
    assert prompt.startswith(CS.EXTRACTION_SYSTEM)
    assert 'about the model "OLMo-2-1124-7B"' in prompt
    assert "Ignore other models, checkpoints, sizes, or variants" in prompt
    assert "benchmark" not in prompt.split("Allowed fields:")[0].lower()


def test_stage_b_prompt_and_validator_round_trip():
    sch = CS.model_card_schema()
    prompt = C._build_group_prompt("specs_training_access",
                                   ["specifications", "training_context", "access_and_adoption"],
                                   sch.section_models, {}, {"specifications.architecture_type": "dense decoder-only"},
                                   "", schema=sch)
    assert "section(s) of a model card" in prompt
    assert "NEVER a base model's pretraining data attributed to a derivative" in prompt
    assert "architecture_type [enum]: already established" in prompt
    assert "judge_" not in prompt

    # The model contract has no Stage-B-authored enum: architecture_type comes from
    # config.json and access_type from the Hub's gated flag, so both are established and
    # a value Stage B invents for them is dropped rather than argued with.
    out = {"specifications": {"architecture_type": "chatty", "num_parameters": "7B",
                              "context_length": "4096", "precision": "Not applicable",
                              "model_size": "16.1 GiB", "input_output": ["text"],
                              "provenance": {"num_parameters": {"evidence_ids": ["E1"]},
                                             "context_length": {"evidence_ids": ["E1"]},
                                             "model_size": {"evidence_ids": ["E1"]},
                                             "input_output": {"evidence_ids": ["E1"]}}},
           "training_context": {"training_data": "Not specified", "training_data_size": "Not specified",
                                "data_cutoff": "Not specified", "adaptations": "Not specified", "provenance": {}},
           "access_and_adoption": {"access_type": "chatty", "downloads": "Not specified",
                                   "likes": "Not specified", "provenance": {}}}
    norm, errors, stats = V.validate_sections(
        out, ["specifications", "training_context", "access_and_adoption"], sch.section_models,
        {"E1"}, set(), schema=sch)
    assert errors == []
    assert norm["specifications"]["architecture_type"] == "Not specified"
    assert norm["access_and_adoption"]["access_type"] == "Not specified"
    assert norm["specifications"]["precision"] == "Not applicable"     # third state survives
    assert norm["specifications"]["input_output"] == ["text"]
    # a value with no cited evidence is the reportable error
    out["specifications"]["provenance"].pop("input_output")
    _, errors, _ = V.validate_sections(
        out, ["specifications", "training_context", "access_and_adoption"], sch.section_models,
        {"E1"}, set(), schema=sch)
    assert [(e.type, e.path) for e in errors] == [("evidence_missing", "specifications.input_output")]


def test_value_fields_reject_sentences():
    sch = CS.model_card_schema()
    assert {"identity.name", "identity.release_date", "training_context.data_cutoff"} <= sch.value_fields
    out = {"identity": {"model_id": "allenai/OLMo-2-1124-7B-Instruct",
                        "name": "The official display name is OLMo-2-1124-7B-Instruct.",
                        "developed_by": "Not specified", "model_type": "Not specified", "license": "apache-2.0",
                        "release_date": "The model was released in November 2024.",
                        "version": "470b1fba1ae01581f270116362ee4aa1b97f4c84", "summary": "Not specified",
                        "provenance": {"name": {"evidence_ids": ["E1"]}, "release_date": {"evidence_ids": ["E1"]},
                                       "license": {"evidence_ids": ["E1"]}}},
           "lineage": {"base_models": "Not specified", "model_family": "Not specified",
                       "derivatives": "Not specified", "provenance": {}}}
    _, errors, _ = V.validate_sections(out, ["identity", "lineage"], sch.section_models, {"E1"}, set(), schema=sch)
    assert sorted((e.path, e.type) for e in errors) == [("identity.name", "sentence_in_value_field"),
                                                         ("identity.release_date", "sentence_in_value_field")]
    out["identity"]["name"] = "OLMo-2-1124-7B-Instruct"
    out["identity"]["release_date"] = "November 2024"
    _, errors, _ = V.validate_sections(out, ["identity", "lineage"], sch.section_models, {"E1"}, set(), schema=sch)
    assert errors == []


def test_blank_card_matches_section_models():
    sch = CS.model_card_schema()
    card = blank_card()
    for sec, model in sch.section_models.items():
        for fname in model.model_fields:
            if fname == "provenance" and sec != "provenance_and_quality":
                continue
            assert fname in card[sec], (sec, fname)
