from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import model_cards.run_summary as run_summary_module
from model_cards.claim_gate import DecisionStatus, GateName, ProseCheckerDecision
from model_cards.extraction import ExtractionBatch, QuoteProposal, materialize_quote_batch
from model_cards.factreasoner import CheckOutcome, CheckerResponse
from model_cards.models import RelationToTarget
from model_cards.pipeline import run_offline_pipeline
from model_cards.risk_mapping import RiskCatalog, TaxonomyRisk
from model_cards.run_ledger import (
    EXACT_MODEL,
    AttemptBinding,
    RouteSnapshot,
    UsageLedger,
    UsageReceipt,
    json_sha256,
    path_sha256,
)
from model_cards.run_summary import (
    AUDIT_VIEW_FILENAME,
    USAGE_SUMMARY_FILENAME,
    RunSummaryArtifactReference,
    RunSummaryArtifacts,
    RunSummaryError,
    write_run_summaries,
)
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import build_source_document_catalog


REVISION = "a" * 40
SUMMARY = "The exact target is an instruction-following language model."
SOURCE_BODY_MARKER = "private source body marker that summaries must never copy"
PROVIDER = "Synthetic Provider"
PARAMETERS = (
    "max_tokens",
    "reasoning",
    "response_format",
    "structured_outputs",
    "temperature",
)
RISK_CATALOG = RiskCatalog.build(
    (
        TaxonomyRisk(
            risk_id="atlas-output-with-personal-data",
            name="Output with personal data",
            description="A model might reveal personal data in generated output.",
            source_url="https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas",
        ),
    )
)


