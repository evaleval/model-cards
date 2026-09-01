from __future__ import annotations

from dataclasses import replace
import unittest

from model_cards.artifact import CardArtifact, project_card
from model_cards.bindings import (
    build_artifact,
    quote_binding,
    resolve_json_pointer,
    source_from_dict,
    structured_binding,
    verify_artifact_sources,
)
from model_cards.models import (
    Disposition,
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from model_cards.quote import match_quote
from model_cards.schema import NOT_SPECIFIED
from tests.helpers import synthetic_artifact, synthetic_specification


class BindingPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.artifact = synthetic_artifact()

    def _one(self, field_path: str):
        matches = [item for item in self.artifact.bindings if item.field_path == field_path]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_exact_target_evidence_is_accepted(self) -> None:
        binding = self._one("evaluation.benchmark_scores[0]")
        self.assertEqual(binding.disposition, Disposition.ACCEPTED)
        self.assertTrue(binding.evidence[0].verified)
        card = project_card(self.artifact)
        self.assertEqual(card["evaluation"]["benchmark_scores"][0]["score"], 73.5)
        self.assertEqual(card["specifications"]["context_length"], "4096 tokens")

    def test_target_identity_values_must_match_the_artifact_target(self) -> None:
        cases = (
            ("model_id", "example-lab/another-model", "target_model_id_mismatch"),
            ("revision", "9999999999999999999999999999999999999999", "target_revision_mismatch"),
        )
        for source_key, wrong_value, reason in cases:
            with self.subTest(source_key=source_key):
                specification = synthetic_specification()
                specification["sources"][0]["data"][source_key] = wrong_value
                artifact = build_artifact(specification)
                field_path = "identity.model_id" if source_key == "model_id" else "identity.version"
                binding = next(item for item in artifact.bindings if item.field_path == field_path)
                self.assertEqual(binding.disposition, Disposition.REJECTED)
                self.assertEqual(binding.reason, reason)

    def test_hugging_face_source_revision_must_match_the_target(self) -> None:
        specification = synthetic_specification()
        specification["sources"][1]["source_revision"] = "0" * 40
        artifact = build_artifact(specification)
        binding = next(item for item in artifact.bindings if item.field_path == "identity.summary")
        self.assertEqual(binding.disposition, Disposition.REJECTED)
        self.assertEqual(binding.reason, "source_revision_mismatch")

    def test_developer_code_requires_a_resolved_commit(self) -> None:
        target = self.artifact.target
        for revision, expected, reason in (
            ("main", Disposition.REJECTED, "developer_code_revision_unresolved"),
            ("a" * 40, Disposition.ACCEPTED, "exact_target_supported"),
        ):
            with self.subTest(revision=revision):
                source = SourceDocument(
                    source_id="synthetic-developer-code",
                    role=SourceRole.DEVELOPER_CODE,
                    source_revision=revision,
                    target=target,
                    synthetic=True,
                    text="https://example.invalid/code",
                )
                binding = quote_binding(
                    target=target,
                    source=source,
                    field_path="links.code_repository",
                    value="https://example.invalid/code",
                    quote="https://example.invalid/code",
                    claim_entity=f"{target.model_id}@{target.revision}",
                    relation=RelationToTarget.EXACT_TARGET,
                )
                self.assertEqual(binding.disposition, expected)
                self.assertEqual(binding.reason, reason)

    def test_json_pointer_rejects_noncanonical_array_indexes(self) -> None:
        source = {"rows": ["first", "second"]}
        self.assertEqual(resolve_json_pointer(source, "/rows/1"), "second")
        for token in ("-1", "01", "+1", " 1"):
            with self.subTest(token=token):
                with self.assertRaises(ValueError):
                    resolve_json_pointer(source, f"/rows/{token}")
        with self.assertRaises(ValueError):
            resolve_json_pointer({"~2": "invalid"}, "/~2")

    def test_exact_target_claim_entity_must_match_target(self) -> None:
        specification = synthetic_specification()
        candidate = next(
            item for item in specification["candidates"] if item["field_path"] == "identity.name"
        )
        candidate["claim_entity"] = "example-lab/unrelated@" + "9" * 40
        binding = next(
            item for item in build_artifact(specification).bindings if item.field_path == "identity.name"
        )
        self.assertEqual(binding.disposition, Disposition.REJECTED)
        self.assertEqual(binding.reason, "claim_entity_target_mismatch")

    def test_base_claim_entity_must_match_the_base_row(self) -> None:
        specification = synthetic_specification()
        candidate = next(
            item
            for item in specification["candidates"]
            if item["field_path"] == "lineage.base_models[0]"
        )
        candidate["claim_entity"] = "example-lab/unrelated-base"
        binding = next(
            item
            for item in build_artifact(specification).bindings
            if item.field_path == "lineage.base_models[0]"
        )
        self.assertEqual(binding.disposition, Disposition.REJECTED)
        self.assertEqual(binding.reason, "base_claim_entity_mismatch")

    def test_comparison_claim_entity_must_match_the_link_row(self) -> None:
        specification = synthetic_specification()
        candidate = next(
            item
            for item in specification["candidates"]
            if item["field_path"] == "evaluation.related_model_scores[0]"
        )
        candidate["claim_entity"] = "example-lab/unrelated-comparison@" + "3" * 40
        binding = next(
            item
            for item in build_artifact(specification).bindings
            if item.field_path == "evaluation.related_model_scores[0]"
        )
        self.assertEqual(binding.disposition, Disposition.REJECTED)
        self.assertEqual(binding.reason, "related_claim_entity_mismatch")

    def test_comparison_source_target_must_match_the_link_row(self) -> None:
        specification = synthetic_specification()
        source = next(
            item
            for item in specification["sources"]
            if item["source_id"] == "synthetic-comparison-record"
        )
        source["target"] = {
            "model_id": "example-lab/unrelated-comparison",
            "revision": "3" * 40,
        }
        binding = next(
            item
            for item in build_artifact(specification).bindings
            if item.field_path == "evaluation.related_model_scores[0]"
        )
        self.assertEqual(binding.disposition, Disposition.REJECTED)
        self.assertEqual(binding.reason, "related_source_target_mismatch")

    def test_family_numeric_evidence_remains_visible_but_withheld(self) -> None:
        binding = self._one("training_context.training_data_size")
        self.assertEqual(binding.relation, RelationToTarget.MODEL_FAMILY)
        self.assertEqual(binding.disposition, Disposition.WITHHELD)
        self.assertEqual(binding.reason, "family_scope_not_target")
        self.assertTrue(binding.evidence[0].verified)
        self.assertEqual(
            project_card(self.artifact)["training_context"]["training_data_size"],
            NOT_SPECIFIED,
        )

    def test_non_exact_evidence_does_not_close_an_exact_target_gap(self) -> None:
        card = project_card(self.artifact)
        self.assertIn(
            "training_context.training_data_size",
            card["provenance_and_quality"]["missing_fields"],
        )
        flags = card["provenance_and_quality"]["flagged_fields"]
        self.assertIn("training_context.training_data_size", flags)

    def test_base_relation_only_populates_explicit_lineage(self) -> None:
        binding = self._one("lineage.base_models[0]")
        self.assertEqual(binding.disposition, Disposition.ACCEPTED)
        self.assertEqual(
            project_card(self.artifact)["lineage"]["base_models"],
            [{"model_id": "example-lab/synthetic-base-1b", "relation": "base"}],
        )

    def test_comparison_link_is_not_a_target_score(self) -> None:
        binding = self._one("evaluation.related_model_scores[0]")
        self.assertEqual(binding.disposition, Disposition.ACCEPTED)
        self.assertEqual(binding.relation, RelationToTarget.COMPARISON_MODEL)
        value = project_card(self.artifact)["evaluation"]["related_model_scores"][0]
        self.assertNotIn("score", value)

    def test_related_model_links_reject_scores_and_wrong_relations(self) -> None:
        target = self.artifact.target
        rows = (
            (
                {"model_id": "example-lab/other", "link": "https://example.invalid/other", "score": 7},
                RelationToTarget.COMPARISON_MODEL,
            ),
            (
                {"model_id": "example-lab/other", "link": "https://example.invalid/other", "accuracy": "73.5"},
                RelationToTarget.COMPARISON_MODEL,
            ),
            ({"model_id": "example-lab/other"}, RelationToTarget.COMPARISON_MODEL),
            (
                {"model_id": "example-lab/other", "link": "https://example.invalid/other"},
                RelationToTarget.EXACT_TARGET,
            ),
        )
        for index, (row, relation) in enumerate(rows):
            with self.subTest(index=index, relation=relation.value):
                source = SourceDocument(
                    source_id=f"synthetic-related-{index}",
                    role=SourceRole.EEE_INDEX,
                    source_revision="synthetic-index-v3",
                    target=target if relation is RelationToTarget.EXACT_TARGET else TargetIdentity(
                        "example-lab/other", "4" * 40
                    ),
                    synthetic=True,
                    data={"row": row},
                )
                binding = structured_binding(
                    target=target,
                    source=source,
                    field_path="evaluation.related_model_scores[0]",
                    pointer="/row",
                    claim_entity=(
                        f"{target.model_id}@{target.revision}"
                        if relation is RelationToTarget.EXACT_TARGET
                        else "example-lab/other@" + "4" * 40
                    ),
                    relation=relation,
                )
                self.assertEqual(binding.disposition, Disposition.WITHHELD)

    def test_eee_index_is_not_checkpoint_score_authority(self) -> None:
        target = self.artifact.target
        source = SourceDocument(
            source_id="synthetic-index-score",
            role=SourceRole.EEE_INDEX,
            source_revision="synthetic-index-v2",
            target=target,
            synthetic=True,
            text="Synthetic Model 1B has a reported Toy Score of 88.0 accuracy.",
        )
        binding = quote_binding(
            target=target,
            source=source,
            field_path="evaluation.benchmark_scores[1]",
            value={
                "benchmark": "Toy Score",
                "metric": "accuracy",
                "score": 88.0,
                "setting": "reported",
            },
            quote="Synthetic Model 1B has a reported Toy Score of 88.0 accuracy.",
            claim_entity=f"{target.model_id}@{target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
            benchmark_scope={
                "benchmark": "Toy Score",
                "metric": "accuracy",
                "setting": "reported",
            },
        )
        self.assertEqual(binding.disposition, Disposition.WITHHELD)
        self.assertEqual(binding.reason, "index_not_field_authority")

    def test_conflicting_accepted_values_leave_the_field_unfilled(self) -> None:
        specification = synthetic_specification()
        source = source_from_dict(specification["sources"][1])
        second = quote_binding(
            target=self.artifact.target,
            source=source,
            field_path="identity.summary",
            value="The exact checkpoint uses synthetic preference tuning.",
            quote="The exact checkpoint uses synthetic preference tuning.",
            claim_entity=f"{self.artifact.target.model_id}@{self.artifact.target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        conflicted = CardArtifact(
            target=self.artifact.target,
            bindings=self.artifact.bindings + (second,),
        )
        card = project_card(conflicted)
        self.assertEqual(card["identity"]["summary"], NOT_SPECIFIED)
        reasons = {
            item["reason"]
            for item in card["provenance_and_quality"]["flagged_fields"]["identity.summary"]
        }
        self.assertEqual(reasons, {"conflicting_accepted_values"})

    def test_exact_quote_verification_accepts_only_a_normalized_substring(self) -> None:
        match = match_quote("A model - with exact spacing.", "A  model — with exact spacing.")
        self.assertIsNotNone(match)
        self.assertEqual(match.quote, "A model - with exact spacing.")
        self.assertIsNone(match_quote("a model - with exact spacing.", "A model - with exact spacing."))

        specification = synthetic_specification()
        target = TargetIdentity.from_dict(specification["target"])
        source = source_from_dict(specification["sources"][1])
        binding = quote_binding(
            target=target,
            source=source,
            field_path="identity.summary",
            value="A paraphrased description",
            quote="This sentence does not occur in the source.",
            claim_entity=f"{target.model_id}@{target.revision}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        self.assertEqual(binding.disposition, Disposition.REJECTED)
        self.assertEqual(binding.reason, "quote_not_verified")
        self.assertFalse(binding.evidence[0].verified)

    def test_end_to_end_build_retains_a_rejected_quote_candidate(self) -> None:
        specification = synthetic_specification()
        specification["candidates"].append(
            {
                "kind": "quote",
                "source_id": "synthetic-model-page",
                "field_path": "links.system_card",
                "value": "https://example.invalid/system-card",
                "quote": "This link does not occur in the source.",
                "claim_entity": (
                    "example-lab/synthetic-model-1b@"
                    "1111111111111111111111111111111111111111"
                ),
                "relation": "exact_target",
            }
        )
        artifact = build_artifact(specification)
        binding = artifact.bindings[-1]
        self.assertEqual(binding.disposition, Disposition.REJECTED)
        self.assertEqual(binding.reason, "quote_not_verified")

    def test_replay_is_deterministic(self) -> None:
        first = synthetic_artifact().to_dict()
        second = synthetic_artifact().to_dict()
        self.assertEqual(first, second)

    def test_evidence_replays_against_separately_supplied_sources(self) -> None:
        specification = synthetic_specification()
        artifact = build_artifact(specification)
        sources = [source_from_dict(item) for item in specification["sources"]]
        verify_artifact_sources(artifact, sources)

        changed = synthetic_specification()
        changed["sources"][2]["text"] += " Changed."
        changed_sources = [source_from_dict(item) for item in changed["sources"]]
        with self.assertRaises(ValueError):
            verify_artifact_sources(artifact, changed_sources)

    def test_input_and_serialized_payloads_do_not_alias_the_artifact(self) -> None:
        specification = synthetic_specification()
        artifact = build_artifact(specification)
        before = artifact.to_dict()

        specification["sources"][0]["data"]["display_name"] = "Changed input"
        specification["candidates"][10]["value"]["score"] = 0
        exported = artifact.to_dict()
        exported["bindings"][10]["value"]["score"] = 1
        exported["card"]["evaluation"]["benchmark_scores"][0]["score"] = 2

        self.assertEqual(artifact.to_dict(), before)

    def test_direct_nested_mutation_is_detected_before_projection(self) -> None:
        artifact = synthetic_artifact()
        binding = next(
            item for item in artifact.bindings if item.field_path == "evaluation.benchmark_scores[0]"
        )
        binding.value["score"] = 99
        with self.assertRaises(ValueError):
            project_card(artifact)

    def test_caller_owned_binding_container_cannot_change_an_artifact(self) -> None:
        original = synthetic_artifact()
        caller_bindings = list(original.bindings)
        artifact = CardArtifact(target=original.target, bindings=caller_bindings)
        family = next(
            item
            for item in original.bindings
            if item.field_path == "training_context.training_data_size"
        )
        malicious = replace(
            family,
            disposition=Disposition.ACCEPTED,
            reason="exact_target_supported",
        )
        caller_bindings.append(malicious)
        self.assertEqual(len(artifact.bindings), len(original.bindings))
        self.assertEqual(
            project_card(artifact)["training_context"]["training_data_size"],
            NOT_SPECIFIED,
        )
        with self.assertRaises(ValueError):
            CardArtifact(target=original.target, bindings=original.bindings + (malicious,))


if __name__ == "__main__":
    unittest.main()
