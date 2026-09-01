"""Deterministically migrate retained legacy public cards to contract version 1."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any

from .models import LifecycleStatus
from .schema import (
    CONTENT_FIELD_PATHS,
    NOT_APPLICABLE,
    NOT_SPECIFIED,
    blank_card,
    get_field,
    validate_public_card,
)


def _path(field_path: str) -> str:
    if field_path == "identity.version":
        return "identity.revision"
    if field_path == "links.tech_report":
        return "model_details.technical_report"
    for old, new in (
        ("specifications.", "model_details."),
        ("training_context.", "training."),
        ("access_and_adoption.", "model_details."),
        ("links.", "model_details."),
    ):
        if field_path.startswith(old):
            return new + field_path[len(old) :]
    return field_path


def _source_reference(
    *,
    logical_name: str,
    digest: str,
    model_id: str,
    revision: str,
    old_card: dict[str, Any],
) -> dict[str, str]:
    if logical_name in {"README.md", "README.plain.md"}:
        uri = f"https://huggingface.co/{model_id}/resolve/{revision}/README.md"
        role = "hugging_face_snapshot"
        source_revision = revision
    elif logical_name == "config.json":
        uri = f"https://huggingface.co/{model_id}/resolve/{revision}/config.json"
        role = "hugging_face_metadata"
        source_revision = revision
    elif logical_name == "model_info.json":
        uri = f"https://huggingface.co/api/models/{model_id}/revision/{revision}"
        role = "hugging_face_metadata"
        source_revision = revision
    elif logical_name == "paper.md":
        report = old_card.get("links", {}).get("tech_report")
        uri = report if isinstance(report, str) and report.startswith("https://") else f"urn:sha256:{digest}"
        role = "developer_report"
        source_revision = NOT_SPECIFIED
    elif logical_name == "github_README.md":
        repository = old_card.get("links", {}).get("code_repository")
        uri = (
            repository
            if isinstance(repository, str) and repository.startswith("https://")
            else f"urn:sha256:{digest}"
        )
        role = "developer_code"
        source_revision = NOT_SPECIFIED
    else:
        uri = f"urn:sha256:{digest}"
        role = "eee_index"
        source_revision = NOT_SPECIFIED
    return {
        "source_uri": uri,
        "source_role": role,
        "source_revision": source_revision,
        "source_sha256": digest,
    }


def _validation_checks(old_provenance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {
        "contract_schema": {"status": "completed", "checked": 1, "passed": 1}
    }
    quote = old_provenance.get("quote_verify")
    if isinstance(quote, dict):
        checked = quote.get("emitted", 0)
        passed = quote.get("verified", 0)
        failed = quote.get("rejected", 0)
        if all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in (checked, passed, failed)):
            checks["quote_verification"] = {
                "status": "completed",
                "checked": checked,
                "passed": passed,
                "failed": failed,
            }
    eav = old_provenance.get("eav")
    if isinstance(eav, dict):
        checked = eav.get("checked", 0)
        failed = eav.get("demoted", 0)
        unavailable = eav.get("missing_verdicts", 0)
        passed = max(checked - failed - unavailable, 0) if isinstance(checked, int) else 0
        counts = (checked, passed, failed, unavailable)
        if all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in counts):
            checks["entity_attribution"] = {
                "status": "completed" if unavailable == 0 else "partial",
                "checked": checked,
                "passed": passed,
                "failed": failed,
                "unavailable": unavailable,
            }
    return checks


def migrate_legacy_card(value: dict[str, Any]) -> dict[str, Any]:
    """Relocate existing values and add only contract/missingness/lifecycle metadata."""

    if value.get("contract_version") == "1":
        migrated = deepcopy(value)
        validate_public_card(migrated)
        return migrated
    expected = {
        "identity",
        "lineage",
        "specifications",
        "training_context",
        "access_and_adoption",
        "evaluation",
        "links",
        "provenance_and_quality",
    }
    if set(value) != expected:
        raise ValueError("input is not a supported retained public card")

    card = blank_card()
    identity = deepcopy(value["identity"])
    identity["revision"] = identity.pop("version")
    card["identity"] = identity

    lineage = deepcopy(value["lineage"])
    if isinstance(lineage.get("base_models"), list):
        for item in lineage["base_models"]:
            if isinstance(item, dict) and item.get("relation") == "base":
                item["relation"] = "base_model"
    card["lineage"] = lineage

    card["model_details"].update(deepcopy(value["specifications"]))
    card["model_details"].update(deepcopy(value["access_and_adoption"]))
    links = deepcopy(value["links"])
    links["technical_report"] = links.pop("tech_report")
    card["model_details"].update(links)
    card["training"] = deepcopy(value["training_context"])
    card["evaluation"] = deepcopy(value["evaluation"])

    old_quality = value["provenance_and_quality"]
    card_info = old_quality.get("card_info", {})
    target = card_info.get("target")
    if not isinstance(target, str) or "@" not in target:
        raise ValueError("retained card does not record an exact target")
    model_id, revision = target.rsplit("@", 1)
    if (
        card["identity"]["model_id"] != model_id
        or card["identity"]["revision"] != revision
    ):
        raise ValueError("retained card identity disagrees with its target metadata")

    manifest = card_info.get("source_manifest")
    if not isinstance(manifest, dict):
        raise ValueError("retained card source manifest is missing")
    card["provenance"] = {
        "source_manifest": {
            name: _source_reference(
                logical_name=name,
                digest=digest,
                model_id=model_id,
                revision=revision,
                old_card=value,
            )
            for name, digest in sorted(manifest.items())
        },
        "field_references": {},
        "generator": {
            "name": "auto_benchmarkcard",
            "commit": card_info.get("composer_commit", NOT_SPECIFIED),
            "model": card_info.get("llm"),
        },
    }

    old_provenance = old_quality.get("provenance", {})
    flagged: dict[str, list[dict[str, str]]] = {}
    old_flagged = old_quality.get("flagged_fields", [])
    if isinstance(old_flagged, list):
        for field_path in old_flagged:
            if isinstance(field_path, str):
                flagged[_path(field_path)] = [{"reason": "reported_by_generator"}]
    elif isinstance(old_flagged, dict):
        for field_path, findings in old_flagged.items():
            if isinstance(field_path, str) and isinstance(findings, list):
                flagged[_path(field_path)] = deepcopy(findings)

    missing = [path for path in CONTENT_FIELD_PATHS if get_field(card, path) == NOT_SPECIFIED]
    applicable = [path for path in CONTENT_FIELD_PATHS if get_field(card, path) != NOT_APPLICABLE]
    coverage = round((len(applicable) - len(missing)) / len(applicable), 6) if applicable else 1.0
    card["validation"] = {
        "overall_status": "partial",
        "checks": _validation_checks(old_provenance if isinstance(old_provenance, dict) else {}),
        "flagged_fields": flagged,
        "missing_fields": missing,
        "coverage_score": coverage,
    }

    old_status = card_info.get("lifecycle_status", "generated_unreviewed")
    allowed = {item.value for item in LifecycleStatus}
    if old_status not in allowed:
        raise ValueError("retained card has an unsafe lifecycle label")
    card["lifecycle"] = {
        "status": old_status,
        "generated_at": card_info.get("generated_at", NOT_SPECIFIED),
        "validated_at": card_info.get("validated_at", NOT_SPECIFIED),
    }
    validate_public_card(card)
    return card


def migrate_file(source: str | Path, destination: str | Path, *, force: bool = False) -> Path:
    source_path = Path(source)
    destination_path = Path(destination)
    if destination_path.exists() and not force:
        raise FileExistsError(f"output exists: {destination_path}")
    value = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("retained card root must be an object")
    migrated = migrate_legacy_card(value)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(
        json.dumps(migrated, allow_nan=False, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    print(migrate_file(args.source, args.destination, force=args.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