def _canonical(value) -> bytes:
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


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class Adapter:
    def resolve_revision(self, model_id, requested_revision):
        return REVISION

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(
            FetchStatus.OK,
            json.dumps(
                {
                    "id": model_id,
                    "sha": revision,
                    "pipeline_tag": "text-generation",
                    "config": {"model_type": "fixture-transformer"},
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
        )

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                f"# Exact target\n\n{SUMMARY}\n\n{SOURCE_BODY_MARKER}\n".encode(),
            )
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                b'{"model_type":"fixture-transformer"}',
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class SupportingFactChecker:
    checker_id = "tests/run_summary_support"
    checker_revision = "fixture-v1"

    def check(self, request):
        return CheckerResponse(
            outcome=CheckOutcome.SUPPORT,
            reason_code="fixture_support",
            cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
        )


class ContradictingSummaryChecker(SupportingFactChecker):
    checker_id = "tests/run_summary_contradiction"

    def check(self, request):
        if request.atom.field_path == "identity.summary":
            return CheckerResponse(
                outcome=CheckOutcome.CONTRADICTION,
                reason_code="fixture_contradiction",
                cited_chunk_ids=(request.contexts[0].chunk.chunk_id,),
            )
        return super().check(request)


class RunSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = self.root / "bundle"
        self.run = self.root / "run"
        collect_hf_source_bundle("acme/Instruct", self.bundle, Adapter())

    def pipeline(self, run: Path | None = None, **kwargs):
        return run_offline_pipeline(
            self.bundle,
            run or self.run,
            risk_catalog=RISK_CATALOG,
            fact_checker=kwargs.pop("fact_checker", SupportingFactChecker()),
            **kwargs,
        )

    def quote_input(self):
        catalog = build_source_document_catalog(replay_source_bundle(self.bundle))
        source = next(
            item for item in catalog.documents if item.source_uri.endswith("/README.md")
        )
        batch = ExtractionBatch.build(
            target=catalog.target,
            source_catalog_sha256=catalog.catalog_sha256,
            provider="Together",
            inference_config_sha256="b" * 64,
            proposals=(
                QuoteProposal(
                    source_id=source.source_id,
                    field_path="identity.summary",
                    value=SUMMARY,
                    quote=SUMMARY,
                    claim_entity=f"acme/Instruct@{REVISION}",
                    relation=RelationToTarget.EXACT_TARGET,
                ),
            ),
        )
        candidate = materialize_quote_batch(batch, catalog).candidates[0]
        decisions = tuple(
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=gate,
                checker="tests/run_summary_gate",
                method=method,
                status=DecisionStatus.ACCEPTED,
                reason=reason,
            )
            for gate, method, reason in (
                (GateName.FIELD_FIT, "bounded_semantic_field_review", "fixture_field_fit"),
                (
                    GateName.VALUE_SUPPORT,
                    "bounded_complete_value_review",
                    "fixture_value_support",
                ),
            )
        )
        return batch, decisions

    def add_paid_retry(
        self,
        *,
        run: Path | None = None,
        provider: str = PROVIDER,
    ) -> None:
        destination = run or self.run
        ledger = UsageLedger(destination / "usage.jsonl")
        binding = AttemptBinding(
            logical_call_id="summary.logical.001",
            attempt_id="summary.attempt.001",
            model=EXACT_MODEL,
            provider=provider,
            request_sha256=_sha("bounded-request"),
            schema_sha256=json_sha256(
                {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                    "additionalProperties": False,
                }
            ),
            sidecar_path_sha256=path_sha256(destination / "decision.json"),
            context_metadata={"stage": "extraction", "target_id": "acme-instruct"},
        )
        ledger.begin_attempt(binding)

        def route():
            return RouteSnapshot(
                model=EXACT_MODEL,
                provider=provider,
                checked_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                prompt_price_per_token_usd="0.001",
                completion_price_per_token_usd="0.001",
                context_length=4096,
                max_completion_tokens=1024,
                supported_parameters=PARAMETERS,
            )

        first = ledger.reserve(
            binding,
            retry_index=0,
            route=route(),
            input_token_ceiling=100,
            output_token_ceiling=100,
        )
        ledger.record_terminal(
            first,
            outcome="retryable_http_error",
            receipt=UsageReceipt(
                http_status=429,
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                charged_usd="0.01",
                latency_ms=20,
                returned_model=None,
                returned_provider=None,
            ),
            reason_code="http_retryable",
        )
        second = ledger.reserve(
            binding,
            retry_index=1,
            route=route(),
            input_token_ceiling=100,
            output_token_ceiling=100,
        )
        ledger.record_terminal(
            second,
            outcome="completed",
            receipt=UsageReceipt(
                http_status=200,
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                charged_usd="0.04",
                latency_ms=30,
                returned_model=EXACT_MODEL,
                returned_provider=provider,
            ),
            reason_code="structured_decision_completed",
            decision_sha256="d" * 64,
            sidecar_sha256="e" * 64,
        )

    def test_empty_usage_summary_and_audit_view_are_canonical_and_idempotent(self) -> None:
        result = self.pipeline()
        first = write_run_summaries(result, self.run)
        self.assertEqual(
            first.to_dict(), RunSummaryArtifacts.from_dict(first.to_dict()).to_dict()
        )
        self.assertEqual(
            [AUDIT_VIEW_FILENAME, USAGE_SUMMARY_FILENAME],
            [item.filename for item in first.artifacts],
        )
        for reference in first.artifacts:
            self.assertEqual(
                reference.artifact_sha256,
                hashlib.sha256((self.run / reference.filename).read_bytes()).hexdigest(),
            )
        before = {
            name: (self.run / name).read_bytes()
            for name in (USAGE_SUMMARY_FILENAME, AUDIT_VIEW_FILENAME)
        }
        usage = json.loads(before[USAGE_SUMMARY_FILENAME])
        audit = json.loads(before[AUDIT_VIEW_FILENAME])
        self.assertEqual(before[USAGE_SUMMARY_FILENAME], _canonical(usage))
        self.assertEqual(before[AUDIT_VIEW_FILENAME], _canonical(audit))
        self.assertEqual(1, usage["ledger"]["ledger_count"])
        self.assertEqual(0, usage["metrics"]["paid_calls"])
        self.assertEqual(0, usage["metrics"]["total_tokens"])
        self.assertEqual(0, usage["metrics"]["latency_ms"])
        self.assertEqual(result.result_sha256, audit["pipeline_result_sha256"])
        self.assertEqual(0, audit["repair"]["record_count"])
        self.assertEqual(len(result.artifacts) + 1, audit["stages"]["artifact_count"])
        self.assertEqual(result.validation.to_dict(), audit["validation"]["validation_flags"])

        encoded = json.dumps({"usage": usage, "audit": audit}, sort_keys=True)
        self.assertNotIn(str(self.root), encoded)
        self.assertNotIn(SOURCE_BODY_MARKER, encoded)
        self.assertNotIn("raw_response", encoded)
        second = write_run_summaries(result, self.run)
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(
            before,
            {
                name: (self.run / name).read_bytes()
                for name in (USAGE_SUMMARY_FILENAME, AUDIT_VIEW_FILENAME)
            },
        )

    def test_usage_summary_reports_calls_tokens_retries_cost_and_latency(self) -> None:
        result = self.pipeline()
        self.add_paid_retry()
        write_run_summaries(result, self.run)
        usage = json.loads((self.run / USAGE_SUMMARY_FILENAME).read_text())
        metrics = usage["metrics"]
        self.assertEqual(2, metrics["paid_calls"])
        self.assertEqual(1, metrics["retry_count"])
        self.assertEqual(10, metrics["prompt_tokens"])
        self.assertEqual(5, metrics["completion_tokens"])
        self.assertEqual(15, metrics["total_tokens"])
        self.assertEqual("0.050", metrics["committed_usd"])
        self.assertEqual(50, metrics["latency_ms"])
        self.assertEqual(30, metrics["max_latency_ms"])
        self.assertEqual([PROVIDER], metrics["providers"])
        audit = json.loads((self.run / AUDIT_VIEW_FILENAME).read_text())
        self.assertEqual(metrics, audit["usage"])

    def test_repair_counts_are_body_free_and_bound_to_final_composition(self) -> None:
        batch, decisions = self.quote_input()
        result = self.pipeline(
            quote_batches=(batch,),
            prose_checker_decisions=decisions,
            fact_checker=ContradictingSummaryChecker(),
        )
        write_run_summaries(result, self.run)
        audit = json.loads((self.run / AUDIT_VIEW_FILENAME).read_text())
        self.assertEqual(1, audit["repair"]["record_count"])
        self.assertEqual(0, audit["repair"]["semantic_submission_count"])
        self.assertEqual(1, audit["repair"]["actionable_candidate_count"])
        self.assertEqual(1, audit["repair"]["withheld_candidate_count"])
        self.assertEqual(result.composition_sha256, audit["validation"]["composition_sha256"])
        encoded = json.dumps(audit, sort_keys=True)
        self.assertNotIn(SUMMARY, encoded)
        self.assertNotIn(SOURCE_BODY_MARKER, encoded)

    def test_registered_artifact_and_existing_summary_tampering_fail_closed(self) -> None:
        result = self.pipeline()
        write_run_summaries(result, self.run)
        summary_path = self.run / USAGE_SUMMARY_FILENAME
        summary_path.write_text(summary_path.read_text() + " ", encoding="utf-8")
        with self.assertRaises(RunSummaryError):
            write_run_summaries(result, self.run)

        other = self.root / "other-run"
        other_result = self.pipeline(other)
        public_card = other / "public-card.json"
        public_card.write_text(public_card.read_text() + " ", encoding="utf-8")
        with self.assertRaises(RunSummaryError):
            write_run_summaries(other_result, other)

    def test_symlinks_duplicate_ledgers_and_ledger_drift_are_rejected(self) -> None:
        result = self.pipeline()
        outside = self.root / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        os.symlink(outside, self.run / AUDIT_VIEW_FILENAME)
        with self.assertRaises(RunSummaryError):
            write_run_summaries(result, self.run)

        duplicate_run = self.root / "duplicate-run"
        duplicate_result = self.pipeline(duplicate_run)
        nested = duplicate_run / "nested"
        nested.mkdir()
        (nested / "usage.jsonl").write_bytes(b"")
        with self.assertRaises(RunSummaryError):
            write_run_summaries(duplicate_result, duplicate_run)

        drift_run = self.root / "drift-run"
        drift_result = self.pipeline(drift_run)
        write_run_summaries(drift_result, drift_run)
        self.add_paid_retry(run=drift_run)
        with self.assertRaises(RunSummaryError):
            write_run_summaries(drift_result, drift_run)

        root_link = self.root / "run-link"
        os.symlink(self.run, root_link)
        with self.assertRaises(RunSummaryError):
            write_run_summaries(result, root_link)

        real_parent = self.root / "real-parent"
        nested_run = real_parent / "nested" / "run"
        nested_result = self.pipeline(nested_run)
        alias_parent = self.root / "alias-parent"
        os.symlink(real_parent, alias_parent)
        with self.assertRaises(RunSummaryError):
            write_run_summaries(nested_result, alias_parent / "nested" / "run")

    def test_absolute_path_like_provider_metadata_is_not_exported(self) -> None:
        for index, provider in enumerate(
            (
                "Provider:/etc/private-config",
                "Provider+/etc/private-config",
                "Provider)/etc/private-config",
            )
        ):
            with self.subTest(provider=provider):
                run = self.root / f"path-provider-{index}"
                result = self.pipeline(run)
                self.add_paid_retry(run=run, provider=provider)
                with self.assertRaises(RunSummaryError):
                    write_run_summaries(result, run)
                self.assertFalse((run / USAGE_SUMMARY_FILENAME).exists())
                self.assertFalse((run / AUDIT_VIEW_FILENAME).exists())

    def test_usage_metrics_and_digest_reject_an_aba_ledger_change(self) -> None:
        result = self.pipeline()
        original_bytes = (self.run / "usage.jsonl").read_bytes()
        paid_run = self.root / "paid-ledger-run"
        self.pipeline(paid_run)
        self.add_paid_retry(run=paid_run)
        paid_bytes = (paid_run / "usage.jsonl").read_bytes()
        original_audit = UsageLedger.audit_metrics

        def aba_audit(ledger):
            (self.run / "usage.jsonl").write_bytes(paid_bytes)
            try:
                return original_audit(ledger)
            finally:
                (self.run / "usage.jsonl").write_bytes(original_bytes)

        with patch.object(UsageLedger, "audit_metrics", new=aba_audit):
            with self.assertRaises(RunSummaryError):
                write_run_summaries(result, self.run)
        self.assertFalse((self.run / USAGE_SUMMARY_FILENAME).exists())
        self.assertFalse((self.run / AUDIT_VIEW_FILENAME).exists())

    def test_summary_write_races_fail_and_roll_back_only_new_files(self) -> None:
        for index, tampered_name in enumerate(
            (USAGE_SUMMARY_FILENAME, AUDIT_VIEW_FILENAME)
        ):
            with self.subTest(tampered_name=tampered_name):
                run = self.root / f"summary-race-{index}"
                result = self.pipeline(run)
                original = run_summary_module._write_or_verify

                def tampering_write(path, value):
                    written = original(path, value)
                    if path.name == AUDIT_VIEW_FILENAME:
                        target = run / tampered_name
                        target.write_bytes(target.read_bytes() + b" ")
                    return written

                with patch.object(
                    run_summary_module,
                    "_write_or_verify",
                    side_effect=tampering_write,
                ):
                    with self.assertRaises(RunSummaryError):
                        write_run_summaries(result, run)
                self.assertFalse((run / USAGE_SUMMARY_FILENAME).exists())
                self.assertFalse((run / AUDIT_VIEW_FILENAME).exists())
                write_run_summaries(result, run)

    def test_control_drift_after_link_rolls_back_and_can_be_retried(self) -> None:
        result = self.pipeline()
        original = run_summary_module._write_or_verify
        injected = False

        def drifting_write(path, value):
            nonlocal injected
            written = original(path, value)
            if path.name == AUDIT_VIEW_FILENAME and not injected:
                injected = True
                self.add_paid_retry()
            return written

        with patch.object(
            run_summary_module,
            "_write_or_verify",
            side_effect=drifting_write,
        ):
            with self.assertRaises(RunSummaryError):
                write_run_summaries(result, self.run)
        self.assertFalse((self.run / USAGE_SUMMARY_FILENAME).exists())
        self.assertFalse((self.run / AUDIT_VIEW_FILENAME).exists())
        summaries = write_run_summaries(result, self.run)
        self.assertEqual(
            2,
            json.loads((self.run / USAGE_SUMMARY_FILENAME).read_text())["metrics"][
                "paid_calls"
            ],
        )
        self.assertEqual(result.run_id, summaries.run_id)

    def test_summary_result_rejects_duplicate_artifact_references(self) -> None:
        result = self.pipeline()
        summaries = write_run_summaries(result, self.run)
        audit, usage = summaries.artifacts
        duplicate = RunSummaryArtifactReference(
            filename=AUDIT_VIEW_FILENAME,
            artifact_sha256="f" * 64,
        )
        with self.assertRaises(RunSummaryError):
            RunSummaryArtifacts(
                run_id=summaries.run_id,
                pipeline_result_sha256=summaries.pipeline_result_sha256,
                usage_summary_sha256=summaries.usage_summary_sha256,
                audit_view_sha256=summaries.audit_view_sha256,
                artifacts=(audit, duplicate, usage),
            )


if __name__ == "__main__":
    unittest.main()
