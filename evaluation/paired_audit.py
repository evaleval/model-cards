#!/usr/bin/env python3
"""Offline cross-instrument audit for frozen Model Card evaluation artifacts.

The audit deliberately consumes privacy-safe aggregate artifacts.  It never
loads source bodies, calls a provider, or promotes automated dispositions to
human ground truth.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from model_cards.quality_report import (
    QUALITY_REPORT_VERSION,
    QualityReport,
    QualityReportError,
)


AUDIT_VERSION = "model-card-paired-failure-audit/v1"
ENGINEERING_READ_VERSION = "baseline-full-engineering-read/v1"
LABELS_VERSION = "model-card-paired-audit-labels/v1"
TARGET_MAP_VERSION = "model-card-paired-audit-target-map/v1"
AUTO_BENCHMARKCARDS_SUMMARY_SHA256 = (
    "dcd4d976566278e1a6872daf3d1dcb87af731c8c95af3796459f278a95af2317"
)
AUTO_BENCHMARKCARDS_VERIFIER_SHA256 = (
    "03a0e9497ec2d1fa6b4ce92e32a51070ad24e55218d6e7cbf2c74d4fdcdc5323"
)
AUTO_BENCHMARKCARDS_SCHEMA_VERSION = 3

_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
_ITEM_ID_RE = re.compile(r"^[a-z][a-z0-9-]{7,127}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CURRENT_FINDING_CODES = (
    "wrong_entity",
    "wrong_checkpoint",
    "wrong_relation",
    "wrong_field",
    "invalid_score_row",
)
_GATES = (
    "coordinate_integrity",
    "entity_scope",
    "field_fit",
    "value_support",
)

_ABC_SUMMARY_KEYS = {
    "candidate_risk_source_judge",
    "frozen_corpus",
    "human_validation",
    "public_source_screen",
    "sample",
    "schema_version",
    "source_bounded_judge",
    "validation_flags",
}
_ABC_FIVE_STATE_NAMES = (
    "filled_fully_supported",
    "filled_partially_supported",
    "filled_unsupported",
    "not_specified_information_available",
    "not_specified_no_information",
)
_ABC_SCREEN_CATEGORIES = {
    "fabricated-fact",
    "other",
    "thin",
    "wrong-identity",
    "wrong-paper",
    "wrong-section-splice",
}
_ABC_VERIFIER_LABELS = {
    "confirmed-material",
    "confirmed-trivial",
    "not-a-defect",
}
_ABC_VERIFIER_COLUMNS = (
    "row_id",
    "card",
    "card_reference",
    "finding_index",
    "category",
    "field",
    "issue",
    "screen_claimed_ground_truth",
    "verifier_label",
    "evidence_url",
    "notes",
)
_ABC_VERIFIER_CATEGORY_COUNTS = {
    "fabricated-fact": 38,
    "other": 7,
    "thin": 24,
    "wrong-identity": 4,
    "wrong-paper": 4,
    "wrong-section-splice": 77,
}
_ABC_VERIFIER_LABEL_COUNTS = {
    "confirmed-material": 111,
    "confirmed-trivial": 20,
    "not-a-defect": 23,
}
_ABC_VERIFIER_MATERIAL_COUNTS = {
    "fabricated-fact": 22,
    "other": 3,
    "thin": 17,
    "wrong-identity": 3,
    "wrong-paper": 3,
    "wrong-section-splice": 63,
}
_ABC_RELEASE_SUMMARY_SIGNATURE = {
    "field_rows": 3450,
    "filled_rows": 2035,
    "not_specified_rows": 1415,
    "supported_including_eee": 0.8608375363016555,
    "partial": 0.12432775746741817,
    "unsupported": 0.014834706230926285,
    "five_state_counts": {
        "filled_fully_supported": (1746, 3450),
        "filled_partially_supported": (259, 3450),
        "filled_unsupported": (30, 3450),
        "not_specified_information_available": (244, 3450),
        "not_specified_no_information": (1171, 3450),
    },
    "five_state_values": {
        "filled_fully_supported": 0.5189412066126995,
        "filled_partially_supported": 0.07494886520954902,
        "filled_unsupported": 0.008942849291046896,
        "not_specified_information_available": 0.0729494117353641,
        "not_specified_no_information": 0.32421766715134054,
    },
    "five_state_ci95": {
        "filled_fully_supported": (0.4748678152236265, 0.5610093497001332),
        "filled_partially_supported": (0.064441892612462, 0.08563095431806408),
        "filled_unsupported": (0.005221766611770648, 0.013490839232384534),
        "not_specified_information_available": (
            0.055584359232074936,
            0.09249614396962402,
        ),
        "not_specified_no_information": (
            0.28178441745069405,
            0.36920754763787206,
        ),
    },
    "risk_counts": (547, 214, 761),
    "risk_rate": 0.748351513135232,
    "risk_ci95": (0.6938486579427771, 0.7994730375808277),
    "warning_counts": (33, 30, 1),
    "warning_rates": (0.0303030303030303, 0.018591000304935164),
    "screen_label_counts": {
        "confirmed-material": 111,
        "confirmed-trivial": 20,
        "not-a-defect": 23,
        "unsure": 0,
    },
    "inference_guard": (
        "defect prevalence",
        "screen recall",
        "screen accuracy",
        "standard false-positive rate",
        "human reliability",
    ),
}

_LABEL_ENUMS = {
    "support": {
        "fully_supported",
        "partially_supported",
        "unsupported",
        "unavailable",
        "not_applicable",
    },
    "source_binding": {
        "correct",
        "wrong",
        "missing",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "entity_checkpoint": {
        "correct",
        "wrong_entity",
        "wrong_checkpoint",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "relation": {
        "correct",
        "wrong",
        "unresolved",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "field_fit": {
        "correct",
        "wrong",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "score_row": {
        "correct",
        "wrong",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "omission": {
        "not_omitted",
        "justified_abstention",
        "source_present_omission",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "conflict_visibility": {
        "visible",
        "not_visible",
        "no_conflict",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "risk_grounding": {
        "adequate",
        "inadequate",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "risk_applicability": {
        "applies",
        "does_not_apply",
        "unclear",
        "unavailable",
        "not_applicable",
    },
    "actionable_error": {"yes", "no", "unclear", "unavailable"},
}


class AuditError(ValueError):
    """An input is malformed, stale, unpaired, or outside the audit contract."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AuditError("audit value is not finite JSON") from exc


