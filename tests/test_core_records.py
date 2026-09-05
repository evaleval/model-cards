from __future__ import annotations

from datetime import datetime, timezone
import hashlib

import pytest
from pydantic import ValidationError

from model_cards.core.records import (
    AssignmentOrigin,
    BenchmarkScope,
    BindingRecord,
    CardArtifact,
    ClaimEntity,
    DerivationTrace,
    EvidenceSpan,
    RelationToTarget,
    ReviewEvent,
    SourceBundle,
    SourceFile,
    TargetIdentity,
    VerifierAction,
)
from model_cards.core.schema import (
    NOT_SPECIFIED,
    CARD_FIELD_PATHS,
    blank_card,
    flatten_card,
    get_field_value,
    set_field_value,
    validate_complete_card,
)


REVISION = "a" * 40
SOURCE_HASH = "b" * 64


def target() -> TargetIdentity:
    return TargetIdentity(
        model_id="owner/model",
        requested_revision="main",
        resolved_revision=REVISION,
    )


def text_evidence(**overrides: object) -> EvidenceSpan:
    values: dict[str, object] = {
        "source_uri": f"hf://owner/model@{REVISION}/README.md",
        "source_revision": REVISION,
        "source_sha256": SOURCE_HASH,
        "exact_text": "Model 7B",
        "start_offset": 10,
        "end_offset": 18,
        "section_path": ("Model details",),
        "context_before": "Name: ",
        "context_after": "\nLicense: Apache-2.0",
    }
    values.update(overrides)
    return EvidenceSpan(**values)


def binding(**overrides: object) -> BindingRecord:
    values: dict[str, object] = {
        "field_path": "identity.name",
        "proposed_value": "Model 7B",
        "target": target(),
        "claim_entity": {"model_id": "owner/model", "revision": REVISION},
        "relation_to_target": RelationToTarget.EXACT_TARGET,
        "assignment_origin": AssignmentOrigin.STRUCTURED_EXPLICIT,
        "evidence": (text_evidence(),),
        "verifier_action": VerifierAction.ACCEPT,
        "verifier_reason": "exact.literal_match",
    }
    values.update(overrides)
    return BindingRecord(**values)


def test_schema_v5_has_exactly_the_canonical_38_paths_and_fresh_blank_card() -> None:
    assert len(CARD_FIELD_PATHS) == 38
    assert len(set(CARD_FIELD_PATHS)) == 38
    assert CARD_FIELD_PATHS[0] == "identity.model_id"
    assert CARD_FIELD_PATHS[-1] == "provenance_and_quality.card_info"
    assert {
        "lineage.base_models",
        "evaluation.benchmark_scores",
        "links.tech_report",
        "provenance_and_quality.coverage_score",
    }.issubset(CARD_FIELD_PATHS)

    first = blank_card()
    second = blank_card()
    validate_complete_card(first)
    assert tuple(flatten_card(first)) == CARD_FIELD_PATHS
    assert set(flatten_card(first).values()) == {NOT_SPECIFIED}
    first["identity"]["name"] = "changed"
    assert second["identity"]["name"] == NOT_SPECIFIED


def test_indexed_field_paths_update_without_allowing_gaps() -> None:
    card = blank_card()
    set_field_value(
        card,
        "evaluation.benchmark_scores[0]",
        {"metric": "acc", "score": 0.7},
        create_missing=True,
    )
    set_field_value(
        card,
        "evaluation.benchmark_scores[1]",
        {"metric": "f1", "score": 0.6},
        create_missing=True,
    )
    assert get_field_value(card, "evaluation.benchmark_scores[1]") == {
        "metric": "f1",
        "score": 0.6,
    }
    with pytest.raises(IndexError, match="next valid index"):
        set_field_value(
            blank_card(),
            "evaluation.benchmark_scores[2]",
            {"score": 1},
            create_missing=True,
        )


