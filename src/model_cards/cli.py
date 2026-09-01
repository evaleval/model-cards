"""Offline command-line interface for building and inspecting model cards."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from .artifact import project_card
from .bindings import build_artifact
from .models import RelationToTarget, ReviewAction
from .render import save_html, save_json
from .review import append_review, load_artifact, save_artifact
from .schema import canonical_field_path, get_field, validate_field_path


def _new_path(value: str, *, inputs: tuple[Path, ...] = ()) -> Path:
    path = Path(value)
    if any(path.resolve() == item.resolve() for item in inputs):
        raise ValueError("output must differ from its input")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    return path


def _read_object(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input root must be a JSON object")
    return value


def _cmd_build(args: argparse.Namespace) -> int:
    source = Path(args.specification)
    artifact = build_artifact(_read_object(source))
    json_path = _new_path(args.json)
    html_path = _new_path(args.html)
    if json_path.resolve() == html_path.resolve():
        raise ValueError("JSON and HTML outputs must differ")
    save_json(artifact, json_path)
    save_html(artifact, html_path)
    print(f"wrote {json_path}")
    print(f"wrote {html_path}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    source = Path(args.artifact)
    destination = _new_path(args.html, inputs=(source,))
    save_html(load_artifact(source), destination)
    print(f"wrote {destination}")
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    artifact = load_artifact(args.artifact)
    if args.field:
        field_path = validate_field_path(args.field)
        base = canonical_field_path(field_path)
        payload = {
            "target": artifact.target.to_dict(),
            "field_path": field_path,
            "value": get_field(project_card(artifact), field_path),
            "bindings": [
                item.to_dict()
                for item in artifact.effective_bindings()
                if canonical_field_path(item.field_path) == base
            ],
        }
    else:
        payload = {
            "target": artifact.target.to_dict(),
            "schema_version": artifact.schema_version,
            "binding_count": len(artifact.bindings),
            "review_count": len(artifact.reviews),
            "dispositions": {
                disposition: sum(
                    item.disposition.value == disposition
                    for item in artifact.effective_bindings()
                )
                for disposition in ("accepted", "withheld", "rejected")
            },
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    source = Path(args.artifact)
    destination = _new_path(args.output, inputs=(source,))
    artifact = load_artifact(source)
    corrected_value = None
    if args.action == ReviewAction.REASSIGN.value:
        if args.field is None or args.relation is None or args.value_json is None:
            raise ValueError("reassign requires --field, --relation, and --value-json")
        corrected_value = json.loads(args.value_json)
    elif any(item is not None for item in (args.field, args.relation, args.value_json)):
        raise ValueError("field, relation, and value are only valid with reassign")
    reviewed = append_review(
        artifact,
        binding_id=args.binding_id,
        action=args.action,
        reason=args.reason,
        field_path=args.field,
        relation=args.relation,
        corrected_value=corrected_value,
    )
    save_artifact(reviewed, destination)
    print(f"wrote {destination}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="model-cards",
        description="Build and inspect evidence-bound Model Cards offline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build JSON and static HTML from a specification")
    build.add_argument("specification")
    build.add_argument("--json", required=True, help="new artifact output path")
    build.add_argument("--html", required=True, help="new static HTML output path")
    build.set_defaults(handler=_cmd_build)

    render = subparsers.add_parser("render", help="render an artifact as static HTML")
    render.add_argument("artifact")
    render.add_argument("--html", required=True, help="new static HTML output path")
    render.set_defaults(handler=_cmd_render)

    inspect = subparsers.add_parser("inspect", help="inspect an artifact or one field")
    inspect.add_argument("artifact")
    inspect.add_argument("--field")
    inspect.set_defaults(handler=_cmd_inspect)

    review = subparsers.add_parser("review", help="append one review event to a new artifact")
    review.add_argument("artifact")
    review.add_argument("binding_id")
    review.add_argument("--action", required=True, choices=[item.value for item in ReviewAction])
    review.add_argument("--reason", required=True)
    review.add_argument("--field")
    review.add_argument("--relation", choices=[item.value for item in RelationToTarget])
    review.add_argument("--value-json")
    review.add_argument("--output", required=True)
    review.set_defaults(handler=_cmd_review)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except (KeyError, ValueError, TypeError, IndexError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
