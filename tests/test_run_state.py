from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from model_cards.models import TargetIdentity
from model_cards.run_state import (
    JOURNAL_FILENAME,
    MANIFEST_FILENAME,
    RunEvent,
    RunManifest,
    RunStateError,
    RunStore,
    USAGE_LEDGER_FILENAME,
)


class RunStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "run"
        self.target = TargetIdentity("example-lab/exact-model", "1" * 40)
        self.manifest = RunManifest(
            target=self.target,
            source_bundle_id="hf_bundle_" + "2" * 32,
            source_manifest_sha256="3" * 64,
            configuration={
                "inference_model": "deepseek/deepseek-v4-flash-0731",
                "temperature": 0,
                "contract": "model-card/v1",
            },
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def clock(self):
        return datetime(2026, 9, 1, 1, 2, 3, 456000, tzinfo=timezone.utc)

    def test_manifest_is_closed_content_addressed_and_round_trips(self) -> None:
        encoded = self.manifest.to_dict()
        restored = RunManifest.from_dict(json.loads(json.dumps(encoded)))
        self.assertEqual(restored, self.manifest)
        self.assertTrue(self.manifest.run_id.startswith("model_card_run_"))
        with self.assertRaisesRegex(RunStateError, "digest"):
            RunManifest.from_dict({**encoded, "manifest_sha256": "0" * 64})
        with self.assertRaisesRegex(RunStateError, "closed shape"):
            RunManifest.from_dict({**encoded, "extra": True})

    def test_private_configuration_material_is_rejected(self) -> None:
        for configuration in (
            {"api_key": "secret"},
            {"prompt": "do a thing"},
            {"path": "/Users/person/private"},
            {"nested": {"provider_trace": "x"}},
        ):
            with self.subTest(configuration=configuration):
                with self.assertRaises(RunStateError):
                    RunManifest(
                        target=self.target,
                        source_bundle_id="hf_bundle_" + "2" * 32,
                        source_manifest_sha256="3" * 64,
                        configuration=configuration,
                    )

    def test_initialize_admits_one_target_and_is_idempotent(self) -> None:
        store = RunStore.initialize(self.root, self.manifest)
        self.assertEqual(store.manifest, self.manifest)
        self.assertTrue((self.root / MANIFEST_FILENAME).is_file())
        self.assertTrue((self.root / JOURNAL_FILENAME).is_file())
        self.assertTrue((self.root / USAGE_LEDGER_FILENAME).is_file())
        self.assertEqual(RunStore.initialize(self.root, self.manifest).manifest, self.manifest)

        other = RunManifest(
            target=TargetIdentity("example-lab/other", "4" * 40),
            source_bundle_id="hf_bundle_" + "5" * 32,
            source_manifest_sha256="6" * 64,
            configuration=dict(self.manifest.configuration),
        )
        with self.assertRaisesRegex(RunStateError, "another target/config"):
            RunStore.initialize(self.root, other)

    def test_append_replay_resume_and_artifact_drift(self) -> None:
        store = RunStore.initialize(self.root, self.manifest)
        artifact = self.root / "results" / "catalog.json"
        artifact.parent.mkdir()
        artifact.write_bytes(b'{"catalog":"fixture"}\n')
        expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
        event = store.record_stage(
            stage="collect",
            logical_id="exact_source_bundle",
            status="completed",
            reason="frozen_bundle_verified",
            artifact_path=artifact,
            input_sha256s=("8" * 64, "7" * 64),
            metrics={"source_count": 3, "elapsed_ms": 17},
            clock=self.clock,
        )
        self.assertEqual(event.sequence, 1)
        self.assertEqual(event.artifact_path, "results/catalog.json")
        self.assertEqual(event.artifact_sha256, expected)
        self.assertEqual(event.input_sha256s, ("7" * 64, "8" * 64))
        self.assertEqual(store.events(verify_artifacts=True), (event,))

        resumed = store.record_stage(
            stage="collect",
            logical_id="exact_source_bundle",
            status="completed",
            reason="frozen_bundle_verified",
            artifact_path=artifact,
            input_sha256s=("7" * 64, "8" * 64),
            metrics={"source_count": 3, "elapsed_ms": 17},
            clock=self.clock,
        )
        self.assertEqual(resumed, event)
        self.assertEqual(len(store.events()), 1)

        with self.assertRaisesRegex(RunStateError, "different result"):
            store.record_stage(
                stage="collect",
                logical_id="exact_source_bundle",
                status="failed",
                reason="source_drift",
                artifact_path=artifact,
                input_sha256s=("7" * 64, "8" * 64),
                metrics={"source_count": 3, "elapsed_ms": 17},
                clock=self.clock,
            )
        artifact.write_text("drift", encoding="utf-8")
        with self.assertRaisesRegex(RunStateError, "drifted"):
            store.events(verify_artifacts=True)

    def test_journal_chain_detects_torn_and_tampered_lines(self) -> None:
        store = RunStore.initialize(self.root, self.manifest)
        first = store.record_stage(
            stage="risk_map",
            logical_id="risk_mapping",
            status="unavailable",
            reason="risk_provider_unavailable",
            metrics={"candidate_count": 0},
            clock=self.clock,
        )
        store.record_stage(
            stage="complete",
            logical_id="pipeline_result",
            status="withheld",
            reason="validation_incomplete",
            input_sha256s=(first.event_sha256,),
            clock=self.clock,
        )
        self.assertEqual(len(store.events()), 2)

        journal = self.root / JOURNAL_FILENAME
        raw = journal.read_bytes()
        journal.write_bytes(raw[:-1])
        with self.assertRaisesRegex(RunStateError, "torn"):
            store.events()

        journal.write_bytes(raw)
        lines = raw.splitlines()
        value = json.loads(lines[1])
        value["previous_event_sha256"] = "0" * 64
        # Recomputing neither event ID nor digest exercises closed record integrity.
        lines[1] = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        journal.write_bytes(b"\n".join(lines) + b"\n")
        with self.assertRaises(RunStateError):
            store.events()

    def test_serialized_event_rejects_private_metrics_and_absolute_artifacts(self) -> None:
        base = dict(
            sequence=1,
            run_id=self.manifest.run_id,
            stage="extract",
            logical_id="quote_candidates",
            status="completed",
            reason="candidate_extraction_completed",
            artifact_path=None,
            artifact_sha256=None,
            input_sha256s=(),
            metrics={},
            created_at="2026-09-01T01:02:03.456Z",
            previous_event_sha256=None,
        )
        event = RunEvent(**base)
        self.assertEqual(RunEvent.from_dict(event.to_dict()), event)
        with self.assertRaises(RunStateError):
            RunEvent(**{**base, "metrics": {"source_text": "private"}})
        with self.assertRaises(RunStateError):
            RunEvent(
                **{
                    **base,
                    "artifact_path": "/tmp/card.json",
                    "artifact_sha256": "9" * 64,
                }
            )

    def test_artifact_must_be_inside_root_and_not_a_symlink(self) -> None:
        store = RunStore.initialize(self.root, self.manifest)
        outside = Path(self.temporary.name) / "outside.json"
        outside.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(RunStateError, "inside"):
            store.record_stage(
                stage="export",
                logical_id="public_card",
                status="completed",
                reason="privacy_safe_export",
                artifact_path=outside,
                clock=self.clock,
            )
        link = self.root / "link.json"
        link.symlink_to(outside)
        with self.assertRaises(RunStateError):
            store.record_stage(
                stage="export",
                logical_id="public_card",
                status="completed",
                reason="privacy_safe_export",
                artifact_path=link,
                clock=self.clock,
            )


if __name__ == "__main__":
    unittest.main()
