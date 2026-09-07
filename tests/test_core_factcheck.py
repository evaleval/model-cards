"""The final-claim pass runs when it can, and says so when it cannot.

Failure class: silent_validation_absence. A validation step that is quietly missing reads
exactly like one that passed. The card records the pass's status and reason either way.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from model_cards.core import factcheck as F
from model_cards.core.records import (
    AssignmentOrigin, BindingRecord, ClaimEntity, EvidenceSpan, RelationToTarget,
    TargetIdentity, VerifierAction,
)
from model_cards.core.schema import blank_card, set_field_value

REV = "a" * 40
URI = "https://huggingface.co/org/target/blob/main/README.md"


def _binding(path, value, exact):
    return BindingRecord(
        field_path=path, proposed_value=value,
        target=TargetIdentity(model_id="org/target", requested_revision=REV,
                              resolved_revision=REV),
        claim_entity=ClaimEntity(model_id="org/target", revision=REV),
        relation_to_target=RelationToTarget.EXACT_TARGET,
        assignment_origin=AssignmentOrigin.LLM_INFERRED,
        evidence=(EvidenceSpan(source_uri=URI, source_revision=REV, source_sha256="b" * 64,
                               exact_text=exact, start_offset=0, end_offset=len(exact)),),
        verifier_action=VerifierAction.ACCEPT, verifier_reason="llm_bound_exact_target")


def test_claims_are_the_prose_fields_with_their_cited_source_windows():
    card = blank_card()
    set_field_value(card, "identity.summary", "A fully open seven billion parameter model.")
    set_field_value(card, "specifications.num_parameters", "7,298,617,344 parameters")
    quote = "Target 7B is a fully open language model."
    source = "Header. " + quote + " More prose that follows the quote in the README."
    claims = F.build_claims(card, [_binding("identity.summary", "A fully open model.", quote)],
                            {URI: source}, "org/target")
    assert [a["field"] for a in claims["atoms"]] == ["identity.summary"]
    # a value field is not a prose claim, and an unbound prose field contributes nothing
    assert all(a["field"] != "specifications.num_parameters" for a in claims["atoms"])
    assert claims["contexts"][0]["text"].startswith("Header.")
    assert quote in claims["contexts"][0]["text"]
    assert claims["topic"] == "org/target"


def test_a_prose_field_without_a_binding_is_not_claimed():
    card = blank_card()
    set_field_value(card, "identity.summary", "A summary with no binding behind it.")
    claims = F.build_claims(card, [], {URI: "source"}, "org/target")
    assert claims["atoms"] == []


def test_a_withheld_binding_does_not_become_a_claim():
    card = blank_card()
    set_field_value(card, "identity.summary", "A fully open model.")
    withheld = _binding("identity.summary", "A fully open model.", "Target 7B is open.")
    withheld = withheld.model_copy(update={
        "verifier_action": VerifierAction.WITHHOLD,
        "verifier_reason": "leaf_value_not_in_cited_evidence", "binding_id": ""})
    claims = F.build_claims(card, [withheld], {URI: "Target 7B is open."}, "org/target")
    assert claims["atoms"] == []


def test_an_unrunnable_pass_reports_why_instead_of_passing(monkeypatch):
    """silent_validation_absence."""
    card = blank_card()
    set_field_value(card, "identity.summary", "A fully open model.")
    quote = "Target 7B is open."
    monkeypatch.delenv("FACTREASONER_MODEL", raising=False)
    monkeypatch.delenv("FACTREASONER_API_BASE", raising=False)
    monkeypatch.delenv("FACTREASONER_API_KEY", raising=False)
    result = F.final_claim_pass(card, [_binding("identity.summary", "A fully open model.", quote)],
                                {URI: quote}, "org/target", probe=False)
    assert result["status"] == "unavailable"
    assert "FACTREASONER_MODEL" in result["reason"]
    assert result["claims_built"] == 1
    assert result["contradicted_fields"] == []


def test_the_pass_is_off_by_default_and_the_card_records_that(tmp_path, monkeypatch):
    """silent_validation_absence, end to end: a card composed today says the pass did not
    run and why, rather than leaving the reader to assume it did."""
    from model_cards.core import compose_llm as CL
    from tests.test_core_compose_llm import MODEL, REV as CREV, _ScriptedLLM, _write_bundle

    monkeypatch.delenv("MODELCARDS_FACTCHECK", raising=False)
    root = _write_bundle(tmp_path / "bundles")
    art = CL.compose_model_card_llm(f"{MODEL}@{CREV}", root, _ScriptedLLM(), allow_unpinned=True)
    recorded = art.card["provenance_and_quality"]["provenance"]["final_claim_pass"]
    assert recorded["status"] == "disabled"
    assert recorded["reason"] == "MODELCARDS_FACTCHECK is not set"
    assert art.metadata["final_claim_pass"]["status"] == "disabled"


def test_the_pass_reads_marginals_not_the_counts_block():
    """Failure class: factreasoner_result_misread. The composer tool returns the per-atom
    verdicts under "marginals"; "results" is a dict of counts. The first reader iterated
    "results" as the atom list and died on its first key, so every end-to-end run
    reported status failed with claims_built 0 (2026-09-06, after the route was fixed)."""
    from model_cards.core.factcheck import read_outcomes

    claims = {"atoms": [
        {"id": "a0", "field": "identity.summary", "text": "X is a base model."},
        {"id": "a1", "field": "training_context.adaptations", "text": "X was distilled."},
        {"id": "a2", "field": "evaluation.results_summary", "text": "X scores 99 on MMLU."},
        {"id": "a3", "field": "identity.model_type", "text": "Causal language model."},
    ]}
    results = {
        "results": {"num_atoms": 4, "num_contexts": 6, "factuality_score": 0.5},
        "marginals": [
            {"variable": "a0", "probabilities": [0.01, 0.99], "p_true": 0.99},
            {"variable": "a1", "probabilities": [0.5, 0.5], "p_true": 0.5},
            {"variable": "a2", "probabilities": [0.9, 0.1], "p_true": 0.1},
            {"variable": "a3", "probabilities": [0.6, 0.4], "p_true": 0.4},
        ],
        "escalation": {"escalated_atoms": 1, "still_neutral": ["a1"]},
    }
    out = read_outcomes(claims, results)
    assert [(o["atom"], o["label"]) for o in out["atoms"]] == [
        ("a0", "supported"), ("a1", "neutral"), ("a2", "contradicted"), ("a3", "uncertain")]
    assert out["contradicted_fields"] == ["evaluation.results_summary"]
    assert out["factuality_score"] == 0.5
    assert out["escalation"]["still_neutral"] == ["a1"]
    assert out["label_counts"] == {"supported": 1, "neutral": 1, "uncertain": 1,
                                   "contradicted": 1, "unscored": 0}
    # an atom the library never scored is visible as such, not silently supported
    out = read_outcomes(claims, {"results": {}, "marginals": [{"variable": "a0"}]})
    assert out["atoms"][0]["label"] == "unscored"


def test_the_route_pins_a_provider_that_returns_logprobs(monkeypatch):
    """Failure class: logprobs_dropped_by_provider_routing. OpenRouter answers from the
    cheapest endpoint for a model, and most of them drop `logprobs` silently, so the
    2026-09-05 probes of four models all came back empty. Naming the provider with no
    fallback is what makes the NLI extractor's logprobs arrive. `require_parameters` is
    deliberately absent: Mellea sends request fields the provider does not advertise, and
    with the flag OpenRouter returned 404 "Filter by Parameters" on the first NLI call."""
    from model_cards.core.factcheck import provider_body, route_from_env

    assert provider_body("") == {}
    body = provider_body("Novita")
    assert body == {"provider": {"order": ["Novita"], "allow_fallbacks": False}}
    assert "require_parameters" not in body["provider"]

    monkeypatch.setenv("FACTREASONER_PROVIDER", "Novita")
    monkeypatch.setenv("FACTREASONER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    assert route_from_env()["provider"] == "Novita"


def test_merlin_and_the_cache_are_absolute_not_cwd_relative(monkeypatch, tmp_path):
    """Failure class: cwd_relative_library_defaults. The composer tool defaults to
    "merlin/bin/merlin" and "factreasoner_cache" relative to whatever directory the batch
    was started in; the first end-to-end run reached the probabilistic layer and died
    with FileNotFoundError on the relative merlin path."""
    from model_cards.core import factcheck as F

    fake = tmp_path / "merlin"
    fake.write_bytes(b"#!/bin/sh\n")
    monkeypatch.setenv("MERLIN_BIN", str(fake))
    assert F.merlin_path() == str(fake)
    monkeypatch.setenv("MERLIN_BIN", str(tmp_path / "absent"))
    assert F.merlin_path() == ""
    monkeypatch.setenv("FACTREASONER_CACHE_DIR", str(tmp_path / "cache"))
    assert F.cache_dir() == str(tmp_path / "cache")
    monkeypatch.delenv("FACTREASONER_CACHE_DIR")
    assert Path(F.cache_dir()).is_absolute()


def test_the_provider_value_is_an_order(monkeypatch):
    """Failure class: single_provider_rate_limited. Novita answered 429 on four of twelve
    probes with four cards in flight (2026-09-06); a second logprobs provider stands
    behind the first, fallbacks outside the list stay off."""
    from model_cards.core.factcheck import provider_body

    assert provider_body("Novita, AkashML") == {
        "provider": {"order": ["Novita", "AkashML"], "allow_fallbacks": False}}
    assert provider_body("Novita") == {"provider": {"order": ["Novita"], "allow_fallbacks": False}}
