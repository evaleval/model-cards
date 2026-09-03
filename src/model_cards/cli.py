"""Offline command-line interface for building and inspecting model cards."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import sys
import tempfile
from typing import Any, Sequence

from .artifact import CardArtifact, project_card
from .bindings import build_artifact
from .claim_gate import ClaimGateRecord, verify_claim_gate_record
from .models import RelationToTarget, ReviewAction
from .field_repair import FieldRepairRecord
from .findings import OmissionAudit
from .family_risk import FamilyRiskAuthorizationReport
from .hf_adapter import HuggingFaceHubAdapter
from .official_discovery import (
    discover_official_sources,
    exact_target_declaration_record_ids,
    replay_official_discovery,
)
from .official_http import StdlibOfficialSourceAdapter
from .official_sources import (
    DEFAULT_MAX_SOURCES,
    RelationAssertion,
    collect_official_sources,
    replay_official_sources,
)
from .orchestration import (
    ORCHESTRATION_MANIFEST_FILENAME,
    OrchestrationError,
    run_provider_assisted_pipeline,
)
from .factreasoner import FactReasonerRecord
from .pipeline import (
    PipelineResult,
    PrivacyScanReport,
    run_offline_pipeline,
    verify_pipeline_result,
)
from .provider import (
    MissingCredentialError,
    PINNED_PROVIDER,
    ProviderError,
    ProviderRouteError,
    ProviderTerminalAttemptError,
    ProviderUncertainError,
    RetryExhaustedError,
    TransportUncertainError,
)
from .provider_adapters import summarize_aggregate_budget
from .provider_execution import (
    PROVIDER_EXECUTION_MANIFEST_FILENAME,
    ProviderExecutionRunEvidence,
)
from .quality_report import (
    QualityReportError,
    build_quality_report,
    write_quality_report,
)
from .public_export import export_public_card
from .publication import project_publication_card
from .publication_contract import build_publication_schema
from .publication_schema import publication_coverage, validate_publication_card
from .render import save_html, save_json
from .review import append_review, load_artifact, save_artifact
from .publication_validation import PublicationValidationReport
from .review_audit import ReviewClosureEvidence, audit_reviewed_candidate
from .risk_mapping import load_pinned_nexus_catalog
from .run_ledger import BudgetCapError, LedgerError, UncertainSendError
from .run_summary import (
    AUDIT_VIEW_FILENAME,
    USAGE_SUMMARY_FILENAME,
    RunSummaryError,
    write_run_summaries,
)
from .run_state import RunManifest
from .schema import (
    CONTRACT_VERSION,
    canonical_field_path,
    get_field,
    validate_field_path,
    validate_public_card,
)
from .scholarly_discovery import (
    DEFAULT_MAX_HINTS as DEFAULT_MAX_SCHOLARLY_HINTS,
    SCHOLARLY_DISCOVERY_FILENAME,
    StdlibScholarlyDiscoveryTransport,
    discover_scholarly_sources,
    load_scholarly_discovery,
)
from .source_bundle import (
    BundleManifest,
    collect_hf_source_bundle,
    parse_target_request,
    replay_source_bundle,
)
from .source_state import load_source_state


_EXACT_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SAFE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_PROVIDER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/+()-]{0,127}$")
_AGGREGATE_BUDGET_FILENAME = "aggregate-budget.jsonl"
_AGGREGATE_BUDGET_SUMMARY_FILENAME = "aggregate-budget-summary.json"
_MAX_OFFICIAL_SOURCES_WITH_SCHOLARLY_HINTS = (
    DEFAULT_MAX_SOURCES + DEFAULT_MAX_SCHOLARLY_HINTS
)


class CliCommandError(ValueError):
    """One public, path-free CLI error code."""

    def __init__(self, code: str):
        if not isinstance(code, str) or not _SAFE_CODE_RE.fullmatch(code):
            raise ValueError("CLI error code is invalid")
        super().__init__(code)
        self.code = code


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("JSON object contains duplicate keys")
        output[key] = value
    return output


def _strict_json_bytes(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise ValueError("input is not UTF-8 JSON") from exc


def _json_line(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _print_json(value: Any) -> None:
    print(_json_line(value))


def _safe_relative_name(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise CliCommandError("unsafe_artifact_name")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise CliCommandError("unsafe_artifact_name")
    return value


def _new_path(value: str, *, inputs: tuple[Path, ...] = ()) -> Path:
    path = Path(value)
    if any(path.resolve() == item.resolve() for item in inputs):
        raise ValueError("output must differ from its input")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    return path


def _read_object(path: Path) -> dict:
    value = _strict_json_bytes(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError("input root must be a JSON object")
    return value


def _requested_target(model_id: str, revision: str | None) -> tuple[str, str | None]:
    try:
        return parse_target_request(model_id, revision)
    except (TypeError, ValueError) as exc:
        raise CliCommandError("invalid_target_request") from exc


def _provider_mode(output: Path, provider: str | None) -> str | None:
    if provider is not None and (
        not isinstance(provider, str) or not _PROVIDER_NAME_RE.fullmatch(provider)
    ):
        raise CliCommandError("invalid_provider")
    admission = output / ORCHESTRATION_MANIFEST_FILENAME
    run_manifest = output / "run-manifest.json"
    if provider is None and (admission.exists() or admission.is_symlink()):
        raise CliCommandError("provider_mode_conflict")
    if provider is not None and (
        run_manifest.exists() or run_manifest.is_symlink()
    ) and not admission.is_file():
        raise CliCommandError("provider_mode_conflict")
    return provider


def _require_requested_bundle(
    manifest: BundleManifest,
    model_id: str,
    requested_revision: str | None,
) -> None:
    if manifest.target.model_id != model_id:
        raise CliCommandError("target_mismatch")
    if requested_revision is None:
        if manifest.requested_revision is not None:
            raise CliCommandError("target_mismatch")
    elif _EXACT_REVISION_RE.fullmatch(requested_revision):
        if manifest.target.revision != requested_revision:
            raise CliCommandError("target_mismatch")
    elif manifest.requested_revision != requested_revision:
        raise CliCommandError("target_mismatch")


def _read_bundle_for_request(
    bundle_directory: Path,
    model_id: str,
    requested_revision: str | None,
    *,
    invalid_code: str,
):
    try:
        bundle = replay_source_bundle(bundle_directory)
    except Exception as exc:
        raise CliCommandError(invalid_code) from exc
    _require_requested_bundle(bundle.manifest, model_id, requested_revision)
    return bundle


def _bundle_manifest_bytes(manifest: BundleManifest) -> bytes:
    return (_json_line(manifest.to_dict()) + "\n").encode("utf-8")


def _copy_verified_bundle(source: Path, destination: Path) -> None:
    temporary_root = Path(
        tempfile.mkdtemp(prefix=".source-bundle-copy-", dir=str(destination.parent))
    )
    candidate = temporary_root / "bundle"
    published = False
    try:
        shutil.copytree(source, candidate)
        replay_source_bundle(candidate)
        os.rename(candidate, destination)
        published = True
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
    if not published:  # pragma: no cover - defensive; the original exception wins
        raise CliCommandError("offline_bundle_copy_failed")


def _copy_verified_official_bundle(
    source: Path,
    destination: Path,
    *,
    expected_target: Any,
    expected_hf_bundle_id: str,
) -> None:
    temporary_root = Path(
        tempfile.mkdtemp(prefix=".official-bundle-copy-", dir=str(destination.parent))
    )
    candidate = temporary_root / "bundle"
    published = False
    try:
        shutil.copytree(source, candidate)
        replayed = replay_official_sources(candidate, expected_target=expected_target)
        if replayed.manifest.source_bundle_id != expected_hf_bundle_id:
            raise CliCommandError("official_bundle_target_mismatch")
        os.rename(candidate, destination)
        published = True
    finally:
        if temporary_root.exists():
            shutil.rmtree(temporary_root)
    if not published:  # pragma: no cover - defensive; original exception wins
        raise CliCommandError("official_bundle_copy_failed")


def _environment_hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def _verify_existing_run_target(output: Path, manifest: BundleManifest) -> None:
    run_manifest_path = output / "run-manifest.json"
    if not run_manifest_path.exists() and not run_manifest_path.is_symlink():
        return
    try:
        run_manifest = RunManifest.from_dict(_read_object(run_manifest_path))
    except Exception as exc:
        raise CliCommandError("existing_run_invalid") from exc
    if run_manifest.target.to_dict() != manifest.target.to_dict():
        raise CliCommandError("target_mismatch")


def _prepare_generation_bundle(
    *,
    model_id: str,
    requested_revision: str | None,
    output: Path,
    offline_bundle: Path | None,
) -> Path:
    offline = None
    if offline_bundle is not None:
        offline = _read_bundle_for_request(
            offline_bundle,
            model_id,
            requested_revision,
            invalid_code="offline_bundle_invalid",
        )
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise CliCommandError("output_not_directory")
    bundle_destination = output / "source-bundle"
    if bundle_destination.exists() or bundle_destination.is_symlink():
        existing = _read_bundle_for_request(
            bundle_destination,
            model_id,
            requested_revision,
            invalid_code="existing_bundle_invalid",
        )
        if (
            offline is not None
            and _bundle_manifest_bytes(existing.manifest)
            != _bundle_manifest_bytes(offline.manifest)
        ):
            raise CliCommandError("target_bundle_conflict")
        _verify_existing_run_target(output, existing.manifest)
        return bundle_destination

    if output.exists() and any(output.iterdir()):
        raise CliCommandError("output_missing_source_bundle")
    output.mkdir(parents=True, exist_ok=True)
    try:
        if offline is not None:
            _copy_verified_bundle(offline_bundle, bundle_destination)
        else:
            adapter = HuggingFaceHubAdapter(token=_environment_hf_token())
            collect_hf_source_bundle(
                model_id,
                bundle_destination,
                adapter,
                revision=requested_revision,
            )
    except CliCommandError:
        raise
    except Exception as exc:
        raise CliCommandError("source_collection_failed") from exc
    collected = _read_bundle_for_request(
        bundle_destination,
        model_id,
        requested_revision,
        invalid_code="collected_bundle_invalid",
    )
    if offline is not None and _bundle_manifest_bytes(collected.manifest) != _bundle_manifest_bytes(
        offline.manifest
    ):
        raise CliCommandError("offline_bundle_copy_failed")
    return bundle_destination


def _prepare_official_bundle(
    *,
    hf_bundle_directory: Path,
    output: Path,
    offline_hf: bool,
    offline_official_bundle: Path | None,
) -> Path | None:
    try:
        hf_bundle = replay_source_bundle(hf_bundle_directory)
    except Exception as exc:
        raise CliCommandError("existing_bundle_invalid") from exc
    destination = output / "official-source-bundle"
    run_manifest_path = output / "run-manifest.json"
    if run_manifest_path.exists() or run_manifest_path.is_symlink():
        try:
            admitted = RunManifest.from_dict(_read_object(run_manifest_path))
        except Exception as exc:
            raise CliCommandError("existing_run_invalid") from exc
        mode = admitted.configuration.get("source_state_mode")
        if mode == "hf_only":
            if offline_official_bundle is not None:
                raise CliCommandError("official_bundle_mode_conflict")
            return None
        if mode == "hf_and_official" and not destination.is_dir():
            raise CliCommandError("existing_official_bundle_invalid")
    offline = None
    if offline_official_bundle is not None:
        try:
            offline = replay_official_sources(
                offline_official_bundle,
                expected_target=hf_bundle.manifest.target,
            )
        except Exception as exc:
            raise CliCommandError("offline_official_bundle_invalid") from exc
        if offline.manifest.source_bundle_id != hf_bundle.manifest.bundle_id:
            raise CliCommandError("official_bundle_target_mismatch")

    if destination.exists() or destination.is_symlink():
        try:
            existing = replay_official_sources(
                destination,
                expected_target=hf_bundle.manifest.target,
            )
        except Exception as exc:
            raise CliCommandError("existing_official_bundle_invalid") from exc
        if existing.manifest.source_bundle_id != hf_bundle.manifest.bundle_id:
            raise CliCommandError("official_bundle_target_mismatch")
        if offline is not None and existing.manifest.to_dict() != offline.manifest.to_dict():
            raise CliCommandError("official_bundle_conflict")
        return destination

    if offline is not None:
        try:
            _copy_verified_official_bundle(
                offline_official_bundle,
                destination,
                expected_target=hf_bundle.manifest.target,
                expected_hf_bundle_id=hf_bundle.manifest.bundle_id,
            )
        except CliCommandError:
            raise
        except Exception as exc:
            raise CliCommandError("official_bundle_copy_failed") from exc
        return destination

    # Supplying a frozen HF bundle means fully offline unless the caller also
    # supplies its ancestry-bound official bundle. The normal online command
    # performs bounded declared and scholarly discovery plus official
    # collection automatically. Scholarly results remain discovery-only.
    if offline_hf:
        return None

    discovery_path = output / "official-discovery.json"
    scholarly_path = output / SCHOLARLY_DISCOVERY_FILENAME
    try:
        if discovery_path.exists() or discovery_path.is_symlink():
            if discovery_path.is_symlink() or not discovery_path.is_file():
                raise CliCommandError("official_discovery_invalid")
            discovery = replay_official_discovery(
                hf_bundle,
                discovery_path.read_bytes(),
            )
        else:
            discovery = discover_official_sources(hf_bundle)
            _atomic_json_update(
                discovery_path,
                discovery.to_dict(),
                immutable=True,
            )
        if scholarly_path.exists() or scholarly_path.is_symlink():
            if scholarly_path.is_symlink() or not scholarly_path.is_file():
                raise CliCommandError("scholarly_discovery_invalid")
            scholarly = load_scholarly_discovery(
                scholarly_path.read_bytes(),
                expected_target=hf_bundle.manifest.target,
            )
        else:
            scholarly = discover_scholarly_sources(
                hf_bundle.manifest.target,
                StdlibScholarlyDiscoveryTransport(),
            )
            _atomic_json_update(
                scholarly_path,
                scholarly.to_dict(),
                immutable=True,
            )
        allowed_hosts = tuple(
            sorted(
                set(discovery.policy.publication_hosts)
                | set(discovery.policy.code_hosts)
                | set(discovery.policy.owned_hosts)
            )
        )
        exact_record_ids = set(
            exact_target_declaration_record_ids(hf_bundle, discovery)
        )
        relation_assertions = tuple(
            RelationAssertion(
                candidate_record_id=record.record_id,
                subject_model_id=discovery.target.model_id,
                relation_to_target=RelationToTarget.EXACT_TARGET,
                declaring_source_id=record.declaring_source_id or "",
                declaration_locator=record.declaration_locator,
                target_revision=discovery.target.revision,
            )
            for record in discovery.records
            if record.record_id in exact_record_ids
        )
        collect_official_sources(
            discovery,
            destination,
            StdlibOfficialSourceAdapter(allowed_hosts),
            relation_assertions=relation_assertions,
            discovery_hints=scholarly.hints,
            max_sources=_MAX_OFFICIAL_SOURCES_WITH_SCHOLARLY_HINTS,
        )
        replayed = replay_official_sources(
            destination,
            expected_target=hf_bundle.manifest.target,
            expected_discovery_id=discovery.discovery_id,
        )
        if replayed.manifest.source_bundle_id != hf_bundle.manifest.bundle_id:
            raise CliCommandError("official_bundle_target_mismatch")
    except CliCommandError:
        raise
    except Exception as exc:
        raise CliCommandError("official_source_collection_failed") from exc
    return destination


def _pipeline_summary(result: PipelineResult, run_directory: Path) -> dict[str, Any]:
    names = {
        "source-bundle/manifest.json",
        "pipeline-result.json",
        *(item.filename for item in result.artifacts),
    }
    if (run_directory / "official-source-bundle" / "manifest.json").is_file():
        names.add("official-source-bundle/manifest.json")
    if (run_directory / "official-discovery.json").is_file():
        names.add("official-discovery.json")
    if (run_directory / SCHOLARLY_DISCOVERY_FILENAME).is_file():
        names.add(SCHOLARLY_DISCOVERY_FILENAME)
    if (run_directory / ORCHESTRATION_MANIFEST_FILENAME).is_file():
        names.add(ORCHESTRATION_MANIFEST_FILENAME)
    if (run_directory / PROVIDER_EXECUTION_MANIFEST_FILENAME).is_file():
        names.add(PROVIDER_EXECUTION_MANIFEST_FILENAME)
    for name in (AUDIT_VIEW_FILENAME, USAGE_SUMMARY_FILENAME, "provider-result.json"):
        if (run_directory / name).is_file():
            names.add(name)
    artifacts = sorted(_safe_relative_name(item) for item in names)
    return {
        "target": result.target.to_dict(),
        "status": result.lifecycle_status.value,
        "artifacts": artifacts,
    }


def _generate_target(
    *,
    model_id: str,
    revision: str | None,
    output: Path,
    offline_bundle: Path | None,
    offline_official_bundle: Path | None = None,
    provider: str | None = None,
    aggregate_budget_path: Path | None = None,
) -> dict[str, Any]:
    parsed_model_id, requested_revision = _requested_target(model_id, revision)
    if aggregate_budget_path is not None and provider is None:
        raise CliCommandError("aggregate_budget_requires_provider")
    provider = _provider_mode(output, provider)
    bundle_directory = _prepare_generation_bundle(
        model_id=parsed_model_id,
        requested_revision=requested_revision,
        output=output,
        offline_bundle=offline_bundle,
    )
    official_bundle_directory = _prepare_official_bundle(
        hf_bundle_directory=bundle_directory,
        output=output,
        offline_hf=offline_bundle is not None,
        offline_official_bundle=offline_official_bundle,
    )
    expected_path = output / "pipeline-result.json"
    try:
        if provider is not None:
            assisted = run_provider_assisted_pipeline(
                bundle_directory,
                output,
                official_bundle_directory=official_bundle_directory,
                provider=provider,
                ledger_path=output / "usage.jsonl",
                decision_dir=output / "provider-decisions",
                aggregate_budget_path=aggregate_budget_path,
            )
            result = assisted.pipeline_result
        elif expected_path.exists() or expected_path.is_symlink():
            expected = PipelineResult.from_dict(_read_object(expected_path))
            if expected.target.model_id != parsed_model_id:
                raise CliCommandError("target_mismatch")
            bundle = replay_source_bundle(bundle_directory)
            if expected.target.to_dict() != bundle.manifest.target.to_dict():
                raise CliCommandError("target_mismatch")
            result = verify_pipeline_result(
                expected,
                bundle_directory,
                output,
                official_bundle_directory=official_bundle_directory,
            )
        else:
            result = run_offline_pipeline(
                bundle_directory,
                output,
                official_bundle_directory=official_bundle_directory,
            )
        if provider is not None:
            _atomic_json_update(
                output / "provider-result.json",
                assisted.to_dict(),
                immutable=True,
            )
        write_run_summaries(result, output)
    except CliCommandError:
        raise
    except MissingCredentialError as exc:
        raise CliCommandError("openrouter_key_unavailable") from exc
    except BudgetCapError as exc:
        raise CliCommandError("provider_budget_cap_reached") from exc
    except (ProviderUncertainError, UncertainSendError, TransportUncertainError) as exc:
        raise CliCommandError("provider_send_uncertain") from exc
    except ProviderRouteError as exc:
        raise CliCommandError("provider_route_unavailable") from exc
    except RetryExhaustedError as exc:
        raise CliCommandError("provider_retries_exhausted") from exc
    except ProviderTerminalAttemptError as exc:
        if exc.reason_code == "retry_exhausted":
            raise CliCommandError("provider_retries_exhausted") from exc
        raise CliCommandError("provider_pipeline_failed_or_stale") from exc
    except (OrchestrationError, ProviderError, LedgerError) as exc:
        raise CliCommandError("provider_pipeline_failed_or_stale") from exc
    except RunSummaryError as exc:
        raise CliCommandError("run_summary_failed_or_stale") from exc
    except Exception as exc:
        raise CliCommandError("pipeline_failed_or_stale") from exc
    return _pipeline_summary(result, output)


def _cmd_collect(args: argparse.Namespace) -> int:
    model_id, requested_revision = _requested_target(args.model_id, args.revision)
    destination = Path(args.output)
    if destination.exists() or destination.is_symlink():
        replayed = _read_bundle_for_request(
            destination,
            model_id,
            requested_revision,
            invalid_code="existing_bundle_invalid",
        )
    else:
        try:
            adapter = HuggingFaceHubAdapter(token=_environment_hf_token())
            collect_hf_source_bundle(
                model_id,
                destination,
                adapter,
                revision=requested_revision,
            )
        except Exception as exc:
            raise CliCommandError("source_collection_failed") from exc
        replayed = _read_bundle_for_request(
            destination,
            model_id,
            requested_revision,
            invalid_code="collected_bundle_invalid",
        )
    artifacts = ["manifest.json"]
    artifacts.extend(
        item.object_path
        for item in replayed.manifest.sources
        if item.object_path is not None
    )
    _print_json(
        {
            "target": replayed.manifest.target.to_dict(),
            "status": "collected",
            "artifacts": sorted(
                _safe_relative_name(item) for item in set(artifacts)
            ),
        }
    )
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    summary = _generate_target(
        model_id=args.model_id,
        revision=args.revision,
        output=Path(args.output),
        offline_bundle=Path(args.offline_bundle) if args.offline_bundle else None,
        offline_official_bundle=(
            Path(args.offline_official_bundle)
            if args.offline_official_bundle
            else None
        ),
        provider=args.provider,
        aggregate_budget_path=(
            Path(args.aggregate_budget_journal)
            if args.aggregate_budget_journal
            else None
        ),
    )
    _print_json(summary)
    return 0


def _canonical_request(model_id: str, revision: str | None) -> str:
    return model_id if revision is None else f"{model_id}@{revision}"


def _read_batch_requests(value: str) -> tuple[str, ...]:
    if value.lstrip().startswith("["):
        raw = value.encode("utf-8")
    else:
        try:
            raw = Path(value).read_bytes()
        except OSError as exc:
            raise CliCommandError("batch_input_unavailable") from exc
    try:
        parsed = _strict_json_bytes(raw)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CliCommandError("batch_input_invalid") from exc
    if not isinstance(parsed, list) or not parsed:
        raise CliCommandError("batch_input_invalid")
    requests: list[str] = []
    for item in parsed:
        if not isinstance(item, str):
            raise CliCommandError("batch_input_invalid")
        model_id, revision = _requested_target(item, None)
        requests.append(_canonical_request(model_id, revision))
    if len(requests) != len(set(requests)):
        raise CliCommandError("batch_target_duplicate")
    return tuple(requests)


def _batch_target_directory(request: str) -> str:
    digest = hashlib.sha256(request.encode("utf-8")).hexdigest()[:20]
    return f"target-{digest}"


def _validate_batch_aggregate_budget_path(output: Path, journal: Path) -> None:
    """Keep the shared journal disjoint from files the batch owns or replaces."""

    if journal.is_symlink() or journal.parent.is_symlink():
        raise CliCommandError("aggregate_budget_path_conflict")
    try:
        lexical_output = Path(os.path.abspath(output))
        lexical_journal = Path(os.path.abspath(journal))
        resolved_output = output.resolve(strict=False)
        resolved_journal = journal.resolve(strict=False)
    except OSError as exc:
        raise CliCommandError("aggregate_budget_path_conflict") from exc
    control_names = (
        "batch-request.json",
        "batch-result.json",
        _AGGREGATE_BUDGET_SUMMARY_FILENAME,
    )
    lexical_controls = tuple(lexical_output / name for name in control_names)
    resolved_controls = tuple(
        resolved_output / name
        for name in control_names
    )
    if lexical_journal in lexical_controls or resolved_journal in resolved_controls:
        raise CliCommandError("aggregate_budget_path_conflict")
    for candidate, target_root in (
        (lexical_journal, lexical_output / "targets"),
        (resolved_journal, resolved_output / "targets"),
    ):
        try:
            candidate.relative_to(target_root)
        except ValueError:
            continue
        raise CliCommandError("aggregate_budget_path_conflict")
    if lexical_journal == lexical_output or resolved_journal == resolved_output:
        raise CliCommandError("aggregate_budget_path_conflict")
    if journal.exists():
        default_journal = resolved_output / _AGGREGATE_BUDGET_FILENAME
        aliases = (*resolved_controls, default_journal)
        for candidate in aliases:
            if resolved_journal == candidate or not candidate.exists():
                continue
            try:
                aliases_batch_file = os.path.samefile(journal, candidate)
            except OSError as exc:
                raise CliCommandError("aggregate_budget_path_conflict") from exc
            if aliases_batch_file:
                raise CliCommandError("aggregate_budget_path_conflict")


def _parse_batch_offline_bundles(
    values: Sequence[str], requests: Sequence[str]
) -> dict[str, Path]:
    output: dict[str, Path] = {}
    known = set(requests)
    for value in values:
        if not isinstance(value, str) or "=" not in value:
            raise CliCommandError("batch_offline_bundle_invalid")
        request_value, path_value = value.split("=", 1)
        model_id, revision = _requested_target(request_value, None)
        request = _canonical_request(model_id, revision)
        if request not in known or request in output or not path_value:
            raise CliCommandError("batch_offline_bundle_invalid")
        output[request] = Path(path_value)
    return output


def _atomic_json_update(path: Path, value: Any, *, immutable: bool) -> None:
    payload = (_json_line(value) + "\n").encode("utf-8")
    if path.is_symlink() or path.parent.is_symlink():
        raise CliCommandError("batch_output_unsafe")
    if path.exists():
        if not path.is_file():
            raise CliCommandError("batch_output_unsafe")
        if path.read_bytes() == payload:
            return
        if immutable:
            raise CliCommandError("batch_request_conflict")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _batch_failure_code(exc: Exception) -> str:
    if isinstance(exc, CliCommandError):
        return exc.code
    return "generation_failed"


def _batch_failure_artifacts(target_output: Path, relative_directory: str) -> list[str]:
    """Expose only body-free controls needed to account for a failed target."""

    artifacts = []
    for name in (ORCHESTRATION_MANIFEST_FILENAME, "usage.jsonl"):
        path = target_output / name
        if path.is_file() and not path.is_symlink():
            artifacts.append(
                _safe_relative_name(f"{relative_directory}/{name}")
            )
    return sorted(artifacts)


def _cmd_batch(args: argparse.Namespace) -> int:
    requests = _read_batch_requests(args.targets)
    if args.aggregate_budget_journal and args.provider is None:
        raise CliCommandError("aggregate_budget_requires_provider")
    offline = _parse_batch_offline_bundles(args.offline_bundle, requests)
    offline_official = _parse_batch_offline_bundles(
        args.offline_official_bundle, requests
    )
    output = Path(args.output)
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise CliCommandError("batch_output_unsafe")
    aggregate_budget_path = (
        Path(args.aggregate_budget_journal)
        if args.aggregate_budget_journal
        else (
            output / _AGGREGATE_BUDGET_FILENAME
            if args.provider is not None
            else None
        )
    )
    if aggregate_budget_path is not None:
        _validate_batch_aggregate_budget_path(output, aggregate_budget_path)
    output.mkdir(parents=True, exist_ok=True)
    request_payload = {"targets": list(requests)}
    _atomic_json_update(output / "batch-request.json", request_payload, immutable=True)
    records: list[dict[str, Any]] = []
    failure_count = 0
    for request in requests:
        model_id, revision = _requested_target(request, None)
        relative_directory = f"targets/{_batch_target_directory(request)}"
        target_output = output.joinpath(*PurePosixPath(relative_directory).parts)
        try:
            summary = _generate_target(
                model_id=model_id,
                revision=revision,
                output=target_output,
                offline_bundle=offline.get(request),
                offline_official_bundle=offline_official.get(request),
                provider=args.provider,
                aggregate_budget_path=aggregate_budget_path,
            )
            records.append(
                {
                    "request": request,
                    "target": summary["target"],
                    "status": summary["status"],
                    "artifacts": [
                        _safe_relative_name(f"{relative_directory}/{item}")
                        for item in summary["artifacts"]
                    ],
                }
            )
        except Exception as exc:
            failure_count += 1
            records.append(
                {
                    "request": request,
                    "status": "failed",
                    "reason": _batch_failure_code(exc),
                    "artifacts": _batch_failure_artifacts(
                        target_output, relative_directory
                    ),
                }
            )
    batch_artifacts = ["batch-request.json", "batch-result.json"]
    if aggregate_budget_path is not None:
        budget_summary = summarize_aggregate_budget(aggregate_budget_path)
        local_budget = (
            aggregate_budget_path.resolve()
            == (output / _AGGREGATE_BUDGET_FILENAME).resolve()
        )
        _atomic_json_update(
            output / _AGGREGATE_BUDGET_SUMMARY_FILENAME,
            {
                **budget_summary,
                "journal_scope": "batch_root" if local_budget else "external_shared",
            },
            immutable=False,
        )
        batch_artifacts.append(_AGGREGATE_BUDGET_SUMMARY_FILENAME)
        if local_budget:
            batch_artifacts.append(_AGGREGATE_BUDGET_FILENAME)
    aggregate = {
        "status": "completed" if not failure_count else "completed_with_failures",
        "targets": records,
        "artifacts": sorted(batch_artifacts),
    }
    _atomic_json_update(output / "batch-result.json", aggregate, immutable=False)
    _print_json(aggregate)
    return 0 if not failure_count else 1


def _cmd_repair(args: argparse.Namespace) -> int:
    try:
        record = FieldRepairRecord.from_dict(_read_object(Path(args.record)))
    except Exception as exc:
        raise CliCommandError("repair_record_invalid") from exc
    _print_json(
        {
            "target": record.context.target.to_dict(),
            "status": record.outcome.value,
            "field_path": record.context.field_path,
            "attempt_count": len(record.attempts),
            "reason": record.reason.value,
            "selected_candidate_id": record.selected_candidate_id,
        }
    )
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    try:
        report = build_quality_report(
            args.primary_batch,
            args.replay_batch,
        )
        destination = write_quality_report(report, args.output)
    except QualityReportError as exc:
        raise CliCommandError("quality_report_failed_or_stale") from exc
    _print_json(
        {
            "status": "completed",
            "target_count": len(report.targets),
            "report_sha256": report.report_sha256,
            "artifacts": [_safe_relative_name(destination.name)],
        }
    )
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    source = Path(args.specification)
    artifact = build_artifact(_read_object(source))
    json_path = _new_path(args.json)
    html_path = _new_path(args.html)
    if json_path.resolve() == html_path.resolve():
        raise ValueError("JSON and HTML outputs must differ")
    save_json(artifact, json_path)
    save_html(artifact, html_path)
    print(f"wrote {json_path}")
    print(f"wrote {html_path}")
    return 0


def _cmd_render(args: argparse.Namespace) -> int:
    source = Path(args.artifact)
    destination = _new_path(args.html, inputs=(source,))
    save_html(load_artifact(source), destination)
    print(f"wrote {destination}")
    return 0


def _cmd_inspect(args: argparse.Namespace) -> int:
    value = _read_object(Path(args.artifact))
    if "pipeline_version" in value:
        result = PipelineResult.from_dict(value)
        payload = {
            "target": result.target.to_dict(),
            "lifecycle_status": result.lifecycle_status.value,
            "composition_status": result.composition_status.value,
            "claim_count": len(result.claims),
            "validation": result.validation.to_dict(),
            "artifacts": sorted(item.filename for item in result.artifacts),
        }
        _print_json(payload)
        return 0
    if "repair_version" in value:
        record = FieldRepairRecord.from_dict(value)
        _print_json(
            {
                "target": record.context.target.to_dict(),
                "field_path": record.context.field_path,
                "outcome": record.outcome.value,
                "reason": record.reason.value,
                "attempt_count": len(record.attempts),
                "selected_candidate_id": record.selected_candidate_id,
            }
        )
        return 0
    artifact = CardArtifact.from_dict(value)
    if args.field:
        field_path = validate_field_path(args.field)
        base = canonical_field_path(field_path)
        payload = {
            "target": artifact.target.to_dict(),
            "field_path": field_path,
            "value": get_field(project_card(artifact), field_path),
            "bindings": [
                item.to_dict()
                for item in artifact.effective_bindings()
                if canonical_field_path(item.field_path) == base
            ],
        }
    else:
        payload = {
            "target": artifact.target.to_dict(),
            "contract_version": artifact.contract_version,
            "lifecycle_status": artifact.lifecycle_status.value,
            "binding_count": len(artifact.bindings),
            "review_count": len(artifact.reviews),
            "dispositions": {
                disposition: sum(
                    item.disposition.value == disposition
                    for item in artifact.effective_bindings()
                )
                for disposition in ("accepted", "withheld", "rejected")
            },
        }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _cmd_review(args: argparse.Namespace) -> int:
    source = Path(args.artifact)
    destination = _new_path(args.output, inputs=(source,))
    artifact = load_artifact(source)
    corrected_value = None
    gate_record = None
    if args.action == ReviewAction.REASSIGN.value:
        if any(
            item is None
            for item in (
                args.field,
                args.relation,
                args.value_json,
                args.gate_record,
                args.source_bundle,
            )
        ):
            raise ValueError(
                "reassign requires --field, --relation, --value-json, "
                "--gate-record, and --source-bundle"
            )
        corrected_value = json.loads(args.value_json)
        gate_record = ClaimGateRecord.from_dict(
            _read_object(Path(args.gate_record))
        )
        state = load_source_state(args.source_bundle, args.official_bundle)
        if state.target != artifact.target:
            raise ValueError("review source bundle target differs from the artifact")
        verify_claim_gate_record(gate_record, state.documents)
    elif any(
        item is not None
        for item in (
            args.field,
            args.relation,
            args.value_json,
            args.gate_record,
            args.source_bundle,
            args.official_bundle,
        )
    ):
        raise ValueError(
            "field, relation, value, gate record, and source bundles are only "
            "valid with reassign"
        )
    reviewed = append_review(
        artifact,
        binding_id=args.binding_id,
        action=args.action,
        reason=args.reason,
        field_path=args.field,
        relation=args.relation,
        corrected_value=corrected_value,
        gate_record=gate_record,
    )
    save_artifact(reviewed, destination)
    print(f"wrote {destination}")
    return 0


def _cmd_audit_review(args: argparse.Namespace) -> int:
    source = Path(args.artifact)
    inputs = [source, Path(args.source_bundle)]
    if args.official_bundle is not None:
        inputs.append(Path(args.official_bundle))
    if args.prior_omissions is not None:
        inputs.append(Path(args.prior_omissions))
    closure_names = (
        "claim_gates",
        "publication_factreasoner",
        "publication_validation",
        "final_factreasoner",
        "family_risk_authorizations",
        "risk_mapping",
        "privacy",
        "provider_run",
    )
    closure_values = tuple(getattr(args, name) for name in closure_names)
    if any(item is not None for item in closure_values) and not all(
        item is not None for item in closure_values
    ):
        raise ValueError(
            "sealed review audit requires all downstream closure artifacts"
        )
    inputs.extend(Path(item) for item in closure_values if item is not None)
    destination = _new_path(args.output, inputs=tuple(inputs))
    artifact = load_artifact(source)
    state = load_source_state(args.source_bundle, args.official_bundle)
    if state.target != artifact.target:
        raise ValueError("review audit source bundle target differs from the artifact")
    prior = (
        None
        if args.prior_omissions is None
        else OmissionAudit.from_dict(_read_object(Path(args.prior_omissions)))
    )
    closure = None
    if all(item is not None for item in closure_values):
        gate_inventory = _read_object(Path(args.claim_gates))
        if (
            set(gate_inventory) != {"target", "extraction_sha256", "records"}
            or gate_inventory["target"] != artifact.target.to_dict()
            or not isinstance(gate_inventory["extraction_sha256"], str)
            or re.fullmatch(r"[0-9a-f]{64}", gate_inventory["extraction_sha256"])
            is None
            or not isinstance(gate_inventory["records"], list)
        ):
            raise ValueError("claim-gate inventory is malformed or targets another model")
        closure = ReviewClosureEvidence(
            claim_gate_records=tuple(
                ClaimGateRecord.from_dict(item) for item in gate_inventory["records"]
            ),
            publication_catalog=state.hf_catalog,
            publication_factreasoner=FactReasonerRecord.from_dict(
                _read_object(Path(args.publication_factreasoner))
            ),
            publication_validation=PublicationValidationReport.from_dict(
                _read_object(Path(args.publication_validation))
            ),
            final_factreasoner=FactReasonerRecord.from_dict(
                _read_object(Path(args.final_factreasoner))
            ),
            family_authorization=FamilyRiskAuthorizationReport.from_dict(
                _read_object(Path(args.family_risk_authorizations))
            ),
            risk_catalog=load_pinned_nexus_catalog(),
            risk_mapping=_read_object(Path(args.risk_mapping)),
            privacy=PrivacyScanReport.from_dict(
                _read_object(Path(args.privacy))
            ),
            provider_execution=ProviderExecutionRunEvidence.load(args.provider_run),
        )
    audit = audit_reviewed_candidate(
        artifact,
        state.documents,
        prior_omission_audit=prior,
        closure_evidence=closure,
    )
    _atomic_json_update(destination, audit.to_dict(), immutable=True)
    _print_json(
        {
            "audit_sha256": audit.audit_sha256,
            "source_present_omission_count": len(audit.source_present_omissions),
            "verdict": audit.verdict,
        }
    )
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    value = _read_object(Path(args.input))
    if "pipeline_version" in value:
        result = PipelineResult.from_dict(value)
        _print_json(
            {
                "kind": "pipeline_result",
                "lifecycle_status": result.lifecycle_status.value,
                "valid": True,
            }
        )
        return 0
    if "repair_version" in value:
        record = FieldRepairRecord.from_dict(value)
        _print_json(
            {
                "kind": "field_repair_record",
                "outcome": record.outcome.value,
                "valid": True,
            }
        )
        return 0
    if "artifact_id" in value:
        artifact = CardArtifact.from_dict(value)
        card = project_card(artifact)
        validate_public_card(card)
        kind = "artifact"
        result = {
            "contract_version": CONTRACT_VERSION,
            "kind": kind,
            "lifecycle_status": card["lifecycle"]["status"],
            "valid": True,
        }
    elif "contract_version" in value:
        validate_public_card(value)
        result = {
            "contract_version": CONTRACT_VERSION,
            "kind": "audit_card",
            "lifecycle_status": value["lifecycle"]["status"],
            "valid": True,
        }
    else:
        validate_publication_card(value)
        result = {
            "coverage_score": publication_coverage(value),
            "kind": "public_card",
            "valid": True,
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    record = export_public_card(
        args.artifact,
        args.output,
        source_bundle_directory=args.source_bundle,
        official_bundle_directory=args.official_bundle,
        force=args.force,
    )
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_schema(args: argparse.Namespace) -> int:
    print(json.dumps(build_publication_schema(), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="modelcards",
        description="Collect, generate, validate, and inspect evidence-bound Model Cards.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect = subparsers.add_parser(
        "collect", help="freeze an exact-revision Hugging Face source bundle"
    )
    collect.add_argument("model_id", help="Hugging Face namespace/name")
    collect.add_argument("--revision", help="branch, tag, ref, or exact commit")
    collect.add_argument("--output", required=True, help="bundle output directory")
    collect.set_defaults(handler=_cmd_collect)

    generate = subparsers.add_parser(
        "generate", help="run or resume provider-free generation from an exact bundle"
    )
    generate.add_argument("model_id", help="Hugging Face namespace/name")
    generate.add_argument("--revision", help="branch, tag, ref, or exact commit")
    generate.add_argument("--output", required=True, help="local run directory")
    generate.add_argument(
        "--offline-bundle",
        help="verified frozen bundle to copy and replay without network access",
    )
    generate.add_argument(
        "--offline-official-bundle",
        help="verified official-source bundle discovered from the same frozen Hub bundle",
    )
    generate.add_argument(
        "--provider",
        choices=(PINNED_PROVIDER,),
        metavar=PINNED_PROVIDER,
        help=(
            "enable assisted extraction and validation on the pinned OpenRouter "
            "provider and model; uses OPENROUTER_API_KEY"
        ),
    )
    generate.add_argument(
        "--aggregate-budget-journal",
        help=(
            "shared append-only 300-call budget journal for provider-assisted "
            "targets; reuse the same path across a bounded cohort"
        ),
    )
    generate.set_defaults(handler=_cmd_generate)

    batch = subparsers.add_parser(
        "batch", help="generate a strict JSON array of model_id[@revision] targets"
    )
    batch.add_argument("targets", help="JSON array text or path to a JSON array file")
    batch.add_argument("--output", required=True, help="batch output directory")
    batch.add_argument(
        "--provider",
        choices=(PINNED_PROVIDER,),
        metavar=PINNED_PROVIDER,
        help=(
            "enable assisted extraction and validation for every target on the "
            "pinned OpenRouter provider and one shared aggregate budget"
        ),
    )
    batch.add_argument(
        "--aggregate-budget-journal",
        help=(
            "shared append-only 300-call budget journal; provider batches default "
            "to OUTPUT/aggregate-budget.jsonl"
        ),
    )
    batch.add_argument(
        "--offline-bundle",
        action="append",
        default=[],
        metavar="TARGET=DIR",
        help="repeatable target-specific frozen bundle for fully offline generation",
    )
    batch.add_argument(
        "--offline-official-bundle",
        action="append",
        default=[],
        metavar="TARGET=DIR",
        help="repeatable target-specific official bundle bound to the matching Hub bundle",
    )
    batch.set_defaults(handler=_cmd_batch)

    build = subparsers.add_parser("build", help="build JSON and static HTML from a specification")
    build.add_argument("specification")
    build.add_argument("--json", required=True, help="new artifact output path")
    build.add_argument("--html", required=True, help="new static HTML output path")
    build.set_defaults(handler=_cmd_build)

    render = subparsers.add_parser("render", help="render an artifact as static HTML")
    render.add_argument("artifact")
    render.add_argument("--html", required=True, help="new static HTML output path")
    render.set_defaults(handler=_cmd_render)

    inspect = subparsers.add_parser("inspect", help="inspect an artifact or one field")
    inspect.add_argument("artifact")
    inspect.add_argument("--field")
    inspect.set_defaults(handler=_cmd_inspect)

    review = subparsers.add_parser("review", help="append one review event to a new artifact")
    review.add_argument("artifact")
    review.add_argument("binding_id")
    review.add_argument("--action", required=True, choices=[item.value for item in ReviewAction])
    review.add_argument("--reason", required=True)
    review.add_argument("--field")
    review.add_argument("--relation", choices=[item.value for item in RelationToTarget])
    review.add_argument("--value-json")
    review.add_argument(
        "--gate-record",
        help="four-part Claim Support Gate record for the corrected candidate",
    )
    review.add_argument(
        "--source-bundle",
        help="frozen Hugging Face source bundle used to replay the gate",
    )
    review.add_argument(
        "--official-bundle",
        help="optional ancestry-bound official source bundle used to replay the gate",
    )
    review.add_argument("--output", required=True)
    review.set_defaults(handler=_cmd_review)

    audit_review = subparsers.add_parser(
        "audit-review",
        help="replay gates and omissions after append-only review events",
    )
    audit_review.add_argument("artifact")
    audit_review.add_argument("--source-bundle", required=True)
    audit_review.add_argument("--official-bundle")
    audit_review.add_argument("--prior-omissions")
    audit_review.add_argument("--claim-gates")
    audit_review.add_argument("--publication-factreasoner")
    audit_review.add_argument("--publication-validation")
    audit_review.add_argument("--final-factreasoner")
    audit_review.add_argument("--family-risk-authorizations")
    audit_review.add_argument("--risk-mapping")
    audit_review.add_argument("--privacy")
    audit_review.add_argument(
        "--provider-run",
        help=(
            "provider-assisted run root containing the exact execution manifest, "
            "pipeline result, usage ledger, and normalized decisions"
        ),
    )
    audit_review.add_argument("--output", required=True)
    audit_review.set_defaults(handler=_cmd_audit_review)

    repair = subparsers.add_parser(
        "repair",
        help="validate and summarize an automated field-repair record (not human review)",
    )
    repair.add_argument("record")
    repair.set_defaults(handler=_cmd_repair)

    report = subparsers.add_parser(
        "report",
        help="build a privacy-safe aggregate report for one batch or a paired replay",
    )
    report.add_argument("primary_batch", help="primary batch run directory")
    report.add_argument(
        "--replay-batch",
        help="paired batch directory generated from the same ordered targets",
    )
    report.add_argument("--output", required=True, help="new quality-report JSON path")
    report.set_defaults(handler=_cmd_report)

    validate = subparsers.add_parser(
        "validate", help="validate a public card or local CardArtifact"
    )
    validate.add_argument("input")
    validate.set_defaults(handler=_cmd_validate)

    export = subparsers.add_parser(
        "export", help="export a source-clean public JSON card from a local CardArtifact"
    )
    export.add_argument("artifact")
    export.add_argument("--output", required=True)
    export.add_argument("--source-bundle", required=True)
    export.add_argument("--official-bundle")
    export.add_argument("--force", action="store_true")
    export.set_defaults(handler=_cmd_export)

    schema = subparsers.add_parser("schema", help="print the packaged public JSON Schema")
    schema.set_defaults(handler=_cmd_schema)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except CliCommandError as exc:
        print(f"error: {exc.code}", file=sys.stderr)
        return 2
    except (KeyError, ValueError, TypeError, IndexError, OSError, json.JSONDecodeError) as exc:
        if args.command in {"collect", "generate", "batch", "repair", "report"}:
            print("error: command_failed", file=sys.stderr)
            return 2
        print(f"error: {exc}", file=sys.stderr)
        return 2
