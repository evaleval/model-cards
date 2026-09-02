"""Crash-safe accounting journal for bounded paid structured calls.

The journal is a single locked, fsynced, append-only JSONL file.  It stores
identities, hashes, route bounds, reservations, and normalized receipts, but it
cannot store prompts, request/response bodies, credentials, or provider traces.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from types import MappingProxyType
from typing import Any, Callable, Iterator, Mapping, Sequence


LEDGER_VERSION = "openrouter-usage-ledger/v1"
SIDECAR_VERSION = "normalized-decision-sidecar/v1"
EXACT_MODEL = "deepseek/deepseek-v4-flash-0731"
GLOBAL_USD_CAP = Decimal("25")
GLOBAL_PAID_CALL_CAP = 300
MAX_RETRIES = 2
MAX_CONTEXT_METADATA_BYTES = 4096
MAX_ROUTE_AGE_SECONDS = 60

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,191}$")
_PROVIDER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._:/+()-]{0,127}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_EVENT_ID_RE = re.compile(r"^ledger_event_[0-9a-f]{32}$")
_RESERVATION_ID_RE = re.compile(r"^reservation_[0-9a-f]{24}$")
_REASON_RE = re.compile(r"^[a-z][a-z0-9._-]{0,63}$")
_BANNED_METADATA_KEYS = (
    "prompt",
    "response",
    "request_body",
    "content",
    "credential",
    "secret",
    "api_key",
    "token",
    "trace",
    "source_text",
    "evidence_text",
)
_REQUIRED_ROUTE_PARAMETERS = frozenset(
    {
        "max_tokens",
        "reasoning",
        "response_format",
        "structured_outputs",
        "temperature",
    }
)
_TERMINAL_OUTCOMES = frozenset(
    {
        "completed",
        "retryable_http_error",
        "terminal_http_error",
        "invalid_response",
        "uncertain_send",
        "cost_over_reservation",
    }
)


class LedgerError(RuntimeError):
    pass


class LedgerIntegrityError(LedgerError):
    pass


class LedgerConflictError(LedgerError):
    pass


class BudgetCapError(LedgerError):
    pass


class UncertainSendError(LedgerConflictError):
    pass


Clock = Callable[[], datetime]
DecisionValidator = Callable[[Mapping[str, Any]], None]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class RouteSnapshot:
    model: str
    provider: str
    checked_at: str
    prompt_price_per_token_usd: str
    completion_price_per_token_usd: str
    context_length: int
    max_completion_tokens: int
    supported_parameters: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.model != EXACT_MODEL:
            raise LedgerIntegrityError("route model is not the exact pinned model")
        _validate_provider(self.provider)
        _parse_timestamp(self.checked_at)
        _money(self.prompt_price_per_token_usd, "route prompt price")
        _money(self.completion_price_per_token_usd, "route completion price")
        for name, value in (
            ("context_length", self.context_length),
            ("max_completion_tokens", self.max_completion_tokens),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise LedgerIntegrityError(f"route {name} must be a positive integer")
        parameters = tuple(self.supported_parameters)
        if parameters != tuple(sorted(set(parameters))) or not all(
            isinstance(item, str) and item for item in parameters
        ):
            raise LedgerIntegrityError("route parameters must be sorted unique strings")
        if not _REQUIRED_ROUTE_PARAMETERS.issubset(parameters):
            raise LedgerIntegrityError("route lacks required structured-output parameters")
        object.__setattr__(self, "supported_parameters", parameters)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "provider": self.provider,
            "checked_at": self.checked_at,
            "prompt_price_per_token_usd": self.prompt_price_per_token_usd,
            "completion_price_per_token_usd": self.completion_price_per_token_usd,
            "context_length": self.context_length,
            "max_completion_tokens": self.max_completion_tokens,
            "supported_parameters": list(self.supported_parameters),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "RouteSnapshot":
        item = _strict_object(
            value,
            {
                "model",
                "provider",
                "checked_at",
                "prompt_price_per_token_usd",
                "completion_price_per_token_usd",
                "context_length",
                "max_completion_tokens",
                "supported_parameters",
            },
            "route snapshot",
        )
        if not isinstance(item["supported_parameters"], list):
            raise LedgerIntegrityError("route parameters must be a list")
        return cls(
            model=item["model"],
            provider=item["provider"],
            checked_at=item["checked_at"],
            prompt_price_per_token_usd=item["prompt_price_per_token_usd"],
            completion_price_per_token_usd=item["completion_price_per_token_usd"],
            context_length=item["context_length"],
            max_completion_tokens=item["max_completion_tokens"],
            supported_parameters=tuple(item["supported_parameters"]),
        )


@dataclass(frozen=True)
class UsageReceipt:
    http_status: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    charged_usd: str | None
    latency_ms: int
    returned_model: str | None
    returned_provider: str | None

    def __post_init__(self) -> None:
        if self.http_status is not None and (
            isinstance(self.http_status, bool)
            or not isinstance(self.http_status, int)
            or not 100 <= self.http_status <= 599
        ):
            raise LedgerIntegrityError("receipt HTTP status is invalid")
        tokens = (self.prompt_tokens, self.completion_tokens, self.total_tokens)
        for value in tokens:
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise LedgerIntegrityError("receipt token count is invalid")
        if all(value is not None for value in tokens):
            if self.prompt_tokens + self.completion_tokens != self.total_tokens:
                raise LedgerIntegrityError("receipt token counts do not add up")
        elif any(value is not None for value in tokens):
            raise LedgerIntegrityError("receipt token counts must be all present or all absent")
        if self.charged_usd is not None:
            _money(self.charged_usd, "receipt charge")
        if (
            isinstance(self.latency_ms, bool)
            or not isinstance(self.latency_ms, int)
            or self.latency_ms < 0
            or self.latency_ms > 86_400_000
        ):
            raise LedgerIntegrityError("receipt latency is invalid")
        for name, value in (
            ("returned_model", self.returned_model),
            ("returned_provider", self.returned_provider),
        ):
            if value is not None and (
                not isinstance(value, str) or not value or len(value) > 256 or not _portable(value)
            ):
                raise LedgerIntegrityError(f"receipt {name} is invalid")

    def to_dict(self) -> dict[str, Any]:
        return {
            "http_status": self.http_status,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "charged_usd": self.charged_usd,
            "latency_ms": self.latency_ms,
            "returned_model": self.returned_model,
            "returned_provider": self.returned_provider,
        }

    @classmethod
    def from_dict(cls, value: Any) -> "UsageReceipt":
        item = _strict_object(
            value,
            {
                "http_status",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "charged_usd",
                "latency_ms",
                "returned_model",
                "returned_provider",
            },
            "usage receipt",
        )
        return cls(**item)


@dataclass(frozen=True)
class AttemptBinding:
    logical_call_id: str
    attempt_id: str
    model: str
    provider: str
    request_sha256: str
    schema_sha256: str
    sidecar_path_sha256: str
    context_metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        _validate_id(self.logical_call_id, "logical_call_id")
        _validate_id(self.attempt_id, "attempt_id")
        if self.model != EXACT_MODEL:
            raise LedgerIntegrityError("attempt model is not the exact pinned model")
        _validate_provider(self.provider)
        for name, value in (
            ("request_sha256", self.request_sha256),
            ("schema_sha256", self.schema_sha256),
            ("sidecar_path_sha256", self.sidecar_path_sha256),
        ):
            if not isinstance(value, str) or not _DIGEST_RE.fullmatch(value):
                raise LedgerIntegrityError(f"attempt {name} is invalid")
        metadata = _validate_context_metadata(self.context_metadata)
        object.__setattr__(self, "context_metadata", MappingProxyType(dict(metadata)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "logical_call_id": self.logical_call_id,
            "attempt_id": self.attempt_id,
            "model": self.model,
            "provider": self.provider,
            "request_sha256": self.request_sha256,
            "schema_sha256": self.schema_sha256,
            "sidecar_path_sha256": self.sidecar_path_sha256,
            "context_metadata": dict(self.context_metadata),
        }

    @classmethod
    def from_dict(cls, value: Any) -> "AttemptBinding":
        item = _strict_object(
            value,
            {
                "logical_call_id",
                "attempt_id",
                "model",
                "provider",
                "request_sha256",
                "schema_sha256",
                "sidecar_path_sha256",
                "context_metadata",
            },
            "attempt binding",
        )
        return cls(**item)


@dataclass(frozen=True)
class ReservationToken:
    reservation_id: str
    binding: AttemptBinding
    retry_index: int
    reserved_usd: str
    input_token_ceiling: int
    output_token_ceiling: int
    route: RouteSnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.reservation_id, str) or not _RESERVATION_ID_RE.fullmatch(
            self.reservation_id
        ):
            raise LedgerIntegrityError("reservation id is invalid")
        if not isinstance(self.binding, AttemptBinding):
            raise LedgerIntegrityError("reservation binding is invalid")
        if (
            isinstance(self.retry_index, bool)
            or not isinstance(self.retry_index, int)
            or not 0 <= self.retry_index <= MAX_RETRIES
        ):
            raise LedgerIntegrityError("reservation retry index is invalid")
        reserved = _money(self.reserved_usd, "reservation amount")
        for name, value in (
            ("input_token_ceiling", self.input_token_ceiling),
            ("output_token_ceiling", self.output_token_ceiling),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise LedgerIntegrityError(f"reservation {name} is invalid")
        if not isinstance(self.route, RouteSnapshot):
            raise LedgerIntegrityError("reservation route is invalid")
        expected = (
            Decimal(self.input_token_ceiling)
            * _money(self.route.prompt_price_per_token_usd, "route prompt price")
            + Decimal(self.output_token_ceiling)
            * _money(self.route.completion_price_per_token_usd, "route completion price")
        )
        if reserved != expected:
            raise LedgerIntegrityError("reservation is not bound to route prices and tokens")

    def to_dict(self) -> dict[str, Any]:
        return {
            "reservation_id": self.reservation_id,
            "binding": self.binding.to_dict(),
            "retry_index": self.retry_index,
            "reserved_usd": self.reserved_usd,
            "input_token_ceiling": self.input_token_ceiling,
            "output_token_ceiling": self.output_token_ceiling,
            "route": self.route.to_dict(),
        }


@dataclass(frozen=True)
class AttemptSnapshot:
    binding: AttemptBinding
    status: str
    reservations: tuple[ReservationToken, ...]
    terminal_events: tuple[Mapping[str, Any], ...]

    @property
    def latest_reservation(self) -> ReservationToken | None:
        return self.reservations[-1] if self.reservations else None

    @property
    def latest_terminal(self) -> Mapping[str, Any] | None:
        return self.terminal_events[-1] if self.terminal_events else None


class UsageLedger:
    def __init__(self, path: str | os.PathLike[str], *, clock: Clock = utc_now) -> None:
        self.path = Path(path)
        self.clock = clock

    def inspect(self, binding: AttemptBinding) -> AttemptSnapshot | None:
        with _locked_file(self.path) as handle:
            state = _replay(_read_events(handle))
        attempt = state["attempts"].get(_attempt_key(binding))
        if attempt is None:
            return None
        _assert_binding(attempt["binding"], binding)
        return _snapshot(attempt)

    def begin_attempt(self, binding: AttemptBinding) -> AttemptSnapshot:
        with _locked_file(self.path) as handle:
            state = _replay(_read_events(handle))
            key = _attempt_key(binding)
            existing = state["attempts"].get(key)
            if existing is not None:
                _assert_binding(existing["binding"], binding)
                return _snapshot(existing)
            for attempt in state["attempts"].values():
                prior = attempt["binding"]
                if prior.attempt_id == binding.attempt_id:
                    raise LedgerConflictError("attempt_id is already used by another binding")
                if (
                    prior.request_sha256 == binding.request_sha256
                    and prior.logical_call_id != binding.logical_call_id
                ):
                    raise LedgerConflictError(
                        "request hash is already bound to another logical call"
                    )
                if prior.logical_call_id == binding.logical_call_id:
                    if prior.request_sha256 != binding.request_sha256:
                        raise LedgerConflictError(
                            "logical call is already bound to another request hash"
                        )
                    prior_snapshot = _snapshot(attempt)
                    if prior_snapshot.status == "completed":
                        raise LedgerConflictError(
                            "logical call already completed under an earlier attempt"
                        )
                    if prior_snapshot.status in {"pending", "uncertain"}:
                        raise UncertainSendError(
                            "earlier attempt has a potentially paid uncertain send"
                        )
            _append_event(handle, "attempt_manifest", binding.to_dict(), self.clock)
            state = _replay(_read_events(handle))
            return _snapshot(state["attempts"][key])

    def reserve(
        self,
        binding: AttemptBinding,
        *,
        retry_index: int,
        route: RouteSnapshot,
        input_token_ceiling: int,
        output_token_ceiling: int,
    ) -> ReservationToken:
        with _locked_file(self.path) as handle:
            state = _replay(_read_events(handle))
            if state["global_halt"]:
                raise BudgetCapError("global halt is active after reservation overrun")
            attempt = state["attempts"].get(_attempt_key(binding))
            if attempt is None:
                raise LedgerConflictError("attempt manifest must precede reservation")
            _assert_binding(attempt["binding"], binding)
            snapshot = _snapshot(attempt)
            if snapshot.status in {"completed", "failed", "uncertain", "pending"}:
                if snapshot.status in {"uncertain", "pending"}:
                    raise UncertainSendError("attempt has an unresolved reservation")
                raise LedgerConflictError("attempt is already terminal")
            expected_retry = len(snapshot.reservations)
            if retry_index != expected_retry or not 0 <= retry_index <= MAX_RETRIES:
                raise LedgerConflictError("retry reservation index is not contiguous")
            if retry_index > 0:
                prior = snapshot.latest_terminal
                if prior is None or prior["payload"]["outcome"] != "retryable_http_error":
                    raise LedgerConflictError("retry requires an explicitly retryable response")
            now = _aware_now(self.clock)
            _validate_fresh_route(route, binding, now)
            if input_token_ceiling + output_token_ceiling > route.context_length:
                raise LedgerConflictError("token ceilings exceed the live route context")
            if output_token_ceiling > route.max_completion_tokens:
                raise LedgerConflictError("output ceiling exceeds the live route capability")
            reservation = (
                Decimal(input_token_ceiling)
                * _money(route.prompt_price_per_token_usd, "route prompt price")
                + Decimal(output_token_ceiling)
                * _money(route.completion_price_per_token_usd, "route completion price")
            )
            if state["paid_calls"] + 1 > GLOBAL_PAID_CALL_CAP:
                raise BudgetCapError("global paid-call cap would be exceeded")
            if state["committed_usd"] + reservation > GLOBAL_USD_CAP:
                raise BudgetCapError("global USD cap would be exceeded")
            reservation_id = "reservation_" + hashlib.sha256(
                _canonical_bytes(
                    {
                        "binding": binding.to_dict(),
                        "retry_index": retry_index,
                        "route": route.to_dict(),
                        "input_token_ceiling": input_token_ceiling,
                        "output_token_ceiling": output_token_ceiling,
                        "sequence": state["event_count"] + 1,
                    }
                )
            ).hexdigest()[:24]
            token = ReservationToken(
                reservation_id=reservation_id,
                binding=binding,
                retry_index=retry_index,
                reserved_usd=_money_text(reservation),
                input_token_ceiling=input_token_ceiling,
                output_token_ceiling=output_token_ceiling,
                route=route,
            )
            _append_event(handle, "reservation", token.to_dict(), self.clock)
            return token

    def record_terminal(
        self,
        token: ReservationToken,
        *,
        outcome: str,
        receipt: UsageReceipt,
        reason_code: str,
        decision_sha256: str | None = None,
        sidecar_sha256: str | None = None,
    ) -> None:
        if outcome not in _TERMINAL_OUTCOMES:
            raise LedgerConflictError("terminal outcome is invalid")
        if not isinstance(reason_code, str) or not _REASON_RE.fullmatch(reason_code):
            raise LedgerConflictError("terminal reason code is invalid")
        for name, value in (
            ("decision_sha256", decision_sha256),
            ("sidecar_sha256", sidecar_sha256),
        ):
            if value is not None and (
                not isinstance(value, str) or not _DIGEST_RE.fullmatch(value)
            ):
                raise LedgerConflictError(f"terminal {name} is invalid")
        _validate_terminal_semantics(
            token,
            outcome=outcome,
            receipt=receipt,
            decision_sha256=decision_sha256,
            sidecar_sha256=sidecar_sha256,
        )
        payload = {
            "reservation_id": token.reservation_id,
            "outcome": outcome,
            "reason_code": reason_code,
            "receipt": receipt.to_dict(),
            "decision_sha256": decision_sha256,
            "sidecar_sha256": sidecar_sha256,
        }
        with _locked_file(self.path) as handle:
            state = _replay(_read_events(handle))
            attempt = state["attempts"].get(_attempt_key(token.binding))
            if attempt is None:
                raise LedgerConflictError("terminal event references an unknown attempt")
            _assert_binding(attempt["binding"], token.binding)
            stored = attempt["reservations_by_id"].get(token.reservation_id)
            if stored is None or stored.to_dict() != token.to_dict():
                raise LedgerConflictError("terminal event references another reservation")
            if token.reservation_id in attempt["terminals_by_reservation"]:
                raise LedgerConflictError("reservation already has a terminal event")
            _append_event(handle, "reservation_terminal", payload, self.clock)

    def audit_state(self) -> Mapping[str, Any]:
        with _locked_file(self.path) as handle:
            state = _replay(_read_events(handle))
        return {
            "paid_calls": state["paid_calls"],
            "committed_usd": _money_text(state["committed_usd"]),
            "global_halt": state["global_halt"],
            "attempt_count": len(state["attempts"]),
            "event_count": state["event_count"],
        }

    def audit_metrics(self) -> Mapping[str, Any]:
        """Return a privacy-safe aggregate of every validated ledger receipt."""

        with _locked_file(self.path) as handle:
            state = _replay(_read_events(handle))
        prompt_tokens = completion_tokens = total_tokens = 0
        latency_ms = 0
        max_latency_ms = 0
        receipt_count = 0
        token_receipt_count = 0
        retry_count = 0
        providers: set[str] = set()
        outcomes: dict[str, int] = {}
        statuses: dict[str, int] = {}
        for attempt in state["attempts"].values():
            snapshot = _snapshot(attempt)
            statuses[snapshot.status] = statuses.get(snapshot.status, 0) + 1
            providers.add(snapshot.binding.provider)
            retry_count += max(0, len(snapshot.reservations) - 1)
            for event in snapshot.terminal_events:
                terminal = _terminal_from_dict(event["payload"])
                outcome = terminal["outcome"]
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                receipt = terminal["receipt"]
                receipt_count += 1
                latency_ms += receipt.latency_ms
                max_latency_ms = max(max_latency_ms, receipt.latency_ms)
                if receipt.total_tokens is not None:
                    token_receipt_count += 1
                    prompt_tokens += receipt.prompt_tokens or 0
                    completion_tokens += receipt.completion_tokens or 0
                    total_tokens += receipt.total_tokens
        return {
            "paid_calls": state["paid_calls"],
            "committed_usd": _money_text(state["committed_usd"]),
            "global_halt": state["global_halt"],
            "attempt_count": len(state["attempts"]),
            "receipt_count": receipt_count,
            "token_receipt_count": token_receipt_count,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "retry_count": retry_count,
            "latency_ms": latency_ms,
            "max_latency_ms": max_latency_ms,
            "providers": sorted(providers),
            "attempt_statuses": {
                key: statuses[key] for key in sorted(statuses)
            },
            "terminal_outcomes": {
                key: outcomes[key] for key in sorted(outcomes)
            },
        }


def write_decision_sidecar(
    path: str | os.PathLike[str],
    *,
    token: ReservationToken,
    decision: Mapping[str, Any],
    receipt: UsageReceipt,
) -> tuple[str, str]:
    normalized = _json_object(decision, "normalized decision")
    decision_sha = hashlib.sha256(_canonical_bytes(normalized)).hexdigest()
    payload = {
        "sidecar_version": SIDECAR_VERSION,
        "logical_call_id": token.binding.logical_call_id,
        "attempt_id": token.binding.attempt_id,
        "model": token.binding.model,
        "provider": token.binding.provider,
        "request_sha256": token.binding.request_sha256,
        "schema_sha256": token.binding.schema_sha256,
        "reservation_id": token.reservation_id,
        "decision_sha256": decision_sha,
        "decision": normalized,
        "receipt": receipt.to_dict(),
    }
    encoded = _canonical_bytes(payload)
    destination = Path(path)
    if destination.exists() or destination.is_symlink():
        raise LedgerConflictError("normalized decision sidecar already exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.tmp-", dir=str(destination.parent)
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise LedgerConflictError("normalized decision sidecar already exists") from exc
        linked = True
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        if not linked and destination.exists():
            # Only unlink when this invocation linked it but failed before durable return.
            pass
    return decision_sha, hashlib.sha256(encoded).hexdigest()


def read_decision_sidecar(
    path: str | os.PathLike[str],
    *,
    binding: AttemptBinding,
    validator: DecisionValidator,
) -> tuple[dict[str, Any], UsageReceipt, str, str, str]:
    source = Path(path)
    if source.is_symlink() or not source.is_file() or not stat.S_ISREG(source.stat().st_mode):
        raise LedgerConflictError("normalized decision sidecar is missing or unsafe")
    encoded = source.read_bytes()
    value = _load_canonical_json(encoded, "normalized decision sidecar")
    item = _strict_object(
        value,
        {
            "sidecar_version",
            "logical_call_id",
            "attempt_id",
            "model",
            "provider",
            "request_sha256",
            "schema_sha256",
            "reservation_id",
            "decision_sha256",
            "decision",
            "receipt",
        },
        "normalized decision sidecar",
    )
    expected = {
        "sidecar_version": SIDECAR_VERSION,
        "logical_call_id": binding.logical_call_id,
        "attempt_id": binding.attempt_id,
        "model": binding.model,
        "provider": binding.provider,
        "request_sha256": binding.request_sha256,
        "schema_sha256": binding.schema_sha256,
    }
    if any(item.get(key) != expected_value for key, expected_value in expected.items()):
        raise LedgerConflictError("normalized decision sidecar binding is inconsistent")
    if not isinstance(item["reservation_id"], str) or not _RESERVATION_ID_RE.fullmatch(
        item["reservation_id"]
    ):
        raise LedgerConflictError("normalized decision sidecar reservation is invalid")
    decision = _json_object(item["decision"], "normalized decision")
    decision_sha = hashlib.sha256(_canonical_bytes(decision)).hexdigest()
    if item["decision_sha256"] != decision_sha:
        raise LedgerConflictError("normalized decision sidecar was tampered")
    validation_failed = False
    try:
        validator(decision)
    except Exception:
        validation_failed = True
    if validation_failed:
        raise LedgerConflictError(
            "normalized decision no longer passes validation"
        )
    receipt = UsageReceipt.from_dict(item["receipt"])
    return (
        decision,
        receipt,
        item["reservation_id"],
        decision_sha,
        hashlib.sha256(encoded).hexdigest(),
    )


def path_sha256(path: str | os.PathLike[str]) -> str:
    return hashlib.sha256(str(Path(path).resolve()).encode("utf-8")).hexdigest()


def json_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _snapshot(attempt: Mapping[str, Any]) -> AttemptSnapshot:
    reservations = tuple(attempt["reservations"])
    terminals = tuple(attempt["terminals"])
    if not reservations:
        status = "manifested"
    else:
        latest = terminals[-1] if terminals else None
        if len(terminals) < len(reservations):
            status = "pending"
        else:
            outcome = latest["payload"]["outcome"]
            if outcome == "completed":
                status = "completed"
            elif (
                outcome == "retryable_http_error"
                and latest["payload"]["reason_code"] == "http_retryable"
                and len(reservations) <= MAX_RETRIES
            ):
                status = "ready_to_retry"
            elif outcome == "uncertain_send":
                status = "uncertain"
            else:
                status = "failed"
    return AttemptSnapshot(
        binding=attempt["binding"],
        status=status,
        reservations=reservations,
        terminal_events=terminals,
    )


def _validate_terminal_semantics(
    token: ReservationToken,
    *,
    outcome: str,
    receipt: UsageReceipt,
    decision_sha256: str | None,
    sidecar_sha256: str | None,
) -> None:
    reserved = _money(token.reserved_usd, "reservation amount")
    charged = (
        _money(receipt.charged_usd, "receipt charge")
        if receipt.charged_usd is not None
        else None
    )
    if outcome == "completed":
        if (
            receipt.http_status != 200
            or charged is None
            or charged > reserved
            or receipt.returned_model != token.binding.model
            or receipt.returned_provider != token.binding.provider
            or decision_sha256 is None
            or sidecar_sha256 is None
        ):
            raise LedgerConflictError("completed reservation receipt is invalid")
    elif outcome == "retryable_http_error":
        if (
            receipt.http_status != 429
            and (receipt.http_status is None or not 500 <= receipt.http_status <= 599)
        ):
            raise LedgerConflictError("retryable outcome requires HTTP 429 or 5xx")
        if decision_sha256 is not None or sidecar_sha256 is not None:
            raise LedgerConflictError("retryable response cannot have a decision sidecar")
    elif outcome == "uncertain_send":
        if charged is not None or receipt.http_status is not None:
            raise LedgerConflictError("uncertain send cannot claim a known charge or status")
        if decision_sha256 is not None or sidecar_sha256 is not None:
            raise LedgerConflictError("uncertain send cannot claim a decision")
    elif outcome == "cost_over_reservation":
        if (
            charged is None
            or charged <= reserved
            or decision_sha256 is not None
            or sidecar_sha256 is not None
        ):
            raise LedgerConflictError("reservation overrun must exceed reserved USD")
    else:
        if decision_sha256 is not None or sidecar_sha256 is not None:
            raise LedgerConflictError("failed reservation cannot have a decision sidecar")
    if outcome != "uncertain_send" and charged is None:
        raise LedgerConflictError("known provider response must report a charge")
    if (
        charged is not None
        and charged > reserved
        and outcome != "cost_over_reservation"
    ):
        raise LedgerConflictError("charge over reservation must trigger the global halt outcome")


def _replay(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    attempts: dict[tuple[str, str], dict[str, Any]] = {}
    request_logical: dict[str, str] = {}
    event_ids: set[str] = set()
    paid_calls = 0
    committed = Decimal("0")
    global_halt = False
    for expected_sequence, event in enumerate(events, 1):
        _validate_event(event, expected_sequence)
        if event["event_id"] in event_ids:
            raise LedgerIntegrityError("usage ledger contains duplicate event ids")
        event_ids.add(event["event_id"])
        event_type = event["event"]
        payload = event["payload"]
        if event_type == "attempt_manifest":
            binding = AttemptBinding.from_dict(payload)
            key = _attempt_key(binding)
            if key in attempts:
                raise LedgerIntegrityError("usage ledger repeats an attempt manifest")
            if any(item["binding"].attempt_id == binding.attempt_id for item in attempts.values()):
                raise LedgerIntegrityError("usage ledger reuses an attempt id")
            prior_logical = request_logical.setdefault(
                binding.request_sha256, binding.logical_call_id
            )
            if prior_logical != binding.logical_call_id:
                raise LedgerIntegrityError("request hash crosses logical call identities")
            for prior in attempts.values():
                if (
                    prior["binding"].logical_call_id == binding.logical_call_id
                    and prior["binding"].request_sha256 != binding.request_sha256
                ):
                    raise LedgerIntegrityError("logical call changes request hash")
            attempts[key] = {
                "binding": binding,
                "reservations": [],
                "reservations_by_id": {},
                "terminals": [],
                "terminals_by_reservation": {},
            }
        elif event_type == "reservation":
            token = _reservation_from_dict(payload)
            key = _attempt_key(token.binding)
            attempt = attempts.get(key)
            if attempt is None:
                raise LedgerIntegrityError("reservation precedes its attempt manifest")
            _assert_binding(attempt["binding"], token.binding)
            if token.reservation_id in attempt["reservations_by_id"]:
                raise LedgerIntegrityError("usage ledger repeats a reservation id")
            if token.retry_index != len(attempt["reservations"]):
                raise LedgerIntegrityError("usage ledger retry indexes are not contiguous")
            if token.retry_index > 0:
                previous = attempt["terminals"][-1] if attempt["terminals"] else None
                if previous is None or previous["payload"]["outcome"] != "retryable_http_error":
                    raise LedgerIntegrityError("usage ledger retry lacks retryable response")
            attempt["reservations"].append(token)
            attempt["reservations_by_id"][token.reservation_id] = token
            paid_calls += 1
            committed += _money(token.reserved_usd, "reservation amount")
        elif event_type == "reservation_terminal":
            item = _terminal_from_dict(payload)
            reservation_id = item["reservation_id"]
            owners = [
                attempt
                for attempt in attempts.values()
                if reservation_id in attempt["reservations_by_id"]
            ]
            if len(owners) != 1:
                raise LedgerIntegrityError("terminal references an unknown reservation")
            attempt = owners[0]
            if reservation_id in attempt["terminals_by_reservation"]:
                raise LedgerIntegrityError("reservation has duplicate terminal events")
            token = attempt["reservations_by_id"][reservation_id]
            _validate_terminal_semantics(
                token,
                outcome=item["outcome"],
                receipt=item["receipt"],
                decision_sha256=item["decision_sha256"],
                sidecar_sha256=item["sidecar_sha256"],
            )
            attempt["terminals"].append(event)
            attempt["terminals_by_reservation"][reservation_id] = event
            reserved = _money(token.reserved_usd, "reservation amount")
            if item["outcome"] == "uncertain_send":
                pass
            else:
                charged = _money(item["receipt"].charged_usd, "receipt charge")
                committed += charged - reserved
            if item["outcome"] == "cost_over_reservation":
                global_halt = True
        else:
            raise LedgerIntegrityError("usage ledger contains an unknown event type")
    if paid_calls > GLOBAL_PAID_CALL_CAP:
        raise LedgerIntegrityError("usage ledger exceeds the global paid-call cap")
    return {
        "attempts": attempts,
        "paid_calls": paid_calls,
        "committed_usd": committed,
        "global_halt": global_halt,
        "event_count": len(events),
    }


def _validate_event(event: Mapping[str, Any], expected_sequence: int) -> None:
    item = _strict_object(
        event,
        {"ledger_version", "event_id", "sequence", "event", "recorded_at", "payload"},
        "usage ledger event",
    )
    if item["ledger_version"] != LEDGER_VERSION:
        raise LedgerIntegrityError("usage ledger version is unsupported")
    if item["sequence"] != expected_sequence:
        raise LedgerIntegrityError("usage ledger sequence is truncated or reordered")
    if not isinstance(item["event_id"], str) or not _EVENT_ID_RE.fullmatch(item["event_id"]):
        raise LedgerIntegrityError("usage ledger event id is invalid")
    _parse_timestamp(item["recorded_at"])
    expected_id = _event_id(
        sequence=item["sequence"],
        event=item["event"],
        recorded_at=item["recorded_at"],
        payload=item["payload"],
    )
    if item["event_id"] != expected_id:
        raise LedgerIntegrityError("usage ledger event id does not match its content")


def _terminal_from_dict(value: Any) -> dict[str, Any]:
    item = _strict_object(
        value,
        {
            "reservation_id",
            "outcome",
            "reason_code",
            "receipt",
            "decision_sha256",
            "sidecar_sha256",
        },
        "reservation terminal",
    )
    if not isinstance(item["reservation_id"], str) or not _RESERVATION_ID_RE.fullmatch(
        item["reservation_id"]
    ):
        raise LedgerIntegrityError("terminal reservation id is invalid")
    if item["outcome"] not in _TERMINAL_OUTCOMES:
        raise LedgerIntegrityError("terminal outcome is invalid")
    if not isinstance(item["reason_code"], str) or not _REASON_RE.fullmatch(
        item["reason_code"]
    ):
        raise LedgerIntegrityError("terminal reason code is invalid")
    for name in ("decision_sha256", "sidecar_sha256"):
        value = item[name]
        if value is not None and (not isinstance(value, str) or not _DIGEST_RE.fullmatch(value)):
            raise LedgerIntegrityError(f"terminal {name} is invalid")
    item = dict(item)
    item["receipt"] = UsageReceipt.from_dict(item["receipt"])
    return item


def _reservation_from_dict(value: Any) -> ReservationToken:
    item = _strict_object(
        value,
        {
            "reservation_id",
            "binding",
            "retry_index",
            "reserved_usd",
            "input_token_ceiling",
            "output_token_ceiling",
            "route",
        },
        "reservation",
    )
    return ReservationToken(
        reservation_id=item["reservation_id"],
        binding=AttemptBinding.from_dict(item["binding"]),
        retry_index=item["retry_index"],
        reserved_usd=item["reserved_usd"],
        input_token_ceiling=item["input_token_ceiling"],
        output_token_ceiling=item["output_token_ceiling"],
        route=RouteSnapshot.from_dict(item["route"]),
    )


@contextmanager
def _locked_file(path: Path) -> Iterator[Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "r+b", buffering=0)
        descriptor = -1
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _read_events(handle: Any) -> list[dict[str, Any]]:
    handle.seek(0)
    raw = handle.read()
    if raw and not raw.endswith(b"\n"):
        raise LedgerIntegrityError("usage ledger is truncated")
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(raw.splitlines(), 1):
        parse_failed = False
        try:
            event = json.loads(
                line.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
                parse_constant=_reject_nonfinite,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, LedgerIntegrityError):
            parse_failed = True
        if parse_failed:
            raise LedgerIntegrityError(
                f"usage ledger line {line_number} is not strict JSON"
            )
        if line + b"\n" != _canonical_bytes(event):
            raise LedgerIntegrityError(f"usage ledger line {line_number} is non-canonical")
        events.append(event)
    return events


def _append_event(handle: Any, event: str, payload: Mapping[str, Any], clock: Clock) -> None:
    events = _read_events(handle)
    sequence = len(events) + 1
    recorded_at = _timestamp(clock)
    normalized_payload = _json_object(payload, "ledger event payload")
    row = {
        "ledger_version": LEDGER_VERSION,
        "event_id": _event_id(
            sequence=sequence,
            event=event,
            recorded_at=recorded_at,
            payload=normalized_payload,
        ),
        "sequence": sequence,
        "event": event,
        "recorded_at": recorded_at,
        "payload": normalized_payload,
    }
    handle.seek(0, os.SEEK_END)
    handle.write(_canonical_bytes(row))
    os.fsync(handle.fileno())


def _event_id(*, sequence: int, event: str, recorded_at: str, payload: Any) -> str:
    return "ledger_event_" + hashlib.sha256(
        _canonical_bytes(
            {
                "ledger_version": LEDGER_VERSION,
                "sequence": sequence,
                "event": event,
                "recorded_at": recorded_at,
                "payload": payload,
            }
        )
    ).hexdigest()[:32]


def _validate_context_metadata(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or len(value) > 24:
        raise LedgerIntegrityError("context metadata must be a bounded object")
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if (
            not isinstance(key, str)
            or not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", key)
            or any(token in key for token in _BANNED_METADATA_KEYS)
        ):
            raise LedgerIntegrityError("context metadata key is unsafe")
        if isinstance(item, bool) or item is None:
            normalized[key] = item
        elif isinstance(item, int) and not isinstance(item, bool) and abs(item) <= 10**15:
            normalized[key] = item
        elif isinstance(item, str) and len(item) <= 256 and _portable(item):
            if item.startswith(("/", "~")) or "\\" in item:
                raise LedgerIntegrityError("context metadata cannot contain local paths")
            normalized[key] = item
        else:
            raise LedgerIntegrityError("context metadata value is unsafe")
    if len(_canonical_bytes(normalized)) > MAX_CONTEXT_METADATA_BYTES:
        raise LedgerIntegrityError("context metadata exceeds its byte limit")
    return normalized


def _validate_fresh_route(
    route: RouteSnapshot, binding: AttemptBinding, now: datetime
) -> None:
    if route.model != binding.model or route.provider != binding.provider:
        raise LedgerConflictError("fresh route differs from the pinned attempt")
    checked = _parse_timestamp(route.checked_at)
    age = (now - checked).total_seconds()
    if age < -5 or age > MAX_ROUTE_AGE_SECONDS:
        raise LedgerConflictError("route check is stale")


def _attempt_key(binding: AttemptBinding) -> tuple[str, str]:
    return binding.logical_call_id, binding.attempt_id


def _assert_binding(stored: AttemptBinding, expected: AttemptBinding) -> None:
    if stored.to_dict() != expected.to_dict():
        raise LedgerConflictError("attempt identity is pinned to different inputs")


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        raise LedgerIntegrityError(f"{label} is invalid")


def _validate_provider(value: str) -> None:
    if not isinstance(value, str) or not _PROVIDER_RE.fullmatch(value):
        raise LedgerIntegrityError("provider is invalid")


def _money(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise LedgerIntegrityError(f"{label} must be an exact decimal")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise LedgerIntegrityError(f"{label} is invalid") from exc
    if not parsed.is_finite() or parsed < 0:
        raise LedgerIntegrityError(f"{label} must be finite and non-negative")
    return parsed


def _money_text(value: Decimal) -> str:
    return format(value, "f")


def _aware_now(clock: Clock) -> datetime:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise LedgerIntegrityError("clock must return a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _timestamp(clock: Clock) -> str:
    return _aware_now(clock).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise LedgerIntegrityError("timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LedgerIntegrityError("timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise LedgerIntegrityError("timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise LedgerIntegrityError(f"{label} must be a JSON object")
    json_failed = False
    try:
        encoded = _canonical_bytes(dict(value))
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError):
        json_failed = True
    if json_failed:
        raise LedgerIntegrityError(f"{label} must be finite JSON")
    if not isinstance(decoded, dict):
        raise LedgerIntegrityError(f"{label} must be a JSON object")
    return decoded


def _load_canonical_json(encoded: bytes, label: str) -> Any:
    parse_failed = False
    try:
        value = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, LedgerIntegrityError):
        parse_failed = True
    if parse_failed:
        raise LedgerIntegrityError(f"{label} is not strict JSON")
    if encoded != _canonical_bytes(value):
        raise LedgerIntegrityError(f"{label} is non-canonical")
    return value


def _canonical_bytes(value: Any) -> bytes:
    encoding_failed = False
    try:
        encoded = (
            json.dumps(
                value,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError):
        encoding_failed = True
    if encoding_failed:
        raise LedgerIntegrityError("value is not finite JSON")
    return encoded


def _strict_object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise LedgerIntegrityError(f"{label} is not a closed object")
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise LedgerIntegrityError("JSON object contains duplicate keys")
        value[key] = item
    return value


def _reject_nonfinite(value: str) -> None:
    raise LedgerIntegrityError(f"JSON contains non-finite value {value!r}")


def _portable(value: str) -> bool:
    return all(ord(character) >= 32 and ord(character) != 127 for character in value)


__all__ = [
    "AttemptBinding",
    "AttemptSnapshot",
    "BudgetCapError",
    "EXACT_MODEL",
    "GLOBAL_PAID_CALL_CAP",
    "GLOBAL_USD_CAP",
    "LEDGER_VERSION",
    "LedgerConflictError",
    "LedgerError",
    "LedgerIntegrityError",
    "MAX_RETRIES",
    "ReservationToken",
    "RouteSnapshot",
    "SIDECAR_VERSION",
    "UncertainSendError",
    "UsageLedger",
    "UsageReceipt",
    "json_sha256",
    "path_sha256",
    "read_decision_sidecar",
    "utc_now",
    "write_decision_sidecar",
]
