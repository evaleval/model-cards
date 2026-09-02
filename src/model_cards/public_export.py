"""Export one source-clean public card from a local ``CardArtifact``."""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from .artifact import CardArtifact, project_card
from .publication import project_publication_card, publication_record
from .publication_contract import build_publication_schema
from .publication_schema import validate_publication_card
from .publication_sources import (
    assert_no_source_excerpt,
    replay_publication_enrichment,
)
from .publication_validation import remove_publication_fields
from .schema import validate_public_card
from .source_state import ImmutableSourceState, load_source_state


BLOCKED_KEYS = frozenset(
    {
        "authorization_sha256",
        "bindings",
        "context_after",
        "context_before",
        "contract_version",
        "cost_ledger",
        "evidence",
        "environmental_information",
        "exact_text",
        "lifecycle",
        "omission_review_events",
        "prompt",
        "provenance",
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
        "use_and_risk",
        "validation",
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


def verify_publication_snapshot(
    artifact: CardArtifact,
    source_state: ImmutableSourceState,
) -> dict[str, Any]:
    """Replay and return one source-bound publication snapshot.

    A digest-shaped catalog identifier is not sufficient by itself.  This
    boundary reverifies the frozen source state, replays deterministic Hub
    enrichment and withholding, and checks public prose against every active
    Hub and official document before any bytes can be exported.
    """

    if not isinstance(artifact, CardArtifact):
        raise PublicExportError("publication export requires a CardArtifact")
    if not isinstance(source_state, ImmutableSourceState):
        raise PublicExportError("publication export requires a frozen source state")
    try:
        source_state = source_state.reverify()
        artifact.validate_integrity()
        if artifact.publication_card is None:
            raise PublicExportError(
                "artifact has no replay-bound publication snapshot"
            )
        if artifact.target != source_state.target:
            raise PublicExportError(
                "publication snapshot target differs from the frozen sources"
            )
        if (
            artifact.publication_source_catalog_sha256
            != source_state.active_catalog_sha256
        ):
            raise PublicExportError(
                "publication snapshot differs from the active frozen source catalog"
            )

        base_card = project_publication_card(project_card(artifact))
        complete = replay_publication_enrichment(source_state.hf_catalog, base_card)
        complete_paths = {item.field_path for item in complete.provenance}
        retained_paths = {
            item.field_path for item in artifact.publication_provenance
        }
        if not retained_paths.issubset(complete_paths):
            raise PublicExportError(
                "publication provenance does not replay from the frozen sources"
            )
        replayed = replay_publication_enrichment(
            source_state.hf_catalog,
            base_card,
            withheld_fields=tuple(sorted(complete_paths - retained_paths)),
        )
        card = remove_publication_fields(
            replayed.card,
            artifact.publication_withheld_fields,
        )
        if (
            card != artifact.publication_card
            or replayed.provenance != artifact.publication_provenance
        ):
            raise PublicExportError(
                "publication card or provenance does not replay from frozen sources"
            )
        assert_no_source_excerpt(card, source_state.catalog)
        validate_publication_card(card)
        assert_public_projection(card)
        return deepcopy(card)
    except PublicExportError:
        raise
    except Exception as exc:
        raise PublicExportError(
            "publication snapshot failed frozen-source replay"
        ) from exc


def export_public_card(
    artifact_path: str | Path,
    output_path: str | Path,
    *,
    source_bundle_directory: str | Path,
    official_bundle_directory: str | Path | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Replay a serialized ``CardArtifact`` and write its public snapshot."""

    source = Path(artifact_path)
    try:
        payload, _raw = _load_object(source)
        artifact = CardArtifact.from_dict(payload)
        audit_card = project_card(artifact)
        validate_public_card(audit_card)
        source_state = load_source_state(
            source_bundle_directory,
            official_bundle_directory,
        )
        card = verify_publication_snapshot(artifact, source_state)
    except PublicExportError:
        raise
    except (
        KeyError,
        TypeError,
        ValueError,
        RuntimeError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise PublicExportError(f"invalid CardArtifact: {exc}") from exc

    expected_target = f"{artifact.target.model_id}@{artifact.target.revision}"
    if (
        card["identity"]["model_id"] != artifact.target.model_id
        or card["identity"]["version"] != artifact.target.revision
    ):
        raise PublicExportError("card identity does not match artifact target")

    scores = card["evaluation"].get("benchmark_scores")
    score_rows = len(scores) if isinstance(scores, list) else 0
    publication = publication_record(card)
    record = {
        "card_projection_sha256": hashlib.sha256(_canonical_json(card)).hexdigest(),
        "coverage_score": publication["coverage_score"],
        "exact_target": expected_target,
        "publication_field_count": publication["field_count"],
        "publication_schema_sha256": hashlib.sha256(
            _canonical_json(build_publication_schema())
        ).hexdigest(),
        "score_rows": score_rows,
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
    parser.add_argument(
        "--source-bundle",
        required=True,
        help="frozen Hugging Face source-bundle directory",
    )
    parser.add_argument(
        "--official-bundle",
        help="optional frozen official-source bundle directory",
    )
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = export_public_card(
        args.artifact,
        args.output,
        source_bundle_directory=args.source_bundle,
        official_bundle_directory=args.official_bundle,
        force=args.force,
    )
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
