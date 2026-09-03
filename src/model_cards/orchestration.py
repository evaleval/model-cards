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

from .claim_gate import (
    ClaimCandidate,
    ClaimGateRecord,
    GateName,
    ProseCheckerDecision,
    evaluate_claim_gate,
)
from .extraction import (
    EXTRACTION_VERSION,
    ExtractionBatch,
    build_source_windows,
    build_use_risk_windows,
    deterministic_publisher_context_candidates,
    deterministic_structured_candidates,
    materialize_quote_batch,
)
from .factreasoner import (
    FACTREASONER_KERNEL_VERSION,
    IBM_FACTREASONER_ADAPTER_VERSION,
    IBM_FACTREASONER_INFERENCE_METHOD,
    IBM_FACTREASONER_RELATION_PROBABILITY,
    IBM_FACTREASONER_UPSTREAM_REVISION,
    CheckOutcome,
    CheckRequest,
    CheckerResponse,
    FactChecker,
    IBMFactReasonerAdapter,
    UpstreamFactReasonerUnavailable,
)
from .models import TargetIdentity
from .family_risk import (
    FAMILY_RISK_BRIDGE_VERSION,
    FamilyContextApplicabilityDecision,
    FamilyDecisionStatus,
    FamilyMembershipDecision,
    FamilyRiskBridgeError,
    select_config_family_membership,
    validate_family_context_gate,
)
from .pipeline import (
    PIPELINE_VERSION,
    PipelineResult,
    deterministic_publisher_context_decisions,
    run_offline_pipeline,
)
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
    OpenRouterFamilyContextChecker,
    OpenRouterFactChecker,
    OpenRouterQuoteExtractor,
    ProviderAdapterError,
    _validate_existing_pinned_ledger,
    build_nexus_openrouter_inference_engine,
)
from .provider_execution import (
    PROVIDER_EXECUTION_MANIFEST_FILENAME,
    ProviderExecutionCollector,
    ProviderExecutionError,
    ProviderExecutionManifest,
)
from .risk_mapping import (
    MappingStatus,
    NexusGenericRiskDetector,
    RiskCatalog,
    RiskMappingReport,
    RiskMappingError,
    TaxonomyRelease,
    load_pinned_nexus_catalog,
)
from .run_state import MANIFEST_FILENAME, RunStore, USAGE_LEDGER_FILENAME
from .run_ledger import path_sha256
from .source_state import ImmutableSourceState, load_source_state


ORCHESTRATION_VERSION = "provider-assisted-model-card-orchestration/v16"
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


def _unavailable_family_decision(
    record: ClaimGateRecord,
    membership: FamilyMembershipDecision,
    membership_gate: ClaimGateRecord,
) -> FamilyContextApplicabilityDecision:
    return FamilyContextApplicabilityDecision.for_gate(
        record,
        membership,
        membership_gate,
        status=FamilyDecisionStatus.UNAVAILABLE,
        checker=_CLAIM_AVAILABILITY_CHECKER,
        method="recorded_provider_response_availability",
        reason="provider_response_unavailable",
        rationale=(
            "The checkpoint applicability provider response was unavailable."
        ),
    )


def _family_decision(
    checker: OpenRouterFamilyContextChecker,
    record: ClaimGateRecord,
    membership: FamilyMembershipDecision,
    membership_gate: ClaimGateRecord,
) -> FamilyContextApplicabilityDecision:
    try:
        return checker.assess(record, membership, membership_gate)
    except ProviderTerminalAttemptError as exc:
        if exc.reason_code not in RECOVERABLE_PROVIDER_FAILURE_REASON_CODES:
            raise
        return _unavailable_family_decision(
            record, membership, membership_gate
        )
    except ProviderResponseError as exc:
        if exc.reason_code not in RECOVERABLE_PROVIDER_FAILURE_REASON_CODES:
            raise
        return _unavailable_family_decision(
            record, membership, membership_gate
        )