def test_target_identity_retains_requested_revision_and_requires_exact_commit() -> None:
    parsed = TargetIdentity.from_spec(
        "owner/model@release-v1", resolved_revision=REVISION.upper()
    )
    assert parsed.requested_target == "owner/model@release-v1"
    assert parsed.canonical_target == f"owner/model@{REVISION}"
    assert str(parsed) == parsed.canonical_target

    with pytest.raises(ValidationError, match="40-character"):
        TargetIdentity(
            model_id="owner/model",
            requested_revision="main",
            resolved_revision="main",
        )
    with pytest.raises(ValueError, match="model_id@revision"):
        TargetIdentity.from_spec("owner/model", resolved_revision=REVISION)


@pytest.mark.parametrize(
    ("relation", "entity"),
    [
        (
            RelationToTarget.EXACT_TARGET,
            ClaimEntity(model_id="owner/model", revision=REVISION),
        ),
        (
            RelationToTarget.BASE,
            ClaimEntity(model_id="base/model", revision="base-release"),
        ),
        (
            RelationToTarget.DERIVATIVE,
            ClaimEntity(model_id="child/model", revision="child-release"),
        ),
        (
            RelationToTarget.SIBLING_OR_COMPARISON,
            ClaimEntity(label="Model 7B (reported comparison row)"),
        ),
    ],
)
def test_base_checkpoint_derivative_and_comparison_relations_round_trip(
    relation: RelationToTarget, entity: ClaimEntity
) -> None:
    record = binding(
        claim_entity=entity,
        relation_to_target=relation,
        verifier_action=VerifierAction.ACCEPT,
    )
    restored = BindingRecord.model_validate_json(record.model_dump_json())
    assert restored == record
    assert restored.relation_to_target is relation
    assert restored.claim_entity == entity


def test_exact_target_rejects_a_different_checkpoint() -> None:
    with pytest.raises(ValidationError, match="different|does not match"):
        binding(
            claim_entity={"model_id": "owner/model", "revision": "c" * 40},
            relation_to_target=RelationToTarget.EXACT_TARGET,
        )
    with pytest.raises(ValidationError, match="target commit"):
        binding(
            claim_entity={"model_id": "owner/model", "revision": "main"},
            relation_to_target=RelationToTarget.EXACT_TARGET,
        )
    with pytest.raises(ValidationError, match="target commit"):
        binding(
            claim_entity={"model_id": "owner/model"},
            relation_to_target=RelationToTarget.EXACT_TARGET,
        )


def test_binding_id_is_deterministic_and_serialization_is_lossless() -> None:
    first = binding()
    second = binding()
    assert first.binding_id == second.binding_id
    assert first.binding_id.startswith("bnd_")
    assert len(first.binding_id) == 28

    loaded = BindingRecord.model_validate_json(first.model_dump_json())
    assert loaded == first
    with pytest.raises(ValidationError, match="content-derived"):
        BindingRecord.model_validate(
            {**first.model_dump(mode="python"), "binding_id": "bnd_" + "0" * 24}
        )


def test_benchmark_scope_and_score_row_anchor_are_typed() -> None:
    scope = BenchmarkScope(
        benchmark_id="mmlu_pro",
        version="1.1",
        subset="law",
        split="test",
        setting={"shots": 5, "reasoning_mode": "direct"},
    )
    evidence = text_evidence(
        exact_text="Model 7B | 72.1",
        start_offset=40,
        end_offset=55,
        table_caption="Main results",
        table_header=("Model", "MMLU-Pro"),
        row_anchor="Model 7B",
    )
    score = binding(
        field_path="evaluation.benchmark_scores[0]",
        proposed_value={"metric": "accuracy", "score": 72.1},
        benchmark_scope=scope,
        evidence=(evidence,),
    )
    restored = BindingRecord.model_validate_json(score.model_dump_json())
    assert restored.benchmark_scope == scope
    assert restored.evidence[0].row_anchor == "Model 7B"
    assert restored.evidence[0].table_header == ("Model", "MMLU-Pro")

    with pytest.raises(ValidationError, match="benchmark_scope"):
        binding(
            field_path="evaluation.benchmark_scores[0]",
            proposed_value={"score": 72.1},
        )
    with pytest.raises(ValidationError, match="table header"):
        text_evidence(row_anchor="Model 7B")


