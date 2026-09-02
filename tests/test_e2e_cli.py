from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
from unittest import mock
import unittest

from model_cards.cli import build_parser, main
from model_cards.field_repair import (
    FieldRepairContext,
    FieldRepairRecord,
    RepairFinding,
    RepairOutcome,
    RepairReason,
)
from model_cards.models import TargetIdentity
from model_cards.official_sources import OfficialFetchStatus, OfficialRemoteObject
from model_cards.pipeline import PipelineResult
from model_cards.provider import ProviderTerminalAttemptError, RetryExhaustedError
from model_cards.quality_report import load_quality_report
from model_cards.publication_schema import validate_publication_card
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
)


COMMIT = "a" * 40
SECOND_COMMIT = "b" * 40


def _json_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


class _FixtureHubAdapter:
    def __init__(
        self,
        model_id: str,
        revision: str,
        *,
        sparse: bool = False,
    ) -> None:
        self.model_id = model_id
        self.revision = revision
        self.sparse = sparse

    def resolve_revision(self, model_id, requested_revision):
        if model_id != self.model_id:
            raise ValueError("unexpected fixture model")
        return self.revision

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        if self.sparse:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="fixture_unavailable")
        return RemoteObject(
            FetchStatus.OK,
            _json_bytes(
                {
                    "id": self.model_id,
                    "sha": self.revision,
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                }
            ),
        )

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if self.sparse:
            return RemoteObject(FetchStatus.UNAVAILABLE, reason_code="fixture_unavailable")
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    "# Exact target\n\n"
                    f"This frozen source describes {self.model_id} at {self.revision}.\n"
                ).encode("utf-8"),
            )
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                _json_bytes({"model_type": "fixture", "torch_dtype": "float16"}),
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class _LinkedFixtureHubAdapter(_FixtureHubAdapter):
    OFFICIAL_URL = "https://github.com/acme/collect"

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    "# Exact target\n\n"
                    f"This frozen source describes {self.model_id} at {self.revision}.\n\n"
                    f"[Official developer code]({self.OFFICIAL_URL})\n"
                ).encode("utf-8"),
            )
        return super().fetch_file(
            model_id, revision, repo_path, max_bytes=max_bytes
        )


class _FixtureOfficialAdapter:
    def fetch(self, url, *, max_bytes, max_redirects):
        if url != _LinkedFixtureHubAdapter.OFFICIAL_URL:
            return OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE,
                reason_code="fixture_not_provided",
            )
        return OfficialRemoteObject(
            OfficialFetchStatus.OK,
            content=b"Official developer documentation for the exact fixture target.",
            final_url=url,
            redirect_chain=(url,),
            media_type="text/plain",
        )


