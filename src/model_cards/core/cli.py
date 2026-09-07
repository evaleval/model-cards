"""Command-line workflow for offline generation, review, inspection, and export."""

from __future__ import annotations

import argparse
from html import escape
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable, Sequence

from .bridge import ComposerBridgeError
from .public import PublicationError
from .spans import CompositionError
from .records import CardArtifact, RelationToTarget, VerifierAction
from .render import render_html, render_markdown, save_html, save_markdown
from .review import (
    accept_binding,
    effective_binding,
    export_reviewed_artifact,
    export_reviewed_card,
    load_artifact,
    review_history,
    reviewed_projection_paths,
    save_artifact,
    withhold_binding,
    reassign_binding,
)
from .schema import canonical_field_path, get_field_value
from .source import ModelSourceError


class CliError(ValueError):
    """A command could not be completed without weakening an invariant."""


def _json(value: Any, *, indent: int | None = None) -> str:
    return json.dumps(value, ensure_ascii=False, indent=indent, sort_keys=True)


def _atomic_write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return path


def _prepare_output(
    output: str | Path,
    *,
    input_path: str | Path | None = None,
    protected_input_dir: str | Path | None = None,
    force: bool = False,
) -> Path:
    destination = Path(output).expanduser()
    if input_path is not None:
        source = Path(input_path).expanduser()
        if source.resolve(strict=False) == destination.resolve(strict=False):
            raise CliError("output must be distinct from the input artifact")
    if protected_input_dir is not None:
        protected = Path(protected_input_dir).expanduser().resolve(strict=False)
        resolved_destination = destination.resolve(strict=False)
        if resolved_destination == protected or resolved_destination.is_relative_to(protected):
            raise CliError("output must be outside the frozen source-bundle directory")
    if destination.exists() and not force:
        raise CliError(f"output already exists (pass --force to replace it): {destination}")
    return destination


def _write_or_print(text: str, output: str | None, *, force: bool = False) -> None:
    if output is None:
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    destination = _prepare_output(output, force=force)
    _atomic_write_text(destination, text)
    print(destination)


def _binding_view(
    artifact: CardArtifact,
    binding_id: str,
    *,
    reviewed_projection_path: str | None = None,
) -> dict[str, Any]:
    binding = artifact.binding(binding_id)
    item = effective_binding(artifact, binding_id)
    return {
        "binding_id": binding.binding_id,
        "generation": {
            "field_path": binding.field_path,
            "value": binding.proposed_value,
            "claim_entity": binding.claim_entity.model_dump(mode="json"),
            "relation_to_target": binding.relation_to_target.value,
            "assignment_origin": binding.assignment_origin.value,
            "action": binding.verifier_action.value,
            "reason": binding.verifier_reason,
            "benchmark_scope": (
                binding.benchmark_scope.model_dump(mode="json")
                if binding.benchmark_scope is not None
                else None
            ),
        },
        "effective": {
            "field_path": item.field_path,
            "reviewed_projection_path": reviewed_projection_path,
            "value": item.value,
            "claim_entity": item.claim_entity.model_dump(mode="json"),
            "relation_to_target": item.relation_to_target.value,
            "assignment_origin": item.assignment_origin.value,
            "action": item.action.value,
            "reason": item.reason_code,
            "benchmark_scope": (
                item.benchmark_scope.model_dump(mode="json")
                if item.benchmark_scope is not None
                else None
            ),
        },
        "evidence": [item.model_dump(mode="json") for item in binding.evidence],
        "derivation_trace": (
            binding.derivation_trace.model_dump(mode="json")
            if binding.derivation_trace is not None
            else None
        ),
        "review_history": [
            event.model_dump(mode="json", exclude_none=True)
            for event in review_history(artifact, binding_id)
        ],
    }


def _field_matches(selector: str, effective_path: str) -> bool:
    requested_canonical = canonical_field_path(selector)
    if selector == requested_canonical:
        return canonical_field_path(effective_path) == requested_canonical
    return effective_path == selector


