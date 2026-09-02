from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
from io import StringIO
import json
from pathlib import Path
import shutil
import tempfile
from unittest import mock
import unittest

from model_cards.claim_gate import ClaimCandidate, evaluate_claim_gate
from model_cards.cli import main
from model_cards.models import (
    Evidence,
    EvidenceKind,
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from model_cards.official_discovery import discover_official_sources
from model_cards.official_sources import (
    OfficialFetchStatus,
    OfficialRemoteObject,
    collect_official_sources,
)
from model_cards.quality_report import (
    QualityReportError,
    _assert_body_free,
    _explicit_findings,
    build_quality_report,
    load_quality_report,
    serialize_quality_report,
    write_quality_report,
)
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)


REVISION = "a" * 40
OTHER_REVISION = "b" * 40
REQUEST = f"acme/Quality@{REVISION}"
FAILED_REQUEST = f"acme/Unavailable@{OTHER_REVISION}"
BODY_SENTINEL = "SYNTHETIC-EVIDENCE-BODY-DO-NOT-SERIALIZE"
OFFICIAL_BODY_SENTINEL = "SYNTHETIC-OFFICIAL-BODY-DO-NOT-SERIALIZE"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8") + b"\n"


class _HubAdapter:
    def __init__(self, *, precision: str) -> None:
        self.precision = precision

    def resolve_revision(self, model_id, requested_revision):
        if model_id != "acme/Quality" or requested_revision != REVISION:
            raise AssertionError("unexpected synthetic target")
        return REVISION

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(
            FetchStatus.OK,
            _canonical(
                {
                    "id": model_id,
                    "sha": revision,
                    "pipeline_tag": "text-generation",
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                        {"rfilename": "TRAINING.md"},
                    ],
                }
            ).rstrip(b"\n"),
        )

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(
                FetchStatus.OK,
                (
                    "# Exact target\n\n"
                    "This synthetic source describes the exact target.\n\n"
                    "[Official code](https://github.com/acme/quality)\n\n"
                    f"{BODY_SENTINEL}\n"
                ).encode("utf-8"),
            )
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                _canonical(
                    {
                        "model_type": "quality-fixture",
                        "torch_dtype": self.precision,
                    }
                ).rstrip(b"\n"),
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class _OfficialAdapter:
    def fetch(self, url, *, max_bytes, max_redirects):
        if url != "https://github.com/acme/quality":
            return OfficialRemoteObject(
                OfficialFetchStatus.UNAVAILABLE,
                reason_code="synthetic_unavailable",
            )
        return OfficialRemoteObject(
            OfficialFetchStatus.OK,
            content=OFFICIAL_BODY_SENTINEL.encode("utf-8"),
            final_url=url,
            redirect_chain=(url,),
            media_type="text/plain",
        )


class QualityReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.bundle = cls.root / "bundle"
        cls.changed_bundle = cls.root / "changed-bundle"
        collect_hf_source_bundle(
            "acme/Quality",
            cls.bundle,
            _HubAdapter(precision="float16"),
            revision=REVISION,
        )
        collect_hf_source_bundle(
            "acme/Quality",
            cls.changed_bundle,
            _HubAdapter(precision="bfloat16"),
            revision=REVISION,
        )
        cls.official_bundle = cls.root / "official-bundle"
        discovery = discover_official_sources(replay_source_bundle(cls.bundle))
        collect_official_sources(
            discovery,
            cls.official_bundle,
            _OfficialAdapter(),
        )
        cls.primary = cls.root / "batch-primary"
        cls.replay = cls.root / "batch-replay"
        cls.changed = cls.root / "batch-changed"
        cls.official = cls.root / "batch-official"
        cls._make_batch(cls.primary, cls.bundle)
        cls._make_batch(cls.replay, cls.bundle)
        cls._make_batch(cls.changed, cls.changed_bundle)
        cls._make_batch(cls.official, cls.bundle, cls.official_bundle)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def _make_batch(
        cls,
        output: Path,
        bundle: Path,
        official_bundle: Path | None = None,
    ) -> None:
        stdout = StringIO()
        stderr = StringIO()
        arguments = [
            "batch",
            json.dumps([REQUEST, FAILED_REQUEST]),
            "--output",
            str(output),
            "--offline-bundle",
            f"{REQUEST}={bundle}",
        ]
        if official_bundle is not None:
            arguments.extend(
                [
                    "--offline-official-bundle",
                    f"{REQUEST}={official_bundle}",
                ]
            )
        with mock.patch(
            "model_cards.cli.HuggingFaceHubAdapter",
            side_effect=RuntimeError("synthetic unavailable target"),
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            return_code = main(arguments)
        if return_code != 1:
            raise AssertionError(
                f"synthetic batch did not retain its honest failure: {stderr.getvalue()}"
            )
        result = json.loads(stdout.getvalue())
        if result["status"] != "completed_with_failures":
            raise AssertionError("synthetic batch status is not complete")

    def test_aggregate_is_closed_body_free_and_preserves_batch_order(self) -> None:
        report = build_quality_report(self.primary, self.replay)
        value = report.to_dict()
        self.assertEqual(
            [entry["request"] for entry in value["targets"]],
            [REQUEST, FAILED_REQUEST],
        )
        self.assertEqual(value["aggregate"]["requests_total"], 2)
        self.assertEqual(value["aggregate"]["succeeded"], 1)
        self.assertEqual(value["aggregate"]["failed"], 1)
        self.assertEqual(value["targets"][1]["status"], "failed")
        self.assertIsNone(value["targets"][1]["metrics"])
        self.assertEqual(
            [entry["gate"] for entry in value["targets"][0]["metrics"]["claims"]["gates"]],
            [
                "coordinate_integrity",
                "entity_scope",
                "field_fit",
                "value_support",
            ],
        )
        self.assertEqual(value["aggregate"]["provider"]["ledger_count"], 1)
        self.assertEqual(value["aggregate"]["provider"]["paid_calls"], 0)
        metrics = value["targets"][0]["metrics"]
        self.assertGreater(metrics["sources"]["unavailable"], 0)
        self.assertEqual(metrics["factreasoner"]["atoms_decided"], metrics["factreasoner"]["atoms_total"])
        self.assertEqual(metrics["factreasoner"]["decision_coverage_ppm"], 1_000_000)
        for gate in metrics["claims"]["gates"]:
            self.assertEqual(gate["reasons"]["total"], gate["checked"])
        self.assertTrue(
            {
                "catalog_available",
                "context_count",
                "taxonomy_candidate_count",
                "taxonomy_mapped_count",
                "taxonomy_included_count",
                "mapping_derivation_count",
                "applicability_total",
                "ground_count",
            }
            <= set(metrics["risk"])
        )
        self.assertTrue(
            {
                "paid_calls",
                "prompt_tokens",
                "completion_tokens",
                "retry_count",
                "committed_usd",
                "latency_ms",
            }
            <= set(metrics["provider"])
        )
        self.assertTrue(value["replay_stability"]["all_targets_stable"])
        self.assertTrue(
            {"inputs", "values", "bindings", "artifact", "decisions"}
            <= set(value["targets"][0]["surfaces"])
        )
        encoded = serialize_quality_report(report)
        self.assertNotIn(BODY_SENTINEL.encode("utf-8"), encoded)
        self.assertNotIn(str(self.root).encode("utf-8"), encoded)
        for forbidden_key in (
            b'"body"',
            b'"quote"',
            b'"hypothesis"',
            b'"prompt"',
            b'"raw_ledger_rows"',
        ):
            self.assertNotIn(forbidden_key, encoded)

    def test_combined_official_source_state_is_replayed_without_bodies(self) -> None:
        hf_only = build_quality_report(self.primary).to_dict()["targets"][0]
        combined_report = build_quality_report(self.official)
        combined = combined_report.to_dict()["targets"][0]
        self.assertGreater(
            combined["metrics"]["sources"]["total"],
            hf_only["metrics"]["sources"]["total"],
        )
        self.assertGreater(combined["metrics"]["sources"]["loaded"], 0)
        combined_run = next(self.official.glob("targets/*"))
        source_state = json.loads((combined_run / "source-state.json").read_text())
        artifact = json.loads((combined_run / "card-artifact.json").read_text())
        self.assertEqual(
            source_state["active_catalog_sha256"],
            artifact["publication"]["source_catalog_sha256"],
        )
        serialized = serialize_quality_report(combined_report)
        self.assertNotIn(OFFICIAL_BODY_SENTINEL.encode("utf-8"), serialized)

        stale = self.root / "batch-official-stale-discovery"
        shutil.copytree(self.official, stale)
        replacement = discover_official_sources(
            replay_source_bundle(self.bundle), max_candidates=31
        )
        batch_result_path = stale / "batch-result.json"
        batch_result = json.loads(batch_result_path.read_text())
        successful = batch_result["targets"][0]
        run_prefix = next(
            Path(item).parent
            for item in successful["artifacts"]
            if item.endswith("/pipeline-result.json")
        )
        discovery_relative = (run_prefix / "official-discovery.json").as_posix()
        (stale / discovery_relative).write_bytes(_canonical(replacement.to_dict()))
        successful["artifacts"] = sorted(
            [*successful["artifacts"], discovery_relative]
        )
        batch_result_path.write_bytes(_canonical(batch_result))
        with self.assertRaises(QualityReportError):
            build_quality_report(stale)

    def test_privacy_boundary_rejects_arbitrary_absolute_paths(self) -> None:
        for unsafe in (
            "/opt/private/run.json",
            "provider (/srv/private/ledger.json)",
            r"C:\Users\alice\private.json",
        ):
            with self.subTest(unsafe=unsafe), self.assertRaises(QualityReportError):
                _assert_body_free({"provider_name": unsafe})

    def test_paired_report_separates_value_and_cost_latency_stability(self) -> None:
        report = build_quality_report(self.primary, self.changed).to_dict()
        comparison = report["replay_stability"]["targets"][0]
        self.assertFalse(comparison["inputs"])
        self.assertFalse(comparison["values"])
        self.assertFalse(comparison["bindings"])
        self.assertFalse(comparison["artifact"])
        self.assertTrue(comparison["cost_latency"])
        self.assertEqual(comparison["comparison_status"], "changed")
        self.assertFalse(report["replay_stability"]["all_targets_stable"])

    def test_canonical_round_trip_tamper_checks_and_atomic_no_overwrite(self) -> None:
        report = build_quality_report(self.primary, self.replay)
        destination = self.root / "quality-report.json"
        self.assertEqual(write_quality_report(report, destination), destination)
        self.assertEqual(write_quality_report(report, destination), destination)
        self.assertEqual(load_quality_report(destination).to_dict(), report.to_dict())

        with self.assertRaises(FileExistsError):
            write_quality_report(build_quality_report(self.primary), destination)

        tampered = self.root / "quality-report-tampered.json"
        value = deepcopy(report.to_dict())
        value["report_sha256"] = "0" * 64
        tampered.write_bytes(_canonical(value))
        with self.assertRaises(QualityReportError):
            load_quality_report(tampered)

        internally_inconsistent = self.root / "quality-report-inconsistent.json"
        value = deepcopy(report.to_dict())
        value["aggregate"]["failed"] = 0
        payload = {key: entry for key, entry in value.items() if key != "report_sha256"}
        value["report_sha256"] = hashlib.sha256(_canonical(payload)[:-1]).hexdigest()
        internally_inconsistent.write_bytes(_canonical(value))
        with self.assertRaises(QualityReportError):
            load_quality_report(internally_inconsistent)

        duplicate = self.root / "quality-report-duplicate.json"
        duplicate.write_bytes(b'{"report_sha256":"x","report_sha256":"y"}\n')
        with self.assertRaises(QualityReportError):
            load_quality_report(duplicate)

        noncanonical = self.root / "quality-report-noncanonical.json"
        noncanonical.write_text(json.dumps(report.to_dict(), indent=2) + "\n")
        with self.assertRaises(QualityReportError):
            load_quality_report(noncanonical)

    def test_batch_artifact_tamper_and_result_order_drift_fail_closed(self) -> None:
        tampered = self.root / "tampered-batch"
        shutil.copytree(self.primary, tampered)
        public_card = next(tampered.glob("targets/*/public-card.json"))
        value = json.loads(public_card.read_text())
        value["identity"]["model_id"] = "acme/Tampered"
        public_card.write_bytes(_canonical(value))
        with self.assertRaises(QualityReportError):
            build_quality_report(tampered)

        reordered = self.root / "reordered-batch"
        shutil.copytree(self.primary, reordered)
        batch_result = json.loads((reordered / "batch-result.json").read_text())
        batch_result["targets"].reverse()
        (reordered / "batch-result.json").write_bytes(_canonical(batch_result))
        with self.assertRaises(QualityReportError):
            build_quality_report(reordered)

        ledger_tampered = self.root / "ledger-tampered-batch"
        shutil.copytree(self.primary, ledger_tampered)
        usage_ledger = next(ledger_tampered.glob("targets/*/usage.jsonl"))
        usage_ledger.write_bytes(b'{"event":"fabricated"}\n')
        with self.assertRaises(QualityReportError):
            build_quality_report(ledger_tampered)

        symlinked = self.root / "symlinked-batch"
        shutil.copytree(self.primary, symlinked)
        linked_card = next(symlinked.glob("targets/*/public-card.json"))
        original_card = next(self.primary.glob("targets/*/public-card.json"))
        linked_card.unlink()
        linked_card.symlink_to(original_card)
        with self.assertRaises(QualityReportError):
            build_quality_report(symlinked)

    def test_adversarial_findings_are_explicit_codes_without_evidence_text(self) -> None:
        target = TargetIdentity("acme/Quality", REVISION)
        structured_source = SourceDocument(
            source_id="source-config",
            source_uri=(
                "https://huggingface.co/acme/Quality/blob/"
                f"{REVISION}/config.json"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=target,
            data={"model_type": "quality-fixture"},
        )
        structured_evidence = Evidence(
            kind=EvidenceKind.STRUCTURED,
            source_id=structured_source.source_id,
            source_uri=structured_source.source_uri,
            source_role=structured_source.role,
            source_revision=structured_source.source_revision,
            source_sha256=structured_source.sha256,
            source_target=target,
            synthetic=False,
            verified=True,
            pointer="/model_type",
            fragment="quality-fixture",
        )
        score = {
            "benchmark": "SyntheticEval",
            "metric": "accuracy",
            "score": 0.99,
            "setting": "zero-shot",
            "split": "test",
        }
        structured_candidate = ClaimCandidate(
            target=target,
            field_path="evaluation.benchmark_scores[0]",
            value=score,
            benchmark_scope={
                "benchmark": score["benchmark"],
                "metric": score["metric"],
                "setting": score["setting"],
            },
            claim_entity=f"{target.model_id}@{target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=(structured_evidence,),
        )

        quote_text = "An architecture statement for an unrelated model."
        quote_source = SourceDocument(
            source_id="source-readme",
            source_uri=(
                "https://huggingface.co/acme/Quality/blob/"
                f"{REVISION}/README.md"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=target,
            text=quote_text,
        )
        quote_evidence = Evidence(
            kind=EvidenceKind.QUOTE,
            source_id=quote_source.source_id,
            source_uri=quote_source.source_uri,
            source_role=quote_source.role,
            source_revision=quote_source.source_revision,
            source_sha256=quote_source.sha256,
            source_target=TargetIdentity(target.model_id, OTHER_REVISION),
            synthetic=False,
            verified=True,
            quote=quote_text,
            char_start=0,
            char_end=len(quote_text),
        )
        quote_candidate = ClaimCandidate(
            target=target,
            field_path="model_details.architecture_type",
            value=quote_text,
            claim_entity=f"acme/Other@{OTHER_REVISION}",
            relation=RelationToTarget.SIBLING_CHECKPOINT,
            evidence=(quote_evidence,),
        )
        wrong_entity_evidence = Evidence(
            kind=EvidenceKind.QUOTE,
            source_id=quote_source.source_id,
            source_uri=quote_source.source_uri,
            source_role=quote_source.role,
            source_revision=quote_source.source_revision,
            source_sha256=quote_source.sha256,
            source_target=target,
            synthetic=False,
            verified=True,
            quote=quote_text,
            char_start=0,
            char_end=len(quote_text),
        )
        wrong_entity_candidate = ClaimCandidate(
            target=target,
            field_path="model_details.architecture_type",
            value=quote_text,
            claim_entity=f"acme/Other@{REVISION}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=(wrong_entity_evidence,),
        )
        records = (
            evaluate_claim_gate(structured_candidate, (structured_source,)),
            evaluate_claim_gate(quote_candidate, (quote_source,)),
            evaluate_claim_gate(wrong_entity_candidate, (quote_source,)),
        )
        findings = _explicit_findings(records)
        self.assertEqual(
            {entry["code"] for entry in findings},
            {
                "coordinate_failure",
                "structured_failure",
                "wrong_entity",
                "wrong_checkpoint",
                "wrong_relation",
                "wrong_field",
                "invalid_score_row",
            },
        )
        encoded = _canonical(findings)
        self.assertNotIn(quote_text.encode("utf-8"), encoded)


if __name__ == "__main__":
    unittest.main()
