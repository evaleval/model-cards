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
from .models import RelationToTarget, ReviewAction
from .field_repair import FieldRepairRecord
from .hf_adapter import HuggingFaceHubAdapter
from .official_discovery import (
    discover_official_sources,
    replay_official_discovery,
)
from .official_http import StdlibOfficialSourceAdapter
from .official_sources import collect_official_sources, replay_official_sources
from .orchestration import (
    ORCHESTRATION_MANIFEST_FILENAME,
    OrchestrationError,
    run_provider_assisted_pipeline,
)
from .pipeline import PipelineResult, run_offline_pipeline, verify_pipeline_result
from .provider import (
    MissingCredentialError,
    ProviderError,
    ProviderRouteError,
    ProviderUncertainError,
    RetryExhaustedError,
    TransportUncertainError,
)
from .quality_report import (
    QualityReportError,
    build_quality_report,
    write_quality_report,
)
from .public_export import export_public_card
from .render import save_html, save_json
from .review import append_review, load_artifact, save_artifact
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
    load_contract_schema,
    validate_field_path,
    validate_public_card,
)
from .source_bundle import (
    BundleManifest,
    collect_hf_source_bundle,
    parse_target_request,
    replay_source_bundle,
)


_EXACT_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_SAFE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_PROVIDER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/+()-]{0,127}$")


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
    # performs bounded official discovery and collection automatically.
    if offline_hf:
        return None

    discovery_path = output / "official-discovery.json"
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
        allowed_hosts = tuple(
            sorted(
                set(discovery.policy.publication_hosts)
                | set(discovery.policy.code_hosts)
                | set(discovery.policy.owned_hosts)
            )
        )
        collect_official_sources(
            discovery,
            destination,
            StdlibOfficialSourceAdapter(allowed_hosts),
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
    if (run_directory / ORCHESTRATION_MANIFEST_FILENAME).is_file():
        names.add(ORCHESTRATION_MANIFEST_FILENAME)
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
) -> dict[str, Any]:
    parsed_model_id, requested_revision = _requested_target(model_id, revision)
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


def _cmd_batch(args: argparse.Namespace) -> int:
    requests = _read_batch_requests(args.targets)
    offline = _parse_batch_offline_bundles(args.offline_bundle, requests)
    offline_official = _parse_batch_offline_bundles(
        args.offline_official_bundle, requests
    )
    output = Path(args.output)
    if output.is_symlink() or (output.exists() and not output.is_dir()):
        raise CliCommandError("batch_output_unsafe")
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
                    "artifacts": [],
                }
            )
    aggregate = {
        "status": "completed" if not failure_count else "completed_with_failures",
        "targets": records,
        "artifacts": ["batch-request.json", "batch-result.json"],
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
    if args.action == ReviewAction.REASSIGN.value:
        if args.field is None or args.relation is None or args.value_json is None:
            raise ValueError("reassign requires --field, --relation, and --value-json")
        corrected_value = json.loads(args.value_json)
    elif any(item is not None for item in (args.field, args.relation, args.value_json)):
        raise ValueError("field, relation, and value are only valid with reassign")
    reviewed = append_review(
        artifact,
        binding_id=args.binding_id,
        action=args.action,
        reason=args.reason,
        field_path=args.field,
        relation=args.relation,
        corrected_value=corrected_value,
    )
    save_artifact(reviewed, destination)
    print(f"wrote {destination}")
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
        kind = "artifact"
    else:
        card = value
        validate_public_card(card)
        kind = "public_card"
    validate_public_card(card)
    print(
        json.dumps(
            {
                "contract_version": CONTRACT_VERSION,
                "kind": kind,
                "lifecycle_status": card["lifecycle"]["status"],
                "valid": True,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    record = export_public_card(args.artifact, args.output, force=args.force)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


def _cmd_schema(args: argparse.Namespace) -> int:
    print(json.dumps(load_contract_schema(), ensure_ascii=False, indent=2))
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
        help=(
            "exact OpenRouter provider for assisted extraction and validation; "
            "uses OPENROUTER_API_KEY and the pinned model"
        ),
    )
    generate.set_defaults(handler=_cmd_generate)

    batch = subparsers.add_parser(
        "batch", help="generate a strict JSON array of model_id[@revision] targets"
    )
    batch.add_argument("targets", help="JSON array text or path to a JSON array file")
    batch.add_argument("--output", required=True, help="batch output directory")
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
    review.add_argument("--output", required=True)
    review.set_defaults(handler=_cmd_review)

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
