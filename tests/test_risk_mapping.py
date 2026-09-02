from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import importlib.util
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from model_cards.risk_mapping import (
    ApplicabilityDecision,
    ApplicabilityStatus,
    INFERENCE_MODEL,
    MappingStatus,
    NEXUS_PACKAGE_VERSION,
    NexusGenericRiskDetector,
    NexusSelection,
    RiskCatalog,
    RiskMappingError,
    TaxonomyRisk,
    UseContext,
    load_pinned_nexus_catalog,
    map_candidate_risks,
    unavailable_risk_report,
)
from model_cards.schema import validate_field_value


RISK = TaxonomyRisk(
    risk_id="atlas-output-with-personal-data",
    name="Output with personal data",
    description="A model might reveal personal data in generated output.",
    source_url="https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas",
)
OTHER_RISK = TaxonomyRisk(
    risk_id="atlas-impact-on-the-environment",
    name="Impact on the environment",
    description="Training and operating large models can consume energy and water.",
    source_url="https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas",
    mitigation_ids=("mitigation:measure_energy",),
)


def context(identifier: str = "context:personal_assistant") -> UseContext:
    return UseContext(
        context_id=identifier,
        description="The publisher intends the model for personalized assistant responses.",
        supporting_fields=("use_and_risk.intended_uses[0]",),
        supporting_candidate_ids=("claim-" + "a" * 24,),
        source_refs=("src_" + "b" * 24,),
    )


class Detector:
    detector_name = "ai_atlas_nexus.generic_usecase"
    detector_version = NEXUS_PACKAGE_VERSION
    inference_model = INFERENCE_MODEL
    inference_config_sha256 = "c" * 64

    def __init__(self, selections=()):
        self.selections = tuple(selections)
        self.calls = 0

    def detect(self, contexts, catalog):
        self.calls += 1
        return self.selections


class Checker:
    def __init__(self, status=ApplicabilityStatus.ACCEPTED):
        self.status = status
        self.calls = 0

    def assess(self, candidate, contexts):
        self.calls += 1
        return ApplicabilityDecision.for_candidate(
            candidate,
            status=self.status,
            checker="deepseek/deepseek-v4-flash-0731",
            method="bounded_use_context_applicability",
            reason=(
                "specific_use_context_supported"
                if self.status is ApplicabilityStatus.ACCEPTED
                else "risk_not_specific_to_context"
            ),
            rationale=(
                "The accepted publisher use context specifically involves personalized "
                "responses, making disclosure of personal data a relevant candidate risk."
            ),
        )


