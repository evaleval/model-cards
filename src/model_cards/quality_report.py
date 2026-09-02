"""Body-free quality aggregation for completed CLI batch runs.

This module is deliberately downstream of the generation pipeline.  It reads
one completed batch, or a pair of batches produced from the same ordered target
requests, and verifies every reusable typed artifact before reducing it to
counts, closed finding codes, and content digests.  Source bodies, quotes,
referent hypotheses, evidence text, prompts, and usage-ledger rows are never
copied into the report.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field as dataclass_field
from decimal import Decimal, InvalidOperation
import errno
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Iterable, Mapping, Sequence

from .artifact import CardArtifact, project_card
from .claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    DecisionStatus,
    GATE_ORDER,
    GateName,
    verify_claim_gate_record,
)
from .combined_sources import CombinedSourceDocumentCatalog
from .composer import CompositionResult
from .extraction import (
    EXTRACTION_VERSION,
    ExtractionBatch,
    ExtractionResult,
    ProposalOutcome,
)
from .factreasoner import FactReasonerRecord, FieldAction
from .findings import FieldAuditStatus, OmissionAudit, OmissionReason
from .models import (
    EvidenceKind,
    RelationToTarget,
    TargetIdentity,
    TaxonomyRiskDerivation,
)
from .official_discovery import OfficialDiscoveryManifest
from .official_sources import replay_official_sources
from .pipeline import (
    CompositionStatus,
    PipelineRepairReport,
    PipelineResult,
    PrivacyScanReport,
    RiskStageSummary,
)
from .public_export import assert_public_projection
from .publication import project_publication_card
from .publication_contract import FIELD_PATHS as PUBLICATION_FIELD_PATHS
from .publication_schema import PUBLICATION_SCHEMA, validate_publication_card
from .publication_sources import (
    assert_no_source_excerpt,
    replay_publication_enrichment,
)
from .publication_validation import (
    PublicationValidationReport,
    remove_publication_fields,
    replay_publication_validation,
)
from .risk_mapping import RISK_MAPPING_VERSION, UseContext
from .run_ledger import UsageLedger
from .run_summary import (
    AUDIT_VIEW_FILENAME,
    USAGE_SUMMARY_FILENAME,
    write_run_summaries,
)
from .run_state import RunStore
from .schema import (
    CONTRACT_VERSION,
    CONTENT_FIELD_PATHS,
    get_field,
    parse_field_path,
    validate_public_card,
)
from .source_bundle import parse_target_request, replay_source_bundle
from .source_documents import SourceDocumentCatalog
from .source_state import SourceStateMode, load_source_state


QUALITY_REPORT_VERSION = "model-card-quality-report/v1"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_CODE_RE = re.compile(r"^[a-z][a-z0-9._:-]{0,127}$")
_CLAIM_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_FIELD_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)(?:\[[0-9]+\])?$")
_LOCAL_PATH_RE = re.compile(
    r"(?i)(?:file://|(?:^|\s)~[/\\]|[A-Z]:[\\/]Users[\\/]"
    r"|/Users/[^/\s]+/|/home/[^/\s]+/|/private/var/folders/|/tmp/)"
)
_ABSOLUTE_PATH_RE = re.compile(
    r"(?i)(?:^|[\s\"'(<\[={,:;])(?:file://|~[/\\]|[a-z]:[/\\]"
    r"|/(?!/)(?:[^/\s\"']+(?:/|$)))"
)
_BANNED_REPORT_KEYS = frozenset(
    {
        "body",
        "evidence",
        "evidence_text",
        "hypothesis",
        "prompt",
        "quote",
        "raw_ledger_rows",
        "raw_prompt",
        "raw_request",
        "raw_response",
        "source_content",
        "source_text",
    }
)
_SUCCESS_STATUSES = frozenset({"generated_unreviewed", "generated_validated"})
_BATCH_STATUSES = frozenset({"completed", "completed_with_failures"})
_FINDING_CODES = frozenset(
    {
        "coordinate_failure",
        "structured_failure",
        "wrong_entity",
        "wrong_checkpoint",
        "wrong_relation",
        "wrong_field",
        "invalid_score_row",
    }
)
_SURFACE_KEYS = (
    "inputs",
    "values",
    "bindings",
    "artifact",
    "decisions",
    "validation",
    "risk",
    "omission",
    "privacy",
    "cost_latency",
)
_PIPELINE_ARTIFACT_FILENAMES = frozenset(
    {
        "source-state.json",
        "source-catalog.json",
        "extraction.json",
        "claim-gates.json",
        "composition-original.json",
        "factreasoner-original.json",
        "omissions-original.json",
        "composition.json",
        "repairs.json",
        "risk-mapping.json",
        "factreasoner-content.json",
        "factreasoner-publication-original.json",
        "publication-validation.json",
        "factreasoner.json",
        "omissions.json",
        "privacy.json",
        "card-artifact.json",
        "public-card.json",
    }
)


class QualityReportError(ValueError):
    """A batch, artifact, ledger, or serialized report failed closed checks."""


@dataclass(frozen=True, init=False)
class QualityReport:
    """Immutable canonical report whose public representation contains no bodies."""

    _payload_json: str = dataclass_field(repr=False)
    report_sha256: str

    def __init__(
        self,
        *,
        primary_batch_sha256: str,
        replay_batch_sha256: str | None,
        primary_batch_status: str,
        replay_batch_status: str | None,
        targets: Sequence[Mapping[str, Any]],
        aggregate: Mapping[str, Any],
        replay_stability: Mapping[str, Any],
        report_version: str = QUALITY_REPORT_VERSION,
    ) -> None:
        payload = {
            "report_version": report_version,
            "primary_batch_sha256": primary_batch_sha256,
            "replay_batch_sha256": replay_batch_sha256,
            "primary_batch_status": primary_batch_status,
            "replay_batch_status": replay_batch_status,
            "targets": [dict(item) for item in targets],
            "aggregate": dict(aggregate),
            "replay_stability": dict(replay_stability),
        }
        _validate_report_payload(payload)
        _assert_body_free(payload)
        encoded = _canonical(payload)
        object.__setattr__(self, "_payload_json", encoded.decode("utf-8"))
        object.__setattr__(self, "report_sha256", hashlib.sha256(encoded).hexdigest())

    def _payload(self) -> dict[str, Any]:
        return json.loads(self._payload_json)

    @property
    def targets(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._payload()["targets"])

    @property
    def aggregate(self) -> dict[str, Any]:
        return self._payload()["aggregate"]

    @property
    def replay_stability(self) -> dict[str, Any]:
        return self._payload()["replay_stability"]

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "report_sha256": self.report_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "QualityReport":
        item = _strict_object(
            value,
            {
                "report_version",
                "primary_batch_sha256",
                "replay_batch_sha256",
                "primary_batch_status",
                "replay_batch_status",
                "targets",
                "aggregate",
                "replay_stability",
                "report_sha256",
            },
            "quality report",
        )
        if not isinstance(item["targets"], list):
            raise QualityReportError("quality report targets must be an array")
        report = cls(
            report_version=item["report_version"],
            primary_batch_sha256=item["primary_batch_sha256"],
            replay_batch_sha256=item["replay_batch_sha256"],
            primary_batch_status=item["primary_batch_status"],
            replay_batch_status=item["replay_batch_status"],
            targets=item["targets"],
            aggregate=item["aggregate"],
            replay_stability=item["replay_stability"],
        )
        if item["report_sha256"] != report.report_sha256:
            raise QualityReportError("quality report digest is inconsistent")
        return report


@dataclass(frozen=True)
class _LoadedTarget:
    record: dict[str, Any]
    provider: dict[str, Any] | None


@dataclass(frozen=True)
class _LoadedBatch:
    status: str
    requests: tuple[str, ...]
    targets: tuple[_LoadedTarget, ...]
    batch_sha256: str


def build_quality_report(
    primary_batch_directory: str | os.PathLike[str],
    replay_batch_directory: str | os.PathLike[str] | None = None,
) -> QualityReport:
    """Validate and aggregate one batch, optionally comparing a paired replay."""

    try:
        primary = _load_batch(Path(primary_batch_directory))
        replay = (
            None
            if replay_batch_directory is None
            else _load_batch(Path(replay_batch_directory))
        )
        if replay is not None and replay.requests != primary.requests:
            raise QualityReportError(
                "paired batches must have the same ordered target requests"
            )
        aggregate = _aggregate(primary)
        stability = _replay_stability(primary, replay)
        return QualityReport(
            primary_batch_sha256=primary.batch_sha256,
            replay_batch_sha256=None if replay is None else replay.batch_sha256,
            primary_batch_status=primary.status,
            replay_batch_status=None if replay is None else replay.status,
            targets=tuple(item.record for item in primary.targets),
            aggregate=aggregate,
            replay_stability=stability,
        )
    except QualityReportError:
        raise
    except Exception as exc:
        raise QualityReportError("batch quality validation failed") from exc


def serialize_quality_report(report: QualityReport) -> bytes:
    """Return strict canonical UTF-8 JSON with a trailing newline."""

    if not isinstance(report, QualityReport):
        raise QualityReportError("report must be a QualityReport")
    verified = QualityReport.from_dict(report.to_dict())
    return _canonical(verified.to_dict()) + b"\n"


def load_quality_report(path: str | os.PathLike[str]) -> QualityReport:
    """Load a canonical report and reject duplicate keys, drift, and extra fields."""

    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise QualityReportError("quality report file is missing or unsafe")
    raw = source.read_bytes()
    value = _strict_json(raw, "quality report")
    if raw != _canonical(value) + b"\n":
        raise QualityReportError("quality report file is not canonical")
    return QualityReport.from_dict(value)


def write_quality_report(
    report: QualityReport,
    destination: str | os.PathLike[str],
) -> Path:
    """Atomically publish a report; an identical existing file is idempotent."""

    payload = serialize_quality_report(report)
    path = Path(destination)
    if path.is_symlink() or path.parent.is_symlink():
        raise QualityReportError("quality report destination is unsafe")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_file() and path.read_bytes() == payload:
            return path
        raise FileExistsError("refusing to overwrite a different quality report")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
            if not path.is_file() or path.read_bytes() != payload:
                raise FileExistsError(
                    "refusing to overwrite a different quality report"
                ) from exc
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary.exists():
            temporary.unlink()
    return path


def _load_batch(root: Path) -> _LoadedBatch:
    if root.is_symlink() or not root.is_dir():
        raise QualityReportError("batch directory is missing or unsafe")
    request_value = _read_canonical_object(root / "batch-request.json", "batch request")
    request_value = _strict_object(request_value, {"targets"}, "batch request")
    requests_raw = request_value["targets"]
    if (
        not isinstance(requests_raw, list)
        or not requests_raw
        or not all(isinstance(item, str) for item in requests_raw)
        or len(requests_raw) != len(set(requests_raw))
    ):
        raise QualityReportError("batch request targets are invalid")
    requests = tuple(requests_raw)
    for request in requests:
        model_id, revision = parse_target_request(request, None)
        canonical_request = model_id if revision is None else f"{model_id}@{revision}"
        if request != canonical_request:
            raise QualityReportError("batch target request is not canonical")

    result_value = _read_canonical_object(root / "batch-result.json", "batch result")
    result_value = _strict_object(
        result_value, {"status", "targets", "artifacts"}, "batch result"
    )
    if result_value["status"] not in _BATCH_STATUSES:
        raise QualityReportError("batch result is not complete")
    if result_value["artifacts"] != ["batch-request.json", "batch-result.json"]:
        raise QualityReportError("batch result control artifacts are invalid")
    rows = result_value["targets"]
    if not isinstance(rows, list) or len(rows) != len(requests):
        raise QualityReportError("batch result does not cover every request")
    if [item.get("request") if isinstance(item, dict) else None for item in rows] != list(
        requests
    ):
        raise QualityReportError("batch result request order is inconsistent")

    targets: list[_LoadedTarget] = []
    failures = 0
    batch_components: list[dict[str, Any]] = []
    for request, row in zip(requests, rows):
        if not isinstance(row, dict):
            raise QualityReportError("batch target result is not an object")
        if row.get("status") == "failed":
            item = _strict_object(
                row, {"request", "status", "reason", "artifacts"}, "failed target"
            )
            _require_code(item["reason"], "failed target reason")
            if item["artifacts"] != []:
                raise QualityReportError("failed target cannot claim artifacts")
            record = {
                "request": request,
                "status": "failed",
                "failure_reason": item["reason"],
                "target": None,
                "run_sha256": None,
                "metrics": None,
                "surfaces": None,
            }
            targets.append(_LoadedTarget(record=record, provider=None))
            failures += 1
            batch_components.append(
                {"request": request, "status": "failed", "reason": item["reason"]}
            )
            continue
        item = _strict_object(
            row, {"request", "target", "status", "artifacts"}, "successful target"
        )
        if item["status"] not in _SUCCESS_STATUSES:
            raise QualityReportError("successful target lifecycle is invalid")
        target, provider = _load_successful_target(root, request, item)
        targets.append(_LoadedTarget(record=target, provider=provider))
        batch_components.append(
            {
                "request": request,
                "status": item["status"],
                "run_sha256": target["run_sha256"],
                "cost_latency_sha256": target["surfaces"]["cost_latency"],
            }
        )
    expected_status = "completed_with_failures" if failures else "completed"
    if result_value["status"] != expected_status:
        raise QualityReportError("batch result failure summary is inconsistent")
    batch_sha256 = _digest(
        {
            "batch_request": request_value,
            "batch_status": result_value["status"],
            "targets": batch_components,
        }
    )
    return _LoadedBatch(
        status=result_value["status"],
        requests=requests,
        targets=tuple(targets),
        batch_sha256=batch_sha256,
    )


def _load_successful_target(
    batch_root: Path,
    request: str,
    batch_record: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    target_value = _strict_object(
        batch_record["target"], {"model_id", "revision"}, "batch target identity"
    )
    model_id, requested_revision = parse_target_request(request, None)
    try:
        resolved_target = TargetIdentity.from_dict(target_value)
    except Exception as exc:
        raise QualityReportError("batch target identity is not exact") from exc
    if resolved_target.model_id != model_id:
        raise QualityReportError("batch target model differs from its request")
    artifacts = batch_record["artifacts"]
    if (
        not isinstance(artifacts, list)
        or not artifacts
        or artifacts != sorted(set(artifacts))
    ):
        raise QualityReportError("batch target artifacts are not canonical")
    artifact_paths = tuple(_safe_relative(item) for item in artifacts)
    pipeline_entries = [item for item in artifact_paths if item.name == "pipeline-result.json"]
    if len(pipeline_entries) != 1:
        raise QualityReportError("batch target has no unique pipeline result")
    run_relative = pipeline_entries[0].parent
    if len(run_relative.parts) != 2 or run_relative.parts[0] != "targets":
        raise QualityReportError("batch target run directory is not canonical")
    if any(not _is_within(item, run_relative) for item in artifact_paths):
        raise QualityReportError("batch target artifact crosses run boundaries")
    run_root = _safe_child(batch_root, run_relative, require_directory=True)
    for relative in artifact_paths:
        _safe_child(batch_root, relative, require_file=True)

    pipeline_value = _read_canonical_object(
        run_root / "pipeline-result.json", "pipeline result"
    )
    try:
        result = PipelineResult.from_dict(pipeline_value)
    except Exception as exc:
        raise QualityReportError("pipeline result failed typed validation") from exc
    if result.target.to_dict() != target_value or result.lifecycle_status.value != batch_record[
        "status"
    ]:
        raise QualityReportError("pipeline result differs from batch target summary")

    try:
        store = RunStore.open(run_root)
    except Exception as exc:
        raise QualityReportError("run manifest or journal failed validation") from exc
    if (
        store.manifest.target != result.target
        or store.manifest.run_id != result.run_id
        or store.manifest.source_bundle_id != result.source_bundle_id
        or store.manifest.source_manifest_sha256 != result.source_manifest_sha256
    ):
        raise QualityReportError("run manifest differs from pipeline result")

    expected_batch_artifacts = {
        run_relative / "source-bundle" / "manifest.json",
        run_relative / "pipeline-result.json",
        run_relative / AUDIT_VIEW_FILENAME,
        run_relative / USAGE_SUMMARY_FILENAME,
    }
    artifact_by_name = {item.filename: item for item in result.artifacts}
    if (
        len(artifact_by_name) != len(result.artifacts)
        or set(artifact_by_name) != _PIPELINE_ARTIFACT_FILENAMES
    ):
        raise QualityReportError("pipeline artifact inventory is not the closed contract")
    artifact_events = {
        item.artifact_path: item
        for item in store.events(verify_artifacts=True)
        if item.artifact_path is not None
    }
    if set(artifact_events) != _PIPELINE_ARTIFACT_FILENAMES | {
        "pipeline-result.json"
    }:
        raise QualityReportError("run journal artifact inventory differs from the pipeline")
    for reference in result.artifacts:
        path = _safe_child(run_root, PurePosixPath(reference.filename), require_file=True)
        event = artifact_events.get(reference.filename)
        if (
            hashlib.sha256(path.read_bytes()).hexdigest()
            != reference.artifact_sha256
            or event is None
            or (
                event.stage,
                event.logical_id,
                event.status,
                event.reason,
                event.artifact_sha256,
            )
            != (
                reference.stage,
                reference.logical_id,
                reference.status,
                reference.reason,
                reference.artifact_sha256,
            )
        ):
            raise QualityReportError("pipeline artifact reference hash is stale")
        expected_batch_artifacts.add(run_relative / reference.filename)

    source_state_value = _read_canonical_object(
        run_root / "source-state.json", "source state"
    )
    state_mode = source_state_value.get("mode")
    official_directory: Path | None = None
    if state_mode == SourceStateMode.HF_AND_OFFICIAL.value:
        official_manifest = (
            run_relative / "official-source-bundle" / "manifest.json"
        )
        expected_batch_artifacts.add(official_manifest)
        _safe_child(batch_root, official_manifest, require_file=True)
        official_directory = _safe_child(
            batch_root,
            run_relative / "official-source-bundle",
            require_directory=True,
        )
    elif state_mode != SourceStateMode.HF_ONLY.value:
        raise QualityReportError("source state mode is unsupported")
    discovery_path = run_root / "official-discovery.json"
    if discovery_path.exists() or discovery_path.is_symlink():
        discovery_relative = run_relative / "official-discovery.json"
        expected_batch_artifacts.add(discovery_relative)
        discovery_value = _read_canonical_object(
            _safe_child(batch_root, discovery_relative, require_file=True),
            "official discovery",
        )
        try:
            discovery = OfficialDiscoveryManifest.from_dict(discovery_value)
        except Exception as exc:
            raise QualityReportError(
                "official discovery failed typed validation"
            ) from exc
        if state_mode != SourceStateMode.HF_AND_OFFICIAL.value:
            raise QualityReportError(
                "official discovery exists without an official source state"
            )
    else:
        discovery = None
    if set(artifact_paths) != expected_batch_artifacts:
        raise QualityReportError("batch target artifact inventory is incomplete or stale")
    try:
        source_state = load_source_state(
            run_root / "source-bundle",
            official_bundle_directory=official_directory,
        )
    except Exception as exc:
        raise QualityReportError("source state replay failed") from exc
    try:
        hf_bundle = replay_source_bundle(
            run_root / "source-bundle",
            expected_model_id=resolved_target.model_id,
            expected_revision=resolved_target.revision,
        )
    except Exception as exc:
        raise QualityReportError("Hub source request binding failed") from exc
    if hf_bundle.manifest.requested_revision != requested_revision:
        raise QualityReportError("Hub bundle requested revision differs from the batch")
    if (
        source_state.to_dict() != source_state_value
        or source_state.target != result.target
        or result.source_bundle_id != source_state.active_catalog_bundle_id
        or result.source_manifest_sha256 != source_state.snapshot_sha256
        or result.source_catalog_sha256 != source_state.active_catalog_sha256
    ):
        raise QualityReportError("source state differs from pipeline result")
    if discovery is not None and (
        discovery.target != source_state.target
        or discovery.source_bundle_id != source_state.hf_bundle_id
        or source_state.official_catalog is None
    ):
        raise QualityReportError("official discovery differs from source state")
    if discovery is not None:
        try:
            official_bundle = replay_official_sources(
                official_directory,
                expected_target=source_state.target,
                expected_discovery_id=discovery.discovery_id,
            )
        except Exception as exc:
            raise QualityReportError(
                "official discovery ancestry differs from the collected bundle"
            ) from exc
        if official_bundle.manifest.policy != discovery.policy:
            raise QualityReportError(
                "official discovery policy differs from the collected bundle"
            )
    source_catalog = source_state.catalog
    source_value = _read_canonical_object(run_root / "source-catalog.json", "source catalog")
    if source_value != source_catalog.to_dict():
        raise QualityReportError("serialized source catalog does not replay")

    for name in (AUDIT_VIEW_FILENAME, USAGE_SUMMARY_FILENAME):
        _safe_child(run_root, PurePosixPath(name), require_file=True)
    try:
        run_summaries = write_run_summaries(result, run_root)
    except Exception as exc:
        raise QualityReportError("derived run summaries failed validation") from exc
    if (
        run_summaries.run_id != result.run_id
        or run_summaries.pipeline_result_sha256 != result.result_sha256
        or any(
            hashlib.sha256((run_root / reference.filename).read_bytes()).hexdigest()
            != reference.artifact_sha256
            for reference in run_summaries.artifacts
        )
    ):
        raise QualityReportError("derived run summary identity is stale")

    extraction = _load_extraction(run_root, result)
    gates, gate_value = _load_gates(run_root, result, extraction, source_catalog.documents)
    composition = _load_composition(run_root, result)
    repair = _load_repair_chain(run_root, result)
    artifact, public_card = _load_exports(run_root, result)
    privacy = _load_privacy(run_root, result)
    content_fact, original_publication_fact, publication_validation, fact = (
        _load_publication_validation_chain(
            run_root,
            result,
            artifact,
            public_card,
            source_state.hf_catalog,
            source_catalog,
        )
    )
    omission = _load_omissions(
        run_root,
        result,
        publication_validation,
    )
    risk_value, risk_metrics, risk_surface = _load_risk(
        run_root, result, artifact, repair
    )

    included_ids = {item.candidate_id for item in result.claims if item.included}
    if composition is not None and set(composition.plan.included_candidate_ids) != included_ids:
        raise QualityReportError("composition selection differs from pipeline claims")
    if {item.candidate.candidate_id for item in gates} != {
        item.candidate_id for item in result.claims
    }:
        raise QualityReportError("claim-gate inventory differs from pipeline claims")
    if fact.target != result.target or omission.content_sha256 != result.omission_audit_sha256:
        raise QualityReportError("typed validation artifacts differ from pipeline result")

    provider = _provider_metrics(run_root / "usage.jsonl")
    metrics = {
        "schema_export": _schema_export_metrics(result, artifact, public_card),
        "fields": _field_metrics(omission, publication_validation),
        "sources": _source_metrics(source_catalog.records),
        "claims": _claim_metrics(gates, result),
        "findings": _finding_metrics(_explicit_findings(gates)),
        "factreasoner": _fact_metrics(fact),
        "omissions": _omission_metrics(
            omission,
            publication_validation,
            result.conflict_count,
        ),
        "risk": risk_metrics,
        "privacy": _privacy_metrics(privacy, result),
        "provider": provider,
    }
    surfaces = _surface_digests(
        result=result,
        public_card=public_card,
        artifact=artifact,
        gates=gates,
        fact=fact,
        content_fact=content_fact,
        original_publication_fact=original_publication_fact,
        publication_validation=publication_validation,
        repair=repair,
        risk_surface=risk_surface,
        provider=provider,
        input_surface=store.manifest.manifest_sha256,
    )
    record = {
        "request": request,
        "status": result.lifecycle_status.value,
        "failure_reason": None,
        "target": result.target.to_dict(),
        "run_sha256": result.result_sha256,
        "metrics": metrics,
        "surfaces": surfaces,
    }
    # These values are deliberately read to ensure strict artifact parsing is
    # not optimized away while no body-bearing value crosses into ``record``.
    if not gate_value or not risk_value:
        raise QualityReportError("pipeline quality artifacts are incomplete")
    return record, provider


def _load_extraction(run_root: Path, result: PipelineResult) -> tuple[ClaimCandidate, ...]:
    value = _read_canonical_object(run_root / "extraction.json", "extraction artifact")
    item = _strict_object(
        value,
        {
            "extraction_version",
            "target",
            "catalog_sha256",
            "structured",
            "quote_batches",
            "quote_results",
            "candidates",
        },
        "extraction artifact",
    )
    if item["target"] != result.target.to_dict() or item["catalog_sha256"] != result.source_catalog_sha256:
        raise QualityReportError("extraction artifact target or catalog is stale")
    for name in ("quote_batches", "quote_results", "candidates"):
        if not isinstance(item[name], list):
            raise QualityReportError(f"extraction {name} must be an array")
    try:
        batches = tuple(
            ExtractionBatch.from_dict(batch) for batch in item["quote_batches"]
        )
        candidates = tuple(ClaimCandidate.from_dict(entry) for entry in item["candidates"])
    except Exception as exc:
        raise QualityReportError("extraction typed records are invalid") from exc
    if batches != tuple(sorted(batches, key=lambda entry: entry.batch_sha256)) or any(
        entry.target != result.target
        or entry.source_catalog_sha256 != result.source_catalog_sha256
        for entry in batches
    ):
        raise QualityReportError("extraction batches are stale or non-canonical")
    if candidates != tuple(sorted(candidates, key=lambda entry: entry.candidate_id)):
        raise QualityReportError("extraction candidate order is not canonical")
    references = {entry.candidate_id: entry for entry in result.claims}
    if set(references) != {entry.candidate_id for entry in candidates}:
        raise QualityReportError("extraction candidates differ from pipeline claims")
    for candidate in candidates:
        reference = references[candidate.candidate_id]
        if candidate.target != result.target or candidate.content_sha256 != reference.candidate_sha256:
            raise QualityReportError("extraction candidate digest or target is stale")
    candidate_by_id = {entry.candidate_id: entry for entry in candidates}
    summaries = (
        _typed_extraction_summary(
            item["structured"], result.target, candidate_by_id
        ),
        *(
            _typed_extraction_summary(summary, result.target, candidate_by_id)
            for summary in item["quote_results"]
        ),
    )
    if len(summaries) != len(batches) + 1 or any(
        summary.input_sha256 != batch.batch_sha256
        for summary, batch in zip(summaries[1:], batches)
    ):
        raise QualityReportError("quote extraction results differ from their batches")
    summarized_ids = {
        candidate.candidate_id
        for summary in summaries
        for candidate in summary.candidates
    }
    if summarized_ids != set(candidate_by_id):
        raise QualityReportError("extraction summaries omit inventory candidates")
    return candidates


def _typed_extraction_summary(
    value: Any,
    target: Any,
    candidate_by_id: Mapping[str, ClaimCandidate],
) -> ExtractionResult:
    item = _strict_object(
        value,
        {
            "extraction_version",
            "target",
            "input_sha256",
            "result_sha256",
            "candidate_ids",
            "candidate_sha256",
            "outcomes",
        },
        "extraction summary",
    )
    if any(not isinstance(item[name], list) for name in ("candidate_ids", "candidate_sha256", "outcomes")):
        raise QualityReportError("extraction summary arrays are invalid")
    if len(item["candidate_ids"]) != len(item["candidate_sha256"]):
        raise QualityReportError("extraction summary candidate hashes are incomplete")
    if item["extraction_version"] != EXTRACTION_VERSION or item["target"] != target.to_dict():
        raise QualityReportError("extraction summary version or target is stale")
    if item["candidate_ids"] != sorted(set(item["candidate_ids"])):
        raise QualityReportError("extraction summary candidates are not canonical")
    try:
        candidates = tuple(candidate_by_id[entry] for entry in item["candidate_ids"])
    except (KeyError, TypeError) as exc:
        raise QualityReportError("extraction summary references an unknown candidate") from exc
    if item["candidate_sha256"] != [entry.content_sha256 for entry in candidates]:
        raise QualityReportError("extraction summary candidate digests are stale")
    try:
        typed = ExtractionResult(
            extraction_version=item["extraction_version"],
            target=target,
            input_sha256=item["input_sha256"],
            candidates=candidates,
            outcomes=tuple(ProposalOutcome(**entry) for entry in item["outcomes"]),
            result_sha256=item["result_sha256"],
        )
    except Exception as exc:
        raise QualityReportError("extraction summary failed typed validation") from exc
    return typed


def _load_gates(
    run_root: Path,
    result: PipelineResult,
    candidates: tuple[ClaimCandidate, ...],
    sources: Sequence[Any],
) -> tuple[tuple[ClaimGateRecord, ...], dict[str, Any]]:
    value = _read_canonical_object(run_root / "claim-gates.json", "claim gates")
    item = _strict_object(value, {"target", "extraction_sha256", "records"}, "claim gates")
    if item["target"] != result.target.to_dict() or not isinstance(item["records"], list):
        raise QualityReportError("claim-gate target or record array is invalid")
    extraction_value = _read_canonical_object(run_root / "extraction.json", "extraction artifact")
    if item["extraction_sha256"] != _digest(extraction_value):
        raise QualityReportError("claim-gate extraction digest is stale")
    try:
        records = tuple(ClaimGateRecord.from_dict(entry) for entry in item["records"])
    except Exception as exc:
        raise QualityReportError("claim-gate records failed typed validation") from exc
    by_candidate = {entry.candidate_id: entry for entry in candidates}
    references = {entry.candidate_id: entry for entry in result.claims}
    if len(records) != len(by_candidate):
        raise QualityReportError("claim-gate records do not cover extraction candidates")
    for record in records:
        candidate_id = record.candidate.candidate_id
        if candidate_id not in by_candidate or record.candidate.to_dict() != by_candidate[candidate_id].to_dict():
            raise QualityReportError("claim-gate candidate differs from extraction")
        reference = references.get(candidate_id)
        if (
            reference is None
            or reference.gate_record_sha256 != record.content_sha256
            or reference.projection_eligible != record.projection_eligible
        ):
            raise QualityReportError("claim-gate result differs from pipeline reference")
        try:
            verify_claim_gate_record(record, sources)
        except Exception as exc:
            raise QualityReportError("claim-gate source replay failed") from exc
    return records, value


def _load_composition(run_root: Path, result: PipelineResult) -> CompositionResult | None:
    value = _read_canonical_object(run_root / "composition.json", "composition artifact")
    if result.composition_status is CompositionStatus.COMPLETED:
        try:
            composition = CompositionResult.from_dict(value)
        except Exception as exc:
            raise QualityReportError("composition failed typed validation") from exc
        if composition.content_sha256 != result.composition_sha256 or composition.plan.target != result.target:
            raise QualityReportError("composition differs from pipeline result")
        return composition
    item = _strict_object(
        value,
        {"status", "reason", "target", "composition_sha256", "card"},
        "unavailable composition",
    )
    if (
        item["status"] != "unavailable"
        or item["target"] != result.target.to_dict()
        or item["composition_sha256"] != result.composition_sha256
    ):
        raise QualityReportError("unavailable composition differs from pipeline result")
    validate_public_card(item["card"])
    return None


def _load_repair_chain(
    run_root: Path,
    result: PipelineResult,
) -> PipelineRepairReport:
    """Validate the original audit and the immutable final withholding bridge."""

    repair_value = _read_canonical_object(run_root / "repairs.json", "repair report")
    try:
        repair = PipelineRepairReport.from_dict(repair_value)
    except Exception as exc:
        raise QualityReportError("repair report failed typed validation") from exc
    if (
        repair.target != result.target
        or repair.post_repair_composition_sha256 != result.composition_sha256
    ):
        raise QualityReportError("repair report differs from final composition")

    original_composition_value = _read_canonical_object(
        run_root / "composition-original.json", "original composition"
    )
    if original_composition_value.get("status") == "unavailable":
        unavailable = _strict_object(
            original_composition_value,
            {"status", "reason", "target", "composition_sha256", "card"},
            "unavailable original composition",
        )
        if (
            unavailable["target"] != result.target.to_dict()
            or unavailable["composition_sha256"]
            != repair.original_composition_sha256
        ):
            raise QualityReportError("original composition identity is stale")
        _require_code(unavailable["reason"], "original composition reason")
        validate_public_card(unavailable["card"])
    else:
        try:
            original_composition = CompositionResult.from_dict(
                original_composition_value
            )
        except Exception as exc:
            raise QualityReportError(
                "original composition failed typed validation"
            ) from exc
        if (
            original_composition.plan.target != result.target
            or original_composition.content_sha256
            != repair.original_composition_sha256
        ):
            raise QualityReportError("original composition identity is stale")

    original_fact_value = _read_canonical_object(
        run_root / "factreasoner-original.json", "original FactReasoner artifact"
    )
    original_omission_value = _read_canonical_object(
        run_root / "omissions-original.json", "original omission artifact"
    )
    try:
        original_fact = FactReasonerRecord.from_dict(original_fact_value)
        original_fact.validate_integrity()
        original_omission = OmissionAudit.from_dict(original_omission_value)
    except Exception as exc:
        raise QualityReportError("original audit chain failed typed validation") from exc
    if (
        original_fact.target != result.target
        or original_fact.content_sha256 != repair.original_factreasoner_sha256
        or original_omission.content_sha256
        != repair.original_omission_audit_sha256
        or original_omission.composition_result_sha256
        != repair.original_composition_sha256
    ):
        raise QualityReportError("original audit chain identity is stale")

    claim_ids = {entry.candidate_id for entry in result.claims}
    if (
        not set(repair.actionable_candidate_ids) <= claim_ids
        or not set(repair.structural_withheld_candidate_ids) <= claim_ids
        or any(
            entry.included and entry.candidate_id in repair.withheld_candidate_ids
            for entry in result.claims
        )
    ):
        raise QualityReportError("repair withholding differs from final claims")
    return repair


def _load_exports(
    run_root: Path, result: PipelineResult
) -> tuple[CardArtifact, dict[str, Any]]:
    artifact_value = _read_canonical_object(run_root / "card-artifact.json", "card artifact")
    artifact_keys = {
        "artifact_id",
        "contract_version",
        "target",
        "lifecycle",
        "card",
        "bindings",
        "reviews",
        "validation_checks",
        "derivations",
    }
    if "publication" in artifact_value:
        artifact_keys.add("publication")
    _strict_object(
        artifact_value,
        artifact_keys,
        "card artifact",
    )
    try:
        artifact = CardArtifact.from_dict(artifact_value)
    except Exception as exc:
        raise QualityReportError("card artifact failed typed validation") from exc
    public_card = _read_canonical_object(run_root / "public-card.json", "public card")
    try:
        validate_publication_card(public_card)
        assert_public_projection(public_card)
    except Exception as exc:
        raise QualityReportError("public card failed schema or privacy validation") from exc
    if (
        artifact.target != result.target
        or artifact.artifact_id != result.artifact_id
        or artifact.lifecycle_status != result.lifecycle_status
        or (
            artifact.publication_card
            if artifact.publication_card is not None
            else project_publication_card(project_card(artifact))
        )
        != public_card
        or hashlib.sha256((run_root / "card-artifact.json").read_bytes()).hexdigest()
        != result.artifact_sha256
        or hashlib.sha256((run_root / "public-card.json").read_bytes()).hexdigest()
        != result.public_card_sha256
    ):
        raise QualityReportError("exported artifact or public card differs from pipeline result")
    return artifact, public_card


def _load_privacy(run_root: Path, result: PipelineResult) -> PrivacyScanReport:
    value = _read_canonical_object(run_root / "privacy.json", "privacy artifact")
    try:
        report = PrivacyScanReport.from_dict(value)
    except Exception as exc:
        raise QualityReportError("privacy report failed typed validation") from exc
    if report.to_dict() != result.privacy.to_dict() or report.scanned_card_sha256 != result.public_card_sha256:
        raise QualityReportError("privacy report differs from public export")
    return report


def _load_factreasoner_file(
    run_root: Path,
    filename: str,
    *,
    label: str,
    expected_sha256: str,
    target: TargetIdentity,
) -> FactReasonerRecord:
    value = _read_canonical_object(run_root / filename, label)
    try:
        record = FactReasonerRecord.from_dict(value)
        record.validate_integrity()
    except Exception as exc:
        raise QualityReportError(f"{label} failed typed validation") from exc
    if record.content_sha256 != expected_sha256 or record.target != target:
        raise QualityReportError(f"{label} differs from pipeline result")
    return record


def _load_publication_validation_chain(
    run_root: Path,
    result: PipelineResult,
    artifact: CardArtifact,
    public_card: Mapping[str, Any],
    hf_catalog: SourceDocumentCatalog,
    source_catalog: SourceDocumentCatalog | CombinedSourceDocumentCatalog,
) -> tuple[
    FactReasonerRecord,
    FactReasonerRecord,
    PublicationValidationReport,
    FactReasonerRecord,
]:
    """Replay the deterministic bridge around the final public FactReasoner."""

    content_fact = _load_factreasoner_file(
        run_root,
        "factreasoner-content.json",
        label="content FactReasoner artifact",
        expected_sha256=result.content_factreasoner_sha256,
        target=result.target,
    )
    original_publication_fact = _load_factreasoner_file(
        run_root,
        "factreasoner-publication-original.json",
        label="pre-withhold publication FactReasoner artifact",
        expected_sha256=result.publication_original_factreasoner_sha256,
        target=result.target,
    )
    final_fact = _load_factreasoner_file(
        run_root,
        "factreasoner.json",
        label="final publication FactReasoner artifact",
        expected_sha256=result.factreasoner_sha256,
        target=result.target,
    )
    validation_value = _read_canonical_object(
        run_root / "publication-validation.json",
        "publication validation artifact",
    )
    try:
        validation = PublicationValidationReport.from_dict(validation_value)
    except Exception as exc:
        raise QualityReportError(
            "publication validation report failed typed validation"
        ) from exc
    if validation.content_sha256 != result.publication_validation_sha256:
        raise QualityReportError(
            "publication validation report differs from pipeline result"
        )
    if (
        not isinstance(hf_catalog, SourceDocumentCatalog)
        or not isinstance(
            source_catalog,
            (SourceDocumentCatalog, CombinedSourceDocumentCatalog),
        )
        or source_catalog.target != result.target
        or artifact.publication_source_catalog_sha256
        != source_catalog.catalog_sha256
    ):
        raise QualityReportError(
            "publication snapshot differs from the active frozen source catalog"
        )

    base_card = project_publication_card(project_card(artifact))
    try:
        initial = replay_publication_enrichment(hf_catalog, base_card)
        assert_no_source_excerpt(initial.card, source_catalog)
        validated = replay_publication_validation(
            validation,
            initial.card,
            original_publication_fact,
        )
    except Exception as exc:
        raise QualityReportError(
            "publication enrichment or validation replay failed"
        ) from exc

    initial_paths = {item.field_path for item in initial.provenance}
    withheld_paths = set(validation.withheld_field_paths)
    derived_withheld = tuple(sorted(withheld_paths.intersection(initial_paths)))
    direct_withheld = tuple(sorted(withheld_paths - initial_paths))
    try:
        replayed_enrichment = replay_publication_enrichment(
            hf_catalog,
            base_card,
            withheld_fields=derived_withheld,
        )
        replayed_public_card = remove_publication_fields(
            replayed_enrichment.card,
            direct_withheld,
        )
        assert_no_source_excerpt(replayed_public_card, source_catalog)
    except Exception as exc:
        raise QualityReportError("final publication replay failed") from exc
    if (
        replayed_public_card != public_card
        or validated.final_card != public_card
        or artifact.publication_card != public_card
        or artifact.publication_provenance != replayed_enrichment.provenance
        or artifact.publication_withheld_fields != direct_withheld
    ):
        raise QualityReportError(
            "final public card or deterministic provenance does not replay"
        )

    publication_schema_sha256 = _digest(PUBLICATION_SCHEMA)
    final_coverage = tuple(item.field_path for item in final_fact.field_coverage)
    if (
        original_publication_fact.schema_sha256 != publication_schema_sha256
        or final_fact.schema_sha256 != publication_schema_sha256
        or final_fact.card_sha256 != _digest(public_card)
        or len(final_coverage) != len(PUBLICATION_FIELD_PATHS)
        or set(final_coverage) != set(PUBLICATION_FIELD_PATHS)
        or any(
            item.action is FieldAction.REPAIR_OR_WITHHOLD
            for item in final_fact.field_decisions
        )
    ):
        raise QualityReportError(
            "final FactReasoner is not bound to the complete publication card"
        )
    return content_fact, original_publication_fact, validation, final_fact


def _load_omissions(
    run_root: Path,
    result: PipelineResult,
    publication_validation: PublicationValidationReport,
) -> OmissionAudit:
    value = _read_canonical_object(run_root / "omissions.json", "omission artifact")
    try:
        audit = OmissionAudit.from_dict(value)
    except Exception as exc:
        raise QualityReportError("omission audit failed typed validation") from exc
    if (
        audit.content_sha256 != result.omission_audit_sha256
        or (
            len(audit.source_present_omissions)
            + len(publication_validation.source_present_omissions)
        )
        != result.source_present_omission_count
    ):
        raise QualityReportError("omission audit differs from pipeline result")
    return audit


def _load_risk(
    run_root: Path,
    result: PipelineResult,
    artifact: CardArtifact,
    repair: PipelineRepairReport,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    value = _read_canonical_object(run_root / "risk-mapping.json", "risk mapping")
    item = _strict_object(
        value,
        {
            "summary",
            "use_contexts",
            "taxonomy_derivations",
            "factreasoner_withheld_derivation_ids",
            "taxonomy_mapping",
        },
        "risk mapping",
    )
    try:
        summary = RiskStageSummary.from_dict(item["summary"])
    except Exception as exc:
        raise QualityReportError("risk summary failed typed validation") from exc
    if summary.to_dict() != result.risk.to_dict():
        raise QualityReportError("risk summary differs from pipeline result")
    if (
        not isinstance(item["use_contexts"], list)
        or not isinstance(item["taxonomy_derivations"], list)
        or not isinstance(item["factreasoner_withheld_derivation_ids"], list)
    ):
        raise QualityReportError("risk context or derivation array is invalid")
    try:
        contexts = tuple(UseContext.from_dict(entry) for entry in item["use_contexts"])
        derivations = tuple(
            TaxonomyRiskDerivation.from_dict(entry)
            for entry in item["taxonomy_derivations"]
        )
    except Exception as exc:
        raise QualityReportError("risk contexts or derivations failed typed validation") from exc
    if contexts != tuple(sorted(contexts, key=lambda entry: entry.context_id)):
        raise QualityReportError("risk contexts are not canonical")
    if _digest([entry.to_dict() for entry in contexts]) != summary.context_sha256:
        raise QualityReportError("risk context digest is stale")
    fact_withheld_ids = tuple(item["factreasoner_withheld_derivation_ids"])
    if (
        fact_withheld_ids != tuple(sorted(set(fact_withheld_ids)))
        or fact_withheld_ids != repair.factreasoner_withheld_derivation_ids
    ):
        raise QualityReportError("risk FactReasoner withholding is inconsistent")

    mapping = item["taxonomy_mapping"]
    candidate_count = mapping_included_count = 0
    included_count = applicability_total = applicability_accepted = 0
    mapping_report_sha256 = None
    ground_count = 0
    if mapping is None:
        if summary.status != "unavailable" or summary.mapping_report_sha256 is not None:
            raise QualityReportError("missing risk mapping disagrees with stage status")
    else:
        mapping = _strict_object(
            mapping,
            {
                "mapping_version",
                "status",
                "catalog_sha256",
                "context_sha256",
                "candidate_ids",
                "candidate_sha256",
                "decision_sha256",
                "included_risks",
                "reason",
                "report_sha256",
            },
            "taxonomy mapping",
        )
        for name in ("candidate_ids", "candidate_sha256", "decision_sha256", "included_risks"):
            if not isinstance(mapping[name], list):
                raise QualityReportError(f"taxonomy mapping {name} must be an array")
        if mapping["mapping_version"] != RISK_MAPPING_VERSION:
            raise QualityReportError("taxonomy mapping version is invalid")
        candidate_ids = mapping["candidate_ids"]
        if candidate_ids != sorted(set(candidate_ids)) or any(
            not isinstance(value, str) or not value.startswith("risk-candidate-")
            for value in candidate_ids
        ):
            raise QualityReportError("taxonomy candidate identifiers are invalid")
        if len(candidate_ids) != len(mapping["candidate_sha256"]) or len(candidate_ids) != len(mapping["decision_sha256"]):
            raise QualityReportError("taxonomy mapping decisions do not cover candidates")
        for digest in (*mapping["candidate_sha256"], *mapping["decision_sha256"]):
            _require_digest(digest, "taxonomy mapping digest")
        payload = {key: mapping[key] for key in mapping if key != "report_sha256"}
        if mapping["report_sha256"] != _digest(payload):
            raise QualityReportError("taxonomy mapping report digest is stale")
        if (
            mapping["catalog_sha256"] != summary.catalog_sha256
            or mapping["context_sha256"] != summary.context_sha256
            or mapping["report_sha256"] != summary.mapping_report_sha256
        ):
            raise QualityReportError("taxonomy mapping inputs differ from risk summary")
        candidate_count = len(candidate_ids)
        mapping_included_count = len(mapping["included_risks"])
        applicability_total = len(mapping["decision_sha256"])
        applicability_accepted = mapping_included_count
        if mapping_included_count > candidate_count:
            raise QualityReportError("taxonomy mapping includes too many risks")
        for risk in mapping["included_risks"]:
            if not isinstance(risk, dict) or not isinstance(risk.get("grounds"), list):
                raise QualityReportError("taxonomy included risk grounding is malformed")
            ground_count += len(risk["grounds"])
        mapping_report_sha256 = mapping["report_sha256"]
    included_count = len(derivations)
    if (
        candidate_count != summary.taxonomy_candidate_count
        or included_count != summary.taxonomy_included_count
        or mapping_included_count - len(fact_withheld_ids) != included_count
    ):
        raise QualityReportError("taxonomy counts differ across risk artifacts")
    for derivation in derivations:
        if (
            derivation.target != result.target
            or derivation.risk_report_sha256 != mapping_report_sha256
            or derivation.risk_catalog_sha256 != summary.catalog_sha256
        ):
            raise QualityReportError("taxonomy derivation inputs are stale")
    exported = tuple(artifact.derivations)
    if not {entry.derivation_id for entry in exported} <= {
        entry.derivation_id for entry in derivations
    }:
        raise QualityReportError("exported taxonomy derivation is not in risk mapping")
    context_source_refs = {ref for context in contexts for ref in context.source_refs}
    metrics = {
        "status": summary.status,
        "reason": summary.reason,
        "catalog_available": summary.catalog_sha256 is not None,
        "catalog_sha256": summary.catalog_sha256,
        "context_count": len(contexts),
        "grounded_context_count": sum(
            bool(entry.supporting_fields and entry.supporting_candidate_ids and entry.source_refs)
            for entry in contexts
        ),
        "publisher_context_count": len(summary.publisher_context_candidate_ids),
        "publisher_risk_count": len(summary.publisher_reported_risk_candidate_ids),
        "taxonomy_candidate_count": candidate_count,
        "taxonomy_mapped_count": mapping_included_count,
        "taxonomy_included_count": included_count,
        "taxonomy_withheld_count": candidate_count - included_count,
        "taxonomy_factreasoner_withheld_count": len(fact_withheld_ids),
        "applicability_total": applicability_total,
        "applicability_accepted": applicability_accepted,
        "applicability_withheld": applicability_total - applicability_accepted,
        "mapping_derivation_count": len(derivations),
        "exported_derivation_count": len(exported),
        "ground_count": ground_count,
        "input_claim_count": len(
            {claim.candidate_id for entry in derivations for claim in entry.input_claims}
        ),
        "supporting_source_count": len(
            context_source_refs.union(
                ref for entry in derivations for ref in entry.supporting_source_refs
            )
        ),
    }
    surface = _digest(
        {
            "summary_sha256": summary.summary_sha256,
            "mapping_report_sha256": mapping_report_sha256,
            "context_sha256": summary.context_sha256,
            "derivations": [entry.content_sha256 for entry in derivations],
            "exported_derivations": [entry.content_sha256 for entry in exported],
        }
    )
    return value, metrics, surface


def _schema_export_metrics(
    result: PipelineResult,
    artifact: CardArtifact,
    public_card: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_valid": True,
        "public_projection_safe": True,
        "contract_version": artifact.contract_version,
        "lifecycle_status": result.lifecycle_status.value,
        "artifact_binding_count": len(artifact.bindings),
        "artifact_derivation_count": len(artifact.derivations),
    }


def _field_metrics(
    audit: OmissionAudit,
    publication: PublicationValidationReport,
) -> dict[str, Any]:
    present = sum(item.status is FieldAuditStatus.PRESENT for item in audit.records)
    publication_present = sum(
        item.reason.value == "present" for item in publication.records
    )
    present += publication_present
    total = len(audit.records) + len(publication.records)
    omitted = total - present
    reasons = Counter(
        item.reason.value for item in audit.records if item.reason is not None
    )
    reasons.update(
        item.reason.value
        for item in publication.records
        if item.reason.value != "present"
    )
    return {
        "total": total,
        "present": present,
        "omitted": omitted,
        "abstention_ppm": _rate_ppm(omitted, total),
        "source_present_omissions": (
            len(audit.source_present_omissions)
            + len(publication.source_present_omissions)
        ),
        "omission_reasons": _distribution(reasons),
    }


def _source_metrics(records: Sequence[Any]) -> dict[str, Any]:
    statuses = Counter(item.status.value for item in records)
    reasons = Counter(item.reason_code for item in records)
    loaded = statuses.get("loaded", 0)
    return {
        "total": len(records),
        "loaded": loaded,
        "unavailable": len(records) - loaded,
        "statuses": _distribution(statuses),
        "reasons": _distribution(reasons),
    }


def _gate_metrics(records: Sequence[ClaimGateRecord]) -> list[dict[str, Any]]:
    output = []
    for gate in GATE_ORDER:
        decisions = [
            next(item for item in record.decisions if item.gate is gate)
            for record in records
        ]
        accepted = sum(item.status is DecisionStatus.ACCEPTED for item in decisions)
        output.append(
            {
                "gate": gate.value,
                "checked": len(decisions),
                "accepted": accepted,
                "withheld": len(decisions) - accepted,
                "reasons": _distribution(Counter(item.reason for item in decisions)),
            }
        )
    return output


def _claim_metrics(
    records: Sequence[ClaimGateRecord], result: PipelineResult
) -> dict[str, Any]:
    total = len(records)
    eligible = sum(item.projection_eligible for item in records)
    included = sum(item.included for item in result.claims)
    return {
        "total": total,
        "eligible": eligible,
        "included": included,
        "withheld": total - included,
        "gates": _gate_metrics(records),
    }


def _explicit_findings(records: Sequence[ClaimGateRecord]) -> tuple[dict[str, str], ...]:
    findings: dict[tuple[str, str], dict[str, str]] = {}

    def add(record: ClaimGateRecord, code: str, reason: str) -> None:
        if code not in _FINDING_CODES:
            raise QualityReportError("unknown quality finding code")
        candidate = record.candidate
        findings[(candidate.candidate_id, code)] = {
            "candidate_id": candidate.candidate_id,
            "field_path": candidate.field_path,
            "code": code,
            "reason": reason,
        }

    for record in records:
        candidate = record.candidate
        decisions = {item.gate: item for item in record.decisions}
        coordinate = decisions[GateName.COORDINATE_INTEGRITY]
        entity = decisions[GateName.ENTITY_SCOPE]
        field = decisions[GateName.FIELD_FIT]
        value = decisions[GateName.VALUE_SUPPORT]
        if coordinate.status is DecisionStatus.WITHHELD:
            add(record, "coordinate_failure", coordinate.reason)
        if (
            {item.kind for item in candidate.evidence} == {EvidenceKind.STRUCTURED}
            and any(
                decisions[gate].status is DecisionStatus.WITHHELD
                for gate in (
                    GateName.COORDINATE_INTEGRITY,
                    GateName.FIELD_FIT,
                    GateName.VALUE_SUPPORT,
                )
            )
        ):
            reason = next(
                item.reason
                for item in record.decisions
                if item.status is DecisionStatus.WITHHELD
            )
            add(record, "structured_failure", reason)

        expected_entity = f"{candidate.target.model_id}@{candidate.target.revision}"
        entity_model, _, entity_revision = candidate.claim_entity.rpartition("@")
        if (
            candidate.relation is RelationToTarget.EXACT_TARGET
            and candidate.claim_entity != expected_entity
        ):
            if entity_model != candidate.target.model_id:
                add(record, "wrong_entity", entity.reason)
            elif entity_revision != candidate.target.revision:
                add(record, "wrong_checkpoint", entity.reason)
        if entity.status is DecisionStatus.WITHHELD:
            lowered = entity.reason.casefold()
            if any(token in lowered for token in ("entity", "model_id", "source_target")):
                add(record, "wrong_entity", entity.reason)
            if any(token in lowered for token in ("revision", "checkpoint")):
                add(record, "wrong_checkpoint", entity.reason)
            if any(token in lowered for token in ("relation", "scope")):
                add(record, "wrong_relation", entity.reason)
        for evidence in candidate.evidence:
            if evidence.source_target is not None and evidence.source_target != candidate.target:
                if evidence.source_target.model_id == candidate.target.model_id:
                    add(record, "wrong_checkpoint", "source_target_revision_mismatch")
                else:
                    add(record, "wrong_entity", "source_target_model_mismatch")
        if (
            candidate.relation is not RelationToTarget.EXACT_TARGET
            and entity.status is DecisionStatus.WITHHELD
        ):
            add(record, "wrong_relation", "relation_not_permitted_for_field")
        if field.status is DecisionStatus.WITHHELD:
            add(record, "wrong_field", field.reason)
        try:
            base, _ = parse_field_path(candidate.field_path)
        except Exception:
            base = ""
        if base == "evaluation.benchmark_scores" and (
            field.status is DecisionStatus.WITHHELD
            or value.status is DecisionStatus.WITHHELD
        ):
            reason = field.reason if field.status is DecisionStatus.WITHHELD else value.reason
            add(record, "invalid_score_row", reason)
    return tuple(
        findings[key]
        for key in sorted(findings, key=lambda item: (item[0], item[1]))
    )


def _finding_metrics(records: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    return {
        "total": len(records),
        "codes": _distribution(Counter(item["code"] for item in records)),
        "records": [dict(item) for item in records],
    }


def _fact_metrics(record: FactReasonerRecord) -> dict[str, Any]:
    coverage = Counter(item.status.value for item in record.field_coverage)
    outcomes = Counter(item.outcome.value for item in record.decisions)
    atom_actions = Counter(item.field_action.value for item in record.decisions)
    field_actions = Counter(item.action.value for item in record.field_decisions)
    reasons = Counter(item.reason_code for item in record.decisions)
    source_statuses = Counter(item.status for item in record.source_availability)
    source_reasons = Counter(item.reason_code for item in record.source_availability)
    return {
        "fields_total": len(record.field_coverage),
        "fields_checked": coverage.get("checked", 0),
        "fields_absent": coverage.get("absence", 0),
        "atoms_total": len(record.atoms),
        "atoms_decided": len(record.decisions),
        "decision_coverage_ppm": _rate_ppm(
            len(record.decisions), len(record.atoms)
        ),
        "source_limited_atoms": sum(item.source_limited for item in record.decisions),
        "unavailable_atoms": outcomes.get("unavailable", 0),
        "corpus_truncated": record.corpus_truncated,
        "coverage_statuses": _distribution(coverage),
        "atom_outcomes": _distribution(outcomes),
        "atom_actions": _distribution(atom_actions),
        "field_actions": _distribution(field_actions),
        "decision_reasons": _distribution(reasons),
        "source_statuses": _distribution(source_statuses),
        "source_reasons": _distribution(source_reasons),
    }


def _omission_metrics(
    audit: OmissionAudit,
    publication: PublicationValidationReport,
    conflict_count: int,
) -> dict[str, Any]:
    conflict_fields = [
        item for item in audit.records if item.reason is OmissionReason.CONFLICTING
    ]
    return {
        "source_present_count": (
            len(audit.source_present_omissions)
            + len(publication.source_present_omissions)
        ),
        "conflict_field_count": len(conflict_fields),
        "conflict_record_count": sum(len(item.conflict_sha256s) for item in conflict_fields),
        "composition_conflict_count": conflict_count,
        "reasons": _distribution(
            Counter(
                [
                    item.reason.value
                    for item in audit.records
                    if item.reason is not None
                ]
                + [
                    item.reason.value
                    for item in publication.records
                    if item.reason.value != "present"
                ]
            )
        ),
    }


def _privacy_metrics(report: PrivacyScanReport, result: PipelineResult) -> dict[str, Any]:
    return {
        "status": report.status,
        "reason": report.reason,
        "checked": report.checked,
        "passed": report.passed,
        "withheld": len(report.withheld_candidate_ids),
        "public_card_hash_verified": report.scanned_card_sha256 == result.public_card_sha256,
        "artifact_hash_verified": True,
    }


def _provider_metrics(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise QualityReportError("run usage ledger is missing or unsafe")
    try:
        raw = dict(UsageLedger(path).audit_metrics())
    except Exception as exc:
        raise QualityReportError("usage ledger failed aggregate audit") from exc
    expected = {
        "paid_calls",
        "committed_usd",
        "global_halt",
        "attempt_count",
        "receipt_count",
        "token_receipt_count",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "retry_count",
        "latency_ms",
        "max_latency_ms",
        "providers",
        "attempt_statuses",
        "terminal_outcomes",
    }
    if set(raw) != expected:
        raise QualityReportError("usage ledger aggregate shape is invalid")
    _money(raw["committed_usd"])
    if not isinstance(raw["providers"], list) or raw["providers"] != sorted(set(raw["providers"])):
        raise QualityReportError("usage ledger provider summary is invalid")
    if not isinstance(raw["attempt_statuses"], dict) or not isinstance(raw["terminal_outcomes"], dict):
        raise QualityReportError("usage ledger outcome summaries are invalid")
    return {
        "ledger_count": 1,
        "paid_calls": raw["paid_calls"],
        "committed_usd": raw["committed_usd"],
        "global_halt": raw["global_halt"],
        "attempt_count": raw["attempt_count"],
        "receipt_count": raw["receipt_count"],
        "token_receipt_count": raw["token_receipt_count"],
        "prompt_tokens": raw["prompt_tokens"],
        "completion_tokens": raw["completion_tokens"],
        "total_tokens": raw["total_tokens"],
        "retry_count": raw["retry_count"],
        "latency_ms": raw["latency_ms"],
        "max_latency_ms": raw["max_latency_ms"],
        "providers": list(raw["providers"]),
        "attempt_statuses": _distribution(Counter(raw["attempt_statuses"])),
        "terminal_outcomes": _distribution(Counter(raw["terminal_outcomes"])),
    }


def _surface_digests(
    *,
    result: PipelineResult,
    public_card: Mapping[str, Any],
    artifact: CardArtifact,
    gates: Sequence[ClaimGateRecord],
    fact: FactReasonerRecord,
    content_fact: FactReasonerRecord,
    original_publication_fact: FactReasonerRecord,
    publication_validation: PublicationValidationReport,
    repair: PipelineRepairReport,
    risk_surface: str,
    provider: Mapping[str, Any],
    input_surface: str,
) -> dict[str, str]:
    audit_card = project_card(artifact)
    values = {
        field_path: get_field(audit_card, field_path)
        for field_path in CONTENT_FIELD_PATHS
    }
    decisions = {
        "gates": [record.content_sha256 for record in gates],
        "content_factreasoner": content_fact.content_sha256,
        "publication_factreasoner_original": (
            original_publication_fact.content_sha256
        ),
        "publication_validation": publication_validation.content_sha256,
        "publication_factreasoner_final": fact.content_sha256,
        "repair": repair.report_sha256,
    }
    validation = {
        "pipeline": result.validation.to_dict(),
        "lifecycle": audit_card["lifecycle"],
        "validation": audit_card["validation"],
    }
    return {
        "inputs": input_surface,
        "values": _digest(values),
        "bindings": _digest([item.to_dict() for item in artifact.bindings]),
        "artifact": result.artifact_sha256,
        "decisions": _digest(decisions),
        "validation": _digest(validation),
        "risk": risk_surface,
        "omission": _digest(
            {
                "audit": result.omission_audit_sha256,
                "publication": publication_validation.content_sha256,
            }
        ),
        "privacy": result.privacy.report_sha256,
        "cost_latency": _provider_surface(provider),
    }


def _aggregate(batch: _LoadedBatch) -> dict[str, Any]:
    successful = [
        item.record["metrics"]
        for item in batch.targets
        if item.record["metrics"] is not None
    ]
    failures = [
        item.record["failure_reason"]
        for item in batch.targets
        if item.record["status"] == "failed"
    ]
    providers = [item.provider for item in batch.targets if item.provider is not None]
    gates = []
    for index, gate in enumerate(GATE_ORDER):
        values = [item["claims"]["gates"][index] for item in successful]
        gates.append(
            {
                "gate": gate.value,
                "checked": sum(item["checked"] for item in values),
                "accepted": sum(item["accepted"] for item in values),
                "withheld": sum(item["withheld"] for item in values),
                "reasons": _merge_distributions(item["reasons"] for item in values),
            }
        )
    return {
        "requests_total": len(batch.targets),
        "succeeded": len(successful),
        "failed": len(failures),
        "failure_reasons": _distribution(Counter(failures)),
        "schema_export": {
            "schema_valid": sum(item["schema_export"]["schema_valid"] for item in successful),
            "public_projection_safe": sum(
                item["schema_export"]["public_projection_safe"] for item in successful
            ),
            "generated_validated": sum(
                item["schema_export"]["lifecycle_status"] == "generated_validated"
                for item in successful
            ),
            "artifact_bindings": sum(
                item["schema_export"]["artifact_binding_count"] for item in successful
            ),
            "artifact_derivations": sum(
                item["schema_export"]["artifact_derivation_count"] for item in successful
            ),
        },
        "fields": {
            "total": sum(item["fields"]["total"] for item in successful),
            "present": sum(item["fields"]["present"] for item in successful),
            "omitted": sum(item["fields"]["omitted"] for item in successful),
            "abstention_ppm": _rate_ppm(
                sum(item["fields"]["omitted"] for item in successful),
                sum(item["fields"]["total"] for item in successful),
            ),
            "source_present_omissions": sum(
                item["fields"]["source_present_omissions"] for item in successful
            ),
            "omission_reasons": _merge_distributions(
                item["fields"]["omission_reasons"] for item in successful
            ),
        },
        "sources": {
            "total": sum(item["sources"]["total"] for item in successful),
            "loaded": sum(item["sources"]["loaded"] for item in successful),
            "unavailable": sum(item["sources"]["unavailable"] for item in successful),
            "statuses": _merge_distributions(item["sources"]["statuses"] for item in successful),
            "reasons": _merge_distributions(item["sources"]["reasons"] for item in successful),
        },
        "claims": {
            "total": sum(item["claims"]["total"] for item in successful),
            "eligible": sum(item["claims"]["eligible"] for item in successful),
            "included": sum(item["claims"]["included"] for item in successful),
            "withheld": sum(item["claims"]["withheld"] for item in successful),
            "gates": gates,
        },
        "findings": {
            "total": sum(item["findings"]["total"] for item in successful),
            "codes": _merge_distributions(item["findings"]["codes"] for item in successful),
        },
        "factreasoner": _aggregate_fact(successful),
        "omissions": {
            "source_present_count": sum(
                item["omissions"]["source_present_count"] for item in successful
            ),
            "conflict_field_count": sum(
                item["omissions"]["conflict_field_count"] for item in successful
            ),
            "conflict_record_count": sum(
                item["omissions"]["conflict_record_count"] for item in successful
            ),
            "composition_conflict_count": sum(
                item["omissions"]["composition_conflict_count"] for item in successful
            ),
            "reasons": _merge_distributions(item["omissions"]["reasons"] for item in successful),
        },
        "risk": _aggregate_risk(successful),
        "privacy": {
            "completed": sum(item["privacy"]["status"] == "completed" for item in successful),
            "passed_without_withholding": sum(
                item["privacy"]["status"] == "completed" and item["privacy"]["withheld"] == 0
                for item in successful
            ),
            "checked": sum(item["privacy"]["checked"] for item in successful),
            "passed": sum(item["privacy"]["passed"] for item in successful),
            "withheld": sum(item["privacy"]["withheld"] for item in successful),
            "statuses": _distribution(Counter(item["privacy"]["status"] for item in successful)),
            "reasons": _distribution(Counter(item["privacy"]["reason"] for item in successful)),
        },
        "provider": _aggregate_provider(providers),
    }


def _aggregate_fact(successful: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    facts = [item["factreasoner"] for item in successful]
    numeric = (
        "fields_total",
        "fields_checked",
        "fields_absent",
        "atoms_total",
        "atoms_decided",
        "source_limited_atoms",
        "unavailable_atoms",
    )
    output = {key: sum(item[key] for item in facts) for key in numeric}
    output["decision_coverage_ppm"] = _rate_ppm(
        output["atoms_decided"], output["atoms_total"]
    )
    output["corpus_truncated_targets"] = sum(item["corpus_truncated"] for item in facts)
    for key in (
        "coverage_statuses",
        "atom_outcomes",
        "atom_actions",
        "field_actions",
        "decision_reasons",
        "source_statuses",
        "source_reasons",
    ):
        output[key] = _merge_distributions(item[key] for item in facts)
    return output


def _aggregate_risk(successful: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    risks = [item["risk"] for item in successful]
    numeric = (
        "context_count",
        "grounded_context_count",
        "publisher_context_count",
        "publisher_risk_count",
        "taxonomy_candidate_count",
        "taxonomy_mapped_count",
        "taxonomy_included_count",
        "taxonomy_withheld_count",
        "taxonomy_factreasoner_withheld_count",
        "applicability_total",
        "applicability_accepted",
        "applicability_withheld",
        "mapping_derivation_count",
        "exported_derivation_count",
        "ground_count",
        "input_claim_count",
        "supporting_source_count",
    )
    output = {key: sum(item[key] for item in risks) for key in numeric}
    output["catalog_available"] = sum(item["catalog_available"] for item in risks)
    output["catalog_sha256s"] = sorted(
        {
            item["catalog_sha256"]
            for item in risks
            if item["catalog_sha256"] is not None
        }
    )
    output["statuses"] = _distribution(Counter(item["status"] for item in risks))
    output["reasons"] = _distribution(Counter(item["reason"] for item in risks))
    return output


def _aggregate_provider(providers: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    numeric = (
        "ledger_count",
        "paid_calls",
        "attempt_count",
        "receipt_count",
        "token_receipt_count",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "retry_count",
        "latency_ms",
    )
    output = {key: sum(item[key] for item in providers) for key in numeric}
    output["committed_usd"] = format(
        sum((_money(item["committed_usd"]) for item in providers), Decimal("0")),
        "f",
    )
    output["global_halt"] = any(item["global_halt"] for item in providers)
    output["max_latency_ms"] = max(
        (item["max_latency_ms"] for item in providers), default=0
    )
    output["providers"] = sorted(
        {provider for item in providers for provider in item["providers"]}
    )
    output["attempt_statuses"] = _merge_distributions(
        item["attempt_statuses"] for item in providers
    )
    output["terminal_outcomes"] = _merge_distributions(
        item["terminal_outcomes"] for item in providers
    )
    return output


def _replay_stability(
    primary: _LoadedBatch,
    replay: _LoadedBatch | None,
) -> dict[str, Any]:
    if replay is None:
        return {
            "status": "not_provided",
            "request_order_stable": None,
            "targets": [],
            "aggregate_cost_latency_stable": None,
            "all_targets_stable": None,
        }
    comparisons = []
    all_stable = True
    for request, left, right in zip(primary.requests, primary.targets, replay.targets):
        left_record = left.record
        right_record = right.record
        left_success = left_record["surfaces"] is not None
        right_success = right_record["surfaces"] is not None
        if left_success and right_success:
            surfaces = {
                key: left_record["surfaces"][key] == right_record["surfaces"][key]
                for key in _SURFACE_KEYS
            }
            target_stable = all(surfaces.values()) and left_record["status"] == right_record["status"]
            comparison_status = "stable" if target_stable else "changed"
        elif not left_success and not right_success:
            target_stable = (
                left_record["status"] == right_record["status"]
                and left_record["failure_reason"] == right_record["failure_reason"]
            )
            surfaces = {key: None for key in _SURFACE_KEYS}
            comparison_status = "stable_failure" if target_stable else "changed_failure"
        else:
            target_stable = False
            surfaces = {key: None for key in _SURFACE_KEYS}
            comparison_status = "status_changed"
        all_stable = all_stable and target_stable
        comparisons.append(
            {
                "request": request,
                "comparison_status": comparison_status,
                "primary_status": left_record["status"],
                "replay_status": right_record["status"],
                "primary_failure_reason": left_record["failure_reason"],
                "replay_failure_reason": right_record["failure_reason"],
                **surfaces,
                "all_stable": target_stable,
            }
        )
    primary_provider = _aggregate_provider(
        [item.provider for item in primary.targets if item.provider is not None]
    )
    replay_provider = _aggregate_provider(
        [item.provider for item in replay.targets if item.provider is not None]
    )
    aggregate_stable = _provider_surface(primary_provider) == _provider_surface(replay_provider)
    all_stable = all_stable and aggregate_stable
    return {
        "status": "compared",
        "request_order_stable": True,
        "targets": comparisons,
        "aggregate_cost_latency_stable": aggregate_stable,
        "all_targets_stable": all_stable,
    }


def _provider_surface(provider: Mapping[str, Any]) -> str:
    return _digest(
        {
            "ledger_count": provider["ledger_count"],
            "paid_calls": provider["paid_calls"],
            "committed_usd": provider["committed_usd"],
            "global_halt": provider["global_halt"],
            "attempt_count": provider["attempt_count"],
            "receipt_count": provider["receipt_count"],
            "token_receipt_count": provider["token_receipt_count"],
            "prompt_tokens": provider["prompt_tokens"],
            "completion_tokens": provider["completion_tokens"],
            "total_tokens": provider["total_tokens"],
            "retry_count": provider["retry_count"],
            "latency_ms": provider["latency_ms"],
            "max_latency_ms": provider["max_latency_ms"],
            "providers": provider["providers"],
            "attempt_statuses": provider["attempt_statuses"],
            "terminal_outcomes": provider["terminal_outcomes"],
        }
    )


def _validate_report_payload(value: Any) -> None:
    item = _strict_object(
        value,
        {
            "report_version",
            "primary_batch_sha256",
            "replay_batch_sha256",
            "primary_batch_status",
            "replay_batch_status",
            "targets",
            "aggregate",
            "replay_stability",
        },
        "quality report payload",
    )
    if item["report_version"] != QUALITY_REPORT_VERSION:
        raise QualityReportError("quality report version is unsupported")
    _require_digest(item["primary_batch_sha256"], "primary batch digest")
    if item["replay_batch_sha256"] is not None:
        _require_digest(item["replay_batch_sha256"], "replay batch digest")
    if item["primary_batch_status"] not in _BATCH_STATUSES:
        raise QualityReportError("primary batch status is invalid")
    if item["replay_batch_status"] is not None and item["replay_batch_status"] not in _BATCH_STATUSES:
        raise QualityReportError("replay batch status is invalid")
    if not isinstance(item["targets"], list):
        raise QualityReportError("quality target records must be an array")
    for target in item["targets"]:
        _validate_target_record(target)
    requests = [target["request"] for target in item["targets"]]
    if len(requests) != len(set(requests)):
        raise QualityReportError("quality target requests are duplicated")
    expected_primary_status = (
        "completed_with_failures"
        if any(target["status"] == "failed" for target in item["targets"])
        else "completed"
    )
    if item["primary_batch_status"] != expected_primary_status:
        raise QualityReportError("primary batch status disagrees with target outcomes")
    loaded_targets = tuple(
        _LoadedTarget(
            record=dict(target),
            provider=(
                None
                if target["metrics"] is None
                else target["metrics"]["provider"]
            ),
        )
        for target in item["targets"]
    )
    reconstructed = _LoadedBatch(
        status=item["primary_batch_status"],
        requests=tuple(requests),
        targets=loaded_targets,
        batch_sha256=item["primary_batch_sha256"],
    )
    _validate_aggregate(item["aggregate"], len(item["targets"]))
    if item["aggregate"] != _aggregate(reconstructed):
        raise QualityReportError("aggregate metrics differ from per-target metrics")
    batch_components = []
    for target in item["targets"]:
        if target["status"] == "failed":
            batch_components.append(
                {
                    "request": target["request"],
                    "status": "failed",
                    "reason": target["failure_reason"],
                }
            )
        else:
            batch_components.append(
                {
                    "request": target["request"],
                    "status": target["status"],
                    "run_sha256": target["run_sha256"],
                    "cost_latency_sha256": target["surfaces"]["cost_latency"],
                }
            )
    if item["primary_batch_sha256"] != _digest(
        {
            "batch_request": {"targets": requests},
            "batch_status": item["primary_batch_status"],
            "targets": batch_components,
        }
    ):
        raise QualityReportError("primary batch digest differs from target records")
    _validate_replay(item["replay_stability"], item["targets"])
    has_replay = item["replay_batch_sha256"] is not None
    if has_replay != (item["replay_batch_status"] is not None):
        raise QualityReportError("replay batch metadata is incomplete")
    if has_replay != (item["replay_stability"]["status"] == "compared"):
        raise QualityReportError("replay stability status is inconsistent")
    if has_replay:
        replay_failed = any(
            entry["replay_status"] == "failed"
            for entry in item["replay_stability"]["targets"]
        )
        expected_replay_status = (
            "completed_with_failures" if replay_failed else "completed"
        )
        if item["replay_batch_status"] != expected_replay_status:
            raise QualityReportError(
                "replay batch status disagrees with target outcomes"
            )


def _validate_target_record(value: Any) -> None:
    item = _strict_object(
        value,
        {
            "request",
            "status",
            "failure_reason",
            "target",
            "run_sha256",
            "metrics",
            "surfaces",
        },
        "target quality record",
    )
    model_id, revision = parse_target_request(item["request"], None)
    canonical_request = model_id if revision is None else f"{model_id}@{revision}"
    if item["request"] != canonical_request:
        raise QualityReportError("target quality request is not canonical")
    if item["status"] == "failed":
        _require_code(item["failure_reason"], "target failure reason")
        if any(item[name] is not None for name in ("target", "run_sha256", "metrics", "surfaces")):
            raise QualityReportError("failed target quality record claims run output")
        return
    if item["status"] not in _SUCCESS_STATUSES or item["failure_reason"] is not None:
        raise QualityReportError("successful target quality status is invalid")
    target = _strict_object(item["target"], {"model_id", "revision"}, "quality target")
    try:
        resolved_target = TargetIdentity.from_dict(target)
    except Exception as exc:
        raise QualityReportError("quality target is not an exact identity") from exc
    if resolved_target.model_id != model_id:
        raise QualityReportError("quality target model differs from request")
    _require_digest(item["run_sha256"], "target run digest")
    _validate_target_metrics(item["metrics"])
    if item["metrics"]["schema_export"]["lifecycle_status"] != item["status"]:
        raise QualityReportError("target lifecycle differs from schema/export metrics")
    surfaces = _strict_object(item["surfaces"], set(_SURFACE_KEYS), "target surfaces")
    for name in _SURFACE_KEYS:
        _require_digest(surfaces[name], f"target {name} surface")


def _validate_target_metrics(value: Any) -> None:
    item = _strict_object(
        value,
        {
            "schema_export",
            "fields",
            "sources",
            "claims",
            "findings",
            "factreasoner",
            "omissions",
            "risk",
            "privacy",
            "provider",
        },
        "target metrics",
    )
    schema = _strict_object(
        item["schema_export"],
        {
            "schema_valid",
            "public_projection_safe",
            "contract_version",
            "lifecycle_status",
            "artifact_binding_count",
            "artifact_derivation_count",
        },
        "schema/export metrics",
    )
    if schema["schema_valid"] is not True or schema["public_projection_safe"] is not True:
        raise QualityReportError("successful report must have verified schema and projection")
    if (
        schema["contract_version"] != CONTRACT_VERSION
        or schema["lifecycle_status"] not in _SUCCESS_STATUSES
    ):
        raise QualityReportError("schema/export contract or lifecycle is invalid")
    _nonnegative_many(schema, ("artifact_binding_count", "artifact_derivation_count"))

    fields = _strict_object(
        item["fields"],
        {
            "total",
            "present",
            "omitted",
            "abstention_ppm",
            "source_present_omissions",
            "omission_reasons",
        },
        "field metrics",
    )
    _nonnegative_many(fields, ("total", "present", "omitted", "abstention_ppm", "source_present_omissions"))
    if fields["present"] + fields["omitted"] != fields["total"] or fields["abstention_ppm"] > 1_000_000:
        raise QualityReportError("field coverage counts are inconsistent")
    _validate_distribution(fields["omission_reasons"], expected_total=fields["omitted"])

    sources = _strict_object(
        item["sources"], {"total", "loaded", "unavailable", "statuses", "reasons"}, "source metrics"
    )
    _nonnegative_many(sources, ("total", "loaded", "unavailable"))
    if sources["loaded"] + sources["unavailable"] != sources["total"]:
        raise QualityReportError("source availability counts are inconsistent")
    _validate_distribution(sources["statuses"], expected_total=sources["total"])
    _validate_distribution(sources["reasons"], expected_total=sources["total"])

    claims = _strict_object(item["claims"], {"total", "eligible", "included", "withheld", "gates"}, "claim metrics")
    _nonnegative_many(claims, ("total", "eligible", "included", "withheld"))
    if claims["included"] > claims["eligible"] or claims["included"] + claims["withheld"] != claims["total"]:
        raise QualityReportError("claim counts are inconsistent")
    _validate_gates(claims["gates"], claims["total"])

    findings = _strict_object(item["findings"], {"total", "codes", "records"}, "finding metrics")
    _nonnegative(findings["total"], "finding total")
    _validate_distribution(findings["codes"], expected_total=findings["total"])
    if not isinstance(findings["records"], list) or len(findings["records"]) != findings["total"]:
        raise QualityReportError("quality finding records are incomplete")
    prior = None
    for finding in findings["records"]:
        finding = _strict_object(finding, {"candidate_id", "field_path", "code", "reason"}, "quality finding")
        if not _CLAIM_RE.fullmatch(finding["candidate_id"]) or finding["code"] not in _FINDING_CODES:
            raise QualityReportError("quality finding identity or code is invalid")
        if not _FIELD_RE.fullmatch(finding["field_path"]):
            raise QualityReportError("quality finding field path is invalid")
        _require_code(finding["reason"], "quality finding reason")
        key = (finding["candidate_id"], finding["code"])
        if prior is not None and key <= prior:
            raise QualityReportError("quality findings are not sorted and unique")
        prior = key

    _validate_fact(item["factreasoner"], aggregate=False)
    _validate_omissions(item["omissions"])
    _validate_risk(item["risk"], aggregate=False)
    privacy = _strict_object(
        item["privacy"],
        {
            "status",
            "reason",
            "checked",
            "passed",
            "withheld",
            "public_card_hash_verified",
            "artifact_hash_verified",
        },
        "privacy metrics",
    )
    if privacy["status"] not in {"completed", "failed"}:
        raise QualityReportError("privacy metric status is invalid")
    _require_code(privacy["reason"], "privacy metric reason")
    _nonnegative_many(privacy, ("checked", "passed", "withheld"))
    if privacy["passed"] + privacy["withheld"] > privacy["checked"]:
        raise QualityReportError("privacy metric outcomes exceed checks")
    if privacy["public_card_hash_verified"] is not True or privacy["artifact_hash_verified"] is not True:
        raise QualityReportError("privacy/export hashes are not verified")
    _validate_provider(item["provider"])


def _validate_gates(value: Any, expected_checked: int) -> None:
    if not isinstance(value, list) or len(value) != len(GATE_ORDER):
        raise QualityReportError("claim metrics require four gate records")
    for gate, entry in zip(GATE_ORDER, value):
        entry = _strict_object(entry, {"gate", "checked", "accepted", "withheld", "reasons"}, "gate metrics")
        if entry["gate"] != gate.value:
            raise QualityReportError("gate metric order is invalid")
        _nonnegative_many(entry, ("checked", "accepted", "withheld"))
        if entry["checked"] != expected_checked or entry["accepted"] + entry["withheld"] != entry["checked"]:
            raise QualityReportError("gate metric outcomes are inconsistent")
        _validate_distribution(entry["reasons"], expected_total=entry["checked"])


def _validate_fact(value: Any, *, aggregate: bool) -> None:
    numeric = {
        "fields_total",
        "fields_checked",
        "fields_absent",
        "atoms_total",
        "atoms_decided",
        "decision_coverage_ppm",
        "source_limited_atoms",
        "unavailable_atoms",
    }
    flag = "corpus_truncated_targets" if aggregate else "corpus_truncated"
    distributions = {
        "coverage_statuses",
        "atom_outcomes",
        "atom_actions",
        "field_actions",
        "decision_reasons",
        "source_statuses",
        "source_reasons",
    }
    item = _strict_object(value, numeric | {flag} | distributions, "FactReasoner metrics")
    _nonnegative_many(item, numeric)
    if item["fields_checked"] + item["fields_absent"] != item["fields_total"]:
        raise QualityReportError("FactReasoner field coverage is inconsistent")
    if (
        item["atoms_decided"] != item["atoms_total"]
        or item["decision_coverage_ppm"]
        != _rate_ppm(item["atoms_decided"], item["atoms_total"])
    ):
        raise QualityReportError("FactReasoner atom coverage is inconsistent")
    if aggregate:
        _nonnegative(item[flag], flag)
    elif not isinstance(item[flag], bool):
        raise QualityReportError("FactReasoner corpus truncation flag is invalid")
    _validate_distribution(item["coverage_statuses"], expected_total=item["fields_total"])
    for key in ("atom_outcomes", "atom_actions", "decision_reasons"):
        _validate_distribution(item[key], expected_total=item["atoms_total"])
    _validate_distribution(item["field_actions"], expected_total=item["fields_checked"])
    _validate_distribution(item["source_statuses"])
    _validate_distribution(item["source_reasons"], expected_total=item["source_statuses"]["total"])


def _validate_omissions(value: Any) -> None:
    item = _strict_object(
        value,
        {
            "source_present_count",
            "conflict_field_count",
            "conflict_record_count",
            "composition_conflict_count",
            "reasons",
        },
        "omission metrics",
    )
    _nonnegative_many(item, ("source_present_count", "conflict_field_count", "conflict_record_count", "composition_conflict_count"))
    _validate_distribution(item["reasons"])


def _validate_risk(value: Any, *, aggregate: bool) -> None:
    numeric = {
        "context_count",
        "grounded_context_count",
        "publisher_context_count",
        "publisher_risk_count",
        "taxonomy_candidate_count",
        "taxonomy_mapped_count",
        "taxonomy_included_count",
        "taxonomy_withheld_count",
        "taxonomy_factreasoner_withheld_count",
        "applicability_total",
        "applicability_accepted",
        "applicability_withheld",
        "mapping_derivation_count",
        "exported_derivation_count",
        "ground_count",
        "input_claim_count",
        "supporting_source_count",
    }
    if aggregate:
        item = _strict_object(
            value,
            numeric
            | {
                "catalog_available",
                "catalog_sha256s",
                "statuses",
                "reasons",
            },
            "aggregate risk metrics",
        )
        _nonnegative(item["catalog_available"], "aggregate risk catalog count")
        if (
            not isinstance(item["catalog_sha256s"], list)
            or item["catalog_sha256s"] != sorted(set(item["catalog_sha256s"]))
        ):
            raise QualityReportError("aggregate risk catalog identities are invalid")
        for digest in item["catalog_sha256s"]:
            _require_digest(digest, "aggregate risk catalog digest")
        _validate_distribution(item["statuses"])
        _validate_distribution(item["reasons"], expected_total=item["statuses"]["total"])
    else:
        item = _strict_object(
            value,
            numeric
            | {
                "catalog_available",
                "catalog_sha256",
                "status",
                "reason",
            },
            "risk metrics",
        )
        if not isinstance(item["catalog_available"], bool) or item["status"] not in {"completed", "unavailable"}:
            raise QualityReportError("risk availability or status is invalid")
        if item["catalog_available"] != (item["catalog_sha256"] is not None):
            raise QualityReportError("risk catalog availability is inconsistent")
        if item["catalog_sha256"] is not None:
            _require_digest(item["catalog_sha256"], "risk catalog digest")
        _require_code(item["reason"], "risk metric reason")
    _nonnegative_many(item, numeric)
    if (
        item["taxonomy_included_count"] + item["taxonomy_withheld_count"] != item["taxonomy_candidate_count"]
        or item["taxonomy_mapped_count"]
        - item["taxonomy_factreasoner_withheld_count"]
        != item["taxonomy_included_count"]
        or item["taxonomy_mapped_count"] > item["taxonomy_candidate_count"]
        or item["applicability_accepted"] + item["applicability_withheld"] != item["applicability_total"]
        or item["exported_derivation_count"] > item["mapping_derivation_count"]
    ):
        raise QualityReportError("risk mapping counts are inconsistent")


def _validate_provider(value: Any) -> None:
    numeric = {
        "ledger_count",
        "paid_calls",
        "attempt_count",
        "receipt_count",
        "token_receipt_count",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "retry_count",
        "latency_ms",
        "max_latency_ms",
    }
    item = _strict_object(
        value,
        numeric
        | {
            "committed_usd",
            "global_halt",
            "providers",
            "attempt_statuses",
            "terminal_outcomes",
        },
        "provider metrics",
    )
    _nonnegative_many(item, numeric)
    _money(item["committed_usd"])
    if not isinstance(item["global_halt"], bool):
        raise QualityReportError("provider global halt flag is invalid")
    if (
        not isinstance(item["providers"], list)
        or item["providers"] != sorted(set(item["providers"]))
        or any(not isinstance(entry, str) or not entry or len(entry) > 128 for entry in item["providers"])
    ):
        raise QualityReportError("provider list is invalid")
    _validate_distribution(item["attempt_statuses"], expected_total=item["attempt_count"])
    _validate_distribution(item["terminal_outcomes"], expected_total=item["receipt_count"])


def _validate_aggregate(value: Any, request_count: int) -> None:
    item = _strict_object(
        value,
        {
            "requests_total",
            "succeeded",
            "failed",
            "failure_reasons",
            "schema_export",
            "fields",
            "sources",
            "claims",
            "findings",
            "factreasoner",
            "omissions",
            "risk",
            "privacy",
            "provider",
        },
        "aggregate metrics",
    )
    _nonnegative_many(item, ("requests_total", "succeeded", "failed"))
    if item["requests_total"] != request_count or item["succeeded"] + item["failed"] != request_count:
        raise QualityReportError("aggregate request counts are inconsistent")
    _validate_distribution(item["failure_reasons"], expected_total=item["failed"])
    schema = _strict_object(
        item["schema_export"],
        {"schema_valid", "public_projection_safe", "generated_validated", "artifact_bindings", "artifact_derivations"},
        "aggregate schema/export metrics",
    )
    _nonnegative_many(schema, schema.keys())
    if schema["schema_valid"] > item["succeeded"] or schema["public_projection_safe"] > item["succeeded"]:
        raise QualityReportError("aggregate schema/export counts exceed successful targets")
    fields = _strict_object(item["fields"], {"total", "present", "omitted", "abstention_ppm", "source_present_omissions", "omission_reasons"}, "aggregate field metrics")
    _nonnegative_many(fields, ("total", "present", "omitted", "abstention_ppm", "source_present_omissions"))
    if fields["present"] + fields["omitted"] != fields["total"] or fields["abstention_ppm"] > 1_000_000:
        raise QualityReportError("aggregate field counts are inconsistent")
    _validate_distribution(fields["omission_reasons"], expected_total=fields["omitted"])
    sources = _strict_object(item["sources"], {"total", "loaded", "unavailable", "statuses", "reasons"}, "aggregate source metrics")
    _nonnegative_many(sources, ("total", "loaded", "unavailable"))
    if sources["loaded"] + sources["unavailable"] != sources["total"]:
        raise QualityReportError("aggregate source counts are inconsistent")
    _validate_distribution(sources["statuses"], expected_total=sources["total"])
    _validate_distribution(sources["reasons"], expected_total=sources["total"])
    claims = _strict_object(item["claims"], {"total", "eligible", "included", "withheld", "gates"}, "aggregate claim metrics")
    _nonnegative_many(claims, ("total", "eligible", "included", "withheld"))
    if claims["included"] > claims["eligible"] or claims["included"] + claims["withheld"] != claims["total"]:
        raise QualityReportError("aggregate claim counts are inconsistent")
    _validate_gates(claims["gates"], claims["total"])
    findings = _strict_object(item["findings"], {"total", "codes"}, "aggregate findings")
    _nonnegative(findings["total"], "aggregate finding total")
    _validate_distribution(findings["codes"], expected_total=findings["total"])
    _validate_fact(item["factreasoner"], aggregate=True)
    _validate_omissions(item["omissions"])
    _validate_risk(item["risk"], aggregate=True)
    privacy = _strict_object(item["privacy"], {"completed", "passed_without_withholding", "checked", "passed", "withheld", "statuses", "reasons"}, "aggregate privacy metrics")
    _nonnegative_many(privacy, ("completed", "passed_without_withholding", "checked", "passed", "withheld"))
    _validate_distribution(privacy["statuses"], expected_total=item["succeeded"])
    _validate_distribution(privacy["reasons"], expected_total=item["succeeded"])
    _validate_provider(item["provider"])


def _validate_replay(value: Any, targets: Sequence[Mapping[str, Any]]) -> None:
    requests = [entry["request"] for entry in targets]
    item = _strict_object(
        value,
        {"status", "request_order_stable", "targets", "aggregate_cost_latency_stable", "all_targets_stable"},
        "replay stability",
    )
    if item["status"] == "not_provided":
        if item["targets"] != [] or any(item[name] is not None for name in ("request_order_stable", "aggregate_cost_latency_stable", "all_targets_stable")):
            raise QualityReportError("unpaired replay stability must be empty")
        return
    if item["status"] != "compared" or item["request_order_stable"] is not True:
        raise QualityReportError("paired replay stability status is invalid")
    if not isinstance(item["targets"], list) or len(item["targets"]) != len(requests):
        raise QualityReportError("paired replay target coverage is incomplete")
    if [entry.get("request") if isinstance(entry, dict) else None for entry in item["targets"]] != list(requests):
        raise QualityReportError("paired replay target order is inconsistent")
    for primary, entry in zip(targets, item["targets"]):
        entry = _strict_object(
            entry,
            {
                "request",
                "comparison_status",
                "primary_status",
                "replay_status",
                "primary_failure_reason",
                "replay_failure_reason",
                *_SURFACE_KEYS,
                "all_stable",
            },
            "target replay stability",
        )
        if entry["comparison_status"] not in {"stable", "changed", "stable_failure", "changed_failure", "status_changed"}:
            raise QualityReportError("target replay comparison status is invalid")
        if entry["primary_status"] not in _SUCCESS_STATUSES | {"failed"} or entry["replay_status"] not in _SUCCESS_STATUSES | {"failed"}:
            raise QualityReportError("target replay lifecycle status is invalid")
        if entry["primary_status"] != primary["status"]:
            raise QualityReportError("replay comparison primary lifecycle is stale")
        for status_key, reason_key in (
            ("primary_status", "primary_failure_reason"),
            ("replay_status", "replay_failure_reason"),
        ):
            if entry[status_key] == "failed":
                _require_code(entry[reason_key], "replay failure reason")
            elif entry[reason_key] is not None:
                raise QualityReportError(
                    "successful replay comparison claims a failure reason"
                )
        if entry["primary_failure_reason"] != primary["failure_reason"]:
            raise QualityReportError("replay primary failure reason is stale")
        if not isinstance(entry["all_stable"], bool):
            raise QualityReportError("target replay all_stable flag is invalid")
        comparable = entry["primary_status"] != "failed" and entry["replay_status"] != "failed"
        for key in _SURFACE_KEYS:
            if comparable and not isinstance(entry[key], bool):
                raise QualityReportError("comparable replay surface must be boolean")
            if not comparable and entry[key] is not None:
                raise QualityReportError("failed replay surface must be unavailable")
        if comparable:
            expected_stable = (
                entry["primary_status"] == entry["replay_status"]
                and all(entry[key] for key in _SURFACE_KEYS)
            )
            expected_comparison = "stable" if expected_stable else "changed"
        elif entry["primary_status"] == "failed" and entry["replay_status"] == "failed":
            expected_stable = (
                entry["primary_failure_reason"]
                == entry["replay_failure_reason"]
            )
            expected_comparison = (
                "stable_failure" if expected_stable else "changed_failure"
            )
        else:
            expected_stable = False
            expected_comparison = "status_changed"
        if (
            entry["all_stable"] != expected_stable
            or entry["comparison_status"] != expected_comparison
        ):
            raise QualityReportError("target replay derived flags are inconsistent")
    if not isinstance(item["aggregate_cost_latency_stable"], bool) or not isinstance(item["all_targets_stable"], bool):
        raise QualityReportError("aggregate replay flags are invalid")
    if item["all_targets_stable"] != (
        item["aggregate_cost_latency_stable"]
        and all(entry["all_stable"] for entry in item["targets"])
    ):
        raise QualityReportError("aggregate replay stability is inconsistent")


def _distribution(counter: Mapping[str, int]) -> dict[str, Any]:
    entries = [
        {"key": str(key), "count": int(counter[key])}
        for key in sorted(counter)
        if int(counter[key]) > 0
    ]
    return {"total": sum(item["count"] for item in entries), "entries": entries}


def _merge_distributions(values: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    for value in values:
        _validate_distribution(value)
        for entry in value["entries"]:
            counter[entry["key"]] += entry["count"]
    return _distribution(counter)


def _validate_distribution(value: Any, expected_total: int | None = None) -> None:
    item = _strict_object(value, {"total", "entries"}, "count distribution")
    _nonnegative(item["total"], "count distribution total")
    if not isinstance(item["entries"], list):
        raise QualityReportError("count distribution entries must be an array")
    keys = []
    count = 0
    for entry in item["entries"]:
        entry = _strict_object(entry, {"key", "count"}, "count entry")
        _require_code(entry["key"], "count entry key")
        _nonnegative(entry["count"], "count entry count")
        if entry["count"] == 0:
            raise QualityReportError("count distribution cannot contain zero entries")
        keys.append(entry["key"])
        count += entry["count"]
    if keys != sorted(set(keys)) or count != item["total"]:
        raise QualityReportError("count distribution is not canonical")
    if expected_total is not None and item["total"] != expected_total:
        raise QualityReportError("count distribution total is inconsistent")


def _rate_ppm(numerator: int, denominator: int) -> int:
    return 0 if denominator == 0 else numerator * 1_000_000 // denominator


def _money(value: Any) -> Decimal:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise QualityReportError("provider cost is invalid")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise QualityReportError("provider cost is invalid") from exc
    if not parsed.is_finite() or parsed < 0:
        raise QualityReportError("provider cost is invalid")
    return parsed


def _nonnegative_many(value: Mapping[str, Any], keys: Iterable[str]) -> None:
    for key in keys:
        _nonnegative(value[key], key)


def _nonnegative(value: Any, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise QualityReportError(f"{label} must be a non-negative integer")


def _require_code(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _CODE_RE.fullmatch(value):
        raise QualityReportError(f"{label} is invalid")
    return value


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
        raise QualityReportError(f"{label} is invalid")
    return value


def _strict_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise QualityReportError(f"{label} has an invalid closed shape")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise QualityReportError("quality report value is not finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _strict_json(raw: bytes, label: str) -> Any:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
        _reject_overflow_numbers(value)
    except (UnicodeDecodeError, json.JSONDecodeError, QualityReportError, RecursionError, ValueError):
        raise QualityReportError(f"{label} is not strict UTF-8 JSON") from None
    return value


def _read_canonical_object(path: Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise QualityReportError(f"{label} is missing or unsafe")
    raw = path.read_bytes()
    value = _strict_json(raw, label)
    if not isinstance(value, dict) or raw != _canonical(value) + b"\n":
        raise QualityReportError(f"{label} is not a canonical object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise QualityReportError("JSON contains a duplicate key")
        output[key] = value
    return output


def _reject_nonfinite(value: str) -> None:
    raise QualityReportError(f"JSON contains a non-finite constant: {value}")


def _reject_overflow_numbers(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise QualityReportError("JSON contains a non-finite number")
    if isinstance(value, list):
        for item in value:
            _reject_overflow_numbers(item)
    elif isinstance(value, dict):
        for item in value.values():
            _reject_overflow_numbers(item)


def _safe_relative(value: Any) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise QualityReportError("batch artifact path is invalid")
    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value or any(part in {"", ".", ".."} for part in path.parts):
        raise QualityReportError("batch artifact path is not normalized relative POSIX")
    return path


def _safe_child(
    root: Path,
    relative: PurePosixPath,
    *,
    require_file: bool = False,
    require_directory: bool = False,
) -> Path:
    path = root.joinpath(*relative.parts)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise QualityReportError("batch artifact path contains a symbolic link")
    try:
        path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise QualityReportError("batch artifact escapes its batch directory") from exc
    if require_file and not path.is_file():
        raise QualityReportError("batch artifact file is missing")
    if require_directory and not path.is_dir():
        raise QualityReportError("batch target directory is missing")
    return path


def _is_within(path: PurePosixPath, parent: PurePosixPath) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _assert_body_free(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or key.casefold() in _BANNED_REPORT_KEYS:
                raise QualityReportError("quality report contains a body-bearing key")
            _assert_body_free(item)
    elif isinstance(value, list):
        for item in value:
            _assert_body_free(item)
    elif isinstance(value, str):
        if (
            any(ord(character) < 32 for character in value)
            or _LOCAL_PATH_RE.search(value)
            or _ABSOLUTE_PATH_RE.search(value)
        ):
            raise QualityReportError("quality report contains machine-local text")


__all__ = [
    "QUALITY_REPORT_VERSION",
    "QualityReport",
    "QualityReportError",
    "build_quality_report",
    "load_quality_report",
    "serialize_quality_report",
    "write_quality_report",
]