def _matching_decisions(
    candidate: ClaimCandidate,
    decisions: tuple[ProseCheckerDecision, ...],
) -> tuple[ProseCheckerDecision, ...]:
    matches = []
    for decision in decisions:
        probe = ProseCheckerDecision.for_candidate(
            candidate,
            gate=decision.gate,
            checker=decision.checker,
            method=decision.method,
            status=decision.status,
            reason=decision.reason,
        )
        if probe.request_sha256 == decision.request_sha256:
            matches.append(decision)
    return tuple(sorted(matches, key=lambda item: item.gate.value))


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


def _safe_aggregate_budget_path(
    value: str | os.PathLike[str] | None,
    *,
    ledger_path: Path,
) -> Path | None:
    if value is None:
        return None
    path = Path(value)
    if path.is_symlink() or path.parent.is_symlink():
        raise OrchestrationError("aggregate budget path is unsafe")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        resolved = path.resolve(strict=False)
    except OSError as exc:
        raise OrchestrationError("aggregate budget path is unavailable") from exc
    if resolved == ledger_path.resolve():
        raise OrchestrationError(
            "aggregate budget journal must be distinct from the usage ledger"
        )
    if resolved.exists() and not resolved.is_file():
        raise OrchestrationError("aggregate budget journal is not a regular file")
    return resolved


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
    execution_collector: ProviderExecutionCollector | None = None,
    aggregate_budget_path: Path | None = None,
) -> tuple[Any | None, Any | None, str]:
    if catalog is None:
        return None, None, "risk_catalog_unavailable"
    # A caller may inject the already-materialized pinned catalog (for example,
    # after loading it once in a batch runner), but the executable Nexus package
    # and its bundled snapshot still have to pass the same release/hash checks.
    try:
        installed_catalog = load_pinned_nexus_catalog()
    except RiskMappingError as exc:
        if "unavailable" in str(exc).casefold():
            return None, None, "nexus_dependency_unavailable"
        raise OrchestrationError(
            "the installed Nexus dependency or risk snapshot has drifted"
        ) from exc
    if installed_catalog != catalog:
        raise OrchestrationError(
            "the admitted risk catalog differs from the exact installed snapshot"
        )
    try:
        engine = build_nexus_openrouter_inference_engine(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget_path=aggregate_budget_path,
            execution_collector=execution_collector,
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
            aggregate_budget_path=aggregate_budget_path,
            execution_collector=execution_collector,
        )
    except (ProviderAdapterError, RiskMappingError) as exc:
        raise OrchestrationError("risk provider interfaces failed closed") from exc
    return detector, checker, "nexus_provider_enabled"


class _UnavailableIBMFactReasonerChecker:
    """Visible fail-closed checker used when the exact optional runtime is absent."""

    checker_id = "ibm/factreasoner-fr1-unavailable"
    checker_revision = IBM_FACTREASONER_UPSTREAM_REVISION

    def __init__(self, reason_code: str) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,127}", reason_code):
            raise OrchestrationError("FactReasoner unavailability reason is invalid")
        self.reason_code = reason_code

    def check(self, request: CheckRequest) -> CheckerResponse:
        if not isinstance(request, CheckRequest):
            raise OrchestrationError("FactReasoner checker requires a CheckRequest")
        return CheckerResponse(
            outcome=CheckOutcome.UNAVAILABLE,
            reason_code=self.reason_code,
        )

    def check_many(
        self, requests: tuple[CheckRequest, ...]
    ) -> tuple[CheckerResponse, ...]:
        return tuple(self.check(item) for item in requests)


