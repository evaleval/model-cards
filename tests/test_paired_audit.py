from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from evaluation.paired_audit import (
    AUTO_BENCHMARKCARDS_SCHEMA_VERSION,
    AUTO_BENCHMARKCARDS_SUMMARY_SHA256,
    AUTO_BENCHMARKCARDS_VERIFIER_SHA256,
    AuditError,
    _abc_verifier,
    build_audit,
    main,
)
from model_cards.quality_report import (
    QualityReport,
    _LoadedBatch,
    _LoadedTarget,
    _aggregate,
    _digest,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TARGET_REQUEST = "example/model@" + "b" * 40
FAILED_TARGET_REQUEST = "example/failed@" + "c" * 40


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def distribution(**counts: int) -> dict:
    return {
        "entries": [
            {"key": key, "count": counts[key]}
            for key in sorted(counts)
            if counts[key] > 0
        ],
        "total": sum(counts.values()),
    }


def quality_report(
    *,
    input_digest: str = "a" * 64,
    included: int = 2,
    wrong_field: int = 1,
    source_present: int = 1,
    publication_conflicts: int = 0,
    include_failed: bool = False,
) -> dict:
    total = 3
    request = TARGET_REQUEST
    metrics = {
            "schema_export": {
                "schema_valid": True,
                "public_projection_safe": True,
                "contract_version": "1",
                "lifecycle_status": "generated_unreviewed",
                "artifact_binding_count": included,
                "artifact_derivation_count": 1,
            },
            "fields": {
                "total": 4,
                "present": 2,
                "omitted": 2,
                "abstention_ppm": 500000,
                "source_present_omissions": source_present,
                "omission_reasons": distribution(not_found=1, conflicting=1),
            },
            "sources": {
                "total": 1,
                "loaded": 1,
                "unavailable": 0,
                "statuses": distribution(loaded=1),
                "reasons": distribution(loaded=1),
            },
            "claims": {
                "total": total,
                "eligible": included,
                "included": included,
                "withheld": total - included,
                "gates": [
                    {
                        "gate": "coordinate_integrity",
                        "checked": total,
                        "accepted": total,
                        "withheld": 0,
                        "reasons": distribution(coordinates_replayed=total),
                    },
                    {
                        "gate": "entity_scope",
                        "checked": total,
                        "accepted": total,
                        "withheld": 0,
                        "reasons": distribution(entity_scope_exact=total),
                    },
                    {
                        "gate": "field_fit",
                        "checked": total,
                        "accepted": total - wrong_field,
                        "withheld": wrong_field,
                        "reasons": distribution(
                            semantic_field_fit=total - wrong_field,
                            wrong_field=wrong_field,
                        ),
                    },
                    {
                        "gate": "value_support",
                        "checked": total,
                        "accepted": included,
                        "withheld": total - included,
                        "reasons": distribution(
                            semantic_value_support=included,
                            incomplete_value_support=total - included,
                        ),
                    },
                ],
            },
            "findings": {
                "total": wrong_field,
                "codes": distribution(wrong_field=wrong_field),
                "records": [
                    {
                        "candidate_id": f"claim-{index:024x}",
                        "field_path": "identity.summary",
                        "code": "wrong_field",
                        "reason": "wrong_field",
                    }
                    for index in range(wrong_field)
                ],
            },
            "factreasoner": {
                "fields_total": 4,
                "fields_checked": 3,
                "fields_absent": 1,
                "atoms_total": 3,
                "atoms_decided": 3,
                "decision_coverage_ppm": 1000000,
                "source_limited_atoms": 1,
                "unavailable_atoms": 1,
                "corpus_truncated": False,
                "coverage_statuses": distribution(checked=3, absence=1),
                "atom_outcomes": distribution(support=1, neutral=1, unavailable=1),
                "atom_actions": distribution(keep=2, collect_or_withhold=1),
                "field_actions": distribution(keep=2, collect_or_withhold=1),
                "decision_reasons": distribution(supported=1, neutral=1, unavailable=1),
                "source_statuses": distribution(loaded=1),
                "source_reasons": distribution(loaded=1),
            },
            "omissions": {
                "source_present_count": source_present,
                "conflict_field_count": 1,
                "conflict_record_count": 2,
                "composition_conflict_count": 1,
                "publication_conflict_count": publication_conflicts,
                "publication_conflict_field_count": publication_conflicts,
                "publication_conflict_reasons": distribution(
                    metadata_base_model_declarations_disagree=publication_conflicts
                ),
                "reasons": distribution(not_found=1, conflicting=1),
            },
            "risk": {
                "catalog_available": True,
                "catalog_sha256": "f" * 64,
                "status": "completed",
                "reason": "mapped",
                "context_count": 2,
                "grounded_context_count": 1,
                "publisher_context_count": 1,
                "publisher_risk_count": 0,
                "taxonomy_candidate_count": 2,
                "taxonomy_mapped_count": 2,
                "taxonomy_included_count": 1,
                "taxonomy_withheld_count": 1,
                "taxonomy_factreasoner_withheld_count": 1,
                "applicability_total": 2,
                "applicability_accepted": 1,
                "applicability_withheld": 1,
                "mapping_derivation_count": 2,
                "exported_derivation_count": 1,
                "ground_count": 2,
                "input_claim_count": 2,
                "supporting_source_count": 1,
            },
            "privacy": {
                "status": "completed",
                "reason": "passed",
                "checked": 1,
                "passed": 1,
                "withheld": 0,
                "public_card_hash_verified": True,
                "artifact_hash_verified": True,
            },
            "provider": {
                "ledger_count": 1,
                "paid_calls": 0,
                "attempt_count": 0,
                "receipt_count": 0,
                "token_receipt_count": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "retry_count": 0,
                "latency_ms": 0,
                "max_latency_ms": 0,
                "committed_usd": "0",
                "global_halt": False,
                "providers": [],
                "attempt_statuses": distribution(),
                "terminal_outcomes": distribution(),
            },
        }
    surfaces = {
        "inputs": input_digest,
        "values": "4" * 64,
        "bindings": "5" * 64,
        "artifact": "6" * 64,
        "decisions": "7" * 64,
        "validation": "8" * 64,
        "risk": "9" * 64,
        "omission": "c" * 64,
        "privacy": "d" * 64,
        "cost_latency": "e" * 64,
    }
    targets = [
        {
            "request": request,
            "status": "generated_unreviewed",
            "failure_reason": None,
            "target": {"model_id": "example/model", "revision": "b" * 40},
            "run_sha256": "3" * 64,
            "metrics": metrics,
            "surfaces": surfaces,
            "provider": metrics["provider"],
        }
    ]
    if include_failed:
        targets.append(
            {
                "request": FAILED_TARGET_REQUEST,
                "status": "failed",
                "failure_reason": "source_unavailable",
                "target": None,
                "run_sha256": None,
                "metrics": None,
                "surfaces": None,
                "provider": None,
            }
        )
    batch_status = "completed_with_failures" if include_failed else "completed"
    batch_components = []
    for target in targets:
        if target["status"] == "failed":
            batch_components.append(
                {
                    "request": target["request"],
                    "status": "failed",
                    "reason": target["failure_reason"],
                    "cost_latency_sha256": None,
                }
            )
        else:
            batch_components.append(
                {
                    "request": target["request"],
                    "status": target["status"],
                    "run_sha256": target["run_sha256"],
                    "cost_latency_sha256": surfaces["cost_latency"],
                }
            )
    requests = tuple(target["request"] for target in targets)
    primary_digest = _digest(
        {
            "batch_request": {"targets": list(requests)},
            "batch_status": batch_status,
            "targets": batch_components,
            "aggregate_budget": None,
        }
    )
    loaded = _LoadedBatch(
        status=batch_status,
        requests=requests,
        targets=tuple(
            _LoadedTarget(
                record=target,
                provider=None if target["metrics"] is None else metrics["provider"],
                aggregate_budget_path_sha256=None,
            )
            for target in targets
        ),
        aggregate_budget=None,
        batch_sha256=primary_digest,
    )
    replay_targets = []
    for target in targets:
        failed = target["status"] == "failed"
        replay_targets.append(
            {
                "request": target["request"],
                "comparison_status": "stable_failure" if failed else "stable",
                "primary_status": target["status"],
                "replay_status": target["status"],
                "primary_failure_reason": target["failure_reason"],
                "replay_failure_reason": target["failure_reason"],
                **{
                    key: None if failed else True
                    for key in surfaces
                },
                "all_stable": True,
            }
        )
    report = QualityReport(
        primary_batch_sha256=primary_digest,
        replay_batch_sha256="2" * 64,
        primary_batch_status=batch_status,
        replay_batch_status=batch_status,
        targets=targets,
        aggregate=_aggregate(loaded),
        replay_stability={
            "status": "compared",
            "request_order_stable": True,
            "all_targets_stable": True,
            "aggregate_cost_latency_stable": True,
            "targets": replay_targets,
        },
    )
    return report.to_dict()


def abc_summary() -> dict:
    def paper_metric(
        value: float,
        ci95: tuple[float, float],
        num: int,
        den: int,
    ) -> dict:
        flagged_num = min(num, den // 2)
        return {
            "value": value,
            "ci95": list(ci95),
            "ci_method": "stratified-cluster-bootstrap-percentile",
            "counts": {
                "num": float(num),
                "den": float(den),
                "by_stratum": {
                    "flagged": {"num": float(flagged_num), "den": den / 2},
                    "unflagged": {
                        "num": float(num - flagged_num),
                        "den": den / 2,
                    },
                },
            },
        }

    return {
        "schema_version": AUTO_BENCHMARKCARDS_SCHEMA_VERSION,
        "frozen_corpus": {},
        "human_validation": {},
        "sample": {},
        "source_bounded_judge": {
            "field_rows": 3450.0,
            "filled_rows": 2035.0,
            "not_specified_rows": 1415.0,
            "supported_including_eee": 0.8608375363016555,
            "partial": 0.12432775746741817,
            "unsupported": 0.014834706230926285,
            "common_denominator_five_state": {
                "filled_fully_supported": paper_metric(
                    0.5189412066126995,
                    (0.4748678152236265, 0.5610093497001332),
                    1746,
                    3450,
                ),
                "filled_partially_supported": paper_metric(
                    0.07494886520954902,
                    (0.064441892612462, 0.08563095431806408),
                    259,
                    3450,
                ),
                "filled_unsupported": paper_metric(
                    0.008942849291046896,
                    (0.005221766611770648, 0.013490839232384534),
                    30,
                    3450,
                ),
                "not_specified_information_available": paper_metric(
                    0.0729494117353641,
                    (0.055584359232074936, 0.09249614396962402),
                    244,
                    3450,
                ),
                "not_specified_no_information": paper_metric(
                    0.32421766715134054,
                    (0.28178441745069405, 0.36920754763787206),
                    1171,
                    3450,
                ),
            },
        },
        "candidate_risk_source_judge": {
            "sample_counts": {
                "total": 761,
                "relevant_and_grounded": 547,
                "not_relevant_or_not_grounded": 214,
            },
            "s_weighted_grounded_rate": {
                "value": 0.748351513135232,
                "ci95": [0.6938486579427771, 0.7994730375808277],
                "counts": {"num": 547.0, "den": 761.0},
            },
            "human_validated": False,
            "headline_result": False,
        },
        "validation_flags": {
            "weighted_precision": 0.0303030303030303,
            "weighted_recall": 0.018591000304935164,
            "n_flagged_fields_raw": 33,
            "n_unsupported_fields_raw": 30,
            "n_overlap_raw": 1,
        },
        "public_source_screen": {
            "n_findings": 154,
            "raw_label_counts": {
                "confirmed-material": 111,
                "confirmed-trivial": 20,
                "not-a-defect": 23,
                "unsure": 0,
            },
            "inference_guard": [
                "defect prevalence",
                "screen recall",
                "screen accuracy",
                "standard false-positive rate",
                "human reliability",
            ],
        },
    }


def engineering_read() -> dict:
    report = {
        "report_version": "baseline-full-engineering-read/v1",
        "status": "automated_engineering_read_not_human_validated",
        "independent_model_evaluation": False,
        "better_than_auto_benchmarkcards_claimed": False,
        "method": "Synthetic source-parity fixture.",
        "limitations": ["Not human truth."],
        "targets": [{"source_parity": {"identical": True}}],
        "aggregate": {
            "targets": 1,
            "source_parity_passed": True,
            "pre_gate_accept_to_reference_withhold": 1,
            "change_counts": {"wrong_relation": 1},
        },
    }
    report["report_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    return report


def paired_target_map(*, include_failed: bool = False) -> dict:
    targets = [
        {
            "target_blind_id": "target-model",
            "target_request": TARGET_REQUEST,
        }
    ]
    if include_failed:
        targets.append(
            {
                "target_blind_id": "target-failed",
                "target_request": FAILED_TARGET_REQUEST,
            }
        )
    return {
        "mapping_version": "model-card-paired-audit-target-map/v1",
        "targets": targets,
    }


def completed_labels(
    *,
    conditions: tuple[str, ...] = ("A", "B"),
    target_blind_ids: tuple[str, ...] = ("target-model",),
) -> dict:
    base = {
        "support": "fully_supported",
        "source_binding": "correct",
        "entity_checkpoint": "correct",
        "relation": "correct",
        "field_fit": "correct",
        "score_row": "not_applicable",
        "omission": "not_omitted",
        "conflict_visibility": "no_conflict",
        "risk_grounding": "not_applicable",
        "risk_applicability": "not_applicable",
    }
    items = []
    for condition in conditions:
        for target_blind_id in target_blind_ids:
            for index, (warned, error) in enumerate(
                ((True, "yes"), (True, "no"), (False, "yes"), (False, "no")),
                1,
            ):
                items.append(
                    {
                        **base,
                        "item_id": f"label-item-{index}",
                        "target_blind_id": target_blind_id,
                        "condition": condition,
                        "warning_present": warned,
                        "actionable_error": error,
                    }
                )
    return {
        "labels_version": "model-card-paired-audit-labels/v1",
        "study_status": "annotation_complete",
        "blinded": True,
        "items": items,
        "annotator_confirmation": {
            "completed": True,
            "used_only_displayed_evidence": True,
            "uncertainty_notes": "Synthetic unit-test labels only.",
        },
    }


class PairedAuditTests(unittest.TestCase):
    def test_public_label_template_is_empty_and_schema_valid(self) -> None:
        schema = json.loads(
            (REPOSITORY_ROOT / "evaluation" / "paired-audit-labels.schema.json").read_text(
                encoding="utf-8"
            )
        )
        template = json.loads(
            (REPOSITORY_ROOT / "evaluation" / "paired-audit-labels-template.json").read_text(
                encoding="utf-8"
            )
        )
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(template)
        self.assertEqual(template["study_status"], "design_only_no_human_results")
        self.assertEqual(template["items"], [])
        self.assertFalse(template["annotator_confirmation"]["completed"])

        target_map_schema = json.loads(
            (
                REPOSITORY_ROOT
                / "evaluation"
                / "paired-audit-target-map.schema.json"
            ).read_text(encoding="utf-8")
        )
        Draft202012Validator.check_schema(target_map_schema)
        Draft202012Validator(target_map_schema).validate(paired_target_map())

        completed = completed_labels()
        Draft202012Validator(schema).validate(completed)
        self.assertNotIn("target_request", canonical(completed).decode("utf-8"))
        self.assertNotIn("example/model", canonical(completed).decode("utf-8"))

    def test_single_condition_reports_mechanical_metrics_and_scope_guards(self) -> None:
        result = build_audit(
            [("current", quality_report(publication_conflicts=1))],
            auto_benchmarkcards_summary=abc_summary(),
            engineering_read=engineering_read(),
        )
        metrics = result["model_cards_conditions"]["current"]
        self.assertEqual(result["status"], "automated_audit_no_new_human_labels")
        self.assertFalse(result["claims_of_superiority"])
        self.assertFalse(result["system_output_human_reviewed"])
        self.assertEqual(result["pairing"]["status"], "paired_replay_identical_frozen_inputs")
        self.assertEqual(metrics["assignment_findings"]["counts"]["wrong_field"], 1)
        self.assertEqual(metrics["factreasoner"]["informative_coverage"]["numerator"], 2)
        self.assertEqual(metrics["factreasoner"]["informative_coverage"]["denominator"], 3)
        self.assertEqual(metrics["omissions"]["source_present"], 1)
        self.assertEqual(metrics["conflict_visibility"]["conflict_fields"], 2)
        self.assertEqual(metrics["conflict_visibility"]["conflict_records"], 3)
        self.assertEqual(metrics["conflict_visibility"]["publication_conflicts"], 1)
        self.assertEqual(
            metrics["conflict_visibility"]["publication_conflict_reasons"],
            {"metadata_base_model_declarations_disagree": 1},
        )
        self.assertEqual(
            result["auto_benchmarkcards_reference"]["warnings"]["reference_labels"],
            "automated_source_judge",
        )
        engineering = result["identical_source_engineering_read"]
        self.assertNotIn("method", engineering)
        self.assertNotIn("limitations", engineering)
        self.assertIn("not copied", engineering["privacy_guard"])
        self.assertIsNone(result["paired_deltas"])
        digest = result.pop("report_sha256")
        self.assertEqual(hashlib.sha256(canonical(result)).hexdigest(), digest)

    def test_two_conditions_require_identical_input_surfaces_and_emit_neutral_deltas(self) -> None:
        first = quality_report(included=1, wrong_field=1)
        second = quality_report(included=2, wrong_field=0)
        result = build_audit([("A", first), ("B", second)])
        self.assertEqual(result["pairing"]["status"], "paired_identical_frozen_inputs")
        self.assertEqual(result["paired_deltas"]["direction"], "B_minus_A")
        self.assertEqual(
            result["paired_deltas"]["count_deltas"]["support.claims_included"], 1
        )
        self.assertIn("do not imply improvement", result["paired_deltas"]["interpretation"])

        mismatched = quality_report(input_digest="f" * 64)
        with self.assertRaisesRegex(AuditError, "identical frozen input"):
            build_audit([("A", first), ("B", mismatched)])

    def test_canonical_quality_report_validation_rejects_forged_aggregate(self) -> None:
        forged = quality_report()
        forged["aggregate"]["claims"]["included"] = 1
        forged["aggregate"]["claims"]["withheld"] = 2
        forged["aggregate"]["claims"]["gates"][3] = {
            "gate": "value_support",
            "checked": 3,
            "accepted": 1,
            "withheld": 2,
            "reasons": distribution(
                semantic_value_support=1,
                incomplete_value_support=2,
            ),
        }
        forged.pop("report_sha256")
        forged["report_sha256"] = hashlib.sha256(canonical(forged)).hexdigest()
        with self.assertRaisesRegex(AuditError, "not a canonical quality report"):
            build_audit([("forged", forged)])

    def test_failed_targets_are_accepted_without_claiming_paired_input_identity(self) -> None:
        first = quality_report(include_failed=True)
        second = quality_report(include_failed=True)

        single = build_audit([("current", first)])
        self.assertEqual(
            single["pairing"]["status"],
            "paired_replay_with_unavailable_input_surfaces",
        )
        self.assertEqual(single["pairing"]["input_surface_matches"], 1)
        self.assertEqual(single["pairing"]["input_surfaces_unavailable"], 1)

        paired = build_audit([("A", first), ("B", second)])
        self.assertEqual(
            paired["pairing"]["status"],
            "paired_conditions_with_unavailable_input_surfaces",
        )
        self.assertEqual(paired["pairing"]["input_surface_matches"], 1)
        self.assertEqual(paired["pairing"]["input_surfaces_unavailable"], 1)
        self.assertIsNone(paired["paired_deltas"])

    def test_auto_benchmarkcards_summary_is_schema_and_release_checked(self) -> None:
        current = quality_report()
        malformed = abc_summary()
        malformed["schema_version"] += 1
        with self.assertRaisesRegex(AuditError, "schema version"):
            build_audit(
                [("current", current)],
                auto_benchmarkcards_summary=malformed,
            )

        drifted = abc_summary()
        drifted["source_bounded_judge"]["field_rows"] += 1
        with self.assertRaisesRegex(AuditError, "field row counts"):
            build_audit(
                [("current", current)],
                auto_benchmarkcards_summary=drifted,
            )

    def test_auto_benchmarkcards_cli_rejects_unpinned_release_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            condition = root / "quality.json"
            summary = root / "results_summary.json"
            verifier = root / "verifier_ratings.csv"
            output = root / "audit.json"
            condition.write_bytes(canonical(quality_report()) + b"\n")
            summary.write_bytes(canonical(abc_summary()) + b"\n")
            verifier.write_text(
                "row_id,card,card_reference,finding_index,category,field,issue,"
                "screen_claimed_ground_truth,verifier_label,evidence_url,notes\n",
                encoding="utf-8",
            )

            self.assertEqual(
                main(
                    [
                        "--condition",
                        f"current={condition}",
                        "--auto-benchmarkcards-summary",
                        str(summary),
                        "--output",
                        str(output),
                    ]
                ),
                2,
            )
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(AuditError, "frozen release"):
                _abc_verifier(verifier)

        self.assertEqual(len(AUTO_BENCHMARKCARDS_SUMMARY_SHA256), 64)
        self.assertEqual(len(AUTO_BENCHMARKCARDS_VERIFIER_SHA256), 64)

    def test_warning_precision_and_recall_require_complete_blinded_labels(self) -> None:
        first = quality_report()
        second = quality_report()
        result = build_audit(
            [("A", first), ("B", second)],
            labels=completed_labels(),
            target_map=paired_target_map(),
        )
        human = result["human_labels"]
        self.assertTrue(human["human_results_present"])
        self.assertEqual(human["targets"], 1)
        self.assertEqual(human["conditions"]["A"]["source_binding"], {"correct": 4})
        warning = human["conditions"]["B"]["warning"]
        self.assertEqual(warning["true_positive"], 1)
        self.assertEqual(warning["false_positive"], 1)
        self.assertEqual(warning["false_negative"], 1)
        self.assertEqual(warning["true_negative"], 1)
        self.assertTrue(human["warning_precision_recall_available"])
        self.assertTrue(warning["precision_available"])
        self.assertTrue(warning["recall_available"])
        self.assertEqual(warning["precision"]["value"], 0.5)
        self.assertEqual(warning["recall"]["value"], 0.5)

        with self.assertRaisesRegex(AuditError, "require a private target map"):
            build_audit([("A", first), ("B", second)], labels=completed_labels())

        wrong_target_map = deepcopy(paired_target_map())
        wrong_target_map["targets"][0]["target_request"] = "example/not-in-condition"
        with self.assertRaisesRegex(AuditError, "exactly cover report targets"):
            build_audit(
                [("A", first), ("B", second)],
                labels=completed_labels(),
                target_map=wrong_target_map,
            )

        one_sided = completed_labels(conditions=("B",))
        with self.assertRaisesRegex(AuditError, "every target in condition A"):
            build_audit(
                [("A", first), ("B", second)],
                labels=one_sided,
                target_map=paired_target_map(),
            )

        mismatched_items = completed_labels()
        del mismatched_items["items"][-1]
        with self.assertRaisesRegex(AuditError, "matching item universe"):
            build_audit(
                [("A", first), ("B", second)],
                labels=mismatched_items,
                target_map=paired_target_map(),
            )

        failed_target = quality_report(include_failed=True)
        with self.assertRaisesRegex(AuditError, "every target in condition A"):
            build_audit(
                [("A", failed_target), ("B", failed_target)],
                labels=completed_labels(),
                target_map=paired_target_map(include_failed=True),
            )

        incomplete = deepcopy(completed_labels())
        incomplete["study_status"] = "annotation_in_progress"
        with self.assertRaisesRegex(AuditError, "violate their JSON Schema"):
            build_audit(
                [("A", first), ("B", second)],
                labels=incomplete,
                target_map=paired_target_map(),
            )

        missing_source_binding = deepcopy(completed_labels())
        del missing_source_binding["items"][0]["source_binding"]
        with self.assertRaisesRegex(AuditError, "violate their JSON Schema"):
            build_audit(
                [("A", first), ("B", second)],
                labels=missing_source_binding,
                target_map=paired_target_map(),
            )

        missing_confirmation_field = deepcopy(completed_labels())
        del missing_confirmation_field["annotator_confirmation"][
            "uncertainty_notes"
        ]
        with self.assertRaisesRegex(AuditError, "violate their JSON Schema"):
            build_audit(
                [("A", first), ("B", second)],
                labels=missing_confirmation_field,
                target_map=paired_target_map(),
            )

    def test_cli_writes_new_canonical_report_and_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "quality.json"
            output = root / "audit.json"
            source.write_bytes(canonical(quality_report()) + b"\n")
            args = [
                "--condition",
                f"current={source}",
                "--output",
                str(output),
            ]
            self.assertEqual(main(args), 0)
            value = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(value["report_version"], "model-card-paired-failure-audit/v1")
            self.assertEqual(main(args), 2)

    def test_cli_hashes_private_target_map_without_exporting_target_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "condition-a.json"
            second = root / "condition-b.json"
            labels_path = root / "labels.json"
            target_map_path = root / "private-target-map.json"
            output = root / "audit.json"
            first.write_bytes(canonical(quality_report()) + b"\n")
            second.write_bytes(canonical(quality_report()) + b"\n")
            labels_path.write_bytes(canonical(completed_labels()) + b"\n")
            target_map_path.write_bytes(canonical(paired_target_map()) + b"\n")

            self.assertEqual(
                main(
                    [
                        "--condition",
                        f"A={first}",
                        "--condition",
                        f"B={second}",
                        "--labels",
                        str(labels_path),
                        "--target-map",
                        str(target_map_path),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            value = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("paired_audit_target_map", value["input_receipts"])
            self.assertEqual(value["human_labels"]["targets"], 1)
            self.assertNotIn(TARGET_REQUEST, output.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
