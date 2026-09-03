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
    source_digest: str = "a" * 64,
    treatment_digest: str = "1" * 64,
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
        "source_inputs": source_digest,
        "treatment": treatment_digest,
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
        "support": "not_applicable",
        "source_binding": "not_applicable",
        "entity_checkpoint": "not_applicable",
        "relation": "not_applicable",
        "field_fit": "not_applicable",
        "score_row": "not_applicable",
        "omission": "not_applicable",
        "conflict_visibility": "not_applicable",
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
                        "actionable_error": error,
                    }
                )
    manifest = paired_item_manifest(target_blind_ids=target_blind_ids)
    return {
        "labels_version": "model-card-paired-audit-labels/v2",
        "item_manifest_sha256": manifest["manifest_sha256"],
        "study_status": "annotation_complete",
        "blinded": True,
        "items": items,
        "annotator_confirmation": {
            "completed": True,
            "used_only_displayed_evidence": True,
            "uncertainty_notes": "Synthetic unit-test labels only.",
        },
    }


def _condition_artifact_fixture(condition: str, artifacts: list[dict]) -> dict:
    pipeline_result_sha256 = "3" * 64
    source_input_surface_sha256 = "a" * 64
    treatment_surface_sha256 = "1" * 64
    identity = {
        "pipeline_result_sha256": pipeline_result_sha256,
        "source_input_surface_sha256": source_input_surface_sha256,
        "treatment_surface_sha256": treatment_surface_sha256,
        "artifacts": artifacts,
    }
    return {
        "condition": condition,
        **{key: value for key, value in identity.items() if key != "artifacts"},
        "run_identity_sha256": hashlib.sha256(canonical(identity)).hexdigest(),
        "reviewer_payload_sha256s": {
            "primary": ("1" if condition == "A" else "2") * 64,
            "warning_followup": ("3" if condition == "A" else "4") * 64,
        },
        "artifacts": artifacts,
    }


