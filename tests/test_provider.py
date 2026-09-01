from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.provider import (
    MODEL_ID,
    OPENROUTER_API_URL,
    OPENROUTER_ROUTE_URL,
    MissingCredentialError,
    ProviderHttpRequest,
    ProviderHttpResponse,
    ProviderResponseError,
    ProviderRouteError,
    ProviderUncertainError,
    RetryExhaustedError,
    StructuredCallSpec,
    structured_json_call,
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
) -> bytes:
    decision = decision or {"value": "normalized"}
    return json.dumps(
        {
            "model": model,
            "provider": provider,
            "choices": [
                {
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

    def test_returned_model_or_provider_drift_is_terminal_without_fallback(self) -> None:
        cases = [
            success_payload(model="fallback/model"),
            success_payload(provider="Fallback Provider"),
        ]
        for index, body in enumerate(cases):
            with self.subTest(index=index):
                ledger = self.root / f"drift-{index}.jsonl"
                decision = self.root / f"drift-{index}.json"
                transport = FixtureTransport([(200, body)])
                with self.assertRaises(ProviderResponseError):
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
                self.assertEqual(1, transport.paid_count)
                self.assertFalse(decision.exists())

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

    def test_nonretryable_4xx_is_one_terminal_send(self) -> None:
        sleeps: list[float] = []
        transport = FixtureTransport([(400, b"{}")])
        with self.assertRaises(ProviderResponseError):
            self.call(transport, sleeper=sleeps.append)
        self.assertEqual(1, transport.route_count)
        self.assertEqual(1, transport.paid_count)
        self.assertEqual([], sleeps)

    def test_timeout_is_uncertain_and_never_sent_again(self) -> None:
        transport = FixtureTransport([TimeoutError(f"timeout {KEY}")])
        with self.assertRaises(ProviderUncertainError) as caught:
            self.call(transport)
        self.assertNotIn(KEY, str(caught.exception))
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
