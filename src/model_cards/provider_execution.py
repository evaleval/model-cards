"""Local-only manifest binding semantic outputs to settled provider calls.

The public card never contains this material.  A provider-assisted run records
one deduplicated manifest beside ``usage.jsonl`` and ``provider-decisions`` so
review closure can replay exact structured requests without credentials,
network access, or new ledger writes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import threading
from typing import Any, Mapping

from .models import TargetIdentity
from .pipeline import PipelineResult
from .provider import (
    MODEL_ID,
    PINNED_PROVIDER,
    PROVIDER_RUNTIME_VERSION,
    RECOVERABLE_PROVIDER_FAILURE_REASON_CODES,
    ProviderError,
    ProviderExecutionBinding,
    verify_provider_execution,
)
from .run_ledger import (
    AttemptBinding,
    AttemptSnapshot,
    LedgerError,
    UsageLedger,
    UsageReceipt,
)


PROVIDER_EXECUTION_MANIFEST_VERSION = "provider-execution-manifest/v3"
PROVIDER_EXECUTION_MANIFEST_FILENAME = "provider-execution.json"

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[a-z0-9][a-z0-9._/-]{2,127}$")
_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{1,127}$")
_CLAIM_ID_RE = re.compile(r"^claim-[0-9a-f]{24}$")
_RISK_CANDIDATE_ID_RE = re.compile(r"^risk-candidate-[0-9a-f]{24}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_QUOTE_EXTRACTION_STAGE = "quote_extraction"
_USE_RISK_EXTRACTION_STAGE = "quote_extraction_use_risk"
_CLAIM_GATE_STAGES = ("entity_scope", "field_fit", "value_support")
_FAMILY_APPLICABILITY_STAGE = "family_applicability"
_NEXUS_SELECTION_STAGE = "nexus_risk_selection"
_RISK_APPLICABILITY_STAGE = "risk_applicability"
_FACTREASONER_STAGE = "factreasoner_batch"
_RECOVERABLE_FAILED_OUTCOMES = frozenset(
    {"terminal_http_error", "invalid_response", "retryable_http_error"}
)
_ALLOWED_STAGES = frozenset(
    {
        _QUOTE_EXTRACTION_STAGE,
        _USE_RISK_EXTRACTION_STAGE,
        *_CLAIM_GATE_STAGES,
        _FAMILY_APPLICABILITY_STAGE,
        _NEXUS_SELECTION_STAGE,
        _RISK_APPLICABILITY_STAGE,
        _FACTREASONER_STAGE,
    }
)


class ProviderExecutionError(ValueError):
    """Provider execution evidence is missing, stale, or internally inconsistent."""


def _canonical(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise ProviderExecutionError("provider execution value is not finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _canonical_ids(
    values: Any,
    *,
    pattern: re.Pattern[str],
    label: str,
) -> tuple[str, ...]:
    try:
        identifiers = tuple(values)
    except TypeError as exc:
        raise ProviderExecutionError(
            f"provider execution {label} identifiers are invalid"
        ) from exc
    if any(
        not isinstance(item, str) or not pattern.fullmatch(item)
        for item in identifiers
    ) or identifiers != tuple(sorted(set(identifiers))):
        raise ProviderExecutionError(
            f"provider execution {label} identifiers are not canonical"
        )
    return identifiers


@dataclass(frozen=True)
class ProviderFailedExecutionBinding:
    """Privacy-safe proof of one safely settled, recoverable failed attempt."""

    attempt: AttemptBinding
    reservation_id: str
    outcome: str
    reason_code: str
    receipt: UsageReceipt
    failure_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, AttemptBinding):
            raise ProviderExecutionError("provider failure attempt is invalid")
        if self.attempt.provider != PINNED_PROVIDER:
            raise ProviderExecutionError("provider failure route is not pinned")
        if (
            not isinstance(self.reservation_id, str)
            or not re.fullmatch(r"reservation_[0-9a-f]{24}", self.reservation_id)
            or not isinstance(self.outcome, str)
            or self.outcome not in _RECOVERABLE_FAILED_OUTCOMES
            or not isinstance(self.reason_code, str)
            or (
                self.outcome == "retryable_http_error"
                and self.reason_code != "retry_exhausted"
            )
            or not _REASON_RE.fullmatch(self.reason_code)
            or self.reason_code not in RECOVERABLE_PROVIDER_FAILURE_REASON_CODES
            or not isinstance(self.receipt, UsageReceipt)
        ):
            raise ProviderExecutionError("provider failure terminal is invalid")
        object.__setattr__(self, "failure_sha256", _digest(self._payload()))

    @property
    def context_metadata(self) -> Mapping[str, Any]:
        return self.attempt.context_metadata

    @property
    def logical_call_id(self) -> str:
        return self.attempt.logical_call_id

    @property
    def attempt_id(self) -> str:
        return self.attempt.attempt_id

    def _payload(self) -> dict[str, Any]:
        return {
            "attempt": self.attempt.to_dict(),
            "reservation_id": self.reservation_id,
            "outcome": self.outcome,
            "reason_code": self.reason_code,
            "receipt": self.receipt.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "failure_sha256": self.failure_sha256}

    @classmethod
    def from_dict(cls, value: Any) -> "ProviderFailedExecutionBinding":
        expected = {
            "attempt",
            "reservation_id",
            "outcome",
            "reason_code",
            "receipt",
            "failure_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ProviderExecutionError("provider failure binding has an invalid shape")
        try:
            result = cls(
                attempt=AttemptBinding.from_dict(value["attempt"]),
                reservation_id=value["reservation_id"],
                outcome=value["outcome"],
                reason_code=value["reason_code"],
                receipt=UsageReceipt.from_dict(value["receipt"]),
            )
        except LedgerError as exc:
            raise ProviderExecutionError("provider failure binding is invalid") from exc
        if result.failure_sha256 != value["failure_sha256"]:
            raise ProviderExecutionError("provider failure digest is inconsistent")
        return result

    @classmethod
    def from_snapshot(
        cls, snapshot: AttemptSnapshot
    ) -> "ProviderFailedExecutionBinding":
        if not isinstance(snapshot, AttemptSnapshot) or snapshot.status != "failed":
            raise ProviderExecutionError("provider failure snapshot is not settled")
        terminal = snapshot.latest_terminal
        if terminal is None or not isinstance(terminal.get("payload"), Mapping):
            raise ProviderExecutionError("provider failure terminal is missing")
        payload = terminal["payload"]
        if payload.get("decision_sha256") is not None or payload.get(
            "sidecar_sha256"
        ) is not None:
            raise ProviderExecutionError("provider failure unexpectedly has a decision")
        try:
            return cls(
                attempt=snapshot.binding,
                reservation_id=payload["reservation_id"],
                outcome=payload["outcome"],
                reason_code=payload["reason_code"],
                receipt=UsageReceipt.from_dict(payload["receipt"]),
            )
        except (KeyError, LedgerError) as exc:
            raise ProviderExecutionError("provider failure terminal is malformed") from exc

    def verify(self, ledger_path: str | os.PathLike[str]) -> None:
        try:
            snapshot = UsageLedger(ledger_path).inspect_read_only(self.attempt)
        except LedgerError as exc:
            raise ProviderExecutionError("provider failure ledger replay failed") from exc
        if snapshot is None or snapshot.status != "failed":
            raise ProviderExecutionError("provider failure is not failed in the ledger")
        replayed = ProviderFailedExecutionBinding.from_snapshot(snapshot)
        if replayed.to_dict() != self.to_dict():
            raise ProviderExecutionError("provider failure differs from its ledger terminal")


def _ledger_inventory(
    ledger_path: Path,
) -> tuple[tuple[AttemptBinding, ...], tuple[ProviderFailedExecutionBinding, ...]]:
    """Return all completed attempts and exact recoverable terminal failures."""

    try:
        raw = ledger_path.read_bytes()
        rows = [json.loads(line) for line in raw.splitlines() if line]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderExecutionError("provider execution ledger is malformed") from exc
    attempts: list[AttemptBinding] = []
    try:
        for row in rows:
            if isinstance(row, Mapping) and row.get("event") == "attempt_manifest":
                attempts.append(AttemptBinding.from_dict(row.get("payload")))
    except LedgerError as exc:
        raise ProviderExecutionError("provider execution ledger attempt is invalid") from exc
    completed: list[AttemptBinding] = []
    failures: list[ProviderFailedExecutionBinding] = []
    ledger = UsageLedger(ledger_path)
    for attempt in attempts:
        try:
            snapshot = ledger.inspect_read_only(attempt)
        except LedgerError as exc:
            raise ProviderExecutionError("provider execution ledger failed replay") from exc
        if snapshot is None:
            raise ProviderExecutionError("provider execution ledger lost an attempt")
        if snapshot.status == "completed":
            completed.append(attempt)
        elif snapshot.status == "failed":
            failures.append(ProviderFailedExecutionBinding.from_snapshot(snapshot))
        else:
            raise ProviderExecutionError(
                "provider execution ledger contains an unsettled attempt"
            )
    keys = [(item.logical_call_id, item.attempt_id) for item in attempts]
    if len(keys) != len(set(keys)):
        raise ProviderExecutionError("provider execution ledger repeats an attempt")
    return (
        tuple(sorted(completed, key=lambda item: (item.logical_call_id, item.attempt_id))),
        tuple(sorted(failures, key=lambda item: item.failure_sha256)),
    )


def _verify_semantic_coverage(
    executions: tuple[ProviderExecutionBinding, ...],
    failures: tuple[ProviderFailedExecutionBinding, ...],
    *,
    source_catalog_sha256: str,
    eligible_text_source_ids: tuple[str, ...],
    use_risk_signal_source_ids: tuple[str, ...],
    quote_candidate_ids: tuple[str, ...],
    family_applicability_candidate_ids: tuple[str, ...],
    family_applicability_failed_candidate_ids: tuple[str, ...],
    nexus_instruction_sha256s: tuple[str, ...],
    risk_applicability_candidate_ids: tuple[str, ...],
    factreasoner_batch_sha256s: tuple[str, ...],
) -> None:
    """Prove the provider stages ran even when their decisions were empty."""

    quote_extractions: Counter[str] = Counter()
    use_risk_extractions: Counter[str] = Counter()
    claim_gates: dict[str, Counter[str]] = {
        stage: Counter() for stage in _CLAIM_GATE_STAGES
    }
    failed_claim_gates: dict[str, Counter[str]] = {
        stage: Counter() for stage in _CLAIM_GATE_STAGES
    }
    family_applicability: Counter[str] = Counter()
    failed_family_applicability: Counter[str] = Counter()
    nexus_selections: Counter[str] = Counter()
    risk_applicability: Counter[str] = Counter()
    factreasoner_attempts: dict[
        str, list[tuple[int, bool, str | None]]
    ] = {}

    entries: tuple[tuple[Any, bool], ...] = tuple(
        (item, False) for item in executions
    ) + tuple((item, True) for item in failures)
    for entry, failed in entries:
        metadata = dict(entry.context_metadata)
        stage = metadata.get("stage")
        if not isinstance(stage, str) or not re.fullmatch(
            r"[a-z][a-z0-9_]{2,63}", stage
        ):
            raise ProviderExecutionError(
                "provider execution stage metadata is invalid"
            )
        if stage not in _ALLOWED_STAGES:
            raise ProviderExecutionError("provider execution stage is unexpected")
        if stage in {_QUOTE_EXTRACTION_STAGE, _USE_RISK_EXTRACTION_STAGE}:
            if failed:
                raise ProviderExecutionError(
                    "provider extraction failures cannot seal a completed run"
                )
            if set(metadata) != {"stage", "source_id", "catalog_sha256"}:
                raise ProviderExecutionError(
                    "provider extraction execution metadata is invalid"
                )
            source_id = metadata["source_id"]
            if (
                not isinstance(source_id, str)
                or not _SOURCE_ID_RE.fullmatch(source_id)
                or metadata["catalog_sha256"] != source_catalog_sha256
            ):
                raise ProviderExecutionError(
                    "provider extraction execution metadata is stale"
                )
            expected_logical = (
                f"extract.{source_id}.{source_catalog_sha256[:16]}"
                if stage == _QUOTE_EXTRACTION_STAGE
                else f"extract-use-risk.{source_id}.{source_catalog_sha256[:16]}"
            )
            if entry.logical_call_id != expected_logical:
                raise ProviderExecutionError(
                    "provider extraction logical identity is inconsistent"
                )
            counter = (
                quote_extractions
                if stage == _QUOTE_EXTRACTION_STAGE
                else use_risk_extractions
            )
            counter[source_id] += 1
        elif stage in claim_gates:
            if set(metadata) != {"stage", "candidate_id"}:
                raise ProviderExecutionError(
                    "provider claim-gate execution metadata is invalid"
                )
            candidate_id = metadata["candidate_id"]
            if (
                not isinstance(candidate_id, str)
                or not _CLAIM_ID_RE.fullmatch(candidate_id)
            ):
                raise ProviderExecutionError(
                    "provider claim-gate execution metadata is invalid"
                )
            if entry.logical_call_id != f"claim.{stage}.{candidate_id}":
                raise ProviderExecutionError(
                    "provider claim-gate logical identity is inconsistent"
                )
            (failed_claim_gates if failed else claim_gates)[stage][candidate_id] += 1
        elif stage == _FAMILY_APPLICABILITY_STAGE:
            if set(metadata) != {"stage", "candidate_id"}:
                raise ProviderExecutionError(
                    "provider family-applicability execution metadata is invalid"
                )
            candidate_id = metadata["candidate_id"]
            if (
                not isinstance(candidate_id, str)
                or not _CLAIM_ID_RE.fullmatch(candidate_id)
            ):
                raise ProviderExecutionError(
                    "provider family-applicability execution metadata is invalid"
                )
            if entry.logical_call_id != f"family.applicability.{candidate_id}":
                raise ProviderExecutionError(
                    "provider family-applicability logical identity is inconsistent"
                )
            (
                failed_family_applicability if failed else family_applicability
            )[candidate_id] += 1
        elif stage == _NEXUS_SELECTION_STAGE:
            if failed or set(metadata) != {"stage", "instruction_sha256"}:
                raise ProviderExecutionError(
                    "provider Nexus execution metadata is invalid"
                )
            instruction_sha256 = metadata["instruction_sha256"]
            if (
                not isinstance(instruction_sha256, str)
                or not _DIGEST_RE.fullmatch(instruction_sha256)
                or entry.logical_call_id
                != f"nexus.risk_selection.{instruction_sha256[:24]}"
            ):
                raise ProviderExecutionError(
                    "provider Nexus execution identity is inconsistent"
                )
            nexus_selections[instruction_sha256] += 1
        elif stage == _RISK_APPLICABILITY_STAGE:
            if failed or set(metadata) != {"stage", "risk_candidate_id"}:
                raise ProviderExecutionError(
                    "provider risk-applicability execution metadata is invalid"
                )
            risk_candidate_id = metadata["risk_candidate_id"]
            if (
                not isinstance(risk_candidate_id, str)
                or not _RISK_CANDIDATE_ID_RE.fullmatch(risk_candidate_id)
                or entry.logical_call_id
                != f"risk.applicability.{risk_candidate_id}"
            ):
                raise ProviderExecutionError(
                    "provider risk-applicability execution identity is inconsistent"
                )
            risk_applicability[risk_candidate_id] += 1
        elif stage == _FACTREASONER_STAGE:
            if set(metadata) != {"stage", "batch_sha256", "request_count"}:
                raise ProviderExecutionError(
                    "provider FactReasoner execution metadata is invalid"
                )
            batch_sha256 = metadata["batch_sha256"]
            request_count = metadata["request_count"]
            if (
                not isinstance(batch_sha256, str)
                or not _DIGEST_RE.fullmatch(batch_sha256)
                or isinstance(request_count, bool)
                or not isinstance(request_count, int)
                or not 1 <= request_count <= 64
                or entry.logical_call_id != f"fact.batch.{batch_sha256[:24]}"
            ):
                raise ProviderExecutionError(
                    "provider FactReasoner execution identity is inconsistent"
                )
            attempt_prefix = entry.logical_call_id + ".attempt"
            if not entry.attempt_id.startswith(attempt_prefix):
                raise ProviderExecutionError(
                    "provider FactReasoner attempt identity is inconsistent"
                )
            attempt_text = entry.attempt_id[len(attempt_prefix) :]
            if attempt_text not in {"1", "2"}:
                raise ProviderExecutionError(
                    "provider FactReasoner semantic attempt is out of bounds"
                )
            factreasoner_attempts.setdefault(batch_sha256, []).append(
                (
                    int(attempt_text),
                    failed,
                    entry.reason_code if failed else None,
                )
            )

    expected_quote_extractions = Counter(
        {source_id: 1 for source_id in eligible_text_source_ids}
    )
    if quote_extractions != expected_quote_extractions:
        raise ProviderExecutionError(
            "provider quote extraction receipt coverage is incomplete or duplicated"
        )
    expected_use_risk_extractions = Counter(
        {source_id: 1 for source_id in use_risk_signal_source_ids}
    )
    if use_risk_extractions != expected_use_risk_extractions:
        raise ProviderExecutionError(
            "provider use/risk extraction receipt coverage is incomplete, "
            "duplicated, or unexpected"
        )
    expected_claim_gates = Counter(
        {candidate_id: 1 for candidate_id in quote_candidate_ids}
    )
    for stage, observed in claim_gates.items():
        failed_observed = failed_claim_gates[stage]
        if set(observed) | set(failed_observed) != set(expected_claim_gates) or any(
            observed[candidate_id] not in {0, 1}
            or failed_observed[candidate_id] not in {0, 1}
            or observed[candidate_id] + failed_observed[candidate_id] != 1
            for candidate_id in expected_claim_gates
        ):
            raise ProviderExecutionError(
                f"provider {stage} receipt coverage is incomplete or duplicated"
            )
    expected_family_applicability = Counter(
        {candidate_id: 1 for candidate_id in family_applicability_candidate_ids}
    )
    if family_applicability != expected_family_applicability:
        raise ProviderExecutionError(
            "provider family_applicability receipt coverage is incomplete, "
            "duplicated, or unexpected"
        )
    expected_failed_family = Counter(
        {candidate_id: 1 for candidate_id in family_applicability_failed_candidate_ids}
    )
    if failed_family_applicability != expected_failed_family:
        raise ProviderExecutionError(
            "provider failed family_applicability receipt coverage is incomplete, "
            "duplicated, or unexpected"
        )
    if nexus_selections != Counter(
        {instruction_sha256: 1 for instruction_sha256 in nexus_instruction_sha256s}
    ):
        raise ProviderExecutionError(
            "provider Nexus receipt coverage is incomplete, duplicated, or unexpected"
        )
    if risk_applicability != Counter(
        {candidate_id: 1 for candidate_id in risk_applicability_candidate_ids}
    ):
        raise ProviderExecutionError(
            "provider risk-applicability receipt coverage is incomplete, duplicated, "
            "or unexpected"
        )
    expected_fact_batches = set(factreasoner_batch_sha256s)
    if set(factreasoner_attempts) != expected_fact_batches:
        raise ProviderExecutionError(
            "provider FactReasoner receipt coverage is incomplete, duplicated, or "
            "unexpected"
        )
    for batch_sha256 in expected_fact_batches:
        attempts = sorted(factreasoner_attempts[batch_sha256])
        if len({number for number, _failed, _reason in attempts}) != len(attempts):
            raise ProviderExecutionError(
                "provider FactReasoner semantic attempt is duplicated"
            )
        if len(attempts) == 1:
            number, failed, reason = attempts[0]
            valid = number == 1 and (
                not failed or reason != "structured_decision_invalid"
            )
        elif len(attempts) == 2:
            first, second = attempts
            valid = (
                first == (1, True, "structured_decision_invalid")
                and second[0] == 2
            )
        else:
            valid = False
        if not valid:
            raise ProviderExecutionError(
                "provider FactReasoner semantic retry sequence is invalid"
            )


class ProviderExecutionCollector:
    """Process-local, thread-safe collector for new and resumed structured calls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bindings: dict[str, ProviderExecutionBinding] = {}

    def record(self, execution: ProviderExecutionBinding) -> None:
        if not isinstance(execution, ProviderExecutionBinding):
            raise ProviderExecutionError("collector requires a typed execution binding")
        with self._lock:
            prior = self._bindings.setdefault(execution.binding_sha256, execution)
            if prior.to_dict() != execution.to_dict():
                raise ProviderExecutionError("execution binding digest collision")

    @property
    def bindings(self) -> tuple[ProviderExecutionBinding, ...]:
        with self._lock:
            return tuple(self._bindings[key] for key in sorted(self._bindings))