class RiskMappingTests(unittest.TestCase):
    @unittest.skipUnless(
        importlib.util.find_spec("ai_atlas_nexus") is not None,
        "optional pinned Nexus dependency is not installed",
    )
    def test_pinned_catalog_loading_does_not_corrupt_machine_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            catalog = load_pinned_nexus_catalog()
        self.assertGreater(len(catalog.risks), 0)
        self.assertEqual("", stdout.getvalue())
        self.assertEqual("", stderr.getvalue())

    @unittest.skipUnless(
        importlib.util.find_spec("ai_atlas_nexus") is not None,
        "optional pinned Nexus dependency is not installed",
    )
    def test_real_nexus_generic_interface_accepts_offline_grounded_context(self) -> None:
        from ai_atlas_nexus.blocks.inference import (
            InferenceEngine,
            TextGenerationInferenceOutput,
        )

        catalog = load_pinned_nexus_catalog()
        selected = catalog.risks[0]

        class OfflineInferenceEngine(InferenceEngine):
            def __init__(self) -> None:
                # Do not initialize a network client; the real Nexus generic
                # detector only needs the typed engine and generate interface.
                self.model_name_or_path = INFERENCE_MODEL
                self.calls = 0

            def prepare_credentials(self, credentials):
                return {}

            def create_client(self, credentials=None):
                return object()

            def generate(
                self,
                prompts,
                response_format=None,
                postprocessors=None,
                verbose=True,
            ):
                self.calls += 1
                self.assert_schema(response_format, postprocessors)
                return [
                    TextGenerationInferenceOutput(prediction=[selected.name])
                    for _prompt in prompts
                ]

            def chat(
                self,
                messages,
                tools=None,
                response_format=None,
                postprocessors=None,
                verbose=True,
            ):
                raise AssertionError("generic batch risk detection must call generate")

            @staticmethod
            def assert_schema(response_format, postprocessors) -> None:
                if not isinstance(response_format, dict):
                    raise AssertionError("Nexus did not provide its list schema")
                if selected.name not in response_format.get("items", {}).get("enum", []):
                    raise AssertionError("Nexus schema omitted the selected taxonomy risk")
                if postprocessors != ["list_of_str"]:
                    raise AssertionError("Nexus did not request its list postprocessor")

        engine = OfflineInferenceEngine()
        detector = NexusGenericRiskDetector(engine, max_risks=1)
        use_context = context()
        selections = detector.detect((use_context,), catalog)
        self.assertEqual(1, engine.calls)
        self.assertEqual(
            (NexusSelection(selected.risk_id, (use_context.context_id,)),),
            selections,
        )

    def setUp(self) -> None:
        self.catalog = RiskCatalog.build((RISK, OTHER_RISK))

    def test_zero_grounded_contexts_emit_zero_risks_without_detector_or_checker(self) -> None:
        detector = Detector((NexusSelection(RISK.risk_id, ("context:invented",)),))
        checker = Checker()
        report = map_candidate_risks((), self.catalog, detector, checker)
        self.assertEqual(MappingStatus.COMPLETED, report.status)
        self.assertEqual("no_grounded_use_context", report.reason)
        self.assertEqual((), report.candidates)
        self.assertEqual((), report.included_risks)
        self.assertEqual(0, detector.calls)
        self.assertEqual(0, checker.calls)

    def test_generic_adapter_uses_exact_interface_and_covers_every_context(self) -> None:
        contexts = tuple(context(f"context:use_{index}") for index in range(5))

        class FakeNexus:
            def __init__(self) -> None:
                self.calls = []

            def identify_risks_from_usecases(self, usecases, engine, **kwargs):
                self.calls.append((tuple(usecases), engine, kwargs))
                return [[SimpleNamespace(id=RISK.risk_id)] for _item in usecases]

        nexus = FakeNexus()
        engine = object()
        detector = NexusGenericRiskDetector(engine, max_risks=2)
        with patch("model_cards.risk_mapping._new_nexus_instance", return_value=nexus):
            selections = detector.detect(contexts, self.catalog)

        self.assertEqual([2, 2, 1], [len(item[0]) for item in nexus.calls])
        for _usecases, actual_engine, kwargs in nexus.calls:
            self.assertIs(engine, actual_engine)
            self.assertEqual(
                {
                    "taxonomy": "ibm-risk-atlas",
                    "max_risk": 2,
                    "zero_shot_only": True,
                    "batch_inference": True,
                },
                kwargs,
            )
        self.assertEqual(
            (NexusSelection(RISK.risk_id, tuple(item.context_id for item in contexts)),),
            selections,
        )

    def test_specific_nexus_candidate_requires_applicability_and_is_schema_valid(self) -> None:
        use_context = context()
        detector = Detector((NexusSelection(RISK.risk_id, (use_context.context_id,)),))
        checker = Checker()
        report = map_candidate_risks((use_context,), self.catalog, detector, checker)
        self.assertEqual(1, detector.calls)
        self.assertEqual(1, checker.calls)
        self.assertEqual(1, len(report.candidates))
        self.assertEqual(1, len(report.included_risks))
        value = report.included_risks[0]
        validate_field_value("use_and_risk.identified_risks[0]", value)
        self.assertEqual("taxonomy_identified", value["identification_origin"])
        self.assertEqual("generated_unreviewed", value["review_status"])
        self.assertEqual("ai_atlas_nexus", value["mapping_provenance"]["method"])
        self.assertEqual(INFERENCE_MODEL, value["mapping_provenance"]["inference_model"])
        self.assertEqual(RISK.risk_id, value["risk_id"])
        self.assertEqual((use_context.context_id,), report.candidates[0].context_ids)
        self.assertNotIn("publisher_reported", str(value))

    def test_withheld_applicability_never_projects_a_candidate(self) -> None:
        use_context = context()
        report = map_candidate_risks(
            (use_context,),
            self.catalog,
            Detector((NexusSelection(RISK.risk_id, (use_context.context_id,)),)),
            Checker(ApplicabilityStatus.WITHHELD),
        )
        self.assertEqual(1, len(report.candidates))
        self.assertEqual(ApplicabilityStatus.WITHHELD, report.decisions[0].status)
        self.assertEqual((), report.included_risks)

    def test_unknown_taxonomy_id_and_invented_context_fail_closed(self) -> None:
        use_context = context()
        for selection in (
            NexusSelection("atlas-not-in-this-release", (use_context.context_id,)),
            NexusSelection(RISK.risk_id, ("context:invented",)),
        ):
            with self.subTest(selection=selection), self.assertRaises(RiskMappingError):
                map_candidate_risks(
                    (use_context,), self.catalog, Detector((selection,)), Checker()
                )

    def test_benchmark_detector_cannot_be_relabelled_as_generic_model_risk_detector(self) -> None:
        use_context = context()
        detector = Detector()
        detector.detector_name = "ai_atlas_nexus.benchmark_risk_detector"
        with self.assertRaisesRegex(RiskMappingError, "generic Nexus"):
            map_candidate_risks((use_context,), self.catalog, detector, Checker())

    def test_grounding_context_rejects_generic_padding(self) -> None:
        with self.assertRaisesRegex(RiskMappingError, "supporting card fields"):
            UseContext(
                context_id="context:generic",
                description="This is an AI model.",
                supporting_fields=(),
                supporting_candidate_ids=("claim-" + "a" * 24,),
                source_refs=("src_" + "b" * 24,),
            )

    def test_tampered_or_stale_applicability_decision_is_rejected(self) -> None:
        use_context = context()
        detector = Detector((NexusSelection(RISK.risk_id, (use_context.context_id,)),))

        class StaleChecker(Checker):
            def assess(self, candidate, contexts):
                decision = super().assess(candidate, contexts)
                return replace(decision, candidate_sha256="0" * 64)

        with self.assertRaises(RiskMappingError):
            map_candidate_risks((use_context,), self.catalog, detector, StaleChecker())

        candidate_report = map_candidate_risks(
            (use_context,),
            self.catalog,
            Detector((NexusSelection(RISK.risk_id, (use_context.context_id,)),)),
            Checker(),
        )
        with self.assertRaisesRegex(RiskMappingError, "digest"):
            replace(candidate_report.decisions[0], rationale="A changed rationale that is long enough.")

    def test_taxonomy_mitigation_links_are_preserved_without_invention(self) -> None:
        use_context = context("context:training_service")
        report = map_candidate_risks(
            (use_context,),
            self.catalog,
            Detector((NexusSelection(OTHER_RISK.risk_id, (use_context.context_id,)),)),
            Checker(),
        )
        value = report.included_risks[0]
        self.assertEqual("linked", value["mitigation_assessment"])
        self.assertEqual(["mitigation:measure_energy"], value["mitigation_refs"])

    def test_unavailable_stage_is_visible_and_contains_no_placeholder_risks(self) -> None:
        report = unavailable_risk_report((context(),), self.catalog)
        self.assertEqual(MappingStatus.UNAVAILABLE, report.status)
        self.assertEqual("risk_provider_unavailable", report.reason)
        self.assertEqual((), report.candidates)
        self.assertEqual((), report.included_risks)

    def test_same_inputs_are_content_addressed_deterministically(self) -> None:
        use_context = context()
        def run():
            return map_candidate_risks(
                (use_context,),
                self.catalog,
                Detector((NexusSelection(RISK.risk_id, (use_context.context_id,)),)),
                Checker(),
            )
        first, second = run(), run()
        self.assertEqual(first.report_sha256, second.report_sha256)
        self.assertEqual(first.included_risks, second.included_risks)


if __name__ == "__main__":
    unittest.main()