def test_unknown_and_unresolved_assignments_must_be_withheld() -> None:
    unknown = binding(
        claim_entity={"label": "possibly another checkpoint"},
        relation_to_target=RelationToTarget.UNKNOWN,
        assignment_origin=AssignmentOrigin.UNRESOLVED,
        verifier_action=VerifierAction.WITHHOLD,
        verifier_reason="entity.unresolved",
    )
    assert unknown.verifier_action is VerifierAction.WITHHOLD
    with pytest.raises(ValidationError, match="unknown target relation"):
        binding(
            claim_entity={"label": "possibly another checkpoint"},
            relation_to_target=RelationToTarget.UNKNOWN,
            verifier_action=VerifierAction.ACCEPT,
        )


def test_target_identity_fields_and_self_relations_are_guarded() -> None:
    with pytest.raises(ValidationError, match="identity.model_id"):
        binding(field_path="identity.model_id", proposed_value="owner/other")
    with pytest.raises(ValidationError, match="identity.version"):
        binding(field_path="identity.version", proposed_value="c" * 40)
    with pytest.raises(ValidationError, match="self-referential"):
        binding(
            field_path="lineage.base_models[0]",
            proposed_value={"model_id": "owner/model", "relation": "base_model"},
            claim_entity=ClaimEntity(model_id="owner/model"),
            relation_to_target=RelationToTarget.BASE,
        )


def test_structured_pointer_fragment_and_derivation_trace_preserve_audit_inputs() -> None:
    structured = EvidenceSpan(
        source_uri=f"hf://owner/model@{REVISION}/config.json",
        source_revision=REVISION,
        source_sha256=SOURCE_HASH,
        structured_pointer="/max_position_embeddings",
        structured_fragment=4096,
        section_path=("config.json",),
    )
    record = binding(
        field_path="specifications.context_length",
        proposed_value=4096,
        evidence=(structured,),
        derivation_trace=DerivationTrace(
            rule="config.max_position_embeddings.literal",
            inputs={"/max_position_embeddings": 4096},
            output=4096,
        ),
        assignment_origin=AssignmentOrigin.STRUCTURED_EXPLICIT,
    )
    restored = BindingRecord.model_validate_json(record.model_dump_json())
    assert restored.assignment_origin is AssignmentOrigin.STRUCTURED_EXPLICIT
    assert restored.evidence[0].structured_fragment == 4096
    assert restored.derivation_trace is not None
    assert restored.derivation_trace.inputs == {"/max_position_embeddings": 4096}

    with pytest.raises(ValidationError, match="derivation trace output"):
        binding(
            field_path="specifications.context_length",
            proposed_value=4096,
            evidence=(structured,),
            derivation_trace=DerivationTrace(
                rule="config.max_position_embeddings.literal",
                inputs={"/max_position_embeddings": 4096},
                output=2048,
            ),
            assignment_origin=AssignmentOrigin.STRUCTURED_EXPLICIT,
        )

    with pytest.raises(ValidationError, match="structured_pointer.*structured_fragment"):
        EvidenceSpan(
            source_uri=f"hf://owner/model@{REVISION}/config.json",
            source_revision=REVISION,
            source_sha256=SOURCE_HASH,
            structured_pointer="/max_position_embeddings",
        )
    with pytest.raises(ValidationError, match="pointer/fragment"):
        EvidenceSpan(
            source_uri=f"hf://owner/model@{REVISION}/config.json",
            source_revision=REVISION,
            source_sha256=SOURCE_HASH,
        )


