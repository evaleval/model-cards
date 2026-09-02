"""Provider-assisted orchestration over the provider-free pipeline kernel.

This module is deliberately a thin control plane.  It replays one frozen
Hugging Face source bundle, obtains normalized provider decisions through the
single bounded OpenRouter runtime, and injects those typed records into
``run_offline_pipeline``.  The orchestration admission record and returned
summary contain only identifiers, hashes, and counts: source bodies, prompts,
raw provider responses, credentials, and absolute local paths are excluded.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Any, Callable, Mapping

from .claim_gate import ClaimCandidate, GateName, ProseCheckerDecision
from .extraction import EXTRACTION_VERSION, ExtractionBatch, materialize_quote_batch
from .factreasoner import FACTREASONER_KERNEL_VERSION
from .models import TargetIdentity
from .pipeline import PIPELINE_VERSION, PipelineResult, run_offline_pipeline
from .provider import (
    MODEL_ID,
    PINNED_PROVIDER,
    PROVIDER_RUNTIME_VERSION,
    ProviderResponseError,
    ProviderTerminalAttemptError,
    ProviderTransport,
    RECOVERABLE_PROVIDER_FAILURE_REASON_CODES,
    structured_json_call,
)
from .provider_adapters import (
    ADAPTER_VERSION,
    OpenRouterApplicabilityChecker,
    OpenRouterClaimChecker,
    OpenRouterFactChecker,
    OpenRouterQuoteExtractor,
    ProviderAdapterError,
    build_nexus_openrouter_inference_engine,
)
from .risk_mapping import (
    NexusGenericRiskDetector,
    RiskCatalog,
    RiskMappingError,
    TaxonomyRelease,
    load_pinned_nexus_catalog,
)
from .run_state import MANIFEST_FILENAME, RunStore, USAGE_LEDGER_FILENAME
from .source_state import ImmutableSourceState, load_source_state


ORCHESTRATION_VERSION = "provider-assisted-model-card-orchestration/v7"
ORCHESTRATION_SCOPE = "immutable_source_state_catalog"
ORCHESTRATION_MANIFEST_FILENAME = "provider-orchestration.json"
DEFAULT_MAX_RISKS = 5

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
_CLAIM_ID_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_CLAIM_AVAILABILITY_CHECKER = "model-cards/provider-availability-v1"


class OrchestrationError(RuntimeError):
    """Provider orchestration input or immutable run state failed closed."""


CallFunction = Callable[..., Any]


def _unavailable_claim_decision(
    candidate: ClaimCandidate,
    gate: GateName,
) -> ProseCheckerDecision:
    return ProseCheckerDecision.for_candidate(
        candidate,
        gate=gate,
        checker=_CLAIM_AVAILABILITY_CHECKER,
        method="recorded_provider_response_availability",
        status="withheld",
        reason="provider_response_unavailable",
    )


def _claim_decision(
    checker: OpenRouterClaimChecker,
    candidate: ClaimCandidate,
    gate: GateName,
) -> ProseCheckerDecision:
    """Return a semantic decision or leave the local gate to withhold safely.

    A recorded provider response failure is local to this one semantic check.
    Route identity and budget-integrity failures remain fatal, as do uncertain
    sends, route failures, credential failures, and ledger conflicts.
    """

    try:
        return checker.decide(candidate, gate)
    except ProviderTerminalAttemptError as exc:
        # Deterministic replay of an already-recorded failed response. The
        # local availability decision remains byte-identical without a send.
        if exc.reason_code not in RECOVERABLE_PROVIDER_FAILURE_REASON_CODES:
            raise
        return _unavailable_claim_decision(candidate, gate)
    except ProviderResponseError as exc:
        if exc.reason_code not in RECOVERABLE_PROVIDER_FAILURE_REASON_CODES:
            raise
        return _unavailable_claim_decision(candidate, gate)


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
        raise OrchestrationError("orchestration values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _safe_run_paths(
    run_directory: str | os.PathLike[str],
    ledger_path: str | os.PathLike[str],
    decision_dir: str | os.PathLike[str],
) -> tuple[Path, Path, Path, str]:
    root = Path(run_directory)
    if root.is_symlink():
        raise OrchestrationError("run directory cannot be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    try:
        resolved_root = root.resolve(strict=True)
    except OSError as exc:
        raise OrchestrationError("run directory is unavailable") from exc
    if not resolved_root.is_dir():
        raise OrchestrationError("run directory must be a directory")

    ledger = Path(ledger_path)
    decisions = Path(decision_dir)
    lexical_root = Path(os.path.abspath(root))
    lexical_ledger = Path(os.path.abspath(ledger))
    lexical_decisions = Path(os.path.abspath(decisions))
    try:
        resolved_ledger = ledger.resolve(strict=False)
        resolved_decisions = decisions.resolve(strict=False)
        ledger_relative = resolved_ledger.relative_to(resolved_root)
        decisions_relative = resolved_decisions.relative_to(resolved_root)
        lexical_ledger_relative = lexical_ledger.relative_to(lexical_root)
        lexical_decisions_relative = lexical_decisions.relative_to(lexical_root)
    except (OSError, ValueError) as exc:
        raise OrchestrationError(
            "provider ledger and decision directory must be inside the local run"
        ) from exc
    if (
        ledger_relative != PurePosixPath(USAGE_LEDGER_FILENAME)
        or lexical_ledger_relative != PurePosixPath(USAGE_LEDGER_FILENAME)
    ):
        raise OrchestrationError("the run must use its single usage.jsonl ledger")
    if decisions_relative in {PurePosixPath("."), PurePosixPath(USAGE_LEDGER_FILENAME)} or (
        lexical_decisions_relative
        in {PurePosixPath("."), PurePosixPath(USAGE_LEDGER_FILENAME)}
    ):
        raise OrchestrationError("provider decision directory is invalid")

    # Reject existing symlink components even when their resolved target remains
    # below the run root.  Provider receipts must have one stable physical path.
    for relative in (lexical_ledger_relative, lexical_decisions_relative):
        current = lexical_root
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise OrchestrationError("provider state paths cannot contain symlinks")
    if resolved_ledger.exists() and not resolved_ledger.is_file():
        raise OrchestrationError("provider usage ledger is not a regular file")
    if resolved_decisions.exists() and not resolved_decisions.is_dir():
        raise OrchestrationError("provider decision path is not a directory")

    decision_namespace_sha256 = _digest(lexical_decisions_relative.as_posix())
    return resolved_root, resolved_ledger, resolved_decisions, decision_namespace_sha256


def _read_json(path: Path) -> Any:
    def reject_nonfinite(_: str) -> None:
        raise ValueError("non-finite JSON value")

    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), parse_constant=reject_nonfinite)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise OrchestrationError("orchestration admission record is malformed") from exc
    if raw not in {_canonical(value), _canonical(value) + b"\n"}:
        raise OrchestrationError("orchestration admission record is not canonical JSON")
    return value


def _atomic_admit(path: Path, value: Mapping[str, Any]) -> None:
    payload = _canonical(value) + b"\n"
    if path.is_symlink() or path.parent.is_symlink():
        raise OrchestrationError("orchestration admission path is unsafe")
    if path.exists():
        if not path.is_file() or _read_json(path) != dict(value):
            raise OrchestrationError(
                "run is already admitted to another target, catalog, or provider configuration"
            )
        return
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".provider-orchestration.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_name, path)
        except FileExistsError:
            if _read_json(path) != dict(value):
                raise OrchestrationError(
                    "concurrent orchestration admitted a different configuration"
                ) from None
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def _preflight_existing_pipeline(
    root: Path,
    catalog: Any,
    source_manifest_sha256: str,
) -> None:
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.exists() and not manifest_path.is_symlink():
        return
    try:
        store = RunStore.open(root)
    except Exception as exc:
        raise OrchestrationError("existing pipeline run state is unsafe or inconsistent") from exc
    admission_path = root / ORCHESTRATION_MANIFEST_FILENAME
    if admission_path.is_symlink() or not admission_path.is_file():
        raise OrchestrationError(
            "existing pipeline run was not admitted for provider orchestration"
        )
    manifest = store.manifest
    if (
        manifest.target != catalog.target
        or manifest.source_bundle_id != catalog.bundle_id
        or manifest.source_manifest_sha256 != source_manifest_sha256
    ):
        raise OrchestrationError("existing pipeline run targets another source bundle")
    source_catalog_path = root / "source-catalog.json"
    if source_catalog_path.exists() or source_catalog_path.is_symlink():
        value = _read_json(source_catalog_path)
        if (
            not isinstance(value, dict)
            or value.get("catalog_sha256") != catalog.catalog_sha256
        ):
            raise OrchestrationError("existing pipeline source catalog has drifted")


def _verify_frozen_catalog(expected: ImmutableSourceState) -> None:
    """Detect source mutation before handing control to the offline kernel."""

    try:
        current = expected.reverify()
    except Exception as exc:
        raise OrchestrationError("frozen source state changed during orchestration") from exc
    if current.to_dict() != expected.to_dict():
        raise OrchestrationError("target or source catalog drifted during orchestration")


def _select_risk_catalog(explicit: RiskCatalog | None) -> tuple[RiskCatalog | None, str]:
    if explicit is not None:
        if not isinstance(explicit, RiskCatalog) or explicit.release != TaxonomyRelease():
            raise OrchestrationError("risk catalog is not the pinned IBM AI Risk Atlas release")
        return explicit, "explicit_pinned_catalog"
    try:
        return load_pinned_nexus_catalog(), "installed_pinned_catalog"
    except RiskMappingError as exc:
        if "unavailable" in str(exc).casefold():
            return None, "nexus_dependency_unavailable"
        raise OrchestrationError(
            "the installed risk catalog failed its pinned integrity checks"
        ) from exc


def _build_risk_interfaces(
    catalog: RiskCatalog | None,
    *,
    provider: str,
    ledger_path: Path,
    decision_dir: Path,
    environment: Mapping[str, str] | None,
    transport: ProviderTransport | None,
    call: CallFunction,
    max_risks: int,
) -> tuple[Any | None, Any | None, str]:
    if catalog is None:
        return None, None, "risk_catalog_unavailable"
    # A caller may inject the already-materialized pinned catalog (for example,
    # after loading it once in a batch runner), but the executable Nexus package
    # and its bundled snapshot still have to pass the same release/hash checks.
    try:
        load_pinned_nexus_catalog()
    except RiskMappingError as exc:
        if "unavailable" in str(exc).casefold():
            return None, None, "nexus_dependency_unavailable"
        raise OrchestrationError(
            "the installed Nexus dependency or risk snapshot has drifted"
        ) from exc
    try:
        engine = build_nexus_openrouter_inference_engine(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
        )
    except ProviderAdapterError as exc:
        if str(exc) == "ai-atlas-nexus 1.2.4 is unavailable":
            return None, None, "nexus_dependency_unavailable"
        raise OrchestrationError(
            "Nexus provider inference initialization failed closed"
        ) from exc
    try:
        detector = NexusGenericRiskDetector(engine, max_risks=max_risks)
        checker = OpenRouterApplicabilityChecker(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
        )
    except (ProviderAdapterError, RiskMappingError) as exc:
        raise OrchestrationError("risk provider interfaces failed closed") from exc
    return detector, checker, "nexus_provider_enabled"


@dataclass(frozen=True)
class ProviderOrchestrationResult:
    """Privacy-safe summary plus the typed downstream pipeline result."""

    target: TargetIdentity
    source_bundle_id: str
    source_manifest_sha256: str
    source_catalog_sha256: str
    provider: str
    eligible_text_source_ids: tuple[str, ...]
    extraction_batch_sha256s: tuple[str, ...]
    quote_candidate_ids: tuple[str, ...]
    prose_decision_sha256s: tuple[str, ...]
    risk_catalog_sha256: str | None
    risk_interface_status: str
    pipeline_result: PipelineResult = dataclass_field(repr=False)
    orchestration_version: str = ORCHESTRATION_VERSION
    result_sha256: str = dataclass_field(init=False)

    def __post_init__(self) -> None:
        if self.orchestration_version != ORCHESTRATION_VERSION:
            raise OrchestrationError("orchestration summary version is unsupported")
        if not isinstance(self.target, TargetIdentity):
            raise OrchestrationError("orchestration target is invalid")
        if self.provider != PINNED_PROVIDER:
            raise OrchestrationError("orchestration provider is not pinned")
        for name in (
            "source_manifest_sha256",
            "source_catalog_sha256",
        ):
            if not _DIGEST_RE.fullmatch(getattr(self, name)):
                raise OrchestrationError(f"{name} is invalid")
        if self.risk_catalog_sha256 is not None and not _DIGEST_RE.fullmatch(
            self.risk_catalog_sha256
        ):
            raise OrchestrationError("risk catalog digest is invalid")
        source_ids = tuple(self.eligible_text_source_ids)
        batches = tuple(self.extraction_batch_sha256s)
        candidates = tuple(self.quote_candidate_ids)
        decisions = tuple(self.prose_decision_sha256s)
        if source_ids != tuple(sorted(set(source_ids))) or any(
            not _SOURCE_ID_RE.fullmatch(item) for item in source_ids
        ):
            raise OrchestrationError("eligible source identifiers are invalid")
        if batches != tuple(sorted(set(batches))) or any(
            not _DIGEST_RE.fullmatch(item) for item in batches
        ):
            raise OrchestrationError("extraction batch digests are invalid")
        if candidates != tuple(sorted(set(candidates))) or any(
            not _CLAIM_ID_RE.fullmatch(item) for item in candidates
        ):
            raise OrchestrationError("quote candidate identifiers are invalid")
        if decisions != tuple(sorted(decisions)) or any(
            not _DIGEST_RE.fullmatch(item) for item in decisions
        ):
            raise OrchestrationError("prose decision digests are invalid")
        if len(decisions) != 2 * len(candidates):
            raise OrchestrationError(
                "every quote candidate requires two semantic decisions"
            )
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,127}", self.risk_interface_status):
            raise OrchestrationError("risk interface status is invalid")
        if not isinstance(self.pipeline_result, PipelineResult):
            raise OrchestrationError("orchestration requires a typed pipeline result")
        if (
            self.pipeline_result.target != self.target
            or self.pipeline_result.source_bundle_id != self.source_bundle_id
            or self.pipeline_result.source_manifest_sha256 != self.source_manifest_sha256
            or self.pipeline_result.source_catalog_sha256 != self.source_catalog_sha256
        ):
            raise OrchestrationError(
                "downstream pipeline result drifted from orchestration input"
            )
        object.__setattr__(self, "eligible_text_source_ids", source_ids)
        object.__setattr__(self, "extraction_batch_sha256s", batches)
        object.__setattr__(self, "quote_candidate_ids", candidates)
        object.__setattr__(self, "prose_decision_sha256s", decisions)
        object.__setattr__(self, "result_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "orchestration_version": self.orchestration_version,
            "scope": ORCHESTRATION_SCOPE,
            "model": MODEL_ID,
            "target": self.target.to_dict(),
            "source_bundle_id": self.source_bundle_id,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_catalog_sha256": self.source_catalog_sha256,
            "provider": self.provider,
            "eligible_text_source_ids": list(self.eligible_text_source_ids),
            "extraction_batch_sha256s": list(self.extraction_batch_sha256s),
            "quote_candidate_ids": list(self.quote_candidate_ids),
            "prose_decision_sha256s": list(self.prose_decision_sha256s),
            "risk_catalog_sha256": self.risk_catalog_sha256,
            "risk_interface_status": self.risk_interface_status,
            "pipeline_result_sha256": self.pipeline_result.result_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "result_sha256": self.result_sha256}


def run_provider_assisted_pipeline(
    bundle_directory: str | os.PathLike[str],
    run_directory: str | os.PathLike[str],
    *,
    official_bundle_directory: str | os.PathLike[str] | None = None,
    provider: str,
    ledger_path: str | os.PathLike[str],
    decision_dir: str | os.PathLike[str],
    environment: Mapping[str, str] | None = None,
    transport: ProviderTransport | None = None,
    call: CallFunction = structured_json_call,
    risk_catalog: RiskCatalog | None = None,
    max_risks: int = DEFAULT_MAX_RISKS,
) -> ProviderOrchestrationResult:
    """Run exact-target provider stages, then the deterministic offline kernel.

    Text documents from the verified Hugging Face and optional ancestry-bound
    official-source bundles are eligible. JSON documents stay on the
    deterministic structured-extraction path; each exact-target text document
    receives exactly one quote-extraction call.
    """

    if provider != PINNED_PROVIDER:
        raise OrchestrationError("the pinned OpenRouter provider is required")
    if not callable(call):
        raise OrchestrationError("provider call must be callable")
    if (
        not isinstance(max_risks, int)
        or isinstance(max_risks, bool)
        or not 1 <= max_risks <= 10
    ):
        raise OrchestrationError("max_risks must be between 1 and 10")
    root, ledger, decisions, decision_namespace_sha256 = _safe_run_paths(
        run_directory, ledger_path, decision_dir
    )
    try:
        source_state = load_source_state(
            bundle_directory,
            official_bundle_directory=official_bundle_directory,
        )
        catalog = source_state.catalog
    except Exception as exc:
        raise OrchestrationError("frozen source-state replay failed closed") from exc
    source_manifest_sha256 = source_state.snapshot_sha256
    _preflight_existing_pipeline(root, catalog, source_manifest_sha256)

    selected_catalog, catalog_status = _select_risk_catalog(risk_catalog)
    risk_detector, risk_checker, risk_status = _build_risk_interfaces(
        selected_catalog,
        provider=provider,
        ledger_path=ledger,
        decision_dir=decisions,
        environment=environment,
        transport=transport,
        call=call,
        max_risks=max_risks,
    )
    eligible = tuple(
        sorted(
            (
                item
                for item in catalog.documents
                if item.target == catalog.target and item.text is not None
            ),
            key=lambda item: item.source_id,
        )
    )
    admission = {
        "orchestration_version": ORCHESTRATION_VERSION,
        "adapter_version": ADAPTER_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "factreasoner_kernel_version": FACTREASONER_KERNEL_VERSION,
        "pipeline_version": PIPELINE_VERSION,
        "provider_runtime_version": PROVIDER_RUNTIME_VERSION,
        "scope": ORCHESTRATION_SCOPE,
        "model": MODEL_ID,
        "target": catalog.target.to_dict(),
        "source_bundle_id": catalog.bundle_id,
        "source_manifest_sha256": source_manifest_sha256,
        "source_catalog_sha256": catalog.catalog_sha256,
        "source_state_mode": source_state.mode.value,
        "source_state_sha256": _digest(source_state.to_dict()),
        "hf_bundle_id": source_state.hf_bundle_id,
        "official_bundle_id": source_state.official_bundle_id,
        "provider": provider,
        "eligible_source_set_sha256": _digest([item.source_id for item in eligible]),
        "ledger_slot_sha256": _digest(USAGE_LEDGER_FILENAME),
        "decision_namespace_sha256": decision_namespace_sha256,
        "risk_catalog_sha256": (
            None if selected_catalog is None else selected_catalog.catalog_sha256
        ),
        "risk_catalog_status": catalog_status,
        "risk_interface_status": risk_status,
        "max_risks": max_risks,
    }
    _atomic_admit(root / ORCHESTRATION_MANIFEST_FILENAME, admission)

    try:
        extractor = OpenRouterQuoteExtractor(
            provider=provider,
            ledger_path=ledger,
            decision_dir=decisions,
            environment=environment,
            transport=transport,
            call=call,
        )
        claim_checker = OpenRouterClaimChecker(
            provider=provider,
            ledger_path=ledger,
            decision_dir=decisions,
            environment=environment,
            transport=transport,
            call=call,
        )
        fact_checker = OpenRouterFactChecker(
            provider=provider,
            ledger_path=ledger,
            decision_dir=decisions,
            environment=environment,
            transport=transport,
            call=call,
        )
        batches = tuple(
            extractor.extract_source(
                source,
                target=catalog.target,
                source_catalog_sha256=catalog.catalog_sha256,
            )
            for source in eligible
        )
    except ProviderAdapterError as exc:
        raise OrchestrationError("provider extraction initialization failed closed") from exc

    for batch in batches:
        if (
            not isinstance(batch, ExtractionBatch)
            or batch.target != catalog.target
            or batch.source_catalog_sha256 != catalog.catalog_sha256
            or batch.provider != provider
            or batch.inference_model != MODEL_ID
        ):
            raise OrchestrationError("provider extraction batch drifted from the admitted run")
    materialized = tuple(materialize_quote_batch(batch, catalog) for batch in batches)
    by_candidate: dict[str, Any] = {}
    for result in materialized:
        for candidate in result.candidates:
            previous = by_candidate.setdefault(candidate.candidate_id, candidate)
            if previous.to_dict() != candidate.to_dict():
                raise OrchestrationError("quote candidate identifier collision")
    quote_candidates = tuple(sorted(by_candidate.values(), key=lambda item: item.candidate_id))

    prose_decisions: list[ProseCheckerDecision] = []
    for candidate in quote_candidates:
        for gate in (GateName.FIELD_FIT, GateName.VALUE_SUPPORT):
            prose_decisions.append(_claim_decision(claim_checker, candidate, gate))
    prose_values = tuple(prose_decisions)
    if len(prose_values) != 2 * len(quote_candidates):
        raise OrchestrationError("provider claim-check coverage is incomplete")

    _verify_frozen_catalog(source_state)
    pipeline_result = run_offline_pipeline(
        bundle_directory,
        root,
        official_bundle_directory=official_bundle_directory,
        quote_batches=tuple(sorted(batches, key=lambda item: item.batch_sha256)),
        prose_checker_decisions=prose_values,
        fact_checker=fact_checker,
        risk_catalog=selected_catalog,
        risk_detector=risk_detector,
        risk_checker=risk_checker,
    )
    return ProviderOrchestrationResult(
        target=catalog.target,
        source_bundle_id=catalog.bundle_id,
        source_manifest_sha256=source_manifest_sha256,
        source_catalog_sha256=catalog.catalog_sha256,
        provider=provider,
        eligible_text_source_ids=tuple(item.source_id for item in eligible),
        extraction_batch_sha256s=tuple(sorted(item.batch_sha256 for item in batches)),
        quote_candidate_ids=tuple(item.candidate_id for item in quote_candidates),
        prose_decision_sha256s=tuple(
            sorted(item.content_sha256 for item in prose_values)
        ),
        risk_catalog_sha256=(
            None if selected_catalog is None else selected_catalog.catalog_sha256
        ),
        risk_interface_status=risk_status,
        pipeline_result=pipeline_result,
    )


__all__ = [
    "DEFAULT_MAX_RISKS",
    "ORCHESTRATION_MANIFEST_FILENAME",
    "ORCHESTRATION_SCOPE",
    "ORCHESTRATION_VERSION",
    "OrchestrationError",
    "ProviderOrchestrationResult",
    "run_provider_assisted_pipeline",
]
