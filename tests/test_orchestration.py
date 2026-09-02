from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from model_cards.extraction import EXTRACTION_VERSION, ExtractionBatch
from model_cards.factreasoner import FACTREASONER_KERNEL_VERSION
from model_cards.pipeline import PIPELINE_VERSION, run_offline_pipeline
from model_cards.provider import (
    MODEL_ID,
    PINNED_PROVIDER,
    PROVIDER_RUNTIME_VERSION,
    ProviderResponseError,
)
from model_cards.provider_adapters import ADAPTER_VERSION, FACT_CHECKER_ID
from model_cards.orchestration import (
    ORCHESTRATION_MANIFEST_FILENAME,
    OrchestrationError,
    _build_risk_interfaces,
    run_provider_assisted_pipeline,
)
from model_cards.official_discovery import discover_official_sources
from model_cards.official_sources import (
    OfficialFetchStatus,
    OfficialRemoteObject,
    collect_official_sources,
)
from model_cards.risk_mapping import RiskCatalog, TaxonomyRisk
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)


REVISION = "a" * 40
OTHER_REVISION = "b" * 40
SUMMARY = "This exact checkpoint summarizes public research papers."
OFFICIAL_USE = "The publisher intends the exact model for research assistants."
OFFICIAL_URL = "https://github.com/acme/exact"
PUBLISHER_RISK_NAME = "Misinformation risk"
PUBLISHER_RISK_DESCRIPTION = "The model may produce incorrect factual statements."
PUBLISHER_RISK_RATIONALE = "This risk applies to the exact checkpoint."
PUBLISHER_RISK_QUOTE = (
    f"{PUBLISHER_RISK_NAME}. {PUBLISHER_RISK_DESCRIPTION} "
    f"{PUBLISHER_RISK_RATIONALE}"
)


class BundleAdapter:
    def __init__(self, revision=REVISION):
        self.revision = revision

    def resolve_revision(self, model_id, requested_revision):
        return self.revision

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
                ("# Summary\n" + SUMMARY + "\n").encode("utf-8"),
            )
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                b'{"model_type":"fixture-transformer"}',
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class OfficialLinkedBundleAdapter(BundleAdapter):
    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    "# Summary\n"
                    + SUMMARY
                    + "\n[Official code]("
                    + OFFICIAL_URL
                    + ")\n"
                ).encode("utf-8"),
            )
        return super().fetch_file(
            model_id, revision, repo_path, max_bytes=max_bytes
        )


class PublisherRiskBundleAdapter(BundleAdapter):
    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    "# Summary\n"
                    + SUMMARY
                    + "\n\n# Risks\n"
                    + PUBLISHER_RISK_QUOTE
                    + "\n"
                ).encode("utf-8"),
            )
        return super().fetch_file(
            model_id, revision, repo_path, max_bytes=max_bytes
        )


class OfficialAdapter:
    def fetch(self, url, *, max_bytes, max_redirects):
        if url != OFFICIAL_URL:
            return OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE,
                reason_code="fixture_not_provided",
            )
        return OfficialRemoteObject(
            OfficialFetchStatus.OK,
            content=OFFICIAL_USE.encode("utf-8"),
            final_url=url,
            redirect_chain=(url,),
            media_type="text/plain",
        )


RISK_CATALOG = RiskCatalog.build(
    (
        TaxonomyRisk(
            risk_id="atlas-inaccurate-output",
            name="Inaccurate output",
            description="Generated text may contain inaccurate information.",
            source_url="https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas",
        ),
    )
)


