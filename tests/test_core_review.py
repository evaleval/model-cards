from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json

import pytest
from pydantic import ValidationError

from model_cards.core.records import (
    AssignmentOrigin,
    BenchmarkScope,
    BindingRecord,
    CardArtifact,
    ClaimEntity,
    EvidenceSpan,
    RelationToTarget,
    TargetIdentity,
    VerifierAction,
)
from model_cards.core.review import (
    ReviewConflictError,
    ReviewError,
    accept_binding,
    effective_binding,
    export_reviewed_artifact,
    export_reviewed_card,
    load_artifact,
    reassign_binding,
    reviewed_projection_paths,
    save_artifact,
    withhold_binding,
)
from model_cards.core.schema import (
    NOT_SPECIFIED,
    blank_card,
    canonical_field_path,
    parse_field_path,
    set_field_value,
)


REVISION = "1" * 40
SOURCE_HASH = "2" * 64


def target() -> TargetIdentity:
    return TargetIdentity(
        model_id="org/target-model",
        requested_revision="release",
        resolved_revision=REVISION,
    )


def evidence(
    text: str = "Target Model",
    *,
    start: int = 0,
    row: str | None = None,
) -> EvidenceSpan:
    values: dict[str, object] = {
        "source_uri": f"hf://org/target-model@{REVISION}/README.md",
        "source_revision": REVISION,
        "source_sha256": SOURCE_HASH,
        "exact_text": text,
        "start_offset": start,
        "end_offset": start + len(text),
        "section_path": ("Evaluation",),
    }
    if row is not None:
        values.update(
            {
                "table_caption": "Reported results",
                "table_header": ("Model", "Score"),
                "row_anchor": row,
            }
        )
    return EvidenceSpan(**values)


def binding(**overrides: object) -> BindingRecord:
    values: dict[str, object] = {
        "field_path": "identity.name",
        "proposed_value": "Target Model",
        "target": target(),
        "claim_entity": {"model_id": target().model_id, "revision": REVISION},
        "relation_to_target": RelationToTarget.EXACT_TARGET,
        "assignment_origin": AssignmentOrigin.LLM_INFERRED,
        "evidence": (evidence(),),
        "verifier_action": VerifierAction.ACCEPT,
        "verifier_reason": "entity.exact_match",
    }
    values.update(overrides)
    return BindingRecord(**values)


def artifact(*bindings: BindingRecord) -> CardArtifact:
    records = list(bindings)
    target_values = (
        ("identity.model_id", target().model_id, "/target/model_id"),
        ("identity.version", target().resolved_revision, "/target/resolved_revision"),
    )
    existing = {canonical_field_path(record.field_path) for record in records}
    for field_path, value, pointer in target_values:
        if field_path in existing:
            continue
        fragment = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        records.append(
            binding(
                field_path=field_path,
                proposed_value=value,
                evidence=(
                    EvidenceSpan(
                        source_uri=(
                            f"hf://model/{target().model_id}@{target().resolved_revision}"
                        ),
                        source_revision=target().resolved_revision,
                        source_sha256=hashlib.sha256(fragment).hexdigest(),
                        structured_pointer=pointer,
                        structured_fragment=value,
                    ),
                ),
                assignment_origin=AssignmentOrigin.STRUCTURED_EXPLICIT,
                verifier_reason="target.manifest",
            )
        )
    card = blank_card()
    grouped: dict[str, list[tuple[tuple[int, ...], object]]] = {}
    for record in records:
        if record.verifier_action is VerifierAction.WITHHOLD:
            continue
        canonical, indexes = parse_field_path(record.field_path)
        grouped.setdefault(canonical, []).append((indexes, record.proposed_value))
    for canonical, assignments in grouped.items():
        if all(len(indexes) == 1 for indexes, _ in assignments):
            by_index = {indexes[0]: value for indexes, value in assignments}
            set_field_value(card, canonical, [by_index[index] for index in sorted(by_index)])
        else:
            for indexes, value in assignments:
                path = canonical + "".join(f"[{index}]" for index in indexes)
                set_field_value(card, path, value, create_missing=True)
    return CardArtifact(target=target(), card=card, bindings=tuple(records))


def test_reviewed_export_includes_accept_and_excludes_unknown_withhold() -> None:
    accepted = binding()
    unresolved = binding(
        field_path="identity.summary",
        proposed_value="Possibly copied from the base model",
        claim_entity={"label": "ambiguous README subject"},
        relation_to_target=RelationToTarget.UNKNOWN,
        assignment_origin=AssignmentOrigin.UNRESOLVED,
        verifier_action=VerifierAction.WITHHOLD,
        verifier_reason="entity.ambiguous",
    )
    reviewed = export_reviewed_card(artifact(accepted, unresolved))
    assert reviewed["identity"]["name"] == "Target Model"
    assert reviewed["identity"]["summary"] == NOT_SPECIFIED


