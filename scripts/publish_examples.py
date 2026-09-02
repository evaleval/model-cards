#!/usr/bin/env python3
"""Validate generated public cards and publish their exact bytes as examples."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import tempfile
from typing import Any, Sequence

from model_cards.artifact import CardArtifact
from model_cards.privacy import audit_public_tree
from model_cards.public_export import (
    assert_public_projection,
    verify_publication_snapshot,
)
from model_cards.public_markdown import render_public_markdown
from model_cards.publication_contract import FIELD_PATHS, NOT_APPLICABLE, NOT_SPECIFIED
from model_cards.publication_schema import get_field, validate_publication_card
from model_cards.source_state import load_source_state


MINIMUM_SPECIFIED_FIELDS = 15


class ExamplePublishError(ValueError):
    """A source card or requested publication path failed closed checks."""


def _reject_constant(value: str) -> None:
    raise ExamplePublishError(f"non-finite JSON number is not permitted: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ExamplePublishError("source card contains duplicate JSON keys")
        value[key] = item
    return value


def _load_card(
    path: Path,
    *,
    source_bundle: str | os.PathLike[str],
    official_bundle: str | os.PathLike[str] | None,
) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise ExamplePublishError("source card must be a real file")
    raw = path.read_bytes()
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExamplePublishError("source card must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ExamplePublishError("source card root must be a JSON object")
    artifact_path = path.with_name("card-artifact.json")
    if artifact_path.is_symlink() or not artifact_path.is_file():
        raise ExamplePublishError(
            "source card requires its replay-bound card-artifact.json sibling"
        )
    try:
        artifact_value = json.loads(
            artifact_path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
        if not isinstance(artifact_value, dict):
            raise ExamplePublishError("card artifact root must be a JSON object")
        artifact = CardArtifact.from_dict(artifact_value)
        source_state = load_source_state(source_bundle, official_bundle)
        replayed = verify_publication_snapshot(artifact, source_state)
    except ExamplePublishError:
        raise
    except Exception as exc:
        raise ExamplePublishError(
            "source card failed replay-bound publication verification"
        ) from exc
    if value != replayed:
        raise ExamplePublishError(
            "source card differs from its replay-bound publication snapshot"
        )
    validate_publication_card(value)
    assert_public_projection(value)
    for field_path in ("identity.model_id", "identity.version"):
        if get_field(value, field_path, NOT_SPECIFIED) in {
            NOT_SPECIFIED,
            NOT_APPLICABLE,
        }:
            raise ExamplePublishError(
                "repository examples require an exact model ID and version"
            )
    specified = sum(
        get_field(value, field_path, NOT_SPECIFIED)
        not in (NOT_SPECIFIED, NOT_APPLICABLE)
        for field_path in FIELD_PATHS
    )
    if specified < MINIMUM_SPECIFIED_FIELDS:
        raise ExamplePublishError(
            "repository examples require at least "
            f"{MINIMUM_SPECIFIED_FIELDS} specified agreed fields"
        )
    return value, raw


def _destination(repo_root: Path, value: str) -> tuple[str, Path]:
    if not value or "\\" in value:
        raise ExamplePublishError("destination must be cards/NAME.json")
    relative = PurePosixPath(value)
    if (
        relative.is_absolute()
        or len(relative.parts) != 2
        or relative.parts[0] != "cards"
        or relative.parts[1] in {"", ".", ".."}
        or not relative.parts[1].endswith(".json")
    ):
        raise ExamplePublishError("destination must be cards/NAME.json")
    normalized = relative.as_posix()
    return normalized, repo_root.joinpath(*relative.parts)


def _parse_mapping(repo_root: Path, value: str) -> tuple[Path, str, Path]:
    if "=" not in value:
        raise ExamplePublishError("mapping must be SOURCE=cards/NAME.json")
    source_value, destination_value = value.split("=", 1)
    if not source_value:
        raise ExamplePublishError("mapping source cannot be empty")
    relative, destination = _destination(repo_root, destination_value)
    source = Path(source_value)
    if source.resolve() == destination.resolve():
        raise ExamplePublishError("source and destination must differ")
    return source, relative, destination


def _markdown_bytes(
    card: dict[str, Any], *, json_filename: str, json_raw: bytes
) -> bytes:
    return render_public_markdown(
        card,
        json_filename=json_filename,
        json_sha256=hashlib.sha256(json_raw).hexdigest(),
    ).encode("utf-8")


def _audit_exact_pair(json_raw: bytes, markdown_raw: bytes, filename: str) -> None:
    with tempfile.TemporaryDirectory(prefix="model-card-example-audit-") as temporary:
        root = Path(temporary)
        json_path = root / "cards" / filename
        markdown_path = json_path.with_suffix(".md")
        json_path.parent.mkdir()
        json_path.write_bytes(json_raw)
        markdown_path.write_bytes(markdown_raw)
        report = audit_public_tree(
            root,
            (f"cards/{filename}", f"cards/{markdown_path.name}"),
        )
    if not report.passed:
        codes = ",".join(sorted({item.code.value for item in report.findings}))
        raise ExamplePublishError(f"source card pair failed privacy audit: {codes}")


def _check_destination(destination: Path, raw: bytes, *, force: bool) -> bool:
    """Return whether ``destination`` needs an atomic replacement."""

    if destination.parent.is_symlink() or destination.is_symlink():
        raise ExamplePublishError("destination cannot traverse a symlink")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file():
            raise ExamplePublishError("destination must be a regular file")
        if destination.read_bytes() == raw:
            return False
        if not force:
            raise ExamplePublishError(f"destination exists: {destination}")
    return True


def _stage_atomic(destination: Path, raw: bytes) -> str:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
        raise
    return temporary_name


def _atomic_write_batch(
    writes: Sequence[tuple[Path, bytes]], *, force: bool
) -> None:
    """Preflight and stage the full JSON/Markdown batch before replacement."""

    pending = [
        (destination, raw)
        for destination, raw in writes
        if _check_destination(destination, raw, force=force)
    ]
    staged: list[tuple[str, Path, bytes]] = []
    try:
        for destination, raw in pending:
            staged.append((_stage_atomic(destination, raw), destination, raw))
        for temporary_name, destination, _raw in staged:
            os.replace(temporary_name, destination)
        for _temporary_name, destination, raw in staged:
            if destination.read_bytes() != raw:
                raise ExamplePublishError(
                    "published example differs from generated source bytes"
                )
    finally:
        for temporary_name, _destination, _raw in staged:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


def publish_examples(
    mappings: Sequence[str],
    *,
    source_bundles: Sequence[str | os.PathLike[str]],
    official_bundles: Sequence[str | os.PathLike[str] | None] | None = None,
    repo_root: str | os.PathLike[str] = ".",
    force: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Validate every mapping, then publish exact JSON plus deterministic Markdown."""

    root = Path(repo_root)
    if root.is_symlink() or not root.is_dir():
        raise ExamplePublishError("repo root must be a real directory")
    root = root.resolve()
    if not mappings:
        raise ExamplePublishError("at least one source-to-destination mapping is required")
    if isinstance(source_bundles, (str, bytes, os.PathLike)):
        raise ExamplePublishError("source_bundles must align one-for-one with mappings")
    if len(source_bundles) != len(mappings):
        raise ExamplePublishError("source_bundles must align one-for-one with mappings")
    if official_bundles is None:
        official_values: tuple[str | os.PathLike[str] | None, ...] = tuple(
            None for _ in mappings
        )
    else:
        if isinstance(official_bundles, (str, bytes, os.PathLike)):
            raise ExamplePublishError(
                "official_bundles must align one-for-one with mappings"
            )
        official_values = tuple(official_bundles)
        if len(official_values) != len(mappings):
            raise ExamplePublishError(
                "official_bundles must align one-for-one with mappings"
            )

    prepared: list[
        tuple[str, Path, bytes, str, Path, bytes, dict[str, Any]]
    ] = []
    destinations: set[str] = set()
    for mapping, source_bundle, official_bundle in zip(
        mappings, source_bundles, official_values
    ):
        _source, relative, destination = _parse_mapping(root, mapping)
        if relative in destinations:
            raise ExamplePublishError("each destination may appear only once")
        destinations.add(relative)
        card, json_raw = _load_card(
            _source,
            source_bundle=source_bundle,
            official_bundle=official_bundle,
        )
        markdown_relative = PurePosixPath(relative).with_suffix(".md").as_posix()
        markdown_destination = destination.with_suffix(".md")
        markdown_raw = _markdown_bytes(
            card,
            json_filename=Path(relative).name,
            json_raw=json_raw,
        )
        _audit_exact_pair(json_raw, markdown_raw, Path(relative).name)
        prepared.append(
            (
                relative,
                destination,
                json_raw,
                markdown_relative,
                markdown_destination,
                markdown_raw,
                card,
            )
        )

    writes = tuple(
        item
        for (
            _relative,
            destination,
            json_raw,
            _markdown_relative,
            markdown_destination,
            markdown_raw,
            _card,
        ) in prepared
        for item in (
            (destination, json_raw),
            (markdown_destination, markdown_raw),
        )
    )
    _atomic_write_batch(writes, force=force)

    records: list[dict[str, Any]] = []
    for (
        relative,
        _destination,
        json_raw,
        markdown_relative,
        _markdown_destination,
        markdown_raw,
        card,
    ) in prepared:
        records.append(
            {
                "destination": relative,
                "markdown_destination": markdown_relative,
                "model_id": card["identity"].get("model_id", "Not specified"),
                "version": card["identity"].get("version", "Not specified"),
                "sha256": hashlib.sha256(json_raw).hexdigest(),
                "markdown_sha256": hashlib.sha256(markdown_raw).hexdigest(),
            }
        )
    return tuple(records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate generated public cards against the agreed publication schema "
            "and privacy boundary, then publish exact JSON and deterministic Markdown "
            "companions into cards/."
        )
    )
    parser.add_argument(
        "mappings", nargs="+", metavar="SOURCE=cards/NAME.json"
    )
    parser.add_argument(
        "--source-bundle",
        action="append",
        required=True,
        help="frozen Hugging Face source bundle; repeat in mapping order",
    )
    parser.add_argument(
        "--official-bundle",
        action="append",
        help="optional official bundle; when used, repeat in mapping order",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = publish_examples(
            args.mappings,
            source_bundles=args.source_bundle,
            official_bundles=args.official_bundle,
            repo_root=args.repo_root,
            force=args.force,
        )
    except (ExamplePublishError, OSError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {"published": list(records)},
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
