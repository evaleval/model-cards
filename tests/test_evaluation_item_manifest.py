from __future__ import annotations

from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from io import StringIO
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock
import unittest

from jsonschema import Draft202012Validator

from evaluation.item_manifest import (
    ConditionRun,
    ItemManifestError,
    _condition_subjects,
    _file_binding,
    _load_run,
    build_evaluation_material,
    main as manifest_main,
    validate_item_manifest,
    validate_reviewer_packet,
    validate_target_sheet,
)
from model_cards.cli import main as modelcards_main
from model_cards.quality_report import build_quality_report
from model_cards.risk_mapping import ApplicabilityDecision, ApplicabilityStatus
from model_cards.source_bundle import collect_hf_source_bundle
from tests.test_quality_report import REQUEST, REVISION, _HubAdapter
from tests.test_offline_component_integration import (
    _HAS_FACTREASONER,
    _HAS_NEXUS,
    _build_family_provider_run,
)


class EvaluationItemManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.bundle = cls.root / "bundle"
        collect_hf_source_bundle(
            "acme/Quality",
            cls.bundle,
            _HubAdapter(precision="float16"),
            revision=REVISION,
        )
        cls.batch = cls.root / "batch"
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr), mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("offline evaluation fixture contacted network"),
        ):
            status = modelcards_main(
                [
                    "batch",
                    json.dumps([REQUEST]),
                    "--output",
                    str(cls.batch),
                    "--offline-bundle",
                    f"{REQUEST}={cls.bundle}",
                ]
            )
        if status != 0:
            raise AssertionError(f"evaluation fixture generation failed: {stderr.getvalue()}")
        cls.run_root = next(cls.batch.glob("targets/*"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def material(self):
        return build_evaluation_material(
            [
                ConditionRun("A", "target-blind-alpha", self.run_root),
                ConditionRun("B", "target-blind-alpha", self.run_root),
            ],
            study_unit_id="study-unit-alpha",
            blinding_key=b"private-test-blinding-key-32bytes!!",
        )

    @unittest.skipUnless(
        _HAS_NEXUS and _HAS_FACTREASONER,
        "exact pinned Nexus and IBM FactReasoner extras are required",
    )
    def test_family_risk_item_binds_complete_authorization_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fixture = _build_family_provider_run(Path(temporary))
            # Provider orchestration consumes the caller's frozen bundle in place,
            # whereas an evaluation condition is a self-contained batch run.  Give
            # this integration fixture the same embedded replay surface required by
            # the quality-report/evaluation contract.
            shutil.copytree(fixture.bundle, fixture.run / "source-bundle")
            manifest, _packets, _target_sheets = build_evaluation_material(
                [ConditionRun("A", "target-family-alpha", fixture.run)],
                study_unit_id="study-unit-family-alpha",
                blinding_key=b"private-test-blinding-key-32bytes!!",
            )
            risk_item = next(
                item for item in manifest["items"] if item["item_kind"] == "risk"
            )
            self.assertTrue(risk_item["conditions"][0]["evidence_bindings"])
            bindings = {
                (binding["artifact_name"], binding["json_pointer"])
                for binding in risk_item["conditions"][0]["artifact_bindings"]
            }
            self.assertTrue(
                {
                    ("family-risk-authorizations.json", "/use_contexts/0"),
                    (
                        "family-risk-authorizations.json",
                        "/applicability_decisions/0",
                    ),
                    ("family-risk-authorizations.json", "/authorizations/0"),
                }.issubset(bindings)
            )

            loaded = _load_run(
                ConditionRun("A", "target-family-alpha", fixture.run)
            )
            candidate = loaded.risk_mapping.candidates[0]
            original_decision = loaded.risk_mapping.decisions[0]
            decision_binding = next(
                binding
                for binding in risk_item["conditions"][0]["artifact_bindings"]
                if binding["artifact_name"] == "risk-mapping.json"
                and binding["json_pointer"] == "/taxonomy_mapping/decisions/0"
            )
            expected_decision_digest = hashlib.sha256(
                json.dumps(
                    original_decision.to_dict(),
                    allow_nan=False,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                ).encode("utf-8")
            ).hexdigest()
            self.assertEqual(
                decision_binding["record_sha256"], expected_decision_digest
            )
            self.assertNotEqual(
                decision_binding["record_sha256"], candidate.candidate_sha256
            )
            with self.assertRaisesRegex(ItemManifestError, "differs from its JSON Pointer"):
                _file_binding(
                    loaded,
                    "risk-mapping.json",
                    "/taxonomy_mapping/candidates/0",
                    original_decision.to_dict(),
                )
            with self.assertRaisesRegex(ItemManifestError, "unresolved"):
                _file_binding(
                    loaded,
                    "risk-mapping.json",
                    "/taxonomy_mapping/decisions/999",
                    original_decision.to_dict(),
                )
            withheld = ApplicabilityDecision.for_candidate(
                candidate,
                status=ApplicabilityStatus.WITHHELD,
                checker=original_decision.checker,
                method=original_decision.method,
                reason="not_applicable_to_documented_context",
                rationale=(
                    "The bounded test decision withholds this risk while retaining "
                    "its exact use-context evidence for independent review."
                ),
            )
            risk_artifact = deepcopy(
                loaded.artifact_values["risk-mapping.json"]
            )
            risk_artifact["taxonomy_mapping"]["decisions"][0] = (
                withheld.to_dict()
            )
            withheld_run = replace(
                loaded,
                risk_mapping=SimpleNamespace(
                    candidates=(candidate,),
                    decisions=(withheld,),
                ),
                risk_derivations=(),
                artifact_values={
                    **loaded.artifact_values,
                    "risk-mapping.json": risk_artifact,
                },
            )
            subjects = _condition_subjects(
                withheld_run,
                b"private-test-blinding-key-32bytes!!",
            )
            withheld_subject = subjects[f"risk:{candidate.risk_id}"]
            self.assertTrue(withheld_subject["evidence_bindings"])
            self.assertTrue(
                any(
                    binding["artifact_name"]
                    == "family-risk-authorizations.json"
                    for binding in withheld_subject["artifact_bindings"]
                )
            )

    def test_builder_is_exhaustive_artifact_bound_and_public_packet_is_blinded(self) -> None:
        manifest, packets, target_sheets = self.material()
        private_schema = json.loads(
            (
                Path(__file__).parents[1]
                / "evaluation"
                / "item-manifest.schema.json"
            ).read_text(encoding="utf-8")
        )
        public_schema = json.loads(
            (
                Path(__file__).parents[1]
                / "evaluation"
                / "reviewer-packet.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(private_schema)
        Draft202012Validator(private_schema).validate(manifest)
        validate_item_manifest(manifest)

        gate_count = len(json.loads((self.run_root / "claim-gates.json").read_text())["records"])
        omission_count = len(json.loads((self.run_root / "omissions.json").read_text())["records"])
        publication_count = len(
            json.loads((self.run_root / "publication-validation.json").read_text())["records"]
        )
        repair_count = len(json.loads((self.run_root / "repairs.json").read_text())["records"])
        risk_count = len(
            json.loads((self.run_root / "risk-mapping.json").read_text())[
                "taxonomy_mapping"
            ]["candidates"]
        )
        kinds = Counter(item["item_kind"] for item in manifest["items"])
        self.assertEqual(gate_count, kinds["claim"])
        self.assertEqual(omission_count + publication_count, kinds["field"])
        self.assertEqual(risk_count, kinds["risk"])
        self.assertEqual(
            gate_count * 4
            + omission_count
            + publication_count
            + repair_count
            + risk_count,
            kinds["warning"],
        )
        self.assertTrue(
            all(
                [entry["condition"] for entry in item["conditions"]] == ["A", "B"]
                for item in manifest["items"]
            )
        )
        evidence = [
            evidence
            for item in manifest["items"]
            for condition in item["conditions"]
            for evidence in condition["evidence_bindings"]
        ]
        self.assertTrue(evidence)
        self.assertTrue(all(entry["source_sha256"] for entry in evidence))
        self.assertTrue(
            any(entry["coordinate"]["json_pointer"] is not None for entry in evidence)
        )
        self.assertTrue(
            any(
                condition["disposition"]["factreasoner"]["phases"]
                for item in manifest["items"]
                for condition in item["conditions"]
            )
        )
        self.assertTrue(
            all(
                any(
                    artifact["artifact_name"]
                    == "family-risk-authorizations.json"
                    for artifact in condition["artifacts"]
                )
                for target in manifest["targets"]
                for condition in target["condition_artifacts"]
            )
        )
        pipeline_result = json.loads(
            (self.run_root / "pipeline-result.json").read_text(encoding="utf-8")
        )
        quality_target = build_quality_report(self.batch).to_dict()["targets"][0]
        for condition in manifest["targets"][0]["condition_artifacts"]:
            self.assertEqual(
                condition["pipeline_result_sha256"],
                pipeline_result["result_sha256"],
            )
            self.assertEqual(
                condition["pipeline_result_sha256"],
                quality_target["run_sha256"],
            )
            self.assertEqual(
                condition["source_input_surface_sha256"],
                quality_target["surfaces"]["source_inputs"],
            )
            self.assertEqual(
                condition["treatment_surface_sha256"],
                quality_target["surfaces"]["treatment"],
            )

        for packet in packets.values():
            Draft202012Validator(public_schema).validate(packet)
            validate_reviewer_packet(packet, manifest)
            encoded = json.dumps(packet, sort_keys=True)
            self.assertNotIn("acme/Quality", encoded)
            self.assertNotIn(REVISION, encoded)
            self.assertNotIn(str(self.root), encoded)
            self.assertNotIn("source_uri\"", encoded)
            expected_kind = (
                {"claim", "field", "risk"}
                if packet["phase"] == "primary"
                else {"warning"}
            )
            expected_count = sum(
                item["item_kind"] in expected_kind
                and next(
                    condition["present"]
                    for condition in item["conditions"]
                    if condition["condition"] == packet["condition"]
                )
                for item in manifest["items"]
            )
            self.assertEqual(expected_count, len(packet["items"]))
            self.assertEqual(
                packet["randomization_sha256"],
                hashlib.sha256(
                    json.dumps(
                        [item["item_id"] for item in packet["items"]],
                        allow_nan=False,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ).encode("utf-8")
                ).hexdigest(),
            )
            if packet["phase"] == "primary":
                self.assertNotIn("warning_present", encoded)
                self.assertNotIn("warning_presentation", encoded)
                self.assertNotIn("system_disposition", encoded)
                for item in packet["items"]:
                    if item["item_kind"] == "field":
                        self.assertEqual(
                            set(item["display_value"]),
                            {"stage"},
                        )
                        self.assertNotIn("source_present", item["display_value"])
                        self.assertNotIn("candidate_count", item["display_value"])
            else:
                self.assertTrue(
                    all("warning_presentation" in item for item in packet["items"])
                )
        self.assertNotEqual(
            [
                item["item_id"]
                for item in packets[("target-blind-alpha", "A", "primary")]["items"]
            ],
            [
                item["item_id"]
                for item in packets[("target-blind-alpha", "B", "primary")]["items"]
            ],
        )
        sheet = target_sheets["target-blind-alpha"]
        validate_target_sheet(sheet, manifest)
        self.assertEqual(sheet["exact_target"]["model_id"], "acme/Quality")
        self.assertEqual(sheet["exact_target"]["revision"], REVISION)
        sheet_text = json.dumps(sheet, sort_keys=True)
        self.assertNotIn('"condition"', sheet_text)
        self.assertNotIn(str(self.root), sheet_text)

    def test_manifest_and_packet_tampering_are_rejected(self) -> None:
        manifest, packets, _target_sheets = self.material()
        tampered = deepcopy(manifest)
        tampered["items"][0]["conditions"][0]["present"] = not tampered["items"][0][
            "conditions"
        ][0]["present"]
        with self.assertRaisesRegex(ItemManifestError, "digest"):
            validate_item_manifest(tampered)

        packet = deepcopy(packets[("target-blind-alpha", "A", "primary")])
        packet["items"].pop()
        with self.assertRaises(ItemManifestError):
            validate_reviewer_packet(packet, manifest)

        receipt_tampered = deepcopy(manifest)
        present = next(
            condition
            for item in receipt_tampered["items"]
            for condition in item["conditions"]
            if condition["present"] and condition["artifact_bindings"]
        )
        present["artifact_bindings"][0]["record_sha256"] = "0" * 64
        receipt_payload = dict(receipt_tampered)
        receipt_payload.pop("manifest_sha256")
        receipt_tampered["manifest_sha256"] = hashlib.sha256(
            json.dumps(
                receipt_payload,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        with self.assertRaisesRegex(ItemManifestError, "native hash inventory"):
            validate_item_manifest(receipt_tampered)

    def test_condition_absent_subject_stays_private_and_is_not_reviewed(self) -> None:
        def condition_subjects(run, key):
            values = dict(_condition_subjects(run, key))
            if run.spec.condition == "B":
                claim_key = next(
                    subject_key
                    for subject_key, subject in values.items()
                    if subject["item_kind"] == "claim"
                )
                values.pop(claim_key)
            return values

        with mock.patch(
            "evaluation.item_manifest._condition_subjects",
            side_effect=condition_subjects,
        ):
            manifest, packets, _target_sheets = self.material()

        absent = next(
            item
            for item in manifest["items"]
            if item["item_kind"] == "claim"
            and [entry["present"] for entry in item["conditions"]]
            == [True, False]
        )
        a_ids = {
            item["item_id"]
            for item in packets[("target-blind-alpha", "A", "primary")]["items"]
        }
        b_ids = {
            item["item_id"]
            for item in packets[("target-blind-alpha", "B", "primary")]["items"]
        }
        self.assertIn(absent["item_id"], a_ids)
        self.assertNotIn(absent["item_id"], b_ids)
        self.assertEqual([], absent["conditions"][1]["artifact_bindings"])
        self.assertEqual([], absent["conditions"][1]["evidence_bindings"])
        for packet in packets.values():
            validate_reviewer_packet(packet, manifest)

    def test_single_condition_census_and_deterministic_packet_order(self) -> None:
        runs = [
            ConditionRun("A", f"target-census-{index:02d}", self.run_root)
            for index in range(12)
        ]
        manifest, packets, target_sheets = build_evaluation_material(
            runs,
            study_unit_id="study-unit-census",
            blinding_key=b"private-census-blinding-key-32bytes!",
        )
        _single_manifest, repeated_packets, _single_sheets = build_evaluation_material(
            [runs[0]],
            study_unit_id="study-unit-census",
            blinding_key=b"private-census-blinding-key-32bytes!",
        )
        for phase in ("primary", "warning_followup"):
            identity = ("target-census-00", "A", phase)
            self.assertEqual(
                [item["item_id"] for item in packets[identity]["items"]],
                [item["item_id"] for item in repeated_packets[identity]["items"]],
            )
        self.assertEqual(manifest["conditions"], ["A"])
        self.assertEqual(len(manifest["targets"]), 12)
        self.assertEqual(len(target_sheets), 12)
        self.assertEqual(len(packets), 24)
        self.assertEqual(
            {phase for _target, _condition, phase in packets},
            {"primary", "warning_followup"},
        )
        validate_item_manifest(manifest)
        for packet in packets.values():
            validate_reviewer_packet(packet, manifest)

    def test_cli_writes_new_private_manifest_and_refuses_overwrite(self) -> None:
        output = self.root / "evaluation-output"
        key_path = self.root / "blinding.key"
        key_path.write_bytes(b"another-private-blinding-key-32bytes")
        key_path.chmod(0o600)
        manifest_path = output / "private-item-manifest.json"
        packet_dir = output / "packets"
        args = [
            "--run",
            f"A:target-blind-cli={self.run_root}",
            "--run",
            f"B:target-blind-cli={self.run_root}",
            "--study-unit-id",
            "study-unit-cli",
            "--blinding-key-file",
            str(key_path),
            "--private-manifest",
            str(manifest_path),
            "--public-packet-dir",
            str(packet_dir),
        ]
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            self.assertEqual(manifest_main(args), 0, stderr.getvalue())
        self.assertEqual(manifest_path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(list(packet_dir.glob("*.json"))), 5)
        target_sheet = json.loads(
            (packet_dir / "target-blind-cli-target.json").read_text(encoding="utf-8")
        )
        self.assertEqual(target_sheet["exact_target"]["model_id"], "acme/Quality")
        self.assertNotIn("condition", target_sheet)
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(manifest_main(args), 2)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