def _selected_card_value(card: dict[str, dict[str, Any]], selector: str) -> Any:
    try:
        return get_field_value(card, selector)
    except (IndexError, TypeError):
        return {"status": "not present at this index in the selected card projection"}


def _inspection_payload(
    artifact: CardArtifact,
    *,
    field: str | None,
    binding_id: str | None,
    reviewed: bool,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "artifact_id": artifact.artifact_id,
        "schema_version": artifact.schema_version,
        "target": artifact.target.model_dump(mode="json"),
        "view": "reviewed" if reviewed else "generation-time",
        "source_verification": (
            "embedded_frozen_bytes_hash_span_pointer_verified"
            if artifact.source_bundle is not None
            else "absent_unverified"
        ),
        "structural_context_verification": "recorded_not_recomputed_at_load",
    }
    if binding_id is not None:
        base.update({"selector": {"binding": binding_id}, "binding": _binding_view(artifact, binding_id)})
        return base

    card = export_reviewed_card(artifact) if reviewed else artifact.card
    if field is not None:
        canonical_field_path(field)  # validate even when there are no matching bindings
        matching = []
        projected_paths = reviewed_projection_paths(artifact) if reviewed else {}
        for binding in artifact.bindings:
            item = effective_binding(artifact, binding.binding_id)
            path = (
                projected_paths.get(binding.binding_id, item.field_path)
                if reviewed
                else binding.field_path
            )
            if _field_matches(field, path):
                matching.append(
                    _binding_view(
                        artifact,
                        binding.binding_id,
                        reviewed_projection_path=(path if reviewed else None),
                    )
                )
        base.update(
            {
                "selector": {"field": field},
                "field_value": _selected_card_value(card, field),
                "bindings": matching,
            }
        )
        return base

    counts = {action.value: 0 for action in VerifierAction}
    summaries = []
    for binding in artifact.bindings:
        item = effective_binding(artifact, binding.binding_id)
        counts[item.action.value] += 1
        summaries.append(
            {
                "binding_id": binding.binding_id,
                "field_path": item.field_path if reviewed else binding.field_path,
                "action": item.action.value if reviewed else binding.verifier_action.value,
                "relation_to_target": (
                    item.relation_to_target.value
                    if reviewed
                    else binding.relation_to_target.value
                ),
            }
        )
    base.update(
        {
            "binding_counts": counts,
            "review_event_count": len(artifact.review_events),
            "bindings": summaries,
        }
    )
    return base


def _inspection_text(payload: dict[str, Any]) -> str:
    target = payload["target"]
    lines = [
        f"Artifact: {payload['artifact_id']}",
        f"Target: {target['model_id']}@{target['resolved_revision']}",
        f"Schema: v{payload['schema_version']}",
        f"View: {payload['view']}",
        f"Source verification: {payload['source_verification']}",
        f"Structural context: {payload['structural_context_verification']}",
    ]
    selector = payload.get("selector")
    if selector:
        kind, value = next(iter(selector.items()))
        lines.append(f"Selected {kind}: {value}")
    if "field_value" in payload:
        lines.extend(("Field value:", _json(payload["field_value"], indent=2)))

    views: list[dict[str, Any]]
    if "binding" in payload:
        views = [payload["binding"]]
    else:
        views = payload.get("bindings", [])
    if "binding_counts" in payload:
        lines.append(f"Effective dispositions: {_json(payload['binding_counts'])}")
        lines.append(f"Review events: {payload['review_event_count']}")
    lines.append(f"Bindings: {len(views)}")
    for view in views:
        if "effective" not in view:
            lines.append(
                f"- {view['binding_id']} {view['field_path']} "
                f"[{view['action']}; {view['relation_to_target']}]"
            )
            continue
        effective = view["effective"]
        lines.extend(
            (
                f"- {view['binding_id']}",
                f"  field: {effective['field_path']}",
                f"  action: {effective['action']}",
                f"  relation: {effective['relation_to_target']}",
                f"  origin: {effective['assignment_origin']}",
                f"  entity: {_json(effective['claim_entity'])}",
                f"  value: {_json(effective['value'])}",
                f"  evidence spans: {len(view['evidence'])}",
                f"  review events: {len(view['review_history'])}",
            )
        )
        for evidence in view["evidence"]:
            anchor = evidence.get("structured_pointer") or (
                f"{evidence.get('start_offset')}:{evidence.get('end_offset')}"
            )
            lines.append(f"    - {evidence['source_uri']} ({anchor})")
    return "\n".join(lines) + "\n"


