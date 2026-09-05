from __future__ import annotations

import hashlib
import json

from model_cards.core.records import (
    AssignmentOrigin,
    BenchmarkScope,
    BindingRecord,
    CardArtifact,
    DerivationTrace,
    EvidenceSpan,
    RelationToTarget,
    TargetIdentity,
    VerifierAction,
)
from model_cards.core.render import (
    render_html,
    render_markdown,
    save_html,
    save_markdown,
)
from model_cards.core.review import reassign_binding
from model_cards.core.schema import blank_card, set_field_value


REVISION = "d" * 40
SOURCE_HASH = "e" * 64


def artifact() -> CardArtifact:
    target = TargetIdentity(
        model_id="org/model",
        requested_revision="main",
        resolved_revision=REVISION,
    )
    evidence = EvidenceSpan(
        source_uri=f"hf://org/model@{REVISION}/README.md",
        source_revision=REVISION,
        source_sha256=SOURCE_HASH,
        exact_text="Model <script>alert(1)</script> | 91.2",
        start_offset=100,
        end_offset=138,
        section_path=("Evaluation", "Main results"),
        table_caption="Headline results",
        table_header=("Model", "MMLU-Pro"),
        row_anchor="Model <script>alert(1)</script>",
        context_before="| Model | Score |\n",
        context_after="\n| Other | 90.0 |",
    )
    record = BindingRecord(
        field_path="evaluation.benchmark_scores[0]",
        proposed_value={
            "model": "Model <script>alert(1)</script>",
            "metric": "accuracy",
            "score": 91.2,
        },
        target=target,
        claim_entity={"model_id": "org/model", "revision": REVISION},
        relation_to_target=RelationToTarget.EXACT_TARGET,
        benchmark_scope=BenchmarkScope(
            benchmark_id="mmlu-pro",
            version="1.0",
            subset="all",
            split="test",
            setting={"shots": 5},
        ),
        assignment_origin=AssignmentOrigin.LLM_INFERRED,
        evidence=(evidence,),
        derivation_trace=DerivationTrace(
            rule="model_index.row_to_score",
            inputs={"row_label": "Model <script>alert(1)</script>", "column": "MMLU-Pro"},
            output={
                "model": "Model <script>alert(1)</script>",
                "metric": "accuracy",
                "score": 91.2,
            },
        ),
        verifier_action=VerifierAction.ACCEPT,
        verifier_reason="row.exact_target",
    )
    card = blank_card()
    set_field_value(card, record.field_path, record.proposed_value, create_missing=True)
    identity_records = []
    for field_path, value, pointer in (
        ("identity.model_id", target.model_id, "/target/model_id"),
        ("identity.version", target.resolved_revision, "/target/resolved_revision"),
    ):
        payload = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        identity_record = BindingRecord(
            field_path=field_path,
            proposed_value=value,
            target=target,
            claim_entity={"model_id": target.model_id, "revision": REVISION},
            relation_to_target=RelationToTarget.EXACT_TARGET,
            assignment_origin=AssignmentOrigin.STRUCTURED_EXPLICIT,
            evidence=(
                EvidenceSpan(
                    source_uri=f"hf://model/{target.model_id}@{REVISION}",
                    source_revision=REVISION,
                    source_sha256=hashlib.sha256(payload).hexdigest(),
                    structured_pointer=pointer,
                    structured_fragment=value,
                ),
            ),
            verifier_action=VerifierAction.ACCEPT,
            verifier_reason="target.manifest",
        )
        set_field_value(card, field_path, value)
        identity_records.append(identity_record)
    initial = CardArtifact(
        target=target,
        card=card,
        bindings=(record, *identity_records),
    )
    return reassign_binding(
        initial,
        record.binding_id,
        reason_code="human.metric_normalized",
        actor="reviewer",
        corrected_value={
            "model": "Model <script>alert(1)</script>",
            "metric": "accuracy_percent",
            "score": 91.2,
        },
    )


def test_markdown_renderer_is_readable_and_audit_complete() -> None:
    markdown = render_markdown(artifact())
    assert "# Model Card: org/model" in markdown
    assert f"org/model@{REVISION}" in markdown
    assert "reviewed projection" in markdown
    assert "evaluation.benchmark_scores[0]` — reassign" in markdown
    assert "MMLU-Pro" in markdown
    assert "Row anchor: `Model <script>alert(1)</script>`" in markdown
    assert "Exact whitespace-normalized offsets: `100:138`" in markdown
    assert "model_index.row_to_score" in markdown
    assert "human.metric_normalized" in markdown
    assert "accuracy_percent" in markdown