def _strict_load(path: Path, label: str) -> tuple[dict[str, Any], str]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise AuditError(f"{label} contains duplicate keys")
            output[key] = value
        return output

    def reject_nonfinite(value: str) -> None:
        raise AuditError(f"{label} contains non-finite number {value}")

    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=reject_nonfinite,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditError(f"{label} is unavailable or invalid JSON") from exc
    if not isinstance(value, dict):
        raise AuditError(f"{label} root must be an object")
    return value, hashlib.sha256(raw).hexdigest()


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise AuditError(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise AuditError(f"{label} must be an array")
    return value


def _count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AuditError(f"{label} must be a non-negative integer")
    return value


def _raw_count(value: Any, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or int(value) != value
    ):
        raise AuditError(f"{label} must be a non-negative integral count")
    return int(value)


def _probability(value: Any, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0.0 <= float(value) <= 1.0
    ):
        raise AuditError(f"{label} must be a finite probability")
    return float(value)


def _interval(value: Any, estimate: float, label: str) -> list[float]:
    bounds = _array(value, label)
    if len(bounds) != 2:
        raise AuditError(f"{label} must contain two bounds")
    lower = _probability(bounds[0], f"{label}[0]")
    upper = _probability(bounds[1], f"{label}[1]")
    if lower > estimate or estimate > upper:
        raise AuditError(f"{label} does not contain its estimate")
    return [lower, upper]


def _verify_embedded_hash(value: Mapping[str, Any], field: str, label: str) -> None:
    expected = value.get(field)
    if not isinstance(expected, str) or not _DIGEST_RE.fullmatch(expected):
        raise AuditError(f"{label} has no valid {field}")
    payload = dict(value)
    payload.pop(field)
    if hashlib.sha256(_canonical(payload)).hexdigest() != expected:
        raise AuditError(f"{label} embedded digest does not match its content")


def _distribution(value: Any, label: str) -> dict[str, int]:
    item = _object(value, label)
    entries = _array(item.get("entries"), f"{label}.entries")
    expected_total = _count(item.get("total"), f"{label}.total")
    result: dict[str, int] = {}
    for index, entry_value in enumerate(entries):
        entry = _object(entry_value, f"{label}.entries[{index}]")
        if set(entry) != {"key", "count"}:
            raise AuditError(f"{label} distribution entry has an invalid shape")
        key = entry["key"]
        if not isinstance(key, str) or not key or key in result:
            raise AuditError(f"{label} distribution key is invalid")
        result[key] = _count(entry["count"], f"{label}.{key}")
    if sum(result.values()) != expected_total:
        raise AuditError(f"{label} distribution total is inconsistent")
    return dict(sorted(result.items()))


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    numerator = _count(numerator, "ratio numerator")
    denominator = _count(denominator, "ratio denominator")
    if numerator > denominator:
        raise AuditError("ratio numerator exceeds denominator")
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": None if denominator == 0 else numerator / denominator,
    }