def test_append_only_withhold_then_accept_keeps_both_events_and_old_artifact() -> None:
    record = binding()
    original = artifact(record)
    first_time = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    withheld = withhold_binding(
        original,
        record.binding_id,
        reason_code="human.needs_check",
        actor="alice",
        created_at=first_time,
    )
    accepted = accept_binding(
        withheld,
        record.binding_id,
        reason_code="human.source_verified",
        actor="bob",
        created_at=first_time + timedelta(seconds=1),
    )

    assert original.review_events == ()
    assert len(withheld.review_events) == 1
    assert len(accepted.review_events) == 2
    assert len({original.artifact_id, withheld.artifact_id, accepted.artifact_id}) == 3
    assert accepted.review_events[1].supersedes_event_id == accepted.review_events[0].event_id
    assert export_reviewed_card(withheld)["identity"]["name"] == NOT_SPECIFIED
    assert export_reviewed_card(accepted)["identity"]["name"] == "Target Model"

    payload = accepted.model_dump(mode="python")
    events = [dict(event) for event in payload["review_events"]]
    events[1]["supersedes_event_id"] = None
    payload["review_events"] = events
    with pytest.raises(ValidationError, match="prior event"):
        CardArtifact.model_validate(payload)


def test_unknown_binding_cannot_be_accepted_until_human_reassignment() -> None:
    unknown = binding(
        claim_entity={"label": "unresolved checkpoint label"},
        relation_to_target=RelationToTarget.UNKNOWN,
        assignment_origin=AssignmentOrigin.UNRESOLVED,
        verifier_action=VerifierAction.WITHHOLD,
        verifier_reason="entity.unresolved",
    )
    initial = artifact(unknown)
    with pytest.raises(ReviewError, match="reassign"):
        accept_binding(
            initial,
            unknown.binding_id,
            reason_code="human.verified",
        )

    corrected = reassign_binding(
        initial,
        unknown.binding_id,
        reason_code="human.exact_checkpoint",
        actor="curator",
        field_path="identity.summary",
        corrected_value="Verified summary",
        claim_entity={"model_id": target().model_id, "revision": REVISION},
        relation_to_target=RelationToTarget.EXACT_TARGET,
    )
    state = effective_binding(corrected, unknown.binding_id)
    assert state.action is VerifierAction.REASSIGN
    assert state.assignment_origin is AssignmentOrigin.HUMAN_CORRECTED
    assert state.field_path == "identity.summary"
    assert state.value == "Verified summary"
    assert state.reason_code == "human.exact_checkpoint"
    reviewed = export_reviewed_card(corrected)
    assert reviewed["identity"]["name"] == NOT_SPECIFIED
    assert reviewed["identity"]["summary"] == "Verified summary"


def test_reviewed_export_compacts_withheld_comparison_rows_and_keeps_scope() -> None:
    comparison = binding(
        field_path="evaluation.benchmark_scores[0]",
        proposed_value={"model": "Comparison 7B", "metric": "accuracy", "score": 82.0},
        claim_entity={"label": "Comparison 7B"},
        relation_to_target=RelationToTarget.SIBLING_OR_COMPARISON,
        evidence=(evidence("Comparison 7B | 82.0", start=20, row="Comparison 7B"),),
        assignment_origin=AssignmentOrigin.LLM_INFERRED,
        verifier_action=VerifierAction.WITHHOLD,
        verifier_reason="row.comparison_not_target",
    )
    target_row = binding(
        field_path="evaluation.benchmark_scores[1]",
        proposed_value={"model": "Target Model", "metric": "accuracy", "score": 84.5},
        benchmark_scope=BenchmarkScope(
            benchmark_id="evalsuite/task",
            version="2026-08",
            subset="hard",
            split="test",
            setting={"shots": 0, "reasoning_mode": "direct"},
        ),
        evidence=(evidence("Target Model | 84.5", start=50, row="Target Model"),),
    )
    reviewed = export_reviewed_card(artifact(comparison, target_row))
    assert reviewed["evaluation"]["benchmark_scores"] == [target_row.proposed_value]
    paths = reviewed_projection_paths(artifact(comparison, target_row))
    assert paths[target_row.binding_id] == "evaluation.benchmark_scores[0]"
    assert comparison.binding_id not in paths
    state = effective_binding(artifact(comparison, target_row), target_row.binding_id)
    assert state.benchmark_scope is not None
    assert state.benchmark_scope.version == "2026-08"
    assert state.benchmark_scope.subset == "hard"
    assert state.benchmark_scope.split == "test"


