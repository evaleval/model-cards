"""Export a source-clean public view from a generated Model Card artifact.

The full artifacts used by the research workflow contain frozen source bytes,
evidence spans, run metadata, and local paths. This module exports only the
generated ``card`` projection and a small allowlisted provenance record.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
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
LOGICAL_SOURCE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
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

STATUS_TEXT = {
    "development": (
        "Generated development output. It has not been human-reviewed and is "
        "not a release."
    ),
    "historical": (
        "Historical offline feasibility output. It is included to show coverage "
        "and honest absence, not as a release-quality card."
    ),
    "audit-case": (
        "Audit-blocked generated output. The automated audit found source-present "
        "omissions, so this card was not promoted."
    ),
}

AUDIT_TEXT = {
    "projected_claim_support_scope_passed": (
        "no blocking support or scope finding among projected claims"
    ),
    "blocked": "blocked",
    "not_run": "not run",
}


class PublicExampleError(ValueError):
    """A generated artifact cannot be exported without crossing the public boundary."""


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
                raise PublicExampleError(f"blocked key at {path}: {names}")
        elif isinstance(item, str) and SENSITIVE_TEXT.search(item):
            raise PublicExampleError(f"sensitive text at {path}")


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


def _target(artifact: dict[str, Any], card: dict[str, Any]) -> str:
    target = artifact.get("target")
    if not isinstance(target, dict):
        raise PublicExampleError("artifact has no exact target")
    model_id = target.get("model_id")
    revision = target.get("resolved_revision", target.get("revision"))
    if not isinstance(model_id, str) or not isinstance(revision, str):
        raise PublicExampleError("artifact has no exact target")
    if (
        model_id.count("/") != 1
        or any(not part or part.strip() != part for part in model_id.split("/"))
        or REVISION_RE.fullmatch(revision) is None
    ):
        raise PublicExampleError("artifact target is not an exact model revision")
    canonical = f"{model_id}@{revision}"

    identity = card.get("identity")
    if not isinstance(identity, dict):
        raise PublicExampleError("card has no identity section")
    if identity.get("model_id") != model_id or identity.get("version") != revision:
        raise PublicExampleError("card identity does not match artifact target")

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
        raise PublicExampleError("card metadata does not match artifact target")
    return canonical


def _binding_counts(artifact: dict[str, Any]) -> dict[str, int]:
    bindings = artifact.get("bindings", [])
    if not isinstance(bindings, list):
        raise PublicExampleError("artifact bindings are not a list")
    counts: Counter[str] = Counter()
    for binding in bindings:
        if not isinstance(binding, dict):
            raise PublicExampleError("artifact contains an invalid binding")
        action = binding.get("verifier_action")
        if action not in BINDING_ACTIONS:
            raise PublicExampleError("artifact contains an unknown verifier action")
        counts[action] += 1
    return dict(sorted(counts.items()))


def _validate_card_info(card_info: dict[str, Any]) -> None:
    extra = set(card_info) - CARD_INFO_KEYS
    if extra:
        names = ", ".join(sorted(extra))
        raise PublicExampleError(f"card_info contains non-public keys: {names}")

    manifest = card_info.get("source_manifest")
    if not isinstance(manifest, dict) or not manifest:
        raise PublicExampleError("card source manifest is missing")
    for name, digest in manifest.items():
        if (
            not isinstance(name, str)
            or LOGICAL_SOURCE_NAME_RE.fullmatch(name) is None
            or name not in PUBLIC_SOURCE_NAMES
            or not isinstance(digest, str)
            or DIGEST_RE.fullmatch(digest) is None
        ):
            raise PublicExampleError(
                "source manifest must contain public logical names and SHA-256 digests"
            )

    commit = card_info.get("composer_commit")
    if not isinstance(commit, str) or REVISION_RE.fullmatch(commit) is None:
        raise PublicExampleError("card_info has no exact composer commit")

    condition = card_info.get("condition")
    if condition is not None and condition != "hybrid":
        raise PublicExampleError("card_info condition is not a public value")
    snapshot = card_info.get("quality_snapshot")
    if snapshot is not None and snapshot != "generation_time":
        raise PublicExampleError("card_info quality_snapshot is not a public value")
    generated_at = card_info.get("generated_at")
    if generated_at is not None and (
        not isinstance(generated_at, str)
        or GENERATED_AT_RE.fullmatch(generated_at) is None
    ):
        raise PublicExampleError("card_info generated_at is not an ISO-8601 timestamp")
    llm = card_info.get("llm")
    if llm is not None and (
        not isinstance(llm, str) or LLM_IDENTIFIER_RE.fullmatch(llm) is None
    ):
        raise PublicExampleError("card_info llm is not a public model identifier")

    fields = card_info.get("inapplicable_fields")
    if (
        not isinstance(fields, list)
        or len(fields) != len(set(fields))
        or not all(item in CONTENT_FIELD_PATHS for item in fields)
    ):
        raise PublicExampleError(
            "card_info inapplicable_fields must contain unique schema field paths"
        )

    frame = card_info.get("frame")
    if frame is not None and (
        not isinstance(frame, dict)
        or not set(frame).issubset(FRAME_KEYS)
        or not all(
            isinstance(key, str)
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
            for key, value in frame.items()
        )
    ):
        raise PublicExampleError("card_info frame must contain integer counts")


def _display(value: Any) -> str:
    if value == "Not specified":
        return "*Not specified*"
    if isinstance(value, str):
        return value.replace("\n", " ")
    if isinstance(value, (int, float, bool)) or value is None:
        return str(value)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return ", ".join(value)
    if isinstance(value, list) and all(isinstance(item, dict) for item in value):
        rows = []
        for item in value:
            if "model_id" not in item:
                break
            details = [
                f"{key}: {entry}"
                for key, entry in item.items()
                if key != "model_id"
            ]
            suffix = f" ({'; '.join(details)})" if details else ""
            rows.append(f"{item['model_id']}{suffix}")
        if len(rows) == len(value):
            return "; ".join(rows)
    if isinstance(value, dict) and set(value) == {"name", "url"}:
        return f"[{value['name']}]({value['url']})"
    if isinstance(value, dict) and set(value).issubset({"input", "output"}):
        parts = []
        for key in ("input", "output"):
            if key in value:
                items = value[key]
                rendered = ", ".join(items) if isinstance(items, list) else str(items)
                parts.append(f"{key}: {rendered}")
        return "; ".join(parts)
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2) + "\n```"


def _settings(value: Any) -> str:
    if not isinstance(value, dict):
        return _display(value).replace("|", "\\|")
    parts = [f"{key}={_display(item)}" for key, item in value.items()]
    return "; ".join(parts).replace("|", "\\|")


def _scores_markdown(scores: list[Any]) -> list[str]:
    lines = [
        "| Benchmark | Metric | Score | Split | Setting |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in scores:
        if not isinstance(row, dict):
            continue
        cells = [
            row.get("benchmark", ""),
            row.get("metric", ""),
            row.get("score", ""),
            row.get("split", ""),
            _settings(row.get("setting", "")),
        ]
        rendered = [str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells]
        lines.append("| " + " | ".join(rendered) + " |")
    return lines


def render_card_markdown(
    artifact: dict[str, Any],
    card: dict[str, Any],
    public_record: dict[str, Any],
) -> str:
    identity = card.get("identity", {})
    name = identity.get("name") if isinstance(identity, dict) else None
    title = name if isinstance(name, str) and name else public_record["exact_target"].split("@", 1)[0]
    counts = public_record["binding_counts"]
    coverage = public_record["coverage_score"]
    coverage_text = f"{coverage * 100:.1f}%" if isinstance(coverage, (int, float)) else "not reported"

    lines = [
        f"# Model Card: {title}",
        "",
        f"> {STATUS_TEXT[public_record['status']]}",
        "",
        f"- Exact target: `{public_record['exact_target']}`",
        f"- Artifact: `{public_record['artifact_id']}`",
        f"- Schema: v{public_record['schema_version']}",
        f"- Field coverage: {coverage_text}",
        f"- Generated bindings: {counts.get('accept', 0)} accepted, "
        f"{counts.get('withhold', 0)} withheld",
        f"- Automated audit annotation: {AUDIT_TEXT[public_record['automated_audit']]}",
        "- Audit record in public export: no",
        "- Human review: not run",
        "",
    ]
    if public_record.get("note"):
        lines.extend((public_record["note"], ""))

    for section, fields in card.items():
        heading = section.replace("_", " ").title()
        lines.extend((f"## {heading}", ""))
        if section == "provenance_and_quality" and isinstance(fields, dict):
            missing = fields.get("missing_fields", [])
            flagged = fields.get("flagged_fields", [])
            lines.extend(
                (
                    f"- Coverage score: {_display(fields.get('coverage_score'))}",
                    f"- Missing fields: {_display(missing) if missing else 'none'}",
                    f"- Flagged fields: {_display(flagged) if flagged else 'none'}",
                    "- Generation summary and source-manifest hashes remain in `card.json`.",
                    "- Field-level evidence remains in the non-public source artifact.",
                    "",
                )
            )
            continue
        if not isinstance(fields, dict):
            lines.extend((_display(fields), ""))
            continue
        for field, value in fields.items():
            label = field.replace("_", " ")
            if section == "evaluation" and field == "benchmark_scores" and isinstance(value, list):
                lines.extend(("", f"### {label.title()}", ""))
                lines.extend(_scores_markdown(value))
                lines.append("")
            else:
                lines.append(f"- **{label}:** {_display(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_public_example(
    artifact_path: str | Path,
    output_dir: str | Path,
    *,
    status: str,
    automated_audit: str,
    note: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    if status not in STATUS_TEXT:
        raise PublicExampleError(f"unknown status: {status}")
    if automated_audit not in AUDIT_TEXT:
        raise PublicExampleError(f"unknown automated audit state: {automated_audit}")

    source = Path(artifact_path)
    raw = source.read_bytes()
    artifact = json.loads(raw)
    if not isinstance(artifact, dict) or not isinstance(artifact.get("card"), dict):
        raise PublicExampleError("input is not a generated Model Card artifact")
    if artifact.get("schema_version") != "5":
        raise PublicExampleError("input is not a schema-v5 artifact")
    card = artifact["card"]
    validate_complete_card(card)
    assert_public_projection(card)

    quality = card.get("provenance_and_quality", {})
    card_info = quality.get("card_info", {}) if isinstance(quality, dict) else {}
    if not isinstance(card_info, dict) or card_info.get("schema_version") != "5":
        raise PublicExampleError("card schema metadata does not match the artifact")
    _validate_card_info(card_info)
    coverage = quality.get("coverage_score") if isinstance(quality, dict) else None
    scores = card.get("evaluation", {}).get("benchmark_scores", [])
    score_rows = len(scores) if isinstance(scores, list) else 0
    artifact_id = artifact.get("artifact_id")
    if not isinstance(artifact_id, str) or ARTIFACT_ID_RE.fullmatch(artifact_id) is None:
        raise PublicExampleError("artifact has no canonical public artifact ID")
    public_record = {
        "artifact_id": artifact_id,
        "audit_annotation_source": (
            "not_applicable"
            if automated_audit == "not_run"
            else "operator_supplied_from_non_public_audit_record"
        ),
        "audit_record_in_export": False,
        "automated_audit": automated_audit,
        "binding_counts": _binding_counts(artifact),
        "card_projection_sha256": _sha256(_canonical_json(card)),
        "coverage_score": coverage,
        "exact_target": _target(artifact, card),
        "export_scope": "generated_card_projection_only",
        "human_review": "not_run",
        "note": note,
        "projection_profile": (
            "historical_feasibility_v5"
            if status == "historical"
            else "model_assisted_v5"
        ),
        "schema_version": artifact.get("schema_version"),
        "schema_validation": "complete_v5_38_field_structure",
        "score_rows": score_rows,
        "source_artifact_sha256": _sha256(raw),
        "status": status,
    }
    if not isinstance(public_record["schema_version"], str):
        raise PublicExampleError("artifact has no schema version")
    assert_public_projection(public_record)

    destination = Path(output_dir)
    paths = {
        "card": destination / "card.json",
        "markdown": destination / "card.md",
        "record": destination / "public-export.json",
    }
    if destination.is_symlink():
        raise PublicExampleError("output directory cannot be a symlink")
    if destination.exists() and not destination.is_dir():
        raise PublicExampleError("output destination must be a directory")
    allowed_paths = set(paths.values())
    existing_entries = set(destination.iterdir()) if destination.exists() else set()
    unexpected = existing_entries - allowed_paths
    if unexpected:
        names = ", ".join(sorted(path.name for path in unexpected))
        raise PublicExampleError(f"output directory contains unexpected entries: {names}")
    if any(path.is_symlink() for path in existing_entries):
        raise PublicExampleError("output files cannot be symlinks")
    if not force:
        existing = [str(path) for path in paths.values() if path.exists()]
        if existing:
            raise PublicExampleError("output exists: " + ", ".join(existing))
    destination.mkdir(parents=True, exist_ok=True)

    card_text = json.dumps(card, ensure_ascii=False, indent=2) + "\n"
    record_text = json.dumps(public_record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    markdown = render_card_markdown(artifact, card, public_record)
    for value in (card_text, record_text, markdown):
        assert_public_projection(value)
    paths["card"].write_text(card_text, encoding="utf-8")
    paths["record"].write_text(record_text, encoding="utf-8")
    paths["markdown"].write_text(markdown, encoding="utf-8")
    return public_record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export the source-clean card projection from a full artifact."
    )
    parser.add_argument("artifact", help="local full CardArtifact JSON")
    parser.add_argument("output_dir", help="public example directory")
    parser.add_argument("--status", choices=sorted(STATUS_TEXT), required=True)
    parser.add_argument(
        "--automated-audit",
        choices=tuple(AUDIT_TEXT),
        required=True,
    )
    parser.add_argument("--note")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    record = export_public_example(
        args.artifact,
        args.output_dir,
        status=args.status,
        automated_audit=args.automated_audit,
        note=args.note,
        force=args.force,
    )
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