def _focused_markdown(payload: dict[str, Any]) -> str:
    selector = payload.get("selector", {})
    label = " / ".join(f"{key}: `{value}`" for key, value in selector.items())
    return (
        "# BindCard inspection\n\n"
        + (f"- Selector: {label}\n" if label else "")
        + f"- Artifact: `{payload['artifact_id']}`\n"
        + f"- View: `{payload['view']}`\n\n"
        + "```json\n"
        + _json(payload, indent=2)
        + "\n```\n"
    )


def _focused_html(payload: dict[str, Any]) -> str:
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>BindCard inspection</title>"
        "<style>body{font:16px/1.5 system-ui,sans-serif;max-width:1000px;"
        "margin:2rem auto;padding:0 1rem}pre{white-space:pre-wrap;overflow-wrap:anywhere;"
        "background:#f5f7fa;border:1px solid #d8dee8;padding:1rem}</style>"
        "</head><body><h1>BindCard inspection</h1><pre>"
        + escape(_json(payload, indent=2))
        + "</pre></body></html>\n"
    )


def _cmd_collect(args: argparse.Namespace) -> int:
    from .model_sources import collect_model_bundle
    from .route import bundle_dir_default

    bundle_dir = args.bundle_dir or bundle_dir_default()
    manifest = collect_model_bundle(args.target, bundle_dir, allow_network=True)
    print(json.dumps(manifest["channels"], indent=1))
    print(f"collected {manifest['slug']} -> {Path(bundle_dir) / manifest['slug']}")
    return 0


def _pinned_llm():
    """The pinned serving route (route.py, recorded with the run); env pins win."""
    from .route import build_llm, load_env

    load_env()
    return build_llm()


def _cmd_compose_llm(args: argparse.Namespace) -> int:
    from .compose_llm import compose_model_card_llm

    destination = _prepare_output(args.output, force=args.force)
    if args.usage_log:
        from auto_benchmarkcard.llm_handler import set_usage_log_path

        # The handler appends and fails soft, so a missing parent directory would drop the
        # whole spend ledger without an error. The ledger is the record of what a run cost.
        Path(args.usage_log).expanduser().parent.mkdir(parents=True, exist_ok=True)
        set_usage_log_path(args.usage_log)
    from .route import bundle_dir_default

    artifact = compose_model_card_llm(args.target, args.bundle_dir or bundle_dir_default(),
                                      _pinned_llm(), allow_unpinned=args.allow_unpinned)
    save_artifact(artifact, destination)
    accepted = sum(1 for b in artifact.bindings if b.verifier_action is VerifierAction.ACCEPT)
    withheld = sum(1 for b in artifact.bindings if b.verifier_action is VerifierAction.WITHHOLD)
    print(f"composed {artifact.artifact_id} for {artifact.target.canonical_target}: "
          f"{accepted} accepted, {withheld} withheld, coverage "
          f"{artifact.card['provenance_and_quality']['coverage_score']} -> {destination}")
    return 0