def paired_item_manifest(
    *,
    target_blind_ids: tuple[str, ...] = ("target-model",),
    include_failed: bool = False,
) -> dict:
    requests = {"target-model": TARGET_REQUEST}
    if include_failed:
        requests["target-failed"] = FAILED_TARGET_REQUEST
    artifact_names = (
        "claim-gates.json",
        "factreasoner-content.json",
        "factreasoner-original.json",
        "factreasoner-publication-original.json",
        "factreasoner.json",
        "family-risk-authorizations.json",
        "omissions.json",
        "pipeline-result.json",
        "publication-validation.json",
        "repairs.json",
        "risk-mapping.json",
    )
    targets = []
    items = []
    inventory = []
    for target_index, blind_id in enumerate(target_blind_ids):
        request = requests[blind_id]
        artifacts = [
            {"artifact_name": name, "artifact_sha256": f"{index + 1:x}" * 64}
            for index, name in enumerate(artifact_names)
        ]
        targets.append(
            {
                "target_blind_id": blind_id,
                "target_request": request,
                "target_sha256": hashlib.sha256(
                    canonical(
                        {
                            "model_id": request.rsplit("@", 1)[0],
                            "revision": request.rsplit("@", 1)[1],
                        }
                    )
                ).hexdigest(),
                "target_sheet_sha256": "8" * 64,
                "frozen_inputs": {
                    "source_bundle_id_sha256": "b" * 64,
                    "source_manifest_sha256": "c" * 64,
                    "source_catalog_sha256": "d" * 64,
                },
                "condition_artifacts": [
                    _condition_artifact_fixture(condition, artifacts)
                    for condition in ("A", "B")
                ],
            }
        )
        for index in range(1, 5):
            items.append(
                {
                    "item_id": f"label-item-{index}",
                    "target_blind_id": blind_id,
                    "item_kind": "warning",
                    "semantic_key_sha256": f"{index}" * 64,
                    "subject": {
                        "field_path": None,
                        "native_ids": [f"warning-{target_index}-{index}"],
                        "native_sha256s": [f"{index + 4:x}" * 64],
                    },
                    "conditions": [
                        {
                            "condition": condition,
                            "present": True,
                            "disposition": {
                                "state": "accepted",
                                "reason": "synthetic_test",
                                "warning_present": index <= 2,
                                "gate_decisions": [],
                                "factreasoner": {"phases": []},
                                "repair": {
                                    "status": "not_applicable",
                                    "predecessor_candidate_sha256": None,
                                    "selected_candidate_sha256": None,
                                    "record_sha256": None,
                                },
                            },
                            "artifact_bindings": [],
                            "evidence_bindings": [],
                        }
                        for condition in ("A", "B")
                    ],
                }
            )
        for condition in ("A", "B"):
            inventory.append(
                {
                    "target_blind_id": blind_id,
                    "condition": condition,
                    "claims": 0,
                    "fields": 0,
                    "risks": 0,
                    "warnings": 4,
                    "repairs": 0,
                }
            )
    manifest = {
        "manifest_version": "model-card-evaluation-item-manifest/v1",
        "study_unit_id": "study-unit-synthetic",
        "conditions": ["A", "B"],
        "blinding_key_sha256": "9" * 64,
        "targets": targets,
        "items": items,
        "inventory": inventory,
    }
    manifest["manifest_sha256"] = hashlib.sha256(canonical(manifest)).hexdigest()
    return manifest


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
        self.assertNotIn("warning_present", canonical(completed).decode("utf-8"))

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
        self.assertEqual(
            result["pairing"]["status"],
            "paired_replay_identical_frozen_sources",
        )
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

    def test_two_conditions_require_identical_source_surfaces_and_allow_different_treatments(
        self,
    ) -> None:
        first = quality_report(included=1, wrong_field=1)
        second = quality_report(
            included=2,
            wrong_field=0,
            treatment_digest="2" * 64,
        )
        result = build_audit([("A", first), ("B", second)])
        self.assertEqual(
            result["pairing"]["status"],
            "paired_identical_frozen_sources",
        )
        self.assertEqual(result["pairing"]["source_surface_matches"], 1)
        self.assertEqual(result["pairing"]["treatment_surface_matches"], 0)
        self.assertEqual(result["pairing"]["treatment_surface_differences"], 1)
        self.assertEqual(result["paired_deltas"]["direction"], "B_minus_A")
        self.assertEqual(
            result["paired_deltas"]["count_deltas"]["support.claims_included"], 1
        )
        self.assertIn("do not imply improvement", result["paired_deltas"]["interpretation"])

        mismatched = quality_report(source_digest="f" * 64)
        with self.assertRaisesRegex(AuditError, "identical frozen source"):
            build_audit([("A", first), ("B", mismatched)])

    def test_legacy_quality_report_version_and_input_surface_fail_closed(self) -> None:
        legacy_version = quality_report()
        legacy_version["report_version"] = "model-card-quality-report/v5"
        legacy_version.pop("report_sha256")
        legacy_version["report_sha256"] = hashlib.sha256(
            canonical(legacy_version)
        ).hexdigest()
        with self.assertRaisesRegex(AuditError, "not a canonical quality report"):
            build_audit([("legacy", legacy_version)])

        legacy_surface = quality_report()
        target = legacy_surface["targets"][0]
        target["surfaces"]["inputs"] = target["surfaces"].pop("source_inputs")
        legacy_surface.pop("report_sha256")
        legacy_surface["report_sha256"] = hashlib.sha256(
            canonical(legacy_surface)
        ).hexdigest()
        with self.assertRaisesRegex(AuditError, "not a canonical quality report"):
            build_audit([("legacy", legacy_surface)])

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
            "paired_replay_with_unavailable_source_surfaces",
        )
        self.assertEqual(single["pairing"]["source_surface_matches"], 1)
        self.assertEqual(single["pairing"]["source_surfaces_unavailable"], 1)
        self.assertEqual(single["pairing"]["treatment_surface_matches"], 1)
        self.assertEqual(single["pairing"]["treatment_surfaces_unavailable"], 1)

        paired = build_audit([("A", first), ("B", second)])
        self.assertEqual(
            paired["pairing"]["status"],
            "paired_conditions_with_unavailable_source_surfaces",
        )
        self.assertEqual(paired["pairing"]["source_surface_matches"], 1)
        self.assertEqual(paired["pairing"]["source_surfaces_unavailable"], 1)
        self.assertEqual(paired["pairing"]["treatment_surface_matches"], 1)
        self.assertEqual(paired["pairing"]["treatment_surfaces_unavailable"], 1)
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
            item_manifest=paired_item_manifest(),
        )
        human = result["human_labels"]
        self.assertTrue(human["human_results_present"])
        self.assertTrue(human["artifact_bound_item_universe"])
        self.assertEqual(
            human["item_manifest_sha256"],
            paired_item_manifest()["manifest_sha256"],
        )
        self.assertEqual(human["targets"], 1)
        self.assertEqual(human["conditions"]["A"]["source_binding"], {})
        self.assertEqual(
            human["conditions"]["A"]["eligible_items"],
            {
                "claims": 0,
                "score_rows": 0,
                "fields": 0,
                "risks": 0,
                "warnings": 4,
            },
        )
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

        mixed_manifest = paired_item_manifest()
        field_item = deepcopy(mixed_manifest["items"][0])
        field_item["item_id"] = "label-field-item"
        field_item["item_kind"] = "field"
        field_item["semantic_key_sha256"] = "a" * 64
        field_item["subject"] = {
            "field_path": "identity.name",
            "native_ids": ["field-identity-name"],
            "native_sha256s": ["b" * 64],
        }
        for condition in field_item["conditions"]:
            condition["disposition"]["warning_present"] = True
        mixed_manifest["items"].append(field_item)
        for inventory in mixed_manifest["inventory"]:
            inventory["fields"] += 1
        mixed_manifest.pop("manifest_sha256")
        mixed_manifest["manifest_sha256"] = hashlib.sha256(
            canonical(mixed_manifest)
        ).hexdigest()

        mixed_labels = completed_labels()
        for condition in ("A", "B"):
            field_label = deepcopy(
                next(
                    item
                    for item in mixed_labels["items"]
                    if item["condition"] == condition
                )
            )
            field_label["item_id"] = "label-field-item"
            field_label["omission"] = "not_omitted"
            field_label["conflict_visibility"] = "no_conflict"
            field_label["actionable_error"] = "not_applicable"
            mixed_labels["items"].append(field_label)
        mixed_labels["item_manifest_sha256"] = mixed_manifest["manifest_sha256"]
        mixed = build_audit(
            [("A", first), ("B", second)],
            labels=mixed_labels,
            target_map=paired_target_map(),
            item_manifest=mixed_manifest,
        )
        mixed_warning = mixed["human_labels"]["conditions"]["A"]["warning"]
        self.assertEqual(mixed_warning["labelled_universe"], 4)
        self.assertEqual(mixed_warning["true_positive"], 1)
        self.assertEqual(
            mixed["human_labels"]["conditions"]["A"]["omission"],
            {"not_omitted": 1},
        )

        reviewer_supplied_warning = completed_labels()
        reviewer_supplied_warning["items"][0]["warning_present"] = False
        with self.assertRaisesRegex(AuditError, "violate their JSON Schema"):
            build_audit(
                [("A", first), ("B", second)],
                labels=reviewer_supplied_warning,
                target_map=paired_target_map(),
                item_manifest=paired_item_manifest(),
            )

        with self.assertRaisesRegex(AuditError, "require a private target map"):
            build_audit([("A", first), ("B", second)], labels=completed_labels())

        with self.assertRaisesRegex(AuditError, "require a private item manifest"):
            build_audit(
                [("A", first), ("B", second)],
                labels=completed_labels(),
                target_map=paired_target_map(),
            )

        wrong_target_map = deepcopy(paired_target_map())
        wrong_target_map["targets"][0]["target_request"] = "example/not-in-condition"
        with self.assertRaisesRegex(AuditError, "exactly cover report targets"):
            build_audit(
                [("A", first), ("B", second)],
                labels=completed_labels(),
                target_map=wrong_target_map,
                item_manifest=paired_item_manifest(),
            )

        stale_manifest_label = completed_labels()
        stale_manifest_label["item_manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(AuditError, "not bound"):
            build_audit(
                [("A", first), ("B", second)],
                labels=stale_manifest_label,
                target_map=paired_target_map(),
                item_manifest=paired_item_manifest(),
            )

        wrong_run_manifest = paired_item_manifest()
        wrong_condition = wrong_run_manifest["targets"][0]["condition_artifacts"][0]
        wrong_condition["pipeline_result_sha256"] = "0" * 64
        wrong_condition["run_identity_sha256"] = hashlib.sha256(
            canonical(
                {
                    "pipeline_result_sha256": wrong_condition[
                        "pipeline_result_sha256"
                    ],
                    "source_input_surface_sha256": wrong_condition[
                        "source_input_surface_sha256"
                    ],
                    "treatment_surface_sha256": wrong_condition[
                        "treatment_surface_sha256"
                    ],
                    "artifacts": wrong_condition["artifacts"],
                }
            )
        ).hexdigest()
        wrong_run_manifest.pop("manifest_sha256")
        wrong_run_manifest["manifest_sha256"] = hashlib.sha256(
            canonical(wrong_run_manifest)
        ).hexdigest()
        wrong_run_labels = completed_labels()
        wrong_run_labels["item_manifest_sha256"] = wrong_run_manifest[
            "manifest_sha256"
        ]
        with self.assertRaisesRegex(AuditError, "quality-report run"):
            build_audit(
                [("A", first), ("B", second)],
                labels=wrong_run_labels,
                target_map=paired_target_map(),
                item_manifest=wrong_run_manifest,
            )

        invalid_kind_labels = completed_labels()
        invalid_kind_labels["items"][0]["support"] = "fully_supported"
        with self.assertRaisesRegex(AuditError, "inapplicable support"):
            build_audit(
                [("A", first), ("B", second)],
                labels=invalid_kind_labels,
                target_map=paired_target_map(),
                item_manifest=paired_item_manifest(),
            )

        one_sided = completed_labels(conditions=("B",))
        with self.assertRaisesRegex(AuditError, "every target in condition A"):
            build_audit(
                [("A", first), ("B", second)],
                labels=one_sided,
                target_map=paired_target_map(),
                item_manifest=paired_item_manifest(),
            )

        mismatched_items = completed_labels()
        del mismatched_items["items"][-1]
        with self.assertRaisesRegex(AuditError, "exactly cover"):
            build_audit(
                [("A", first), ("B", second)],
                labels=mismatched_items,
                target_map=paired_target_map(),
                item_manifest=paired_item_manifest(),
            )

        condition_specific_manifest = paired_item_manifest()
        condition_specific_item = condition_specific_manifest["items"][0]
        condition_specific_item["conditions"][1] = {
            "condition": "B",
            "present": False,
            "disposition": {
                "state": "absent",
                "reason": "condition_did_not_emit_subject",
                "warning_present": False,
                "gate_decisions": [],
                "factreasoner": {"phases": []},
                "repair": {
                    "status": "not_applicable",
                    "predecessor_candidate_sha256": None,
                    "selected_candidate_sha256": None,
                    "record_sha256": None,
                },
            },
            "artifact_bindings": [],
            "evidence_bindings": [],
        }
        condition_specific_manifest["inventory"][1]["warnings"] = 3
        condition_specific_manifest.pop("manifest_sha256")
        condition_specific_manifest["manifest_sha256"] = hashlib.sha256(
            canonical(condition_specific_manifest)
        ).hexdigest()
        condition_specific_labels = completed_labels()
        condition_specific_labels["items"] = [
            item
            for item in condition_specific_labels["items"]
            if not (item["condition"] == "B" and item["item_id"] == "label-item-1")
        ]
        condition_specific_labels["item_manifest_sha256"] = (
            condition_specific_manifest["manifest_sha256"]
        )
        condition_specific = build_audit(
            [("A", first), ("B", second)],
            labels=condition_specific_labels,
            target_map=paired_target_map(),
            item_manifest=condition_specific_manifest,
        )
        self.assertEqual(
            4,
            condition_specific["human_labels"]["conditions"]["A"][
                "eligible_items"
            ]["warnings"],
        )
        self.assertEqual(
            3,
            condition_specific["human_labels"]["conditions"]["B"][
                "eligible_items"
            ]["warnings"],
        )

        failed_target = quality_report(include_failed=True)
        with self.assertRaisesRegex(AuditError, "every target in condition A"):
            build_audit(
                [("A", failed_target), ("B", failed_target)],
                labels=completed_labels(),
                target_map=paired_target_map(include_failed=True),
                item_manifest=paired_item_manifest(),
            )

        incomplete = deepcopy(completed_labels())
        incomplete["study_status"] = "annotation_in_progress"
        with self.assertRaisesRegex(AuditError, "violate their JSON Schema"):
            build_audit(
                [("A", first), ("B", second)],
                labels=incomplete,
                target_map=paired_target_map(),
                item_manifest=paired_item_manifest(),
            )

        missing_source_binding = deepcopy(completed_labels())
        del missing_source_binding["items"][0]["source_binding"]
        with self.assertRaisesRegex(AuditError, "violate their JSON Schema"):
            build_audit(
                [("A", first), ("B", second)],
                labels=missing_source_binding,
                target_map=paired_target_map(),
                item_manifest=paired_item_manifest(),
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
                item_manifest=paired_item_manifest(),
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
            self.assertEqual(value["report_version"], "model-card-paired-failure-audit/v2")
            self.assertEqual(main(args), 2)

    def test_cli_hashes_private_target_map_without_exporting_target_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "condition-a.json"
            second = root / "condition-b.json"
            labels_path = root / "labels.json"
            target_map_path = root / "private-target-map.json"
            item_manifest_path = root / "private-item-manifest.json"
            output = root / "audit.json"
            first.write_bytes(canonical(quality_report()) + b"\n")
            second.write_bytes(canonical(quality_report()) + b"\n")
            labels_path.write_bytes(canonical(completed_labels()) + b"\n")
            target_map_path.write_bytes(canonical(paired_target_map()) + b"\n")
            item_manifest_path.write_bytes(canonical(paired_item_manifest()) + b"\n")

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
                        "--item-manifest",
                        str(item_manifest_path),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            value = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("paired_audit_target_map", value["input_receipts"])
            self.assertIn("paired_audit_item_manifest", value["input_receipts"])
            self.assertEqual(value["human_labels"]["targets"], 1)
            self.assertNotIn(TARGET_REQUEST, output.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
