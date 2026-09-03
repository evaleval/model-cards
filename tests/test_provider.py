from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import traceback
import unittest
from unittest.mock import patch

from model_cards.provider import (
    MODEL_ID,
    OPENROUTER_API_URL,
    OPENROUTER_ROUTE_URL,
    MissingCredentialError,
    ProviderError,
    ProviderExecutionBinding,
    ProviderHttpRequest,
    ProviderHttpResponse,
    ProviderResponseError,
    ProviderRouteError,
    ProviderTerminalAttemptError,
    ProviderUncertainError,
    RetryExhaustedError,
    StructuredCallSpec,
    replay_structured_json_call,
    structured_json_call,
    verify_provider_execution,
)
from model_cards.run_ledger import (
    BudgetCapError,
    LedgerConflictError,
    UncertainSendError,
    UsageLedger,
)


NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
KEY = "synthetic_openrouter_key_for_test"
PROVIDER = "Synthetic Provider"


SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {"value": {"type": "string"}},
    "required": ["value"],
}


def validator(value):
    if not isinstance(value, dict) or set(value) != {"value"}:
        raise ValueError("decision shape is invalid")
    if not isinstance(value["value"], str):
        raise ValueError("decision value is invalid")


def route_payload(
    *,
    provider: str = PROVIDER,
    model: str = MODEL_ID,
    status: int = 0,
    prompt_price: str = "0.000001",
    completion_price: str = "0.000002",
    parameters=None,
) -> bytes:
    parameters = parameters or [
        "reasoning",
        "response_format",
        "structured_outputs",
        "temperature",
        "max_tokens",
    ]
    return json.dumps(
        {
            "data": {
                "id": model,
                "endpoints": [
                    {
                        "provider_name": provider,
                        "model_id": model,
                        "status": status,
                        "supported_parameters": parameters,
                        "pricing": {
                            "prompt": prompt_price,
                            "completion": completion_price,
                        },
                        "context_length": 200_000,
                        "max_completion_tokens": 16_384,
                    }
                ],
            }
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


def success_payload(
    *,
    decision=None,
    provider: str = PROVIDER,
    model: str = MODEL_ID,
    cost: str = "0.001",
    finish_reason: str = "stop",
) -> bytes:
    if decision is None:
        decision = {"value": "normalized"}
    return json.dumps(
        {
            "model": model,
            "provider": provider,
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(decision, sort_keys=True),
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "cost": cost,
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()


class FixtureTransport:
    def __init__(self, paid_outcomes, *, routes=None):
        self.paid_outcomes = list(paid_outcomes)
        self.routes = list(routes or [])
        self.requests: list[ProviderHttpRequest] = []
        self.route_count = 0
        self.paid_count = 0

    def open(self, request: ProviderHttpRequest) -> ProviderHttpResponse:
        self.requests.append(request)
        if request.method == "GET":
            self.route_count += 1
            body = self.routes.pop(0) if self.routes else route_payload()
            if isinstance(body, BaseException):
                raise body
            return ProviderHttpResponse(200, OPENROUTER_ROUTE_URL, body=body)
        self.paid_count += 1
        if not self.paid_outcomes:
            raise AssertionError("unexpected paid call")
        outcome = self.paid_outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        status, body = outcome
        return ProviderHttpResponse(status, OPENROUTER_API_URL, body=body)


class Monotonic:
    def __init__(self):
        self.value = 100.0

    def __call__(self):
        self.value += 0.05
        return self.value


class ProviderRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.ledger_path = self.root / "usage.jsonl"
        self.decision_path = self.root / "decision.json"

    def spec(self, **overrides) -> StructuredCallSpec:
        values = {
            "logical_call_id": "extract.target.001",
            "attempt_id": "attempt.001",
            "provider": PROVIDER,
            "schema_name": "extraction_result",
            "json_schema": SCHEMA,
            "system_prompt": "System instruction that is never persisted.",
            "user_prompt": "PRIVATE PROMPT SENTINEL that is never persisted.",
            "max_output_tokens": 256,
            "context_metadata": {"stage": "extraction", "target_id": "synthetic-model"},
        }
        values.update(overrides)
        return StructuredCallSpec(**values)

    def call(
        self,
        transport,
        *,
        spec=None,
        environment=None,
        sleeper=None,
        ledger_path=None,
        decision_path=None,
    ):
        return structured_json_call(
            spec or self.spec(),
            ledger_path=ledger_path or self.ledger_path,
            decision_path=decision_path or self.decision_path,
            validator=validator,
            environment={"OPENROUTER_API_KEY": KEY}
            if environment is None
            else environment,
            transport=transport,
            clock=lambda: NOW,
            monotonic=Monotonic(),
            sleeper=sleeper or (lambda _seconds: None),
        )

    def terminal_payload(self, ledger_path=None):
        events = [
            json.loads(line)
            for line in (ledger_path or self.ledger_path).read_text().splitlines()
        ]
        return next(
            event["payload"]
            for event in reversed(events)
            if event["event"] == "reservation_terminal"
        )

    def test_success_uses_exact_model_strict_schema_zero_temperature_and_one_provider(self) -> None:
        transport = FixtureTransport([(200, success_payload())])
        result = self.call(transport)
        self.assertFalse(result.resumed)
        self.assertEqual({"value": "normalized"}, result.decision)
        self.assertEqual(MODEL_ID, result.receipt.returned_model)
        self.assertEqual(PROVIDER, result.receipt.returned_provider)
        self.assertEqual(1, transport.route_count)
        self.assertEqual(1, transport.paid_count)
        paid = next(item for item in transport.requests if item.method == "POST")
        payload = json.loads(paid.body)
        self.assertEqual(MODEL_ID, payload["model"])
        self.assertEqual(0, payload["temperature"])
        self.assertEqual(
            {"effort": "minimal", "exclude": True}, payload["reasoning"]
        )
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertEqual([PROVIDER], payload["provider"]["order"])
        self.assertIs(payload["provider"]["allow_fallbacks"], False)
        self.assertIs(payload["provider"]["require_parameters"], True)
        self.assertIn("max_price", payload["provider"])
        self.assertEqual(f"Bearer {KEY}", paid.header("Authorization"))
        self.assertNotIn(KEY, repr(paid))
        persisted = self.ledger_path.read_text() + self.decision_path.read_text()
        self.assertNotIn(KEY, persisted)
        self.assertNotIn("PRIVATE PROMPT SENTINEL", persisted)
        self.assertNotIn("System instruction", persisted)

    def test_execution_binding_round_trips_and_replays_without_mutation(self) -> None:
        first = self.call(FixtureTransport([(200, success_payload())]))
        serialized = first.execution.to_dict()
        self.assertEqual(
            serialized,
            ProviderExecutionBinding.from_dict(serialized).to_dict(),
        )
        ledger_before = self.ledger_path.read_bytes()
        decision_before = self.decision_path.read_bytes()
        ledger_stat_before = self.ledger_path.stat()
        decision_stat_before = self.decision_path.stat()

        replayed = replay_structured_json_call(
            self.spec(),
            ledger_path=self.ledger_path,
            decision_path=self.decision_path,
            validator=validator,
        )

        self.assertTrue(replayed.resumed)
        self.assertEqual(first.decision, replayed.decision)
        self.assertEqual(serialized, replayed.execution.to_dict())
        self.assertEqual(ledger_before, self.ledger_path.read_bytes())
        self.assertEqual(decision_before, self.decision_path.read_bytes())
        self.assertEqual(ledger_stat_before.st_mode, self.ledger_path.stat().st_mode)
        self.assertEqual(
            ledger_stat_before.st_mtime_ns,
            self.ledger_path.stat().st_mtime_ns,
        )
        self.assertEqual(
            decision_stat_before.st_mtime_ns,
            self.decision_path.stat().st_mtime_ns,
        )

    def test_replay_missing_ledger_does_not_create_one(self) -> None:
        missing = self.root / "missing-usage.jsonl"
        with self.assertRaisesRegex(ProviderError, "ledger is invalid"):
            replay_structured_json_call(
                self.spec(),
                ledger_path=missing,
                decision_path=self.decision_path,
                validator=validator,
            )
        self.assertFalse(missing.exists())

    def test_execution_verifier_rejects_copied_sidecar_at_another_path(self) -> None:
        first = self.call(FixtureTransport([(200, success_payload())]))
        copied_dir = self.root / "copied-decisions"
        copied_dir.mkdir()
        copied = copied_dir / self.decision_path.name
        copied.write_bytes(self.decision_path.read_bytes())
        with self.assertRaisesRegex(ProviderError, "path differs"):
            verify_provider_execution(
                first.execution,
                ledger_path=self.ledger_path,
                decision_dir=copied_dir,
                validator=validator,
            )

    def test_execution_binding_detects_manifest_tampering(self) -> None:
        first = self.call(FixtureTransport([(200, success_payload())]))
        tampered = first.execution.to_dict()
        tampered["decision_sha256"] = "0" * 64
        with self.assertRaisesRegex(ProviderError, "digest is inconsistent"):
            ProviderExecutionBinding.from_dict(tampered)

    def test_absent_key_fails_before_route_reservation_or_send(self) -> None:
        transport = FixtureTransport([])
        with self.assertRaises(MissingCredentialError):
            self.call(transport, environment={})
        self.assertEqual([], transport.requests)
        self.assertEqual(0, UsageLedger(self.ledger_path).audit_state()["paid_calls"])

    def test_completed_resume_needs_no_key_route_or_second_send(self) -> None:
        first = FixtureTransport([(200, success_payload())])
        initial = self.call(first)
        forbidden = FixtureTransport([])
        resumed = self.call(forbidden, environment={})
        self.assertTrue(resumed.resumed)
        self.assertEqual(initial.decision, resumed.decision)
        self.assertEqual([], forbidden.requests)
        self.assertEqual(1, UsageLedger(self.ledger_path).audit_state()["paid_calls"])

    def test_wrong_model_stale_provider_or_missing_capability_route_fails_before_reservation(self) -> None:
        cases = [
            route_payload(model="wrong/model"),
            route_payload(status=1),
            route_payload(parameters=["temperature", "max_tokens"]),
            route_payload(provider="Other Provider"),
        ]
        for index, route in enumerate(cases):
            with self.subTest(index=index):
                ledger = self.root / f"route-{index}.jsonl"
                decision = self.root / f"route-{index}.json"
                transport = FixtureTransport([], routes=[route])
                with self.assertRaises(ProviderRouteError):
                    structured_json_call(
                        self.spec(
                            logical_call_id=f"route.check.{index}",
                            attempt_id=f"route-attempt-{index}",
                        ),
                        ledger_path=ledger,
                        decision_path=decision,
                        validator=validator,
                        environment={"OPENROUTER_API_KEY": KEY},
                        transport=transport,
                        clock=lambda: NOW,
                    )
                self.assertEqual(0, UsageLedger(ledger).audit_state()["paid_calls"])
                self.assertEqual(0, transport.paid_count)

        marker = "PRIVATE ROUTE TRANSPORT SENTINEL"
        failed_route = FixtureTransport([], routes=[RuntimeError(marker)])
        with self.assertRaises(ProviderRouteError) as caught:
            self.call(failed_route)
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn(marker, str(caught.exception))
        self.assertNotIn(marker, "".join(traceback.format_exception(caught.exception)))

    def test_returned_model_or_provider_drift_is_terminal_without_fallback(self) -> None:
        cases = [
            (success_payload(model="fallback/model"), "returned_model_mismatch"),
            (
                success_payload(provider="Fallback Provider"),
                "returned_provider_mismatch",
            ),
        ]
        for index, (body, expected_reason) in enumerate(cases):
            with self.subTest(index=index):
                ledger = self.root / f"drift-{index}.jsonl"
                decision = self.root / f"drift-{index}.json"
                transport = FixtureTransport([(200, body)])
                with self.assertRaises(ProviderResponseError) as caught:
                    structured_json_call(
                        self.spec(
                            logical_call_id=f"drift.call.{index}",
                            attempt_id=f"drift-attempt-{index}",
                        ),
                        ledger_path=ledger,
                        decision_path=decision,
                        validator=validator,
                        environment={"OPENROUTER_API_KEY": KEY},
                        transport=transport,
                        clock=lambda: NOW,
                        monotonic=Monotonic(),
                    )
                self.assertEqual(expected_reason, caught.exception.reason_code)
                self.assertEqual(
                    expected_reason, self.terminal_payload(ledger)["reason_code"]
                )
                self.assertEqual(1, transport.paid_count)
                replay = FixtureTransport([])
                with self.assertRaises(ProviderTerminalAttemptError) as terminal:
                    structured_json_call(
                        self.spec(
                            logical_call_id=f"drift.call.{index}",
                            attempt_id=f"drift-attempt-{index}",
                        ),
                        ledger_path=ledger,
                        decision_path=decision,
                        validator=validator,
                        environment={},
                        transport=replay,
                        clock=lambda: NOW,
                    )
                self.assertEqual(expected_reason, terminal.exception.reason_code)
                self.assertEqual([], replay.requests)
                self.assertFalse(decision.exists())

    def test_finish_reason_rejects_truncation_before_parsing_or_persisting_content(self) -> None:
        marker = "PRIVATE PROVIDER RESPONSE SENTINEL"
        transport = FixtureTransport(
            [
                (
                    200,
                    success_payload(
                        decision={"value": marker}, finish_reason="length"
                    ),
                )
            ]
        )
        with self.assertRaises(ProviderResponseError) as caught:
            self.call(transport)
        self.assertEqual("finish_reason_length", caught.exception.reason_code)
        terminal = self.terminal_payload()
        self.assertEqual("finish_reason_length", terminal["reason_code"])
        self.assertEqual("invalid_response", terminal["outcome"])
        self.assertEqual(
            {
                "prompt_tokens": 100,
                "completion_tokens": 20,
                "total_tokens": 120,
                "returned_model": MODEL_ID,
                "returned_provider": PROVIDER,
            },
            {
                name: terminal["receipt"][name]
                for name in (
                    "prompt_tokens",
                    "completion_tokens",
                    "total_tokens",
                    "returned_model",
                    "returned_provider",
                )
            },
        )
        persisted = self.ledger_path.read_text()
        self.assertNotIn(marker, persisted)
        self.assertFalse(self.decision_path.exists())

    def test_nonstop_finish_reasons_have_one_static_privacy_safe_code(self) -> None:
        for index, finish_reason in enumerate(("content_filter", "error", None)):
            with self.subTest(finish_reason=finish_reason):
                ledger = self.root / f"finish-{index}.jsonl"
                decision = self.root / f"finish-{index}.json"
                body = json.loads(success_payload())
                body["choices"][0]["finish_reason"] = finish_reason
                transport = FixtureTransport(
                    [
                        (
                            200,
                            json.dumps(
                                body, sort_keys=True, separators=(",", ":")
                            ).encode(),
                        )
                    ]
                )
                with self.assertRaises(ProviderResponseError) as caught:
                    self.call(
                        transport,
                        spec=self.spec(
                            logical_call_id=f"finish.call.{index}",
                            attempt_id=f"finish-attempt-{index}",
                        ),
                        ledger_path=ledger,
                        decision_path=decision,
                    )
                self.assertEqual("finish_reason_nonstop", caught.exception.reason_code)
                self.assertEqual(
                    "finish_reason_nonstop",
                    self.terminal_payload(ledger)["reason_code"],
                )

    def test_response_validation_failures_have_static_ledger_codes(self) -> None:
        raw_marker = "PRIVATE RAW BODY SENTINEL"
        validator_marker = "PRIVATE VALIDATOR SENTINEL"
        invalid_json = ('{"private_raw_body":"' + raw_marker + '"').encode()
        invalid_choices = json.loads(success_payload())
        invalid_choices["choices"] = []
        invalid_decision_json = json.loads(success_payload())
        invalid_decision_json["choices"][0]["message"]["content"] = "["
        invalid_decision_shape = json.loads(
            success_payload(decision={"wrong": validator_marker})
        )
        missing_usage = json.loads(success_payload())
        missing_usage.pop("usage")
        invalid_prompt_tokens = json.loads(success_payload())
        invalid_prompt_tokens["usage"]["prompt_tokens"] = -1
        mismatched_tokens = json.loads(success_payload())
        mismatched_tokens["usage"]["total_tokens"] = 999
        invalid_cost = json.loads(success_payload())
        invalid_cost["usage"]["cost"] = "not-a-number"
        cases = [
            (invalid_json, "response_json_invalid"),
            (invalid_choices, "response_choices_invalid"),
            (invalid_decision_json, "structured_json_invalid"),
            (invalid_decision_shape, "structured_decision_invalid"),
            (missing_usage, "usage_missing"),
            (invalid_prompt_tokens, "prompt_tokens_invalid"),
            (mismatched_tokens, "usage_total_mismatch"),
            (invalid_cost, "cost_invalid"),
        ]
        for index, (value, expected_reason) in enumerate(cases):
            with self.subTest(reason=expected_reason):
                ledger = self.root / f"invalid-{index}.jsonl"
                decision = self.root / f"invalid-{index}.json"
                body = (
                    value
                    if isinstance(value, bytes)
                    else json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
                )
                transport = FixtureTransport([(200, body)])
                with self.assertRaises(ProviderResponseError) as caught:
                    self.call(
                        transport,
                        spec=self.spec(
                            logical_call_id=f"invalid.call.{index}",
                            attempt_id=f"invalid-attempt-{index}",
                        ),
                        ledger_path=ledger,
                        decision_path=decision,
                    )
                self.assertEqual(expected_reason, caught.exception.reason_code)
                self.assertEqual(
                    expected_reason, self.terminal_payload(ledger)["reason_code"]
                )
                self.assertIsNone(caught.exception.__context__)
                rendered = "".join(traceback.format_exception(caught.exception))
                for marker in (raw_marker, validator_marker):
                    self.assertNotIn(marker, str(caught.exception))
                    self.assertNotIn(marker, rendered)
                    self.assertNotIn(marker, ledger.read_text())
                self.assertFalse(decision.exists())

    def test_response_reason_code_vocabulary_is_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "not registered"):
            ProviderResponseError("static message", reason_code="runtime_supplied_detail")
        with self.assertRaisesRegex(ValueError, "not registered"):
            ProviderTerminalAttemptError(
                "static message", reason_code="future_unclassified_failure"
            )

    def test_only_429_and_5xx_get_two_logged_retries_with_fresh_routes(self) -> None:
        sleeps: list[float] = []
        transport = FixtureTransport(
            [(429, b"{}"), (503, b"{}"), (200, success_payload())]
        )
        result = self.call(transport, sleeper=sleeps.append)
        self.assertEqual({"value": "normalized"}, result.decision)
        self.assertEqual(3, transport.route_count)
        self.assertEqual(3, transport.paid_count)
        self.assertEqual([1.0, 2.0], sleeps)
        state = UsageLedger(self.ledger_path).audit_state()
        self.assertEqual(3, state["paid_calls"])

        exhausted_ledger = self.root / "exhausted.jsonl"
        exhausted_decision = self.root / "exhausted.json"
        exhausted = FixtureTransport([(500, b"{}"), (502, b"{}"), (599, b"{}")])
        with self.assertRaises(RetryExhaustedError):
            structured_json_call(
                self.spec(logical_call_id="retry.exhausted", attempt_id="attempt.exhausted"),
                ledger_path=exhausted_ledger,
                decision_path=exhausted_decision,
                validator=validator,
                environment={"OPENROUTER_API_KEY": KEY},
                transport=exhausted,
                clock=lambda: NOW,
                monotonic=Monotonic(),
                sleeper=lambda _seconds: None,
            )
        self.assertEqual(3, exhausted.paid_count)
        self.assertEqual(3, exhausted.route_count)
        replay = FixtureTransport([])
        with self.assertRaises(ProviderTerminalAttemptError) as caught:
            structured_json_call(
                self.spec(
                    logical_call_id="retry.exhausted",
                    attempt_id="attempt.exhausted",
                ),
                ledger_path=exhausted_ledger,
                decision_path=exhausted_decision,
                validator=validator,
                environment={},
                transport=replay,
                clock=lambda: NOW,
            )
        self.assertEqual("retry_exhausted", caught.exception.reason_code)
        self.assertEqual([], replay.requests)

    def test_nonretryable_4xx_is_one_terminal_send(self) -> None:
        sleeps: list[float] = []
        transport = FixtureTransport([(400, b"{}")])
        with self.assertRaises(ProviderResponseError) as caught:
            self.call(transport, sleeper=sleeps.append)
        self.assertEqual("http_bad_request", caught.exception.reason_code)
        self.assertEqual(1, transport.route_count)
        self.assertEqual(1, transport.paid_count)
        self.assertEqual([], sleeps)

        replay = FixtureTransport([])
        with self.assertRaises(ProviderTerminalAttemptError):
            self.call(replay)
        self.assertEqual([], replay.requests)

        self.decision_path.write_text("{}")
        with self.assertRaises(LedgerConflictError):
            self.call(FixtureTransport([]))

    def test_auth_payment_and_endpoint_http_failures_have_fatal_codes(self) -> None:
        cases = {
            401: "http_authentication_failed",
            402: "http_payment_required",
            403: "http_authentication_failed",
            404: "http_endpoint_not_found",
            409: "http_nonretryable",
            422: "http_unprocessable_request",
        }
        for status, reason_code in cases.items():
            with self.subTest(status=status):
                ledger = self.root / f"http-{status}.jsonl"
                decision = self.root / f"http-{status}.json"
                transport = FixtureTransport([(status, b"{}")])
                with self.assertRaises(ProviderResponseError) as caught:
                    structured_json_call(
                        self.spec(
                            logical_call_id=f"http.status.{status}",
                            attempt_id=f"http-attempt-{status}",
                        ),
                        ledger_path=ledger,
                        decision_path=decision,
                        validator=validator,
                        environment={"OPENROUTER_API_KEY": KEY},
                        transport=transport,
                        clock=lambda: NOW,
                        monotonic=Monotonic(),
                    )
                self.assertEqual(reason_code, caught.exception.reason_code)
                self.assertEqual(reason_code, self.terminal_payload(ledger)["reason_code"])

    def test_timeout_is_uncertain_and_never_sent_again(self) -> None:
        transport = FixtureTransport([TimeoutError(f"timeout {KEY}")])
        with self.assertRaises(ProviderUncertainError) as caught:
            self.call(transport)
        self.assertNotIn(KEY, str(caught.exception))
        self.assertIsNone(caught.exception.__context__)
        self.assertNotIn(KEY, "".join(traceback.format_exception(caught.exception)))
        self.assertEqual(1, transport.paid_count)
        state = UsageLedger(self.ledger_path).audit_state()
        self.assertGreater(Decimal(state["committed_usd"]), Decimal("0"))
        forbidden = FixtureTransport([])
        with self.assertRaises(UncertainSendError):
            self.call(forbidden)
        self.assertEqual([], forbidden.requests)

    def test_duplicate_request_and_logical_bindings_fail_before_second_send(self) -> None:
        first = FixtureTransport([(400, b"{}")])
        with self.assertRaises(ProviderResponseError):
            self.call(first)
        duplicate = FixtureTransport([])
        with self.assertRaises(LedgerConflictError):
            self.call(
                duplicate,
                spec=self.spec(
                    logical_call_id="different.logical.call",
                    attempt_id="different-attempt",
                ),
            )
        self.assertEqual([], duplicate.requests)

        changed = FixtureTransport([])
        with self.assertRaises(LedgerConflictError):
            self.call(
                changed,
                spec=self.spec(
                    attempt_id="changed-request-attempt",
                    user_prompt="A different semantic request.",
                ),
            )
        self.assertEqual([], changed.requests)

    def test_provider_change_requires_new_attempt_and_preserves_semantic_request(self) -> None:
        first = FixtureTransport([(400, b"{}")])
        with self.assertRaises(ProviderResponseError):
            self.call(first)
        same_attempt = FixtureTransport([])
        with self.assertRaises(LedgerConflictError):
            self.call(same_attempt, spec=self.spec(provider="Other Provider"))
        self.assertEqual([], same_attempt.requests)

        second = FixtureTransport(
            [(200, success_payload(provider="Other Provider"))],
            routes=[route_payload(provider="Other Provider")],
        )
        result = self.call(
            second,
            spec=self.spec(attempt_id="attempt.002", provider="Other Provider"),
        )
        self.assertEqual("Other Provider", result.provider)
        self.assertEqual(1, second.paid_count)

    def test_runtime_version_is_bound_into_semantic_request_replay(self) -> None:
        first = FixtureTransport([(200, success_payload())])
        completed = self.call(first)
        self.assertFalse(completed.resumed)
        forbidden = FixtureTransport([])
        with patch(
            "model_cards.provider.PROVIDER_RUNTIME_VERSION",
            "openrouter-structured-provider/future-test",
        ), self.assertRaises(LedgerConflictError):
            self.call(forbidden)
        self.assertEqual([], forbidden.requests)

    def test_cost_over_reservation_activates_global_halt(self) -> None:
        transport = FixtureTransport([(200, success_payload(cost="10"))])
        with self.assertRaisesRegex(ProviderResponseError, "global halt"):
            self.call(transport)
        self.assertTrue(UsageLedger(self.ledger_path).audit_state()["global_halt"])
        next_transport = FixtureTransport([(200, success_payload())])
        with self.assertRaises(BudgetCapError):
            self.call(
                next_transport,
                spec=self.spec(
                    logical_call_id="next.after.halt",
                    attempt_id="attempt.after.halt",
                    user_prompt="Different request after global halt.",
                ),
                decision_path=self.root / "next.json",
            )
        self.assertEqual(0, next_transport.paid_count)

    def test_invalid_decision_cannot_hide_cost_over_reservation(self) -> None:
        transport = FixtureTransport(
            [(200, success_payload(decision={"wrong": "shape"}, cost="10"))]
        )
        with self.assertRaises(ProviderResponseError) as caught:
            self.call(transport)
        self.assertEqual("cost_over_reservation", caught.exception.reason_code)
        self.assertIsNone(caught.exception.__context__)
        self.assertTrue(UsageLedger(self.ledger_path).audit_state()["global_halt"])

    def test_sidecar_tamper_fails_without_key_or_send(self) -> None:
        self.call(FixtureTransport([(200, success_payload())]))
        raw = json.loads(self.decision_path.read_text())
        raw["decision"]["value"] = "tampered"
        self.decision_path.write_text(
            json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n"
        )
        forbidden = FixtureTransport([])
        with self.assertRaises(Exception):
            self.call(forbidden, environment={})
        self.assertEqual([], forbidden.requests)


if __name__ == "__main__":
    unittest.main()
