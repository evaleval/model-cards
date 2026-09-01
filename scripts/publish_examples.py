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

from model_cards.privacy import audit_public_tree
from model_cards.public_export import assert_public_projection
from model_cards.schema import validate_public_card


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


def _load_card(path: Path) -> tuple[dict[str, Any], bytes]:
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
    validate_public_card(value)
    assert_public_projection(value)
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


def _audit_exact_card(raw: bytes, filename: str) -> None:
    with tempfile.TemporaryDirectory(prefix="model-card-example-audit-") as temporary:
        root = Path(temporary)
        staged = root / "cards" / filename
        staged.parent.mkdir()
        staged.write_bytes(raw)
        report = audit_public_tree(root, (f"cards/{filename}",))
    if not report.passed:
        codes = ",".join(sorted({item.code.value for item in report.findings}))
        raise ExamplePublishError(f"source card failed privacy audit: {codes}")


def _atomic_write(destination: Path, raw: bytes, *, force: bool) -> None:
    if destination.parent.is_symlink() or destination.is_symlink():
        raise ExamplePublishError("destination cannot traverse a symlink")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not destination.is_file():
            raise ExamplePublishError("destination must be a JSON file")
        if destination.read_bytes() == raw:
            return
        if not force:
            raise ExamplePublishError(f"destination exists: {destination}")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, destination)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    if destination.read_bytes() != raw:
        raise ExamplePublishError("published example differs from generated source bytes")


def publish_examples(
    mappings: Sequence[str], *, repo_root: str | os.PathLike[str] = ".", force: bool = False
) -> tuple[dict[str, Any], ...]:
    """Validate every mapping first, then publish each source byte-for-byte."""

    root = Path(repo_root)
    if root.is_symlink() or not root.is_dir():
        raise ExamplePublishError("repo root must be a real directory")
    root = root.resolve()
    if not mappings:
        raise ExamplePublishError("at least one source-to-destination mapping is required")

    prepared: list[tuple[Path, str, Path, bytes, dict[str, Any]]] = []
    destinations: set[str] = set()
    for mapping in mappings:
        source, relative, destination = _parse_mapping(root, mapping)
        if relative in destinations:
            raise ExamplePublishError("each destination may appear only once")
        destinations.add(relative)
        card, raw = _load_card(source)
        _audit_exact_card(raw, Path(relative).name)
        prepared.append((source, relative, destination, raw, card))

    records: list[dict[str, Any]] = []
    for _source, relative, destination, raw, card in prepared:
        _atomic_write(destination, raw, force=force)
        records.append(
            {
                "destination": relative,
                "model_id": card["identity"]["model_id"],
                "revision": card["identity"]["revision"],
                "lifecycle_status": card["lifecycle"]["status"],
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
    return tuple(records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate generated public cards against the packaged schema and privacy "
            "boundary, then copy their exact bytes into cards/."
        )
    )
    parser.add_argument(
        "mappings", nargs="+", metavar="SOURCE=cards/NAME.json"
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = publish_examples(
            args.mappings, repo_root=args.repo_root, force=args.force
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
