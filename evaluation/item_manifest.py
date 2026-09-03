#!/usr/bin/env python3
"""Build immutable private evaluation manifests and blinded reviewer packets.

The builder consumes already-produced, typed pipeline artifacts.  It does not
read source bodies or call a provider.  Exact target identities, native record
identifiers, artifact digests, source digests, and evidence coordinates remain
in the private manifest.  Reviewer packets contain HMAC-derived identifiers,
redacted bounded values/evidence, and categorical pipeline dispositions only.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, ValidationError

from model_cards.claim_gate import ClaimGateRecord
from model_cards.factreasoner import FactReasonerRecord
from model_cards.family_risk import FamilyRiskAuthorizationReport
from model_cards.findings import OmissionAudit
from model_cards.models import TaxonomyRiskDerivation
from model_cards.pipeline import PipelineRepairReport, PipelineResult, RiskStageSummary
from model_cards.publication_validation import PublicationValidationReport
from model_cards.quality_report import _source_input_surface, _treatment_surface
from model_cards.risk_mapping import RiskMappingReport, UseContext
from model_cards.run_state import RunStore
from model_cards.source_state import SourceStateMode, load_source_state


ITEM_MANIFEST_VERSION = "model-card-evaluation-item-manifest/v1"
REVIEWER_PACKET_VERSION = "model-card-reviewer-packet/v2"
TARGET_SHEET_VERSION = "model-card-reviewer-target-sheet/v1"
LABELS_VERSION = "model-card-paired-audit-labels/v2"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_RE = re.compile(r"^[a-z][a-z0-9-]{7,127}$")
_CONDITION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
_ABSOLUTE_PATH_RE = re.compile(
    r"(?:/(?:Users|home|private|var|tmp)/[^\s\"'<>]+|[A-Za-z]:\\[^\s\"'<>]+)"
)
_SOURCE_URL_RE = re.compile(
    r"(?:https?://[^\s\"'<>]+|hf://[^\s\"'<>]+|doi:[^\s\"'<>]+)",
    re.IGNORECASE,
)
_REQUIRED_ARTIFACTS = (
    "claim-gates.json",
    "factreasoner-content.json",
    "factreasoner-original.json",
    "factreasoner-publication-original.json",
    "factreasoner.json",
    "family-risk-authorizations.json",
    "omissions.json",
    "pipeline-result.json",
    "publication-validation.json",
    "repairs.json",
    "risk-mapping.json",
)
_KIND_ORDER = {"claim": 0, "field": 1, "risk": 2, "warning": 3}
_SEMANTIC_LABEL_FIELDS = frozenset(
    {
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
        "actionable_error",
    }
)
_KIND_LABEL_FIELDS = {
    "claim": frozenset(
        {"support", "source_binding", "entity_checkpoint", "relation", "field_fit"}
    ),
    "field": frozenset({"omission", "conflict_visibility"}),
    "risk": frozenset({"risk_grounding", "risk_applicability"}),
    "warning": frozenset({"actionable_error"}),
}


class ItemManifestError(ValueError):
    """Evaluation inputs, bindings, or blinded outputs are invalid."""


@dataclass(frozen=True)
class ConditionRun:
    condition: str
    target_blind_id: str
    run_root: Path


@dataclass(frozen=True)
class _LoadedRun:
    spec: ConditionRun
    pipeline: PipelineResult
    gates: tuple[ClaimGateRecord, ...]
    fact_phases: Mapping[str, FactReasonerRecord]
    omissions: OmissionAudit
    publication: PublicationValidationReport
    repairs: PipelineRepairReport
    family_authorization: FamilyRiskAuthorizationReport
    risk_summary: RiskStageSummary
    contexts: tuple[UseContext, ...]
    risk_mapping: RiskMappingReport
    risk_derivations: tuple[TaxonomyRiskDerivation, ...]
    artifact_values: Mapping[str, Mapping[str, Any]]
    artifact_sha256: Mapping[str, str]
    pipeline_result_sha256: str
    source_input_surface_sha256: str
    treatment_surface_sha256: str


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
        raise ItemManifestError("evaluation value is not finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _strict_load(path: Path, label: str) -> tuple[dict[str, Any], str]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ItemManifestError(f"{label} contains duplicate keys")
            result[key] = value
        return result

    def nonfinite(value: str) -> None:
        raise ItemManifestError(f"{label} contains non-finite number {value}")

    if path.is_symlink() or not path.is_file():
        raise ItemManifestError(f"{label} must be a regular non-symlink file")
    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=nonfinite,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ItemManifestError(f"{label} is unavailable or invalid JSON") from exc
    if not isinstance(value, dict):
        raise ItemManifestError(f"{label} root must be an object")
    return value, hashlib.sha256(raw).hexdigest()


def _typed(value: Mapping[str, Any], loader: Any, label: str) -> Any:
    try:
        return loader.from_dict(value)
    except (TypeError, ValueError) as exc:
        raise ItemManifestError(f"{label} failed typed integrity validation") from exc


def _artifact_ref(pipeline: PipelineResult, filename: str) -> str:
    matches = [
        item.artifact_sha256 for item in pipeline.artifacts if item.filename == filename
    ]
    if len(matches) != 1:
        raise ItemManifestError(f"pipeline result does not bind {filename} exactly once")
    return matches[0]


def _load_run(spec: ConditionRun) -> _LoadedRun:
    if not _CONDITION_RE.fullmatch(spec.condition):
        raise ItemManifestError("condition name is invalid")
    if not _OPAQUE_RE.fullmatch(spec.target_blind_id):
        raise ItemManifestError("target blind identifier is invalid")
    root = Path(spec.run_root)
    if root.is_symlink() or not root.is_dir():
        raise ItemManifestError("condition run root must be a regular directory")
    raw: dict[str, Mapping[str, Any]] = {}
    digests: dict[str, str] = {}
    for filename in _REQUIRED_ARTIFACTS:
        value, digest = _strict_load(root / filename, filename)
        raw[filename] = value
        digests[filename] = digest

    pipeline = _typed(raw["pipeline-result.json"], PipelineResult, "pipeline result")
    for filename in _REQUIRED_ARTIFACTS:
        if filename == "pipeline-result.json":
            continue
        if _artifact_ref(pipeline, filename) != digests[filename]:
            raise ItemManifestError(f"{filename} differs from its pipeline binding")

    try:
        store = RunStore.open(root)
        run_manifest = store.manifest
        source_state_value, _source_state_file_sha256 = _strict_load(
            root / "source-state.json", "source state"
        )
        state_mode = source_state_value.get("mode")
        if state_mode == SourceStateMode.HF_AND_OFFICIAL.value:
            official_directory: Path | None = root / "official-source-bundle"
        elif state_mode == SourceStateMode.HF_ONLY.value:
            official_directory = None
        else:
            raise ItemManifestError("source state mode is unsupported")
        source_state = load_source_state(
            root / "source-bundle",
            official_bundle_directory=official_directory,
        )
    except ItemManifestError:
        raise
    except Exception as exc:
        raise ItemManifestError(
            "condition run state failed exact receipt replay"
        ) from exc
    if (
        run_manifest.run_id != pipeline.run_id
        or run_manifest.target != pipeline.target
        or run_manifest.source_bundle_id != pipeline.source_bundle_id
        or run_manifest.source_manifest_sha256 != pipeline.source_manifest_sha256
        or source_state.to_dict() != source_state_value
        or source_state.target != pipeline.target
        or source_state.active_catalog_bundle_id != pipeline.source_bundle_id
        or source_state.snapshot_sha256 != pipeline.source_manifest_sha256
        or source_state.active_catalog_sha256 != pipeline.source_catalog_sha256
    ):
        raise ItemManifestError(
            "condition run/source receipts differ from the pipeline result"
        )
    source_input_surface_sha256 = _source_input_surface(
        result=pipeline,
        source_state=source_state,
    )
    treatment_surface_sha256 = _treatment_surface(run_manifest.configuration)

    gate_rows = raw["claim-gates.json"].get("records")
    if not isinstance(gate_rows, list):
        raise ItemManifestError("claim gate records must be an array")
    gates = tuple(_typed(item, ClaimGateRecord, "claim gate record") for item in gate_rows)
    if [item.candidate.candidate_id for item in gates] != sorted(
        item.candidate.candidate_id for item in gates
    ):
        raise ItemManifestError("claim gate records are not canonical")
    pipeline_claims = {item.candidate_id: item for item in pipeline.claims}
    if set(pipeline_claims) != {item.candidate.candidate_id for item in gates}:
        raise ItemManifestError("claim gate inventory differs from pipeline result")
    for gate in gates:
        reference = pipeline_claims[gate.candidate.candidate_id]
        if (
            reference.candidate_sha256 != gate.candidate.content_sha256
            or reference.gate_record_sha256 != gate.content_sha256
            or reference.projection_eligible != gate.projection_eligible
        ):
            raise ItemManifestError("claim gate record differs from pipeline reference")

    phase_files = {
        "original": "factreasoner-original.json",
        "content": "factreasoner-content.json",
        "publication_original": "factreasoner-publication-original.json",
        "final": "factreasoner.json",
    }
    phases = {
        phase: _typed(raw[filename], FactReasonerRecord, f"{phase} FactReasoner")
        for phase, filename in phase_files.items()
    }
    omissions = _typed(raw["omissions.json"], OmissionAudit, "omission audit")
    publication = _typed(
        raw["publication-validation.json"],
        PublicationValidationReport,
        "publication validation",
    )
    repairs = _typed(raw["repairs.json"], PipelineRepairReport, "repair report")
    family_authorization = _typed(
        raw["family-risk-authorizations.json"],
        FamilyRiskAuthorizationReport,
        "family risk authorization report",
    )

    risk_raw = raw["risk-mapping.json"]
    expected_risk_keys = {
        "factreasoner_withheld_derivation_ids",
        "summary",
        "taxonomy_derivations",
        "taxonomy_mapping",
        "use_contexts",
    }
    if set(risk_raw) != expected_risk_keys:
        raise ItemManifestError("risk mapping artifact has an invalid closed shape")
    if not all(
        isinstance(risk_raw[name], list)
        for name in ("taxonomy_derivations", "use_contexts")
    ) or not isinstance(risk_raw["factreasoner_withheld_derivation_ids"], list):
        raise ItemManifestError("risk mapping arrays are malformed")
    risk_summary = _typed(risk_raw["summary"], RiskStageSummary, "risk summary")
    contexts = tuple(
        _typed(item, UseContext, "risk use context") for item in risk_raw["use_contexts"]
    )
    risk_mapping = _typed(
        risk_raw["taxonomy_mapping"], RiskMappingReport, "taxonomy risk mapping"
    )
    risk_derivations = tuple(
        _typed(item, TaxonomyRiskDerivation, "taxonomy risk derivation")
        for item in risk_raw["taxonomy_derivations"]
    )

    target = pipeline.target
    typed_targets = [
        *(item.candidate.target for item in gates),
        *(record.target for record in phases.values()),
        repairs.target,
        family_authorization.target,
        *(item.target for item in risk_derivations),
    ]
    if any(item != target for item in typed_targets):
        raise ItemManifestError("condition artifacts do not share one exact target")
    gate_by_id = {item.candidate.candidate_id: item for item in gates}
    family_embedded_gates = [*family_authorization.family_gates]
    if family_authorization.membership_gate is not None:
        family_embedded_gates.append(family_authorization.membership_gate)
    if any(
        gate_by_id.get(item.candidate.candidate_id) != item
        for item in family_embedded_gates
    ):
        raise ItemManifestError(
            "family authorization gates differ from the claim-gate inventory"
        )
    context_by_id = {item.context_id: item for item in contexts}
    if any(
        context_by_id.get(item.context.context_id) != item.context
        for item in family_authorization.use_contexts
    ):
        raise ItemManifestError(
            "family authorization contexts differ from the risk input inventory"
        )
    if phases["content"].content_sha256 != pipeline.content_factreasoner_sha256:
        raise ItemManifestError("content FactReasoner binding is stale")
    if phases["original"].content_sha256 != repairs.original_factreasoner_sha256:
        raise ItemManifestError("original FactReasoner binding is stale")
    if (
        phases["publication_original"].content_sha256
        != pipeline.publication_original_factreasoner_sha256
        or phases["final"].content_sha256 != pipeline.factreasoner_sha256
        or publication.content_sha256 != pipeline.publication_validation_sha256
        or omissions.content_sha256 != pipeline.omission_audit_sha256
        or repairs.post_repair_composition_sha256 != pipeline.composition_sha256
        or risk_summary.to_dict() != pipeline.risk.to_dict()
    ):
        raise ItemManifestError("condition artifact chain differs from pipeline result")
    if risk_mapping.report_sha256 != risk_summary.mapping_report_sha256:
        raise ItemManifestError("taxonomy mapping differs from risk summary")
    if tuple(risk_raw["factreasoner_withheld_derivation_ids"]) != (
        repairs.factreasoner_withheld_derivation_ids
    ):
        raise ItemManifestError("risk and repair FactReasoner withholding differ")

    return _LoadedRun(
        spec=ConditionRun(spec.condition, spec.target_blind_id, root),
        pipeline=pipeline,
        gates=gates,
        fact_phases=phases,
        omissions=omissions,
        publication=publication,
        repairs=repairs,
        family_authorization=family_authorization,
        risk_summary=risk_summary,
        contexts=contexts,
        risk_mapping=risk_mapping,
        risk_derivations=risk_derivations,
        artifact_values=raw,
        artifact_sha256=digests,
        pipeline_result_sha256=pipeline.result_sha256,
        source_input_surface_sha256=source_input_surface_sha256,
        treatment_surface_sha256=treatment_surface_sha256,
    )


def _opaque(key: bytes, prefix: str, value: str) -> str:
    digest = hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{prefix}-{digest[:24]}"


def _target_value(run: _LoadedRun) -> dict[str, str]:
    return run.pipeline.target.to_dict()


def _target_request(run: _LoadedRun) -> str:
    target = run.pipeline.target
    return f"{target.model_id}@{target.revision}"


def _resolve_pointer(value: Any, pointer: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ItemManifestError("artifact record JSON Pointer is invalid")
    current = value
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                raise ItemManifestError("artifact record JSON Pointer is unresolved")
            current = current[token]
        elif isinstance(current, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", token):
                raise ItemManifestError("artifact record JSON Pointer index is invalid")
            index = int(token)
            if index >= len(current):
                raise ItemManifestError("artifact record JSON Pointer is unresolved")
            current = current[index]
        else:
            raise ItemManifestError("artifact record JSON Pointer is unresolved")
    return current


def _file_binding(
    run: _LoadedRun, filename: str, pointer: str, record: Any
) -> dict[str, str]:
    artifact = run.artifact_values.get(filename)
    if artifact is None:
        raise ItemManifestError("artifact record file is outside the sealed run")
    resolved = _resolve_pointer(artifact, pointer)
    if _canonical(resolved) != _canonical(record):
        raise ItemManifestError("artifact record differs from its JSON Pointer")
    record_digest = _digest(record)
    return {
        "artifact_name": filename,
        "artifact_sha256": run.artifact_sha256[filename],
        "json_pointer": pointer,
        "record_sha256": record_digest,
    }


def _evidence_binding(key: bytes, evidence: Mapping[str, Any]) -> dict[str, Any]:
    source_uri = evidence.get("source_uri")
    source_revision = evidence.get("source_revision")
    kind = evidence.get("kind")
    if not isinstance(source_uri, str) or not isinstance(source_revision, str):
        raise ItemManifestError("claim evidence lacks source identity")
    if kind == "quote":
        fragment = evidence.get("quote")
        coordinate = {
            "char_start": evidence.get("char_start"),
            "char_end": evidence.get("char_end"),
            "json_pointer": None,
            "section_path": evidence.get("section_path", []),
            "table_id": evidence.get("table_id"),
        }
    elif kind == "structured":
        fragment = evidence.get("fragment")
        coordinate = {
            "char_start": None,
            "char_end": None,
            "json_pointer": evidence.get("pointer"),
            "section_path": evidence.get("section_path", []),
            "table_id": evidence.get("table_id"),
        }
    else:
        raise ItemManifestError("claim evidence kind is invalid")
    identity = _digest(
        {
            "source_id": evidence.get("source_id"),
            "source_sha256": evidence.get("source_sha256"),
            "coordinate": coordinate,
            "fragment_sha256": _digest(fragment),
        }
    )
    return {
        "evidence_id": _opaque(key, "evidence", identity),
        "evidence_sha256": _digest(evidence),
        "source_id": evidence.get("source_id"),
        "source_sha256": evidence.get("source_sha256"),
        "source_revision_sha256": hashlib.sha256(source_revision.encode()).hexdigest(),
        "source_uri_sha256": hashlib.sha256(source_uri.encode()).hexdigest(),
        "kind": kind,
        "coordinate": coordinate,
        "fragment_sha256": _digest(fragment),
    }


def _evidence_for_candidate(key: bytes, candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    evidence = candidate.get("evidence")
    if not isinstance(evidence, list):
        raise ItemManifestError("claim candidate evidence must be an array")
    return [_evidence_binding(key, item) for item in evidence]


def _fact_binding(run: _LoadedRun, field_path: str) -> dict[str, Any]:
    phases: list[dict[str, Any]] = []
    for phase, record in run.fact_phases.items():
        coverage = next(
            (item for item in record.field_coverage if item.field_path == field_path), None
        )
        field_decision = next(
            (item for item in record.field_decisions if item.field_path == field_path), None
        )
        if coverage is None:
            continue
        atom_ids = list(coverage.atom_ids)
        decisions = [item for item in record.decisions if item.atom_id in set(atom_ids)]
        phases.append(
            {
                "phase": phase,
                "record_sha256": record.content_sha256,
                "coverage_status": coverage.status.value,
                "field_action": (
                    None if field_decision is None else field_decision.action.value
                ),
                "outcomes": [item.outcome.value for item in decisions],
                "atom_decision_sha256s": [item.content_sha256 for item in decisions],
            }
        )
    return {"phases": phases}


def _repair_binding(run: _LoadedRun, field_path: str, candidate_id: str | None) -> dict[str, Any]:
    # Field-audit subjects can cover several candidate lineages.  Their repair
    # outcomes remain exhaustive as separate candidate-specific claim/repair
    # subjects; do not collapse several predecessors into one misleading field
    # disposition.
    if candidate_id is None:
        return {
            "status": "not_applicable",
            "predecessor_candidate_sha256": None,
            "selected_candidate_sha256": None,
            "record_sha256": None,
        }
    matches = [
        item
        for item in run.repairs.records
        if item.context.field_path == field_path
        and item.context.predecessor_candidate_id == candidate_id
    ]
    if len(matches) > 1:
        raise ItemManifestError("repair report has ambiguous field/candidate lineage")
    if not matches:
        return {
            "status": "not_applicable",
            "predecessor_candidate_sha256": None,
            "selected_candidate_sha256": None,
            "record_sha256": None,
        }
    record = matches[0]
    return {
        "status": record.outcome.value,
        "predecessor_candidate_sha256": record.context.predecessor_candidate_sha256,
        "selected_candidate_sha256": record.selected_candidate_sha256,
        "record_sha256": record.content_sha256,
    }


def _empty_disposition() -> dict[str, Any]:
    return {
        "state": "absent",
        "reason": "condition_did_not_emit_subject",
        "warning_present": False,
        "gate_decisions": [],
        "factreasoner": {"phases": []},
        "repair": {
            "status": "not_applicable",
            "predecessor_candidate_sha256": None,
            "selected_candidate_sha256": None,
            "record_sha256": None,
        },
    }


def _condition_subjects(run: _LoadedRun, key: bytes) -> dict[str, dict[str, Any]]:
    subjects: dict[str, dict[str, Any]] = {}
    gate_by_id = {item.candidate.candidate_id: item for item in run.gates}

    def put(subject_key: str, value: dict[str, Any]) -> None:
        if subject_key in subjects:
            raise ItemManifestError("condition emitted a duplicate evaluation subject")
        value["native_sha256s"] = sorted(
            set(value["native_sha256s"])
            | {
                binding["record_sha256"]
                for binding in value["artifact_bindings"]
            }
        )
        subjects[subject_key] = value

    for index, gate in enumerate(run.gates):
        candidate = gate.candidate.to_dict()
        candidate_id = gate.candidate.candidate_id
        reference = next(
            item for item in run.pipeline.claims if item.candidate_id == candidate_id
        )
        decision_values = [item.to_dict() for item in gate.decisions]
        warning = any(item["status"] == "withheld" for item in decision_values)
        artifacts = [
            _file_binding(
                run,
                "claim-gates.json",
                f"/records/{index}",
                gate.to_dict(),
            )
        ]
        evidence = _evidence_for_candidate(key, candidate)
        disposition = {
            "state": "included" if reference.included else "withheld",
            "reason": "projection_included" if reference.included else "projection_withheld",
            "warning_present": warning,
            "gate_decisions": [
                {
                    "gate": item["gate"],
                    "status": item["status"],
                    "reason": item["reason"],
                    "decision_sha256": item["decision_sha256"],
                }
                for item in decision_values
            ],
            "factreasoner": _fact_binding(run, gate.candidate.field_path),
            "repair": _repair_binding(run, gate.candidate.field_path, candidate_id),
        }
        put(
            f"claim:{candidate_id}",
            {
                "item_kind": "claim",
                "field_path": gate.candidate.field_path,
                "native_ids": [candidate_id],
                "native_sha256s": [gate.candidate.content_sha256, gate.content_sha256],
                "display_value": candidate["value"],
                "artifact_bindings": artifacts,
                "evidence_bindings": evidence,
                "_native_evidence": candidate["evidence"],
                "disposition": disposition,
            },
        )
        for decision_index, decision in enumerate(decision_values):
            put(
                f"warning:claim_gate:{candidate_id}:{decision['gate']}",
                {
                    "item_kind": "warning",
                    "field_path": gate.candidate.field_path,
                    "native_ids": [candidate_id, decision["gate"]],
                    "native_sha256s": [decision["decision_sha256"]],
                    "display_value": {
                        "warning_type": "claim_gate",
                        "gate": decision["gate"],
                        "reason": decision["reason"],
                    },
                    "artifact_bindings": [
                        _file_binding(
                            run,
                            "claim-gates.json",
                            f"/records/{index}/decisions/{decision_index}",
                            decision,
                        )
                    ],
                    "evidence_bindings": evidence,
                    "_native_evidence": candidate["evidence"],
                    "disposition": {
                        **_empty_disposition(),
                        "state": decision["status"],
                        "reason": decision["reason"],
                        "warning_present": decision["status"] == "withheld",
                    },
                },
            )

    for stage, filename, records in (
        ("content", "omissions.json", run.omissions.records),
        ("publication", "publication-validation.json", run.publication.records),
    ):
        for index, record in enumerate(records):
            value = record.to_dict()
            field_path = record.field_path
            candidate_ids = list(value.get("candidate_ids", []))
            candidate_evidence = [
                evidence
                for candidate_id in candidate_ids
                if candidate_id in gate_by_id
                for evidence in _evidence_for_candidate(
                    key, gate_by_id[candidate_id].candidate.to_dict()
                )
            ]
            native_evidence = [
                evidence
                for candidate_id in candidate_ids
                if candidate_id in gate_by_id
                for evidence in gate_by_id[candidate_id].candidate.to_dict()["evidence"]
            ]
            state = value.get("status", value.get("reason"))
            reason = value.get("reason") or "present"
            warning = state not in {"present"}
            binding = _file_binding(run, filename, f"/records/{index}", value)
            repair = _repair_binding(run, field_path, None)
            put(
                f"field:{stage}:{field_path}",
                {
                    "item_kind": "field",
                    "field_path": field_path,
                    "native_ids": [field_path, stage],
                    "native_sha256s": [value["record_sha256"]],
                    # The primary reviewer must infer source presence and omission
                    # from the displayed evidence.  Candidate counts and the
                    # pipeline's source-present flag would disclose the answer.
                    "display_value": {"stage": stage},
                    "artifact_bindings": [binding],
                    "evidence_bindings": candidate_evidence,
                    "_native_evidence": native_evidence,
                    "disposition": {
                        "state": state,
                        "reason": reason,
                        "warning_present": warning,
                        "gate_decisions": [],
                        "factreasoner": _fact_binding(run, field_path),
                        "repair": repair,
                    },
                },
            )
            put(
                f"warning:field:{stage}:{field_path}",
                {
                    "item_kind": "warning",
                    "field_path": field_path,
                    "native_ids": [field_path, stage],
                    "native_sha256s": [value["record_sha256"]],
                    "display_value": {
                        "warning_type": "field_audit",
                        "stage": stage,
                        "reason": reason,
                    },
                    "artifact_bindings": [binding],
                    "evidence_bindings": candidate_evidence,
                    "_native_evidence": native_evidence,
                    "disposition": {
                        **_empty_disposition(),
                        "state": state,
                        "reason": reason,
                        "warning_present": warning,
                    },
                },
            )

    derivation_by_risk = {
        str(item.value["risk_id"]): item for item in run.risk_derivations
    }
    risk_decision_by_id = {
        item.candidate_id: item for item in run.risk_mapping.decisions
    }
    family_authorization_by_candidate = {
        item.candidate.candidate_id: (index, item)
        for index, item in enumerate(run.family_authorization.authorizations)
    }
    family_decision_by_candidate = {
        item.family_candidate_id: (index, item)
        for index, item in enumerate(
            run.family_authorization.applicability_decisions
        )
    }
    context_by_id = {item.context_id: item for item in run.contexts}
    if len(context_by_id) != len(run.contexts):
        raise ItemManifestError("risk input inventory contains duplicate contexts")
    family_context_by_sha256 = {
        item.context.context_sha256: (index, item)
        for index, item in enumerate(run.family_authorization.use_contexts)
    }
    if len(family_context_by_sha256) != len(
        run.family_authorization.use_contexts
    ):
        raise ItemManifestError("family risk authorization contexts are ambiguous")
    for index, candidate in enumerate(run.risk_mapping.candidates):
        decision = risk_decision_by_id[candidate.candidate_id]
        derivation = derivation_by_risk.get(candidate.risk_id)
        artifacts = [
            _file_binding(
                run,
                "risk-mapping.json",
                f"/taxonomy_mapping/candidates/{index}",
                candidate.to_dict(),
            ),
            _file_binding(
                run,
                "risk-mapping.json",
                f"/taxonomy_mapping/decisions/{index}",
                decision.to_dict(),
            ),
        ]
        native_sha = [candidate.candidate_sha256, decision.decision_sha256]
        evidence: list[dict[str, Any]] = []
        native_evidence: list[Mapping[str, Any]] = []

        try:
            selected_contexts = tuple(
                context_by_id[context_id] for context_id in candidate.context_ids
            )
        except KeyError as exc:
            raise ItemManifestError(
                "risk candidate references an unavailable use context"
            ) from exc
        supporting_candidate_ids = sorted(
            {
                candidate_id
                for context in selected_contexts
                for candidate_id in context.supporting_candidate_ids
            }
        )
        if tuple(sorted(candidate.source_refs)) != tuple(
            sorted(
                {
                    source_ref
                    for context in selected_contexts
                    for source_ref in context.source_refs
                }
            )
        ):
            raise ItemManifestError(
                "risk candidate source refs differ from its use contexts"
            )
        for candidate_id in supporting_candidate_ids:
            gate = gate_by_id.get(candidate_id)
            if gate is None:
                raise ItemManifestError(
                    "risk use context references a claim outside the gate inventory"
                )
            candidate_value = gate.candidate.to_dict()
            evidence.extend(_evidence_for_candidate(key, candidate_value))
            native_evidence.extend(candidate_value["evidence"])

        family_inputs = {
            candidate_id
            for candidate_id in supporting_candidate_ids
            if candidate_id in family_authorization_by_candidate
        }
        selected_family_contexts = [
            family_context_by_sha256[context.context_sha256]
            for context in selected_contexts
            if context.context_sha256 in family_context_by_sha256
        ]
        covered_authorizations = {
            authorization_sha256
            for _context_index, family_context in selected_family_contexts
            for authorization_sha256 in family_context.authorization_sha256s
        }
        expected_authorizations = {
            family_authorization_by_candidate[candidate_id][1].authorization_sha256
            for candidate_id in family_inputs
        }
        if family_inputs and (
            not selected_family_contexts
            or not expected_authorizations.issubset(covered_authorizations)
        ):
            raise ItemManifestError(
                "family-derived risk lacks its authorized use-context chain"
            )
        for context_index, family_context in selected_family_contexts:
            artifacts.append(
                _file_binding(
                    run,
                    "family-risk-authorizations.json",
                    f"/use_contexts/{context_index}",
                    family_context.to_dict(),
                )
            )
            native_sha.append(family_context.record_sha256)
        for candidate_id in sorted(family_inputs):
            authorization_index, authorization = family_authorization_by_candidate[
                candidate_id
            ]
            decision_entry = family_decision_by_candidate.get(candidate_id)
            if decision_entry is None:
                raise ItemManifestError(
                    "family-derived risk lacks its applicability decision"
                )
            decision_index, applicability = decision_entry
            if applicability.decision_sha256 != (
                authorization.applicability.decision_sha256
            ):
                raise ItemManifestError(
                    "family authorization and applicability decision differ"
                )
            artifacts.extend(
                (
                    _file_binding(
                        run,
                        "family-risk-authorizations.json",
                        f"/applicability_decisions/{decision_index}",
                        applicability.to_dict(),
                    ),
                    _file_binding(
                        run,
                        "family-risk-authorizations.json",
                        f"/authorizations/{authorization_index}",
                        authorization.to_dict(),
                    ),
                )
            )
            native_sha.extend(
                (
                    applicability.decision_sha256,
                    authorization.authorization_sha256,
                )
            )

        if derivation is not None:
            derivation_index = run.risk_derivations.index(derivation)
            if (
                derivation.risk_candidate_id != candidate.candidate_id
                or derivation.risk_candidate_sha256 != candidate.candidate_sha256
                or derivation.applicability_decision_sha256
                != decision.decision_sha256
                or set(derivation.context_sha256s)
                != {context.context_sha256 for context in selected_contexts}
                or {item.candidate_id for item in derivation.input_claims}
                != set(supporting_candidate_ids)
            ):
                raise ItemManifestError(
                    "risk derivation differs from its candidate use-context chain"
                )
            artifacts.append(
                _file_binding(
                    run,
                    "risk-mapping.json",
                    f"/taxonomy_derivations/{derivation_index}",
                    derivation.to_dict(),
                )
            )
            native_sha.append(derivation.content_sha256)
        withheld_by_fact = bool(
            derivation is not None
            and derivation.derivation_id
            in set(run.repairs.factreasoner_withheld_derivation_ids)
        )
        state = "factreasoner_withheld" if withheld_by_fact else decision.status.value
        value = {
            "risk_id": candidate.risk_id,
            "name": candidate.name,
            "description": candidate.description,
        }
        put(
            f"risk:{candidate.risk_id}",
            {
                "item_kind": "risk",
                "field_path": None,
                "native_ids": [candidate.candidate_id, candidate.risk_id],
                "native_sha256s": native_sha,
                "display_value": value,
                "artifact_bindings": artifacts,
                "evidence_bindings": evidence,
                "_native_evidence": native_evidence,
                "disposition": {
                    **_empty_disposition(),
                    "state": state,
                    "reason": decision.reason,
                    "warning_present": state != "accepted",
                },
            },
        )
        put(
            f"warning:risk:{candidate.risk_id}",
            {
                "item_kind": "warning",
                "field_path": None,
                "native_ids": [candidate.candidate_id, candidate.risk_id],
                "native_sha256s": native_sha,
                "display_value": {
                    "warning_type": "risk_applicability",
                    "risk_id": candidate.risk_id,
                    "reason": decision.reason,
                },
                "artifact_bindings": artifacts,
                "evidence_bindings": evidence,
                "_native_evidence": native_evidence,
                "disposition": {
                    **_empty_disposition(),
                    "state": state,
                    "reason": decision.reason,
                    "warning_present": state != "accepted",
                },
            },
        )

    for index, record in enumerate(run.repairs.records):
        value = record.to_dict()
        candidate_id = record.context.predecessor_candidate_id
        evidence = (
            []
            if candidate_id not in gate_by_id
            else _evidence_for_candidate(
                key, gate_by_id[candidate_id].candidate.to_dict()
            )
        )
        native_evidence = (
            []
            if candidate_id not in gate_by_id
            else gate_by_id[candidate_id].candidate.to_dict()["evidence"]
        )
        put(
            f"warning:repair:{candidate_id}",
            {
                "item_kind": "warning",
                "field_path": record.context.field_path,
                "native_ids": [candidate_id],
                "native_sha256s": [record.content_sha256],
                "display_value": {
                    "warning_type": "repair",
                    "outcome": record.outcome.value,
                    "reason": record.reason.value,
                    "attempts": len(record.attempts),
                },
                "artifact_bindings": [
                    _file_binding(
                        run,
                        "repairs.json",
                        f"/records/{index}",
                        value,
                    )
                ],
                "evidence_bindings": evidence,
                "_native_evidence": native_evidence,
                "disposition": {
                    **_empty_disposition(),
                    "state": record.outcome.value,
                    "reason": record.reason.value,
                    "warning_present": record.outcome.value == "withheld",
                    "repair": _repair_binding(
                        run, record.context.field_path, candidate_id
                    ),
                },
            },
        )
    return subjects


def _redaction_tokens(target: Mapping[str, str]) -> list[tuple[str, str]]:
    model_id = target["model_id"]
    revision = target["revision"]
    pieces = [piece for piece in model_id.split("/") if len(piece) >= 3]
    values = [(f"{model_id}@{revision}", "[target]")]
    values.append((model_id, "[target]"))
    values.append((revision, "[revision]"))
    for index, piece in enumerate(reversed(pieces)):
        values.append((piece, "[target]" if index == 0 else "[publisher]"))
    return sorted(values, key=lambda item: len(item[0]), reverse=True)


def _redact_text(value: str, target: Mapping[str, str]) -> str:
    output = value
    for token, replacement in _redaction_tokens(target):
        pattern = re.escape(token)
        if token in target["model_id"].split("/"):
            pattern = rf"(?<![A-Za-z0-9]){pattern}(?![A-Za-z0-9])"
        output = re.sub(pattern, replacement, output, flags=re.IGNORECASE)
    output = _ABSOLUTE_PATH_RE.sub("[local-path]", output)
    return _SOURCE_URL_RE.sub("[source-url]", output)


def _redact(value: Any, target: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return _redact_text(value, target)
    if isinstance(value, list):
        return [_redact(item, target) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item, target) for key, item in value.items()}
    return value


def _public_evidence(
    key: bytes,
    candidate_evidence: Iterable[Mapping[str, Any]],
    target: Mapping[str, str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for evidence in candidate_evidence:
        private = _evidence_binding(key, evidence)
        if private["evidence_id"] in seen:
            continue
        seen.add(private["evidence_id"])
        fragment = evidence.get("quote") if evidence.get("kind") == "quote" else evidence.get("fragment")
        if not isinstance(fragment, str):
            fragment = _canonical(fragment).decode("utf-8")
        output.append(
            {
                "evidence_id": private["evidence_id"],
                "kind": private["kind"],
                "excerpt": _redact_text(fragment[:1200], target),
                "coordinate_kind": (
                    "character_range" if private["kind"] == "quote" else "json_pointer"
                ),
            }
        )
    return output


def _tasks(kind: str) -> list[str]:
    return {
        "claim": ["claim_support", "assignment"],
        "field": ["omission", "conflict_visibility"],
        "risk": ["risk_applicability"],
        "warning": ["warning_utility"],
    }[kind]


def _packet_payload(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "packet_version": packet["packet_version"],
        "study_unit_id": packet["study_unit_id"],
        "condition": packet["condition"],
        "target_blind_id": packet["target_blind_id"],
        "target_sheet_sha256": packet["target_sheet_sha256"],
        "phase": packet["phase"],
        "randomization_sha256": packet["randomization_sha256"],
        "items": packet["items"],
        "privacy": packet["privacy"],
    }


def build_evaluation_material(
    runs: Sequence[ConditionRun],
    *,
    study_unit_id: str,
    blinding_key: bytes,
) -> tuple[
    dict[str, Any],
    dict[tuple[str, str, str], dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    """Return one sealed manifest and phased packets per target/condition."""

    if not _OPAQUE_RE.fullmatch(study_unit_id):
        raise ItemManifestError("study unit identifier is invalid")
    if not isinstance(blinding_key, bytes) or len(blinding_key) < 32:
        raise ItemManifestError("blinding key must contain at least 32 bytes")
    loaded = tuple(_load_run(item) for item in runs)
    if not loaded:
        raise ItemManifestError("at least one condition run is required")
    identities = [(item.spec.target_blind_id, item.spec.condition) for item in loaded]
    if len(identities) != len(set(identities)):
        raise ItemManifestError("condition run identity is duplicated")
    conditions = tuple(sorted({item.spec.condition for item in loaded}))
    if conditions not in {("A",), ("A", "B")}:
        raise ItemManifestError(
            "reviewer packets require condition A alone or exact conditions A and B"
        )
    target_ids = tuple(sorted({item.spec.target_blind_id for item in loaded}))
    for blind_id in target_ids:
        target_runs = [item for item in loaded if item.spec.target_blind_id == blind_id]
        if tuple(sorted(item.spec.condition for item in target_runs)) != conditions:
            raise ItemManifestError(
                "every blinded target must cover the declared condition universe"
            )
        first = target_runs[0].pipeline
        first_source_surface = target_runs[0].source_input_surface_sha256
        for current in target_runs[1:]:
            if (
                current.pipeline.target != first.target
                or current.pipeline.source_bundle_id != first.source_bundle_id
                or current.pipeline.source_manifest_sha256 != first.source_manifest_sha256
                or current.pipeline.source_catalog_sha256 != first.source_catalog_sha256
                or current.source_input_surface_sha256 != first_source_surface
            ):
                raise ItemManifestError(
                    "paired conditions do not share the exact frozen target and sources"
                )

    subject_maps = {
        (item.spec.target_blind_id, item.spec.condition): _condition_subjects(
            item, blinding_key
        )
        for item in loaded
    }
    manifest_items: list[dict[str, Any]] = []
    packet_items: dict[tuple[str, str], list[dict[str, Any]]] = {
        (blind_id, condition): []
        for blind_id in target_ids
        for condition in conditions
    }
    run_lookup = {
        (item.spec.target_blind_id, item.spec.condition): item for item in loaded
    }
    for blind_id in target_ids:
        union = sorted(
            set().union(
                *(set(subject_maps[(blind_id, condition)]) for condition in conditions)
            ),
            key=lambda key: (
                _KIND_ORDER[
                    next(
                        subject_maps[(blind_id, condition)][key]["item_kind"]
                        for condition in conditions
                        if key in subject_maps[(blind_id, condition)]
                    )
                ],
                key,
            ),
        )
        target = _target_value(run_lookup[(blind_id, conditions[0])])
        for semantic_key in union:
            present_values = [
                subject_maps[(blind_id, condition)][semantic_key]
                for condition in conditions
                if semantic_key in subject_maps[(blind_id, condition)]
            ]
            kinds = {item["item_kind"] for item in present_values}
            fields = {item["field_path"] for item in present_values}
            if len(kinds) != 1 or len(fields) != 1:
                raise ItemManifestError("paired semantic subject changed kind or field")
            kind = next(iter(kinds))
            field_path = next(iter(fields))
            semantic_digest = _digest(
                {
                    "target_sha256": _digest(target),
                    "semantic_key": semantic_key,
                    "item_kind": kind,
                    "field_path": field_path,
                }
            )
            item_id = _opaque(blinding_key, "item", semantic_digest)
            condition_values: list[dict[str, Any]] = []
            native_ids = sorted(
                {entry for item in present_values for entry in item["native_ids"]}
            )
            native_hashes = sorted(
                {entry for item in present_values for entry in item["native_sha256s"]}
            )
            for condition in conditions:
                value = subject_maps[(blind_id, condition)].get(semantic_key)
                if value is None:
                    condition_values.append(
                        {
                            "condition": condition,
                            "present": False,
                            "disposition": _empty_disposition(),
                            "artifact_bindings": [],
                            "evidence_bindings": [],
                        }
                    )
                    continue
                condition_values.append(
                    {
                        "condition": condition,
                        "present": True,
                        "disposition": value["disposition"],
                        "artifact_bindings": value["artifact_bindings"],
                        "evidence_bindings": value["evidence_bindings"],
                    }
                )
                display = _redact(value["display_value"], target)
                public_evidence = _public_evidence(
                    blinding_key, value.get("_native_evidence", []), target
                )
                disposition = value["disposition"]
                packet_items[(blind_id, condition)].append(
                    {
                        "item_id": item_id,
                        "item_kind": kind,
                        "tasks": _tasks(kind),
                        "field_path": field_path,
                        "display_value": display,
                        "evidence": public_evidence,
                        "_warning_presentation": {
                            "state": disposition["state"],
                            "warning_present": disposition["warning_present"],
                        },
                    }
                )
            manifest_items.append(
                {
                    "item_id": item_id,
                    "target_blind_id": blind_id,
                    "item_kind": kind,
                    "semantic_key_sha256": semantic_digest,
                    "subject": {
                        "field_path": field_path,
                        "native_ids": native_ids,
                        "native_sha256s": native_hashes,
                    },
                    "conditions": condition_values,
                }
            )

    target_sheets: dict[str, dict[str, Any]] = {}
    for blind_id in target_ids:
        target = _target_value(run_lookup[(blind_id, conditions[0])])
        sheet: dict[str, Any] = {
            "sheet_version": TARGET_SHEET_VERSION,
            "study_unit_id": study_unit_id,
            "target_blind_id": blind_id,
            "exact_target": target,
            "assignment_instruction": (
                "Use this exact model ID and immutable revision when judging entity, "
                "checkpoint, and relation assignment. Do not infer facts from model memory."
            ),
        }
        sheet["sheet_sha256"] = _digest(sheet)
        target_sheets[blind_id] = sheet

    packets: dict[tuple[str, str, str], dict[str, Any]] = {}
    reviewer_hashes: dict[tuple[str, str], dict[str, str]] = {}
    privacy = {
        "target_identity_in_controlled_sheet": True,
        "treatment_identity_removed": True,
        "source_paths_removed": True,
        "source_uris_removed": True,
    }
    for (blind_id, condition), items in packet_items.items():
        reviewer_hashes[(blind_id, condition)] = {}
        for phase, selected in (
            ("primary", [item for item in items if item["item_kind"] != "warning"]),
            (
                "warning_followup",
                [item for item in items if item["item_kind"] == "warning"],
            ),
        ):
            packet_values = []
            for item in selected:
                public_item = {
                    key: value for key, value in item.items() if not key.startswith("_")
                }
                if phase == "warning_followup":
                    public_item["warning_presentation"] = item[
                        "_warning_presentation"
                    ]
                packet_values.append(public_item)
            packet_values.sort(
                key=lambda item: hmac.new(
                    blinding_key,
                    (
                        f"packet-order:{study_unit_id}:{blind_id}:{condition}:"
                        f"{phase}:{item['item_id']}"
                    ).encode("utf-8"),
                    hashlib.sha256,
                ).hexdigest()
            )
            randomization_sha = _digest([item["item_id"] for item in packet_values])
            packet = {
                "packet_version": REVIEWER_PACKET_VERSION,
                "study_unit_id": study_unit_id,
                "condition": condition,
                "target_blind_id": blind_id,
                "target_sheet_sha256": target_sheets[blind_id]["sheet_sha256"],
                "phase": phase,
                "randomization_sha256": randomization_sha,
                "item_manifest_sha256": None,
                "items": packet_values,
                "privacy": privacy,
            }
            payload_sha = _digest(_packet_payload(packet))
            packet["payload_sha256"] = payload_sha
            reviewer_hashes[(blind_id, condition)][phase] = payload_sha
            packets[(blind_id, condition, phase)] = packet

    target_records = []
    inventory = []
    for blind_id in target_ids:
        target_runs = [item for item in loaded if item.spec.target_blind_id == blind_id]
        first = target_runs[0]
        condition_artifacts = []
        for run in sorted(target_runs, key=lambda item: item.spec.condition):
            artifacts = [
                {"artifact_name": name, "artifact_sha256": run.artifact_sha256[name]}
                for name in sorted(run.artifact_sha256)
            ]
            condition_artifacts.append(
                {
                    "condition": run.spec.condition,
                    "pipeline_result_sha256": run.pipeline_result_sha256,
                    "source_input_surface_sha256": (
                        run.source_input_surface_sha256
                    ),
                    "treatment_surface_sha256": run.treatment_surface_sha256,
                    "run_identity_sha256": _digest(
                        {
                            "pipeline_result_sha256": run.pipeline.result_sha256,
                            "source_input_surface_sha256": (
                                run.source_input_surface_sha256
                            ),
                            "treatment_surface_sha256": (
                                run.treatment_surface_sha256
                            ),
                            "artifacts": artifacts,
                        }
                    ),
                    "reviewer_payload_sha256s": reviewer_hashes[
                        (blind_id, run.spec.condition)
                    ],
                    "artifacts": artifacts,
                }
            )
            entries = subject_maps[(blind_id, run.spec.condition)].values()
            inventory.append(
                {
                    "target_blind_id": blind_id,
                    "condition": run.spec.condition,
                    "claims": sum(item["item_kind"] == "claim" for item in entries),
                    "fields": sum(item["item_kind"] == "field" for item in entries),
                    "risks": sum(item["item_kind"] == "risk" for item in entries),
                    "warnings": sum(item["item_kind"] == "warning" for item in entries),
                    "repairs": len(run.repairs.records),
                }
            )
        target_records.append(
            {
                "target_blind_id": blind_id,
                "target_request": _target_request(first),
                "target_sha256": _digest(_target_value(first)),
                "target_sheet_sha256": target_sheets[blind_id]["sheet_sha256"],
                "frozen_inputs": {
                    "source_bundle_id_sha256": hashlib.sha256(
                        first.pipeline.source_bundle_id.encode()
                    ).hexdigest(),
                    "source_manifest_sha256": first.pipeline.source_manifest_sha256,
                    "source_catalog_sha256": first.pipeline.source_catalog_sha256,
                },
                "condition_artifacts": condition_artifacts,
            }
        )

    manifest: dict[str, Any] = {
        "manifest_version": ITEM_MANIFEST_VERSION,
        "study_unit_id": study_unit_id,
        "conditions": list(conditions),
        "blinding_key_sha256": hashlib.sha256(blinding_key).hexdigest(),
        "targets": target_records,
        "items": manifest_items,
        "inventory": inventory,
    }
    manifest["manifest_sha256"] = _digest(manifest)
    for packet in packets.values():
        packet["item_manifest_sha256"] = manifest["manifest_sha256"]
    validate_item_manifest(manifest)
    for sheet in target_sheets.values():
        validate_target_sheet(sheet, manifest)
    for packet in packets.values():
        validate_reviewer_packet(packet, manifest)
    return manifest, packets, target_sheets


def _schema(filename: str) -> dict[str, Any]:
    value, _ = _strict_load(Path(__file__).with_name(filename), filename)
    return value


def validate_item_manifest(value: Mapping[str, Any]) -> None:
    schema = _schema("item-manifest.schema.json")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)
    except (SchemaError, ValidationError) as exc:
        raise ItemManifestError("item manifest violates its JSON Schema") from exc
    if value.get("manifest_version") != ITEM_MANIFEST_VERSION:
        raise ItemManifestError("item manifest version is unsupported")
    expected = value.get("manifest_sha256")
    payload = dict(value)
    payload.pop("manifest_sha256", None)
    if expected != _digest(payload):
        raise ItemManifestError("item manifest digest does not match its content")
    conditions = value["conditions"]
    if conditions not in (["A"], ["A", "B"]):
        raise ItemManifestError("item manifest condition universe is invalid")
    targets = {item["target_blind_id"] for item in value["targets"]}
    if len(targets) != len(value["targets"]):
        raise ItemManifestError("item manifest target IDs are duplicated")
    artifact_inventory: dict[tuple[str, str], dict[str, str]] = {}
    for target in value["targets"]:
        try:
            model_id, revision = target["target_request"].rsplit("@", 1)
        except ValueError as exc:
            raise ItemManifestError("item manifest target request is malformed") from exc
        if (
            not model_id
            or not re.fullmatch(r"[0-9a-f]{40}", revision)
            or target["target_sha256"]
            != _digest({"model_id": model_id, "revision": revision})
        ):
            raise ItemManifestError("item manifest exact target binding is stale")
        target_conditions = [
            item["condition"] for item in target["condition_artifacts"]
        ]
        if target_conditions != conditions:
            raise ItemManifestError(
                "item manifest target does not cover every declared condition"
            )
        for condition in target["condition_artifacts"]:
            key = (target["target_blind_id"], condition["condition"])
            artifacts = condition["artifacts"]
            by_name = {item["artifact_name"]: item["artifact_sha256"] for item in artifacts}
            if len(by_name) != len(artifacts) or set(by_name) != set(_REQUIRED_ARTIFACTS):
                raise ItemManifestError("item manifest artifact inventory is not exact")
            expected_run_identity = _digest(
                {
                    "pipeline_result_sha256": condition[
                        "pipeline_result_sha256"
                    ],
                    "source_input_surface_sha256": condition[
                        "source_input_surface_sha256"
                    ],
                    "treatment_surface_sha256": condition[
                        "treatment_surface_sha256"
                    ],
                    "artifacts": artifacts,
                }
            )
            if condition["run_identity_sha256"] != expected_run_identity:
                raise ItemManifestError(
                    "item manifest condition run identity is stale"
                )
            artifact_inventory[key] = by_name
    seen: set[tuple[str, str]] = set()
    expected_inventory = {(target, condition) for target in targets for condition in conditions}
    for item in value["items"]:
        identity = (item["target_blind_id"], item["item_id"])
        if identity in seen or item["target_blind_id"] not in targets:
            raise ItemManifestError("item manifest item identity is invalid or duplicated")
        seen.add(identity)
        item_conditions = [entry["condition"] for entry in item["conditions"]]
        if item_conditions != conditions:
            raise ItemManifestError("item manifest item does not cover every condition")
        for condition in item["conditions"]:
            artifacts = artifact_inventory[(item["target_blind_id"], condition["condition"])]
            if any(
                binding["artifact_name"] not in artifacts
                or binding["artifact_sha256"] != artifacts[binding["artifact_name"]]
                for binding in condition["artifact_bindings"]
            ):
                raise ItemManifestError("item artifact binding is outside its sealed run")
            if not condition["present"] and (
                condition["artifact_bindings"] or condition["evidence_bindings"]
            ):
                raise ItemManifestError("absent item retains condition artifacts")
            if condition["present"] and any(
                binding["record_sha256"]
                not in item["subject"]["native_sha256s"]
                for binding in condition["artifact_bindings"]
            ):
                raise ItemManifestError(
                    "item record receipt is outside its native hash inventory"
                )
    inventory_ids = {
        (item["target_blind_id"], item["condition"]) for item in value["inventory"]
    }
    if inventory_ids != expected_inventory or len(inventory_ids) != len(value["inventory"]):
        raise ItemManifestError("item manifest inventory coverage is incomplete")
    for inventory in value["inventory"]:
        counts = {kind: 0 for kind in _KIND_ORDER}
        for item in value["items"]:
            if item["target_blind_id"] != inventory["target_blind_id"]:
                continue
            condition = next(
                entry
                for entry in item["conditions"]
                if entry["condition"] == inventory["condition"]
            )
            if condition["present"]:
                counts[item["item_kind"]] += 1
        if any(
            inventory[name] != counts[kind]
            for name, kind in (
                ("claims", "claim"),
                ("fields", "field"),
                ("risks", "risk"),
                ("warnings", "warning"),
            )
        ):
            raise ItemManifestError("item manifest inventory counts are stale")


def validate_reviewer_packet(
    packet: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    validate_item_manifest(manifest)
    schema = _schema("reviewer-packet.schema.json")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(packet)
    except (SchemaError, ValidationError) as exc:
        raise ItemManifestError("reviewer packet violates its JSON Schema") from exc
    if packet.get("item_manifest_sha256") != manifest["manifest_sha256"]:
        raise ItemManifestError("reviewer packet names another item manifest")
    if packet.get("payload_sha256") != _digest(_packet_payload(packet)):
        raise ItemManifestError("reviewer packet payload digest is stale")
    target = next(
        (
            item
            for item in manifest["targets"]
            if item["target_blind_id"] == packet["target_blind_id"]
        ),
        None,
    )
    if target is None:
        raise ItemManifestError("reviewer packet target is absent from item manifest")
    if packet.get("target_sheet_sha256") != target["target_sheet_sha256"]:
        raise ItemManifestError("reviewer packet names another controlled target sheet")
    condition_record = next(
        (
            item
            for item in target["condition_artifacts"]
            if item["condition"] == packet["condition"]
        ),
        None,
    )
    if (
        condition_record is None
        or condition_record["reviewer_payload_sha256s"].get(packet["phase"])
        != packet["payload_sha256"]
    ):
        raise ItemManifestError("reviewer packet is not bound by its condition manifest")
    expected_items = {
        item["item_id"]
        for item in manifest["items"]
        if item["target_blind_id"] == packet["target_blind_id"]
        and next(
            entry["present"]
            for entry in item["conditions"]
            if entry["condition"] == packet["condition"]
        )
        and (
            (packet["phase"] == "primary" and item["item_kind"] != "warning")
            or (
                packet["phase"] == "warning_followup"
                and item["item_kind"] == "warning"
            )
        )
    }
    packet_ids = [item["item_id"] for item in packet["items"]]
    if len(packet_ids) != len(set(packet_ids)) or set(packet_ids) != expected_items:
        raise ItemManifestError("reviewer packet item universe is not exhaustive")
    if packet["randomization_sha256"] != _digest(packet_ids):
        raise ItemManifestError("reviewer packet randomization receipt is stale")
    for item in packet["items"]:
        if item["tasks"] != _tasks(item["item_kind"]):
            raise ItemManifestError("reviewer packet item tasks do not match its kind")
        if packet["phase"] == "primary":
            if item["item_kind"] == "warning" or "warning_presentation" in item:
                raise ItemManifestError(
                    "primary packet exposes warning-stage information"
                )
        elif (
            item["item_kind"] != "warning"
            or "warning_presentation" not in item
        ):
            raise ItemManifestError(
                "warning follow-up packet is missing its manifest-derived presentation"
            )
        if packet["phase"] == "warning_followup":
            manifest_item = next(
                entry
                for entry in manifest["items"]
                if entry["target_blind_id"] == packet["target_blind_id"]
                and entry["item_id"] == item["item_id"]
            )
            binding = next(
                entry
                for entry in manifest_item["conditions"]
                if entry["condition"] == packet["condition"]
            )
            expected_presentation = {
                "state": binding["disposition"]["state"],
                "warning_present": binding["disposition"]["warning_present"],
            }
            if item["warning_presentation"] != expected_presentation:
                raise ItemManifestError(
                    "warning presentation differs from its private manifest binding"
                )
    encoded = _canonical(packet).decode("utf-8")
    model_id, revision = target["target_request"].rsplit("@", 1)
    exact_forbidden = [model_id, revision]
    component_forbidden = [
        token for token in model_id.split("/") if len(token) >= 3
    ]
    if any(token.casefold() in encoded.casefold() for token in exact_forbidden) or any(
        re.search(
            rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])",
            encoded,
            re.IGNORECASE,
        )
        for token in component_forbidden
    ):
        raise ItemManifestError("reviewer packet leaks exact target identity")
    if _ABSOLUTE_PATH_RE.search(encoded):
        raise ItemManifestError("reviewer packet leaks a local source path")
    if _SOURCE_URL_RE.search(encoded):
        raise ItemManifestError("reviewer packet leaks a source URL")
    if any(
        f'"{key}":' in encoded
        for key in ("source_uri", "source_sha256", "source_revision")
    ):
        raise ItemManifestError("reviewer packet leaks private source identity")
    if packet["phase"] == "primary" and any(
        token in encoded for token in ('"warning_present":', '"system_disposition":')
    ):
        raise ItemManifestError("primary packet leaks a system disposition or warning")


def validate_target_sheet(
    sheet: Mapping[str, Any], manifest: Mapping[str, Any]
) -> None:
    """Validate the condition-neutral exact-target sheet used for assignment tasks."""

    validate_item_manifest(manifest)
    schema = _schema("target-sheet.schema.json")
    try:
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(sheet)
    except (SchemaError, ValidationError) as exc:
        raise ItemManifestError("controlled target sheet violates its JSON Schema") from exc
    payload = dict(sheet)
    expected = payload.pop("sheet_sha256", None)
    if expected != _digest(payload):
        raise ItemManifestError("controlled target sheet digest is stale")
    target = next(
        (
            item
            for item in manifest["targets"]
            if item["target_blind_id"] == sheet["target_blind_id"]
        ),
        None,
    )
    exact = sheet["exact_target"]
    request = f"{exact['model_id']}@{exact['revision']}"
    if (
        target is None
        or target["target_request"] != request
        or target["target_sha256"] != _digest(exact)
        or target["target_sheet_sha256"] != sheet["sheet_sha256"]
    ):
        raise ItemManifestError("controlled target sheet differs from its manifest")
    encoded = _canonical(sheet).decode("utf-8")
    if _ABSOLUTE_PATH_RE.search(encoded) or _SOURCE_URL_RE.search(encoded):
        raise ItemManifestError("controlled target sheet leaks source material")
    if any(token in encoded.casefold() for token in ("condition a", "condition b")):
        raise ItemManifestError("controlled target sheet leaks a treatment condition")


def validate_labels_against_manifest(
    manifest: Mapping[str, Any],
    labels: Mapping[str, Any],
    *,
    target_lookup: Mapping[str, str],
    condition_receipts: Mapping[
        str, Mapping[str, Mapping[str, str] | None]
    ],
) -> None:
    """Require completed labels to cover the exact artifact-bound item universe."""

    validate_item_manifest(manifest)
    if labels.get("labels_version") != LABELS_VERSION:
        raise ItemManifestError("labels version does not support item manifests")
    if labels.get("item_manifest_sha256") != manifest["manifest_sha256"]:
        raise ItemManifestError("labels are not bound to the supplied item manifest")
    manifest_targets = {
        item["target_blind_id"]: item["target_request"] for item in manifest["targets"]
    }
    if manifest_targets != dict(target_lookup):
        raise ItemManifestError("item manifest and private target map differ")
    if set(manifest["conditions"]) != set(condition_receipts):
        raise ItemManifestError("item manifest condition universe differs from reports")
    manifest_requests = set(manifest_targets.values())
    for condition, receipts in condition_receipts.items():
        if set(receipts) != manifest_requests:
            raise ItemManifestError("item manifest target universe differs from reports")
        for target in manifest["targets"]:
            receipt = receipts[target["target_request"]]
            if receipt is None:
                raise ItemManifestError(
                    "item manifest cannot bind a failed quality-report target"
                )
            condition_record = next(
                entry
                for entry in target["condition_artifacts"]
                if entry["condition"] == condition
            )
            expected = {
                "pipeline_result_sha256": condition_record[
                    "pipeline_result_sha256"
                ],
                "source_input_surface_sha256": condition_record[
                    "source_input_surface_sha256"
                ],
                "treatment_surface_sha256": condition_record[
                    "treatment_surface_sha256"
                ],
            }
            if dict(receipt) != expected:
                raise ItemManifestError(
                    "item manifest condition receipt differs from its quality-report run"
                )
    expected = {
        (condition["condition"], item["target_blind_id"], item["item_id"])
        for item in manifest["items"]
        for condition in item["conditions"]
        if condition["present"]
    }
    actual = {
        (item["condition"], item["target_blind_id"], item["item_id"])
        for item in labels.get("items", [])
    }
    if len(actual) != len(labels.get("items", [])) or actual != expected:
        raise ItemManifestError(
            "completed labels do not exactly cover the artifact-bound item manifest"
        )
    manifest_item_by_identity = {
        (item["target_blind_id"], item["item_id"]): item
        for item in manifest["items"]
    }
    for label in labels.get("items", []):
        manifest_item = manifest_item_by_identity[
            (label["target_blind_id"], label["item_id"])
        ]
        applicable = set(_KIND_LABEL_FIELDS[manifest_item["item_kind"]])
        if (
            manifest_item["item_kind"] == "claim"
            and isinstance(manifest_item["subject"]["field_path"], str)
            and manifest_item["subject"]["field_path"].startswith(
                "evaluation.benchmark_scores"
            )
        ):
            applicable.add("score_row")
        for field in _SEMANTIC_LABEL_FIELDS:
            if field in applicable and label[field] == "not_applicable":
                raise ItemManifestError(
                    f"{manifest_item['item_kind']} label marks {field} not applicable"
                )
            if field not in applicable and label[field] != "not_applicable":
                raise ItemManifestError(
                    f"{manifest_item['item_kind']} label supplies inapplicable {field}"
                )


def manifest_warning_presence(
    manifest: Mapping[str, Any],
) -> dict[tuple[str, str, str], bool]:
    """Return the sealed system warning flag for each label identity.

    This is deliberately derived from the private manifest rather than accepted
    from a reviewer-authored label row.
    """

    validate_item_manifest(manifest)
    return {
        (
            condition["condition"],
            item["target_blind_id"],
            item["item_id"],
        ): condition["disposition"]["warning_present"]
        for item in manifest["items"]
        for condition in item["conditions"]
    }


def _write_new(path: Path, value: Mapping[str, Any], *, mode: int) -> None:
    if path.exists() or path.is_symlink():
        raise ItemManifestError("refusing to overwrite an existing evaluation output")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical(value) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError as exc:
        raise ItemManifestError("evaluation output appeared concurrently") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_key(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ItemManifestError("blinding key must be a regular non-symlink file")
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise ItemManifestError("blinding key must not be group/world accessible")
    try:
        value = path.read_bytes()
    except OSError as exc:
        raise ItemManifestError("blinding key is unavailable") from exc
    if len(value) < 32:
        raise ItemManifestError("blinding key must contain at least 32 bytes")
    return value


def _parse_run(value: str) -> ConditionRun:
    if "=" not in value or ":" not in value.split("=", 1)[0]:
        raise ItemManifestError("run must use CONDITION:TARGET_BLIND_ID=RUN_DIR")
    identity, path = value.split("=", 1)
    condition, blind_id = identity.split(":", 1)
    if not path:
        raise ItemManifestError("run directory is missing")
    return ConditionRun(condition, blind_id, Path(path))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build sealed private item bindings and redacted paired reviewer packets."
    )
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        metavar="CONDITION:TARGET_BLIND_ID=RUN_DIR",
    )
    parser.add_argument("--study-unit-id", required=True)
    parser.add_argument("--blinding-key-file", required=True)
    parser.add_argument("--private-manifest", required=True)
    parser.add_argument("--public-packet-dir", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest_path = Path(args.private_manifest)
        packet_dir = Path(args.public_packet_dir)
        runs = [_parse_run(value) for value in args.run]
        manifest, packets, target_sheets = build_evaluation_material(
            runs,
            study_unit_id=args.study_unit_id,
            blinding_key=_read_key(Path(args.blinding_key_file)),
        )
        proposed = [
            packet_dir / f"{blind_id}-{condition}-{phase}.json"
            for blind_id, condition, phase in sorted(packets)
        ]
        target_paths = [
            packet_dir / f"{blind_id}-target.json" for blind_id in sorted(target_sheets)
        ]
        if any(
            path.exists() or path.is_symlink() for path in (*proposed, *target_paths)
        ):
            raise ItemManifestError("refusing to overwrite an existing reviewer packet")
        _write_new(manifest_path, manifest, mode=0o600)
        try:
            for blind_id, path in zip(sorted(target_sheets), target_paths):
                _write_new(path, target_sheets[blind_id], mode=0o644)
            for key, path in zip(sorted(packets), proposed):
                _write_new(path, packets[key], mode=0o644)
        except Exception:
            # The immutable manifest remains a truthful receipt.  A rerun must use
            # new paths rather than silently mutating a partially written packet set.
            raise
        summary = {
            "manifest_sha256": manifest["manifest_sha256"],
            "targets": len(manifest["targets"]),
            "items": len(manifest["items"]),
            "packets": [path.name for path in proposed],
            "target_sheets": [path.name for path in target_paths],
        }
        print(_canonical(summary).decode("utf-8"))
        return 0
    except ItemManifestError as exc:
        print(f"evaluation item manifest failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