def _cmd_batch(args: argparse.Namespace) -> int:
    from .batch import read_targets, run_batch
    from .route import bundle_dir_default, load_env

    load_env()
    targets = read_targets(args.targets)
    if not targets:
        raise CliError(f"no targets in {args.targets}")
    manifest = run_batch(
        targets, phase=args.phase, bundle_dir=args.bundle_dir or bundle_dir_default(),
        out_dir=args.out_dir, concurrency=args.concurrency, resume=args.resume,
        per_card_cap=args.per_card_usd, run_cap=args.per_run_usd,
        per_target_timeout=args.per_target_timeout, collect_timeout=args.collect_timeout,
        export_html=not args.no_html)
    print(_json({k: manifest[k] for k in ("run_id", "phase", "targets", "status_counts",
                                          "totals", "stopped_early")}, indent=1))
    print(Path(args.out_dir) / "run-manifest.json")
    return 1 if manifest["stopped_early"] or manifest["status_counts"].get("failed") else 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    artifact = load_artifact(args.artifact)
    reviewed = not args.generation_time
    if args.format in {"markdown", "html"} and not (args.field or args.binding):
        text = (
            render_markdown(artifact, reviewed=reviewed)
            if args.format == "markdown"
            else render_html(artifact, reviewed=reviewed)
        )
    else:
        payload = _inspection_payload(
            artifact,
            field=args.field,
            binding_id=args.binding,
            reviewed=reviewed,
        )
        if args.format == "json":
            text = _json(payload, indent=2) + "\n"
        elif args.format == "markdown":
            text = _focused_markdown(payload)
        elif args.format == "html":
            text = _focused_html(payload)
        else:
            text = _inspection_text(payload)
    if args.output:
        destination = _prepare_output(
            args.output,
            input_path=args.artifact,
            force=args.force,
        )
        _atomic_write_text(destination, text)
        print(destination)
    else:
        sys.stdout.write(text)
    return 0


def _review_common(args: argparse.Namespace) -> tuple[CardArtifact, Path]:
    destination = _prepare_output(
        args.output,
        input_path=args.artifact,
        force=args.force,
    )
    return load_artifact(args.artifact), destination


def _finish_review(artifact: CardArtifact, destination: Path) -> int:
    save_artifact(artifact, destination)
    event = artifact.review_events[-1]
    print(
        f"appended {event.action.value} event {event.event_id} for "
        f"{event.binding_id} -> {destination}"
    )
    return 0


def _cmd_accept(args: argparse.Namespace) -> int:
    artifact, destination = _review_common(args)
    updated = accept_binding(
        artifact,
        args.binding_id,
        reason_code=args.reason,
        actor=args.actor,
        note=args.note,
    )
    return _finish_review(updated, destination)


def _cmd_withhold(args: argparse.Namespace) -> int:
    artifact, destination = _review_common(args)
    updated = withhold_binding(
        artifact,
        args.binding_id,
        reason_code=args.reason,
        actor=args.actor,
        note=args.note,
    )
    return _finish_review(updated, destination)


