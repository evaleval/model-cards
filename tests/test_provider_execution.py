from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from model_cards.models import TargetIdentity
from model_cards.provider import (
    PINNED_PROVIDER,
    ProviderResponseError,
    ProviderTerminalAttemptError,
    StructuredCallSpec,
    structured_json_call,
)
from model_cards.provider_execution import (
    ProviderExecutionCollector,
    ProviderExecutionError,
    ProviderExecutionManifest,
)
from tests.test_provider import (
    FixtureTransport,
    KEY,
    NOW,
    SCHEMA,
    Monotonic,
    route_payload,
    success_payload,
    validator,
)


class ProviderExecutionManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.ledger = self.root / "usage.jsonl"
        self.decisions = self.root / "provider-decisions"
        self.decisions.mkdir()
        self.decision = self.decisions / "fact-check.json"
        self.target = TargetIdentity("acme/exact", "a" * 40)
        self.fact_batch_sha256 = "7" * 64
        fact_logical = f"fact.batch.{self.fact_batch_sha256[:24]}"
        self.spec = StructuredCallSpec(
            logical_call_id=fact_logical,
            attempt_id=fact_logical + ".attempt1",
            provider=PINNED_PROVIDER,
            schema_name="factreasoner_result",
            json_schema=SCHEMA,
            system_prompt="Private system instruction.",
            user_prompt="PRIVATE SOURCE SENTINEL",
            max_output_tokens=256,
            context_metadata={
                "stage": "factreasoner_batch",
                "batch_sha256": self.fact_batch_sha256,
                "request_count": 1,
            },
        )
        transport = FixtureTransport(
            [(200, success_payload(provider=PINNED_PROVIDER))],
            routes=[route_payload(provider=PINNED_PROVIDER)],
        )
        self.result = structured_json_call(
            self.spec,
            ledger_path=self.ledger,
            decision_path=self.decision,
            validator=validator,
            environment={"OPENROUTER_API_KEY": KEY},
            transport=transport,
            clock=lambda: NOW,
            monotonic=Monotonic(),
            sleeper=lambda _seconds: None,
        )
        self.collector = ProviderExecutionCollector()
        self.collector.record(self.result.execution)
        self.manifest = ProviderExecutionManifest.build(
            target=self.target,
            source_catalog_sha256="1" * 64,
            eligible_text_source_ids=(),
            use_risk_signal_source_ids=(),
            quote_candidate_ids=(),
            family_applicability_candidate_ids=(),
            family_applicability_failed_candidate_ids=(),
            nexus_instruction_sha256s=(),
            risk_applicability_candidate_ids=(),
            factreasoner_batch_sha256s=(self.fact_batch_sha256,),
            pipeline_result_sha256="2" * 64,
            content_factreasoner_sha256="3" * 64,
            publication_original_factreasoner_sha256="4" * 64,
            final_factreasoner_sha256="5" * 64,
            risk_mapping_report_sha256="6" * 64,
            adapter_version="model-card-openrouter-adapters/v19",
            orchestration_version="provider-assisted-model-card-orchestration/v14",
            max_risks=5,
            ledger_path=self.ledger,
            executions=self.collector.bindings,
        )

    def _execution(self, name: str, context_metadata: dict):
        stage = context_metadata["stage"]
        if stage == "quote_extraction":
            logical = (
                f"extract.{context_metadata['source_id']}."
                f"{context_metadata['catalog_sha256'][:16]}"
            )
        elif stage == "quote_extraction_use_risk":
            logical = (
                f"extract-use-risk.{context_metadata['source_id']}."
                f"{context_metadata['catalog_sha256'][:16]}"
            )
        elif stage in {"entity_scope", "field_fit", "value_support"}:
            logical = f"claim.{stage}.{context_metadata['candidate_id']}"
        elif stage == "family_applicability":
            logical = f"family.applicability.{context_metadata['candidate_id']}"
        elif stage == "nexus_risk_selection":
            logical = (
                "nexus.risk_selection."
                + context_metadata["instruction_sha256"][:24]
            )
        elif stage == "risk_applicability":
            logical = f"risk.applicability.{context_metadata['risk_candidate_id']}"
        elif stage == "factreasoner_batch":
            logical = f"fact.batch.{context_metadata['batch_sha256'][:24]}"
        else:
            logical = f"coverage.{name}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=PINNED_PROVIDER,
            schema_name="coverage_result",
            json_schema=SCHEMA,
            system_prompt="Synthetic coverage instruction.",
            user_prompt=f"Synthetic coverage input for {name}.",
            max_output_tokens=64,
            context_metadata=context_metadata,
        )
        result = structured_json_call(
            spec,
            ledger_path=self.ledger,
            decision_path=self.decisions / f"{name}.json",
            validator=validator,
            environment={"OPENROUTER_API_KEY": KEY},
            transport=FixtureTransport(
                [(200, success_payload(provider=PINNED_PROVIDER))],
                routes=[route_payload(provider=PINNED_PROVIDER)],
            ),
            clock=lambda: NOW,
            monotonic=Monotonic(),
            sleeper=lambda _seconds: None,
        )
        return result.execution

    def _coverage_executions(self):
        catalog_sha256 = "1" * 64
        source_ids = ("source-alpha", "source-beta")
        candidate_ids = (
            "claim-111111111111111111111111",
            "claim-222222222222222222222222",
        )
        executions = [self.result.execution]
        for index, source_id in enumerate(source_ids):
            executions.append(
                self._execution(
                    f"extract-{index}",
                    {
                        "stage": "quote_extraction",
                        "source_id": source_id,
                        "catalog_sha256": catalog_sha256,
                    },
                )
            )
        executions.append(
            self._execution(
                "extract-use-risk",
                {
                    "stage": "quote_extraction_use_risk",
                    "source_id": "source-beta",
                    "catalog_sha256": catalog_sha256,
                },
            )
        )
        for candidate_index, candidate_id in enumerate(candidate_ids):
            for stage in ("entity_scope", "field_fit", "value_support"):
                executions.append(
                    self._execution(
                        f"gate-{candidate_index}-{stage}",
                        {"stage": stage, "candidate_id": candidate_id},
                    )
                )
        return source_ids, ("source-beta",), candidate_ids, tuple(executions)

    def _build_coverage_manifest(
        self,
        *,
        eligible_text_source_ids,
        use_risk_signal_source_ids,
        quote_candidate_ids,
        executions,
        source_catalog_sha256="1" * 64,
        family_applicability_candidate_ids=(),
        family_applicability_failed_candidate_ids=(),
        nexus_instruction_sha256s=(),
        risk_applicability_candidate_ids=(),
        factreasoner_batch_sha256s=None,
    ):
        return ProviderExecutionManifest.build(
            target=self.target,
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
            factreasoner_batch_sha256s=(
                (self.fact_batch_sha256,)
                if factreasoner_batch_sha256s is None
                else factreasoner_batch_sha256s
            ),
            pipeline_result_sha256="2" * 64,
            content_factreasoner_sha256="3" * 64,
            publication_original_factreasoner_sha256="4" * 64,
            final_factreasoner_sha256="5" * 64,
            risk_mapping_report_sha256="6" * 64,
            adapter_version="model-card-openrouter-adapters/v19",
            orchestration_version="provider-assisted-model-card-orchestration/v14",
            max_risks=5,
            ledger_path=self.ledger,
            executions=executions,
        )

    def test_manifest_round_trip_and_exact_run_verification(self) -> None:
        value = self.manifest.to_dict()
        restored = ProviderExecutionManifest.from_dict(value)
        self.assertEqual(value, restored.to_dict())
        decisions = restored.verify_run(self.root)
        self.assertEqual(
            {self.result.execution.binding_sha256: {"value": "normalized"}},
            decisions,
        )
        self.assertNotIn(KEY, json.dumps(value))
        self.assertNotIn("PRIVATE SOURCE SENTINEL", json.dumps(value))
        self.assertNotIn(str(self.root), json.dumps(value))

    def test_collector_deduplicates_identical_replay_receipts(self) -> None:
        self.collector.record(self.result.execution)
        self.assertEqual((self.result.execution,), self.collector.bindings)

    def test_manifest_rejects_changed_ledger_or_sidecar_inventory(self) -> None:
        self.ledger.write_bytes(self.ledger.read_bytes() + b"\n")
        with self.assertRaisesRegex(ProviderExecutionError, "ledger has changed"):
            self.manifest.verify_run(self.root)

        self.ledger.write_bytes(self.ledger.read_bytes().rstrip(b"\n") + b"\n")
        extra = self.decisions / "extra.json"
        extra.write_text("{}\n")
        with self.assertRaisesRegex(ProviderExecutionError, "inventory has changed"):
            self.manifest.verify_run(self.root)

    def test_manifest_digest_and_configuration_are_closed(self) -> None:
        value = self.manifest.to_dict()
        value["max_risks"] = 6
        with self.assertRaisesRegex(ProviderExecutionError, "digest is inconsistent"):
            ProviderExecutionManifest.from_dict(value)
        value = self.manifest.to_dict()
        value["unexpected"] = True
        with self.assertRaisesRegex(ProviderExecutionError, "invalid shape"):
            ProviderExecutionManifest.from_dict(value)

    def test_manifest_binds_and_verifies_exact_semantic_receipt_coverage(self) -> None:
        source_ids, use_risk_ids, candidate_ids, executions = (
            self._coverage_executions()
        )
        manifest = self._build_coverage_manifest(
            eligible_text_source_ids=source_ids,
            use_risk_signal_source_ids=use_risk_ids,
            quote_candidate_ids=candidate_ids,
            executions=executions,
        )

        self.assertEqual(source_ids, manifest.eligible_text_source_ids)
        self.assertEqual(use_risk_ids, manifest.use_risk_signal_source_ids)
        self.assertEqual(candidate_ids, manifest.quote_candidate_ids)
        self.assertEqual(len(executions), len(manifest.verify_run(self.root)))
        restored = ProviderExecutionManifest.from_dict(manifest.to_dict())
        self.assertEqual(manifest.to_dict(), restored.to_dict())

    def test_manifest_rejects_missing_duplicate_and_unexpected_stage_receipts(self) -> None:
        source_ids, use_risk_ids, candidate_ids, executions = (
            self._coverage_executions()
        )

        cases = (
            (
                "missing general extraction",
                (*source_ids, "source-gamma"),
                use_risk_ids,
                candidate_ids,
                "quote extraction receipt coverage",
            ),
            (
                "missing use/risk extraction",
                source_ids,
                source_ids,
                candidate_ids,
                "use/risk extraction receipt coverage",
            ),
            (
                "missing entity gate",
                source_ids,
                use_risk_ids,
                (*candidate_ids, "claim-333333333333333333333333"),
                "entity_scope receipt coverage",
            ),
        )
        for label, expected_sources, expected_use_risk, expected_candidates, message in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ProviderExecutionError, message):
                    self._build_coverage_manifest(
                        eligible_text_source_ids=expected_sources,
                        use_risk_signal_source_ids=expected_use_risk,
                        quote_candidate_ids=expected_candidates,
                        executions=executions,
                    )

        with self.assertRaisesRegex(ProviderExecutionError, "entries are duplicated"):
            self._build_coverage_manifest(
                eligible_text_source_ids=source_ids,
                use_risk_signal_source_ids=use_risk_ids,
                quote_candidate_ids=candidate_ids,
                executions=executions + (executions[1],),
            )

        with self.assertRaisesRegex(ProviderExecutionError, "ledger inventory"):
            self._build_coverage_manifest(
                eligible_text_source_ids=source_ids,
                use_risk_signal_source_ids=use_risk_ids,
                quote_candidate_ids=candidate_ids,
                executions=executions[:-1],
            )

    def test_manifest_binds_exact_family_applicability_receipt_coverage(self) -> None:
        source_ids, use_risk_ids, candidate_ids, executions = (
            self._coverage_executions()
        )
        family_candidate_id = "claim-333333333333333333333333"
        family_execution = self._execution(
            "family-applicability",
            {
                "stage": "family_applicability",
                "candidate_id": family_candidate_id,
            },
        )
        complete = executions + (family_execution,)
        manifest = self._build_coverage_manifest(
            eligible_text_source_ids=source_ids,
            use_risk_signal_source_ids=use_risk_ids,
            quote_candidate_ids=candidate_ids,
            family_applicability_candidate_ids=(family_candidate_id,),
            executions=complete,
        )
        self.assertEqual(
            (family_candidate_id,),
            manifest.family_applicability_candidate_ids,
        )

        cases = (
            ("missing", complete, (family_candidate_id, "claim-444444444444444444444444")),
            ("unexpected", complete, ()),
        )
        for label, receipt_values, expected_ids in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(
                    ProviderExecutionError,
                    "family_applicability receipt coverage",
                ):
                    self._build_coverage_manifest(
                        eligible_text_source_ids=source_ids,
                        use_risk_signal_source_ids=use_risk_ids,
                        quote_candidate_ids=candidate_ids,
                        family_applicability_candidate_ids=expected_ids,
                        executions=receipt_values,
                    )

    def test_manifest_rejects_noncanonical_or_stale_coverage_metadata(self) -> None:
        source_ids, use_risk_ids, candidate_ids, executions = (
            self._coverage_executions()
        )
        with self.assertRaisesRegex(ProviderExecutionError, "not canonical"):
            self._build_coverage_manifest(
                eligible_text_source_ids=tuple(reversed(source_ids)),
                use_risk_signal_source_ids=use_risk_ids,
                quote_candidate_ids=candidate_ids,
                executions=executions,
            )
        with self.assertRaisesRegex(ProviderExecutionError, "eligible text sources"):
            self._build_coverage_manifest(
                eligible_text_source_ids=source_ids,
                use_risk_signal_source_ids=("source-gamma",),
                quote_candidate_ids=candidate_ids,
                executions=executions,
            )
        with self.assertRaisesRegex(ProviderExecutionError, "metadata is stale"):
            self._build_coverage_manifest(
                eligible_text_source_ids=source_ids,
                use_risk_signal_source_ids=use_risk_ids,
                quote_candidate_ids=candidate_ids,
                source_catalog_sha256="9" * 64,
                executions=executions,
            )

    def test_manifest_binds_nexus_risk_and_factreasoner_receipts_exactly(self) -> None:
        instruction_sha256 = "8" * 64
        risk_candidate_id = "risk-candidate-" + "9" * 24
        nexus = self._execution(
            "nexus",
            {
                "stage": "nexus_risk_selection",
                "instruction_sha256": instruction_sha256,
            },
        )
        risk = self._execution(
            "risk-applicability",
            {
                "stage": "risk_applicability",
                "risk_candidate_id": risk_candidate_id,
            },
        )
        executions = (self.result.execution, nexus, risk)
        manifest = self._build_coverage_manifest(
            eligible_text_source_ids=(),
            use_risk_signal_source_ids=(),
            quote_candidate_ids=(),
            nexus_instruction_sha256s=(instruction_sha256,),
            risk_applicability_candidate_ids=(risk_candidate_id,),
            executions=executions,
        )
        self.assertEqual((instruction_sha256,), manifest.nexus_instruction_sha256s)
        self.assertEqual(
            (risk_candidate_id,), manifest.risk_applicability_candidate_ids
        )

        for label, nexus_ids, risk_ids, fact_ids, message in (
            (
                "nexus",
                (),
                (risk_candidate_id,),
                (self.fact_batch_sha256,),
                "Nexus receipt coverage",
            ),
            (
                "risk",
                (instruction_sha256,),
                (),
                (self.fact_batch_sha256,),
                "risk-applicability receipt coverage",
            ),
            (
                "factreasoner",
                (instruction_sha256,),
                (risk_candidate_id,),
                (),
                "FactReasoner receipt coverage",
            ),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ProviderExecutionError, message):
                    self._build_coverage_manifest(
                        eligible_text_source_ids=(),
                        use_risk_signal_source_ids=(),
                        quote_candidate_ids=(),
                        nexus_instruction_sha256s=nexus_ids,
                        risk_applicability_candidate_ids=risk_ids,
                        factreasoner_batch_sha256s=fact_ids,
                        executions=executions,
                    )

    def test_manifest_rejects_unknown_stage_receipt(self) -> None:
        rogue = self._execution("rogue", {"stage": "rogue_stage"})
        with self.assertRaisesRegex(ProviderExecutionError, "stage is unexpected"):
            self._build_coverage_manifest(
                eligible_text_source_ids=(),
                use_risk_signal_source_ids=(),
                quote_candidate_ids=(),
                executions=(self.result.execution, rogue),
            )

    def test_recoverable_failed_terminal_is_bound_and_replays_without_send(self) -> None:
        candidate_id = "claim-333333333333333333333333"
        logical = f"family.applicability.{candidate_id}"
        spec = StructuredCallSpec(
            logical_call_id=logical,
            attempt_id=logical + ".attempt1",
            provider=PINNED_PROVIDER,
            schema_name="failed_family_fixture",
            json_schema=SCHEMA,
            system_prompt="Private failed instruction.",
            user_prompt="PRIVATE FAILED SOURCE SENTINEL",
            max_output_tokens=64,
            context_metadata={
                "stage": "family_applicability",
                "candidate_id": candidate_id,
            },
        )
        decision_path = self.decisions / "failed-family.json"
        transport = FixtureTransport(
            [(400, b"{}")], routes=[route_payload(provider=PINNED_PROVIDER)]
        )
        with self.assertRaisesRegex(ProviderResponseError, "HTTP 400"):
            structured_json_call(
                spec,
                ledger_path=self.ledger,
                decision_path=decision_path,
                validator=validator,
                environment={"OPENROUTER_API_KEY": KEY},
                transport=transport,
                clock=lambda: NOW,
                monotonic=Monotonic(),
                sleeper=lambda _seconds: None,
            )
        self.assertEqual(1, transport.paid_count)
        manifest = self._build_coverage_manifest(
            eligible_text_source_ids=(),
            use_risk_signal_source_ids=(),
            quote_candidate_ids=(),
            family_applicability_failed_candidate_ids=(candidate_id,),
            executions=(self.result.execution,),
        )
        self.assertEqual(1, len(manifest.failed_executions))
        self.assertEqual("http_bad_request", manifest.failed_executions[0].reason_code)
        manifest.verify_run(self.root)
        serialized = json.dumps(manifest.to_dict())
        self.assertNotIn("PRIVATE FAILED SOURCE SENTINEL", serialized)

        ledger_before = self.ledger.read_bytes()
        forbidden = FixtureTransport([])
        with self.assertRaisesRegex(
            ProviderTerminalAttemptError, "safely recorded terminal failure"
        ):
            structured_json_call(
                spec,
                ledger_path=self.ledger,
                decision_path=decision_path,
                validator=validator,
                environment={},
                transport=forbidden,
            )
        self.assertEqual([], forbidden.requests)
        self.assertEqual(ledger_before, self.ledger.read_bytes())


if __name__ == "__main__":
    unittest.main()