def test_source_bundle_and_complete_card_artifact_validate_and_round_trip() -> None:
    content = "# Model\n"
    encoded = content.encode("utf-8")
    source_file = SourceFile(
        name="README.md",
        source_uri=f"hf://owner/model@{REVISION}/README.md",
        sha256=hashlib.sha256(encoded).hexdigest(),
        size_bytes=len(encoded),
        media_type="text/markdown",
        content=content,
    )
    bundle = SourceBundle(
        target=target(),
        snapshot_path=f"/cache/snapshots/{REVISION}",
        metadata={"source": "local_cache"},
        files=(source_file,),
        retrieved_at=datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc),
        offline=True,
    )
    for foreign_uri in (
        f"hf://owner/other@{REVISION}/README.md",
        f"hf://owner/model@{'c' * 40}/README.md",
        f"hf://owner/model@{REVISION}/config.json",
    ):
        foreign = source_file.model_copy(update={"source_uri": foreign_uri})
        with pytest.raises(ValidationError, match="snapshot source URI"):
            SourceBundle(
                target=target(),
                snapshot_path=f"/cache/snapshots/{REVISION}",
                files=(foreign,),
                retrieved_at=datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc),
                offline=True,
            )
    card = blank_card()
    card["identity"]["name"] = "Model 7B"
    artifact = CardArtifact(
        target=target(),
        card=card,
        bindings=(
            binding(
                evidence=(
                    text_evidence(
                        source_sha256=source_file.sha256,
                        exact_text="Model",
                        start_offset=2,
                        end_offset=7,
                    ),
                ),
            ),
        ),
        metadata={"condition": "B"},
        source_bundle=bundle,
    )
    restored = CardArtifact.model_validate_json(artifact.model_dump_json())
    assert restored == artifact
    assert restored.source_bundle is not None
    assert restored.source_bundle.file("README.md").content == content

    with pytest.raises(ValidationError, match="sha256 does not match"):
        SourceFile(
            name="README.md",
            source_uri="hf://owner/model/README.md",
            sha256="0" * 64,
            size_bytes=len(encoded),
            media_type="text/markdown",
            content=content,
        )
    with pytest.raises(ValidationError, match="unsupported.*scheme"):
        SourceFile(
            name="README.md",
            source_uri="javascript:alert(1)",
            sha256=source_file.sha256,
            size_bytes=len(encoded),
            media_type="text/markdown",
            content=content,
        )
    mismatched_evidence = binding()
    with pytest.raises(ValidationError, match="evidence hash"):
        CardArtifact(
            target=target(),
            card=blank_card(),
            bindings=(mismatched_evidence,),
            metadata={"condition": "B"},
            source_bundle=bundle,
        )
    wrong_span = binding(
        evidence=(
            text_evidence(
                source_sha256=source_file.sha256,
                exact_text="Wrong",
                start_offset=2,
                end_offset=7,
            ),
        )
    )
    with pytest.raises(ValidationError, match="exact evidence span"):
        CardArtifact(
            target=target(),
            card=blank_card(),
            bindings=(wrong_span,),
            metadata={"condition": "B"},
            source_bundle=bundle,
        )
    incomplete = blank_card()
    del incomplete["identity"]["name"]
    with pytest.raises(ValidationError, match="card fields"):
        CardArtifact(target=target(), card=incomplete)


def test_artifact_id_covers_card_metadata_sources_and_review_log() -> None:
    card = blank_card()
    card["identity"]["name"] = "Model 7B"
    artifact = CardArtifact(target=target(), card=card, bindings=(binding(),))
    payload = artifact.model_dump(mode="python")

    changed_card = blank_card()
    changed_card["identity"]["name"] = "Tampered"
    with pytest.raises(ValidationError, match="BindingRecord projection"):
        CardArtifact.model_validate({**payload, "card": changed_card})
    with pytest.raises(ValidationError, match="content-derived"):
        CardArtifact.model_validate({**payload, "metadata": {"tampered": True}})


def test_review_event_round_trip_keeps_explicit_null_correction_auditable() -> None:
    event = ReviewEvent(
        binding_id=binding().binding_id,
        action=VerifierAction.REASSIGN,
        reason_code="human.corrected",
        actor="reviewer@example.org",
        corrected_value=None,
    )
    assert event.assignment_origin is AssignmentOrigin.HUMAN_CORRECTED
    assert event.corrected_value_set is True
    restored = ReviewEvent.model_validate_json(event.model_dump_json())
    assert restored.corrected_value_set is True
    assert restored.corrected_value is None