def _parsed_json(value: str, *, option: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise CliError(f"{option} must be valid JSON: {exc.msg}") from exc


def _cmd_reassign(args: argparse.Namespace) -> int:
    artifact, destination = _review_common(args)
    changes = any(
        value is not None
        for value in (
            args.field,
            args.value,
            args.value_json,
            args.entity_model_id,
            args.entity_revision,
            args.entity_label,
            args.relation,
            args.benchmark_scope_json,
        )
    )
    if not changes:
        raise CliError("reassign requires at least one corrected assignment option")
    if args.entity_revision and not args.entity_model_id:
        raise CliError("--entity-revision requires --entity-model-id")

    kwargs: dict[str, Any] = {
        "reason_code": args.reason,
        "actor": args.actor,
        "note": args.note,
    }
    if args.field is not None:
        kwargs["field_path"] = args.field
    if args.value is not None:
        kwargs["corrected_value"] = args.value
    elif args.value_json is not None:
        kwargs["corrected_value"] = _parsed_json(args.value_json, option="--value-json")
    if any((args.entity_model_id, args.entity_revision, args.entity_label)):
        kwargs["claim_entity"] = {
            key: value
            for key, value in {
                "model_id": args.entity_model_id,
                "revision": args.entity_revision,
                "label": args.entity_label,
            }.items()
            if value is not None
        }
    if args.relation is not None:
        kwargs["relation_to_target"] = args.relation
    if args.benchmark_scope_json is not None:
        scope = _parsed_json(
            args.benchmark_scope_json,
            option="--benchmark-scope-json",
        )
        if not isinstance(scope, dict):
            raise CliError("--benchmark-scope-json must contain a JSON object")
        kwargs["benchmark_scope"] = scope

    updated = reassign_binding(artifact, args.binding_id, **kwargs)
    return _finish_review(updated, destination)


def _cmd_export(args: argparse.Namespace) -> int:
    destination = _prepare_output(
        args.output,
        input_path=args.artifact,
        force=args.force,
    )
    artifact = load_artifact(args.artifact)
    if artifact.source_bundle is None:
        raise CliError(
            "reviewed export requires an embedded frozen source bundle; "
            "this artifact is unverified"
        )
    if args.kind == "public":
        import hashlib

        from .public import export_public
        from .public_markdown import render_public_markdown

        projection = export_public(artifact, reviewed=not args.generation_time)
        payload = _json(projection, indent=2) + "\n"
        if args.format == "markdown":
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            _atomic_write_text(destination, render_public_markdown(
                projection, json_filename=destination.with_suffix(".json").name,
                json_sha256=digest))
        elif args.format == "json":
            _atomic_write_text(destination, payload)
        else:
            raise CliError("--kind public supports --format json or markdown")
        print(destination)
        return 0
    if args.format == "json":
        if args.kind == "artifact":
            save_artifact(export_reviewed_artifact(artifact), destination)
        else:
            _atomic_write_text(
                destination,
                _json(export_reviewed_card(artifact), indent=2) + "\n",
            )
    else:
        if args.kind == "card":
            raise CliError("--kind card is only supported with --format json")
        if args.format == "markdown":
            save_markdown(artifact, destination, reviewed=True)
        else:
            save_html(artifact, destination, reviewed=True)
    print(destination)
    return 0


def _add_output_guard(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-o", "--out", "--output", dest="output", required=True,
                        help="new output path")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing output path (never the input artifact)",
    )