class ResumableFakeCall:
    """Sidecar-keyed fake: invocations repeat, simulated paid work does not."""

    def __init__(self):
        self.invocations = []
        self.paid_paths = []
        self.cached = {}
        self.specs = []
        self.kwargs = []

    def _decision(self, spec):
        stage = spec.context_metadata["stage"]
        if stage == "quote_extraction":
            payload = json.loads(spec.user_prompt)
            return {
                "proposals": [
                    {
                        "source_id": payload["source"]["source_id"],
                        "field_path": "identity.summary",
                        "value_json": json.dumps(SUMMARY),
                        "quote": SUMMARY,
                        "claim_entity": (
                            payload["target"]["model_id"]
                            + "@"
                            + payload["target"]["revision"]
                        ),
                        "relation": "exact_target",
                        "benchmark_scope_json": None,
                        "origin": "source_stated",
                    }
                ]
            }
        if stage == "field_fit":
            return {"status": "accepted", "reason": "semantic_field_fit"}
        if stage == "value_support":
            return {"status": "accepted", "reason": "semantic_value_support"}
        if stage == "factreasoner":
            payload = json.loads(spec.user_prompt)
            return {
                "outcome": "support",
                "reason_code": "support_in_context",
                "cited_chunk_ids": [payload["contexts"][0]["chunk_id"]],
            }
        raise AssertionError(f"unexpected fake provider stage: {stage}")

    def __call__(self, spec, **kwargs):
        decision_path = Path(kwargs["decision_path"])
        key = str(decision_path)
        self.specs.append(spec)
        self.kwargs.append(kwargs)
        self.invocations.append((spec.context_metadata["stage"], spec.logical_call_id, key))
        resumed = key in self.cached
        if not resumed:
            decision = self._decision(spec)
            kwargs["validator"](decision)
            self.cached[key] = decision
            self.paid_paths.append(key)
        decision = self.cached[key]
        kwargs["validator"](decision)
        return SimpleNamespace(
            decision=decision,
            receipt=SimpleNamespace(prompt_tokens=7, completion_tokens=3),
            resumed=resumed,
        )


class CombinedSourceFakeCall(ResumableFakeCall):
    def _decision(self, spec):
        if spec.context_metadata["stage"] == "quote_extraction":
            payload = json.loads(spec.user_prompt)
            is_official = payload["source"]["source_uri"] == OFFICIAL_URL
            value = OFFICIAL_USE if is_official else SUMMARY
            field_path = (
                "use_and_risk.intended_uses[0]"
                if is_official
                else "identity.summary"
            )
            return {
                "proposals": [
                    {
                        "source_id": payload["source"]["source_id"],
                        "field_path": field_path,
                        "value_json": json.dumps(value),
                        "quote": value,
                        "claim_entity": (
                            payload["target"]["model_id"]
                            + "@"
                            + payload["target"]["revision"]
                        ),
                        "relation": "exact_target",
                        "benchmark_scope_json": None,
                        "origin": "source_stated",
                    }
                ]
            }
        return super()._decision(spec)


class PublisherRiskFakeCall(ResumableFakeCall):
    def _decision(self, spec):
        if spec.context_metadata["stage"] == "quote_extraction":
            payload = json.loads(spec.user_prompt)
            return {
                "proposals": [
                    {
                        "source_id": payload["source"]["source_id"],
                        "field_path": "use_and_risk.identified_risks[0]",
                        "value_json": json.dumps(
                            {
                                "name": PUBLISHER_RISK_NAME,
                                "description": PUBLISHER_RISK_DESCRIPTION,
                                "applicability_rationale": PUBLISHER_RISK_RATIONALE,
                            }
                        ),
                        "quote": PUBLISHER_RISK_QUOTE,
                        "claim_entity": (
                            payload["target"]["model_id"]
                            + "@"
                            + payload["target"]["revision"]
                        ),
                        "relation": "exact_target",
                        "benchmark_scope_json": None,
                        "origin": "source_stated",
                    }
                ]
            }
        return super()._decision(spec)