def test_html_renderer_is_self_contained_script_free_and_escapes_evidence() -> None:
    html = render_html(artifact())
    assert html.startswith("<!doctype html>")
    assert "<style>" in html
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert f"org/model@{REVISION}" in html
    assert "Headline results" in html
    assert "human.metric_normalized" in html
    assert "reviewer" in html
    assert "Evidence bindings" in html


def test_renderers_can_write_standalone_files(tmp_path) -> None:
    card = artifact()
    markdown_path = save_markdown(card, tmp_path / "report.md")
    html_path = save_html(card, tmp_path / "report.html")
    assert markdown_path.read_text(encoding="utf-8") == render_markdown(card)
    assert html_path.read_text(encoding="utf-8") == render_html(card)


def _inspector_artifact():
    """One accepted and one withheld binding on the same field."""
    from model_cards.core.records import (
        AssignmentOrigin, BindingRecord, CardArtifact, ClaimEntity, EvidenceSpan,
        RelationToTarget, TargetIdentity, VerifierAction,
    )
    from model_cards.core.schema import blank_card, set_field_value

    target = TargetIdentity(model_id="org/target", requested_revision="a" * 40,
                            resolved_revision="a" * 40)
    span = EvidenceSpan(source_uri="https://huggingface.co/org/target/blob/main/README.md",
                        source_revision="a" * 40, source_sha256="b" * 64,
                        exact_text="Target 7B scores 63.7 on MMLU.", start_offset=0,
                        end_offset=len("Target 7B scores 63.7 on MMLU."))
    other = EvidenceSpan(source_uri="https://arxiv.org/abs/2501.00656",
                         source_revision="a" * 40, source_sha256="c" * 64,
                         exact_text="Base 7B was pretrained on 4 trillion tokens.",
                         start_offset=0,
                         end_offset=len("Base 7B was pretrained on 4 trillion tokens."))
    accepted = BindingRecord(
        field_path="evaluation.results_summary", proposed_value="Scores 63.7 on MMLU.",
        target=target, claim_entity=ClaimEntity(model_id="org/target", revision="a" * 40),
        relation_to_target=RelationToTarget.EXACT_TARGET,
        assignment_origin=AssignmentOrigin.LLM_INFERRED, evidence=(span,),
        verifier_action=VerifierAction.ACCEPT, verifier_reason="llm_bound_exact_target")
    withheld = BindingRecord(
        field_path="training_context.training_data_size",
        proposed_value="Base 7B was pretrained on 4 trillion tokens.", target=target,
        claim_entity=ClaimEntity(model_id="org/base"), relation_to_target=RelationToTarget.BASE,
        assignment_origin=AssignmentOrigin.UNRESOLVED, evidence=(other,),
        verifier_action=VerifierAction.WITHHOLD,
        verifier_reason="numeric_value_of_base_not_this_checkpoint")
    card = blank_card()
    set_field_value(card, "evaluation.results_summary", "Scores 63.7 on MMLU.")
    return CardArtifact(target=target, card=card, bindings=(accepted, withheld))


def test_inspector_gives_every_field_a_click_through_to_its_span() -> None:
    """Failure class: value_without_a_path_to_its_source. A card value the reader cannot
    trace to a quote is an assertion, which is the thing this pipeline exists to avoid."""
    artifact = _inspector_artifact()
    html = render_html(artifact, reviewed=False)
    accepted, withheld = artifact.bindings
    # the field row links to the binding, and the binding section is the anchor
    assert f'href="#{accepted.binding_id}"' in html
    assert f'id="{accepted.binding_id}"' in html
    assert 'id="field-evaluation.results_summary"' in html
    # the relation and the reason are visible without opening anything
    assert "exact_target" in html and "llm_bound_exact_target" in html
    # the quote itself is the link text
    assert "Target 7B scores 63.7 on MMLU." in html
    # still script-free and self-contained
    assert "<script" not in html.lower() and "http-equiv" not in html.lower()


def test_inspector_shows_what_was_withheld_and_why() -> None:
    """Failure class: silent_withhold. A refused value that is invisible to the reader is
    indistinguishable from a source that never said it."""
    artifact = _inspector_artifact()
    html = render_html(artifact, reviewed=False)
    _, withheld = artifact.bindings
    assert "<h2>Withheld</h2>" in html
    assert "numeric_value_of_base_not_this_checkpoint" in html
    assert f'href="#{withheld.binding_id}"' in html
    assert "1 withheld" in html
    markdown = render_markdown(artifact, reviewed=False)
    assert "## Withheld" in markdown
    assert "numeric_value_of_base_not_this_checkpoint" in markdown
    assert "[exact_target]" in markdown and "[1 withheld]" in markdown