def _add_review_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("artifact", help="input CardArtifact JSON")
    parser.add_argument("binding_id", help="binding primary key")
    parser.add_argument("--reason", required=True, help="machine-readable reason code")
    parser.add_argument("--actor", default="reviewer", help="reviewer identifier")
    parser.add_argument("--note", help="optional human-readable note")
    _add_output_guard(parser)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modelcards",
        description="Generate, inspect and review evidence-bound Model Cards.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser("collect", help="collect a model's source bundle (network)")
    collect.add_argument("target", help="owner/model@revision")
    collect.add_argument("--bundle-dir", default=None, help="bundle root directory")
    collect.set_defaults(handler=_cmd_collect)

    compose = subparsers.add_parser(
        "compose", aliases=["compose-llm"],
        help="compose a card from a collected bundle on the pinned route")
    compose.add_argument("target", help="owner/model@revision")
    compose.add_argument("--bundle-dir", default=None, help="bundle root directory")
    compose.add_argument("--llm-usage-log", "--usage-log", dest="usage_log",
                         help="append per-call LLM usage records to this jsonl")
    compose.add_argument("--allow-unpinned", action="store_true",
                         help="skip the composer revision pin check (development only)")
    _add_output_guard(compose)
    compose.set_defaults(handler=_cmd_compose_llm)

    batch = subparsers.add_parser("batch", help="collect and compose a list of targets")
    batch.add_argument("targets", help="file with one owner/model@revision per line")
    batch.add_argument("--phase", choices=("collect", "compose", "both"), default="both")
    batch.add_argument("--bundle-dir", default=None, help="bundle root directory")
    batch.add_argument("--out-dir", "--out", dest="out_dir", required=True,
                       help="run directory for cards, usage logs and the run manifest")
    batch.add_argument("--concurrency", type=int, default=4, help="concurrent targets (1-6)")
    batch.add_argument("--resume", action="store_true",
                       help="skip targets whose output already exists")
    batch.add_argument("--per-card-usd", type=float, default=2.00, help="per-card spend tripwire")
    batch.add_argument("--per-run-usd", type=float, default=40.00, help="per-run spend tripwire")
    batch.add_argument("--no-html", action="store_true", help="skip the HTML inspector export")
    batch.add_argument("--per-target-timeout", type=int, default=900,
                       help="seconds before one target's composition is killed")
    batch.add_argument("--collect-timeout", type=int, default=900,
                       help="seconds before one target's collection is killed")
    batch.set_defaults(handler=_cmd_batch)

    inspect = subparsers.add_parser("inspect", help="inspect cards, fields, or bindings")
    inspect.add_argument("artifact", help="input CardArtifact JSON")
    selector = inspect.add_mutually_exclusive_group()
    selector.add_argument("--field", help="canonical or indexed schema-v5 field path")
    selector.add_argument("--binding", help="binding primary key")
    inspect.add_argument(
        "--format",
        choices=("text", "json", "markdown", "html"),
        default="text",
    )
    inspect.add_argument(
        "--generation-time",
        action="store_true",
        help="show the original projection instead of effective review dispositions",
    )
    inspect.add_argument("-o", "--out", "--output", dest="output",
                         help="write the report instead of stdout")
    inspect.add_argument("--force", action="store_true", help="replace an existing report")
    inspect.set_defaults(handler=_cmd_inspect)

    accept = subparsers.add_parser("accept", help="append an accept review event")
    _add_review_common(accept)
    accept.set_defaults(handler=_cmd_accept)

    withhold = subparsers.add_parser("withhold", help="append a withhold review event")
    _add_review_common(withhold)
    withhold.set_defaults(handler=_cmd_withhold)

    reassign = subparsers.add_parser("reassign", help="append a corrected assignment")
    _add_review_common(reassign)
    reassign.add_argument("--field", help="corrected schema-v5 field path")
    value = reassign.add_mutually_exclusive_group()
    value.add_argument("--value", help="corrected literal string value")
    value.add_argument("--value-json", help="corrected JSON value")
    reassign.add_argument("--entity-model-id", help="corrected claim owner/model")
    reassign.add_argument("--entity-revision", help="corrected claim revision")
    reassign.add_argument("--entity-label", help="exact source label for the claim entity")
    reassign.add_argument(
        "--relation",
        choices=tuple(value.value for value in RelationToTarget),
        help="corrected relation to the exact target",
    )
    reassign.add_argument(
        "--benchmark-scope-json",
        help="corrected BenchmarkScope JSON object",
    )
    reassign.set_defaults(handler=_cmd_reassign)

    export = subparsers.add_parser("export", help="export the reviewed projection")
    export.add_argument("artifact", help="input CardArtifact JSON")
    export.add_argument(
        "--kind",
        choices=("artifact", "card", "public"),
        default="artifact",
        help="full auditable artifact, bare internal card, or the published "
             "seven-section projection (validated, source-clean)",
    )
    export.add_argument(
        "--generation-time",
        action="store_true",
        help="export the original projection instead of effective review dispositions",
    )
    export.add_argument(
        "--format",
        choices=("json", "markdown", "html"),
        default="json",
    )
    _add_output_guard(export)
    export.set_defaults(handler=_cmd_export)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except (
        CliError,
        ComposerBridgeError,
        CompositionError,
        PublicationError,
        KeyError,
        ModelSourceError,
        OSError,
        ValueError,
    ) as exc:
        print(f"modelcards: error: {exc}", file=sys.stderr)
        return 2


__all__ = ["build_parser", "main"]
