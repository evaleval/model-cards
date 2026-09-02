#!/usr/bin/env python3
"""Regenerate repository examples from verified frozen source bundles only.

The command discovers every ``target*/source-bundle`` below a pilot root,
runs and immediately replays the provider-free pipeline in a private batch
directory, preflights the complete public-card set, and only then delegates
the JSON/Markdown publication transaction to ``publish_examples.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence

from model_cards.pipeline import run_offline_pipeline, verify_pipeline_result
from model_cards.public_export import assert_public_projection
from model_cards.publication_contract import (
    FIELD_PATHS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
)
from model_cards.publication_schema import get_field, validate_publication_card
from model_cards.source_bundle import replay_source_bundle


DEFAULT_MIN_SPECIFIED_FIELDS = 15
_MAX_FILENAME_STEM = 96
_SAFE_FILENAME_CHARACTER = re.compile(r"[^A-Za-z0-9._-]+")


class FrozenExampleRegenerationError(ValueError):
    """Frozen inputs or generated examples failed a closed preflight check."""


def _reject_constant(value: str) -> None:
    raise FrozenExampleRegenerationError(
        f"non-finite JSON number is not permitted: {value}"
    )


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise FrozenExampleRegenerationError(
                "generated public card contains duplicate JSON keys"
            )
        value[key] = item
    return value


def _real_directory(path: str | os.PathLike[str], label: str) -> Path:
    value = Path(path)
    if value.is_symlink() or not value.is_dir():
        raise FrozenExampleRegenerationError(f"{label} must be a real directory")
    return value.resolve()


def _has_symlink_between(root: Path, descendant: Path) -> bool:
    try:
        relative = descendant.relative_to(root)
    except ValueError:
        return True
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            return True
    return False


def discover_frozen_targets(
    pilot_root: str | os.PathLike[str],
) -> tuple[tuple[Path, str, str], ...]:
    """Discover and integrity-check all exact-target source bundles."""

    root = _real_directory(pilot_root, "pilot root")
    manifests: list[Path] = []
    direct = root / "manifest.json"
    if root.name == "source-bundle" and direct.is_file():
        manifests.append(direct)
    manifests.extend(
        path
        for path in root.rglob("manifest.json")
        if path.parent.name == "source-bundle" and path != direct
    )
    manifests = sorted(set(manifests), key=lambda item: item.as_posix())
    if not manifests:
        raise FrozenExampleRegenerationError(
            "pilot root contains no target source-bundle manifests"
        )

    targets: list[tuple[Path, str, str]] = []
    model_ids: set[str] = set()
    exact_targets: set[tuple[str, str]] = set()
    for manifest in manifests:
        bundle = manifest.parent
        if _has_symlink_between(root, bundle):
            raise FrozenExampleRegenerationError(
                "pilot source-bundle paths cannot traverse symbolic links"
            )
        replayed = replay_source_bundle(bundle)
        model_id = replayed.manifest.target.model_id
        revision = replayed.manifest.target.revision
        if model_id in model_ids:
            raise FrozenExampleRegenerationError(
                "pilot source bundles must have unique model IDs"
            )
        if (model_id, revision) in exact_targets:
            raise FrozenExampleRegenerationError(
                "pilot source bundles contain a duplicate exact target"
            )
        model_ids.add(model_id)
        exact_targets.add((model_id, revision))
        targets.append((bundle, model_id, revision))
    return tuple(sorted(targets, key=lambda item: (item[1], item[2])))


def _safe_basename(model_id: str) -> str:
    basename = model_id.rsplit("/", 1)[-1]
    stem = _SAFE_FILENAME_CHARACTER.sub("-", basename).strip("._-").lower()
    if not stem:
        stem = "model"
    if len(stem) > _MAX_FILENAME_STEM:
        digest = hashlib.sha256(model_id.encode("utf-8")).hexdigest()[:12]
        stem = f"{stem[: _MAX_FILENAME_STEM - 13].rstrip('._-')}-{digest}"
    return stem


def destination_filename_map(model_ids: Iterable[str]) -> dict[str, str]:
    """Map model basenames to safe, case-insensitively unique JSON names."""

    values = tuple(model_ids)
    if not values or any(not isinstance(item, str) or "/" not in item for item in values):
        raise FrozenExampleRegenerationError(
            "destination mapping requires non-empty namespaced model IDs"
        )
    if len(values) != len(set(values)):
        raise FrozenExampleRegenerationError(
            "destination mapping requires unique model IDs"
        )

    stems = {model_id: _safe_basename(model_id) for model_id in values}
    groups: dict[str, list[str]] = {}
    for model_id, stem in stems.items():
        groups.setdefault(stem.casefold(), []).append(model_id)

    result: dict[str, str] = {}
    for model_id in sorted(values):
        stem = stems[model_id]
        if len(groups[stem.casefold()]) > 1:
            digest = hashlib.sha256(model_id.encode("utf-8")).hexdigest()[:12]
            stem = f"{stem[: _MAX_FILENAME_STEM - 13].rstrip('._-')}-{digest}"
        result[model_id] = f"{stem}.json"
    if len({item.casefold() for item in result.values()}) != len(result):
        raise FrozenExampleRegenerationError(
            "could not derive unique repository card filenames"
        )
    return result


def _prepare_run_root(path: str | os.PathLike[str], repo_root: Path) -> Path:
    value = Path(path)
    if value.is_symlink():
        raise FrozenExampleRegenerationError(
            "run output cannot be a symbolic link"
        )
    resolved = value.resolve()
    cards = (repo_root / "cards").resolve()
    if resolved == repo_root or resolved == cards or cards in resolved.parents:
        raise FrozenExampleRegenerationError(
            "run output must be a private batch directory, not the repository or cards"
        )
    value.mkdir(parents=True, exist_ok=True)
    if value.is_symlink() or not value.is_dir():
        raise FrozenExampleRegenerationError(
            "run output must be a real directory"
        )
    return resolved


def _strict_public_card(path: Path) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise FrozenExampleRegenerationError(
            "provider-free pipeline did not produce a safe public card"
        )
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrozenExampleRegenerationError(
            "generated public card is not strict UTF-8 JSON"
        ) from exc
    if not isinstance(value, dict):
        raise FrozenExampleRegenerationError(
            "generated public card root must be an object"
        )
    validate_publication_card(value)
    assert_public_projection(value)
    return value, raw


def specified_field_count(card: Mapping[str, Any]) -> int:
    """Count non-placeholder values over the agreed 33-field contract."""

    validate_publication_card(card)
    return sum(
        get_field(card, field_path, NOT_SPECIFIED)
        not in (NOT_SPECIFIED, NOT_APPLICABLE)
        for field_path in FIELD_PATHS
    )


def _load_publish_module() -> ModuleType:
    path = Path(__file__).with_name("publish_examples.py")
    specification = importlib.util.spec_from_file_location(
        "_model_cards_publish_examples", path
    )
    if specification is None or specification.loader is None:
        raise FrozenExampleRegenerationError(
            "could not load the repository example publisher"
        )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def regenerate_frozen_examples(
    *,
    pilot_root: str | os.PathLike[str],
    run_output: str | os.PathLike[str],
    repo_root: str | os.PathLike[str] = ".",
    min_specified_fields: int = DEFAULT_MIN_SPECIFIED_FIELDS,
    force: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Run, replay, preflight, and publish a complete frozen example batch."""

    if (
        isinstance(min_specified_fields, bool)
        or not isinstance(min_specified_fields, int)
        or not 0 <= min_specified_fields <= len(FIELD_PATHS)
    ):
        raise FrozenExampleRegenerationError(
            f"minimum specified fields must be between 0 and {len(FIELD_PATHS)}"
        )
    repository = _real_directory(repo_root, "repository root")
    targets = discover_frozen_targets(pilot_root)
    filenames = destination_filename_map(item[1] for item in targets)
    private_root = _prepare_run_root(run_output, repository)
    target_runs = private_root / "targets"
    target_runs.mkdir(exist_ok=True)
    if target_runs.is_symlink() or not target_runs.is_dir():
        raise FrozenExampleRegenerationError(
            "private target-run directory must be a real directory"
        )

    prepared: list[tuple[str, str, str]] = []
    for bundle, model_id, revision in targets:
        filename_stem = filenames[model_id][:-5]
        exact_digest = hashlib.sha256(
            f"{model_id}@{revision}".encode("utf-8")
        ).hexdigest()[:20]
        run_directory = target_runs / f"{filename_stem}-{exact_digest}"
        if run_directory.is_symlink():
            raise FrozenExampleRegenerationError(
                "target run directory cannot be a symbolic link"
            )

        result = run_offline_pipeline(bundle, run_directory)
        replayed = verify_pipeline_result(result, bundle, run_directory)
        if replayed.to_dict() != result.to_dict():  # defensive; helper also checks
            raise FrozenExampleRegenerationError(
                "provider-free pipeline replay diverged"
            )
        usage_path = run_directory / "usage.jsonl"
        if (
            usage_path.is_symlink()
            or not usage_path.is_file()
            or usage_path.read_bytes()
        ):
            raise FrozenExampleRegenerationError(
                "provider-free run recorded unexpected provider usage"
            )
        if (
            result.target.model_id != model_id
            or result.target.revision != revision
        ):
            raise FrozenExampleRegenerationError(
                "pipeline result target differs from its verified source bundle"
            )

        public_path = run_directory / "public-card.json"
        card, raw = _strict_public_card(public_path)
        identity = card.get("identity", {})
        if (
            identity.get("model_id") != model_id
            or identity.get("version") != revision
        ):
            raise FrozenExampleRegenerationError(
                "public card identity differs from its exact source target"
            )
        if hashlib.sha256(raw).hexdigest() != result.public_card_sha256:
            raise FrozenExampleRegenerationError(
                "public card bytes differ from the pipeline result digest"
            )
        count = specified_field_count(card)
        if count < min_specified_fields:
            raise FrozenExampleRegenerationError(
                "generated public card does not meet the specified-field floor "
                f"({count} < {min_specified_fields})"
            )
        source_text = os.fspath(public_path)
        if "=" in source_text:
            raise FrozenExampleRegenerationError(
                "run output path cannot contain '=' when publishing examples"
            )
        prepared.append(
            (source_text, f"cards/{filenames[model_id]}", os.fspath(bundle))
        )

    # ``publish_examples`` performs one more schema/privacy/Markdown preflight
    # over the full batch before it writes any destination.
    publisher = _load_publish_module()
    mappings = tuple(
        f"{source}={destination}" for source, destination, _bundle in prepared
    )
    records = publisher.publish_examples(
        mappings,
        source_bundles=tuple(bundle for _source, _destination, bundle in prepared),
        repo_root=repository,
        force=force,
    )
    if len(records) != len(targets):
        raise FrozenExampleRegenerationError(
            "example publisher returned an incomplete batch"
        )
    return tuple(records)


def _minimum_field_count(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if not 0 <= result <= len(FIELD_PATHS):
        raise argparse.ArgumentTypeError(
            f"must be between 0 and {len(FIELD_PATHS)}"
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate JSON and Markdown repository cards from verified frozen "
            "source bundles without network or provider calls."
        )
    )
    parser.add_argument("--pilot-root", required=True)
    parser.add_argument("--run-output", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--min-specified-fields",
        type=_minimum_field_count,
        default=DEFAULT_MIN_SPECIFIED_FIELDS,
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace differing existing JSON/Markdown examples after preflight",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = regenerate_frozen_examples(
            pilot_root=args.pilot_root,
            run_output=args.run_output,
            repo_root=args.repo_root,
            min_specified_fields=args.min_specified_fields,
            force=args.force,
        )
    except (
        FrozenExampleRegenerationError,
        OSError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "network_calls": 0,
                "provider_calls": 0,
                "published": list(records),
                "replay_verified": True,
            },
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