def _build_factreasoner_interface(
    *,
    provider: str,
    ledger_path: Path,
    decision_dir: Path,
    environment: Mapping[str, str] | None,
    transport: ProviderTransport | None,
    call: CallFunction,
    execution_collector: ProviderExecutionCollector | None = None,
    aggregate_budget_path: Path | None = None,
) -> tuple[FactChecker, str]:
    """Select genuine upstream FR1 or an explicit no-provider-call failure."""

    status = IBMFactReasonerAdapter.installation_status()
    if status != "ibm_factreasoner_pinned_dependency_available":
        return _UnavailableIBMFactReasonerChecker(status), status
    try:
        nli_checker = OpenRouterFactChecker(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget_path=aggregate_budget_path,
            execution_collector=execution_collector,
        )
    except ProviderAdapterError as exc:
        raise OrchestrationError(
            "FactReasoner NLI provider initialization failed closed"
        ) from exc
    adapter = IBMFactReasonerAdapter(nli_checker)
    try:
        adapter.validate_installation()
    except UpstreamFactReasonerUnavailable as exc:
        return _UnavailableIBMFactReasonerChecker(exc.reason_code), exc.reason_code
    return adapter, "ibm_factreasoner_fr1_enabled"


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
    factreasoner_interface_status: str
    provider_execution_sha256: str | None
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
        if self.provider_execution_sha256 is not None and not _DIGEST_RE.fullmatch(
            self.provider_execution_sha256
        ):
            raise OrchestrationError("provider execution manifest digest is invalid")
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
        if len(decisions) != 3 * len(candidates):
            raise OrchestrationError(
                "every quote candidate requires three semantic decisions"
            )
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,127}", self.risk_interface_status):
            raise OrchestrationError("risk interface status is invalid")
        if not re.fullmatch(
            r"[a-z][a-z0-9_]{2,127}", self.factreasoner_interface_status
        ):
            raise OrchestrationError("FactReasoner interface status is invalid")
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
            "factreasoner_interface_status": self.factreasoner_interface_status,
            "provider_execution_sha256": self.provider_execution_sha256,
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
    aggregate_budget_path: str | os.PathLike[str] | None = None,
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
    receives one general quote-extraction call and, when relevant signals are
    present, at most one dedicated publisher use/risk extraction call.
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
        _validate_existing_pinned_ledger(ledger, provider)
    except ProviderAdapterError as exc:
        raise OrchestrationError(
            "existing provider usage ledger is invalid or unpinned"
        ) from exc
    aggregate_budget = _safe_aggregate_budget_path(
        aggregate_budget_path,
        ledger_path=ledger,
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
    execution_collector = ProviderExecutionCollector()

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
        execution_collector=execution_collector,
        aggregate_budget_path=aggregate_budget,
    )
    fact_checker, factreasoner_status = _build_factreasoner_interface(
        provider=provider,
        ledger_path=ledger,
        decision_dir=decisions,
        environment=environment,
        transport=transport,
        call=call,
        execution_collector=execution_collector,
        aggregate_budget_path=aggregate_budget,
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
    use_risk_signal_source_ids = tuple(
        item.source_id
        for item in eligible
        if build_use_risk_windows(item, windows=build_source_windows(item))
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
        "aggregate_budget_path_sha256": (
            None if aggregate_budget is None else path_sha256(aggregate_budget)
        ),
        "risk_catalog_sha256": (
            None if selected_catalog is None else selected_catalog.catalog_sha256
        ),
        "risk_catalog_status": catalog_status,
        "risk_interface_status": risk_status,
        "family_risk_bridge_version": FAMILY_RISK_BRIDGE_VERSION,
        "factreasoner_interface_status": factreasoner_status,
        "factreasoner_checker_id": fact_checker.checker_id,
        "factreasoner_checker_revision": fact_checker.checker_revision,
        "factreasoner_adapter_version": IBM_FACTREASONER_ADAPTER_VERSION,
        "factreasoner_upstream_revision": IBM_FACTREASONER_UPSTREAM_REVISION,
        "factreasoner_configuration": "FR1",
        "factreasoner_inference_method": IBM_FACTREASONER_INFERENCE_METHOD,
        "factreasoner_relation_probability": IBM_FACTREASONER_RELATION_PROBABILITY,
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
            aggregate_budget_path=aggregate_budget,
            execution_collector=execution_collector,
        )
        claim_checker = OpenRouterClaimChecker(
            provider=provider,
            ledger_path=ledger,
            decision_dir=decisions,
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget_path=aggregate_budget,
            execution_collector=execution_collector,
        )
        family_checker = (
            None
            if risk_detector is None or risk_checker is None
            else OpenRouterFamilyContextChecker(
                provider=provider,
                ledger_path=ledger,
                decision_dir=decisions,
                environment=environment,
                transport=transport,
                call=call,
                aggregate_budget_path=aggregate_budget,
                execution_collector=execution_collector,
            )
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
    semantic_gates = (
        GateName.ENTITY_SCOPE,
        GateName.FIELD_FIT,
        GateName.VALUE_SUPPORT,
    )
    for candidate in quote_candidates:
        for gate in semantic_gates:
            prose_decisions.append(_claim_decision(claim_checker, candidate, gate))
    prose_values = tuple(prose_decisions)
    if len(prose_values) != len(semantic_gates) * len(quote_candidates):
        raise OrchestrationError("provider claim-check coverage is incomplete")

    quote_gate_records = tuple(
        evaluate_claim_gate(
            candidate,
            catalog.documents,
            _matching_decisions(candidate, prose_values),
        )
        for candidate in quote_candidates
    )
    structured_result = deterministic_structured_candidates(catalog)
    publisher_context_result = deterministic_publisher_context_candidates(
        catalog,
        existing_gate_records=quote_gate_records,
    )
    deterministic_context_decisions = (
        deterministic_publisher_context_decisions(publisher_context_result)
    )
    gate_by_candidate: dict[str, ClaimGateRecord] = {
        item.candidate.candidate_id: item for item in quote_gate_records
    }
    for candidate in structured_result.candidates:
        record = evaluate_claim_gate(candidate, catalog.documents)
        prior = gate_by_candidate.setdefault(candidate.candidate_id, record)
        if prior.to_dict() != record.to_dict():
            raise OrchestrationError("structured claim-gate identifier collision")
    for candidate in publisher_context_result.candidates:
        record = evaluate_claim_gate(
            candidate,
            catalog.documents,
            _matching_decisions(candidate, deterministic_context_decisions),
        )
        prior = gate_by_candidate.setdefault(candidate.candidate_id, record)
        if prior.to_dict() != record.to_dict():
            raise OrchestrationError("publisher context claim-gate collision")

    family_applicability_values: list[FamilyContextApplicabilityDecision] = []
    membership_pair = select_config_family_membership(gate_by_candidate.values())
    if membership_pair is not None and family_checker is not None:
        membership_gate, membership = membership_pair
        for record in sorted(
            gate_by_candidate.values(),
            key=lambda item: item.candidate.candidate_id,
        ):
            try:
                validate_family_context_gate(record)
            except FamilyRiskBridgeError:
                continue
            family_applicability_values.append(
                _family_decision(
                    family_checker,
                    record,
                    membership,
                    membership_gate,
                )
            )

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
        family_applicability_decisions=tuple(family_applicability_values),
    )
    execution_path = root / PROVIDER_EXECUTION_MANIFEST_FILENAME
    provider_execution_sha256: str | None = None
    try:
        ledger_has_events = ledger.is_file() and bool(ledger.read_bytes().strip())
    except OSError as exc:
        raise OrchestrationError("provider execution ledger could not be read") from exc
    if execution_collector.bindings or ledger_has_events:
        if not ledger.exists():
            raise OrchestrationError("provider execution evidence is incomplete")
        try:
            risk_payload = _read_json(root / "risk-mapping.json")
            if not isinstance(risk_payload, Mapping) or not isinstance(
                risk_payload.get("use_contexts"), list
            ):
                raise ProviderExecutionError(
                    "provider risk execution artifact is malformed"
                )
            mapping_value = risk_payload.get("taxonomy_mapping")
            typed_mapping = (
                None
                if mapping_value is None
                else RiskMappingReport.from_dict(mapping_value)
            )
            completed_bindings = execution_collector.bindings
            nexus_instruction_sha256s = tuple(
                sorted(
                    item.context_metadata["instruction_sha256"]
                    for item in completed_bindings
                    if item.context_metadata.get("stage")
                    == "nexus_risk_selection"
                )
            )
            risk_applicability_candidate_ids = tuple(
                sorted(
                    item.candidate_id
                    for item in (() if typed_mapping is None else typed_mapping.candidates)
                )
            )
            factreasoner_batch_sha256s = tuple(
                sorted(
                    item.context_metadata["batch_sha256"]
                    for item in completed_bindings
                    if item.context_metadata.get("stage") == "factreasoner_batch"
                )
            )
            expected_nexus_calls = (
                len(risk_payload["use_contexts"])
                if typed_mapping is not None
                and typed_mapping.status is MappingStatus.COMPLETED
                else 0
            )
            if len(nexus_instruction_sha256s) != expected_nexus_calls:
                raise ProviderExecutionError(
                    "provider Nexus execution count differs from risk mapping"
                )
            execution_manifest = ProviderExecutionManifest.build(
                target=catalog.target,
                source_catalog_sha256=catalog.catalog_sha256,
                eligible_text_source_ids=tuple(
                    item.source_id for item in eligible
                ),
                use_risk_signal_source_ids=use_risk_signal_source_ids,
                quote_candidate_ids=tuple(
                    item.candidate_id for item in quote_candidates
                ),
                family_applicability_candidate_ids=tuple(
                    sorted(
                        item.family_candidate_id
                        for item in family_applicability_values
                        if item.status is not FamilyDecisionStatus.UNAVAILABLE
                    )
                ),
                family_applicability_failed_candidate_ids=tuple(
                    sorted(
                        item.family_candidate_id
                        for item in family_applicability_values
                        if item.status is FamilyDecisionStatus.UNAVAILABLE
                    )
                ),
                nexus_instruction_sha256s=nexus_instruction_sha256s,
                risk_applicability_candidate_ids=(
                    risk_applicability_candidate_ids
                ),
                factreasoner_batch_sha256s=factreasoner_batch_sha256s,
                pipeline_result_sha256=pipeline_result.result_sha256,
                content_factreasoner_sha256=(
                    pipeline_result.content_factreasoner_sha256
                ),
                publication_original_factreasoner_sha256=(
                    pipeline_result.publication_original_factreasoner_sha256
                ),
                final_factreasoner_sha256=pipeline_result.factreasoner_sha256,
                risk_mapping_report_sha256=(
                    pipeline_result.risk.mapping_report_sha256
                ),
                adapter_version=ADAPTER_VERSION,
                orchestration_version=ORCHESTRATION_VERSION,
                max_risks=max_risks,
                ledger_path=ledger,
                executions=execution_collector.bindings,
            )
            execution_manifest.verify_run(root)
        except (ProviderExecutionError, RiskMappingError) as exc:
            raise OrchestrationError(
                "provider execution evidence failed closed"
            ) from exc
        _atomic_admit(execution_path, execution_manifest.to_dict())
        provider_execution_sha256 = execution_manifest.manifest_sha256
    elif execution_path.exists() or execution_path.is_symlink():
        raise OrchestrationError("provider execution evidence is incomplete")
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
        factreasoner_interface_status=factreasoner_status,
        provider_execution_sha256=provider_execution_sha256,
        pipeline_result=pipeline_result,
    )


__all__ = [
    "DEFAULT_MAX_RISKS",
    "ORCHESTRATION_MANIFEST_FILENAME",
    "PROVIDER_EXECUTION_MANIFEST_FILENAME",
    "ORCHESTRATION_SCOPE",
    "ORCHESTRATION_VERSION",
    "OrchestrationError",
    "ProviderOrchestrationResult",
    "run_provider_assisted_pipeline",
]
