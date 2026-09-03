from __future__ import annotations

from copy import deepcopy
import unittest

from model_cards.bindings import quote_binding, source_from_dict, structured_binding
from model_cards.claim_gate import (
    ClaimCandidate,
    ClaimGateError,
    ClaimGateRecord,
    ClaimGateReplayError,
    DecisionStatus,
    GATE_ORDER,
    GateName,
    ProseCheckerDecision,
    correct_candidate,
    evaluate_claim_gate,
    make_context_statement_value,
    make_mitigation_value,
    make_publisher_risk_value,
    verify_claim_gate_record,
)
from model_cards.models import EvidenceKind, RelationToTarget, SourceDocument, SourceRole, TargetIdentity
from model_cards.pointer_registry import (
    DEFAULT_POINTER_FIELD_REGISTRY,
    POINTER_REGISTRY_NAME,
    POINTER_REGISTRY_VERSION,
)
from tests.helpers import synthetic_artifact, synthetic_specification


class ClaimSupportGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = synthetic_artifact()
        self.target = self.artifact.target
        self.sources = tuple(
            source_from_dict(item) for item in synthetic_specification()["sources"]
        )

    def binding(self, field_path: str):
        return next(item for item in self.artifact.bindings if item.field_path == field_path)

    def candidate(self, field_path: str) -> ClaimCandidate:
        return ClaimCandidate.from_binding(self.target, self.binding(field_path))

    def accepting_prose_checks(
        self, candidate: ClaimCandidate
    ) -> tuple[
        ProseCheckerDecision,
        ProseCheckerDecision,
        ProseCheckerDecision,
    ]:
        return (
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.ENTITY_SCOPE,
                checker="tests/explicit-prose-checker-v1",
                method="bounded_semantic_entity_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_entity_scope",
            ),
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.FIELD_FIT,
                checker="tests/explicit-prose-checker-v1",
                method="bounded_semantic_field_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_field_fit",
            ),
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=GateName.VALUE_SUPPORT,
                checker="tests/explicit-prose-checker-v1",
                method="bounded_complete_value_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_value_support",
            ),
        )

    @staticmethod
    def outcome(record: ClaimGateRecord, gate: GateName):
        return next(item for item in record.decisions if item.gate is gate)

    def test_structured_candidate_passes_four_independent_decisions_and_replays(self) -> None:
        candidate = self.candidate("identity.license")
        record = evaluate_claim_gate(candidate, self.sources)

        self.assertTrue(record.projection_eligible)
        self.assertEqual(tuple(item.gate for item in record.decisions), GATE_ORDER)
        self.assertTrue(all(item.status is DecisionStatus.ACCEPTED for item in record.decisions))
        for decision in record.decisions:
            self.assertTrue(decision.checker)
            self.assertTrue(decision.method)
            self.assertTrue(decision.reason)
            self.assertGreaterEqual(len(decision.input_digests), 3)
            self.assertEqual(len(decision.content_sha256), 64)

        encoded = record.to_dict()
        decoded = ClaimGateRecord.from_dict(deepcopy(encoded))
        self.assertEqual(decoded.to_dict(), encoded)
        verify_claim_gate_record(decoded, self.sources)

    def test_section_and_table_context_round_trip_and_bind_all_decisions(self) -> None:
        source = SourceDocument(
            source_id="synthetic-context-report",
            source_uri="https://example.invalid/reports/context",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="context-report-v1",
            target=self.target,
            synthetic=True,
            text="Synthetic Model 1B reports its result in the evaluation table.",
        )
        binding = quote_binding(
            target=self.target,
            source=source,
            field_path="identity.summary",
            value=source.text,
            quote=source.text,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            section_path=("Evaluation", "Main results"),
            table_id="table:main-results",
        )
        candidate = ClaimCandidate.from_binding(self.target, binding)
        record = evaluate_claim_gate(
            candidate,
            (*self.sources, source),
            self.accepting_prose_checks(candidate),
        )
        encoded = record.to_dict()
        encoded_evidence = encoded["candidate"]["evidence"][0]

        self.assertEqual(encoded_evidence["section_path"], ["Evaluation", "Main results"])
        self.assertEqual(encoded_evidence["table_id"], "table:main-results")
        decoded = ClaimGateRecord.from_dict(deepcopy(encoded))
        self.assertEqual(
            decoded.candidate.evidence[0].section_path,
            ("Evaluation", "Main results"),
        )
        self.assertEqual(decoded.candidate.evidence[0].table_id, "table:main-results")
        self.assertEqual(decoded.to_dict(), encoded)
        verify_claim_gate_record(decoded, (*self.sources, source))
        for decision in decoded.decisions:
            inputs = {item.name: item.sha256 for item in decision.input_digests}
            self.assertEqual(inputs["evidence"], decoded.candidate.evidence_sha256)

        missing = deepcopy(encoded)
        del missing["candidate"]["evidence"][0]["section_path"]
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(missing)

        tampered = deepcopy(encoded)
        tampered["candidate"]["evidence"][0]["section_path"].append("Altered")
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(tampered)

        invalid_table = deepcopy(encoded)
        invalid_table["candidate"]["evidence"][0]["table_id"] = "not a valid/table id"
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(invalid_table)

        evidence = candidate.evidence[0]
        changed_evidence = type(evidence)(
            kind=evidence.kind,
            source_id=evidence.source_id,
            source_uri=evidence.source_uri,
            source_role=evidence.source_role,
            source_revision=evidence.source_revision,
            source_sha256=evidence.source_sha256,
            source_target=evidence.source_target,
            synthetic=evidence.synthetic,
            verified=evidence.verified,
            quote=evidence.quote,
            char_start=evidence.char_start,
            char_end=evidence.char_end,
            section_path=("Evaluation", "Altered results"),
            table_id=evidence.table_id,
        )
        changed = ClaimCandidate(
            target=candidate.target,
            field_path=candidate.field_path,
            value=candidate.value,
            claim_entity=candidate.claim_entity,
            relation=candidate.relation,
            evidence=(changed_evidence,),
        )
        self.assertNotEqual(changed.evidence_sha256, candidate.evidence_sha256)
        self.assertNotEqual(changed.candidate_id, candidate.candidate_id)
        with self.assertRaisesRegex(ClaimGateError, "stale checker decision"):
            evaluate_claim_gate(
                changed,
                (*self.sources, source),
                record.checker_decisions,
            )

    def test_prose_requires_three_explicit_bounded_checker_decisions(self) -> None:
        candidate = self.candidate("identity.summary")
        missing = evaluate_claim_gate(candidate, self.sources)
        self.assertFalse(missing.projection_eligible)
        self.assertEqual(
            self.outcome(missing, GateName.ENTITY_SCOPE).reason,
            "prose_entity_checker_unavailable",
        )
        self.assertEqual(
            self.outcome(missing, GateName.FIELD_FIT).reason,
            "prose_field_checker_unavailable",
        )
        self.assertEqual(
            self.outcome(missing, GateName.VALUE_SUPPORT).reason,
            "prose_value_checker_unavailable",
        )

        checked = evaluate_claim_gate(
            candidate,
            self.sources,
            self.accepting_prose_checks(candidate),
        )
        self.assertTrue(checked.projection_eligible)
        verify_claim_gate_record(checked, self.sources)

    def test_context_wrapper_metadata_is_deterministic_while_description_is_quote_bound(self) -> None:
        source = SourceDocument(
            source_id="synthetic-limitations-report",
            source_uri="https://example.invalid/reports/limitations",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="limitations-v1",
            target=self.target,
            synthetic=True,
            text="The model may produce incorrect factual statements.",
        )
        carrier = quote_binding(
            target=self.target,
            source=source,
            field_path="identity.summary",
            value=source.text,
            quote=source.text,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        evidence = carrier.evidence
        value = make_context_statement_value(
            field_path="use_and_risk.limitations[0]",
            description=source.text or "",
            origin="publisher_reported",
            evidence=evidence,
        )
        candidate = ClaimCandidate(
            target=self.target,
            field_path="use_and_risk.limitations[0]",
            value=value,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=evidence,
        )
        record = evaluate_claim_gate(
            candidate,
            (*self.sources, source),
            self.accepting_prose_checks(candidate),
        )
        self.assertTrue(record.projection_eligible)
        self.assertNotIn(value["context_id"], source.text or "")
        self.assertNotIn(value["source_refs"][0], source.text or "")

        for key, replacement in (
            ("context_id", "context:000000000000000000000000"),
            ("source_refs", ["synthetic-unrelated-source"]),
            ("origin", "operator_defined"),
        ):
            with self.subTest(key=key):
                malformed = deepcopy(value)
                malformed[key] = replacement
                bad = ClaimCandidate(
                    target=self.target,
                    field_path=candidate.field_path,
                    value=malformed,
                    claim_entity=candidate.claim_entity,
                    relation=candidate.relation,
                    evidence=evidence,
                )
                bad_record = evaluate_claim_gate(
                    bad,
                    (*self.sources, source),
                    self.accepting_prose_checks(bad),
                )
                self.assertEqual(
                    self.outcome(bad_record, GateName.VALUE_SUPPORT).reason,
                    "deterministic_wrapper_metadata_invalid",
                )

    def test_mitigation_wrapper_has_no_generic_metadata_bypass(self) -> None:
        source = SourceDocument(
            source_id="synthetic-mitigation-report",
            source_uri="https://example.invalid/reports/mitigation",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="mitigation-v1",
            target=self.target,
            synthetic=True,
            text="Users should verify important factual statements against primary sources.",
        )
        carrier = quote_binding(
            target=self.target,
            source=source,
            field_path="identity.summary",
            value=source.text,
            quote=source.text,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        value = make_mitigation_value(
            description=source.text or "",
            evidence=carrier.evidence,
        )
        candidate = ClaimCandidate(
            target=self.target,
            field_path="use_and_risk.mitigations[0]",
            value=value,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=carrier.evidence,
        )
        record = evaluate_claim_gate(
            candidate,
            (*self.sources, source),
            self.accepting_prose_checks(candidate),
        )
        self.assertTrue(record.projection_eligible)

        malformed = deepcopy(value)
        malformed["mitigation_id"] = "mitigation:model_generated_label"
        bad = ClaimCandidate(
            target=self.target,
            field_path=candidate.field_path,
            value=malformed,
            claim_entity=candidate.claim_entity,
            relation=candidate.relation,
            evidence=candidate.evidence,
        )
        bad_record = evaluate_claim_gate(
            bad,
            (*self.sources, source),
            self.accepting_prose_checks(bad),
        )
        self.assertEqual(
            self.outcome(bad_record, GateName.VALUE_SUPPORT).reason,
            "deterministic_wrapper_metadata_invalid",
        )
        with self.assertRaises(ClaimGateError):
            make_mitigation_value(
                description=source.text or "",
                evidence=carrier.evidence,
                origin="project_recommended",
            )

    def test_publisher_risk_wrapper_is_exact_and_taxonomy_risk_cannot_bypass_it(self) -> None:
        name = "Misinformation risk"
        description = "The model may produce incorrect factual statements."
        rationale = "This risk applies to the exact checkpoint."
        source = SourceDocument(
            source_id="synthetic-publisher-risk",
            source_uri="https://example.invalid/reports/publisher-risk",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="publisher-risk-v1",
            target=self.target,
            synthetic=True,
            text=f"{name}. {description} {rationale}",
        )
        carrier = quote_binding(
            target=self.target,
            source=source,
            field_path="identity.summary",
            value=source.text,
            quote=source.text,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        value = make_publisher_risk_value(
            name=name,
            description=description,
            applicability_rationale=rationale,
            evidence=carrier.evidence,
        )
        candidate = ClaimCandidate(
            target=self.target,
            field_path="use_and_risk.identified_risks[0]",
            value=value,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=carrier.evidence,
        )
        record = evaluate_claim_gate(
            candidate,
            (*self.sources, source),
            self.accepting_prose_checks(candidate),
        )
        self.assertTrue(record.projection_eligible)
        self.assertNotIn(value["risk_id"], source.text or "")
        self.assertNotIn("source_binding", source.text or "")
        self.assertEqual(value["taxonomy"], None)
        self.assertEqual(value["review_status"], "generated_unreviewed")

        mutations = []
        arbitrary_id = deepcopy(value)
        arbitrary_id["risk_id"] = "publisher-risk:arbitrary"
        mutations.append(arbitrary_id)
        altered_ground = deepcopy(value)
        altered_ground["grounds"][0]["relevance"] = "Model-generated relevance"
        mutations.append(altered_ground)
        invented_link = deepcopy(value)
        invented_link["mitigation_assessment"] = "linked"
        invented_link["mitigation_refs"] = ["mitigation:verify-sources"]
        mutations.append(invented_link)
        taxonomy_risk = deepcopy(value)
        taxonomy_risk.update(
            {
                "risk_id": "taxonomy:risk-example",
                "identification_origin": "taxonomy_identified",
                "taxonomy": {
                    "taxonomy_id": "example-taxonomy",
                    "name": "Example Taxonomy",
                    "version": "v1",
                    "source_url": "https://example.invalid/taxonomy",
                    "snapshot_sha256": "a" * 64,
                },
                "mapping_provenance": {
                    "method": "ai_atlas_nexus",
                    "tool_version": "v1",
                    "inference_model": "test/model",
                    "inference_config_sha256": "b" * 64,
                },
            }
        )
        mutations.append(taxonomy_risk)
        for index, malformed in enumerate(mutations):
            with self.subTest(index=index):
                bad = ClaimCandidate(
                    target=self.target,
                    field_path=candidate.field_path,
                    value=malformed,
                    claim_entity=candidate.claim_entity,
                    relation=candidate.relation,
                    evidence=candidate.evidence,
                )
                bad_record = evaluate_claim_gate(
                    bad,
                    (*self.sources, source),
                    self.accepting_prose_checks(bad),
                )
                self.assertEqual(
                    self.outcome(bad_record, GateName.VALUE_SUPPORT).reason,
                    "deterministic_wrapper_metadata_invalid",
                )
                self.assertFalse(bad_record.projection_eligible)
        with self.assertRaises(ClaimGateError):
            make_publisher_risk_value(
                name=name,
                description=description,
                applicability_rationale=rationale,
                evidence=carrier.evidence,
                mitigation_refs=("mitigation:verify-sources",),
            )

    def test_quote_with_73_5_cannot_support_proposed_99_0(self) -> None:
        original = self.candidate("evaluation.benchmark_scores[0]")
        wrong = ClaimCandidate(
            target=self.target,
            field_path=original.field_path,
            value={
                "benchmark": "Toy Reasoning",
                "metric": "accuracy",
                "score": 99.0,
                "setting": "zero-shot",
            },
            claim_entity=original.claim_entity,
            relation=original.relation,
            evidence=original.evidence,
            benchmark_scope={
                "benchmark": "Toy Reasoning",
                "metric": "accuracy",
                "setting": "zero-shot",
            },
        )
        record = evaluate_claim_gate(wrong, self.sources, self.accepting_prose_checks(wrong))

        self.assertEqual(
            self.outcome(record, GateName.VALUE_SUPPORT).reason,
            "complete_value_not_in_evidence",
        )
        self.assertFalse(record.projection_eligible)

    def test_genuine_quote_assigned_to_wrong_field_is_withheld_without_rewrite(self) -> None:
        summary = self.candidate("identity.summary")
        wrong = ClaimCandidate(
            target=self.target,
            field_path="identity.license",
            value=summary.value,
            claim_entity=summary.claim_entity,
            relation=summary.relation,
            evidence=summary.evidence,
        )
        checks = (
            ProseCheckerDecision.for_candidate(
                wrong,
                gate=GateName.ENTITY_SCOPE,
                checker="tests/explicit-prose-checker-v1",
                method="bounded_semantic_entity_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_entity_scope",
            ),
            ProseCheckerDecision.for_candidate(
                wrong,
                gate=GateName.FIELD_FIT,
                checker="tests/explicit-prose-checker-v1",
                method="bounded_semantic_field_review",
                status=DecisionStatus.WITHHELD,
                reason="semantic_field_mismatch",
            ),
            ProseCheckerDecision.for_candidate(
                wrong,
                gate=GateName.VALUE_SUPPORT,
                checker="tests/explicit-prose-checker-v1",
                method="bounded_complete_value_review",
                status=DecisionStatus.ACCEPTED,
                reason="semantic_value_support",
            ),
        )
        before = wrong.to_dict()
        record = evaluate_claim_gate(wrong, self.sources, checks)

        self.assertEqual(self.outcome(record, GateName.FIELD_FIT).status, DecisionStatus.WITHHELD)
        self.assertEqual(self.outcome(record, GateName.VALUE_SUPPORT).status, DecisionStatus.ACCEPTED)
        self.assertEqual(wrong.to_dict(), before)
        self.assertFalse(record.projection_eligible)

    def test_paraphrased_or_truncated_quote_does_not_support_full_value(self) -> None:
        original = self.candidate("training.adaptations")
        proposed = ClaimCandidate(
            target=self.target,
            field_path=original.field_path,
            value="Preference tuning was applied to the exact checkpoint",
            claim_entity=original.claim_entity,
            relation=original.relation,
            evidence=original.evidence,
        )
        record = evaluate_claim_gate(
            proposed,
            self.sources,
            self.accepting_prose_checks(proposed),
        )
        self.assertEqual(
            self.outcome(record, GateName.VALUE_SUPPORT).reason,
            "complete_value_not_in_evidence",
        )

    def test_source_drift_is_visible_and_breaks_strict_replay(self) -> None:
        candidate = self.candidate("identity.summary")
        record = evaluate_claim_gate(
            candidate,
            self.sources,
            self.accepting_prose_checks(candidate),
        )
        original = next(item for item in self.sources if item.source_id == "synthetic-model-page")
        drifted = SourceDocument(
            source_id=original.source_id,
            source_uri=original.source_uri,
            role=original.role,
            source_revision=original.source_revision,
            target=original.target,
            text=(original.text or "") + " Drift.",
            synthetic=original.synthetic,
        )
        replay_sources = tuple(
            drifted if item.source_id == drifted.source_id else item for item in self.sources
        )

        drift_result = evaluate_claim_gate(
            candidate,
            replay_sources,
            self.accepting_prose_checks(candidate),
        )
        self.assertEqual(
            self.outcome(drift_result, GateName.COORDINATE_INTEGRITY).reason,
            "replay_source_identity_mismatch",
        )
        with self.assertRaises(ClaimGateReplayError):
            verify_claim_gate_record(record, replay_sources)

    def test_base_source_cannot_leak_into_exact_instruct_claim(self) -> None:
        family = self.candidate("training.training_data_size")
        leaked = ClaimCandidate(
            target=self.target,
            field_path=family.field_path,
            value=family.value,
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=family.evidence,
        )
        record = evaluate_claim_gate(
            leaked,
            self.sources,
            self.accepting_prose_checks(leaked),
        )
        self.assertEqual(
            self.outcome(record, GateName.ENTITY_SCOPE).reason,
            "source_target_not_exact",
        )
        self.assertFalse(record.projection_eligible)

    def test_true_sibling_claim_is_allowed_only_in_related_model_field(self) -> None:
        comparison = self.candidate("evaluation.related_model_scores[0]")
        sibling = ClaimCandidate(
            target=self.target,
            field_path=comparison.field_path,
            value=comparison.value,
            claim_entity=comparison.claim_entity,
            relation=RelationToTarget.SIBLING_CHECKPOINT,
            evidence=comparison.evidence,
        )
        record = evaluate_claim_gate(sibling, self.sources)
        self.assertTrue(record.projection_eligible)
        self.assertEqual(
            self.outcome(record, GateName.ENTITY_SCOPE).reason,
            "explicit_related_model_relation",
        )

        wrong_field = ClaimCandidate(
            target=self.target,
            field_path="identity.summary",
            value="Sibling checkpoint result",
            claim_entity=comparison.claim_entity,
            relation=RelationToTarget.SIBLING_CHECKPOINT,
            evidence=comparison.evidence,
        )
        wrong = evaluate_claim_gate(wrong_field, self.sources)
        self.assertEqual(
            self.outcome(wrong, GateName.ENTITY_SCOPE).reason,
            "relation_not_permitted_for_field",
        )

    def test_wrong_benchmark_model_is_withheld_by_entity_scope(self) -> None:
        other_target = TargetIdentity("example-lab/other-model", "8" * 40)
        source = SourceDocument(
            source_id="synthetic-other-benchmark",
            source_uri="https://example.invalid/reports/other-benchmark",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="other-report-v1",
            target=other_target,
            synthetic=True,
            text="Other Model reports 73.5 accuracy on Toy Reasoning in a zero-shot setting.",
        )
        binding = quote_binding(
            target=self.target,
            source=source,
            field_path="evaluation.benchmark_scores[0]",
            value={
                "benchmark": "Toy Reasoning",
                "metric": "accuracy",
                "score": 73.5,
                "setting": "zero-shot",
            },
            quote=source.text or "",
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            benchmark_scope={
                "benchmark": "Toy Reasoning",
                "metric": "accuracy",
                "setting": "zero-shot",
            },
        )
        candidate = ClaimCandidate.from_binding(self.target, binding)
        record = evaluate_claim_gate(
            candidate,
            (*self.sources, source),
            self.accepting_prose_checks(candidate),
        )
        self.assertEqual(
            self.outcome(record, GateName.ENTITY_SCOPE).reason,
            "source_target_not_exact",
        )

    def test_wrong_benchmark_version_or_subset_is_not_complete_support(self) -> None:
        source = SourceDocument(
            source_id="synthetic-versioned-benchmark",
            source_uri="https://example.invalid/reports/versioned-benchmark",
            role=SourceRole.DEVELOPER_REPORT,
            source_revision="versioned-report-v1",
            target=self.target,
            synthetic=True,
            text=(
                "Synthetic Model 1B reports 73.5 accuracy on Toy Reasoning v1 "
                "in a zero-shot main-subset setting."
            ),
        )
        cases = (
            ("Toy Reasoning v2", "zero-shot main-subset"),
            ("Toy Reasoning v1", "zero-shot hard-subset"),
        )
        for index, (benchmark, setting) in enumerate(cases):
            with self.subTest(index=index):
                binding = quote_binding(
                    target=self.target,
                    source=source,
                    field_path="evaluation.benchmark_scores[0]",
                    value={
                        "benchmark": benchmark,
                        "metric": "accuracy",
                        "score": 73.5,
                        "setting": setting,
                    },
                    quote=source.text or "",
                    claim_entity=f"{self.target.model_id}@{self.target.revision}",
                    relation=RelationToTarget.EXACT_TARGET,
                    benchmark_scope={
                        "benchmark": benchmark,
                        "metric": "accuracy",
                        "setting": setting,
                    },
                )
                candidate = ClaimCandidate.from_binding(self.target, binding)
                record = evaluate_claim_gate(
                    candidate,
                    (*self.sources, source),
                    self.accepting_prose_checks(candidate),
                )
                self.assertEqual(
                    self.outcome(record, GateName.VALUE_SUPPORT).reason,
                    "complete_value_not_in_evidence",
                )

    def test_conflicting_structured_licenses_remain_visible_and_withheld(self) -> None:
        first = SourceDocument(
            source_id="synthetic-license-one",
            source_uri=f"hf://{self.target.model_id}@{self.target.revision}/license-one.json",
            role=SourceRole.HUGGING_FACE_METADATA,
            source_revision=self.target.revision,
            target=self.target,
            synthetic=True,
            data={"license": "MIT"},
        )
        second = SourceDocument(
            source_id="synthetic-license-two",
            source_uri=f"hf://{self.target.model_id}@{self.target.revision}/license-two.json",
            role=SourceRole.HUGGING_FACE_METADATA,
            source_revision=self.target.revision,
            target=self.target,
            synthetic=True,
            data={"license": "Apache-2.0"},
        )
        first_binding = structured_binding(
            target=self.target,
            source=first,
            field_path="identity.license",
            pointer="/license",
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        second_binding = structured_binding(
            target=self.target,
            source=second,
            field_path="identity.license",
            pointer="/license",
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        candidate = ClaimCandidate(
            target=self.target,
            field_path="identity.license",
            value="MIT",
            claim_entity=f"{self.target.model_id}@{self.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            evidence=(first_binding.evidence[0], second_binding.evidence[0]),
        )
        record = evaluate_claim_gate(candidate, (*self.sources, first, second))
        self.assertEqual(
            self.outcome(record, GateName.VALUE_SUPPORT).reason,
            "conflicting_evidence_values",
        )
        self.assertEqual(
            self.outcome(record, GateName.COORDINATE_INTEGRITY).status,
            DecisionStatus.ACCEPTED,
        )

    def test_registered_pointer_assigned_to_wrong_field_is_withheld(self) -> None:
        name = self.candidate("identity.name")
        wrong = ClaimCandidate(
            target=self.target,
            field_path="identity.license",
            value=name.value,
            claim_entity=name.claim_entity,
            relation=name.relation,
            evidence=name.evidence,
        )
        record = evaluate_claim_gate(wrong, self.sources)
        self.assertEqual(
            self.outcome(record, GateName.FIELD_FIT).reason,
            "structured_pointer_wrong_field",
        )
        self.assertEqual(
            self.outcome(record, GateName.VALUE_SUPPORT).status,
            DecisionStatus.ACCEPTED,
        )
        self.assertFalse(record.projection_eligible)

    def test_structured_pointer_and_fragment_are_replayed_against_source(self) -> None:
        candidate = self.candidate("identity.license")
        evidence = candidate.evidence[0]
        mismatched = type(evidence)(
            kind=EvidenceKind.STRUCTURED,
            source_id=evidence.source_id,
            source_uri=evidence.source_uri,
            source_role=evidence.source_role,
            source_revision=evidence.source_revision,
            source_sha256=evidence.source_sha256,
            source_target=evidence.source_target,
            synthetic=evidence.synthetic,
            verified=True,
            pointer="/display_name",
            fragment=evidence.fragment,
        )
        wrong = ClaimCandidate(
            target=candidate.target,
            field_path=candidate.field_path,
            value=candidate.value,
            claim_entity=candidate.claim_entity,
            relation=candidate.relation,
            evidence=(mismatched,),
        )
        record = evaluate_claim_gate(wrong, self.sources)
        self.assertEqual(
            self.outcome(record, GateName.COORDINATE_INTEGRITY).reason,
            "pointer_fragment_mismatch",
        )
        self.assertEqual(
            self.outcome(record, GateName.FIELD_FIT).reason,
            "structured_pointer_wrong_field",
        )

    def test_strict_deserialization_rejects_missing_duplicate_ambiguous_and_malformed(self) -> None:
        candidate = self.candidate("identity.summary")
        record = evaluate_claim_gate(
            candidate,
            self.sources,
            self.accepting_prose_checks(candidate),
        )
        encoded = record.to_dict()

        missing = deepcopy(encoded)
        missing["decisions"].pop()
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(missing)

        duplicate = deepcopy(encoded)
        duplicate["decisions"][1] = deepcopy(duplicate["decisions"][0])
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(duplicate)

        ambiguous = deepcopy(encoded)
        ambiguous["checker_decisions"].append(deepcopy(ambiguous["checker_decisions"][0]))
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(ambiguous)

        malformed = deepcopy(encoded)
        malformed["unexpected"] = "not allowed"
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(malformed)

        tampered = deepcopy(encoded)
        tampered["decisions"][0]["reason"] = "tampered_reason"
        with self.assertRaises(ClaimGateError):
            ClaimGateRecord.from_dict(tampered)

    def test_stale_checker_decision_is_rejected_after_correction(self) -> None:
        prior = self.candidate("identity.summary")
        checks = self.accepting_prose_checks(prior)
        corrected = correct_candidate(prior, value="Synthetic Model 1B")

        self.assertEqual(corrected.previous_candidate_id, prior.candidate_id)
        self.assertNotEqual(corrected.candidate_id, prior.candidate_id)
        self.assertEqual(prior.previous_candidate_id, None)
        with self.assertRaisesRegex(ClaimGateError, "stale checker decision"):
            evaluate_claim_gate(corrected, self.sources, checks)
        with self.assertRaisesRegex(ClaimGateError, "correction must change"):
            correct_candidate(prior, value=prior.value)

    def test_registry_is_closed_named_versioned_and_content_addressed(self) -> None:
        registry = DEFAULT_POINTER_FIELD_REGISTRY
        self.assertEqual(registry.name, POINTER_REGISTRY_NAME)
        self.assertEqual(registry.version, POINTER_REGISTRY_VERSION)
        self.assertEqual(len(registry.sha256), 64)
        self.assertTrue(registry.rules)
        self.assertTrue(
            all(item.pointer.startswith("/") and item.field_path for item in registry.rules)
        )

    def test_direct_config_string_declarations_are_registered_but_numeric_context_is_not(self) -> None:
        source = SourceDocument(
            source_id="synthetic-direct-config",
            source_uri=f"hf://{self.target.model_id}@{self.target.revision}/config.json",
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=self.target.revision,
            target=self.target,
            synthetic=True,
            data={
                "model_type": "synthetic_decoder",
                "torch_dtype": "bfloat16",
                "max_position_embeddings": 4096,
            },
        )
        for pointer, field_path in (
            ("/model_type", "model_details.architecture_type"),
            ("/torch_dtype", "model_details.precision"),
        ):
            with self.subTest(pointer=pointer):
                binding = structured_binding(
                    target=self.target,
                    source=source,
                    field_path=field_path,
                    pointer=pointer,
                    claim_entity=f"{self.target.model_id}@{self.target.revision}",
                    relation=RelationToTarget.EXACT_TARGET,
                )
                candidate = ClaimCandidate.from_binding(self.target, binding)
                record = evaluate_claim_gate(candidate, (*self.sources, source))
                self.assertTrue(record.projection_eligible)

        lookup = DEFAULT_POINTER_FIELD_REGISTRY.lookup(
            source_role=SourceRole.HUGGING_FACE_SNAPSHOT,
            pointer="/max_position_embeddings",
            field_path="model_details.context_length",
            fragment=4096,
        )
        self.assertEqual(lookup.status.value, "unregistered")

    def test_quote_coordinate_offsets_are_replayed_not_just_quote_presence(self) -> None:
        candidate = self.candidate("identity.summary")
        evidence = candidate.evidence[0]
        shifted = type(evidence)(
            kind=EvidenceKind.QUOTE,
            source_id=evidence.source_id,
            source_uri=evidence.source_uri,
            source_role=evidence.source_role,
            source_revision=evidence.source_revision,
            source_sha256=evidence.source_sha256,
            source_target=evidence.source_target,
            synthetic=evidence.synthetic,
            verified=True,
            quote=evidence.quote,
            char_start=(evidence.char_start or 0) + 1,
            char_end=(evidence.char_end or 0) + 1,
        )
        shifted_candidate = ClaimCandidate(
            target=candidate.target,
            field_path=candidate.field_path,
            value=candidate.value,
            claim_entity=candidate.claim_entity,
            relation=candidate.relation,
            evidence=(shifted,),
        )
        record = evaluate_claim_gate(
            shifted_candidate,
            self.sources,
            self.accepting_prose_checks(shifted_candidate),
        )
        self.assertEqual(
            self.outcome(record, GateName.COORDINATE_INTEGRITY).reason,
            "quote_coordinate_mismatch",
        )


if __name__ == "__main__":
    unittest.main()