class E2ECommandLineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def bundle(
        self,
        model_id: str = "acme/Instruct",
        revision: str = COMMIT,
        *,
        sparse: bool = False,
    ) -> Path:
        destination = self.root / f"bundle-{len(list(self.root.glob('bundle-*')))}"
        collect_hf_source_bundle(
            model_id,
            destination,
            _FixtureHubAdapter(model_id, revision, sparse=sparse),
            revision=revision,
        )
        return destination

    def invoke(self, arguments, *, environment=None):
        stdout = StringIO()
        stderr = StringIO()
        patcher = mock.patch.dict(os.environ, environment or {}, clear=False)
        with patcher, redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(arguments)
        return result, stdout.getvalue(), stderr.getvalue()

    def assert_private_text_absent(self, text: str) -> None:
        for forbidden in (
            str(self.root),
            "/Users/",
            "/private/",
            "source body secret",
            "hf_super_secret_token",
            "Bearer ",
            "prompt",
            "provider_trace",
        ):
            self.assertNotIn(forbidden, text)

    def test_exact_generate_invocation_is_offline_private_and_resumable(self) -> None:
        self.assertEqual(build_parser().prog, "modelcards")
        frozen = self.bundle()
        output = self.root / "run"
        arguments = [
            "generate",
            "acme/Instruct",
            "--revision",
            COMMIT,
            "--output",
            str(output),
            "--offline-bundle",
            str(frozen),
        ]
        result, stdout, stderr = self.invoke(
            arguments,
            environment={"HF_TOKEN": "hf_super_secret_token"},
        )
        self.assertEqual(result, 0, stderr)
        summary = json.loads(stdout)
        self.assertEqual(set(summary), {"target", "status", "artifacts"})
        self.assertEqual(summary["target"], {"model_id": "acme/Instruct", "revision": COMMIT})
        self.assertEqual(summary["status"], "generated_unreviewed")
        self.assertIn("source-bundle/manifest.json", summary["artifacts"])
        self.assertIn("pipeline-result.json", summary["artifacts"])
        self.assertIn("audit-view.json", summary["artifacts"])
        self.assertIn("usage-summary.json", summary["artifacts"])
        for name in summary["artifacts"]:
            path = PurePosixPath(name)
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
        self.assert_private_text_absent(stdout + stderr)
        self.assertTrue((output / "public-card.json").is_file())
        usage = json.loads((output / "usage-summary.json").read_text())
        self.assertEqual(0, usage["metrics"]["paid_calls"])
        self.assertEqual("0", usage["metrics"]["committed_usd"])
        validate_publication_card(
            json.loads((output / "public-card.json").read_text())
        )
        expected = PipelineResult.from_dict(
            json.loads((output / "pipeline-result.json").read_text())
        )
        self.assertEqual(expected.target.model_id, "acme/Instruct")
        journal_before = (output / "journal.jsonl").read_bytes()

        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("resume attempted network collection"),
        ), mock.patch(
            "model_cards.cli.collect_hf_source_bundle",
            side_effect=AssertionError("resume recollected sources"),
        ):
            resumed, resumed_stdout, resumed_stderr = self.invoke(arguments[:-2])
        self.assertEqual(resumed, 0, resumed_stderr)
        self.assertEqual(json.loads(resumed_stdout), summary)
        self.assertEqual((output / "journal.jsonl").read_bytes(), journal_before)
        self.assert_private_text_absent(resumed_stdout + resumed_stderr)

        validated, validate_stdout, validate_stderr = self.invoke(
            ["validate", str(output / "pipeline-result.json")]
        )
        self.assertEqual(validated, 0, validate_stderr)
        self.assertEqual(json.loads(validate_stdout)["kind"], "pipeline_result")

    def test_generate_cli_rejects_every_unpinned_provider(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(
                [
                    "generate",
                    "acme/Instruct",
                    "--output",
                    "run",
                    "--provider",
                    "Baidu",
                ]
            )

    def test_normal_generate_automatically_freezes_and_replays_official_sources(self) -> None:
        output = self.root / "online-run"
        arguments = [
            "generate",
            "acme/Collect",
            "--revision",
            COMMIT,
            "--output",
            str(output),
        ]
        hub = _LinkedFixtureHubAdapter("acme/Collect", COMMIT)
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter", return_value=hub
        ), mock.patch(
            "model_cards.cli.StdlibOfficialSourceAdapter",
            return_value=_FixtureOfficialAdapter(),
        ) as official_factory:
            result, stdout, stderr = self.invoke(arguments)
        self.assertEqual(result, 0, stderr)
        summary = json.loads(stdout)
        self.assertIn("official-discovery.json", summary["artifacts"])
        self.assertIn("official-source-bundle/manifest.json", summary["artifacts"])
        self.assertIn("source-state.json", summary["artifacts"])
        self.assertEqual(
            "hf_and_official",
            json.loads((output / "source-state.json").read_text())["mode"],
        )
        official_factory.assert_called_once()
        allowed_hosts = set(official_factory.call_args.args[0])
        self.assertIn("github.com", allowed_hosts)
        self.assertIn("arxiv.org", allowed_hosts)
        self.assert_private_text_absent(stdout + stderr)

        journal_before = (output / "journal.jsonl").read_bytes()
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("resume attempted Hub access"),
        ), mock.patch(
            "model_cards.cli.StdlibOfficialSourceAdapter",
            side_effect=AssertionError("resume attempted official-source access"),
        ):
            resumed, resumed_stdout, resumed_stderr = self.invoke(arguments)
        self.assertEqual(resumed, 0, resumed_stderr)
        self.assertEqual(json.loads(resumed_stdout), summary)
        self.assertEqual(journal_before, (output / "journal.jsonl").read_bytes())
        self.assert_private_text_absent(resumed_stdout + resumed_stderr)

    def test_generate_provider_mode_uses_orchestration_and_resumes_without_new_work(self) -> None:
        from model_cards.orchestration import (
            run_provider_assisted_pipeline as actual_assisted_pipeline,
        )
        from tests.test_orchestration import RISK_CATALOG, ResumableFakeCall

        frozen = self.bundle()
        output = self.root / "assisted-run"
        fake = ResumableFakeCall()

        def assisted(*args, **kwargs):
            with mock.patch(
                "model_cards.orchestration._build_risk_interfaces",
                return_value=(None, None, "nexus_dependency_unavailable"),
            ):
                return actual_assisted_pipeline(
                    *args,
                    **kwargs,
                    environment={"OPENROUTER_API_KEY": "fixture-only"},
                    call=fake,
                    risk_catalog=RISK_CATALOG,
                )

        arguments = [
            "generate",
            "acme/Instruct",
            "--revision",
            COMMIT,
            "--output",
            str(output),
            "--offline-bundle",
            str(frozen),
            "--provider",
            "Together",
        ]
        with mock.patch(
            "model_cards.cli.run_provider_assisted_pipeline",
            side_effect=assisted,
        ):
            result, stdout, stderr = self.invoke(arguments)
        self.assertEqual(result, 0, stderr)
        summary = json.loads(stdout)
        self.assertIn("provider-orchestration.json", summary["artifacts"])
        self.assertIn("provider-result.json", summary["artifacts"])
        self.assertIn("usage-summary.json", summary["artifacts"])
        admission = json.loads((output / "provider-orchestration.json").read_text())
        self.assertEqual("Together", admission["provider"])
        self.assertEqual(
            "deepseek/deepseek-v4-flash-0731", admission["model"]
        )
        first_paid = list(fake.paid_paths)
        self.assertTrue(first_paid)
        self.assert_private_text_absent(stdout + stderr)

        with mock.patch(
            "model_cards.cli.run_provider_assisted_pipeline",
            side_effect=assisted,
        ), mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("assisted resume attempted Hub access"),
        ):
            resumed, resumed_stdout, resumed_stderr = self.invoke(arguments[:-4] + arguments[-2:])
        self.assertEqual(resumed, 0, resumed_stderr)
        self.assertEqual(json.loads(resumed_stdout), summary)
        self.assertEqual(first_paid, fake.paid_paths)
        self.assert_private_text_absent(resumed_stdout + resumed_stderr)

    def test_provider_missing_key_retains_safe_admission_and_locks_mode(self) -> None:
        frozen = self.bundle()
        output = self.root / "missing-key-run"
        arguments = [
            "generate",
            "acme/Instruct",
            "--revision",
            COMMIT,
            "--output",
            str(output),
            "--offline-bundle",
            str(frozen),
            "--provider",
            "Together",
        ]
        with mock.patch(
            "model_cards.orchestration._build_risk_interfaces",
            return_value=(None, None, "nexus_dependency_unavailable"),
        ), mock.patch(
            "model_cards.provider.UrllibProviderTransport.open",
            side_effect=AssertionError("missing key reached transport"),
        ):
            result, stdout, stderr = self.invoke(
                arguments,
                environment={"OPENROUTER_API_KEY": ""},
            )
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("openrouter_key_unavailable", stderr)
        self.assertTrue((output / "provider-orchestration.json").is_file())
        self.assertEqual(b"", (output / "usage.jsonl").read_bytes())
        self.assertFalse((output / "run-manifest.json").exists())
        self.assert_private_text_absent(stdout + stderr)

        without_provider = arguments[:-2]
        locked, locked_stdout, locked_stderr = self.invoke(without_provider)
        self.assertEqual(locked, 2)
        self.assertEqual(locked_stdout, "")
        self.assertIn("provider_mode_conflict", locked_stderr)

    def test_retry_exhaustion_and_its_terminal_replay_have_one_cli_code(self) -> None:
        frozen = self.bundle()
        output = self.root / "retry-exhausted-run"
        arguments = [
            "generate",
            "acme/Instruct",
            "--revision",
            COMMIT,
            "--output",
            str(output),
            "--offline-bundle",
            str(frozen),
            "--provider",
            "Together",
        ]
        failures = (
            RetryExhaustedError(),
            ProviderTerminalAttemptError(
                "recorded terminal retry exhaustion",
                reason_code="retry_exhausted",
            ),
        )
        rendered: list[str] = []
        for failure in failures:
            with mock.patch(
                "model_cards.cli.run_provider_assisted_pipeline",
                side_effect=failure,
            ):
                result, stdout, stderr = self.invoke(arguments)
            self.assertEqual(2, result)
            self.assertEqual("", stdout)
            self.assertIn("provider_retries_exhausted", stderr)
            self.assert_private_text_absent(stderr)
            rendered.append(stderr)
        self.assertEqual(rendered[0], rendered[1])

    def test_invalid_provider_and_cross_mode_reuse_fail_before_network_or_calls(self) -> None:
        output = self.root / "invalid-provider"
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("invalid provider reached source collection"),
        ), self.assertRaises(SystemExit):
            self.invoke(
                [
                    "generate",
                    "acme/Instruct",
                    "--output",
                    str(output),
                    "--provider",
                    "bad\nprovider",
                ]
            )
        self.assertFalse(output.exists())

        frozen = self.bundle()
        offline_output = self.root / "offline-mode"
        offline_args = [
            "generate",
            "acme/Instruct",
            "--revision",
            COMMIT,
            "--output",
            str(offline_output),
            "--offline-bundle",
            str(frozen),
        ]
        completed, _, completed_stderr = self.invoke(offline_args)
        self.assertEqual(completed, 0, completed_stderr)
        with mock.patch(
            "model_cards.cli.run_provider_assisted_pipeline",
            side_effect=AssertionError("cross-mode run reached provider orchestration"),
        ):
            conflict, conflict_stdout, conflict_stderr = self.invoke(
                offline_args + ["--provider", "Together"]
            )
        self.assertEqual(conflict, 2)
        self.assertEqual(conflict_stdout, "")
        self.assertIn("provider_mode_conflict", conflict_stderr)

    def test_offline_bundle_target_mismatch_never_admits_or_contacts_network(self) -> None:
        frozen = self.bundle("acme/First")
        output = self.root / "mismatch-run"
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("offline mode contacted network"),
        ):
            result, stdout, stderr = self.invoke(
                [
                    "generate",
                    "acme/Second",
                    "--revision",
                    COMMIT,
                    "--output",
                    str(output),
                    "--offline-bundle",
                    str(frozen),
                ]
            )
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("target_mismatch", stderr)
        self.assertFalse(output.exists())
        self.assert_private_text_absent(stdout + stderr)

    def test_sparse_frozen_bundle_emits_an_honest_unreviewed_candidate(self) -> None:
        frozen = self.bundle("acme/Sparse", sparse=True)
        output = self.root / "sparse-run"
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("offline mode contacted network"),
        ):
            result, stdout, stderr = self.invoke(
                [
                    "generate",
                    "acme/Sparse",
                    "--revision",
                    COMMIT,
                    "--output",
                    str(output),
                    "--offline-bundle",
                    str(frozen),
                ]
            )
        self.assertEqual(result, 0, stderr)
        self.assertEqual(json.loads(stdout)["status"], "generated_unreviewed")
        pipeline = PipelineResult.from_dict(
            json.loads((output / "pipeline-result.json").read_text())
        )
        self.assertFalse(pipeline.claims)
        self.assertEqual(pipeline.composition_status.value, "unavailable")
        self.assert_private_text_absent(stdout + stderr)

    def test_batch_continues_after_one_failure_and_admits_each_target_once(self) -> None:
        first_request = f"acme/First@{COMMIT}"
        failed_request = f"acme/Unavailable@{COMMIT}"
        second_request = f"acme/Second@{SECOND_COMMIT}"
        first = self.bundle("acme/First", COMMIT)
        second = self.bundle("acme/Second", SECOND_COMMIT)
        targets = json.dumps([first_request, failed_request, second_request])
        output = self.root / "batch"
        arguments = [
            "batch",
            targets,
            "--output",
            str(output),
            "--offline-bundle",
            f"{first_request}={first}",
            "--offline-bundle",
            f"{second_request}={second}",
        ]
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=RuntimeError(
                "hf_super_secret_token /Users/private source body secret"
            ),
        ):
            result, stdout, stderr = self.invoke(
                arguments,
                environment={"HF_TOKEN": "hf_super_secret_token"},
            )
        self.assertEqual(result, 1)
        aggregate = json.loads(stdout)
        self.assertEqual(aggregate["status"], "completed_with_failures")
        self.assertEqual([item["request"] for item in aggregate["targets"]], json.loads(targets))
        statuses = {item["request"]: item["status"] for item in aggregate["targets"]}
        self.assertEqual(statuses[failed_request], "failed")
        self.assertEqual(statuses[first_request], "generated_unreviewed")
        self.assertEqual(statuses[second_request], "generated_unreviewed")
        self.assertEqual(
            len(list((output / "targets").glob("*/run-manifest.json"))),
            2,
        )
        self.assertEqual(
            json.loads((output / "batch-result.json").read_text()),
            aggregate,
        )
        self.assert_private_text_absent(stdout + stderr)

        journals = {
            path.parent.name: path.read_bytes()
            for path in (output / "targets").glob("*/journal.jsonl")
        }
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=RuntimeError("source body secret /private/retry"),
        ):
            resumed, resumed_stdout, resumed_stderr = self.invoke(arguments)
        self.assertEqual(resumed, 1)
        self.assertEqual(json.loads(resumed_stdout), aggregate)
        self.assertEqual(
            journals,
            {
                path.parent.name: path.read_bytes()
                for path in (output / "targets").glob("*/journal.jsonl")
            },
        )
        self.assert_private_text_absent(resumed_stdout + resumed_stderr)

    def test_report_command_builds_a_paired_body_free_batch_report(self) -> None:
        request = f"acme/Report@{COMMIT}"
        frozen = self.bundle("acme/Report", COMMIT)
        batches = []
        for label in ("primary", "replay"):
            batch = self.root / f"report-{label}"
            result, stdout, stderr = self.invoke(
                [
                    "batch",
                    json.dumps([request]),
                    "--output",
                    str(batch),
                    "--offline-bundle",
                    f"{request}={frozen}",
                ]
            )
            self.assertEqual(result, 0, stderr)
            self.assertEqual("completed", json.loads(stdout)["status"])
            batches.append(batch)

        report_path = self.root / "paired-quality-report.json"
        result, stdout, stderr = self.invoke(
            [
                "report",
                str(batches[0]),
                "--replay-batch",
                str(batches[1]),
                "--output",
                str(report_path),
            ]
        )
        self.assertEqual(result, 0, stderr)
        summary = json.loads(stdout)
        self.assertEqual("completed", summary["status"])
        self.assertEqual(1, summary["target_count"])
        report = load_quality_report(report_path)
        self.assertEqual(summary["report_sha256"], report.report_sha256)
        self.assertTrue(report.replay_stability["all_targets_stable"])
        self.assert_private_text_absent(stdout + stderr)

    def test_collect_uses_only_environment_token_and_sanitizes_failures(self) -> None:
        destination = self.root / "collected"
        adapter = _FixtureHubAdapter("acme/Collect", COMMIT)
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter", return_value=adapter
        ) as adapter_factory:
            result, stdout, stderr = self.invoke(
                [
                    "collect",
                    "acme/Collect",
                    "--revision",
                    COMMIT,
                    "--output",
                    str(destination),
                ],
                environment={"HF_TOKEN": "hf_super_secret_token"},
            )
        self.assertEqual(result, 0, stderr)
        adapter_factory.assert_called_once_with(token="hf_super_secret_token")
        self.assertEqual(json.loads(stdout)["status"], "collected")
        self.assert_private_text_absent(stdout + stderr)
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("collect resume contacted network"),
        ):
            resumed, resumed_stdout, resumed_stderr = self.invoke(
                [
                    "collect",
                    "acme/Collect",
                    "--revision",
                    COMMIT,
                    "--output",
                    str(destination),
                ]
            )
        self.assertEqual(resumed, 0, resumed_stderr)
        self.assertEqual(json.loads(resumed_stdout), json.loads(stdout))

        failed_output = self.root / "failed"
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=RuntimeError(
                "hf_super_secret_token /Users/private source body secret"
            ),
        ):
            failed, failed_stdout, failed_stderr = self.invoke(
                [
                    "generate",
                    "acme/Failure",
                    "--output",
                    str(failed_output),
                ],
                environment={"HF_TOKEN": "hf_super_secret_token"},
            )
        self.assertEqual(failed, 2)
        self.assertEqual(failed_stdout, "")
        self.assertIn("source_collection_failed", failed_stderr)
        self.assert_private_text_absent(failed_stdout + failed_stderr)

    def test_repair_command_validates_automated_record_without_review_claims(self) -> None:
        target = TargetIdentity("acme/Repair", COMMIT)
        context = FieldRepairContext(
            field_path="identity.summary",
            base_field_path="identity.summary",
            target=target,
            predecessor_candidate_id="claim-" + "1" * 24,
            predecessor_candidate_sha256="1" * 64,
            composition_result_sha256="2" * 64,
            omission_audit_sha256="3" * 64,
            factreasoner_record_sha256="4" * 64,
            candidate_inventory_sha256="5" * 64,
            gate_inventory_sha256="6" * 64,
            allowed_evidence_sha256s=(),
            findings=(RepairFinding.SOURCE_PRESENT_OMISSION,),
        )
        record = FieldRepairRecord(
            context=context,
            attempts=(),
            outcome=RepairOutcome.WITHHELD,
            reason=RepairReason.NO_ACCEPTED_RELEVANT_EVIDENCE,
            selected_candidate_id=None,
            selected_candidate_sha256=None,
        )
        path = self.root / "repair.json"
        path.write_text(json.dumps(record.to_dict()), encoding="utf-8")
        result, stdout, stderr = self.invoke(["repair", str(path)])
        self.assertEqual(result, 0, stderr)
        summary = json.loads(stdout)
        self.assertEqual(summary["status"], "withheld")
        self.assertEqual(summary["attempt_count"], 0)
        self.assertNotIn("reviewed", stdout.casefold())
        self.assertNotIn("approved", stdout.casefold())
        self.assert_private_text_absent(stdout + stderr)


if __name__ == "__main__":
    unittest.main()