@dataclass(frozen=True)
class ProviderExecutionManifest:
    target: TargetIdentity
    source_catalog_sha256: str
    eligible_text_source_ids: tuple[str, ...]
    use_risk_signal_source_ids: tuple[str, ...]
    quote_candidate_ids: tuple[str, ...]
    family_applicability_candidate_ids: tuple[str, ...]
    family_applicability_failed_candidate_ids: tuple[str, ...]
    nexus_instruction_sha256s: tuple[str, ...]
    risk_applicability_candidate_ids: tuple[str, ...]
    factreasoner_batch_sha256s: tuple[str, ...]
    pipeline_result_sha256: str
    content_factreasoner_sha256: str
    publication_original_factreasoner_sha256: str
    final_factreasoner_sha256: str
    risk_mapping_report_sha256: str | None
    adapter_version: str
    orchestration_version: str
    max_risks: int
    ledger_sha256: str
    ledger_event_count: int
    executions: tuple[ProviderExecutionBinding, ...]
    failed_executions: tuple[ProviderFailedExecutionBinding, ...]
    model: str = MODEL_ID
    provider: str = PINNED_PROVIDER
    provider_runtime_version: str = PROVIDER_RUNTIME_VERSION
    manifest_version: str = PROVIDER_EXECUTION_MANIFEST_VERSION
    manifest_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if self.manifest_version != PROVIDER_EXECUTION_MANIFEST_VERSION:
            raise ProviderExecutionError("provider execution manifest version is invalid")
        if not isinstance(self.target, TargetIdentity):
            raise ProviderExecutionError("provider execution target is invalid")
        if (
            self.model != MODEL_ID
            or self.provider != PINNED_PROVIDER
            or self.provider_runtime_version != PROVIDER_RUNTIME_VERSION
        ):
            raise ProviderExecutionError("provider execution route identity is not pinned")
        for name in (
            "source_catalog_sha256",
            "pipeline_result_sha256",
            "content_factreasoner_sha256",
            "publication_original_factreasoner_sha256",
            "final_factreasoner_sha256",
            "ledger_sha256",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
                raise ProviderExecutionError(f"provider execution {name} is invalid")
        if self.risk_mapping_report_sha256 is not None and not _DIGEST_RE.fullmatch(
            self.risk_mapping_report_sha256
        ):
            raise ProviderExecutionError("provider execution risk mapping digest is invalid")
        for name in ("adapter_version", "orchestration_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
                raise ProviderExecutionError(f"provider execution {name} is invalid")
        if (
            isinstance(self.max_risks, bool)
            or not isinstance(self.max_risks, int)
            or not 1 <= self.max_risks <= 10
        ):
            raise ProviderExecutionError("provider execution max_risks is invalid")
        if (
            isinstance(self.ledger_event_count, bool)
            or not isinstance(self.ledger_event_count, int)
            or self.ledger_event_count < 0
        ):
            raise ProviderExecutionError("provider execution ledger count is invalid")
        try:
            raw_executions = tuple(self.executions)
        except TypeError as exc:
            raise ProviderExecutionError(
                "provider execution entries are malformed"
            ) from exc
        if not all(isinstance(item, ProviderExecutionBinding) for item in raw_executions):
            raise ProviderExecutionError("provider execution entries are malformed")
        executions = tuple(
            sorted(raw_executions, key=lambda item: item.binding_sha256)
        )
        if any(item.model != self.model or item.provider != self.provider for item in executions):
            raise ProviderExecutionError("provider execution entry used another route")
        if len({item.binding_sha256 for item in executions}) != len(executions):
            raise ProviderExecutionError("provider execution entries are duplicated")
        if len({item.decision_name for item in executions}) != len(executions):
            raise ProviderExecutionError("provider execution decision names are duplicated")
        if len({(item.logical_call_id, item.attempt_id) for item in executions}) != len(
            executions
        ):
            raise ProviderExecutionError("provider execution attempts are duplicated")
        try:
            raw_failures = tuple(self.failed_executions)
        except TypeError as exc:
            raise ProviderExecutionError(
                "provider failed execution entries are malformed"
            ) from exc
        if not all(
            isinstance(item, ProviderFailedExecutionBinding) for item in raw_failures
        ):
            raise ProviderExecutionError(
                "provider failed execution entries are malformed"
            )
        failures = tuple(sorted(raw_failures, key=lambda item: item.failure_sha256))
        if len({item.failure_sha256 for item in failures}) != len(failures) or len(
            {(item.logical_call_id, item.attempt_id) for item in failures}
        ) != len(failures):
            raise ProviderExecutionError("provider failed executions are duplicated")
        if {
            (item.logical_call_id, item.attempt_id) for item in executions
        } & {(item.logical_call_id, item.attempt_id) for item in failures}:
            raise ProviderExecutionError(
                "provider attempt is both completed and failed"
            )
        eligible_source_ids = _canonical_ids(
            self.eligible_text_source_ids,
            pattern=_SOURCE_ID_RE,
            label="eligible text source",
        )
        use_risk_source_ids = _canonical_ids(
            self.use_risk_signal_source_ids,
            pattern=_SOURCE_ID_RE,
            label="use/risk signal source",
        )
        quote_candidate_ids = _canonical_ids(
            self.quote_candidate_ids,
            pattern=_CLAIM_ID_RE,
            label="quote candidate",
        )
        family_applicability_candidate_ids = _canonical_ids(
            self.family_applicability_candidate_ids,
            pattern=_CLAIM_ID_RE,
            label="family applicability candidate",
        )
        family_applicability_failed_candidate_ids = _canonical_ids(
            self.family_applicability_failed_candidate_ids,
            pattern=_CLAIM_ID_RE,
            label="failed family applicability candidate",
        )
        if set(family_applicability_candidate_ids) & set(
            family_applicability_failed_candidate_ids
        ):
            raise ProviderExecutionError(
                "family applicability completion and failure coverage overlap"
            )
        nexus_instruction_sha256s = _canonical_ids(
            self.nexus_instruction_sha256s,
            pattern=_DIGEST_RE,
            label="Nexus instruction",
        )
        risk_applicability_candidate_ids = _canonical_ids(
            self.risk_applicability_candidate_ids,
            pattern=_RISK_CANDIDATE_ID_RE,
            label="risk applicability candidate",
        )
        factreasoner_batch_sha256s = _canonical_ids(
            self.factreasoner_batch_sha256s,
            pattern=_DIGEST_RE,
            label="FactReasoner batch",
        )
        if not set(use_risk_source_ids).issubset(eligible_source_ids):
            raise ProviderExecutionError(
                "use/risk signal sources must be eligible text sources"
            )
        _verify_semantic_coverage(
            executions,
            failures,
            source_catalog_sha256=self.source_catalog_sha256,
            eligible_text_source_ids=eligible_source_ids,
            use_risk_signal_source_ids=use_risk_source_ids,
            quote_candidate_ids=quote_candidate_ids,
            family_applicability_candidate_ids=(
                family_applicability_candidate_ids
            ),
            family_applicability_failed_candidate_ids=(
                family_applicability_failed_candidate_ids
            ),
            nexus_instruction_sha256s=nexus_instruction_sha256s,
            risk_applicability_candidate_ids=risk_applicability_candidate_ids,
            factreasoner_batch_sha256s=factreasoner_batch_sha256s,
        )
        object.__setattr__(self, "executions", executions)
        object.__setattr__(self, "failed_executions", failures)
        object.__setattr__(self, "eligible_text_source_ids", eligible_source_ids)
        object.__setattr__(self, "use_risk_signal_source_ids", use_risk_source_ids)
        object.__setattr__(self, "quote_candidate_ids", quote_candidate_ids)
        object.__setattr__(
            self,
            "family_applicability_candidate_ids",
            family_applicability_candidate_ids,
        )
        object.__setattr__(
            self,
            "family_applicability_failed_candidate_ids",
            family_applicability_failed_candidate_ids,
        )
        object.__setattr__(self, "nexus_instruction_sha256s", nexus_instruction_sha256s)
        object.__setattr__(
            self,
            "risk_applicability_candidate_ids",
            risk_applicability_candidate_ids,
        )
        object.__setattr__(
            self, "factreasoner_batch_sha256s", factreasoner_batch_sha256s
        )
        object.__setattr__(self, "manifest_sha256", _digest(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "model": self.model,
            "provider": self.provider,
            "provider_runtime_version": self.provider_runtime_version,
            "adapter_version": self.adapter_version,
            "orchestration_version": self.orchestration_version,
            "max_risks": self.max_risks,
            "target": self.target.to_dict(),
            "source_catalog_sha256": self.source_catalog_sha256,
            "eligible_text_source_ids": list(self.eligible_text_source_ids),
            "use_risk_signal_source_ids": list(self.use_risk_signal_source_ids),
            "quote_candidate_ids": list(self.quote_candidate_ids),
            "family_applicability_candidate_ids": list(
                self.family_applicability_candidate_ids
            ),
            "family_applicability_failed_candidate_ids": list(
                self.family_applicability_failed_candidate_ids
            ),
            "nexus_instruction_sha256s": list(self.nexus_instruction_sha256s),
            "risk_applicability_candidate_ids": list(
                self.risk_applicability_candidate_ids
            ),
            "factreasoner_batch_sha256s": list(
                self.factreasoner_batch_sha256s
            ),
            "pipeline_result_sha256": self.pipeline_result_sha256,
            "content_factreasoner_sha256": self.content_factreasoner_sha256,
            "publication_original_factreasoner_sha256": (
                self.publication_original_factreasoner_sha256
            ),
            "final_factreasoner_sha256": self.final_factreasoner_sha256,
            "risk_mapping_report_sha256": self.risk_mapping_report_sha256,
            "ledger_sha256": self.ledger_sha256,
            "ledger_event_count": self.ledger_event_count,
            "executions": [item.to_dict() for item in self.executions],
            "failed_executions": [
                item.to_dict() for item in self.failed_executions
            ],
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "manifest_sha256": self.manifest_sha256}

    @classmethod
    def build(
        cls,
        *,
        target: TargetIdentity,
        source_catalog_sha256: str,
        eligible_text_source_ids: tuple[str, ...],
        use_risk_signal_source_ids: tuple[str, ...],
        quote_candidate_ids: tuple[str, ...],
        family_applicability_candidate_ids: tuple[str, ...],
        family_applicability_failed_candidate_ids: tuple[str, ...],
        nexus_instruction_sha256s: tuple[str, ...],
        risk_applicability_candidate_ids: tuple[str, ...],
        factreasoner_batch_sha256s: tuple[str, ...],
        pipeline_result_sha256: str,
        content_factreasoner_sha256: str,
        publication_original_factreasoner_sha256: str,
        final_factreasoner_sha256: str,
        risk_mapping_report_sha256: str | None,
        adapter_version: str,
        orchestration_version: str,
        max_risks: int,
        ledger_path: str | os.PathLike[str],
        executions: tuple[ProviderExecutionBinding, ...],
    ) -> "ProviderExecutionManifest":
        ledger = Path(ledger_path)
        if ledger.is_symlink() or not ledger.is_file():
            raise ProviderExecutionError("provider execution ledger is missing or unsafe")
        raw = ledger.read_bytes()
        completed_attempts, failed_executions = _ledger_inventory(ledger)
        completed_by_key = {
            (item.logical_call_id, item.attempt_id): item.to_dict()
            for item in completed_attempts
        }
        execution_by_key = {
            (item.logical_call_id, item.attempt_id): item.attempt_binding.to_dict()
            for item in executions
        }
        if completed_by_key != execution_by_key:
            raise ProviderExecutionError(
                "provider completed ledger inventory differs from collected executions"
            )
        failed_fact_batches = {
            item.context_metadata.get("batch_sha256")
            for item in failed_executions
            if item.context_metadata.get("stage") == _FACTREASONER_STAGE
        }
        if any(
            not isinstance(item, str) or not _DIGEST_RE.fullmatch(item)
            for item in failed_fact_batches
        ):
            raise ProviderExecutionError(
                "failed FactReasoner batch identity is invalid"
            )
        all_factreasoner_batch_sha256s = tuple(
            sorted(set(factreasoner_batch_sha256s) | failed_fact_batches)
        )
        return cls(
            target=target,
            source_catalog_sha256=source_catalog_sha256,
            eligible_text_source_ids=eligible_text_source_ids,
            use_risk_signal_source_ids=use_risk_signal_source_ids,
            quote_candidate_ids=quote_candidate_ids,
            family_applicability_candidate_ids=(
                family_applicability_candidate_ids
            ),
            family_applicability_failed_candidate_ids=(
                family_applicability_failed_candidate_ids
            ),
            nexus_instruction_sha256s=nexus_instruction_sha256s,
            risk_applicability_candidate_ids=risk_applicability_candidate_ids,
            factreasoner_batch_sha256s=all_factreasoner_batch_sha256s,
            pipeline_result_sha256=pipeline_result_sha256,
            content_factreasoner_sha256=content_factreasoner_sha256,
            publication_original_factreasoner_sha256=(
                publication_original_factreasoner_sha256
            ),
            final_factreasoner_sha256=final_factreasoner_sha256,
            risk_mapping_report_sha256=risk_mapping_report_sha256,
            adapter_version=adapter_version,
            orchestration_version=orchestration_version,
            max_risks=max_risks,
            ledger_sha256=hashlib.sha256(raw).hexdigest(),
            ledger_event_count=sum(1 for line in raw.splitlines() if line.strip()),
            executions=executions,
            failed_executions=failed_executions,
        )

    @classmethod
    def from_dict(cls, value: Any) -> "ProviderExecutionManifest":
        expected = {
            "manifest_version",
            "model",
            "provider",
            "provider_runtime_version",
            "adapter_version",
            "orchestration_version",
            "max_risks",
            "target",
            "source_catalog_sha256",
            "eligible_text_source_ids",
            "use_risk_signal_source_ids",
            "quote_candidate_ids",
            "family_applicability_candidate_ids",
            "family_applicability_failed_candidate_ids",
            "nexus_instruction_sha256s",
            "risk_applicability_candidate_ids",
            "factreasoner_batch_sha256s",
            "pipeline_result_sha256",
            "content_factreasoner_sha256",
            "publication_original_factreasoner_sha256",
            "final_factreasoner_sha256",
            "risk_mapping_report_sha256",
            "ledger_sha256",
            "ledger_event_count",
            "executions",
            "failed_executions",
            "manifest_sha256",
        }
        if not isinstance(value, Mapping) or set(value) != expected:
            raise ProviderExecutionError("provider execution manifest has an invalid shape")
        if not isinstance(value["executions"], list) or not isinstance(
            value["failed_executions"], list
        ):
            raise ProviderExecutionError("provider execution manifest entries are invalid")
        for name in (
            "eligible_text_source_ids",
            "use_risk_signal_source_ids",
            "quote_candidate_ids",
            "family_applicability_candidate_ids",
            "family_applicability_failed_candidate_ids",
            "nexus_instruction_sha256s",
            "risk_applicability_candidate_ids",
            "factreasoner_batch_sha256s",
        ):
            if not isinstance(value[name], list):
                raise ProviderExecutionError(
                    "provider execution coverage identifiers are invalid"
                )
        result = cls(
            manifest_version=value["manifest_version"],
            model=value["model"],
            provider=value["provider"],
            provider_runtime_version=value["provider_runtime_version"],
            adapter_version=value["adapter_version"],
            orchestration_version=value["orchestration_version"],
            max_risks=value["max_risks"],
            target=TargetIdentity.from_dict(value["target"]),
            source_catalog_sha256=value["source_catalog_sha256"],
            eligible_text_source_ids=tuple(value["eligible_text_source_ids"]),
            use_risk_signal_source_ids=tuple(value["use_risk_signal_source_ids"]),
            quote_candidate_ids=tuple(value["quote_candidate_ids"]),
            family_applicability_candidate_ids=tuple(
                value["family_applicability_candidate_ids"]
            ),
            family_applicability_failed_candidate_ids=tuple(
                value["family_applicability_failed_candidate_ids"]
            ),
            nexus_instruction_sha256s=tuple(value["nexus_instruction_sha256s"]),
            risk_applicability_candidate_ids=tuple(
                value["risk_applicability_candidate_ids"]
            ),
            factreasoner_batch_sha256s=tuple(
                value["factreasoner_batch_sha256s"]
            ),
            pipeline_result_sha256=value["pipeline_result_sha256"],
            content_factreasoner_sha256=value["content_factreasoner_sha256"],
            publication_original_factreasoner_sha256=value[
                "publication_original_factreasoner_sha256"
            ],
            final_factreasoner_sha256=value["final_factreasoner_sha256"],
            risk_mapping_report_sha256=value["risk_mapping_report_sha256"],
            ledger_sha256=value["ledger_sha256"],
            ledger_event_count=value["ledger_event_count"],
            executions=tuple(
                ProviderExecutionBinding.from_dict(item)
                for item in value["executions"]
            ),
            failed_executions=tuple(
                ProviderFailedExecutionBinding.from_dict(item)
                for item in value["failed_executions"]
            ),
        )
        if result.manifest_sha256 != value["manifest_sha256"]:
            raise ProviderExecutionError("provider execution manifest digest is inconsistent")
        return result

    def verify_run(
        self,
        run_directory: str | os.PathLike[str],
    ) -> dict[str, Mapping[str, Any]]:
        """Verify the exact ledger and every completed normalized sidecar."""

        root = Path(run_directory)
        ledger = root / "usage.jsonl"
        decisions = root / "provider-decisions"
        if root.is_symlink() or ledger.is_symlink() or decisions.is_symlink():
            raise ProviderExecutionError("provider execution run paths are unsafe")
        if not root.is_dir() or not ledger.is_file() or not decisions.is_dir():
            raise ProviderExecutionError("provider execution run is incomplete")
        raw = ledger.read_bytes()
        if (
            hashlib.sha256(raw).hexdigest() != self.ledger_sha256
            or sum(1 for line in raw.splitlines() if line.strip())
            != self.ledger_event_count
        ):
            raise ProviderExecutionError("provider execution ledger has changed")
        completed_attempts, failed_executions = _ledger_inventory(ledger)
        completed_by_key = {
            (item.logical_call_id, item.attempt_id): item.to_dict()
            for item in completed_attempts
        }
        execution_by_key = {
            (item.logical_call_id, item.attempt_id): item.attempt_binding.to_dict()
            for item in self.executions
        }
        if completed_by_key != execution_by_key or tuple(
            item.to_dict() for item in failed_executions
        ) != tuple(item.to_dict() for item in self.failed_executions):
            raise ProviderExecutionError(
                "provider execution attempt inventory has changed"
            )
        actual_names: list[str] = []
        for entry in decisions.iterdir():
            if entry.is_symlink() or not entry.is_file() or entry.suffix != ".json":
                raise ProviderExecutionError("provider decision directory is unsafe")
            actual_names.append(entry.name)
        expected_names = [item.decision_name for item in self.executions]
        if sorted(actual_names) != sorted(expected_names):
            raise ProviderExecutionError("provider execution decision inventory has changed")
        output: dict[str, Mapping[str, Any]] = {}
        for execution in self.executions:
            try:
                decision = verify_provider_execution(
                    execution,
                    ledger_path=ledger,
                    decision_dir=decisions,
                )
            except ProviderError as exc:
                raise ProviderExecutionError(
                    "provider execution receipt could not be replayed"
                ) from exc
            output[execution.binding_sha256] = decision
        for failure in self.failed_executions:
            failure.verify(ledger)
        return output


@dataclass(frozen=True)
class ProviderExecutionRunEvidence:
    """Runtime-only handle for one immutable provider-assisted run.

    ``root`` never enters a serialized artifact.  The semantic identity is the
    execution manifest plus the downstream pipeline result it binds.
    """

    root: Path = field(repr=False, compare=False)
    manifest: ProviderExecutionManifest
    pipeline_result: PipelineResult
    evidence_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        root = Path(self.root)
        if root.is_symlink() or not root.is_dir():
            raise ProviderExecutionError("provider execution run root is unsafe")
        try:
            root = root.resolve(strict=True)
        except OSError as exc:
            raise ProviderExecutionError("provider execution run root is unavailable") from exc
        if not isinstance(self.manifest, ProviderExecutionManifest) or not isinstance(
            self.pipeline_result, PipelineResult
        ):
            raise ProviderExecutionError("provider execution run records are invalid")
        pipeline = self.pipeline_result
        manifest = self.manifest
        if (
            manifest.target != pipeline.target
            or manifest.source_catalog_sha256 != pipeline.source_catalog_sha256
            or manifest.pipeline_result_sha256 != pipeline.result_sha256
            or manifest.content_factreasoner_sha256
            != pipeline.content_factreasoner_sha256
            or manifest.publication_original_factreasoner_sha256
            != pipeline.publication_original_factreasoner_sha256
            or manifest.final_factreasoner_sha256 != pipeline.factreasoner_sha256
            or manifest.risk_mapping_report_sha256
            != pipeline.risk.mapping_report_sha256
        ):
            raise ProviderExecutionError(
                "provider execution manifest is stale for its pipeline result"
            )
        object.__setattr__(self, "root", root)
        self.verify()
        object.__setattr__(
            self,
            "evidence_sha256",
            _digest(
                {
                    "manifest_sha256": manifest.manifest_sha256,
                    "pipeline_result_sha256": pipeline.result_sha256,
                }
            ),
        )

    @classmethod
    def load(
        cls, run_directory: str | os.PathLike[str]
    ) -> "ProviderExecutionRunEvidence":
        root = Path(run_directory)
        try:
            manifest = ProviderExecutionManifest.from_dict(
                _read_canonical_json(root / PROVIDER_EXECUTION_MANIFEST_FILENAME)
            )
            pipeline = PipelineResult.from_dict(
                _read_canonical_json(root / "pipeline-result.json")
            )
        except ProviderExecutionError:
            raise
        except Exception as exc:
            raise ProviderExecutionError(
                "provider execution run records could not be loaded"
            ) from exc
        return cls(root=root, manifest=manifest, pipeline_result=pipeline)

    def verify(self) -> dict[str, Mapping[str, Any]]:
        """Re-read all bound records and verify every retained execution."""

        try:
            current_manifest = ProviderExecutionManifest.from_dict(
                _read_canonical_json(
                    self.root / PROVIDER_EXECUTION_MANIFEST_FILENAME
                )
            )
            current_pipeline = PipelineResult.from_dict(
                _read_canonical_json(self.root / "pipeline-result.json")
            )
        except ProviderExecutionError:
            raise
        except Exception as exc:
            raise ProviderExecutionError(
                "provider execution run records changed"
            ) from exc
        if (
            current_manifest.to_dict() != self.manifest.to_dict()
            or current_pipeline.to_dict() != self.pipeline_result.to_dict()
        ):
            raise ProviderExecutionError("provider execution run records changed")
        return self.manifest.verify_run(self.root)

    def state_snapshot(self) -> tuple[tuple[str, str], ...]:
        """Return hashes of paid-call state for a before/after replay assertion."""

        names = ("usage.jsonl",) + tuple(
            f"provider-decisions/{item.decision_name}"
            for item in self.manifest.executions
        )
        values: list[tuple[str, str]] = []
        for name in names:
            path = self.root.joinpath(*name.split("/"))
            if path.is_symlink() or not path.is_file():
                raise ProviderExecutionError("provider execution state is incomplete")
            values.append((name, hashlib.sha256(path.read_bytes()).hexdigest()))
        return tuple(values)


def _read_canonical_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ProviderExecutionError("provider execution record is missing or unsafe")

    def reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ProviderExecutionError("provider execution JSON has duplicate keys")
            value[key] = item
        return value

    def reject_nonfinite(value: str) -> None:
        raise ProviderExecutionError(
            f"provider execution JSON contains non-finite value {value!r}"
        )

    try:
        raw = path.read_bytes()
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate,
            parse_constant=reject_nonfinite,
        )
    except ProviderExecutionError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderExecutionError("provider execution record is malformed") from exc
    if raw != _canonical(value):
        raise ProviderExecutionError("provider execution record is not canonical JSON")
    return value


__all__ = [
    "PROVIDER_EXECUTION_MANIFEST_FILENAME",
    "PROVIDER_EXECUTION_MANIFEST_VERSION",
    "ProviderExecutionCollector",
    "ProviderExecutionError",
    "ProviderFailedExecutionBinding",
    "ProviderExecutionManifest",
    "ProviderExecutionRunEvidence",
]
