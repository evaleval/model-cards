from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from model_cards.run_ledger import (
    EXACT_MODEL,
    GLOBAL_PAID_CALL_CAP,
    GLOBAL_USD_CAP,
    AttemptBinding,
    BudgetCapError,
    LedgerConflictError,
    LedgerIntegrityError,
    RouteSnapshot,
    UsageLedger,
    UsageReceipt,
    json_sha256,
    path_sha256,
    read_decision_sidecar,
    write_decision_sidecar,
)


NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=timezone.utc)
PROVIDER = "Synthetic Provider"
PARAMETERS = (
    "max_tokens",
    "response_format",
    "structured_outputs",
    "temperature",
)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def binding(
    root: Path,
    *,
    logical_call_id: str = "logical.call.001",
    attempt_id: str = "attempt.001",
    provider: str = PROVIDER,
    request_sha256: str | None = None,
    metadata=None,
) -> AttemptBinding:
    return AttemptBinding(
        logical_call_id=logical_call_id,
        attempt_id=attempt_id,
        model=EXACT_MODEL,
        provider=provider,
        request_sha256=request_sha256 or digest("request-one"),
        schema_sha256=json_sha256(
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            }
        ),
        sidecar_path_sha256=path_sha256(root / "decision.json"),
        context_metadata=metadata
        if metadata is not None
        else {"stage": "extraction", "target_id": "synthetic-model"},
    )


def route(
    *,
    provider: str = PROVIDER,
    checked_at: datetime = NOW,
    prompt_price: str = "0.1",
    completion_price: str = "0.2",
) -> RouteSnapshot:
    return RouteSnapshot(
        model=EXACT_MODEL,
        provider=provider,
        checked_at=checked_at.isoformat().replace("+00:00", "Z"),
        prompt_price_per_token_usd=prompt_price,
        completion_price_per_token_usd=completion_price,
        context_length=4096,
        max_completion_tokens=1024,
        supported_parameters=PARAMETERS,
    )


def receipt(
    *,
    status: int = 400,
    charge: str | None = "0.4",
    returned_model: str | None = None,
    returned_provider: str | None = None,
) -> UsageReceipt:
    return UsageReceipt(
        http_status=status,
        prompt_tokens=None,
        completion_tokens=None,
        total_tokens=None,
        charged_usd=charge,
        latency_ms=12,
        returned_model=returned_model,
        returned_provider=returned_provider,
    )


class UsageLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / "usage.jsonl"
        self.ledger = UsageLedger(self.path, clock=lambda: NOW)

    def test_exact_global_caps_and_route_bound_reservation_accounting(self) -> None:
        self.assertEqual(Decimal("25"), GLOBAL_USD_CAP)
        self.assertEqual(300, GLOBAL_PAID_CALL_CAP)
        item = binding(self.root)
        self.assertEqual("manifested", self.ledger.begin_attempt(item).status)
        token = self.ledger.reserve(
            item,
            retry_index=0,
            route=route(),
            input_token_ceiling=2,
            output_token_ceiling=3,
        )
        self.assertEqual("0.8", token.reserved_usd)
        pending = self.ledger.audit_state()
        self.assertEqual(1, pending["paid_calls"])
        self.assertEqual("0.8", pending["committed_usd"])
        self.ledger.record_terminal(
            token,
            outcome="terminal_http_error",
            receipt=receipt(),
            reason_code="http_400",
        )
        final = self.ledger.audit_state()
        self.assertEqual("0.4", final["committed_usd"])
        self.assertEqual("failed", self.ledger.inspect(item).status)
        self.assertEqual(
            {
                "paid_calls": 1,
                "committed_usd": "0.4",
                "global_halt": False,
                "attempt_count": 1,
                "receipt_count": 1,
                "token_receipt_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "retry_count": 0,
                "latency_ms": 12,
                "max_latency_ms": 12,
                "providers": [PROVIDER],
                "attempt_statuses": {"failed": 1},
                "terminal_outcomes": {"terminal_http_error": 1},
            },
            self.ledger.audit_metrics(),
        )

    def test_manifest_precedes_reservation_and_route_must_be_fresh_and_pinned(self) -> None:
        item = binding(self.root)
        with self.assertRaisesRegex(LedgerConflictError, "manifest"):
            self.ledger.reserve(
                item,
                retry_index=0,
                route=route(),
                input_token_ceiling=1,
                output_token_ceiling=1,
            )
        self.ledger.begin_attempt(item)
        with self.assertRaisesRegex(LedgerConflictError, "stale"):
            self.ledger.reserve(
                item,
                retry_index=0,
                route=route(checked_at=NOW - timedelta(seconds=61)),
                input_token_ceiling=1,
                output_token_ceiling=1,
            )
        with self.assertRaisesRegex(LedgerConflictError, "differs"):
            self.ledger.reserve(
                item,
                retry_index=0,
                route=route(provider="Other Provider"),
                input_token_ceiling=1,
                output_token_ceiling=1,
            )
        self.assertEqual(0, self.ledger.audit_state()["paid_calls"])

    def test_metadata_is_bounded_portable_and_immutable(self) -> None:
        item = binding(self.root)
        with self.assertRaises(TypeError):
            item.context_metadata["stage"] = "changed"
        for metadata in (
            {"prompt_excerpt": "do not persist this"},
            {"artifact": "/private/tmp/local.json"},
            {"stage": "x" * 257},
            {f"key_{index}": index for index in range(25)},
        ):
            with self.subTest(metadata=next(iter(metadata))):
                with self.assertRaises(LedgerIntegrityError):
                    binding(self.root, metadata=metadata)

    def test_request_logical_and_attempt_identity_conflicts_are_rejected(self) -> None:
        original = binding(self.root)
        self.ledger.begin_attempt(original)
        with self.assertRaises(LedgerConflictError):
            self.ledger.begin_attempt(
                binding(
                    self.root,
                    logical_call_id="different.logical",
                    attempt_id="different.attempt",
                    request_sha256=original.request_sha256,
                )
            )
        with self.assertRaises(LedgerConflictError):
            self.ledger.begin_attempt(
                binding(
                    self.root,
                    attempt_id="changed.request",
                    request_sha256=digest("another semantic request"),
                )
            )
        with self.assertRaises(LedgerConflictError):
            self.ledger.begin_attempt(
                binding(self.root, provider="Other Provider")
            )

        explicit_new_attempt = binding(
            self.root,
            attempt_id="attempt.002",
            provider="Other Provider",
            request_sha256=original.request_sha256,
        )
        self.assertEqual(
            "manifested", self.ledger.begin_attempt(explicit_new_attempt).status
        )

    def test_usd_cap_counts_pending_reservations_fail_closed(self) -> None:
        first = binding(self.root)
        self.ledger.begin_attempt(first)
        self.ledger.reserve(
            first,
            retry_index=0,
            route=route(prompt_price="10", completion_price="15"),
            input_token_ceiling=1,
            output_token_ceiling=1,
        )
        second = binding(
            self.root,
            logical_call_id="logical.call.002",
            attempt_id="attempt.002",
            request_sha256=digest("request-two"),
        )
        self.ledger.begin_attempt(second)
        with self.assertRaisesRegex(BudgetCapError, "USD cap"):
            self.ledger.reserve(
                second,
                retry_index=0,
                route=route(prompt_price="0.1", completion_price="0.1"),
                input_token_ceiling=1,
                output_token_ceiling=1,
            )
        self.assertEqual("25", self.ledger.audit_state()["committed_usd"])

    def test_paid_call_cap_counts_each_explicit_retry(self) -> None:
        item = binding(self.root)
        self.ledger.begin_attempt(item)
        with patch("model_cards.run_ledger.GLOBAL_PAID_CALL_CAP", 2):
            first = self.ledger.reserve(
                item,
                retry_index=0,
                route=route(prompt_price="0", completion_price="0"),
                input_token_ceiling=1,
                output_token_ceiling=1,
            )
            self.ledger.record_terminal(
                first,
                outcome="retryable_http_error",
                receipt=receipt(status=429, charge="0"),
                reason_code="http_429",
            )
            second = self.ledger.reserve(
                item,
                retry_index=1,
                route=route(prompt_price="0", completion_price="0"),
                input_token_ceiling=1,
                output_token_ceiling=1,
            )
            self.ledger.record_terminal(
                second,
                outcome="retryable_http_error",
                receipt=receipt(status=503, charge="0"),
                reason_code="http_503",
            )
            with self.assertRaisesRegex(BudgetCapError, "paid-call cap"):
                self.ledger.reserve(
                    item,
                    retry_index=2,
                    route=route(prompt_price="0", completion_price="0"),
                    input_token_ceiling=1,
                    output_token_ceiling=1,
                )
        self.assertEqual(2, self.ledger.audit_state()["paid_calls"])
        metrics = self.ledger.audit_metrics()
        self.assertEqual(1, metrics["retry_count"])
        self.assertEqual(2, metrics["receipt_count"])
        self.assertEqual({"retryable_http_error": 2}, metrics["terminal_outcomes"])

    def test_truncation_duplicate_event_identity_and_unknown_fields_fail_replay(self) -> None:
        truncated_path = self.root / "truncated.jsonl"
        UsageLedger(truncated_path, clock=lambda: NOW).begin_attempt(binding(self.root))
        with truncated_path.open("ab") as handle:
            handle.write(b'{"partial"')
        with self.assertRaisesRegex(LedgerIntegrityError, "truncated"):
            UsageLedger(truncated_path).audit_state()

        duplicate_path = self.root / "duplicate.jsonl"
        duplicate = UsageLedger(duplicate_path, clock=lambda: NOW)
        duplicate_item = binding(
            self.root,
            logical_call_id="duplicate.logical",
            attempt_id="duplicate.attempt",
            request_sha256=digest("duplicate-request"),
        )
        duplicate.begin_attempt(duplicate_item)
        duplicate.reserve(
            duplicate_item,
            retry_index=0,
            route=route(),
            input_token_ceiling=1,
            output_token_ceiling=1,
        )
        rows = [json.loads(line) for line in duplicate_path.read_text().splitlines()]
        rows[1]["event_id"] = rows[0]["event_id"]
        duplicate_path.write_text(
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in rows
            )
        )
        with self.assertRaises(LedgerIntegrityError):
            duplicate.audit_state()

        closed_path = self.root / "closed.jsonl"
        closed = UsageLedger(closed_path, clock=lambda: NOW)
        closed.begin_attempt(
            binding(
                self.root,
                logical_call_id="closed.logical",
                attempt_id="closed.attempt",
                request_sha256=digest("closed-request"),
            )
        )
        row = json.loads(closed_path.read_text())
        row["unexpected"] = True
        closed_path.write_text(
            json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        )
        with self.assertRaises(LedgerIntegrityError):
            closed.audit_state()

    def test_sidecar_is_canonical_bound_and_tamper_evident(self) -> None:
        item = binding(self.root)
        self.ledger.begin_attempt(item)
        token = self.ledger.reserve(
            item,
            retry_index=0,
            route=route(prompt_price="0.001", completion_price="0.001"),
            input_token_ceiling=10,
            output_token_ceiling=10,
        )
        completed_receipt = UsageReceipt(
            http_status=200,
            prompt_tokens=8,
            completion_tokens=2,
            total_tokens=10,
            charged_usd="0.01",
            latency_ms=21,
            returned_model=EXACT_MODEL,
            returned_provider=PROVIDER,
        )
        decision_path = self.root / "decision.json"
        decision_sha, sidecar_sha = write_decision_sidecar(
            decision_path,
            token=token,
            decision={"value": "normalized"},
            receipt=completed_receipt,
        )
        restored = read_decision_sidecar(
            decision_path,
            binding=item,
            validator=lambda value: None
            if set(value) == {"value"}
            else (_ for _ in ()).throw(ValueError("invalid")),
        )
        self.assertEqual({"value": "normalized"}, restored[0])
        self.assertEqual(decision_sha, restored[3])
        self.assertEqual(sidecar_sha, restored[4])
        self.assertNotIn(str(self.root), decision_path.read_text())

        raw = json.loads(decision_path.read_text())
        raw["decision"]["value"] = "tampered"
        decision_path.write_text(
            json.dumps(raw, sort_keys=True, separators=(",", ":")) + "\n"
        )
        with self.assertRaises(LedgerConflictError):
            read_decision_sidecar(
                decision_path,
                binding=item,
                validator=lambda _value: None,
            )

    def test_concurrent_writers_share_one_locked_canonical_journal(self) -> None:
        def write(index: int) -> str:
            item = binding(
                self.root,
                logical_call_id=f"concurrent.logical.{index:03d}",
                attempt_id=f"concurrent.attempt.{index:03d}",
                request_sha256=digest(f"concurrent-request-{index}"),
            )
            snapshot = UsageLedger(self.path, clock=lambda: NOW).begin_attempt(item)
            return snapshot.status

        with ThreadPoolExecutor(max_workers=8) as executor:
            statuses = list(executor.map(write, range(24)))
        self.assertEqual(["manifested"] * 24, statuses)
        state = self.ledger.audit_state()
        self.assertEqual(24, state["attempt_count"])
        self.assertEqual(24, state["event_count"])


if __name__ == "__main__":
    unittest.main()