def _gate_map(claims: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    gates = _array(claims.get("gates"), "quality claims.gates")
    output: dict[str, dict[str, Any]] = {}
    for raw in gates:
        gate = _object(raw, "quality gate")
        name = gate.get("gate")
        if name not in _GATES or name in output:
            raise AuditError("quality report gate identity is invalid")
        checked = _count(gate.get("checked"), f"{name}.checked")
        accepted = _count(gate.get("accepted"), f"{name}.accepted")
        withheld = _count(gate.get("withheld"), f"{name}.withheld")
        if accepted + withheld != checked:
            raise AuditError("quality report gate counts are inconsistent")
        output[name] = {
            "checked": checked,
            "accepted": accepted,
            "withheld": withheld,
            "acceptance": _ratio(accepted, checked),
            "reasons": _distribution(gate.get("reasons"), f"{name}.reasons"),
        }
    if set(output) != set(_GATES):
        raise AuditError("quality report does not contain all four gates")
    return {name: output[name] for name in _GATES}


def _quality_metrics(report: Mapping[str, Any]) -> dict[str, Any]:
    if report.get("report_version") != QUALITY_REPORT_VERSION:
        raise AuditError("quality report version is unsupported")
    _verify_embedded_hash(report, "report_sha256", "quality report")
    targets = _array(report.get("targets"), "quality report targets")
    aggregate = _object(report.get("aggregate"), "quality report aggregate")
    claims = _object(aggregate.get("claims"), "quality aggregate claims")
    fields = _object(aggregate.get("fields"), "quality aggregate fields")
    findings = _object(aggregate.get("findings"), "quality aggregate findings")
    fact = _object(aggregate.get("factreasoner"), "quality aggregate FactReasoner")
    omissions = _object(aggregate.get("omissions"), "quality aggregate omissions")
    risk = _object(aggregate.get("risk"), "quality aggregate risk")

    claim_total = _count(claims.get("total"), "claims.total")
    included = _count(claims.get("included"), "claims.included")
    withheld = _count(claims.get("withheld"), "claims.withheld")
    if included + withheld != claim_total:
        raise AuditError("quality report claim counts are inconsistent")
    gates = _gate_map(claims)

    finding_codes = _distribution(findings.get("codes"), "quality findings.codes")
    assignment = {code: finding_codes.get(code, 0) for code in _CURRENT_FINDING_CODES}

    field_total = _count(fields.get("total"), "fields.total")
    field_present = _count(fields.get("present"), "fields.present")
    field_omitted = _count(fields.get("omitted"), "fields.omitted")
    if field_present + field_omitted != field_total:
        raise AuditError("quality report field counts are inconsistent")
    source_present = _count(
        omissions.get("source_present_count"), "omissions.source_present_count"
    )
    core_conflict_fields = _count(
        omissions.get("conflict_field_count"), "omissions.conflict_field_count"
    )
    core_conflict_records = _count(
        omissions.get("conflict_record_count"), "omissions.conflict_record_count"
    )
    publication_conflict_fields = _count(
        omissions.get("publication_conflict_field_count"),
        "omissions.publication_conflict_field_count",
    )
    publication_conflicts = _count(
        omissions.get("publication_conflict_count"),
        "omissions.publication_conflict_count",
    )
    publication_conflict_reasons = _distribution(
        omissions.get("publication_conflict_reasons"),
        "omissions.publication_conflict_reasons",
    )
    if sum(publication_conflict_reasons.values()) != publication_conflicts:
        raise AuditError("publication conflict reason counts are inconsistent")

    atoms_total = _count(fact.get("atoms_total"), "factreasoner.atoms_total")
    atoms_decided = _count(fact.get("atoms_decided"), "factreasoner.atoms_decided")
    unavailable = _count(fact.get("unavailable_atoms"), "factreasoner.unavailable_atoms")
    outcomes = _distribution(fact.get("atom_outcomes"), "factreasoner.atom_outcomes")
    if atoms_decided != atoms_total or sum(outcomes.values()) != atoms_total:
        raise AuditError("FactReasoner decision counts are inconsistent")
    if outcomes.get("unavailable", 0) != unavailable:
        raise AuditError("FactReasoner unavailable count is inconsistent")
    informative = atoms_total - unavailable

    context_total = _count(risk.get("context_count"), "risk.context_count")
    grounded_contexts = _count(
        risk.get("grounded_context_count"), "risk.grounded_context_count"
    )
    applicability_total = _count(
        risk.get("applicability_total"), "risk.applicability_total"
    )
    applicability_accepted = _count(
        risk.get("applicability_accepted"), "risk.applicability_accepted"
    )
    taxonomy_candidates = _count(
        risk.get("taxonomy_candidate_count"), "risk.taxonomy_candidate_count"
    )
    taxonomy_included = _count(
        risk.get("taxonomy_included_count"), "risk.taxonomy_included_count"
    )

    return {
        "targets": len(targets),
        "successful_targets": _count(aggregate.get("succeeded"), "aggregate.succeeded"),
        "support": {
            "claims_total": claim_total,
            "included": included,
            "withheld": withheld,
            "included_rate": _ratio(included, claim_total),
            "gates": gates,
            "interpretation": (
                "Automated gate dispositions over generated candidates; not human factual-accuracy labels."
            ),
        },
        "assignment_findings": {
            "counts": assignment,
            "candidate_denominator": claim_total,
            "interpretation": (
                "Mechanically detected or withheld candidate conditions, not error prevalence."
            ),
        },
        "omissions": {
            "fields_total": field_total,
            "present": field_present,
            "omitted": field_omitted,
            "abstention_rate": _ratio(field_omitted, field_total),
            "source_present": source_present,
            "source_present_rate": _ratio(source_present, field_total),
            "reasons": _distribution(fields.get("omission_reasons"), "fields.omission_reasons"),
            "interpretation": (
                "Source-present is relative to the frozen candidate inventory, not all public sources."
            ),
        },
        "conflict_visibility": {
            "conflict_fields": core_conflict_fields + publication_conflict_fields,
            "conflict_records": core_conflict_records + publication_conflicts,
            "composition_conflicts": _count(
                omissions.get("composition_conflict_count"),
                "omissions.composition_conflict_count",
            ),
            "publication_conflict_fields": publication_conflict_fields,
            "publication_conflicts": publication_conflicts,
            "publication_conflict_reasons": publication_conflict_reasons,
            "interpretation": (
                "Counts explicit composition and publication conflict records; recall requires an independently labelled conflict universe."
            ),
        },
        "factreasoner": {
            "fields_total": _count(fact.get("fields_total"), "factreasoner.fields_total"),
            "fields_checked": _count(
                fact.get("fields_checked"), "factreasoner.fields_checked"
            ),
            "atoms_total": atoms_total,
            "atoms_decided": atoms_decided,
            "decision_coverage": _ratio(atoms_decided, atoms_total),
            "informative_atoms": informative,
            "informative_coverage": _ratio(informative, atoms_total),
            "source_limited_atoms": _count(
                fact.get("source_limited_atoms"), "factreasoner.source_limited_atoms"
            ),
            "outcomes": outcomes,
            "interpretation": (
                "Decision coverage includes unavailable outcomes; informative coverage excludes them."
            ),
        },
        "risk": {
            "contexts": context_total,
            "grounded_contexts": grounded_contexts,
            "grounded_context_rate": _ratio(grounded_contexts, context_total),
            "taxonomy_candidates": taxonomy_candidates,
            "taxonomy_included": taxonomy_included,
            "taxonomy_inclusion_rate": _ratio(taxonomy_included, taxonomy_candidates),
            "applicability_total": applicability_total,
            "applicability_accepted": applicability_accepted,
            "applicability_acceptance_rate": _ratio(
                applicability_accepted, applicability_total
            ),
            "interpretation": (
                "Automated grounding and applicability dispositions; candidates are not confirmed harms."
            ),
        },
        "warnings": {
            "status": "unavailable_without_complete_labels",
            "precision": None,
            "recall": None,
            "reason": (
                "The quality report has no independently labelled warning/non-warning universe."
            ),
        },
    }


def _target_input_surfaces(report: Mapping[str, Any]) -> dict[str, str | None]:
    output: dict[str, str | None] = {}
    for index, raw in enumerate(_array(report.get("targets"), "quality targets")):
        target = _object(raw, f"quality targets[{index}]")
        request = target.get("request")
        if not isinstance(request, str) or not request or request in output:
            raise AuditError("quality target request is invalid or duplicated")
        if target.get("status") == "failed":
            if target.get("surfaces") is not None:
                raise AuditError("failed quality target claims an input surface")
            output[request] = None
            continue
        surfaces = _object(target.get("surfaces"), "target surfaces")
        digest = surfaces.get("inputs")
        if not isinstance(digest, str) or not _DIGEST_RE.fullmatch(digest):
            raise AuditError("quality target input surface is invalid")
        output[request] = digest
    return output


def _pairing(conditions: Sequence[tuple[str, Mapping[str, Any]]]) -> dict[str, Any]:
    if len(conditions) == 2:
        name_a, report_a = conditions[0]
        name_b, report_b = conditions[1]
        surfaces_a = _target_input_surfaces(report_a)
        surfaces_b = _target_input_surfaces(report_b)
        if set(surfaces_a) != set(surfaces_b):
            raise AuditError("paired conditions do not contain the same target requests")
        mismatches = [
            request
            for request in sorted(surfaces_a)
            if surfaces_a[request] is not None
            and surfaces_b[request] is not None
            and surfaces_a[request] != surfaces_b[request]
        ]
        if mismatches:
            raise AuditError("paired conditions do not share identical frozen input surfaces")
        unavailable = [
            request
            for request in sorted(surfaces_a)
            if surfaces_a[request] is None or surfaces_b[request] is None
        ]
        return {
            "status": (
                "paired_conditions_with_unavailable_input_surfaces"
                if unavailable
                else "paired_identical_frozen_inputs"
            ),
            "conditions": [name_a, name_b],
            "targets": len(surfaces_a),
            "input_surface_matches": len(surfaces_a) - len(unavailable),
            "input_surfaces_unavailable": len(unavailable),
            "interpretation": (
                "Unavailable input surfaces prevent paired deltas."
                if unavailable
                else "Input identity permits paired engineering deltas; it does not provide truth labels."
            ),
        }

    name, report = conditions[0]
    stability = report.get("replay_stability")
    if not isinstance(stability, dict) or stability.get("status") != "compared":
        return {
            "status": "single_condition_no_verified_replay",
            "conditions": [name],
            "targets": len(_target_input_surfaces(report)),
            "input_surface_matches": 0,
            "interpretation": "No paired condition or verified replay was supplied.",
        }
    entries = _array(stability.get("targets"), "replay stability targets")
    input_matches = sum(
        isinstance(entry, dict) and entry.get("inputs") is True for entry in entries
    )
    unavailable = sum(
        isinstance(entry, dict) and entry.get("inputs") is None for entry in entries
    )
    all_stable = (
        stability.get("all_targets_stable") is True
        and stability.get("request_order_stable") is True
        and input_matches + unavailable == len(entries)
    )
    return {
        "status": (
            "paired_replay_with_unavailable_input_surfaces"
            if all_stable and unavailable
            else "paired_replay_identical_frozen_inputs"
            if all_stable
            else "paired_replay_not_fully_stable"
        ),
        "conditions": [name],
        "targets": len(entries),
        "input_surface_matches": input_matches,
        "input_surfaces_unavailable": unavailable,
        "all_output_surfaces_stable": bool(stability.get("all_targets_stable")),
        "interpretation": (
            "Replay includes failed targets without frozen input surfaces; no paired delta is inferred."
            if unavailable
            else "Replay stability measures determinism over frozen inputs, not factual accuracy."
        ),
    }


def _vector(metrics: Mapping[str, Any]) -> dict[str, int]:
    support = _object(metrics["support"], "condition support")
    assignment = _object(metrics["assignment_findings"], "condition assignment")
    omissions = _object(metrics["omissions"], "condition omissions")
    conflicts = _object(metrics["conflict_visibility"], "condition conflicts")
    fact = _object(metrics["factreasoner"], "condition FactReasoner")
    risk = _object(metrics["risk"], "condition risk")
    outcomes = _object(fact["outcomes"], "condition FactReasoner outcomes")
    output = {
        "support.claims_included": support["included"],
        "support.claims_withheld": support["withheld"],
        "omissions.source_present": omissions["source_present"],
        "conflicts.visible_fields": conflicts["conflict_fields"],
        "factreasoner.informative_atoms": fact["informative_atoms"],
        "factreasoner.support": outcomes.get("support", 0),
        "factreasoner.contradiction": outcomes.get("contradiction", 0),
        "factreasoner.neutral": outcomes.get("neutral", 0),
        "factreasoner.unavailable": outcomes.get("unavailable", 0),
        "risk.grounded_contexts": risk["grounded_contexts"],
        "risk.applicability_accepted": risk["applicability_accepted"],
    }
    for code in _CURRENT_FINDING_CODES:
        output[f"assignment.{code}"] = assignment["counts"].get(code, 0)
    return dict(sorted(output.items()))


def _paired_deltas(
    conditions: Sequence[tuple[str, Mapping[str, Any]]],
    metrics: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any] | None:
    if len(conditions) != 2:
        return None
    if any(
        digest is None
        for _, report in conditions
        for digest in _target_input_surfaces(report).values()
    ):
        return None
    name_a, _ = conditions[0]
    name_b, _ = conditions[1]
    vector_a = _vector(metrics[name_a])
    vector_b = _vector(metrics[name_b])
    return {
        "direction": f"{name_b}_minus_{name_a}",
        "count_deltas": {
            key: vector_b[key] - vector_a[key] for key in sorted(vector_a)
        },
        "interpretation": (
            "Mechanical count changes on identical inputs; signs do not imply improvement."
        ),
    }


def _abc_reference(summary: Mapping[str, Any]) -> dict[str, Any]:
    if set(summary) != _ABC_SUMMARY_KEYS:
        raise AuditError("Auto-BenchmarkCards summary has an unexpected closed shape")
    if summary.get("schema_version") != AUTO_BENCHMARKCARDS_SCHEMA_VERSION:
        raise AuditError("Auto-BenchmarkCards summary schema version is unsupported")
    source = _object(summary.get("source_bounded_judge"), "ABC source-bounded judge")
    five = _object(
        source.get("common_denominator_five_state"), "ABC five-state outcomes"
    )
    risk = _object(
        summary.get("candidate_risk_source_judge"), "ABC candidate-risk judge"
    )
    flags = _object(summary.get("validation_flags"), "ABC validation flags")
    screen = _object(summary.get("public_source_screen"), "ABC public-source screen")

    def paper_metric(name: str) -> dict[str, Any]:
        item = _object(five.get(name), f"ABC metric {name}")
        if set(item) != {"value", "ci95", "ci_method", "counts"}:
            raise AuditError(f"ABC metric {name} has an invalid shape")
        value = _probability(item.get("value"), f"ABC metric {name}.value")
        if item.get("ci_method") != "stratified-cluster-bootstrap-percentile":
            raise AuditError(f"ABC metric {name} CI method is unsupported")
        counts = _object(item.get("counts"), f"ABC metric {name}.counts")
        if set(counts) != {"num", "den", "by_stratum"}:
            raise AuditError(f"ABC metric {name}.counts has an invalid shape")
        numerator = _raw_count(counts.get("num"), f"ABC metric {name}.counts.num")
        denominator = _raw_count(counts.get("den"), f"ABC metric {name}.counts.den")
        if numerator > denominator:
            raise AuditError(f"ABC metric {name} numerator exceeds denominator")
        strata = _object(
            counts.get("by_stratum"), f"ABC metric {name}.counts.by_stratum"
        )
        if set(strata) != {"flagged", "unflagged"}:
            raise AuditError(f"ABC metric {name} strata are invalid")
        stratum_totals = [0, 0]
        for stratum_name in ("flagged", "unflagged"):
            stratum = _object(
                strata.get(stratum_name),
                f"ABC metric {name}.counts.by_stratum.{stratum_name}",
            )
            if set(stratum) != {"num", "den"}:
                raise AuditError(f"ABC metric {name} stratum shape is invalid")
            stratum_num = _raw_count(
                stratum.get("num"), f"ABC metric {name}.{stratum_name}.num"
            )
            stratum_den = _raw_count(
                stratum.get("den"), f"ABC metric {name}.{stratum_name}.den"
            )
            if stratum_num > stratum_den:
                raise AuditError(f"ABC metric {name} stratum count is inconsistent")
            stratum_totals[0] += stratum_num
            stratum_totals[1] += stratum_den
        if stratum_totals != [numerator, denominator]:
            raise AuditError(f"ABC metric {name} stratum totals are inconsistent")
        return {
            "value": value,
            "numerator_raw": numerator,
            "denominator_raw": denominator,
            "ci95": _interval(item.get("ci95"), value, f"ABC metric {name}.ci95"),
        }

    if set(five) != set(_ABC_FIVE_STATE_NAMES):
        raise AuditError("Auto-BenchmarkCards five-state outcome set is invalid")
    field_rows = _raw_count(source.get("field_rows"), "ABC field_rows")
    filled_rows = _raw_count(source.get("filled_rows"), "ABC filled_rows")
    not_specified_rows = _raw_count(
        source.get("not_specified_rows"), "ABC not_specified_rows"
    )
    if filled_rows + not_specified_rows != field_rows:
        raise AuditError("Auto-BenchmarkCards field row counts are inconsistent")
    source_rates = {
        name: _probability(source.get(name), f"ABC {name}")
        for name in ("supported_including_eee", "partial", "unsupported")
    }
    if not math.isclose(sum(source_rates.values()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise AuditError("Auto-BenchmarkCards filled-field rates are inconsistent")
    paper_metrics = {name: paper_metric(name) for name in _ABC_FIVE_STATE_NAMES}
    if any(item["denominator_raw"] != field_rows for item in paper_metrics.values()):
        raise AuditError("Auto-BenchmarkCards five-state denominators are inconsistent")
    if sum(item["numerator_raw"] for item in paper_metrics.values()) != field_rows:
        raise AuditError("Auto-BenchmarkCards five-state counts are not exhaustive")

    risk_counts = _object(risk.get("sample_counts"), "ABC candidate-risk counts")
    if set(risk_counts) != {
        "total",
        "relevant_and_grounded",
        "not_relevant_or_not_grounded",
    }:
        raise AuditError("Auto-BenchmarkCards candidate-risk counts are invalid")
    risk_total = _raw_count(risk_counts.get("total"), "ABC risk sample total")
    risk_grounded = _raw_count(
        risk_counts.get("relevant_and_grounded"), "ABC grounded risk count"
    )
    risk_not_grounded = _raw_count(
        risk_counts.get("not_relevant_or_not_grounded"),
        "ABC ungrounded risk count",
    )
    if risk_grounded + risk_not_grounded != risk_total:
        raise AuditError("Auto-BenchmarkCards candidate-risk counts are inconsistent")
    risk_rate = _object(
        risk.get("s_weighted_grounded_rate"), "ABC weighted risk-grounding rate"
    )
    risk_rate_value = _probability(
        risk_rate.get("value"), "ABC weighted risk-grounding rate.value"
    )
    risk_ci95 = _interval(
        risk_rate.get("ci95"),
        risk_rate_value,
        "ABC weighted risk-grounding rate.ci95",
    )
    risk_rate_counts = _object(
        risk_rate.get("counts"), "ABC weighted risk-grounding rate.counts"
    )
    if (
        _raw_count(risk_rate_counts.get("num"), "ABC risk rate numerator")
        != risk_grounded
        or _raw_count(risk_rate_counts.get("den"), "ABC risk rate denominator")
        != risk_total
    ):
        raise AuditError("Auto-BenchmarkCards risk-rate counts are inconsistent")
    if risk.get("human_validated") is not False or risk.get("headline_result") is not False:
        raise AuditError("Auto-BenchmarkCards risk result scope is inconsistent")

    warning_counts = (
        _raw_count(flags.get("n_flagged_fields_raw"), "ABC flagged fields"),
        _raw_count(flags.get("n_unsupported_fields_raw"), "ABC unsupported fields"),
        _raw_count(flags.get("n_overlap_raw"), "ABC warning overlap"),
    )
    if warning_counts[2] > min(warning_counts[:2]):
        raise AuditError("Auto-BenchmarkCards warning overlap is inconsistent")
    warning_precision = _probability(
        flags.get("weighted_precision"), "ABC warning precision"
    )
    warning_recall = _probability(flags.get("weighted_recall"), "ABC warning recall")

    screen_findings = _raw_count(screen.get("n_findings"), "ABC screen findings")
    screen_labels = _object(screen.get("raw_label_counts"), "ABC screen labels")
    if set(screen_labels) != {
        "confirmed-material",
        "confirmed-trivial",
        "not-a-defect",
        "unsure",
    }:
        raise AuditError("Auto-BenchmarkCards screen label set is invalid")
    normalized_screen_labels = {
        name: _raw_count(count, f"ABC screen label {name}")
        for name, count in screen_labels.items()
    }
    if sum(normalized_screen_labels.values()) != screen_findings:
        raise AuditError("Auto-BenchmarkCards screen label counts are inconsistent")
    inference_guard = _array(screen.get("inference_guard"), "ABC inference guard")
    if (
        not inference_guard
        or any(not isinstance(item, str) or not item for item in inference_guard)
        or len(set(inference_guard)) != len(inference_guard)
    ):
        raise AuditError("Auto-BenchmarkCards inference guard is invalid")

    release_signature = {
        "field_rows": field_rows,
        "filled_rows": filled_rows,
        "not_specified_rows": not_specified_rows,
        **source_rates,
        "five_state_counts": {
            name: (
                paper_metrics[name]["numerator_raw"],
                paper_metrics[name]["denominator_raw"],
            )
            for name in _ABC_FIVE_STATE_NAMES
        },
        "five_state_values": {
            name: paper_metrics[name]["value"] for name in _ABC_FIVE_STATE_NAMES
        },
        "five_state_ci95": {
            name: tuple(paper_metrics[name]["ci95"])
            for name in _ABC_FIVE_STATE_NAMES
        },
        "risk_counts": (risk_grounded, risk_not_grounded, risk_total),
        "risk_rate": risk_rate_value,
        "risk_ci95": tuple(risk_ci95),
        "warning_counts": warning_counts,
        "warning_rates": (warning_precision, warning_recall),
        "screen_label_counts": normalized_screen_labels,
        "inference_guard": tuple(inference_guard),
    }
    if release_signature != _ABC_RELEASE_SUMMARY_SIGNATURE:
        raise AuditError("Auto-BenchmarkCards summary does not match the frozen release")

    return {
        "measurement_status": "released_auto_benchmarkcards_results",
        "support": {
            "fully_supported_filled_field_rate": source_rates["supported_including_eee"],
            "partially_supported_filled_field_rate": source_rates["partial"],
            "unsupported_filled_field_rate": source_rates["unsupported"],
            "five_state": paper_metrics,
            "instrument": "automated_source_judge_with_separate_limited_human_assessment",
        },
        "omissions": {
            "source_present_abstention": paper_metrics[
                "not_specified_information_available"
            ],
            "scope": "Relative to evidence supplied to the Auto-BenchmarkCards source judge.",
        },
        "risk": {
            "sample_counts": {
                "total": risk_total,
                "relevant_and_grounded": risk_grounded,
                "not_relevant_or_not_grounded": risk_not_grounded,
            },
            "weighted_grounded_rate": {
                "value": risk_rate_value,
                "ci95": risk_ci95,
                "numerator_raw": risk_grounded,
                "denominator_raw": risk_total,
            },
            "human_validated": False,
            "headline_result": False,
        },
        "warnings": {
            "precision": warning_precision,
            "recall": warning_recall,
            "flagged_fields_raw": warning_counts[0],
            "unsupported_fields_raw": warning_counts[1],
            "overlap_raw": warning_counts[2],
            "reference_labels": "automated_source_judge",
        },
        "screen": {
            "candidate_findings": screen_findings,
            "raw_label_counts": normalized_screen_labels,
            "inference_guard": inference_guard,
        },
        "comparability": (
            "Reference context only: Benchmark Cards and Model Cards have different schemas, "
            "units, sources, sampling designs, and instruments. Rates must not be subtracted."
        ),
    }


def _abc_verifier(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise AuditError("Auto-BenchmarkCards verifier CSV is unavailable") from exc
    digest = hashlib.sha256(raw).hexdigest()
    if digest != AUTO_BENCHMARKCARDS_VERIFIER_SHA256:
        raise AuditError(
            "Auto-BenchmarkCards verifier CSV does not match the frozen release"
        )
    try:
        reader = csv.DictReader(text.splitlines())
        if reader.fieldnames != list(_ABC_VERIFIER_COLUMNS):
            raise AuditError("Auto-BenchmarkCards verifier CSV columns are invalid")
        rows = list(reader)
    except csv.Error as exc:
        raise AuditError("Auto-BenchmarkCards verifier CSV is malformed") from exc
    row_ids: set[str] = set()
    material = Counter()
    label_counts = Counter()
    for row in rows:
        row_id = row["row_id"]
        category = row["category"]
        label = row["verifier_label"]
        if (
            not row_id
            or row_id in row_ids
            or category not in _ABC_SCREEN_CATEGORIES
            or label not in _ABC_VERIFIER_LABELS
        ):
            raise AuditError("Auto-BenchmarkCards verifier row is incomplete or duplicated")
        row_ids.add(row_id)
        label_counts[label] += 1
        if label == "confirmed-material":
            material[category] += 1
    category_counts = Counter(row["category"] for row in rows)
    if (
        len(rows) != 154
        or dict(sorted(category_counts.items())) != _ABC_VERIFIER_CATEGORY_COUNTS
        or dict(sorted(label_counts.items())) != _ABC_VERIFIER_LABEL_COUNTS
        or dict(sorted(material.items())) != _ABC_VERIFIER_MATERIAL_COUNTS
    ):
        raise AuditError(
            "Auto-BenchmarkCards verifier counts do not match the frozen release"
        )
    return (
        {
            "measurement_status": "released_screen_positive_verifier_labels",
            "rows": len(rows),
            "verifier_label_counts": dict(sorted(label_counts.items())),
            "confirmed_material_by_paper_category": dict(sorted(material.items())),
            "scope_guard": (
                "These are verified screen-raised candidates, not a complete defect universe "
                "and not category prevalence."
            ),
        },
        digest,
    )


def _engineering_read(value: Mapping[str, Any]) -> dict[str, Any]:
    if value.get("report_version") != ENGINEERING_READ_VERSION:
        raise AuditError("identical-source engineering-read version is unsupported")
    _verify_embedded_hash(value, "report_sha256", "identical-source engineering read")
    if (
        value.get("status") != "automated_engineering_read_not_human_validated"
        or value.get("independent_model_evaluation") is not False
        or value.get("better_than_auto_benchmarkcards_claimed") is not False
    ):
        raise AuditError("engineering read has unsafe or unsupported result claims")
    targets = _array(value.get("targets"), "engineering-read targets")
    if not targets or not all(
        isinstance(item, dict)
        and isinstance(item.get("source_parity"), dict)
        and item["source_parity"].get("identical") is True
        for item in targets
    ):
        raise AuditError("engineering read does not establish source parity for every target")
    aggregate = _object(value.get("aggregate"), "engineering-read aggregate")
    if aggregate.get("source_parity_passed") is not True:
        raise AuditError("engineering read aggregate does not establish source parity")
    changes = _object(aggregate.get("change_counts"), "engineering-read change counts")
    safe_changes: dict[str, int] = {}
    for key, raw_count in changes.items():
        if not isinstance(key, str) or not _NAME_RE.fullmatch(key):
            raise AuditError("engineering-read change-count key is invalid")
        safe_changes[key] = _count(raw_count, f"engineering-read change count {key}")
    return {
        "status": "automated_engineering_read_not_human_validated",
        "targets": len(targets),
        "source_parity_passed": True,
        "pre_gate_accept_to_reference_withhold": _count(
            aggregate.get("pre_gate_accept_to_reference_withhold"),
            "engineering-read accept-to-withhold count",
        ),
        "change_counts": dict(sorted(safe_changes.items())),
        "independent_model_evaluation": False,
        "interpretation": (
            "Observable disposition changes under source parity; the reference gate is not human truth."
        ),
        "privacy_guard": (
            "Free-text method and limitation fields are intentionally not copied from the local artifact."
        ),
    }


def _label_distribution(items: Iterable[Mapping[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(item[key]) for item in items).items()))


def _target_map_lookup(
    target_map: Mapping[str, Any],
    condition_targets: Mapping[str, set[str]],
) -> dict[str, str]:
    target_map_schema, _digest_receipt = _strict_load(
        Path(__file__).with_name("paired-audit-target-map.schema.json"),
        "paired-audit target-map schema",
    )
    try:
        Draft202012Validator.check_schema(target_map_schema)
        Draft202012Validator(target_map_schema).validate(target_map)
    except (SchemaError, ValidationError) as exc:
        raise AuditError("paired-audit target map violates its JSON Schema") from exc
    if target_map.get("mapping_version") != TARGET_MAP_VERSION:
        raise AuditError("paired-audit target-map version is unsupported")

    expected_sets = tuple(condition_targets.values())
    if not expected_sets or any(targets != expected_sets[0] for targets in expected_sets[1:]):
        raise AuditError("paired-audit conditions do not share one target universe")
    expected_requests = expected_sets[0]
    by_blind_id: dict[str, str] = {}
    seen_requests: set[str] = set()
    for index, raw in enumerate(
        _array(target_map.get("targets"), "paired-audit target-map targets")
    ):
        item = _object(raw, f"paired-audit target-map target {index}")
        blind_id = item.get("target_blind_id")
        request = item.get("target_request")
        if not isinstance(blind_id, str) or not _ITEM_ID_RE.fullmatch(blind_id):
            raise AuditError("paired-audit target blind identifier is invalid")
        if not isinstance(request, str) or not request:
            raise AuditError("paired-audit mapped target request is invalid")
        if blind_id in by_blind_id or request in seen_requests:
            raise AuditError("paired-audit target map is not one-to-one")
        by_blind_id[blind_id] = request
        seen_requests.add(request)
    if seen_requests != expected_requests:
        raise AuditError("paired-audit target map does not exactly cover report targets")
    return by_blind_id


def _labels_metrics(
    labels: Mapping[str, Any] | None,
    condition_targets: Mapping[str, set[str]],
    target_map: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if labels is None:
        if target_map is not None:
            raise AuditError("paired-audit target map requires a labels record")
        return {
            "status": "not_supplied",
            "human_results_present": False,
            "warning_precision_recall_available": False,
        }
    labels_schema, _digest_receipt = _strict_load(
        Path(__file__).with_name("paired-audit-labels.schema.json"),
        "paired-audit labels schema",
    )
    try:
        Draft202012Validator.check_schema(labels_schema)
        Draft202012Validator(labels_schema).validate(labels)
    except (SchemaError, ValidationError) as exc:
        raise AuditError("paired-audit labels violate their JSON Schema") from exc
    if labels.get("labels_version") != LABELS_VERSION:
        raise AuditError("paired-audit labels version is unsupported")
    status = labels.get("study_status")
    if status not in {
        "design_only_no_human_results",
        "annotation_in_progress",
        "annotation_complete",
    }:
        raise AuditError("paired-audit labels study status is invalid")
    items = _array(labels.get("items"), "paired-audit label items")
    confirmation = _object(
        labels.get("annotator_confirmation"), "paired-audit annotator confirmation"
    )
    target_lookup = (
        None
        if target_map is None
        else _target_map_lookup(target_map, condition_targets)
    )
    if status != "annotation_complete":
        if items:
            raise AuditError("incomplete annotation record cannot contain scored items")
        return {
            "status": status,
            "human_results_present": False,
            "warning_precision_recall_available": False,
        }
    if labels.get("blinded") is not True:
        raise AuditError("complete paired labels must confirm blinded annotation")
    if (
        confirmation.get("completed") is not True
        or confirmation.get("used_only_displayed_evidence") is not True
    ):
        raise AuditError("complete paired labels lack annotator confirmation")
    if not items:
        raise AuditError("complete paired labels contain no items")
    if target_lookup is None:
        raise AuditError("complete paired labels require a private target map")

    required = {
        "item_id",
        "target_blind_id",
        "condition",
        "support",
        "source_binding",
        "entity_checkpoint",
        "relation",
        "field_fit",
        "score_row",
        "omission",
        "conflict_visibility",
        "risk_grounding",
        "risk_applicability",
        "warning_present",
        "actionable_error",
    }
    seen: set[tuple[str, str, str]] = set()
    by_condition: dict[str, list[dict[str, Any]]] = {
        name: [] for name in condition_targets
    }
    by_condition_target: dict[str, dict[str, list[dict[str, Any]]]] = {
        name: {blind_id: [] for blind_id in target_lookup}
        for name in condition_targets
    }
    for index, raw in enumerate(items):
        item = _object(raw, f"paired-audit labels item {index}")
        if set(item) != required:
            raise AuditError("paired-audit label item has an invalid closed shape")
        condition = item["condition"]
        if condition not in by_condition:
            raise AuditError("paired-audit label names an unknown condition")
        if not isinstance(item["item_id"], str) or not _ITEM_ID_RE.fullmatch(
            item["item_id"]
        ):
            raise AuditError("paired-audit item_id is invalid")
        blind_id = item["target_blind_id"]
        if not isinstance(blind_id, str) or blind_id not in target_lookup:
            raise AuditError("paired-audit label names an unknown target blind identifier")
        if target_lookup[blind_id] not in condition_targets[condition]:
            raise AuditError(
                "paired-audit mapped target is absent from its frozen condition"
            )
        identity = (condition, blind_id, item["item_id"])
        if identity in seen:
            raise AuditError("paired-audit label item is duplicated")
        seen.add(identity)
        for key, allowed in _LABEL_ENUMS.items():
            if item[key] not in allowed:
                raise AuditError(f"paired-audit {key} label is invalid")
        if not isinstance(item["warning_present"], bool):
            raise AuditError("paired-audit warning_present must be boolean")
        by_condition[condition].append(item)
        by_condition_target[condition][blind_id].append(item)

    for condition, targets in by_condition_target.items():
        if any(not target_items for target_items in targets.values()):
            raise AuditError(
                f"complete paired labels do not cover every target in condition {condition}"
            )
    condition_names = tuple(by_condition_target)
    if len(condition_names) == 2:
        left, right = condition_names
        for blind_id in target_lookup:
            left_ids = {
                item["item_id"] for item in by_condition_target[left][blind_id]
            }
            right_ids = {
                item["item_id"] for item in by_condition_target[right][blind_id]
            }
            if left_ids != right_ids:
                raise AuditError(
                    "complete paired labels do not share a matching item universe"
                )

    condition_metrics: dict[str, Any] = {}
    warning_precision_recall_available = False
    for condition, condition_items in by_condition.items():
        decided_warning = [
            item
            for item in condition_items
            if item["actionable_error"] in {"yes", "no"}
        ]
        tp = sum(
            item["warning_present"] and item["actionable_error"] == "yes"
            for item in decided_warning
        )
        fp = sum(
            item["warning_present"] and item["actionable_error"] == "no"
            for item in decided_warning
        )
        fn = sum(
            not item["warning_present"] and item["actionable_error"] == "yes"
            for item in decided_warning
        )
        tn = sum(
            not item["warning_present"] and item["actionable_error"] == "no"
            for item in decided_warning
        )
        precision_denominator = tp + fp
        recall_denominator = tp + fn
        precision_available = precision_denominator > 0
        recall_available = recall_denominator > 0
        warning_precision_recall_available = (
            warning_precision_recall_available
            or (precision_available and recall_available)
        )
        condition_metrics[condition] = {
            "items": len(condition_items),
            "support": _label_distribution(condition_items, "support"),
            "source_binding": _label_distribution(
                condition_items, "source_binding"
            ),
            "entity_checkpoint": _label_distribution(
                condition_items, "entity_checkpoint"
            ),
            "relation": _label_distribution(condition_items, "relation"),
            "field_fit": _label_distribution(condition_items, "field_fit"),
            "score_row": _label_distribution(condition_items, "score_row"),
            "omission": _label_distribution(condition_items, "omission"),
            "conflict_visibility": _label_distribution(
                condition_items, "conflict_visibility"
            ),
            "risk_grounding": _label_distribution(condition_items, "risk_grounding"),
            "risk_applicability": _label_distribution(
                condition_items, "risk_applicability"
            ),
            "warning": {
                "labelled_universe": len(decided_warning),
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "true_negative": tn,
                "precision_available": precision_available,
                "recall_available": recall_available,
                "precision": _ratio(tp, precision_denominator),
                "recall": _ratio(tp, recall_denominator),
            },
        }
    return {
        "status": "completed_blinded_annotations",
        "human_results_present": True,
        "warning_precision_recall_available": warning_precision_recall_available,
        "targets": len(target_lookup),
        "conditions": condition_metrics,
        "scope_guard": (
            "Metrics describe only the supplied labelled universe; sampling and agreement "
            "must be reported separately."
        ),
    }


def _crosswalk() -> list[dict[str, Any]]:
    return [
        {
            "auto_benchmarkcards_category": "wrong-section-splice",
            "model_cards_measures": list(_CURRENT_FINDING_CODES),
            "relationship": "broad_overlap_not_equivalent",
            "note": (
                "The paper label combines wrong field, benchmark component, metadata, and "
                "score-layer errors; current codes are narrower mechanical findings."
            ),
        },
        {
            "auto_benchmarkcards_category": "fabricated-fact",
            "model_cards_measures": ["value_support", "factreasoner_outcomes"],
            "relationship": "proxy_only",
            "note": (
                "Gate withholding or contradiction is not a human determination that a fact is fabricated."
            ),
        },
        {
            "auto_benchmarkcards_category": "thin",
            "model_cards_measures": ["source_present_omissions", "abstentions"],
            "relationship": "closest_mechanical_analogue",
            "note": "Both remain relative to the evidence inventory each system examined.",
        },
        {
            "auto_benchmarkcards_category": "wrong-identity",
            "model_cards_measures": ["wrong_entity", "wrong_checkpoint"],
            "relationship": "partial_overlap",
            "note": "A blinded reviewer is needed to establish an actual identity error.",
        },
        {
            "auto_benchmarkcards_category": "wrong-paper",
            "model_cards_measures": ["source_present_omissions"],
            "relationship": "no_exact_current_code",
            "note": "The current audit has no complete independently labelled paper universe.",
        },
        {
            "auto_benchmarkcards_category": "other",
            "model_cards_measures": ["source_present_omissions", "conflict_visibility"],
            "relationship": "not_comparable",
            "note": "The paper residual category cannot be reconstructed from aggregate Model Card metrics.",
        },
    ]


def build_audit(
    conditions: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    auto_benchmarkcards_summary: Mapping[str, Any] | None = None,
    auto_benchmarkcards_verifier: Mapping[str, Any] | None = None,
    engineering_read: Mapping[str, Any] | None = None,
    labels: Mapping[str, Any] | None = None,
    target_map: Mapping[str, Any] | None = None,
    input_receipts: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not 1 <= len(conditions) <= 2:
        raise AuditError("audit requires one or two Model Card conditions")
    names = [name for name, _ in conditions]
    if len(names) != len(set(names)) or any(not _NAME_RE.fullmatch(name) for name in names):
        raise AuditError("condition names must be unique safe identifiers")
    canonical_conditions: list[tuple[str, Mapping[str, Any]]] = []
    for name, report in conditions:
        try:
            canonical_report = QualityReport.from_dict(report).to_dict()
        except QualityReportError as exc:
            raise AuditError(f"condition {name} is not a canonical quality report") from exc
        canonical_conditions.append((name, canonical_report))
    conditions = tuple(canonical_conditions)
    condition_metrics = {name: _quality_metrics(report) for name, report in conditions}
    pairing = _pairing(conditions)
    condition_targets = {
        name: set(_target_input_surfaces(report)) for name, report in conditions
    }
    label_metrics = _labels_metrics(labels, condition_targets, target_map)
    payload: dict[str, Any] = {
        "report_version": AUDIT_VERSION,
        "status": (
            "automated_audit_with_completed_blinded_labels"
            if label_metrics["human_results_present"]
            else "automated_audit_no_new_human_labels"
        ),
        "claims_of_superiority": False,
        "system_output_human_reviewed": False,
        "input_receipts": dict(input_receipts or {}),
        "pairing": pairing,
        "model_cards_conditions": condition_metrics,
        "paired_deltas": _paired_deltas(conditions, condition_metrics),
        "auto_benchmarkcards_reference": (
            None
            if auto_benchmarkcards_summary is None
            else _abc_reference(auto_benchmarkcards_summary)
        ),
        "auto_benchmarkcards_verifier_categories": (
            None
            if auto_benchmarkcards_verifier is None
            else dict(auto_benchmarkcards_verifier)
        ),
        "identical_source_engineering_read": (
            None if engineering_read is None else _engineering_read(engineering_read)
        ),
        "human_labels": label_metrics,
        "category_crosswalk": _crosswalk(),
        "measurable_now": [
            "automated claim-gate dispositions",
            "mechanically detected entity/checkpoint/relation/field/score-row findings",
            "frozen-inventory omissions and explicit conflict records",
            "FactReasoner coverage and outcome distributions",
            "risk grounding/mapping/applicability dispositions",
            "replay stability and identical-input engineering deltas",
            "warning precision/recall only when a complete labelled warning/non-warning universe is supplied",
        ],
        "needs_blinded_human_annotation": [
            "factual support and source binding",
            "actual wrong entity, checkpoint, relation, field, or score row",
            "omissions beyond the frozen candidate inventory",
            "conflict-detection recall and reviewer usefulness",
            "risk grounding, applicability, and publisher attribution",
            "warning precision and recall on a protocol-fixed item universe",
        ],
        "scope_guards": [
            "Auto-BenchmarkCards rates and Model Cards rates use different units and must not be subtracted.",
            "A gate pass is not a human truth label, and a gate failure is not a confirmed defect.",
            "Zero findings can mean zero triggered checks; it does not establish zero errors.",
            "Risk candidates are review prompts, not confirmed harms or publisher-reported facts.",
            "The audit makes no better-than or released claim and does not imply full-system human review.",
        ],
    }
    payload["report_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
    return payload


def _parse_condition(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise AuditError("condition must use NAME=QUALITY_REPORT.json")
    name, path_text = value.split("=", 1)
    if not _NAME_RE.fullmatch(name) or not path_text:
        raise AuditError("condition name or path is invalid")
    return name, Path(path_text)


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise AuditError("refusing to overwrite an existing audit output")
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = _canonical(value) + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o644)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise AuditError("audit output appeared concurrently") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare privacy-safe Model Card audit metrics with the released "
            "Auto-BenchmarkCards failure taxonomy, entirely offline."
        )
    )
    parser.add_argument(
        "--condition",
        action="append",
        required=True,
        metavar="NAME=QUALITY_REPORT.json",
        help="one or two Model Card quality reports",
    )
    parser.add_argument("--auto-benchmarkcards-summary")
    parser.add_argument("--auto-benchmarkcards-verifier-labels")
    parser.add_argument("--identical-source-engineering-read")
    parser.add_argument("--labels", help="optional completed blinded labels or empty template")
    parser.add_argument(
        "--target-map",
        help="private opaque target-ID to quality-report request mapping",
    )
    parser.add_argument("--output", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        parsed = [_parse_condition(value) for value in args.condition]
        if not 1 <= len(parsed) <= 2 or len({name for name, _ in parsed}) != len(parsed):
            raise AuditError("supply one or two uniquely named conditions")
        conditions: list[tuple[str, Mapping[str, Any]]] = []
        receipts: dict[str, Any] = {}
        for name, path in parsed:
            report, digest = _strict_load(path, f"condition {name}")
            conditions.append((name, report))
            receipts[f"condition_{name}"] = {"sha256": digest}

        abc_summary = None
        if args.auto_benchmarkcards_summary:
            abc_summary, digest = _strict_load(
                Path(args.auto_benchmarkcards_summary), "Auto-BenchmarkCards summary"
            )
            if digest != AUTO_BENCHMARKCARDS_SUMMARY_SHA256:
                raise AuditError(
                    "Auto-BenchmarkCards summary does not match the frozen release"
                )
            receipts["auto_benchmarkcards_summary"] = {"sha256": digest}

        abc_verifier = None
        if args.auto_benchmarkcards_verifier_labels:
            abc_verifier, digest = _abc_verifier(
                Path(args.auto_benchmarkcards_verifier_labels)
            )
            receipts["auto_benchmarkcards_verifier_labels"] = {"sha256": digest}

        engineering = None
        if args.identical_source_engineering_read:
            engineering, digest = _strict_load(
                Path(args.identical_source_engineering_read),
                "identical-source engineering read",
            )
            receipts["identical_source_engineering_read"] = {"sha256": digest}

        labels = None
        if args.labels:
            labels, digest = _strict_load(Path(args.labels), "paired-audit labels")
            receipts["paired_audit_labels"] = {"sha256": digest}

        target_map = None
        if args.target_map:
            target_map, digest = _strict_load(
                Path(args.target_map), "paired-audit target map"
            )
            receipts["paired_audit_target_map"] = {"sha256": digest}

        result = build_audit(
            conditions,
            auto_benchmarkcards_summary=abc_summary,
            auto_benchmarkcards_verifier=abc_verifier,
            engineering_read=engineering,
            labels=labels,
            target_map=target_map,
            input_receipts=receipts,
        )
        _write_new(Path(args.output), result)
        print(
            json.dumps(
                {
                    "report_sha256": result["report_sha256"],
                    "status": result["status"],
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except AuditError as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