class OneCheckerFailureFakeCall(ResumableFakeCall):
    def __init__(self, *, reason_code="http_bad_request"):
        super().__init__()
        self.reason_code = reason_code
        self.failed = False

    def __call__(self, spec, **kwargs):
        if spec.context_metadata["stage"] == "value_support" and not self.failed:
            self.failed = True
            self.specs.append(spec)
            self.kwargs.append(kwargs)
            self.invocations.append(
                (
                    spec.context_metadata["stage"],
                    spec.logical_call_id,
                    str(kwargs["decision_path"]),
                )
            )
            raise ProviderResponseError(
                "synthetic closed provider response failure",
                reason_code=self.reason_code,
            )
        return super().__call__(spec, **kwargs)


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = self.root / "bundle"
        self.run = self.root / "run"
        self.ledger = self.run / "usage.jsonl"
        self.decisions = self.run / "provider-decisions"
        self.transport = object()
        collect_hf_source_bundle("acme/Exact", self.bundle, BundleAdapter())

    def invoke(self, fake, **kwargs):
        values = {
            "provider": "Together",
            "ledger_path": self.ledger,
            "decision_dir": self.decisions,
            "environment": {"OPENROUTER_API_KEY": "fixture-only"},
            "transport": self.transport,
            "call": fake,
            "risk_catalog": RISK_CATALOG,
        }
        values.update(kwargs)
        # Risk is unavailable in this fixture because it has no accepted use
        # context; patching the optional interface also makes the test independent
        # of whether the large Nexus extra is installed in the test environment.
        with patch(
            "model_cards.orchestration._build_risk_interfaces",
            return_value=(None, None, "nexus_dependency_unavailable"),
        ):
            return run_provider_assisted_pipeline(
                self.bundle,
                self.run,
                **values,
            )

    def test_exact_provider_flow_two_gates_and_downstream_injection(self):
        fake = ResumableFakeCall()
        with patch(
            "model_cards.orchestration.run_offline_pipeline",
            wraps=run_offline_pipeline,
        ) as downstream:
            result = self.invoke(fake)

        extraction = [item for item in fake.invocations if item[0] == "quote_extraction"]
        gates = [
            item[0]
            for item in fake.invocations
            if item[0] in {"field_fit", "value_support"}
        ]
        self.assertEqual(1, len(extraction), "JSON sources must stay on the local path")
        self.assertEqual(["field_fit", "value_support"], gates)
        self.assertEqual(MODEL_ID, result.to_dict()["model"])
        self.assertEqual("Together", result.provider)
        self.assertTrue(all(spec.provider == "Together" for spec in fake.specs))
        self.assertTrue(
            all(item["transport"] is self.transport for item in fake.kwargs)
        )
        self.assertTrue(
            all(
                item["environment"] == {"OPENROUTER_API_KEY": "fixture-only"}
                for item in fake.kwargs
            )
        )
        self.assertEqual(
            {self.ledger.resolve()},
            {Path(item["ledger_path"]) for item in fake.kwargs},
        )
        self.assertEqual(
            {self.decisions.resolve()},
            {Path(item["decision_path"]).parent for item in fake.kwargs},
        )
        self.assertEqual(1, len(result.quote_candidate_ids))
        self.assertEqual(2, len(result.prose_decision_sha256s))

        self.assertEqual(1, downstream.call_count)
        injected = downstream.call_args.kwargs
        self.assertEqual(1, len(injected["quote_batches"]))
        self.assertIsInstance(injected["quote_batches"][0], ExtractionBatch)
        self.assertEqual("Together", injected["quote_batches"][0].provider)
        self.assertEqual(2, len(injected["prose_checker_decisions"]))
        self.assertEqual(
            {"field_fit", "value_support"},
            {item.gate.value for item in injected["prose_checker_decisions"]},
        )
        self.assertEqual(FACT_CHECKER_ID, injected["fact_checker"].checker_id)
        self.assertTrue((self.run / "public-card.json").is_file())
        original_fact = json.loads(
            (self.run / "factreasoner-original.json").read_text()
        )
        final_fact = json.loads((self.run / "factreasoner.json").read_text())
        for record in (original_fact, final_fact):
            self.assertTrue(record["decisions"])
            self.assertIn(
                "support", {item["outcome"] for item in record["decisions"]}
            )

    def test_publisher_risk_is_locally_wrapped_gated_and_exported_end_to_end(self):
        self.bundle = self.root / "publisher-risk-bundle"
        collect_hf_source_bundle(
            "acme/Exact", self.bundle, PublisherRiskBundleAdapter()
        )
        fake = PublisherRiskFakeCall()

        result = self.invoke(fake)

        self.assertEqual(1, len(result.quote_candidate_ids))
        card = json.loads((self.run / "card-artifact.json").read_text())["card"]
        risks = card["use_and_risk"]["identified_risks"]
        self.assertEqual(1, len(risks))
        risk = risks[0]
        self.assertEqual("publisher_reported", risk["identification_origin"])
        self.assertIsNone(risk["taxonomy"])
        self.assertTrue(risk["risk_id"].startswith("publisher-risk:"))
        self.assertEqual("source_binding", risk["mapping_provenance"]["method"])
        self.assertEqual("generated_unreviewed", risk["review_status"])
        self.assertTrue(risk["source_refs"])
        self.assertTrue(
            card["provenance"]["field_references"][
                "use_and_risk.identified_risks[0]"
            ]
        )
        self.assertNotIn("derivations", card["provenance"])
        self.assertEqual(
            tuple(result.quote_candidate_ids),
            result.pipeline_result.risk.publisher_reported_risk_candidate_ids,
        )
        self.assertEqual(0, result.pipeline_result.risk.taxonomy_candidate_count)
        self.assertEqual(0, result.pipeline_result.risk.taxonomy_included_count)

        gates = json.loads((self.run / "claim-gates.json").read_text())
        publisher_record = next(
            record
            for record in gates["records"]
            if record["candidate"]["field_path"]
            == "use_and_risk.identified_risks[0]"
        )
        self.assertTrue(publisher_record["projection_eligible"])
        self.assertEqual(
            {"accepted"},
            {decision["status"] for decision in publisher_record["decisions"]},
        )

        provider_decision = next(
            value for value in fake.cached.values() if "proposals" in value
        )
        provider_value = json.loads(
            provider_decision["proposals"][0]["value_json"]
        )
        self.assertEqual(
            {"name", "description", "applicability_rationale"},
            set(provider_value),
        )
        self.assertNotIn("risk_id", provider_value)
        self.assertNotIn("mapping_provenance", provider_value)

        paid_paths = list(fake.paid_paths)
        replayed = self.invoke(fake)
        self.assertEqual(paid_paths, fake.paid_paths)
        self.assertEqual(result.result_sha256, replayed.result_sha256)
        self.assertEqual(
            result.pipeline_result.result_sha256,
            replayed.pipeline_result.result_sha256,
        )

    def test_provider_extracts_hf_and_ancestry_bound_official_text_once_each(self):
        self.bundle = self.root / "linked-bundle"
        official = self.root / "official-bundle"
        collect_hf_source_bundle(
            "acme/Exact", self.bundle, OfficialLinkedBundleAdapter()
        )
        discovery = discover_official_sources(replay_source_bundle(self.bundle))
        collect_official_sources(discovery, official, OfficialAdapter())

        fake = CombinedSourceFakeCall()
        result = self.invoke(fake, official_bundle_directory=official)
        extraction = [
            item for item in fake.invocations if item[0] == "quote_extraction"
        ]
        gates = [
            item for item in fake.invocations
            if item[0] in {"field_fit", "value_support"}
        ]
        self.assertEqual(2, len(extraction))
        self.assertEqual(4, len(gates))
        self.assertEqual(2, len(result.quote_candidate_ids))
        self.assertTrue(result.source_bundle_id.startswith("combined_bundle_"))
        self.assertEqual(
            "hf_and_official",
            json.loads((self.run / "source-state.json").read_text())["mode"],
        )
        card = json.loads((self.run / "card-artifact.json").read_text())["card"]
        intended = card["use_and_risk"]["intended_uses"]
        self.assertEqual([OFFICIAL_USE], [item["description"] for item in intended])
        self.assertTrue(intended[0]["source_refs"][0].startswith("primary_src_"))

    def test_resume_order_is_deterministic_and_does_not_duplicate_paid_work(self):
        fake = ResumableFakeCall()
        first = self.invoke(fake)
        first_invocations = list(fake.invocations)
        first_paid = list(fake.paid_paths)

        second = self.invoke(fake)
        second_invocations = fake.invocations[len(first_invocations) :]
        self.assertEqual(
            [(stage, logical) for stage, logical, _ in first_invocations],
            [(stage, logical) for stage, logical, _ in second_invocations],
        )
        self.assertEqual(first_paid, fake.paid_paths)
        self.assertEqual(first.result_sha256, second.result_sha256)
        self.assertEqual(
            first.pipeline_result.result_sha256,
            second.pipeline_result.result_sha256,
        )
        self.assertEqual(
            sorted(first.extraction_batch_sha256s), list(first.extraction_batch_sha256s)
        )

    def test_one_checker_response_failure_withholds_candidate_and_continues(self):
        result = self.invoke(OneCheckerFailureFakeCall())
        self.assertTrue((self.run / "public-card.json").is_file())
        self.assertEqual(2, len(result.prose_decision_sha256s))
        gates = json.loads((self.run / "claim-gates.json").read_text())
        reasons = {
            decision["reason"]
            for record in gates["records"]
            for decision in record["decisions"]
        }
        self.assertIn("provider_response_unavailable", reasons)

    def test_route_identity_failure_remains_fatal(self):
        with self.assertRaises(ProviderResponseError):
            self.invoke(
                OneCheckerFailureFakeCall(reason_code="returned_provider_mismatch")
            )

    def test_summary_and_admission_do_not_serialize_source_text_prompts_or_paths(self):
        result = self.invoke(ResumableFakeCall())
        summary = json.dumps(result.to_dict(), sort_keys=True)
        admission = (self.run / ORCHESTRATION_MANIFEST_FILENAME).read_text()
        for serialized in (summary, admission):
            self.assertNotIn(SUMMARY, serialized)
            self.assertNotIn("fixture-only", serialized)
            self.assertNotIn(str(self.root), serialized)
            self.assertNotIn("user_prompt", serialized)
            self.assertNotIn("system_prompt", serialized)
            self.assertNotIn("windows", serialized)
        self.assertNotIn("README.md", summary)
        self.assertEqual("immutable_source_state_catalog", result.to_dict()["scope"])
        admitted = json.loads(admission)
        self.assertEqual(PINNED_PROVIDER, admitted["provider"])
        self.assertEqual(ADAPTER_VERSION, admitted["adapter_version"])
        self.assertEqual(EXTRACTION_VERSION, admitted["extraction_version"])
        self.assertEqual(
            FACTREASONER_KERNEL_VERSION,
            admitted["factreasoner_kernel_version"],
        )
        self.assertEqual(PIPELINE_VERSION, admitted["pipeline_version"])
        self.assertEqual(
            PROVIDER_RUNTIME_VERSION, admitted["provider_runtime_version"]
        )

    def test_target_or_catalog_drift_halts_before_another_provider_decision(self):
        fake = ResumableFakeCall()
        self.invoke(fake)
        paid = list(fake.paid_paths)
        other_bundle = self.root / "other-bundle"
        collect_hf_source_bundle(
            "acme/Other",
            other_bundle,
            BundleAdapter(OTHER_REVISION),
        )
        with self.assertRaisesRegex(OrchestrationError, "targets another"):
            with patch(
                "model_cards.orchestration._build_risk_interfaces",
                return_value=(None, None, "nexus_dependency_unavailable"),
            ):
                run_provider_assisted_pipeline(
                    other_bundle,
                    self.run,
                    provider="Together",
                    ledger_path=self.ledger,
                    decision_dir=self.decisions,
                    environment={"OPENROUTER_API_KEY": "fixture-only"},
                    call=fake,
                    risk_catalog=RISK_CATALOG,
                )
        self.assertEqual(paid, fake.paid_paths)

    def test_missing_provider_and_paths_outside_run_fail_before_calls(self):
        fake = ResumableFakeCall()
        common = {
            "ledger_path": self.ledger,
            "decision_dir": self.decisions,
            "call": fake,
            "risk_catalog": RISK_CATALOG,
        }
        with self.assertRaisesRegex(OrchestrationError, "provider"):
            run_provider_assisted_pipeline(
                self.bundle, self.run, provider="", **common
            )
        with self.assertRaisesRegex(OrchestrationError, "pinned"):
            run_provider_assisted_pipeline(
                self.bundle, self.run, provider="Baidu", **common
            )
        with self.assertRaisesRegex(OrchestrationError, "inside"):
            run_provider_assisted_pipeline(
                self.bundle,
                self.run,
                provider="Together",
                ledger_path=self.root / "outside.jsonl",
                decision_dir=self.decisions,
                call=fake,
                risk_catalog=RISK_CATALOG,
            )
        with self.assertRaisesRegex(OrchestrationError, "single"):
            run_provider_assisted_pipeline(
                self.bundle,
                self.run,
                provider="Together",
                ledger_path=self.run / "other.jsonl",
                decision_dir=self.decisions,
                call=fake,
                risk_catalog=RISK_CATALOG,
            )
        with self.assertRaisesRegex(OrchestrationError, "callable"):
            run_provider_assisted_pipeline(
                self.bundle,
                self.run,
                provider="Together",
                ledger_path=self.ledger,
                decision_dir=self.decisions,
                call=None,
                risk_catalog=RISK_CATALOG,
            )
        self.assertEqual([], fake.invocations)

    def test_existing_offline_run_is_rejected_before_provider_work(self):
        run_offline_pipeline(self.bundle, self.run, risk_catalog=RISK_CATALOG)
        fake = ResumableFakeCall()
        with self.assertRaisesRegex(OrchestrationError, "not admitted"):
            run_provider_assisted_pipeline(
                self.bundle,
                self.run,
                provider="Together",
                ledger_path=self.ledger,
                decision_dir=self.decisions,
                call=fake,
                risk_catalog=RISK_CATALOG,
            )
        self.assertEqual([], fake.invocations)

    def test_pinned_nexus_interfaces_share_the_exact_provider_runtime(self):
        engine = object()
        detector = object()
        checker = object()
        environment = {"OPENROUTER_API_KEY": "fixture-only"}
        transport = object()
        fake = ResumableFakeCall()
        with (
            patch(
                "model_cards.orchestration.load_pinned_nexus_catalog",
                return_value=RISK_CATALOG,
            ),
            patch(
                "model_cards.orchestration.build_nexus_openrouter_inference_engine",
                return_value=engine,
            ) as build_engine,
            patch(
                "model_cards.orchestration.NexusGenericRiskDetector",
                return_value=detector,
            ) as build_detector,
            patch(
                "model_cards.orchestration.OpenRouterApplicabilityChecker",
                return_value=checker,
            ) as build_checker,
        ):
            actual = _build_risk_interfaces(
                RISK_CATALOG,
                provider="Together",
                ledger_path=self.ledger,
                decision_dir=self.decisions,
                environment=environment,
                transport=transport,
                call=fake,
                max_risks=4,
            )

        self.assertEqual((detector, checker, "nexus_provider_enabled"), actual)
        build_engine.assert_called_once_with(
            provider="Together",
            ledger_path=self.ledger,
            decision_dir=self.decisions,
            environment=environment,
            transport=transport,
            call=fake,
        )
        build_detector.assert_called_once_with(engine, max_risks=4)
        build_checker.assert_called_once_with(
            provider="Together",
            ledger_path=self.ledger,
            decision_dir=self.decisions,
            environment=environment,
            transport=transport,
            call=fake,
        )


if __name__ == "__main__":
    unittest.main()