def test_review_correction_and_events_survive_save_load_and_reviewed_export(tmp_path) -> None:
    record = binding()
    initial = artifact(record)
    corrected = reassign_binding(
        initial,
        record.binding_id,
        reason_code="human.display_name_corrected",
        actor="reviewer-17",
        corrected_value="Target Model v1",
        note="Matched the exact repository heading.",
    )
    path = tmp_path / "card.json"
    save_artifact(corrected, path)
    loaded = load_artifact(path)
    exported = export_reviewed_artifact(loaded)

    assert loaded == corrected
    assert exported.card["identity"]["name"] == "Target Model v1"
    assert exported.review_events[0].assignment_origin is AssignmentOrigin.HUMAN_CORRECTED
    assert exported.review_events[0].corrected_value_set is True
    assert exported.bindings[0].proposed_value == "Target Model"
    assert exported.bindings[0].assignment_origin is AssignmentOrigin.LLM_INFERRED
    assert exported.artifact_id != loaded.artifact_id


def test_reassign_exact_target_rejects_a_branch_alias() -> None:
    record = binding()
    with pytest.raises(ReviewError, match="checkpoint"):
        reassign_binding(
            artifact(record),
            record.binding_id,
            reason_code="human.bad_alias",
            claim_entity={"model_id": target().model_id, "revision": "main"},
            relation_to_target=RelationToTarget.EXACT_TARGET,
        )


def test_conflicting_accepted_bindings_fail_loudly() -> None:
    first = binding(proposed_value="Target Model")
    second = binding(
        proposed_value="Different Name",
        evidence=(evidence("Different Name", start=100),),
    )
    with pytest.raises(ValidationError, match="conflicting"):
        artifact(first, second)


def test_reassigning_benchmark_score_without_scope_is_rejected() -> None:
    record = binding()
    with pytest.raises(ReviewError, match="benchmark scope"):
        reassign_binding(
            artifact(record),
            record.binding_id,
            reason_code="human.moved_score",
            field_path="evaluation.benchmark_scores[0]",
            corrected_value={"score": 84.5},
        )


def test_non_target_fact_cannot_export_as_unqualified_target_field() -> None:
    sibling_report = binding(
        field_path="links.tech_report",
        proposed_value="https://arxiv.org/abs/2401.00001",
        claim_entity={"label": "comparison system"},
        relation_to_target=RelationToTarget.SIBLING_OR_COMPARISON,
        verifier_action=VerifierAction.ACCEPT,
    )
    with pytest.raises(ReviewError, match="cannot be exported"):
        export_reviewed_card(artifact(sibling_report))


def test_target_manifest_identity_cannot_be_withheld_or_changed() -> None:
    initial = artifact(binding())
    model_id_binding = next(
        item for item in initial.bindings if item.field_path == "identity.model_id"
    )
    with pytest.raises(ReviewError, match="reviewed identity.model_id"):
        withhold_binding(
            initial,
            model_id_binding.binding_id,
            reason_code="human.invalid_withhold",
        )
    with pytest.raises(ReviewError, match="identity.model_id"):
        reassign_binding(
            initial,
            model_id_binding.binding_id,
            reason_code="human.invalid_target_change",
            corrected_value="org/other",
        )


def test_benchmark_value_scope_and_unresolved_scope_are_export_guards() -> None:
    scope = BenchmarkScope(
        benchmark_id="bench",
        version="v1",
        split="test",
        setting={"shots": 0},
    )
    score = binding(
        field_path="evaluation.benchmark_scores[0]",
        proposed_value={
            "benchmark_id": "bench",
            "version": "v1",
            "split": "test",
            "setting": {"shots": 0},
            "metric": "acc",
            "value": 0.9,
        },
        benchmark_scope=scope,
        evidence=(evidence("Target | 0.9", row="Target"),),
    )
    initial = artifact(score)
    with pytest.raises(ReviewError, match="version.*contradicts"):
        reassign_binding(
            initial,
            score.binding_id,
            reason_code="human.partial_scope_change",
            benchmark_scope=scope.model_copy(update={"version": "v2"}),
        )

    comparison = binding(
        field_path="evaluation.benchmark_scores",
        proposed_value={"status": "comparison-row candidate"},
        claim_entity={"label": "comparison row"},
        relation_to_target=RelationToTarget.SIBLING_OR_COMPARISON,
        benchmark_scope=BenchmarkScope(
            benchmark_id="unresolved_markdown_comparison_table",
            setting={"table_index": 0},
        ),
        evidence=(evidence("Other | 1", row="Other"),),
        verifier_action=VerifierAction.WITHHOLD,
        verifier_reason="row.unresolved",
    )
    with pytest.raises(ReviewError, match="resolved scope"):
        reassign_binding(
            artifact(comparison),
            comparison.binding_id,
            reason_code="human.partial_exact_reassign",
            claim_entity={"model_id": target().model_id, "revision": REVISION},
            relation_to_target=RelationToTarget.EXACT_TARGET,
        )


