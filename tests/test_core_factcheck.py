"""The final-claim pass runs when it can, and says so when it cannot.

Failure class: silent_validation_absence. A validation step that is quietly missing reads
exactly like one that passed. The card records the pass's status and reason either way.
"""

from __future__ import annotations

import pytest

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
    assert "logprobs" in recorded["reason"]
    assert art.metadata["final_claim_pass"]["status"] == "disabled"
