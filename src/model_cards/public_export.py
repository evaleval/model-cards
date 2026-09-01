"""Export one source-clean public card from a local ``CardArtifact``."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .artifact import CardArtifact, project_card
from .schema import CONTRACT_VERSION, validate_public_card


BLOCKED_KEYS = frozenset(
    {
        "authorization_sha256",
        "bindings",
        "context_after",
        "context_before",
        "cost_ledger",
        "evidence",
        "exact_text",
        "omission_review_events",
        "prompt",
        "provider_trace",
        "request",
        "response",
        "reviews",
        "route",
        "snapshot_path",
        "source_bundle",
        "source_content",
        "source_text",
        "surrounding_context",
        "usage",
        "validation_checks",
    }
)
SENSITIVE_TEXT = re.compile(
    r"(?ix)(?:"
    r"/Users/|/home/|/private/|/tmp/|/var/tmp/|/var/folders/|"
    r"[A-Z]:[\\/]Users[\\/]|(?:^|\s)~[/\\]|file://|"
    r"\.cache(?:/|\\)|\.codex(?:/|\\)|\.claude(?:/|\\)|"
    r"\.pyenv(?:/|\\)|\.venv(?:/|\\)|"
    r"(?:^|[/\\])vault(?:[/\\]|$)|"
    r"attachments/|pasted-text|private-candidate-evidence|"
    r"source-freeze/|run-state|localhost|127\.0\.0\.1|openrouter|"
    r"https?://[^/@\s]+:[^/@\s]+@|"
    r"api[_-]?key|bearer\s+|sk-[A-Za-z0-9_-]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}"
    r")"
)


class PublicExportError(ValueError):
    """A local artifact cannot cross the public export boundary."""


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def assert_public_projection(value: Any) -> None:
    """Reject private artifact structure, local paths, credentials, and traces."""

    for path, item in _walk(value):
        if isinstance(item, dict):
            found = BLOCKED_KEYS.intersection(item)
            if found:
                raise PublicExportError(
                    f"blocked key at {path}: {', '.join(sorted(found))}"
                )
            for key in item:
                if isinstance(key, str) and SENSITIVE_TEXT.search(key):
                    raise PublicExportError(f"sensitive key at {path}")
        elif isinstance(item, str) and SENSITIVE_TEXT.search(item):
            raise PublicExportError(f"sensitive text at {path}")


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _load_object(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-finite JSON number is not permitted: {value}")

    value = json.loads(raw, parse_constant=reject_constant)
    if not isinstance(value, dict):
        raise PublicExportError("artifact root must be a JSON object")
    return value, raw


def export_public_card(
    artifact_path: str | Path,
    output_path: str | Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Validate a serialized ``CardArtifact`` and write only its public projection."""

    source = Path(artifact_path)
    try:
        payload, raw = _load_object(source)
        artifact = CardArtifact.from_dict(payload)
        card = project_card(artifact)
        validate_public_card(card)
        assert_public_projection(card)
    except PublicExportError:
        raise
    except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        raise PublicExportError(f"invalid CardArtifact: {exc}") from exc

    expected_target = f"{artifact.target.model_id}@{artifact.target.revision}"
    if (
        card["identity"]["model_id"] != artifact.target.model_id
        or card["identity"]["revision"] != artifact.target.revision
    ):
        raise PublicExportError("card identity does not match artifact target")
    if card["lifecycle"]["status"] != artifact.lifecycle_status.value:
        raise PublicExportError("card lifecycle does not match artifact lifecycle")

    scores = card["evaluation"]["benchmark_scores"]
    score_rows = len(scores) if isinstance(scores, list) else 0
    counts = Counter(item.disposition.value for item in artifact.effective_bindings())
    record = {
        "artifact_id": artifact.artifact_id,
        "binding_counts": dict(sorted(counts.items())),
        "card_projection_sha256": hashlib.sha256(_canonical_json(card)).hexdigest(),
        "contract_version": CONTRACT_VERSION,
        "coverage_score": card["validation"]["coverage_score"],
        "exact_target": expected_target,
        "lifecycle_status": artifact.lifecycle_status.value,
        "score_rows": score_rows,
        "source_artifact_sha256": hashlib.sha256(raw).hexdigest(),
    }
    assert_public_projection(record)

    destination = Path(output_path)
    if destination.suffix.lower() != ".json":
        raise PublicExportError("public card output must be a JSON file")
    if destination.is_symlink() or destination.parent.is_symlink():
        raise PublicExportError("public card output cannot be a symlink")
    if destination.exists() and destination.is_dir():
        raise PublicExportError("public card output cannot be a directory")
    if destination.exists() and not force:
        raise PublicExportError(f"output exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(card, allow_nan=False, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the source-clean JSON card from a local CardArtifact."
    )
    parser.add_argument("artifact", help="local CardArtifact JSON")
    parser.add_argument("output", help="public card JSON file")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = export_public_card(args.artifact, args.output, force=args.force)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
