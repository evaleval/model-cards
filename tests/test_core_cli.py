from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from model_cards.core import cli
from model_cards.core.records import (
    AssignmentOrigin,
    BindingRecord,
    CardArtifact,
    EvidenceSpan,
    RelationToTarget,
    SourceBundle,
    SourceFile,
    TargetIdentity,
    VerifierAction,
)
from model_cards.core.review import load_artifact, save_artifact
from model_cards.core.schema import NOT_SPECIFIED, blank_card, set_field_value
from model_cards.core.source import ModelSourceError


REVISION = "a" * 40
def _target() -> TargetIdentity:
    return TargetIdentity(
        model_id="org/target",
        requested_revision=REVISION,
        resolved_revision=REVISION,
    )


def _evidence(text: str = "Target Model") -> EvidenceSpan:
    source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return EvidenceSpan(
        source_uri=f"hf://org/target@{REVISION}/README.md",
        source_revision=REVISION,
        source_sha256=source_hash,
        exact_text=text,
        start_offset=0,
        end_offset=len(text),
        section_path=("Model",),
    )


def _accepted_binding() -> BindingRecord:
    return BindingRecord(
        field_path="identity.name",
        proposed_value="Target Model",
        target=_target(),
        claim_entity={"model_id": "org/target", "revision": REVISION},
        relation_to_target=RelationToTarget.EXACT_TARGET,
        assignment_origin=AssignmentOrigin.STRUCTURED_EXPLICIT,
        evidence=(_evidence(),),
        verifier_action=VerifierAction.ACCEPT,
        verifier_reason="source.exact_target",
    )


def _unknown_binding() -> BindingRecord:
    return BindingRecord(
        field_path="identity.summary",
        proposed_value="An ambiguous summary",
        target=_target(),
        claim_entity={"label": "ambiguous README subject"},
        relation_to_target=RelationToTarget.UNKNOWN,
        assignment_origin=AssignmentOrigin.UNRESOLVED,
        evidence=(_evidence("An ambiguous summary"),),
        verifier_action=VerifierAction.WITHHOLD,
        verifier_reason="entity.unresolved",
    )


def _artifact(*bindings: BindingRecord) -> CardArtifact:
    records = list(bindings)
    for field_path, value, pointer in (
        ("identity.model_id", _target().model_id, "/target/model_id"),
        ("identity.version", _target().resolved_revision, "/target/resolved_revision"),
    ):
        if any(record.field_path.split("[", 1)[0] == field_path for record in records):
            continue
        fragment = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        records.append(
            BindingRecord(
                field_path=field_path,
                proposed_value=value,
                target=_target(),
                claim_entity={"model_id": "org/target", "revision": REVISION},
                relation_to_target=RelationToTarget.EXACT_TARGET,
                assignment_origin=AssignmentOrigin.STRUCTURED_EXPLICIT,
                evidence=(
                    EvidenceSpan(
                        source_uri=f"hf://model/org/target@{REVISION}",
                        source_revision=REVISION,
                        source_sha256=hashlib.sha256(fragment).hexdigest(),
                        structured_pointer=pointer,
                        structured_fragment=value,
                    ),
                ),
                verifier_action=VerifierAction.ACCEPT,
                verifier_reason="target.manifest",
            )
        )
    card = blank_card()
    for binding in records:
        if binding.verifier_action is VerifierAction.ACCEPT:
            set_field_value(card, binding.field_path, binding.proposed_value, create_missing=True)
    content = bindings[0].evidence[0].exact_text if bindings else "# target\n"
    assert content is not None
    raw = content.encode("utf-8")
    source_file = SourceFile(
        name="README.md",
        source_uri=f"hf://org/target@{REVISION}/README.md",
        sha256=hashlib.sha256(raw).hexdigest(),
        size_bytes=len(raw),
        media_type="text/markdown",
        content=content,
    )
    source_bundle = SourceBundle(
        target=_target(),
        snapshot_path=f"/cache/{REVISION}",
        files=(source_file,),
        retrieved_at=datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc),
        offline=True,
    )
    return CardArtifact(
        target=_target(),
        card=card,
        bindings=tuple(records),
        source_bundle=source_bundle,
    )


