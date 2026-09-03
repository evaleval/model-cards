from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path, PurePosixPath
import shutil
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
from model_cards.models import RelationToTarget, TargetIdentity
from model_cards.official_sources import (
    OfficialFetchStatus,
    OfficialRemoteObject,
    OfficialSourceStatus,
    RelationState,
    replay_official_sources,
)
from model_cards.pipeline import PipelineResult
from model_cards.provider import (
    MissingCredentialError,
    ProviderTerminalAttemptError,
    RetryExhaustedError,
)
from model_cards.quality_report import (
    QualityReportError,
    build_quality_report,
    load_quality_report,
    serialize_quality_report,
)
from model_cards.publication_schema import validate_publication_card
from model_cards.scholarly_discovery import ScholarlyResponse, ScholarlyService
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
    OFFICIAL_URL = f"https://github.com/acme/collect/tree/{COMMIT}"

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    "# Exact target\n\n"
                    f"This frozen source describes {self.model_id} at {self.revision}.\n\n"
                    f"[Code repository for {self.model_id}]({self.OFFICIAL_URL})\n"
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


class _FixtureScholarlyAdapter:
    def __init__(self) -> None:
        self.services = []

    def open(self, request):
        self.services.append(request.service)
        if request.service is ScholarlyService.OPENALEX:
            return ScholarlyResponse(
                200,
                _json_bytes({"results": [{"doi": "10.1234/acme.collect"}]}),
            )
        return ScholarlyResponse(
            200,
            _json_bytes(
                {"data": [{"externalIds": {"ArXiv": "2401.01234"}}]}
            ),
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

    def test_audit_review_rejects_partial_closure_artifacts(self) -> None:
        result, _stdout, stderr = self.invoke(
            [
                "audit-review",
                "artifact.json",
                "--source-bundle",
                "bundle",
                "--claim-gates",
                "claim-gates.json",
                "--output",
                "audit.json",
            ]
        )

        self.assertEqual(2, result)
        self.assertIn("requires all downstream closure artifacts", stderr)

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

    def test_generate_threads_shared_aggregate_budget_only_in_provider_mode(self) -> None:
        frozen = self.bundle()
        output = self.root / "aggregate-budget-run"
        aggregate = self.root / "cohort-paid-call-budget.jsonl"
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
            "--aggregate-budget-journal",
            str(aggregate),
        ]
        with mock.patch(
            "model_cards.cli.run_provider_assisted_pipeline",
            side_effect=MissingCredentialError("fixture"),
        ) as assisted:
            result, stdout, stderr = self.invoke(arguments)
        self.assertEqual(2, result)
        self.assertEqual("", stdout)
        self.assertIn("openrouter_key_unavailable", stderr)
        self.assertEqual(
            aggregate,
            assisted.call_args.kwargs["aggregate_budget_path"],
        )

        rejected_output = self.root / "aggregate-without-provider"
        rejected, rejected_stdout, rejected_stderr = self.invoke(
            [
                "generate",
                "acme/Instruct",
                "--output",
                str(rejected_output),
                "--aggregate-budget-journal",
                str(aggregate),
            ]
        )
        self.assertEqual(2, rejected)
        self.assertEqual("", rejected_stdout)
        self.assertIn("aggregate_budget_requires_provider", rejected_stderr)
        self.assertFalse(rejected_output.exists())

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
        scholarly = _FixtureScholarlyAdapter()
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter", return_value=hub
        ), mock.patch(
            "model_cards.cli.StdlibOfficialSourceAdapter",
            return_value=_FixtureOfficialAdapter(),
        ) as official_factory, mock.patch(
            "model_cards.cli.StdlibScholarlyDiscoveryTransport",
            return_value=scholarly,
        ) as scholarly_factory:
            result, stdout, stderr = self.invoke(arguments)
        self.assertEqual(result, 0, stderr)
        summary = json.loads(stdout)
        self.assertIn("official-discovery.json", summary["artifacts"])
        self.assertIn("scholarly-discovery.json", summary["artifacts"])
        self.assertIn("official-source-bundle/manifest.json", summary["artifacts"])
        self.assertIn("source-state.json", summary["artifacts"])
        self.assertEqual(
            "hf_and_official",
            json.loads((output / "source-state.json").read_text())["mode"],
        )
        official_factory.assert_called_once()
        scholarly_factory.assert_called_once_with()
        self.assertEqual(
            [ScholarlyService.OPENALEX, ScholarlyService.SEMANTIC_SCHOLAR],
            scholarly.services,
        )
        allowed_hosts = set(official_factory.call_args.args[0])
        self.assertIn("github.com", allowed_hosts)
        self.assertIn("arxiv.org", allowed_hosts)
        official = replay_official_sources(output / "official-source-bundle")
        collected = [
            item
            for item in official.manifest.sources
            if item.requested_url == _LinkedFixtureHubAdapter.OFFICIAL_URL
        ]
        self.assertEqual(1, len(collected))
        self.assertEqual(OfficialSourceStatus.COLLECTED, collected[0].status)
        self.assertTrue(collected[0].evidence_eligible)
        relations = [
            item
            for item in official.manifest.relations
            if item.source_id == collected[0].source_id
        ]
        self.assertEqual(1, len(relations))
        self.assertEqual(RelationState.DECLARED, relations[0].state)
        self.assertEqual(
            RelationToTarget.EXACT_TARGET,
            relations[0].relation_to_target,
        )
        self.assertEqual("acme/Collect", relations[0].subject_model_id)
        scholarly_hints = [
            item
            for item in official.manifest.sources
            if item.status is OfficialSourceStatus.DISCOVERY_ONLY
        ]
        self.assertEqual(2, len(scholarly_hints))
        self.assertTrue(all(not item.evidence_eligible for item in scholarly_hints))
        self.assert_private_text_absent(stdout + stderr)

        journal_before = (output / "journal.jsonl").read_bytes()
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=AssertionError("resume attempted Hub access"),
        ), mock.patch(
            "model_cards.cli.StdlibOfficialSourceAdapter",
            side_effect=AssertionError("resume attempted official-source access"),
        ), mock.patch(
            "model_cards.cli.StdlibScholarlyDiscoveryTransport",
            side_effect=AssertionError("resume attempted scholarly discovery"),
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

    def test_provider_batch_threads_one_shared_aggregate_budget(self) -> None:
        requests = [f"acme/First@{COMMIT}", f"acme/Second@{SECOND_COMMIT}"]
        output = self.root / "provider-batch"

        def generated(**kwargs):
            return {
                "target": {
                    "model_id": kwargs["model_id"],
                    "revision": kwargs["revision"],
                },
                "status": "generated_unreviewed",
                "artifacts": ["public-card.json"],
            }

        with mock.patch(
            "model_cards.cli._generate_target", side_effect=generated
        ) as generate:
            result, stdout, stderr = self.invoke(
                [
                    "batch",
                    json.dumps(requests),
                    "--output",
                    str(output),
                    "--provider",
                    "Together",
                ]
            )
        self.assertEqual(0, result, stderr)
        self.assertEqual("completed", json.loads(stdout)["status"])
        self.assertEqual(2, generate.call_count)
        for call in generate.call_args_list:
            self.assertEqual("Together", call.kwargs["provider"])
            self.assertEqual(
                output / "aggregate-budget.jsonl",
                call.kwargs["aggregate_budget_path"],
            )

        rejected_output = self.root / "batch-budget-without-provider"
        rejected, rejected_stdout, rejected_stderr = self.invoke(
            [
                "batch",
                json.dumps(requests),
                "--output",
                str(rejected_output),
                "--aggregate-budget-journal",
                str(self.root / "shared.jsonl"),
            ]
        )
        self.assertEqual(2, rejected)
        self.assertEqual("", rejected_stdout)
        self.assertIn("aggregate_budget_requires_provider", rejected_stderr)
        self.assertFalse(rejected_output.exists())

    def test_provider_batch_rejects_budget_journal_aliases_before_writes(self) -> None:
        request = f"acme/Exact@{COMMIT}"
        aliases = (
            "batch-request.json",
            "batch-result.json",
            "aggregate-budget-summary.json",
            "targets/target-arbitrary/usage.jsonl",
        )
        for index, relative in enumerate(aliases):
            with self.subTest(relative=relative):
                output = self.root / f"budget-alias-{index}"
                journal = output.joinpath(*PurePosixPath(relative).parts)
                with mock.patch("model_cards.cli._generate_target") as generate:
                    result, stdout, stderr = self.invoke(
                        [
                            "batch",
                            json.dumps([request]),
                            "--output",
                            str(output),
                            "--provider",
                            "Together",
                            "--aggregate-budget-journal",
                            str(journal),
                        ]
                    )
                self.assertEqual(2, result)
                self.assertEqual("", stdout)
                self.assertIn("aggregate_budget_path_conflict", stderr)
                self.assertFalse(output.exists())
                generate.assert_not_called()

    def test_successful_provider_batch_is_immediately_reportable(self) -> None:
        from model_cards.factreasoner import IBMFactReasonerAdapter
        from model_cards.orchestration import (
            run_provider_assisted_pipeline as actual_assisted_pipeline,
        )
        from tests.test_orchestration import RISK_CATALOG, ResumableFakeCall

        request = f"acme/ProviderReport@{COMMIT}"
        frozen = self.bundle("acme/ProviderReport", COMMIT)
        output = self.root / "provider-report-batch"
        fake = ResumableFakeCall()

        def assisted(*args, **kwargs):
            with (
                mock.patch(
                    "model_cards.orchestration._build_risk_interfaces",
                    return_value=(None, None, "nexus_dependency_unavailable"),
                ),
                mock.patch.object(
                    IBMFactReasonerAdapter,
                    "installation_status",
                    return_value="ibm_factreasoner_dependency_unavailable",
                ),
            ):
                return actual_assisted_pipeline(
                    *args,
                    **kwargs,
                    environment={"OPENROUTER_API_KEY": "fixture-only"},
                    call=fake,
                    risk_catalog=RISK_CATALOG,
                )

        with mock.patch(
            "model_cards.cli.run_provider_assisted_pipeline",
            side_effect=assisted,
        ):
            result, stdout, stderr = self.invoke(
                [
                    "batch",
                    json.dumps([request]),
                    "--output",
                    str(output),
                    "--provider",
                    "Together",
                    "--offline-bundle",
                    f"{request}={frozen}",
                ]
            )

        self.assertEqual(0, result, stderr)
        batch = json.loads(stdout)
        self.assertIn("aggregate-budget.jsonl", batch["artifacts"])
        self.assertIn("aggregate-budget-summary.json", batch["artifacts"])
        self.assertTrue(
            any(
                item.endswith("/provider-orchestration.json")
                for item in batch["targets"][0]["artifacts"]
            )
        )
        self.assertTrue(
            any(
                item.endswith("/provider-result.json")
                for item in batch["targets"][0]["artifacts"]
            )
        )

        with mock.patch(
            "model_cards.quality_report.load_pinned_nexus_catalog",
            return_value=RISK_CATALOG,
        ):
            report = build_quality_report(output)
        value = report.to_dict()
        self.assertEqual(
            "batch_root",
            value["aggregate"]["aggregate_budget"]["journal_scope"],
        )
        self.assertEqual(
            "25", value["aggregate"]["aggregate_budget"]["usd_cap"]
        )
        self.assertEqual(
            value["aggregate"]["provider"]["committed_usd"],
            value["aggregate"]["aggregate_budget"]["committed_usd"],
        )
        self.assertEqual(
            "0",
            value["aggregate"]["aggregate_budget"]["reserved_usd_capacity"],
        )
        self.assertFalse(value["aggregate"]["aggregate_budget"]["global_halt"])
        self.assertEqual(1, value["targets"][0]["provider"]["ledger_count"])
        self.assertNotIn(
            "journal_path_sha256", value["aggregate"]["aggregate_budget"]
        )
        self.assertNotIn(
            str(self.root).encode("utf-8"), serialize_quality_report(report)
        )

        stale = self.root / "provider-report-stale-admission"
        shutil.copytree(output, stale)
        admission_path = next(stale.glob("targets/*/provider-orchestration.json"))
        admission = json.loads(admission_path.read_text())
        admission["eligible_source_set_sha256"] = "0" * 64
        admission_path.write_bytes(_json_bytes(admission) + b"\n")
        with mock.patch(
            "model_cards.quality_report.load_pinned_nexus_catalog",
            return_value=RISK_CATALOG,
        ), self.assertRaises(QualityReportError):
            build_quality_report(stale)

        stale_budget = self.root / "provider-report-stale-budget"
        shutil.copytree(output, stale_budget)
        budget_path = stale_budget / "aggregate-budget-summary.json"
        budget = json.loads(budget_path.read_text())
        budget["reserved_usd_capacity"] = "1"
        budget_path.write_bytes(_json_bytes(budget) + b"\n")
        with mock.patch(
            "model_cards.quality_report.load_pinned_nexus_catalog",
            return_value=RISK_CATALOG,
        ), self.assertRaises(QualityReportError):
            build_quality_report(stale_budget)

    def test_failed_provider_target_cost_is_retained_and_budget_bound(self) -> None:
        from model_cards.factreasoner import IBMFactReasonerAdapter
        from model_cards.orchestration import (
            run_provider_assisted_pipeline as actual_assisted_pipeline,
        )
        from tests.test_orchestration import RISK_CATALOG
        from tests.test_provider import (
            FixtureTransport,
            route_payload,
            success_payload,
        )

        request = f"acme/ProviderFailure@{COMMIT}"
        frozen = self.bundle("acme/ProviderFailure", COMMIT)
        output = self.root / "provider-failure-batch"
        transport = FixtureTransport(
            [
                (
                    200,
                    success_payload(
                        decision={"wrong": "shape"}, provider="Together"
                    ),
                )
            ],
            routes=[route_payload(provider="Together")],
        )

        def assisted(*args, **kwargs):
            with (
                mock.patch(
                    "model_cards.orchestration._build_risk_interfaces",
                    return_value=(None, None, "nexus_dependency_unavailable"),
                ),
                mock.patch.object(
                    IBMFactReasonerAdapter,
                    "installation_status",
                    return_value="ibm_factreasoner_dependency_unavailable",
                ),
            ):
                return actual_assisted_pipeline(
                    *args,
                    **kwargs,
                    environment={"OPENROUTER_API_KEY": "fixture-only"},
                    transport=transport,
                    risk_catalog=RISK_CATALOG,
                )

        with mock.patch(
            "model_cards.cli.run_provider_assisted_pipeline",
            side_effect=assisted,
        ):
            result, stdout, stderr = self.invoke(
                [
                    "batch",
                    json.dumps([request]),
                    "--output",
                    str(output),
                    "--provider",
                    "Together",
                    "--offline-bundle",
                    f"{request}={frozen}",
                ]
            )

        self.assertEqual(1, result, stderr)
        batch = json.loads(stdout)
        self.assertEqual("failed", batch["targets"][0]["status"])
        self.assertTrue(
            any(
                item.endswith("/provider-orchestration.json")
                for item in batch["targets"][0]["artifacts"]
            )
        )
        self.assertTrue(
            any(
                item.endswith("/usage.jsonl")
                for item in batch["targets"][0]["artifacts"]
            )
        )

        value = build_quality_report(output).to_dict()
        self.assertEqual(1, value["targets"][0]["provider"]["paid_calls"])
        self.assertEqual(1, value["aggregate"]["provider"]["paid_calls"])
        self.assertEqual(1, value["aggregate"]["aggregate_budget"]["paid_calls"])
        self.assertEqual(1, value["aggregate"]["aggregate_budget"]["ledger_count"])

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
