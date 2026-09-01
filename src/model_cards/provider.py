"""Bounded OpenRouter structured-output runtime for all model-card stages.

The runtime sends only the exact pinned model through one explicit provider,
uses server-enforced strict JSON Schema at temperature zero, and delegates all
paid-call state transitions to :mod:`model_cards.run_ledger`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Protocol, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from .run_ledger import (
    EXACT_MODEL,
    MAX_RETRIES,
    AttemptBinding,
    LedgerConflictError,
    ReservationToken,
    RouteSnapshot,
    UncertainSendError,
    UsageLedger,
    UsageReceipt,
    json_sha256,
    path_sha256,
    read_decision_sidecar,
    utc_now,
    write_decision_sidecar,
)


MODEL_ID = EXACT_MODEL
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_ROUTE_URL = (
    "https://openrouter.ai/api/v1/models/"
    "deepseek/deepseek-v4-flash-0731/endpoints"
)
OPENROUTER_KEY_ENV = "OPENROUTER_API_KEY"
PROVIDER_RUNTIME_VERSION = "openrouter-structured-provider/v1"
DETERMINISTIC_USER_AGENT = "evaleval-model-cards/0.1 structured-provider/v1"
MAX_REQUEST_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_ROUTE_BYTES = 1024 * 1024
MAX_SCHEMA_BYTES = 256 * 1024
MAX_PROMPT_CHARS = 750_000
MAX_OUTPUT_TOKENS = 16_384
PROMPT_TOKEN_SAFETY_OVERHEAD = 4096
PAID_TIMEOUT_SECONDS = 180.0
ROUTE_TIMEOUT_SECONDS = 15.0

_SCHEMA_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{2,63}$")
_RETRYABLE_STATUSES = frozenset({429, *range(500, 600)})


class ProviderError(RuntimeError):
    pass


class ProviderRouteError(ProviderError):
    pass


class ProviderResponseError(ProviderError):
    pass


class ProviderUncertainError(ProviderError):
    pass


class RetryExhaustedError(ProviderResponseError):
    pass


class MissingCredentialError(ProviderError):
    pass


class TransportUncertainError(OSError):
    pass


Clock = Callable[[], datetime]
Monotonic = Callable[[], float]
Sleeper = Callable[[float], None]
DecisionValidator = Callable[[Mapping[str, Any]], None]


@dataclass(frozen=True)
class ProviderHttpRequest:
    method: str
    url: str
    headers: tuple[tuple[str, str], ...]
    body: bytes | None = field(default=None, repr=False)
    timeout_seconds: float = 0.0
    max_response_bytes: int = 0

    def __post_init__(self) -> None:
        if self.method not in {"GET", "POST"}:
            raise ProviderError("provider request method is invalid")
        expected_url = OPENROUTER_ROUTE_URL if self.method == "GET" else OPENROUTER_API_URL
        if self.url != expected_url:
            raise ProviderError("provider request URL is not pinned")
        if self.method == "GET" and self.body is not None:
            raise ProviderError("route request cannot have a body")
        if self.method == "POST" and not isinstance(self.body, bytes):
            raise ProviderError("paid provider request requires bytes")
        if self.timeout_seconds <= 0 or self.max_response_bytes <= 0:
            raise ProviderError("provider request bounds are invalid")
        seen: set[str] = set()
        for name, value in self.headers:
            if (
                not isinstance(name, str)
                or not isinstance(value, str)
                or name.casefold() in seen
                or "\r" in value
                or "\n" in value
            ):
                raise ProviderError("provider request headers are invalid")
            seen.add(name.casefold())

    def header(self, name: str) -> str | None:
        wanted = name.casefold()
        return next(
            (value for key, value in self.headers if key.casefold() == wanted), None
        )

    def __repr__(self) -> str:
        return (
            f"ProviderHttpRequest(method={self.method!r}, url={self.url!r}, "
            f"header_names={tuple(name for name, _ in self.headers)!r}, "
            f"body_bytes={len(self.body or b'')}, timeout_seconds={self.timeout_seconds!r}, "
            f"max_response_bytes={self.max_response_bytes!r})"
        )


@dataclass(frozen=True)
class ProviderHttpResponse:
    status_code: int
    final_url: str
    headers: tuple[tuple[str, str], ...] = field(default=(), repr=False)
    body: bytes = field(default=b"", repr=False)

    def __post_init__(self) -> None:
        if (
            isinstance(self.status_code, bool)
            or not isinstance(self.status_code, int)
            or not 100 <= self.status_code <= 599
        ):
            raise ProviderError("provider response status is invalid")
        if not isinstance(self.final_url, str):
            raise ProviderError("provider response URL is invalid")
        if not isinstance(self.body, bytes):
            raise ProviderError("provider response body must be bytes")


class ProviderTransport(Protocol):
    def open(self, request: ProviderHttpRequest) -> ProviderHttpResponse:
        """Perform exactly one HTTP request with no automatic retry or fallback."""


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class UrllibProviderTransport:
    """One-shot urllib transport without proxy, redirect, cookie, or SDK retries."""

    def open(self, request: ProviderHttpRequest) -> ProviderHttpResponse:
        urllib_request = Request(
            request.url,
            data=request.body,
            method=request.method,
        )
        for name, value in request.headers:
            urllib_request.add_unredirected_header(name, value)
        opener = build_opener(ProxyHandler({}), _RejectRedirects(), HTTPSHandler())
        try:
            response = opener.open(urllib_request, timeout=request.timeout_seconds)
        except HTTPError as exc:
            response = exc
        except (URLError, TimeoutError, OSError):
            raise TransportUncertainError("provider transport outcome is uncertain") from None
        try:
            body = response.read(request.max_response_bytes + 1)
            if len(body) > request.max_response_bytes:
                raise TransportUncertainError("provider response exceeded its byte bound")
            headers = tuple(
                sorted(
                    ((str(key), str(value)) for key, value in response.headers.items()),
                    key=lambda item: (item[0].casefold(), item[1]),
                )
            )
            return ProviderHttpResponse(
                status_code=int(getattr(response, "status", response.code)),
                final_url=str(response.geturl()),
                headers=headers,
                body=body,
            )
        except TransportUncertainError:
            raise
        except (URLError, TimeoutError, OSError):
            raise TransportUncertainError("provider transport outcome is uncertain") from None
        finally:
            response.close()


@dataclass(frozen=True)
class StructuredCallSpec:
    logical_call_id: str
    attempt_id: str
    provider: str
    schema_name: str
    json_schema: Mapping[str, Any]
    system_prompt: str = field(repr=False)
    user_prompt: str = field(repr=False)
    max_output_tokens: int = 4096
    context_metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.schema_name, str) or not _SCHEMA_NAME_RE.fullmatch(
            self.schema_name
        ):
            raise ProviderError("schema_name is invalid")
        schema = _json_object(self.json_schema, "JSON Schema")
        if schema.get("type") != "object" or schema.get("additionalProperties") is not False:
            raise ProviderError(
                "strict structured output requires an object schema with additionalProperties=false"
            )
        if len(_canonical_bytes(schema)) > MAX_SCHEMA_BYTES:
            raise ProviderError("JSON Schema exceeds its byte bound")
        object.__setattr__(self, "json_schema", schema)
        for label, value in (
            ("system_prompt", self.system_prompt),
            ("user_prompt", self.user_prompt),
        ):
            if (
                not isinstance(value, str)
                or not value
                or len(value) > MAX_PROMPT_CHARS
                or any(ord(character) == 0 for character in value)
            ):
                raise ProviderError(f"{label} is invalid or exceeds its bound")
        if (
            isinstance(self.max_output_tokens, bool)
            or not isinstance(self.max_output_tokens, int)
            or not 1 <= self.max_output_tokens <= MAX_OUTPUT_TOKENS
        ):
            raise ProviderError("max_output_tokens is outside the supported bound")


@dataclass(frozen=True)
class StructuredCallResult:
    decision: Mapping[str, Any]
    receipt: UsageReceipt
    resumed: bool
    logical_call_id: str
    attempt_id: str
    provider: str
    request_sha256: str


def structured_json_call(
    spec: StructuredCallSpec,
    *,
    ledger_path: str | os.PathLike[str],
    decision_path: str | os.PathLike[str],
    validator: DecisionValidator,
    environment: Mapping[str, str] | None = None,
    transport: ProviderTransport | None = None,
    clock: Clock = utc_now,
    monotonic: Monotonic = time.monotonic,
    sleeper: Sleeper = time.sleep,
) -> StructuredCallResult:
    """Run or deterministically resume one strict structured-output attempt."""

    if not isinstance(spec, StructuredCallSpec):
        raise ProviderError("spec must be a StructuredCallSpec")
    request_payload = _request_payload(spec)
    request_fingerprint_bytes = _canonical_bytes(request_payload)
    if len(request_fingerprint_bytes) > MAX_REQUEST_BYTES:
        raise ProviderError("provider request exceeds its byte bound")
    semantic_request = dict(request_payload)
    semantic_request.pop("provider")
    request_sha = json_sha256(semantic_request)
    schema_sha = json_sha256(spec.json_schema)
    binding = AttemptBinding(
        logical_call_id=spec.logical_call_id,
        attempt_id=spec.attempt_id,
        model=MODEL_ID,
        provider=spec.provider,
        request_sha256=request_sha,
        schema_sha256=schema_sha,
        sidecar_path_sha256=path_sha256(decision_path),
        context_metadata=spec.context_metadata,
    )
    ledger = UsageLedger(ledger_path, clock=clock)
    snapshot = ledger.inspect(binding)
    if snapshot is not None:
        resumed = _resume_if_possible(
            ledger,
            snapshot,
            decision_path=decision_path,
            validator=validator,
        )
        if resumed is not None:
            decision, receipt = resumed
            return StructuredCallResult(
                decision=decision,
                receipt=receipt,
                resumed=True,
                logical_call_id=spec.logical_call_id,
                attempt_id=spec.attempt_id,
                provider=spec.provider,
                request_sha256=request_sha,
            )
        if snapshot.status == "failed":
            raise LedgerConflictError(
                "attempt is terminal; an explicit new attempt_id is required"
            )
    elif Path(decision_path).exists() or Path(decision_path).is_symlink():
        raise LedgerConflictError("fresh attempt has a pre-existing decision sidecar")

    api_key = _environment_key(environment)
    snapshot = ledger.begin_attempt(binding)
    if snapshot.status in {"pending", "uncertain"}:
        raise UncertainSendError("attempt cannot be sent again after uncertain state")
    next_retry = len(snapshot.reservations)
    if snapshot.status == "ready_to_retry":
        next_retry = len(snapshot.reservations)
    elif snapshot.status == "manifested":
        next_retry = 0

    active_transport = transport or UrllibProviderTransport()
    while next_retry <= MAX_RETRIES:
        route = _fetch_route(
            provider=spec.provider,
            transport=active_transport,
            clock=clock,
        )
        paid_payload = _route_bound_payload(request_payload, route)
        paid_request_bytes = _canonical_bytes(paid_payload)
        if len(paid_request_bytes) > MAX_REQUEST_BYTES:
            raise ProviderError("route-bound provider request exceeds its byte bound")
        input_ceiling = len(paid_request_bytes) + PROMPT_TOKEN_SAFETY_OVERHEAD
        token = ledger.reserve(
            binding,
            retry_index=next_retry,
            route=route,
            input_token_ceiling=input_ceiling,
            output_token_ceiling=spec.max_output_tokens,
        )
        started = _monotonic(monotonic)
        paid_request = ProviderHttpRequest(
            method="POST",
            url=OPENROUTER_API_URL,
            headers=_paid_headers(api_key),
            body=paid_request_bytes,
            timeout_seconds=PAID_TIMEOUT_SECONDS,
            max_response_bytes=MAX_RESPONSE_BYTES,
        )
        try:
            response = active_transport.open(paid_request)
        except BaseException as exc:
            latency = _latency_ms(started, monotonic)
            unknown = UsageReceipt(
                http_status=None,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                charged_usd=None,
                latency_ms=latency,
                returned_model=None,
                returned_provider=None,
            )
            try:
                ledger.record_terminal(
                    token,
                    outcome="uncertain_send",
                    receipt=unknown,
                    reason_code="transport_uncertain",
                )
            except BaseException:
                pass
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise ProviderUncertainError(
                "provider transport outcome is uncertain; duplicate send is forbidden"
            ) from None
        latency = _latency_ms(started, monotonic)
        try:
            _validate_paid_http_response(response)
        except ProviderUncertainError:
            ledger.record_terminal(
                token,
                outcome="uncertain_send",
                receipt=UsageReceipt(
                    http_status=None,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    charged_usd=None,
                    latency_ms=latency,
                    returned_model=None,
                    returned_provider=None,
                ),
                reason_code="invalid_transport_response",
            )
            raise
        if response.status_code != 200:
            conservative = UsageReceipt(
                http_status=response.status_code,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                charged_usd=token.reserved_usd,
                latency_ms=latency,
                returned_model=None,
                returned_provider=None,
            )
            retryable = response.status_code in _RETRYABLE_STATUSES
            ledger.record_terminal(
                token,
                outcome="retryable_http_error" if retryable else "terminal_http_error",
                receipt=conservative,
                reason_code=(
                    "http_retryable" if retryable else "http_nonretryable"
                ),
            )
            if not retryable:
                raise ProviderResponseError(
                    f"provider returned non-retryable HTTP {response.status_code}"
                )
            if next_retry >= MAX_RETRIES:
                raise RetryExhaustedError("provider exhausted two explicit retries")
            sleeper(float(2**next_retry))
            next_retry += 1
            continue
        try:
            decision, receipt = _extract_structured_response(
                response,
                provider=spec.provider,
                route=route,
                latency_ms=latency,
                validator=validator,
            )
        except ProviderResponseError:
            invalid = _best_effort_receipt(response, token, latency)
            invalid_outcome = (
                "cost_over_reservation"
                if Decimal(invalid.charged_usd) > Decimal(token.reserved_usd)
                else "invalid_response"
            )
            ledger.record_terminal(
                token,
                outcome=invalid_outcome,
                receipt=invalid,
                reason_code=(
                    "cost_over_reservation"
                    if invalid_outcome == "cost_over_reservation"
                    else "invalid_provider_response"
                ),
            )
            raise
        if Decimal(receipt.charged_usd) > Decimal(token.reserved_usd):
            ledger.record_terminal(
                token,
                outcome="cost_over_reservation",
                receipt=receipt,
                reason_code="cost_over_reservation",
            )
            raise ProviderResponseError(
                "provider charge exceeded its route-bounded reservation; global halt is active"
            )
        decision_sha, sidecar_sha = write_decision_sidecar(
            decision_path,
            token=token,
            decision=decision,
            receipt=receipt,
        )
        ledger.record_terminal(
            token,
            outcome="completed",
            receipt=receipt,
            reason_code="structured_output_completed",
            decision_sha256=decision_sha,
            sidecar_sha256=sidecar_sha,
        )
        return StructuredCallResult(
            decision=decision,
            receipt=receipt,
            resumed=False,
            logical_call_id=spec.logical_call_id,
            attempt_id=spec.attempt_id,
            provider=spec.provider,
            request_sha256=request_sha,
        )
    raise AssertionError("unreachable retry state")


def _resume_if_possible(
    ledger: UsageLedger,
    snapshot,
    *,
    decision_path: str | os.PathLike[str],
    validator: DecisionValidator,
) -> tuple[dict[str, Any], UsageReceipt] | None:
    if snapshot.status == "completed":
        decision, receipt, reservation_id, decision_sha, sidecar_sha = read_decision_sidecar(
            decision_path,
            binding=snapshot.binding,
            validator=validator,
        )
        terminal = snapshot.latest_terminal["payload"]
        if (
            terminal["reservation_id"] != reservation_id
            or terminal["decision_sha256"] != decision_sha
            or terminal["sidecar_sha256"] != sidecar_sha
            or terminal["receipt"] != receipt.to_dict()
        ):
            raise LedgerConflictError("completed sidecar differs from its ledger receipt")
        return decision, receipt
    if snapshot.status == "pending":
        if Path(decision_path).is_file() and not Path(decision_path).is_symlink():
            decision, receipt, reservation_id, decision_sha, sidecar_sha = read_decision_sidecar(
                decision_path,
                binding=snapshot.binding,
                validator=validator,
            )
            token = snapshot.latest_reservation
            if token is None or token.reservation_id != reservation_id:
                raise LedgerConflictError("recovery sidecar references another reservation")
            ledger.record_terminal(
                token,
                outcome="completed",
                receipt=receipt,
                reason_code="recovered_completed_sidecar",
                decision_sha256=decision_sha,
                sidecar_sha256=sidecar_sha,
            )
            return decision, receipt
        token = snapshot.latest_reservation
        if token is not None:
            ledger.record_terminal(
                token,
                outcome="uncertain_send",
                receipt=UsageReceipt(
                    http_status=None,
                    prompt_tokens=None,
                    completion_tokens=None,
                    total_tokens=None,
                    charged_usd=None,
                    latency_ms=0,
                    returned_model=None,
                    returned_provider=None,
                ),
                reason_code="resume_pending_reservation",
            )
        raise UncertainSendError(
            "pending reservation has no durable decision; duplicate send is forbidden"
        )
    if snapshot.status == "uncertain":
        raise UncertainSendError("attempt has an uncertain paid send and cannot resume")
    return None


def _request_payload(spec: StructuredCallSpec) -> dict[str, Any]:
    return {
        "model": MODEL_ID,
        "temperature": 0,
        "max_tokens": spec.max_output_tokens,
        "usage": {"include": True},
        "messages": [
            {"role": "system", "content": spec.system_prompt},
            {"role": "user", "content": spec.user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": spec.schema_name,
                "strict": True,
                "schema": dict(spec.json_schema),
            },
        },
        "provider": {
            "order": [spec.provider],
            "allow_fallbacks": False,
            "require_parameters": True,
            "data_collection": "deny",
        },
    }


def _route_bound_payload(
    request_payload: Mapping[str, Any], route: RouteSnapshot
) -> dict[str, Any]:
    payload = _json_object(request_payload, "provider request")
    provider = dict(payload["provider"])
    provider["max_price"] = {
        "prompt": float(Decimal(route.prompt_price_per_token_usd) * Decimal(1_000_000)),
        "completion": float(
            Decimal(route.completion_price_per_token_usd) * Decimal(1_000_000)
        ),
    }
    payload["provider"] = provider
    return payload


def _fetch_route(
    *, provider: str, transport: ProviderTransport, clock: Clock
) -> RouteSnapshot:
    request = ProviderHttpRequest(
        method="GET",
        url=OPENROUTER_ROUTE_URL,
        headers=(
            ("Accept", "application/json"),
            ("Accept-Encoding", "identity"),
            ("Cache-Control", "no-store"),
            ("User-Agent", DETERMINISTIC_USER_AGENT),
        ),
        body=None,
        timeout_seconds=ROUTE_TIMEOUT_SECONDS,
        max_response_bytes=MAX_ROUTE_BYTES,
    )
    try:
        response = transport.open(request)
    except Exception:
        raise ProviderRouteError("fresh provider route check failed") from None
    if (
        not isinstance(response, ProviderHttpResponse)
        or response.status_code != 200
        or response.final_url != OPENROUTER_ROUTE_URL
        or len(response.body) > MAX_ROUTE_BYTES
    ):
        raise ProviderRouteError("fresh provider route check was not exact HTTP 200")
    payload = _strict_json_object(response.body, "route response", decimal_numbers=True)
    data = payload.get("data")
    if not isinstance(data, dict) or data.get("id") != MODEL_ID:
        raise ProviderRouteError("route response model differs from the exact model")
    endpoints = data.get("endpoints")
    if not isinstance(endpoints, list):
        raise ProviderRouteError("route response lacks endpoint records")
    matches = [
        item
        for item in endpoints
        if isinstance(item, dict) and item.get("provider_name") == provider
    ]
    if len(matches) != 1:
        raise ProviderRouteError("route response lacks one exact provider")
    endpoint = matches[0]
    if endpoint.get("model_id") != MODEL_ID or endpoint.get("status") != 0:
        raise ProviderRouteError("provider route is stale or points to another model")
    parameters = endpoint.get("supported_parameters")
    pricing = endpoint.get("pricing")
    if not isinstance(parameters, list) or not all(isinstance(item, str) for item in parameters):
        raise ProviderRouteError("provider route lacks structured capabilities")
    if not isinstance(pricing, dict):
        raise ProviderRouteError("provider route lacks bounded pricing")
    prompt_price = _decimal(pricing.get("prompt"), "route prompt price")
    completion_price = _decimal(pricing.get("completion"), "route completion price")
    context_length = endpoint.get("context_length")
    max_completion = endpoint.get("max_completion_tokens")
    checked_at = _clock_timestamp(clock)
    try:
        return RouteSnapshot(
            model=MODEL_ID,
            provider=provider,
            checked_at=checked_at,
            prompt_price_per_token_usd=_decimal_text(prompt_price),
            completion_price_per_token_usd=_decimal_text(completion_price),
            context_length=context_length,
            max_completion_tokens=max_completion,
            supported_parameters=tuple(sorted(set(parameters))),
        )
    except Exception as exc:
        raise ProviderRouteError("provider route capabilities are invalid") from exc


def _extract_structured_response(
    response: ProviderHttpResponse,
    *,
    provider: str,
    route: RouteSnapshot,
    latency_ms: int,
    validator: DecisionValidator,
) -> tuple[dict[str, Any], UsageReceipt]:
    envelope = _strict_json_object(response.body, "provider response", decimal_numbers=True)
    if envelope.get("model") != MODEL_ID:
        raise ProviderResponseError("returned model differs from the exact pinned model")
    if envelope.get("provider") != provider:
        raise ProviderResponseError("returned provider differs from the pinned provider")
    choices = envelope.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ProviderResponseError("provider response choices are invalid")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ProviderResponseError("provider response lacks structured content")
    content = message["content"]
    if len(content.encode("utf-8")) > MAX_RESPONSE_BYTES:
        raise ProviderResponseError("structured decision exceeds its bound")
    decision = _strict_json_object(content.encode("utf-8"), "structured decision")
    try:
        validator(decision)
    except Exception as exc:
        raise ProviderResponseError("structured decision failed local validation") from exc
    usage = envelope.get("usage")
    if not isinstance(usage, dict):
        raise ProviderResponseError("provider response lacks usage receipt")
    prompt_tokens = _nonnegative_int(usage.get("prompt_tokens"), "prompt_tokens")
    completion_tokens = _nonnegative_int(
        usage.get("completion_tokens"), "completion_tokens"
    )
    total_tokens = _nonnegative_int(usage.get("total_tokens"), "total_tokens")
    if prompt_tokens + completion_tokens != total_tokens:
        raise ProviderResponseError("provider usage token counts do not add up")
    charged = _decimal(usage.get("cost"), "provider cost")
    receipt = UsageReceipt(
        http_status=200,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        charged_usd=_decimal_text(charged),
        latency_ms=latency_ms,
        returned_model=MODEL_ID,
        returned_provider=provider,
    )
    # Route prices bound the reservation.  The actual provider receipt remains
    # authoritative and a higher cost triggers the ledger's global halt.
    return decision, receipt


def _best_effort_receipt(
    response: ProviderHttpResponse, token: ReservationToken, latency_ms: int
) -> UsageReceipt:
    charged = token.reserved_usd
    try:
        envelope = _strict_json_object(
            response.body, "provider response", decimal_numbers=True
        )
        usage = envelope.get("usage")
        if isinstance(usage, dict):
            candidate = _decimal(usage.get("cost"), "provider cost")
            charged = _decimal_text(candidate)
    except Exception:
        pass
    return UsageReceipt(
        http_status=200,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        charged_usd=charged,
        latency_ms=latency_ms,
        returned_model=None,
        returned_provider=None,
    )


def _validate_paid_http_response(response: Any) -> None:
    if not isinstance(response, ProviderHttpResponse):
        raise ProviderUncertainError("provider transport returned an invalid response type")
    if response.final_url != OPENROUTER_API_URL:
        raise ProviderUncertainError("paid provider request was redirected")
    if len(response.body) > MAX_RESPONSE_BYTES:
        raise ProviderUncertainError("paid provider response exceeded its byte bound")


def _paid_headers(api_key: str) -> tuple[tuple[str, str], ...]:
    return (
        ("Accept", "application/json"),
        ("Accept-Encoding", "identity"),
        ("Authorization", f"Bearer {api_key}"),
        ("Cache-Control", "no-store"),
        ("Content-Type", "application/json"),
        ("User-Agent", DETERMINISTIC_USER_AGENT),
    )


def _environment_key(environment: Mapping[str, str] | None) -> str:
    source = os.environ if environment is None else environment
    value = source.get(OPENROUTER_KEY_ENV)
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 4096
        or value.strip() != value
        or any(ord(character) < 33 or ord(character) == 127 for character in value)
    ):
        raise MissingCredentialError("OpenRouter credential is absent or malformed")
    return value


def _clock_timestamp(clock: Clock) -> str:
    value = clock()
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ProviderError("provider clock must return a timezone-aware datetime")
    return value.isoformat().replace("+00:00", "Z")


def _monotonic(clock: Monotonic) -> float:
    value = clock()
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ProviderError("monotonic clock returned an invalid value")
    return float(value)


def _latency_ms(started: float, clock: Monotonic) -> int:
    elapsed = _monotonic(clock) - started
    if elapsed < 0:
        raise ProviderError("monotonic clock moved backwards")
    return min(int(round(elapsed * 1000)), 86_400_000)


def _strict_json_object(
    raw: bytes, label: str, *, decimal_numbers: bool = False
) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ProviderResponseError(f"{label} contains duplicate keys")
            value[key] = item
        return value

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique,
            parse_float=Decimal if decimal_numbers else float,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        error = ProviderRouteError if label == "route response" else ProviderResponseError
        raise error(f"{label} is not finite JSON") from None
    if not isinstance(value, dict):
        error = ProviderRouteError if label == "route response" else ProviderResponseError
        raise error(f"{label} must be a JSON object")
    return value


def _json_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProviderError(f"{label} must be a JSON object")
    try:
        encoded = _canonical_bytes(dict(value))
        decoded = json.loads(encoded)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ProviderError(f"{label} must be finite JSON") from exc
    if not isinstance(decoded, dict):
        raise ProviderError(f"{label} must be a JSON object")
    return decoded


def _canonical_bytes(value: Any) -> bytes:
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
        raise ProviderError("provider value is not finite JSON") from exc


def _decimal(value: Any, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ProviderResponseError(f"{label} is invalid")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ProviderResponseError(f"{label} is invalid") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ProviderResponseError(f"{label} is invalid")
    return parsed


def _decimal_text(value: Decimal) -> str:
    return format(value, "f")


def _nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ProviderResponseError(f"{label} is invalid")
    return value


__all__ = [
    "DETERMINISTIC_USER_AGENT",
    "MODEL_ID",
    "MissingCredentialError",
    "OPENROUTER_API_URL",
    "OPENROUTER_KEY_ENV",
    "OPENROUTER_ROUTE_URL",
    "PROVIDER_RUNTIME_VERSION",
    "ProviderError",
    "ProviderHttpRequest",
    "ProviderHttpResponse",
    "ProviderResponseError",
    "ProviderRouteError",
    "ProviderTransport",
    "ProviderUncertainError",
    "RetryExhaustedError",
    "StructuredCallResult",
    "StructuredCallSpec",
    "TransportUncertainError",
    "UrllibProviderTransport",
    "structured_json_call",
]