def test_lineage_value_must_match_corrected_claim_entity() -> None:
    base = binding(
        field_path="lineage.base_models[0]",
        proposed_value={"model_id": "org/base-a", "relation": "base_model"},
        claim_entity={"model_id": "org/base-a"},
        relation_to_target=RelationToTarget.BASE,
    )
    with pytest.raises(ReviewError, match="lineage value"):
        reassign_binding(
            artifact(base),
            base.binding_id,
            reason_code="human.partial_lineage_change",
            claim_entity={"model_id": "org/base-b"},
        )


def test_the_lineage_rule_has_one_definition() -> None:
    """Failure class: duplicated_invariant_drift. records.py and review.py each carried
    their own copy of the lineage row rule. When the contract moved to base_model /
    derivative_model only one copy moved, so every card with a base_model tag saved
    cleanly and then failed to render, which is the worst place to find out."""
    from model_cards.core import records as R
    from model_cards.core import review as V

    assert R.lineage_expectations("lineage.base_models") == (R.RelationToTarget.BASE, "base_model")
    assert R.lineage_expectations("lineage.derivatives") == (
        R.RelationToTarget.DERIVATIVE, "derivative_model")
    assert V.lineage_expectations is R.lineage_expectations
    assert V.LINEAGE_FIELDS is R.LINEAGE_FIELDS

    row = BindingRecord(
        field_path="lineage.base_models",
        proposed_value={"model_id": "org/base-a", "relation": "base_model", "kind": "finetune"},
        target=target(), claim_entity=ClaimEntity(model_id="org/base-a"),
        relation_to_target=RelationToTarget.BASE,
        assignment_origin=AssignmentOrigin.STRUCTURED_EXPLICIT,
        evidence=(evidence(),), verifier_action=VerifierAction.ACCEPT,
        verifier_reason="structured_explicit_source")
    artifact_with_row = artifact(row)
    # the same row must survive both validators, not only the one that built it
    assert effective_binding(artifact_with_row, row.binding_id).value["relation"] == "base_model"
    export_reviewed_card(artifact_with_row)


def test_the_reviewed_export_carries_what_generation_accepted() -> None:
    """Failure class: projection_divergence. The generation-time card and the reviewed
    projection are two views of one ledger. The reviewed one refused a family binding the
    gates had allowed, so any card with an accepted family statement composed and saved
    cleanly and then could not be rendered, published or judged at all."""
    from model_cards.core.model_gates import FAMILY_ALLOWED_FIELDS

    family = BindingRecord(
        field_path="training_context.training_data",
        proposed_value="Trained on the OLMo 2 pretraining mixture.",
        target=target(), claim_entity=ClaimEntity(label="OLMo 2"),
        relation_to_target=RelationToTarget.FAMILY,
        assignment_origin=AssignmentOrigin.LLM_INFERRED, evidence=(evidence(),),
        verifier_action=VerifierAction.ACCEPT,
        verifier_reason="family_statement_allowed_for_this_field")
    card = artifact(family)
    projected = export_reviewed_card(card)
    assert projected["training_context"]["training_data"].startswith("Trained on")
    assert "training_context.training_data" in FAMILY_ALLOWED_FIELDS

    # a family statement on a field the policy does not cover is still refused
    off_policy = BindingRecord(
        field_path="specifications.num_parameters", proposed_value="7B to 13B",
        target=target(), claim_entity=ClaimEntity(label="OLMo 2"),
        relation_to_target=RelationToTarget.FAMILY,
        assignment_origin=AssignmentOrigin.LLM_INFERRED, evidence=(evidence(),),
        verifier_action=VerifierAction.ACCEPT, verifier_reason="should_not_have_passed")
    with pytest.raises(ReviewError, match="specifications.num_parameters"):
        export_reviewed_card(artifact(off_policy))
