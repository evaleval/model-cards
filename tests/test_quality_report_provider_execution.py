from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import shutil
import tempfile
from unittest import mock
import unittest

from model_cards.cli import main
from model_cards.factreasoner import IBMFactReasonerAdapter
from model_cards.family_risk import (
    FAMILY_RISK_BRIDGE_VERSION,
    FamilyRiskAuthorizationReport,
)
from model_cards.orchestration import run_provider_assisted_pipeline
from model_cards.privacy import audit_public_tree
from model_cards.provider import PINNED_PROVIDER
from model_cards.provider_execution import (
    PROVIDER_EXECUTION_MANIFEST_FILENAME,
    ProviderExecutionRunEvidence,
)
from model_cards.quality_report import (
    QualityReportError,
    build_quality_report,
    serialize_quality_report,
)
from model_cards.source_bundle import collect_hf_source_bundle
from tests.test_offline_component_integration import (
    REVISION,
    SYNTHETIC_KEY,
    USE_STATEMENT,
    _BundleAdapter,
    _OfflineOpenRouterTransport,
)
from tests.test_orchestration import RISK_CATALOG


REQUEST = f"acme/Exact@{REVISION}"


def _canonical(value: object) -> bytes:
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


class ProviderExecutionQualityReportTests(unittest.TestCase):
    """Exercise quality admission of real, receipt-bound offline provider runs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.bundle = cls.root / "bundle"
        cls.batch = cls.root / "provider-batch"
        collect_hf_source_bundle(
            "acme/Exact",
            cls.bundle,
            _BundleAdapter(),
            revision=REVISION,
        )

        transport = _OfflineOpenRouterTransport()

        def assisted(*args, **kwargs):
            with mock.patch(
                "model_cards.orchestration._build_risk_interfaces",
                return_value=(None, None, "nexus_dependency_unavailable"),
            ), mock.patch.object(
                IBMFactReasonerAdapter,
                "installation_status",
                return_value="ibm_factreasoner_dependency_unavailable",
            ):
                return run_provider_assisted_pipeline(
                    *args,
                    **kwargs,
                    environment={"OPENROUTER_API_KEY": SYNTHETIC_KEY},
                    transport=transport,
                    risk_catalog=RISK_CATALOG,
                    max_risks=1,
                )

        stdout = StringIO()
        stderr = StringIO()
        with mock.patch(
            "model_cards.cli.run_provider_assisted_pipeline",
            side_effect=assisted,
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(
                [
                    "batch",
                    json.dumps([REQUEST]),
                    "--output",
                    str(cls.batch),
                    "--provider",
                    PINNED_PROVIDER,
                    "--offline-bundle",
                    f"{REQUEST}={cls.bundle}",
                ]
            )
        if result != 0:
            raise AssertionError(
                "offline provider batch fixture failed: "
                + stderr.getvalue()
                + stdout.getvalue()
            )
        cls.batch_summary = json.loads(stdout.getvalue())
        cls.run_root = next(cls.batch.glob("targets/*"))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def copied_batch(self, name: str) -> tuple[Path, Path]:
        destination = self.root / name
        shutil.copytree(self.batch, destination)
        return destination, next(destination.glob("targets/*"))

    def build_report(self, batch: Path):
        with mock.patch(
            "model_cards.quality_report.load_pinned_nexus_catalog",
            return_value=RISK_CATALOG,
        ):
            return build_quality_report(batch)

    def test_accepts_bound_manifest_without_public_leakage(self) -> None:
        admission = json.loads(
            (self.run_root / "provider-orchestration.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            FAMILY_RISK_BRIDGE_VERSION,
            admission["family_risk_bridge_version"],
        )
        family_report = FamilyRiskAuthorizationReport.from_dict(
            json.loads(
                (self.run_root / "family-risk-authorizations.json").read_text(
                    encoding="utf-8"
                )
            )
        )
        self.assertEqual((), family_report.nexus_inputs)

        provider_result = json.loads(
            (self.run_root / "provider-result.json").read_text(encoding="utf-8")
        )
        self.assertIsNotNone(provider_result["provider_execution_sha256"])
        self.assertTrue(
            any(
                item.endswith("/" + PROVIDER_EXECUTION_MANIFEST_FILENAME)
                for item in self.batch_summary["targets"][0]["artifacts"]
            )
        )

        execution = ProviderExecutionRunEvidence.load(self.run_root)
        self.assertEqual(
            provider_result["provider_execution_sha256"],
            execution.manifest.manifest_sha256,
        )
        self.assertTrue(execution.manifest.executions)

        report = self.build_report(self.batch)
        encoded = serialize_quality_report(report)
        public_card = (self.run_root / "public-card.json").read_bytes()
        public_audit = audit_public_tree(self.run_root, ("public-card.json",))
        self.assertTrue(public_audit.passed, public_audit.to_dict())

        for private_value in (
            SYNTHETIC_KEY.encode("utf-8"),
            str(self.root).encode("utf-8"),
            USE_STATEMENT.encode("utf-8"),
            b'"executions"',
            b'"provider_execution_sha256"',
            b"provider-decisions/",
        ):
            with self.subTest(private_value=private_value):
                self.assertNotIn(private_value, encoded)
                self.assertNotIn(private_value, public_card)

    def test_rejects_tampered_normalized_decision(self) -> None:
        batch, run = self.copied_batch("provider-decision-tampered")
        decision_path = next((run / "provider-decisions").glob("*.json"))
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
        decision["tampered"] = True
        decision_path.write_bytes(_canonical(decision))

        with self.assertRaises(QualityReportError):
            self.build_report(batch)

    def test_rejects_tampered_family_authorization(self) -> None:
        batch, run = self.copied_batch("family-authorization-tampered")
        path = run / "family-risk-authorizations.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["report_sha256"] = "0" * 64
        path.write_bytes(_canonical(report))

        with self.assertRaises(QualityReportError):
            self.build_report(batch)

    def test_rejects_missing_bound_manifest(self) -> None:
        batch, run = self.copied_batch("provider-manifest-missing")
        (run / PROVIDER_EXECUTION_MANIFEST_FILENAME).unlink()

        with self.assertRaises(QualityReportError):
            self.build_report(batch)

    def test_rejects_nonempty_ledger_when_result_disclaims_execution(self) -> None:
        batch, run = self.copied_batch("provider-result-disclaims-execution")
        (run / PROVIDER_EXECUTION_MANIFEST_FILENAME).unlink()
        result_path = run / "provider-result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result["provider_execution_sha256"] = None
        payload = {key: value for key, value in result.items() if key != "result_sha256"}
        result["result_sha256"] = hashlib.sha256(
            _canonical(payload).removesuffix(b"\n")
        ).hexdigest()
        result_path.write_bytes(_canonical(result))
        batch_result_path = batch / "batch-result.json"
        batch_result = json.loads(batch_result_path.read_text(encoding="utf-8"))
        artifacts = batch_result["targets"][0]["artifacts"]
        batch_result["targets"][0]["artifacts"] = [
            item
            for item in artifacts
            if not item.endswith("/" + PROVIDER_EXECUTION_MANIFEST_FILENAME)
        ]
        batch_result_path.write_bytes(_canonical(batch_result))

        with self.assertRaisesRegex(QualityReportError, "lacks a result binding"):
            self.build_report(batch)

    def test_rejects_valid_but_stale_manifest_result_binding(self) -> None:
        batch, run = self.copied_batch("provider-manifest-stale")
        manifest_path = run / PROVIDER_EXECUTION_MANIFEST_FILENAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["max_risks"] = 2
        payload = {
            key: value for key, value in manifest.items() if key != "manifest_sha256"
        }
        manifest["manifest_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
        manifest_path.write_bytes(_canonical(manifest))

        with self.assertRaises(QualityReportError):
            self.build_report(batch)


if __name__ == "__main__":
    unittest.main()
