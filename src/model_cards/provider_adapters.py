"""Typed OpenRouter adapters for extraction and post-extraction gates.

All adapters use the one bounded runtime in :mod:`model_cards.provider`.  The
only provider-visible text is the public-source excerpt or frozen-source chunk
needed for the current decision.  Prompts and raw responses are never returned
or serialized by this module; normalized decisions are stored by the provider
runtime in the caller's private run directory.
"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable, Iterator, Mapping, Sequence

from jsonschema import Draft202012Validator

from .claim_gate import (
    ClaimCandidate,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
)
from .extraction import (
    ExtractionBatch,
    MAX_EXTRACTION_BATCH_PROPOSALS,
    MAX_PROVIDER_PROPOSALS,
    MAX_USE_RISK_PROVIDER_PROPOSALS,
    PUBLISHER_RISK_FIELD,
    PUBLISHER_RISK_PROPOSAL_FIELDS,
    ProviderProposalRejection,
    SourceWindow,
    build_source_windows,
    build_use_risk_windows,
    extraction_response_schema,
    normalize_provider_proposals,
    publisher_risk_proposal_schema,
    proposals_from_provider_value,
    use_risk_extraction_response_schema,
)
from .factreasoner import (
    CheckOutcome,
    CheckRequest,
    CheckerResponse,
    MAX_FACT_CHECKS_PER_BATCH,
    check_request_sha256,
)
from .models import SourceDocument, TargetIdentity
from .provider import (
    MODEL_ID,
    PINNED_PROVIDER,
    PROVIDER_RUNTIME_VERSION,
    REASONING_CONFIG,
    ProviderResponseError,
    ProviderTerminalAttemptError,
    ProviderTransport,
    StructuredCallSpec,
    structured_json_call,
)
from .risk_mapping import (
    ApplicabilityDecision,
    ApplicabilityStatus,
    RiskCandidate,
    UseContext,
)
from .run_ledger import (
    AttemptBinding,
    BudgetCapError,
    GLOBAL_PAID_CALL_CAP,
    GLOBAL_USD_CAP,
    MAX_RETRIES,
    UsageLedger,
    json_sha256,
    path_sha256,
)
from .schema import (
    CONTENT_FIELD_PATHS,
    CONTRACT_SCHEMA,
    LIST_FIELDS,
)


ADAPTER_VERSION = "model-card-openrouter-adapters/v17"
CLAIM_CHECKER_ID = "openrouter/deepseek-v4-flash-0731"
FACT_CHECKER_ID = "openrouter/deepseek-v4-flash-0731"
MAX_EXTRACTION_OUTPUT_TOKENS = 8192
MAX_CLAIM_OUTPUT_TOKENS = 1024
MAX_FACT_OUTPUT_TOKENS = 8192
MAX_RISK_OUTPUT_TOKENS = 1536
AGGREGATE_BUDGET_VERSION = "openrouter-aggregate-budget/v2"
AGGREGATE_BUDGET_SUMMARY_VERSION = (
    "openrouter-aggregate-budget-summary/v2"
)

_DESCRIPTION_ITEM_FIELDS = frozenset(
    {
        "use_and_risk.intended_uses",
        "use_and_risk.out_of_scope_uses",
        "use_and_risk.limitations",
        "use_and_risk.known_biases",
        "use_and_risk.mitigations",
    }
)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


class ProviderAdapterError(ValueError):
    """An adapter input or normalized provider decision is invalid."""


CallFunction = Callable[..., Any]


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise ProviderAdapterError("provider adapter values must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _closed(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ProviderAdapterError(f"{label} has an invalid closed shape")
    return value


def _extraction_value_contract() -> dict[str, Any]:
    """Build the decoded-value contract shown to the quote extractor."""

    fields: dict[str, Any] = {}
    for field_path in CONTENT_FIELD_PATHS:
        section, field = field_path.split(".", 1)
        section_ref = CONTRACT_SCHEMA["properties"][section]["$ref"]
        section_schema = CONTRACT_SCHEMA["$defs"][section_ref.rsplit("/", 1)[-1]]
        property_schema = section_schema["properties"][field]
        if field_path in LIST_FIELDS:
            array_schema = next(
                option
                for option in property_schema.get("anyOf", ())
                if option.get("type") == "array"
            )
            value_schema = array_schema["items"]
        else:
            value_schema = property_schema
        if field_path in _DESCRIPTION_ITEM_FIELDS:
            # The local materializer adds identifiers and evidence references;
            # the provider proposes only the quoted description.
            value_schema = {"type": "string", "minLength": 1}
        elif field_path == PUBLISHER_RISK_FIELD:
            value_schema = publisher_risk_proposal_schema()
        fields[field_path] = value_schema
    referenced: set[str] = set()
    pending = list(fields.values())
    while pending:
        current = pending.pop()
        if isinstance(current, Mapping):
            reference = current.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/$defs/"):
                name = reference.rsplit("/", 1)[-1]
                if name not in referenced:
                    if name not in CONTRACT_SCHEMA["$defs"]:
                        raise ProviderAdapterError(
                            "field contract references an unknown definition"
                        )
                    referenced.add(name)
                    pending.append(CONTRACT_SCHEMA["$defs"][name])
            pending.extend(current.values())
        elif isinstance(current, Sequence) and not isinstance(
            current, (str, bytes, bytearray)
        ):
            pending.extend(current)
    return {
        "$schema": CONTRACT_SCHEMA["$schema"],
        "$defs": {
            name: CONTRACT_SCHEMA["$defs"][name] for name in sorted(referenced)
        },
        "field_value_schemas": fields,
        "indexed_fields": sorted(LIST_FIELDS),
        "description_item_fields": sorted(_DESCRIPTION_ITEM_FIELDS),
        "publisher_risk_item_field": PUBLISHER_RISK_FIELD,
    }


def _use_risk_value_contract() -> dict[str, Any]:
    """Return the typed subset used by the publisher use/risk recovery pass."""

    contract = _extraction_value_contract()
    allowed = sorted(_DESCRIPTION_ITEM_FIELDS | {PUBLISHER_RISK_FIELD})
    contract["field_value_schemas"] = {
        field_path: contract["field_value_schemas"][field_path]
        for field_path in allowed
    }
    contract["indexed_fields"] = allowed
    contract["description_item_fields"] = sorted(_DESCRIPTION_ITEM_FIELDS)
    return contract


def _private_directory(path: str | os.PathLike[str]) -> Path:
    root = Path(path)
    if root.is_symlink():
        raise ProviderAdapterError("provider decision directory cannot be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ProviderAdapterError("provider decision directory is invalid")
    return root


def _validate_existing_pinned_ledger(path: Path, provider: str) -> None:
    """Reject a reused ledger containing attempts for any other provider."""

    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise ProviderAdapterError("usage ledger path is unsafe")
    try:
        providers = UsageLedger(path).audit_metrics()["providers"]
    except Exception as exc:
        raise ProviderAdapterError("existing usage ledger failed validation") from exc
    if not isinstance(providers, list) or any(item != provider for item in providers):
        raise ProviderAdapterError(
            "existing usage ledger contains an unpinned provider"
        )


@contextmanager
def _locked_aggregate_file(path: Path) -> Iterator[Any]:
    if path.is_symlink() or path.parent.is_symlink():
        raise ProviderAdapterError("aggregate budget path is unsafe")
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as exc:
        raise ProviderAdapterError("aggregate budget journal is unavailable") from exc
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ProviderAdapterError(
                "aggregate budget journal is not a regular file"
            )
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


_AGGREGATE_MONEY_RE = re.compile(r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")


def _aggregate_money(value: Any, label: str) -> Decimal:
    if not isinstance(value, str) or not _AGGREGATE_MONEY_RE.fullmatch(value):
        raise ProviderAdapterError(f"{label} is invalid")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - guarded by the regex
        raise ProviderAdapterError(f"{label} is invalid") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ProviderAdapterError(f"{label} is invalid")
    return parsed


def _aggregate_money_text(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True)
class _AggregateLedgerSnapshot:
    paid_calls: int
    committed_usd: Decimal
    global_halt: bool


@dataclass(frozen=True)
class _AggregateReservation:
    ledger_sha256: str
    base_paid_calls: int
    base_committed_usd: Decimal
    reserved_usd: Decimal


_EMPTY_AGGREGATE_SNAPSHOT = _AggregateLedgerSnapshot(0, Decimal("0"), False)


class _AggregatePaidCallBudget:
    """Serialize sends under one durable USD 25 / 300-paid-call cohort cap.

    Target ledgers remain authoritative. The shared journal reserves one exact
    route-bounded send before the target ledger does, then reconciles both the
    paid-call count and committed USD while the aggregate lock is held. An open
    reservation survives process interruption and is either reused for the same
    send or reconciled from the target ledger before any later authorization.
    """

    _EVENT_KEYS = {
        "aggregate_budget_version",
        "event_type",
        "ledger_sha256",
        "operation_sha256",
        "paid_calls",
        "committed_usd",
        "global_halt",
        "base_paid_calls",
        "base_committed_usd",
        "slots",
        "reserved_usd",
    }

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        ledger_path: Path,
    ) -> None:
        self.path = Path(path)
        self.ledger_path = ledger_path
        if self.path.is_symlink() or self.path.parent.is_symlink():
            raise ProviderAdapterError("aggregate budget path is unsafe")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.resolve() == ledger_path.resolve():
            raise ProviderAdapterError(
                "aggregate budget journal must be distinct from the usage ledger"
            )
        if self.path.exists() and not self.path.is_file():
            raise ProviderAdapterError("aggregate budget journal is not a regular file")
        self.ledger_sha256 = path_sha256(ledger_path)

    @contextmanager
    def _locked(self) -> Iterator[Any]:
        with _locked_aggregate_file(self.path) as handle:
            yield handle

    @staticmethod
    def _consumed(
        latest: Mapping[str, _AggregateLedgerSnapshot],
        reservation: _AggregateReservation,
    ) -> bool:
        observed = latest.get(
            reservation.ledger_sha256, _EMPTY_AGGREGATE_SNAPSHOT
        )
        delta = observed.paid_calls - reservation.base_paid_calls
        if delta == 0 and observed.committed_usd == reservation.base_committed_usd:
            return False
        if (
            delta == 1
            and observed.committed_usd >= reservation.base_committed_usd
        ):
            return True
        raise BudgetCapError(
            "aggregate reservation and target ledger commitments diverged"
        )

    @classmethod
    def _totals(
        cls,
        latest: Mapping[str, _AggregateLedgerSnapshot],
        open_reservations: Mapping[str, _AggregateReservation],
    ) -> tuple[int, Decimal, int, Decimal, bool]:
        paid_calls = sum(item.paid_calls for item in latest.values())
        committed_usd = sum(
            (item.committed_usd for item in latest.values()), Decimal("0")
        )
        reserved_calls = 0
        reserved_usd = Decimal("0")
        for reservation in open_reservations.values():
            if not cls._consumed(latest, reservation):
                reserved_calls += 1
                reserved_usd += reservation.reserved_usd
        total_calls = paid_calls + reserved_calls
        total_usd = committed_usd + reserved_usd
        global_halt = (
            any(item.global_halt for item in latest.values())
            or total_calls > GLOBAL_PAID_CALL_CAP
            or total_usd > GLOBAL_USD_CAP
        )
        return total_calls, total_usd, reserved_calls, reserved_usd, global_halt

    @classmethod
    def _state(
        cls, handle: Any
    ) -> tuple[
        dict[str, _AggregateLedgerSnapshot],
        dict[str, _AggregateReservation],
        int,
        Decimal,
        bool,
    ]:
        handle.seek(0)
        raw = handle.read()
        if raw and not raw.endswith(b"\n"):
            raise ProviderAdapterError("aggregate budget journal is truncated")
        latest: dict[str, _AggregateLedgerSnapshot] = {}
        open_reservations: dict[str, _AggregateReservation] = {}
        for line in raw.splitlines():
            try:
                value = json.loads(
                    line.decode("utf-8"),
                    parse_constant=lambda _value: (_ for _ in ()).throw(
                        ValueError("non-finite JSON")
                    ),
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ProviderAdapterError(
                    "aggregate budget journal is malformed"
                ) from exc
            item = _closed(value, cls._EVENT_KEYS, "aggregate budget event")
            if (
                item["aggregate_budget_version"] != AGGREGATE_BUDGET_VERSION
                or item["event_type"] not in {"snapshot", "reserve", "settle"}
                or not isinstance(item["ledger_sha256"], str)
                or not _DIGEST_RE.fullmatch(item["ledger_sha256"])
            ):
                raise ProviderAdapterError("aggregate budget event is invalid")
            if line != _canonical(dict(item)).encode("utf-8"):
                raise ProviderAdapterError(
                    "aggregate budget journal is not canonical JSONL"
                )
            event_type = item["event_type"]
            ledger_sha256 = item["ledger_sha256"]
            operation_sha256 = item["operation_sha256"]
            if event_type == "snapshot":
                if (
                    operation_sha256 is not None
                    or item["base_paid_calls"] is not None
                    or item["base_committed_usd"] is not None
                    or item["slots"] != 0
                    or item["reserved_usd"] is not None
                    or not isinstance(item["paid_calls"], int)
                    or isinstance(item["paid_calls"], bool)
                    or item["paid_calls"] < 0
                    or not isinstance(item["global_halt"], bool)
                ):
                    raise ProviderAdapterError("aggregate budget snapshot is invalid")
                current = _AggregateLedgerSnapshot(
                    item["paid_calls"],
                    _aggregate_money(
                        item["committed_usd"], "aggregate committed USD"
                    ),
                    item["global_halt"],
                )
                previous = latest.get(ledger_sha256, _EMPTY_AGGREGATE_SNAPSHOT)
                active = next(
                    (
                        reservation
                        for reservation in open_reservations.values()
                        if reservation.ledger_sha256 == ledger_sha256
                    ),
                    None,
                )
                if (
                    current == previous
                    or current.paid_calls < previous.paid_calls
                    or (previous.global_halt and not current.global_halt)
                    or (
                        active is None
                        and current.paid_calls == previous.paid_calls
                        and current.committed_usd != previous.committed_usd
                    )
                    or (
                        active is None
                        and current.committed_usd < previous.committed_usd
                    )
                ):
                    raise ProviderAdapterError("aggregate budget snapshot is invalid")
                if active is not None:
                    cls._consumed({ledger_sha256: current}, active)
                latest[ledger_sha256] = current
            elif event_type == "reserve":
                previous = latest.get(ledger_sha256, _EMPTY_AGGREGATE_SNAPSHOT)
                if (
                    not isinstance(operation_sha256, str)
                    or not _DIGEST_RE.fullmatch(operation_sha256)
                    or item["paid_calls"] is not None
                    or item["committed_usd"] is not None
                    or item["global_halt"] is not None
                    or not isinstance(item["base_paid_calls"], int)
                    or isinstance(item["base_paid_calls"], bool)
                    or item["base_paid_calls"] != previous.paid_calls
                    or item["slots"] != 1
                    or operation_sha256 in open_reservations
                    or any(
                        reservation.ledger_sha256 == ledger_sha256
                        for reservation in open_reservations.values()
                    )
                ):
                    raise ProviderAdapterError(
                        "aggregate budget reservation is invalid"
                    )
                base_usd = _aggregate_money(
                    item["base_committed_usd"], "aggregate base committed USD"
                )
                reserved_usd = _aggregate_money(
                    item["reserved_usd"], "aggregate reserved USD"
                )
                if base_usd != previous.committed_usd:
                    raise ProviderAdapterError(
                        "aggregate budget reservation is invalid"
                    )
                open_reservations[operation_sha256] = _AggregateReservation(
                    ledger_sha256,
                    item["base_paid_calls"],
                    base_usd,
                    reserved_usd,
                )
            else:
                active = open_reservations.get(operation_sha256)
                if (
                    not isinstance(operation_sha256, str)
                    or not _DIGEST_RE.fullmatch(operation_sha256)
                    or item["paid_calls"] is not None
                    or item["committed_usd"] is not None
                    or item["global_halt"] is not None
                    or item["base_paid_calls"] is not None
                    or item["base_committed_usd"] is not None
                    or item["slots"] != 0
                    or item["reserved_usd"] is not None
                    or active is None
                    or active.ledger_sha256 != ledger_sha256
                ):
                    raise ProviderAdapterError(
                        "aggregate budget settlement is invalid"
                    )
                del open_reservations[operation_sha256]
            cls._totals(latest, open_reservations)
        total_calls, total_usd, _, _, global_halt = cls._totals(
            latest, open_reservations
        )
        return latest, open_reservations, total_calls, total_usd, global_halt

    @staticmethod
    def _append(handle: Any, event: Mapping[str, Any]) -> None:
        payload = _canonical(dict(event)).encode("utf-8") + b"\n"
        handle.seek(0, os.SEEK_END)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    @staticmethod
    def _snapshot_event(
        ledger_sha256: str, snapshot: _AggregateLedgerSnapshot
    ) -> dict[str, Any]:
        return {
            "aggregate_budget_version": AGGREGATE_BUDGET_VERSION,
            "event_type": "snapshot",
            "ledger_sha256": ledger_sha256,
            "operation_sha256": None,
            "paid_calls": snapshot.paid_calls,
            "committed_usd": _aggregate_money_text(snapshot.committed_usd),
            "global_halt": snapshot.global_halt,
            "base_paid_calls": None,
            "base_committed_usd": None,
            "slots": 0,
            "reserved_usd": None,
        }

    @staticmethod
    def _settlement_event(
        operation_sha256: str, reservation: _AggregateReservation
    ) -> dict[str, Any]:
        return {
            "aggregate_budget_version": AGGREGATE_BUDGET_VERSION,
            "event_type": "settle",
            "ledger_sha256": reservation.ledger_sha256,
            "operation_sha256": operation_sha256,
            "paid_calls": None,
            "committed_usd": None,
            "global_halt": None,
            "base_paid_calls": None,
            "base_committed_usd": None,
            "slots": 0,
            "reserved_usd": None,
        }

    def _reconcile(
        self,
        handle: Any,
        latest: dict[str, _AggregateLedgerSnapshot],
        open_reservations: dict[str, _AggregateReservation],
    ) -> None:
        raw = UsageLedger(self.ledger_path).audit_state()
        observed = _AggregateLedgerSnapshot(
            raw["paid_calls"],
            _aggregate_money(raw["committed_usd"], "target committed USD"),
            raw["global_halt"],
        )
        previous = latest.get(self.ledger_sha256, _EMPTY_AGGREGATE_SNAPSHOT)
        if (
            not isinstance(observed.paid_calls, int)
            or isinstance(observed.paid_calls, bool)
            or observed.paid_calls < previous.paid_calls
            or (previous.global_halt and not observed.global_halt)
        ):
            raise ProviderAdapterError("aggregate budget ledger state regressed")
        active = next(
            (
                reservation
                for reservation in open_reservations.values()
                if reservation.ledger_sha256 == self.ledger_sha256
            ),
            None,
        )
        if active is None and observed.committed_usd < previous.committed_usd:
            raise ProviderAdapterError("aggregate budget ledger commitment regressed")
        if active is not None:
            self._consumed({self.ledger_sha256: observed}, active)
        if observed != previous:
            self._append(
                handle, self._snapshot_event(self.ledger_sha256, observed)
            )
            latest[self.ledger_sha256] = observed

    def _settle_consumed(
        self,
        handle: Any,
        latest: Mapping[str, _AggregateLedgerSnapshot],
        open_reservations: dict[str, _AggregateReservation],
    ) -> None:
        for operation_sha256, reservation in tuple(open_reservations.items()):
            if (
                reservation.ledger_sha256 == self.ledger_sha256
                and self._consumed(latest, reservation)
            ):
                self._append(
                    handle,
                    self._settlement_event(operation_sha256, reservation),
                )
                del open_reservations[operation_sha256]

    @contextmanager
    def guard(self, *, decision_path: Path) -> Iterator["_AggregateBudgetSession"]:
        with self._locked() as handle:
            latest, open_reservations, _, _, _ = self._state(handle)
            self._reconcile(handle, latest, open_reservations)
            self._settle_consumed(handle, latest, open_reservations)
            session = _AggregateBudgetSession(
                budget=self,
                handle=handle,
                latest=latest,
                open_reservations=open_reservations,
                decision_path=decision_path,
            )
            try:
                yield session
            finally:
                self._reconcile(handle, latest, open_reservations)
                for operation_sha256, reservation in tuple(
                    open_reservations.items()
                ):
                    if reservation.ledger_sha256 == self.ledger_sha256:
                        self._append(
                            handle,
                            self._settlement_event(operation_sha256, reservation),
                        )
                        del open_reservations[operation_sha256]
                self._totals(latest, open_reservations)


@dataclass
class _AggregateBudgetSession:
    budget: _AggregatePaidCallBudget
    handle: Any
    latest: dict[str, _AggregateLedgerSnapshot]
    open_reservations: dict[str, _AggregateReservation]
    decision_path: Path

    def authorize_send(
        self,
        *,
        binding: AttemptBinding,
        retry_index: int,
        route: Any,
        input_token_ceiling: int,
        output_token_ceiling: int,
    ) -> None:
        self.budget._reconcile(
            self.handle, self.latest, self.open_reservations
        )
        self.budget._settle_consumed(
            self.handle, self.latest, self.open_reservations
        )
        total_calls, total_usd, _, _, global_halt = self.budget._totals(
            self.latest, self.open_reservations
        )
        if global_halt:
            raise BudgetCapError("aggregate budget global halt is active")
        if (
            not isinstance(retry_index, int)
            or isinstance(retry_index, bool)
            or not 0 <= retry_index <= MAX_RETRIES
            or not isinstance(input_token_ceiling, int)
            or isinstance(input_token_ceiling, bool)
            or input_token_ceiling <= 0
            or not isinstance(output_token_ceiling, int)
            or isinstance(output_token_ceiling, bool)
            or output_token_ceiling <= 0
        ):
            raise ProviderAdapterError("aggregate send bounds are invalid")
        reserved_usd = (
            Decimal(input_token_ceiling)
            * _aggregate_money(
                route.prompt_price_per_token_usd, "route prompt price"
            )
            + Decimal(output_token_ceiling)
            * _aggregate_money(
                route.completion_price_per_token_usd, "route completion price"
            )
        )
        operation_sha256 = _digest(
            {
                "decision_path_sha256": path_sha256(self.decision_path),
                "logical_call_id": binding.logical_call_id,
                "attempt_id": binding.attempt_id,
                "request_sha256": binding.request_sha256,
                "retry_index": retry_index,
            }
        )
        active_entry = next(
            (
                (key, reservation)
                for key, reservation in self.open_reservations.items()
                if reservation.ledger_sha256 == self.budget.ledger_sha256
            ),
            None,
        )
        current = self.latest.get(
            self.budget.ledger_sha256, _EMPTY_AGGREGATE_SNAPSHOT
        )
        if active_entry is not None:
            active_operation, active = active_entry
            if (
                active_operation != operation_sha256
                or active.base_paid_calls != current.paid_calls
                or active.base_committed_usd != current.committed_usd
                or active.reserved_usd != reserved_usd
                or self.budget._consumed(self.latest, active)
            ):
                raise ProviderAdapterError(
                    "open aggregate reservation differs from the exact paid send"
                )
            return
        if total_calls + 1 > GLOBAL_PAID_CALL_CAP:
            raise BudgetCapError("aggregate paid-call cap would be exceeded")
        if total_usd + reserved_usd > GLOBAL_USD_CAP:
            raise BudgetCapError("aggregate USD cap would be exceeded")
        reservation = _AggregateReservation(
            self.budget.ledger_sha256,
            current.paid_calls,
            current.committed_usd,
            reserved_usd,
        )
        self.budget._append(
            self.handle,
            {
                "aggregate_budget_version": AGGREGATE_BUDGET_VERSION,
                "event_type": "reserve",
                "ledger_sha256": reservation.ledger_sha256,
                "operation_sha256": operation_sha256,
                "paid_calls": None,
                "committed_usd": None,
                "global_halt": None,
                "base_paid_calls": reservation.base_paid_calls,
                "base_committed_usd": _aggregate_money_text(
                    reservation.base_committed_usd
                ),
                "slots": 1,
                "reserved_usd": _aggregate_money_text(
                    reservation.reserved_usd
                ),
            },
        )
        self.open_reservations[operation_sha256] = reservation


def summarize_aggregate_budget(
    path: str | os.PathLike[str],
) -> dict[str, Any]:
    """Return a body-free, locked snapshot of one aggregate budget journal."""

    journal = Path(path)
    with _locked_aggregate_file(journal) as handle:
        latest, open_reservations, total_calls, total_usd, global_halt = (
            _AggregatePaidCallBudget._state(handle)
        )
        handle.seek(0)
        raw = handle.read()
    paid_calls = sum(item.paid_calls for item in latest.values())
    committed_usd = sum(
        (item.committed_usd for item in latest.values()), Decimal("0")
    )
    _, _, reserved_calls, reserved_usd, _ = _AggregatePaidCallBudget._totals(
        latest, open_reservations
    )
    ledgers = set(latest)
    ledgers.update(item.ledger_sha256 for item in open_reservations.values())
    return {
        "aggregate_budget_summary_version": AGGREGATE_BUDGET_SUMMARY_VERSION,
        "aggregate_budget_version": AGGREGATE_BUDGET_VERSION,
        "journal_path_sha256": path_sha256(journal),
        "journal_sha256": hashlib.sha256(raw).hexdigest(),
        "journal_event_count": len(raw.splitlines()),
        "ledger_count": len(ledgers),
        "paid_calls": paid_calls,
        "committed_usd": _aggregate_money_text(committed_usd),
        "open_reservation_count": len(open_reservations),
        "reserved_call_capacity": reserved_calls,
        "reserved_usd_capacity": _aggregate_money_text(reserved_usd),
        "total_budget_commitment": total_calls,
        "total_usd_commitment": _aggregate_money_text(total_usd),
        "paid_call_cap": GLOBAL_PAID_CALL_CAP,
        "usd_cap": _aggregate_money_text(GLOBAL_USD_CAP),
        "global_halt": global_halt,
    }


@dataclass(frozen=True)
class _Runtime:
    provider: str
    ledger_path: Path
    decision_dir: Path
    environment: Mapping[str, str] | None
    transport: ProviderTransport | None
    call: CallFunction
    aggregate_budget: _AggregatePaidCallBudget | None

    @classmethod
    def build(
        cls,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        environment: Mapping[str, str] | None,
        transport: ProviderTransport | None,
        call: CallFunction,
        aggregate_budget_path: str | os.PathLike[str] | None = None,
    ) -> "_Runtime":
        if provider != PINNED_PROVIDER:
            raise ProviderAdapterError("the pinned OpenRouter provider is required")
        ledger = Path(ledger_path)
        if ledger.is_symlink() or ledger.parent.is_symlink():
            raise ProviderAdapterError("usage ledger path is unsafe")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        _validate_existing_pinned_ledger(ledger, provider)
        aggregate = (
            None
            if aggregate_budget_path is None
            else _AggregatePaidCallBudget(
                aggregate_budget_path,
                ledger_path=ledger,
            )
        )
        return cls(
            provider=provider,
            ledger_path=ledger,
            decision_dir=_private_directory(decision_dir),
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget=aggregate,
        )

    def invoke(
        self,
        spec: StructuredCallSpec,
        *,
        decision_name: str,
        validator: Callable[[Mapping[str, Any]], None],
        semantic_retries: int = 0,
    ) -> Any:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,191}\.json", decision_name):
            raise ProviderAdapterError("decision sidecar name is invalid")
        if semantic_retries not in {0, 1}:
            raise ProviderAdapterError("semantic retry bound is invalid")
        if not spec.attempt_id.endswith(".attempt1"):
            raise ProviderAdapterError("initial provider attempt must end in .attempt1")
        for semantic_attempt in range(semantic_retries + 1):
            attempt_number = semantic_attempt + 1
            active_spec = (
                spec
                if semantic_attempt == 0
                else replace(
                    spec,
                    attempt_id=spec.attempt_id[: -len("attempt1")] + "attempt2",
                )
            )
            # Semantic attempts need distinct durable sidecars.  Otherwise a
            # successful attempt2 sidecar sits beside attempt1's failed ledger
            # record, and a fresh process mistakes that sidecar for corrupt
            # attempt1 state before it can resume attempt2.
            active_decision_name = (
                decision_name
                if semantic_retries == 0
                else (
                    decision_name[: -len(".json")]
                    + f".attempt{attempt_number}.json"
                )
            )
            if not re.fullmatch(
                r"[a-z0-9][a-z0-9_.-]{2,191}\.json", active_decision_name
            ):
                raise ProviderAdapterError("attempt decision sidecar name is invalid")
            decision_path = self.decision_dir / active_decision_name
            budget_guard = (
                nullcontext(None)
                if self.aggregate_budget is None
                else self.aggregate_budget.guard(
                    decision_path=decision_path,
                )
            )
            try:
                with budget_guard as paid_send_budget:
                    call_kwargs = {
                        "ledger_path": self.ledger_path,
                        "decision_path": decision_path,
                        "validator": validator,
                        "environment": self.environment,
                        "transport": self.transport,
                    }
                    if paid_send_budget is not None:
                        call_kwargs["paid_send_budget"] = paid_send_budget
                    return self.call(
                        active_spec,
                        **call_kwargs,
                    )
            except (ProviderResponseError, ProviderTerminalAttemptError) as exc:
                if (
                    exc.reason_code != "structured_decision_invalid"
                    or semantic_attempt >= semantic_retries
                ):
                    raise
        raise AssertionError("unreachable semantic retry state")


class OpenRouterQuoteExtractor:
    """Bounded general extraction plus conditional publisher-use/risk recovery."""

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        aggregate_budget_path: str | os.PathLike[str] | None = None,
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget_path=aggregate_budget_path,
        )

    def extract_source(
        self,
        source: SourceDocument,
        *,
        target: TargetIdentity,
        source_catalog_sha256: str,
    ) -> ExtractionBatch:
        if source.target != target or source.text is None:
            raise ProviderAdapterError("quote extraction requires exact-target text")
        if not _DIGEST_RE.fullmatch(source_catalog_sha256):
            raise ProviderAdapterError("source catalog digest is invalid")
        windows = build_source_windows(source)
        use_risk_windows = build_use_risk_windows(source, windows=windows)
        response = extraction_response_schema()
        use_risk_response = use_risk_extraction_response_schema()
        value_contract = _extraction_value_contract()
        use_risk_value_contract = _use_risk_value_contract()
        configuration = {
            "adapter_version": ADAPTER_VERSION,
            "model": MODEL_ID,
            "provider": self.runtime.provider,
            "schema": response["name"],
            "temperature": 0,
            "reasoning": dict(REASONING_CONFIG),
            "max_output_tokens": MAX_EXTRACTION_OUTPUT_TOKENS,
            "window_ids": [item.window_id for item in windows],
            "content_fields": list(CONTENT_FIELD_PATHS),
            "field_value_contract_sha256": _digest(value_contract),
            "use_risk_schema": use_risk_response["name"],
            "use_risk_window_ids": [item.window_id for item in use_risk_windows],
            "use_risk_value_contract_sha256": _digest(use_risk_value_contract),
            "max_proposals": MAX_PROVIDER_PROPOSALS,
            "max_use_risk_proposals": MAX_USE_RISK_PROVIDER_PROPOSALS,
            "max_batch_proposals": MAX_EXTRACTION_BATCH_PROPOSALS,
            "proposal_rejection_policy": "hash_only_per_item_fail_closed",
        }
        config_sha = json_sha256(configuration)
        payload = {
            "target": target.to_dict(),
            "source": {
                "source_id": source.source_id,
                "source_uri": source.source_uri,
                "source_revision": source.source_revision,
                "source_role": source.role.value,
            },
            "allowed_fields": list(CONTENT_FIELD_PATHS),
            "field_value_contract": value_contract,
            "rules": {
                "quote_must_be_verbatim": True,
                "value_must_be_fully_supported_by_quote": True,
                "value_json_must_decode_to_field_schema": True,
                "text_values_preserve_units_and_qualifiers": (
                    "A quoted value such as 7B must be encoded as the JSON string "
                    "\"7B\", never as the number 7. Do not normalize or infer units."
                ),
                "list_fields_require_one_zero_based_index": True,
                "absence_markers_are_omitted_not_proposed": [
                    "Not specified",
                    "Not applicable",
                ],
                "maximum_proposals": MAX_PROVIDER_PROPOSALS,
                "proposal_selection": (
                    "Scan every supplied window before selecting proposals. If the "
                    "source explicitly states an intended use or out-of-scope use, "
                    "reserve at least one proposal slot for that use context. If it "
                    "explicitly states a limitation, risk, or mitigation, reserve at "
                    "least one additional proposal slot for that material. Fill the "
                    "remaining slots with the highest-value nonredundant exact-target "
                    "identity, model-detail, training, and evaluation facts, up to the "
                    "maximum. Never invent a required category when the source does "
                    "not state it."
                ),
                "publisher_reported_risk": {
                    "field_path": PUBLISHER_RISK_FIELD + "[INDEX]",
                    "origin": "source_stated",
                    "value_fields": list(PUBLISHER_RISK_PROPOSAL_FIELDS),
                    "generated_wrapper_metadata": "omit; constructed locally",
                },
                "unknown_or_ambiguous_claims": "omit",
                "base_family_sibling_claims_keep_relation": True,
                "source_id_must_equal": source.source_id,
            },
            "windows": [
                {
                    "window_id": item.window_id,
                    "normalized_start": item.normalized_start,
                    "normalized_end": item.normalized_end,
                    "excerpt": item.excerpt,
                }
                for item in windows
            ],
        }
        logical = f"extract.{source.source_id}.{source_catalog_sha256[:16]}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name=response["name"],
            json_schema=response["schema"],
            system_prompt=(
                "Extract only verbatim, fully supported Model Card evidence from the "
                "provided frozen public-source windows. Inspect all windows and obey "
                "the category-reservation rule before filling remaining proposal "
                "slots. Return the strict JSON object."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=MAX_EXTRACTION_OUTPUT_TOKENS,
            context_metadata={
                "stage": "quote_extraction",
                "source_id": source.source_id,
                "catalog_sha256": source_catalog_sha256,
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            Draft202012Validator(response["schema"]).validate(value)

        result = self.runtime.invoke(
            spec,
            decision_name=(
                f"extract-v2-{source.source_id}-{source_catalog_sha256[:16]}.json"
            ),
            validator=validate,
        )
        validate(result.decision)
        proposals, rejections = normalize_provider_proposals(
            result.decision,
            expected_source_id=source.source_id,
        )
        # This pass is category-complete rather than a fallback. A general
        # response that happens to contain one intended use can still omit the
        # source's limitations, publisher-reported risks, or mitigations. Run
        # the bounded dedicated pass whenever the frozen source has relevant
        # signals, then deduplicate exact proposals locally.
        if use_risk_windows:
            recovery_payload = {
                "target": target.to_dict(),
                "source": payload["source"],
                "allowed_fields": sorted(
                    _DESCRIPTION_ITEM_FIELDS | {PUBLISHER_RISK_FIELD}
                ),
                "field_value_contract": use_risk_value_contract,
                "rules": {
                    "quote_must_be_verbatim": True,
                    "value_must_be_fully_supported_by_quote": True,
                    "maximum_proposals": MAX_USE_RISK_PROVIDER_PROPOSALS,
                    "description_items": (
                        "For intended uses, out-of-scope uses, limitations, known "
                        "biases, and mitigations, value_json may contain either a "
                        "JSON string or the exact nonempty source prose. Do not "
                        "invent wrapper metadata."
                    ),
                    "publisher_reported_risk": {
                        "field_path": PUBLISHER_RISK_FIELD + "[INDEX]",
                        "origin": "source_stated",
                        "value_fields": list(PUBLISHER_RISK_PROPOSAL_FIELDS),
                    },
                    "source_id_must_equal": source.source_id,
                    "unknown_or_ambiguous_claims": "omit",
                    "absence_markers_are_omitted_not_proposed": [
                        "Not specified",
                        "Not applicable",
                    ],
                },
                "windows": [
                    {
                        "window_id": item.window_id,
                        "normalized_start": item.normalized_start,
                        "normalized_end": item.normalized_end,
                        "excerpt": item.excerpt,
                    }
                    for item in use_risk_windows
                ],
            }
            recovery_logical = (
                f"extract-use-risk.{source.source_id}."
                f"{source_catalog_sha256[:16]}"
            )
            recovery_spec = StructuredCallSpec(
                logical_call_id=recovery_logical,
                attempt_id=recovery_logical + ".attempt1",
                provider=self.runtime.provider,
                schema_name=use_risk_response["name"],
                json_schema=use_risk_response["schema"],
                system_prompt=(
                    "Extract only publisher-stated intended uses, out-of-scope uses, "
                    "limitations, known biases, risks, and mitigations from the "
                    "bounded exact-target windows. Return exact quotes and never "
                    "invent a use or risk to fill the response."
                ),
                user_prompt=_canonical(recovery_payload),
                max_output_tokens=MAX_EXTRACTION_OUTPUT_TOKENS,
                context_metadata={
                    "stage": "quote_extraction_use_risk",
                    "source_id": source.source_id,
                    "catalog_sha256": source_catalog_sha256,
                },
            )

            def validate_use_risk(value: Mapping[str, Any]) -> None:
                Draft202012Validator(use_risk_response["schema"]).validate(value)

            recovered = self.runtime.invoke(
                recovery_spec,
                decision_name=(
                    f"extract-use-risk-v1-{source.source_id}-"
                    f"{source_catalog_sha256[:16]}.json"
                ),
                validator=validate_use_risk,
            )
            validate_use_risk(recovered.decision)
            recovered_proposals, recovered_rejections = normalize_provider_proposals(
                recovered.decision,
                expected_source_id=source.source_id,
            )
            offset = len(result.decision["proposals"])
            combined = {item.proposal_id: item for item in proposals}
            combined_rejections = list(rejections)
            combined_rejections.extend(
                ProviderProposalRejection(
                    proposal_index=offset + item.proposal_index,
                    proposal_sha256=item.proposal_sha256,
                    reason=item.reason,
                )
                for item in recovered_rejections
            )
            raw_by_id: dict[str, tuple[int, Mapping[str, Any]]] = {}
            for index, raw in enumerate(recovered.decision["proposals"]):
                try:
                    normalized = proposals_from_provider_value(
                        {"proposals": [raw]}
                    )[0]
                except (TypeError, ValueError):
                    continue
                raw_by_id.setdefault(normalized.proposal_id, (index, raw))
            for item in recovered_proposals:
                if item.proposal_id not in combined:
                    combined[item.proposal_id] = item
                    continue
                raw_index, raw = raw_by_id[item.proposal_id]
                combined_rejections.append(
                    ProviderProposalRejection(
                        proposal_index=offset + raw_index,
                        proposal_sha256=_digest(raw),
                        reason="duplicate_proposal",
                    )
                )
            proposals = tuple(
                sorted(combined.values(), key=lambda item: item.proposal_id)
            )
            rejections = tuple(
                sorted(combined_rejections, key=lambda item: item.proposal_index)
            )
        return ExtractionBatch.build(
            target=target,
            source_catalog_sha256=source_catalog_sha256,
            provider=self.runtime.provider,
            inference_config_sha256=config_sha,
            proposals=proposals,
            rejections=rejections,
        )


class OpenRouterClaimChecker:
    """Independent field-fit and complete-value checks for one quote candidate."""

    checker_id = CLAIM_CHECKER_ID
    checker_revision = ADAPTER_VERSION

    _REASONS = {
        GateName.FIELD_FIT: {
            "accepted": ("semantic_field_fit",),
            "withheld": ("wrong_field", "ambiguous_field_fit"),
        },
        GateName.VALUE_SUPPORT: {
            "accepted": ("semantic_value_support",),
            "withheld": ("incomplete_value_support", "contradictory_value"),
        },
    }

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        aggregate_budget_path: str | os.PathLike[str] | None = None,
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget_path=aggregate_budget_path,
        )

    def decide(self, candidate: ClaimCandidate, gate: GateName) -> ProseCheckerDecision:
        if not isinstance(candidate, ClaimCandidate):
            raise ProviderAdapterError("claim checker requires a typed candidate")
        gate = GateName(gate)
        if gate not in self._REASONS:
            raise ProviderAdapterError("claim checker can decide only prose gates")
        reasons = self._REASONS[gate]
        allowed_reasons = sorted(reasons["accepted"] + reasons["withheld"])
        schema = {
            "type": "object",
            "required": ["status", "reason"],
            "properties": {
                "status": {"enum": ["accepted", "withheld"]},
                "reason": {"enum": allowed_reasons},
            },
            "additionalProperties": False,
        }
        evidence = [
            {
                "source_id": item.source_id,
                "source_role": item.source_role.value,
                "source_revision": item.source_revision,
                "quote": item.quote,
                "section_path": list(item.section_path),
                "table_id": item.table_id,
            }
            for item in candidate.evidence
        ]
        task = (
            "Decide whether the quoted evidence semantically belongs in exactly the "
            "proposed Model Card field. Do not assess or alter the value."
            if gate is GateName.FIELD_FIT
            else "Decide whether the quoted evidence completely supports every proposed "
            "value and qualification. Do not alter the value, field, entity, or relation."
        )
        payload = {
            "task": task,
            "target": candidate.target.to_dict(),
            "candidate_id": candidate.candidate_id,
            "field_path": candidate.field_path,
            "value": candidate.value,
            "benchmark_scope": candidate.benchmark_scope,
            "claim_entity": candidate.claim_entity,
            "relation": candidate.relation.value,
            "evidence": evidence,
        }
        logical = f"claim.{gate.value}.{candidate.candidate_id}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name=f"model_card_{gate.value}_v1",
            json_schema=schema,
            system_prompt=(
                "Apply only the named Model Card support gate to the supplied frozen "
                "evidence. Accept or withhold; never rewrite any candidate attribute."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=MAX_CLAIM_OUTPUT_TOKENS,
            context_metadata={
                "stage": gate.value,
                "candidate_id": candidate.candidate_id,
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            item = _closed(value, {"status", "reason"}, "claim checker decision")
            if item["status"] not in {"accepted", "withheld"}:
                raise ProviderAdapterError("claim checker status is invalid")
            if item["reason"] not in reasons[item["status"]]:
                raise ProviderAdapterError("claim checker status/reason pair is invalid")

        result = self.runtime.invoke(
            spec,
            decision_name=f"{candidate.candidate_id}-{gate.value}.json",
            validator=validate,
        )
        validate(result.decision)
        return ProseCheckerDecision.for_candidate(
            candidate,
            gate=gate,
            checker=self.checker_id,
            method=f"bounded_openrouter_{gate.value}",
            status=DecisionStatus(result.decision["status"]),
            reason=result.decision["reason"],
        )


class OpenRouterFactChecker:
    """FactReasoner checker using only the request's bounded frozen contexts."""

    checker_id = FACT_CHECKER_ID
    checker_revision = ADAPTER_VERSION

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        aggregate_budget_path: str | os.PathLike[str] | None = None,
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget_path=aggregate_budget_path,
        )
        self._response_cache: dict[str, CheckerResponse] = {}

    def check_many(
        self, requests: Sequence[CheckRequest]
    ) -> tuple[CheckerResponse, ...]:
        ordered = tuple(requests)
        if (
            not ordered
            or len(ordered) > MAX_FACT_CHECKS_PER_BATCH
            or not all(isinstance(item, CheckRequest) for item in ordered)
        ):
            raise ProviderAdapterError(
                "FactReasoner batch requires between 1 and 64 CheckRequests"
            )
        request_hashes = tuple(check_request_sha256(item) for item in ordered)
        request_by_hash: dict[str, CheckRequest] = {}
        missing_hashes: list[str] = []
        for request_hash, request in zip(request_hashes, ordered):
            request_by_hash.setdefault(request_hash, request)
            if (
                request_hash not in self._response_cache
                and request_hash not in missing_hashes
            ):
                missing_hashes.append(request_hash)
        if not missing_hashes:
            return tuple(self._response_cache[item] for item in request_hashes)

        chunk_by_id: dict[str, Mapping[str, Any]] = {}
        context_ids_by_request: dict[str, tuple[str, ...]] = {}
        checks = []
        for request_hash in missing_hashes:
            request = request_by_hash[request_hash]
            context_ids = tuple(item.chunk.chunk_id for item in request.contexts)
            context_ids_by_request[request_hash] = context_ids
            checks.append(
                {
                    "request_sha256": request_hash,
                    "hypothesis": request.hypothesis,
                    "stage": request.stage.value,
                    "fallback_complete": request.fallback_complete,
                    "context_ids": list(context_ids),
                }
            )
            for context in request.contexts:
                existing = chunk_by_id.setdefault(
                    context.chunk.chunk_id,
                    {
                        "chunk_id": context.chunk.chunk_id,
                        "chunk_sha256": context.chunk.content_sha256,
                        "text": context.text,
                    },
                )
                if (
                    existing["chunk_sha256"] != context.chunk.content_sha256
                    or existing["text"] != context.text
                ):
                    raise ProviderAdapterError(
                        "FactReasoner chunk identifier collision"
                    )
        chunk_ids = sorted(chunk_by_id)
        schema = {
            "type": "object",
            "required": ["decisions"],
            "properties": {
                "decisions": {
                    "type": "array",
                    "minItems": len(missing_hashes),
                    "maxItems": len(missing_hashes),
                    "items": {
                        "type": "object",
                        "required": [
                            "request_sha256",
                            "outcome",
                            "cited_chunk_ids",
                        ],
                        "properties": {
                            "request_sha256": {"enum": missing_hashes},
                            "outcome": {
                                "enum": ["support", "contradiction", "neutral"]
                            },
                            "cited_chunk_ids": {
                                "type": "array",
                                "items": {"enum": chunk_ids},
                                "uniqueItems": True,
                                "minItems": 1,
                                "maxItems": len(chunk_ids),
                            },
                        },
                        "additionalProperties": False,
                    },
                }
            },
            "additionalProperties": False,
        }
        payload = {
            "checks": checks,
            "contexts": [chunk_by_id[item] for item in chunk_ids],
            "rules": {
                "one_decision_per_request_in_supplied_order": True,
                "support_requires_complete_entailment": True,
                "contradiction_requires_explicit_conflict": True,
                "otherwise": "neutral",
                "citations_must_belong_to_that_request": True,
            },
        }
        batch_sha256 = _digest(
            {
                "adapter_version": ADAPTER_VERSION,
                "request_sha256s": missing_hashes,
            }
        )
        logical = f"fact.batch.{batch_sha256[:24]}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name="model_card_factreasoner_batch_v1",
            json_schema=schema,
            system_prompt=(
                "Assess each explicit hypothesis only against its named frozen-source "
                "contexts. Return one ordered structured decision per request."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=MAX_FACT_OUTPUT_TOKENS,
            context_metadata={
                "stage": "factreasoner_batch",
                "batch_sha256": batch_sha256,
                "request_count": len(missing_hashes),
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            item = _closed(value, {"decisions"}, "FactReasoner batch decision")
            values = item["decisions"]
            if not isinstance(values, list) or len(values) != len(missing_hashes):
                raise ProviderAdapterError("FactReasoner batch coverage is invalid")
            actual_hashes = []
            for value_item in values:
                decision = _closed(
                    value_item,
                    {"request_sha256", "outcome", "cited_chunk_ids"},
                    "FactReasoner decision",
                )
                request_hash = decision["request_sha256"]
                actual_hashes.append(request_hash)
                if request_hash not in context_ids_by_request:
                    raise ProviderAdapterError("FactReasoner request digest is invalid")
                if decision["outcome"] not in {
                    "support",
                    "contradiction",
                    "neutral",
                }:
                    raise ProviderAdapterError("FactReasoner outcome is invalid")
                cited = decision["cited_chunk_ids"]
                if (
                    not isinstance(cited, list)
                    or not cited
                    or len(cited) != len(set(cited))
                    or not set(cited).issubset(context_ids_by_request[request_hash])
                ):
                    raise ProviderAdapterError("FactReasoner citations are invalid")
            if actual_hashes != missing_hashes:
                raise ProviderAdapterError(
                    "FactReasoner decisions are missing, duplicated, or reordered"
                )

        result = self.runtime.invoke(
            spec,
            decision_name=f"fact-batch-{batch_sha256[:24]}.json",
            validator=validate,
            semantic_retries=1,
        )
        validate(result.decision)
        pending: dict[str, CheckerResponse] = {}
        for decision in result.decision["decisions"]:
            outcome = CheckOutcome(decision["outcome"])
            pending[decision["request_sha256"]] = CheckerResponse(
                outcome=outcome,
                reason_code={
                    CheckOutcome.SUPPORT: "support_in_context",
                    CheckOutcome.CONTRADICTION: "contradiction_in_context",
                    CheckOutcome.NEUTRAL: "no_complete_support",
                }[outcome],
                cited_chunk_ids=tuple(decision["cited_chunk_ids"]),
            )
        self._response_cache.update(pending)
        return tuple(self._response_cache[item] for item in request_hashes)

    def check(self, request: CheckRequest) -> CheckerResponse:
        if not isinstance(request, CheckRequest):
            raise ProviderAdapterError("FactReasoner checker requires a CheckRequest")
        return self.check_many((request,))[0]


class OpenRouterApplicabilityChecker:
    """Independent applicability gate for one taxonomy-grounded risk candidate."""

    def __init__(
        self,
        *,
        provider: str,
        ledger_path: str | os.PathLike[str],
        decision_dir: str | os.PathLike[str],
        aggregate_budget_path: str | os.PathLike[str] | None = None,
        environment: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        call: CallFunction = structured_json_call,
    ) -> None:
        self.runtime = _Runtime.build(
            provider=provider,
            ledger_path=ledger_path,
            decision_dir=decision_dir,
            environment=environment,
            transport=transport,
            call=call,
            aggregate_budget_path=aggregate_budget_path,
        )

    def assess(
        self,
        candidate: RiskCandidate,
        contexts: tuple[UseContext, ...],
    ) -> ApplicabilityDecision:
        if not isinstance(candidate, RiskCandidate) or not contexts:
            raise ProviderAdapterError("risk applicability requires candidate and contexts")
        if tuple(sorted(item.context_id for item in contexts)) != candidate.context_ids:
            raise ProviderAdapterError("risk applicability contexts are stale")
        schema = {
            "type": "object",
            "required": ["status", "reason", "rationale"],
            "properties": {
                "status": {"enum": ["accepted", "withheld"]},
                "reason": {
                    "enum": ["specific_use_context_supported", "risk_not_specific_to_context"]
                },
                "rationale": {"type": "string", "minLength": 20, "maxLength": 1600},
            },
            "additionalProperties": False,
        }
        payload = {
            "risk": {
                "risk_id": candidate.risk_id,
                "name": candidate.name,
                "description": candidate.description,
                "taxonomy": candidate.taxonomy.to_dict(),
            },
            "use_contexts": [item.to_dict() for item in contexts],
            "rules": {
                "candidate_mapping_is_not_confirmed_harm": True,
                "accept_only_if_specific_to_grounded_context": True,
                "do_not_invent_context_or_mitigation": True,
            },
        }
        logical = f"risk.applicability.{candidate.candidate_id}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=self.runtime.provider,
            schema_name="model_card_risk_applicability_v1",
            json_schema=schema,
            system_prompt=(
                "Assess whether the taxonomy risk may specifically apply to the supplied "
                "evidence-backed use context. Do not treat it as publisher-reported harm."
            ),
            user_prompt=_canonical(payload),
            max_output_tokens=MAX_RISK_OUTPUT_TOKENS,
            context_metadata={
                "stage": "risk_applicability",
                "risk_candidate_id": candidate.candidate_id,
            },
        )

        def validate(value: Mapping[str, Any]) -> None:
            item = _closed(
                value, {"status", "reason", "rationale"}, "risk applicability decision"
            )
            expected = {
                "accepted": "specific_use_context_supported",
                "withheld": "risk_not_specific_to_context",
            }
            if item["status"] not in expected or item["reason"] != expected[item["status"]]:
                raise ProviderAdapterError("risk applicability status/reason pair is invalid")
            if not isinstance(item["rationale"], str) or not 20 <= len(
                item["rationale"].strip()
            ) <= 1600:
                raise ProviderAdapterError("risk applicability rationale is invalid")

        result = self.runtime.invoke(
            spec,
            decision_name=f"{candidate.candidate_id}-applicability.json",
            validator=validate,
        )
        validate(result.decision)
        return ApplicabilityDecision.for_candidate(
            candidate,
            status=ApplicabilityStatus(result.decision["status"]),
            checker=CLAIM_CHECKER_ID,
            method="bounded_openrouter_use_context_applicability",
            reason=result.decision["reason"],
            rationale=result.decision["rationale"],
        )


def build_nexus_openrouter_inference_engine(
    *,
    provider: str,
    ledger_path: str | os.PathLike[str],
    decision_dir: str | os.PathLike[str],
    aggregate_budget_path: str | os.PathLike[str] | None = None,
    environment: Mapping[str, str] | None = None,
    transport: ProviderTransport | None = None,
    call: CallFunction = structured_json_call,
) -> Any:
    """Return an optional Nexus ``InferenceEngine`` backed by the exact runtime.

    Nexus performs its supported generic risk-selection flow and supplies the
    taxonomy-constrained response schema.  This adapter wraps root-array schemas
    in a strict object because the provider runtime deliberately accepts only
    closed JSON objects.
    """

    try:
        from ai_atlas_nexus.blocks.inference import (
            InferenceEngine,
            TextGenerationInferenceOutput,
        )
    except (ImportError, ModuleNotFoundError) as exc:
        raise ProviderAdapterError("ai-atlas-nexus 1.2.4 is unavailable") from exc

    runtime = _Runtime.build(
        provider=provider,
        ledger_path=ledger_path,
        decision_dir=decision_dir,
        environment=environment,
        transport=transport,
        call=call,
        aggregate_budget_path=aggregate_budget_path,
    )

    class _OpenRouterNexusEngine(InferenceEngine):
        _inference_engine_type = "openrouter"

        def __init__(self) -> None:
            # Avoid Nexus base initialization: it creates another client and health
            # check, violating the single-runtime/no-hidden-retry invariant.
            self.model_name_or_path = MODEL_ID
            self.credentials = {}
            self.parameters = {"temperature": 0}
            self.concurrency_limit = 1
            self.auto_download_model = False
            self.client = None
            self.backend = self

        def prepare_credentials(self, credentials):
            return {}

        def create_client(self, credentials=None):
            return None

        def ping(self):
            return None

        def generate(
            self,
            prompts,
            response_format=None,
            postprocessors=None,
            verbose=True,
        ):
            if (
                not isinstance(prompts, list)
                or not prompts
                or not all(isinstance(item, str) and item for item in prompts)
            ):
                raise ProviderAdapterError("Nexus prompts are invalid")
            if not isinstance(response_format, dict):
                raise ProviderAdapterError("Nexus must provide a JSON Schema object")
            if postprocessors not in (None, [], ["list_of_str"], ["json_object"]):
                raise ProviderAdapterError("unsupported Nexus postprocessor")
            wrapped = {
                "type": "object",
                "required": ["prediction"],
                "properties": {"prediction": response_format},
                "additionalProperties": False,
            }
            Draft202012Validator.check_schema(wrapped)
            validator = Draft202012Validator(wrapped)
            outputs = []
            for prompt in prompts:
                prompt_sha = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
                logical = f"nexus.risk_selection.{prompt_sha[:24]}"
                spec = StructuredCallSpec(
                    logical_call_id=logical,
                    attempt_id=logical + ".attempt1",
                    provider=runtime.provider,
                    schema_name="nexus_generic_risk_selection_v1",
                    json_schema=wrapped,
                    system_prompt=(
                        "Follow the AI Atlas Nexus generic risk-selection instruction and "
                        "return only values permitted by its supplied taxonomy schema."
                    ),
                    user_prompt=prompt,
                    max_output_tokens=2048,
                    context_metadata={
                        "stage": "nexus_risk_selection",
                        "instruction_sha256": prompt_sha,
                    },
                )

                def validate(value: Mapping[str, Any]) -> None:
                    errors = sorted(
                        validator.iter_errors(value),
                        key=lambda item: tuple(str(x) for x in item.absolute_path),
                    )
                    if errors:
                        raise ProviderAdapterError("Nexus decision violates its taxonomy schema")

                result = runtime.invoke(
                    spec,
                    decision_name=f"nexus-{prompt_sha[:24]}.json",
                    validator=validate,
                )
                validate(result.decision)
                receipt = getattr(result, "receipt", None)
                outputs.append(
                    TextGenerationInferenceOutput(
                        prediction=result.decision["prediction"],
                        input_tokens=getattr(receipt, "prompt_tokens", None),
                        output_tokens=getattr(receipt, "completion_tokens", None),
                        stop_reason="structured_output",
                        model_name_or_path=MODEL_ID,
                        inference_engine="openrouter",
                    )
                )
            return outputs

        def chat(
            self,
            messages,
            tools=None,
            response_format=None,
            postprocessors=None,
            verbose=True,
        ):
            if isinstance(messages, str):
                prompts = [messages]
            elif isinstance(messages, list) and all(isinstance(item, str) for item in messages):
                prompts = messages
            else:
                raise ProviderAdapterError("Nexus chat messages are unsupported")
            return self.generate(
                prompts,
                response_format=response_format,
                postprocessors=postprocessors,
                verbose=verbose,
            )

    return _OpenRouterNexusEngine()


__all__ = [
    "ADAPTER_VERSION",
    "AGGREGATE_BUDGET_SUMMARY_VERSION",
    "AGGREGATE_BUDGET_VERSION",
    "CLAIM_CHECKER_ID",
    "FACT_CHECKER_ID",
    "MAX_CLAIM_OUTPUT_TOKENS",
    "MAX_EXTRACTION_OUTPUT_TOKENS",
    "MAX_FACT_OUTPUT_TOKENS",
    "MAX_RISK_OUTPUT_TOKENS",
    "OpenRouterApplicabilityChecker",
    "OpenRouterClaimChecker",
    "OpenRouterFactChecker",
    "OpenRouterQuoteExtractor",
    "ProviderAdapterError",
    "build_nexus_openrouter_inference_engine",
    "summarize_aggregate_budget",
]
