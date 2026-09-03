from __future__ import annotations

from copy import deepcopy
import hashlib
from types import SimpleNamespace
import unittest

from model_cards.artifact import CardArtifact, project_card
from model_cards.bindings import quote_binding, structured_binding
from model_cards.claim_gate import (
    ClaimCandidate,
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
    evaluate_claim_gate,
)
from model_cards.extraction import (
    ExtractionBatch,
    QuoteProposal,
    materialize_quote_batch,
)
from model_cards.family_risk import (
    AuthorizedFamilyContext,
    FamilyContextApplicabilityDecision,
    FamilyDecisionStatus,
    FamilyMembershipDecision,
    FamilyRiskAuthorizationReport,
    FamilyRiskBridgeError,
    authorize_family_context,
    authorized_nexus_inputs,
    derive_authorized_family_use_contexts,
    build_family_risk_authorization_report,
    select_config_family_membership,
)
from model_cards.model_family import derive_config_model_family
from model_cards.models import (
    Disposition,
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from model_cards.quote import normalize_ws
from model_cards.schema import get_field


REVISION = "a" * 40


class FamilyRiskBridgeTests(unittest.TestCase):
    def semantic_checks(
        self, candidate: ClaimCandidate
    ) -> tuple[ProseCheckerDecision, ...]:
        return tuple(
            ProseCheckerDecision.for_candidate(
                candidate,
                gate=gate,
                checker="tests/family-prose-checker-v1",
                method=f"bounded_family_{gate.value}_review",
                status=DecisionStatus.ACCEPTED,
                reason=f"family_{gate.value}_accepted",
            )
            for gate in (
                GateName.ENTITY_SCOPE,
                GateName.FIELD_FIT,
                GateName.VALUE_SUPPORT,
            )
        )

    def inputs(
        self,
        *,
        model_id: str,
        family_id: str,
        statement: str,
        field_path: str,
        heading: str,
        claim_entity: str,
    ):
        target = TargetIdentity(model_id, REVISION)
        readme = SourceDocument(
            source_id="publisher_readme",
            source_uri=(
                f"https://huggingface.co/{model_id}/resolve/{REVISION}/README.md"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=target,
            synthetic=False,
            text=f"# {heading}\n\n## Usage and Limitations\n\n{statement}\n",
        )
        metadata = SourceDocument(
            source_id="target_metadata",
            source_uri=f"https://huggingface.co/api/models/{model_id}",
            role=SourceRole.HUGGING_FACE_METADATA,
            source_revision=REVISION,
            target=target,
            synthetic=False,
            data={"model_family": family_id},
        )
        catalog_sha256 = hashlib.sha256(model_id.encode()).hexdigest()
        catalog = SimpleNamespace(
            target=target,
            catalog_sha256=catalog_sha256,
            by_id={readme.source_id: readme, metadata.source_id: metadata},
        )
        proposal = QuoteProposal(
            source_id=readme.source_id,
            field_path=field_path,
            value=statement,
            quote=statement,
            claim_entity=claim_entity,
            relation=RelationToTarget.MODEL_FAMILY,
        )
        batch = ExtractionBatch.build(
            target=target,
            source_catalog_sha256=catalog_sha256,
            provider="Together",
            inference_config_sha256="b" * 64,
            proposals=(proposal,),
        )
        family_candidate = materialize_quote_batch(batch, catalog).candidates[0]
        family_gate = evaluate_claim_gate(
            family_candidate,
            (readme, metadata),
            self.semantic_checks(family_candidate),
        )
        membership_candidate = ClaimCandidate.from_binding(
            target,
            structured_binding(
                target=target,
                source=metadata,
                field_path="lineage.model_family",
                pointer="/model_family",
                claim_entity=f"{model_id}@{REVISION}",
                relation=RelationToTarget.EXACT_TARGET,
            ),
        )
        membership_gate = evaluate_claim_gate(
            membership_candidate, (readme, metadata)
        )
        membership = FamilyMembershipDecision.for_gate(
            membership_gate,
            family_id=family_id,
            status=FamilyDecisionStatus.ACCEPTED,
            checker="tests/family-membership-checker-v1",
            method="exact_target_config_family_attestation",
            reason="family_membership_accepted",
            rationale=(
                "The revision-pinned exact-target metadata identifies this model family."
            ),
        )
        applicability = FamilyContextApplicabilityDecision.for_gate(
            family_gate,
            membership,
            membership_gate,
            status=FamilyDecisionStatus.ACCEPTED,
            checker="tests/family-applicability-checker-v1",
            method="bounded_family_checkpoint_review",
            reason="family_context_applicable",
            rationale=(
                "This family statement is explicitly applicable to the exact checkpoint."
            ),
        )
        return (
            target,
            readme,
            metadata,
            family_candidate,
            family_gate,
            membership_gate,
            membership,
            applicability,
        )

    def test_gemma_family_use_requires_both_decisions_before_nexus(self) -> None:
        statement = (
            "Text Generation: These models can be used to generate creative text "
            "formats such as poems, scripts, code, marketing copy, and email drafts."
        )
        (
            target,
            readme,
            _config,
            candidate,
            family_gate,
            membership_gate,
            membership,
            applicability,
        ) = self.inputs(
            model_id="google/gemma-3-4b-pt",
            family_id="gemma3",
            statement=statement,
            field_path="use_and_risk.intended_uses[0]",
            heading="Gemma 3 model card",
            claim_entity="Gemma 3 model family",
        )

        self.assertEqual(RelationToTarget.MODEL_FAMILY, candidate.relation)
        evidence = candidate.evidence[0]
        self.assertTrue(evidence.verified)
        self.assertEqual(REVISION, evidence.source_revision)
        self.assertEqual(statement, evidence.quote)
        self.assertEqual(
            statement,
            normalize_ws(readme.text)[evidence.char_start : evidence.char_end],
        )
        self.assertFalse(family_gate.projection_eligible)
        scope = next(
            item
            for item in family_gate.decisions
            if item.gate is GateName.ENTITY_SCOPE
        )
        self.assertEqual("relation_not_projection_eligible", scope.reason)

        authorized = authorize_family_context(
            family_gate, membership, membership_gate, applicability
        )
        round_tripped = AuthorizedFamilyContext.from_dict(
            deepcopy(authorized.to_dict())
        )
        self.assertEqual(authorized, round_tripped)
        contexts = derive_authorized_family_use_contexts((authorized,))
        nexus_inputs = authorized_nexus_inputs(contexts, (authorized,))
        self.assertEqual(1, len(nexus_inputs))
        self.assertIn("Publisher-reported model-family intended use", nexus_inputs[0].description)
        self.assertIn(target.model_id, nexus_inputs[0].description)
        self.assertEqual((candidate.candidate_id,), nexus_inputs[0].supporting_candidate_ids)
        self.assertEqual((readme.source_id,), nexus_inputs[0].source_refs)

        # Even after risk-context authorization, the underlying family claim is
        # still withheld from card projection. The bridge has no API that
        # rewrites it into an exact-target binding.
        binding = quote_binding(
            target=target,
            source=readme,
            field_path=candidate.field_path,
            value=candidate.value,
            quote=statement,
            claim_entity=candidate.claim_entity,
            relation=candidate.relation,
            section_path=candidate.evidence[0].section_path,
        )
        self.assertEqual(Disposition.WITHHELD, binding.disposition)
        projected = project_card(CardArtifact(target=target, bindings=(binding,)))
        self.assertEqual(
            "Not specified",
            get_field(projected, "use_and_risk.intended_uses"),
        )

    def test_olmo_family_limitation_is_retained_but_not_a_core_use(self) -> None:
        statement = (
            "The OLMo-2 models have limited safety training, but are not "
            "deployed automatically with in-the-loop filtering of responses like "
            "ChatGPT, so the model can produce problematic outputs (especially "
            "when prompted to do so)."
        )
        (
            _target,
            _readme,
            _config,
            candidate,
            family_gate,
            membership_gate,
            membership,
            applicability,
        ) = self.inputs(
            model_id="allenai/OLMo-2-1124-7B-Instruct",
            family_id="olmo2",
            statement=statement,
            field_path="use_and_risk.limitations[0]",
            heading="OLMo-2-1124-7B-Instruct",
            claim_entity="OLMo-2 model family",
        )
        authorized = authorize_family_context(
            family_gate, membership, membership_gate, applicability
        )

        self.assertEqual(RelationToTarget.MODEL_FAMILY, candidate.relation)
        self.assertEqual(statement, authorized.description)
        # A limitation alone cannot be transformed into a generic use case.
        self.assertEqual((), derive_authorized_family_use_contexts((authorized,)))

    def test_withheld_or_missing_authorization_fails_closed(self) -> None:
        statement = (
            "These models can be used to generate creative text formats for "
            "research and educational applications."
        )
        (
            _target,
            _readme,
            _config,
            _candidate,
            family_gate,
            membership_gate,
            membership,
            _applicability,
        ) = self.inputs(
            model_id="google/gemma-3-4b-it",
            family_id="gemma3",
            statement=statement,
            field_path="use_and_risk.intended_uses[0]",
            heading="Gemma 3 model card",
            claim_entity="Gemma 3 model family",
        )
        withheld = FamilyContextApplicabilityDecision.for_gate(
            family_gate,
            membership,
            membership_gate,
            status=FamilyDecisionStatus.WITHHELD,
            checker="tests/family-applicability-checker-v1",
            method="bounded_family_checkpoint_review",
            reason="checkpoint_applicability_unclear",
            rationale=(
                "The statement does not distinguish this checkpoint from its siblings."
            ),
        )
        with self.assertRaises(FamilyRiskBridgeError):
            authorize_family_context(
                family_gate, membership, membership_gate, withheld
            )
        with self.assertRaises(FamilyRiskBridgeError):
            authorized_nexus_inputs((object(),), ())  # type: ignore[arg-type]

    def test_serialized_decision_tampering_and_membership_mismatch_fail(self) -> None:
        statement = (
            "These models can be used to extract and summarize visual data for "
            "text communications."
        )
        (
            _target,
            _readme,
            _config,
            _candidate,
            family_gate,
            membership_gate,
            membership,
            applicability,
        ) = self.inputs(
            model_id="google/gemma-3-4b-pt",
            family_id="gemma3",
            statement=statement,
            field_path="use_and_risk.intended_uses[0]",
            heading="Gemma 3 model card",
            claim_entity="Gemma 3 model family",
        )
        tampered = applicability.to_dict()
        tampered["family_id"] = "olmo2"
        with self.assertRaises(FamilyRiskBridgeError):
            FamilyContextApplicabilityDecision.from_dict(tampered)

        wrong_membership = membership.to_dict()
        wrong_membership["family_id"] = "olmo2"
        with self.assertRaises(FamilyRiskBridgeError):
            FamilyMembershipDecision.from_dict(wrong_membership)

        # A decision for one family candidate cannot authorize another record.
        other_statement = (
            "These models can support interactive language learning experiences "
            "and provide writing practice."
        )
        other = self.inputs(
            model_id="google/gemma-3-4b-pt",
            family_id="gemma3",
            statement=other_statement,
            field_path="use_and_risk.intended_uses[0]",
            heading="Gemma 3 model card",
            claim_entity="Gemma 3 model family",
        )
        with self.assertRaises(FamilyRiskBridgeError):
            authorize_family_context(
                other[4], membership, membership_gate, applicability
            )

    def test_architecture_type_cannot_authorize_family_membership(self) -> None:
        target = TargetIdentity("google/gemma-3-4b-pt", REVISION)
        config = SourceDocument(
            source_id="target_config",
            source_uri=(
                f"https://huggingface.co/{target.model_id}/resolve/"
                f"{REVISION}/config.json"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=target,
            synthetic=False,
            data={"model_type": "gemma3"},
        )
        architecture_candidate = ClaimCandidate.from_binding(
            target,
            structured_binding(
                target=target,
                source=config,
                field_path="model_details.architecture_type",
                pointer="/model_type",
                claim_entity=f"{target.model_id}@{REVISION}",
                relation=RelationToTarget.EXACT_TARGET,
            ),
        )
        architecture_gate = evaluate_claim_gate(
            architecture_candidate, (config,)
        )
        self.assertTrue(architecture_gate.projection_eligible)
        with self.assertRaises(FamilyRiskBridgeError):
            FamilyMembershipDecision.for_gate(
                architecture_gate,
                family_id="gemma3",
                status=FamilyDecisionStatus.ACCEPTED,
                checker="tests/family-membership-checker-v1",
                method="config_architecture_discriminator",
                reason="architecture_is_not_family_membership",
                rationale=(
                    "A config architecture discriminator does not establish family membership."
                ),
            )

    def test_allowlisted_config_family_is_typed_and_unknown_namespace_abstains(self) -> None:
        target = TargetIdentity("google/gemma-3-4b-pt", REVISION)
        config = SourceDocument(
            source_id="target_config",
            source_uri=(
                f"https://huggingface.co/{target.model_id}/resolve/"
                f"{REVISION}/config.json"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=target,
            synthetic=False,
            data={"model_type": "gemma3"},
        )
        derivation = derive_config_model_family(target, config)
        self.assertIsNotNone(derivation)
        assert derivation is not None
        self.assertEqual("gemma3", derivation.family_id)
        self.assertEqual("gemma3", derivation.rule_id)

        spoof_target = TargetIdentity("acme/Gemma-Compatible", REVISION)
        spoof = SourceDocument(
            source_id="spoof_config",
            source_uri=(
                f"https://huggingface.co/{spoof_target.model_id}/resolve/"
                f"{REVISION}/config.json"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=spoof_target,
            synthetic=False,
            data={"model_type": "gemma3"},
        )
        self.assertIsNone(derive_config_model_family(spoof_target, spoof))

    def test_exact_metadata_config_family_is_typed_and_identity_bound(self) -> None:
        target = TargetIdentity("google/gemma-3-4b-pt", REVISION)
        metadata_uri = (
            f"https://huggingface.co/api/models/{target.model_id}/revision/"
            f"{target.revision}"
        )

        def metadata_source(
            *,
            data: dict[str, object] | None = None,
            source_uri: str = metadata_uri,
            synthetic: bool = False,
        ) -> SourceDocument:
            return SourceDocument(
                source_id="target_metadata",
                source_uri=source_uri,
                role=SourceRole.HUGGING_FACE_METADATA,
                source_revision=REVISION,
                target=target,
                synthetic=synthetic,
                data=(
                    data
                    if data is not None
                    else {
                        "id": target.model_id,
                        "modelId": target.model_id,
                        "sha": target.revision,
                        "config": {"model_type": "gemma3"},
                    }
                ),
            )

        derivation = derive_config_model_family(target, metadata_source())
        self.assertIsNotNone(derivation)
        assert derivation is not None
        self.assertEqual("gemma3", derivation.family_id)
        self.assertEqual("/config/model_type", derivation.pointer)

        invalid_sources = (
            metadata_source(
                data={
                    "id": "google/gemma-3-4b-it",
                    "sha": target.revision,
                    "config": {"model_type": "gemma3"},
                }
            ),
            metadata_source(
                data={
                    "id": target.model_id,
                    "sha": "b" * 40,
                    "config": {"model_type": "gemma3"},
                }
            ),
            metadata_source(
                source_uri=f"https://huggingface.co/api/models/{target.model_id}"
            ),
            metadata_source(synthetic=True),
            SourceDocument(
                source_id="metadata_fallback_config",
                source_uri=metadata_uri,
                role=SourceRole.HUGGING_FACE_SNAPSHOT,
                source_revision=REVISION,
                target=target,
                synthetic=False,
                data={"model_type": "gemma3"},
            ),
        )
        for source in invalid_sources:
            with self.subTest(source_uri=source.source_uri, data=source.data):
                self.assertIsNone(derive_config_model_family(target, source))

        for wrong_checkpoint in invalid_sources[:2]:
            with self.subTest(wrong_checkpoint=wrong_checkpoint.data):
                candidate = ClaimCandidate.from_binding(
                    target,
                    structured_binding(
                        target=target,
                        source=wrong_checkpoint,
                        field_path="lineage.model_family",
                        pointer="/config/model_type",
                        claim_entity=f"{target.model_id}@{target.revision}",
                        relation=RelationToTarget.EXACT_TARGET,
                    ),
                )
                gate = evaluate_claim_gate(candidate, (wrong_checkpoint,))
                self.assertFalse(gate.projection_eligible)
                field_fit = next(
                    item
                    for item in gate.decisions
                    if item.gate is GateName.FIELD_FIT
                )
                self.assertEqual(DecisionStatus.WITHHELD, field_fit.status)
                self.assertEqual(
                    "config_model_family_not_allowlisted",
                    field_fit.reason,
                )

    def test_authorization_report_replays_and_missing_decision_is_unavailable(self) -> None:
        statement = (
            "These models can be used to generate creative text formats for "
            "research and educational applications."
        )
        (
            target,
            _readme,
            _metadata,
            _candidate,
            family_gate,
            membership_gate,
            membership,
            applicability,
        ) = self.inputs(
            model_id="google/gemma-3-4b-pt",
            family_id="gemma3",
            statement=statement,
            field_path="use_and_risk.intended_uses[0]",
            heading="Gemma 3 model card",
            claim_entity="Gemma 3 model family",
        )
        # The report's automatic selector intentionally requires the registered
        # config derivation, not this fixture's explicit metadata membership.
        self.assertIsNone(
            select_config_family_membership((family_gate, membership_gate))
        )
        with self.assertRaises(FamilyRiskBridgeError):
            build_family_risk_authorization_report(
                (family_gate, membership_gate),
                (applicability,),
                target=target,
            )

        empty = build_family_risk_authorization_report(
            (family_gate, membership_gate), target=target
        )
        replayed = FamilyRiskAuthorizationReport.from_dict(empty.to_dict())
        self.assertEqual(empty, replayed)
        self.assertEqual((), replayed.nexus_inputs)

    def test_registered_config_membership_authorizes_report_without_projection(self) -> None:
        statement = (
            "These models can be used to generate creative text formats for "
            "research and educational applications."
        )
        values = self.inputs(
            model_id="google/gemma-3-4b-pt",
            family_id="gemma3",
            statement=statement,
            field_path="use_and_risk.intended_uses[0]",
            heading="Gemma 3 model card",
            claim_entity="Gemma 3 model family",
        )
        target, _readme, _metadata, _candidate, family_gate = values[:5]
        config = SourceDocument(
            source_id="target_config",
            source_uri=(
                f"https://huggingface.co/{target.model_id}/resolve/"
                f"{REVISION}/config.json"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            source_revision=REVISION,
            target=target,
            synthetic=False,
            data={"model_type": "gemma3"},
        )
        membership_candidate = ClaimCandidate.from_binding(
            target,
            structured_binding(
                target=target,
                source=config,
                field_path="lineage.model_family",
                pointer="/model_type",
                claim_entity=f"{target.model_id}@{REVISION}",
                relation=RelationToTarget.EXACT_TARGET,
            ),
        )
        membership_gate = evaluate_claim_gate(
            membership_candidate, (config,)
        )
        selected = select_config_family_membership(
            (family_gate, membership_gate)
        )
        self.assertIsNotNone(selected)
        assert selected is not None
        selected_gate, membership = selected
        applicability = FamilyContextApplicabilityDecision.for_gate(
            family_gate,
            membership,
            selected_gate,
            status=FamilyDecisionStatus.ACCEPTED,
            checker="tests/family-applicability-checker-v1",
            method="bounded_family_checkpoint_review",
            reason="family_context_applicable",
            rationale=(
                "This family statement includes the exact registered checkpoint."
            ),
        )
        report = build_family_risk_authorization_report(
            (family_gate, membership_gate),
            (applicability,),
            target=target,
        )
        replayed = FamilyRiskAuthorizationReport.from_dict(report.to_dict())

        self.assertEqual(report, replayed)
        self.assertEqual(1, len(report.authorizations))
        self.assertEqual(1, len(report.nexus_inputs))
        self.assertFalse(family_gate.projection_eligible)


if __name__ == "__main__":
    unittest.main()
