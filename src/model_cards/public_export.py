"""Export one source-clean JSON card from a full generated artifact.

Full research artifacts may contain frozen source bytes, evidence spans, provider
traces, and local execution metadata. This module validates that boundary and writes
only the generated ``card`` projection.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable

from .schema import CONTENT_FIELD_PATHS, validate_complete_card


BLOCKED_KEYS = frozenset(
    {
        "authorization_sha256",
        "bindings",
        "context_after",
        "context_before",
        "cost_ledger",
        "evidence",
        "exact_text",
        "executor_id",
        "metadata",
        "omission_review_events",
        "private_candidate_run",
        "private_source_gap_readiness",
        "prompt",
        "provider",
        "provider_trace",
        "request",
        "response",
        "review_events",
        "route",
        "run_id",
        "snapshot_path",
        "source_bundle",
        "source_content",
        "source_text",
        "spend_owner",
        "structured_fragment",
        "surrounding_context",
        "usage",
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
    r"roster12/|source-freeze/|run-state|"
    r"localhost|127\.0\.0\.1|openrouter|"
    r"https?://[^/@\s]+:[^/@\s]+@|"
    r"api[_-]?key|bearer\s+|sk-[A-Za-z0-9_-]{20,}|"
    r"gh[pousr]_[A-Za-z0-9]{20,}|hf_[A-Za-z0-9]{20,}"
    r")"
)

REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
ARTIFACT_ID_RE = re.compile(r"^card_[0-9a-f]{24}$")
GENERATED_AT_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
LLM_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")

CARD_INFO_KEYS = frozenset(
    {
        "composer_commit",
        "condition",
        "frame",
        "generated_at",
        "inapplicable_fields",
        "llm",
        "quality_snapshot",
        "schema_version",
        "source_manifest",
        "target",
    }
)
PUBLIC_SOURCE_NAMES = frozenset(
    {
        "README.md",
        "README.plain.md",
        "config.json",
        "eee.json",
        "github_README.md",
        "model_info.json",
        "paper.md",
    }
)
FRAME_KEYS = frozenset(
    {
        "target",
        "family",
        "family_target_collision_disambiguated",
        "base",
        "benchmarks",
        "metrics",
        "siblings_llm",
        "comparisons_llm",
        "family_aliases_llm",
        "own_name_dropped",
    }
)
BINDING_ACTIONS = frozenset({"accept", "withhold"})


class PublicExportError(ValueError):
    """A generated artifact cannot cross the public export boundary."""


def _walk(value: Any, path: str = "$") -> Iterable[tuple[str, Any]]:
    yield path, value
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk(item, f"{path}[{index}]")


def assert_public_projection(value: Any) -> None:
    """Reject private artifact structure, local paths, and execution traces."""

    for path, item in _walk(value):
        if isinstance(item, dict):
            found = BLOCKED_KEYS.intersection(item)
            if found:
                names = ", ".join(sorted(found))
                raise PublicExportError(f"blocked key at {path}: {names}")
            for key in item:
                if isinstance(key, str) and SENSITIVE_TEXT.search(key):
                    raise PublicExportError(f"sensitive key at {path}")
        elif isinstance(item, str) and SENSITIVE_TEXT.search(item):
            raise PublicExportError(f"sensitive text at {path}")


def _canonical_json(value: Any) -> bytes:
    text = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return (text + "\n").encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_target(artifact: dict[str, Any], card: dict[str, Any]) -> str:
    target = artifact.get("target")
    if not isinstance(target, dict):
        raise PublicExportError("artifact has no exact target")
    model_id = target.get("model_id")
    revision = target.get("resolved_revision", target.get("revision"))
    if not isinstance(model_id, str) or not isinstance(revision, str):
        raise PublicExportError("artifact has no exact target")
    if (
        model_id.count("/") != 1
        or any(not part or part.strip() != part for part in model_id.split("/"))
        or REVISION_RE.fullmatch(revision) is None
    ):
        raise PublicExportError("artifact target is not an exact model revision")
    canonical = f"{model_id}@{revision}"

    identity = card.get("identity")
    if not isinstance(identity, dict):
        raise PublicExportError("card has no identity section")
    if identity.get("model_id") != model_id or identity.get("version") != revision:
        raise PublicExportError("card identity does not match artifact target")

    card_info = card.get("provenance_and_quality", {}).get("card_info", {})
    recorded = card_info.get("target") if isinstance(card_info, dict) else None
    if isinstance(recorded, dict):
        recorded_model = recorded.get("model_id")
        recorded_revision = recorded.get(
            "resolved_revision",
            recorded.get("revision"),
        )
        recorded = f"{recorded_model}@{recorded_revision}"
    if recorded != canonical:
        raise PublicExportError("card metadata does not match artifact target")
    return canonical


def _binding_counts(artifact: dict[str, Any]) -> dict[str, int]:
    bindings = artifact.get("bindings", [])
    if not isinstance(bindings, list):
        raise PublicExportError("artifact bindings are not a list")
    counts: Counter[str] = Counter()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise PublicExportError("artifact contains an invalid binding")
        action = binding.get("verifier_action")
        if action not in BINDING_ACTIONS:
            raise PublicExportError("artifact contains an unknown verifier action")
        counts[action] += 1
    return dict(sorted(counts.items()))


def _validate_card_info(card_info: dict[str, Any]) -> None:
    extra = set(card_info) - CARD_INFO_KEYS
    if extra:
        names = ", ".join(sorted(extra))
        raise PublicExportError(f"card_info contains non-public keys: {names}")

    manifest = card_info.get("source_manifest")
    if not isinstance(manifest, dict) or not manifest:
        raise PublicExportError("card source manifest is missing")
    for name, digest in manifest.items():
        if (
            name not in PUBLIC_SOURCE_NAMES
            or not isinstance(digest, str)
            or DIGEST_RE.fullmatch(digest) is None
        ):
            raise PublicExportError(
                "source manifest must contain public logical names and SHA-256 digests"
            )

    commit = card_info.get("composer_commit")
    if not isinstance(commit, str) or REVISION_RE.fullmatch(commit) is None:
        raise PublicExportError("card_info has no exact composer commit")

    condition = card_info.get("condition")
    if condition is not None and condition != "hybrid":
        raise PublicExportError("card_info condition is not a public value")
    snapshot = card_info.get("quality_snapshot")
    if snapshot is not None and snapshot != "generation_time":
        raise PublicExportError("card_info quality_snapshot is not a public value")
    generated_at = card_info.get("generated_at")
    if generated_at is not None and (
        not isinstance(generated_at, str)
        or GENERATED_AT_RE.fullmatch(generated_at) is None
    ):
        raise PublicExportError("card_info generated_at is not an ISO-8601 timestamp")
    llm = card_info.get("llm")
    if llm is not None and (
        not isinstance(llm, str) or LLM_IDENTIFIER_RE.fullmatch(llm) is None
    ):
        raise PublicExportError("card_info llm is not a public model identifier")

    fields = card_info.get("inapplicable_fields")
    if (
        not isinstance(fields, list)
        or len(fields) != len(set(fields))
        or not all(item in CONTENT_FIELD_PATHS for item in fields)
    ):
        raise PublicExportError(
            "card_info inapplicable_fields must contain unique schema field paths"
        )

    frame = card_info.get("frame")
    if frame is not None and (
        not isinstance(frame, dict)
        or not set(frame).issubset(FRAME_KEYS)
        or not all(
            isinstance(value, int) and not isinstance(value, bool) and value >= 0
            for value in frame.values()
        )
    ):
        raise PublicExportError("card_info frame must contain public non-negative counts")


def export_public_card(
    artifact_path: str | Path,
    output_path: str | Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Validate a full artifact and write only its JSON card projection."""

    source = Path(artifact_path)
    raw = source.read_bytes()
    artifact = json.loads(raw)
    if not isinstance(artifact, dict) or not isinstance(artifact.get("card"), dict):
        raise PublicExportError("input is not a generated Model Card artifact")
    if artifact.get("schema_version") != "5":
        raise PublicExportError("input is not a schema-v5 artifact")

    card = artifact["card"]
    validate_complete_card(card)
    assert_public_projection(card)

    quality = card.get("provenance_and_quality", {})
    card_info = quality.get("card_info", {}) if isinstance(quality, dict) else {}
    if not isinstance(card_info, dict) or card_info.get("schema_version") != "5":
        raise PublicExportError("card schema metadata does not match the artifact")
    _validate_card_info(card_info)

    coverage = quality.get("coverage_score") if isinstance(quality, dict) else None
    if (
        not isinstance(coverage, (int, float))
        or isinstance(coverage, bool)
        or not math.isfinite(float(coverage))
        or not 0.0 <= float(coverage) <= 1.0
    ):
        raise PublicExportError("card coverage score is invalid")

    scores = card.get("evaluation", {}).get("benchmark_scores", [])
    if scores == "Not specified":
        score_rows = 0
    elif isinstance(scores, list):
        score_rows = len(scores)
    else:
        raise PublicExportError("card benchmark scores have an invalid shape")

    artifact_id = artifact.get("artifact_id")
    if not isinstance(artifact_id, str) or ARTIFACT_ID_RE.fullmatch(artifact_id) is None:
        raise PublicExportError("artifact has no canonical public artifact ID")

    record = {
        "artifact_id": artifact_id,
        "binding_counts": _binding_counts(artifact),
        "card_projection_sha256": _sha256(_canonical_json(card)),
        "coverage_score": coverage,
        "exact_target": _exact_target(artifact, card),
        "schema_version": artifact["schema_version"],
        "score_rows": score_rows,
        "source_artifact_sha256": _sha256(raw),
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
    card_text = json.dumps(card, ensure_ascii=False, indent=2) + "\n"
    assert_public_projection(card_text)
    destination.write_text(card_text, encoding="utf-8")
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the source-clean JSON card from a full artifact."
    )
    parser.add_argument("artifact", help="local full CardArtifact JSON")
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