def _save(tmp_path: Path, artifact: CardArtifact, name: str = "input.json") -> Path:
    path = tmp_path / name
    save_artifact(artifact, path)
    return path


def test_inspect_field_and_binding_in_readable_and_json_forms(tmp_path, capsys) -> None:
    record = _accepted_binding()
    source = _save(tmp_path, _artifact(record))

    assert cli.main(["inspect", str(source), "--field", "identity.name"]) == 0
    text = capsys.readouterr().out
    assert "Selected field: identity.name" in text
    assert record.binding_id in text
    assert "Target Model" in text

    assert (
        cli.main(
            [
                "inspect",
                str(source),
                "--binding",
                record.binding_id,
                "--format",
                "json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["binding"]["effective"]["field_path"] == "identity.name"
    assert payload["binding"]["evidence"][0]["exact_text"] == "Target Model"


def test_accept_and_withhold_append_events_without_overwriting_input(tmp_path) -> None:
    record = _accepted_binding()
    source = _save(tmp_path, _artifact(record))
    withheld_path = tmp_path / "withheld.json"
    accepted_path = tmp_path / "accepted.json"

    assert (
        cli.main(
            [
                "withhold",
                str(source),
                record.binding_id,
                "--reason",
                "human.needs_check",
                "--actor",
                "reviewer-1",
                "-o",
                str(withheld_path),
            ]
        )
        == 0
    )
    assert load_artifact(source).review_events == ()
    withheld = load_artifact(withheld_path)
    assert [event.action for event in withheld.review_events] == [VerifierAction.WITHHOLD]

    assert (
        cli.main(
            [
                "accept",
                str(withheld_path),
                record.binding_id,
                "--reason",
                "human.source_verified",
                "-o",
                str(accepted_path),
            ]
        )
        == 0
    )
    accepted = load_artifact(accepted_path)
    assert [event.action for event in accepted.review_events] == [
        VerifierAction.WITHHOLD,
        VerifierAction.ACCEPT,
    ]
    assert accepted.review_events[1].supersedes_event_id == accepted.review_events[0].event_id


def test_review_command_rejects_input_as_output(tmp_path, capsys) -> None:
    record = _accepted_binding()
    source = _save(tmp_path, _artifact(record))
    before = source.read_bytes()
    assert (
        cli.main(
            [
                "withhold",
                str(source),
                record.binding_id,
                "--reason",
                "human.needs_check",
                "-o",
                str(source),
                "--force",
            ]
        )
        == 2
    )
    assert source.read_bytes() == before
    assert "distinct from the input" in capsys.readouterr().err


def test_incompatible_non_target_reassign_writes_no_unusable_artifact(
    tmp_path, capsys
) -> None:
    record = _unknown_binding()
    source = _save(tmp_path, _artifact(record))
    output = tmp_path / "invalid-reviewed.json"
    assert (
        cli.main(
            [
                "reassign",
                str(source),
                record.binding_id,
                "--relation",
                "sibling_or_comparison",
                "--reason",
                "human.incompatible",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()
    assert "cannot be exported" in capsys.readouterr().err


def test_reassign_corrects_unknown_entity_value_and_relation(tmp_path) -> None:
    record = _unknown_binding()
    source = _save(tmp_path, _artifact(record))
    output = tmp_path / "reassigned.json"
    corrected = {"text": "Verified exact-target summary"}

    assert (
        cli.main(
            [
                "reassign",
                str(source),
                record.binding_id,
                "--reason",
                "human.exact_checkpoint",
                "--value-json",
                json.dumps(corrected),
                "--entity-model-id",
                "org/target",
                "--entity-revision",
                REVISION,
                "--relation",
                "exact_target",
                "-o",
                str(output),
            ]
        )
        == 0
    )
    artifact = load_artifact(output)
    event = artifact.review_events[-1]
    assert event.action is VerifierAction.REASSIGN
    assert event.corrected_value == corrected
    assert event.claim_entity.model_id == "org/target"
    assert event.relation_to_target is RelationToTarget.EXACT_TARGET


def test_export_reviewed_card_artifact_markdown_and_html(tmp_path) -> None:
    record = _accepted_binding()
    source = _save(tmp_path, _artifact(record))
    card_path = tmp_path / "card.json"
    artifact_path = tmp_path / "artifact.json"
    markdown_path = tmp_path / "card.md"
    html_path = tmp_path / "card.html"

    commands = (
        ["export", str(source), "--kind", "card", "-o", str(card_path)],
        ["export", str(source), "-o", str(artifact_path)],
        ["export", str(source), "--format", "markdown", "-o", str(markdown_path)],
        ["export", str(source), "--format", "html", "-o", str(html_path)],
    )
    for command in commands:
        assert cli.main(command) == 0

    card = json.loads(card_path.read_text(encoding="utf-8"))
    assert card["identity"]["name"] == "Target Model"
    assert card["identity"]["summary"] == NOT_SPECIFIED
    assert load_artifact(artifact_path).card["identity"]["name"] == "Target Model"
    assert "# Model Card: org/target" in markdown_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in html_path.read_text(encoding="utf-8")


def test_export_refuses_artifact_without_frozen_source_bundle(tmp_path, capsys) -> None:
    record = _accepted_binding()
    card = blank_card()
    set_field_value(card, record.field_path, record.proposed_value)
    source = _save(
        tmp_path,
        CardArtifact(target=_target(), card=card, bindings=(record,)),
        "unverified.json",
    )
    output = tmp_path / "must-not-exist.json"
    assert cli.main(["export", str(source), "-o", str(output)]) == 2
    assert not output.exists()
    assert "frozen source bundle" in capsys.readouterr().err


def test_cli_rejects_target_identity_change_without_writing_output(
    tmp_path, capsys
) -> None:
    source_artifact = _artifact(_accepted_binding())
    target_binding = next(
        item
        for item in source_artifact.bindings
        if item.field_path == "identity.model_id"
    )
    source = _save(tmp_path, source_artifact)
    output = tmp_path / "invalid-target-change.json"
    assert (
        cli.main(
            [
                "reassign",
                str(source),
                target_binding.binding_id,
                "--reason",
                "human.invalid_target_change",
                "--value",
                "org/other",
                "-o",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()
    assert "identity.model_id" in capsys.readouterr().err


def test_module_entrypoint_help_is_parseable() -> None:
    parser = cli.build_parser()
    args = parser.parse_args(["inspect", "artifact.json", "--field", "identity.name"])
    assert args.handler is cli._cmd_inspect and args.format == "text"


def test_cli_formats_domain_failures_as_clean_exit_two(monkeypatch, capsys) -> None:
    def fail_cleanly(_args):
        raise ModelSourceError("offline target is absent from the local cache")

    monkeypatch.setattr(cli, "_cmd_collect", fail_cleanly)
    assert cli.main(["collect", f"org/target@{REVISION}"]) == 2
    error = capsys.readouterr().err
    assert error == "modelcards: error: offline target is absent from the local cache\n"


def test_cli_has_collect_and_compose_llm_subcommands():
    from model_cards.core.cli import build_parser

    parser = build_parser()
    args = parser.parse_args(["collect", "acme/x@abc", "--bundle-dir", "b"])
    assert args.handler.__name__ == "_cmd_collect" and args.bundle_dir == "b"
    args = parser.parse_args(["compose-llm", "acme/x@abc", "--bundle-dir", "b", "-o", "out.json",
                              "--allow-unpinned"])
    assert args.handler.__name__ == "_cmd_compose_llm" and args.allow_unpinned is True
