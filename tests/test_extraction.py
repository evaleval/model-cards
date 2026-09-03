from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

from jsonschema import Draft202012Validator

from model_cards.claim_gate import (
    DecisionStatus,
    GateName,
    ProseCheckerDecision,
    evaluate_claim_gate,
)
from model_cards.extraction import (
    ExtractionBatch,
    ExtractionError,
    MAX_EXTRACTION_BATCH_PROPOSALS,
    MAX_PROVIDER_ENTITY_CHARS,
    MAX_PROVIDER_FIELD_PATH_CHARS,
    MAX_PROVIDER_PROPOSALS,
    MAX_PROVIDER_QUOTE_CHARS,
    MAX_PROVIDER_SCOPE_JSON_CHARS,
    MAX_PROVIDER_VALUE_JSON_CHARS,
    ProposalStatus,
    ProviderProposalRejection,
    QuoteProposal,
    build_source_windows,
    build_use_risk_windows,
    deterministic_publisher_context_candidates,
    deterministic_structured_candidates,
    extraction_response_schema,
    materialize_quote_batch,
    proposals_from_provider_value,
)
from model_cards.models import (
    RelationToTarget,
    SourceDocument,
    SourceRole,
    TargetIdentity,
)
from model_cards.quote import normalize_ws
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import build_source_document_catalog


REVISION = "a" * 40
README = """# Model Overview

The exact target is an instruction-following language model.

## Evaluation Results

The reported exact-target score is 73.5 on ExampleBench.

## Limitations

The model may produce incorrect answers in personalized assistant responses.

## Risks

Misinformation risk. The model may produce incorrect factual statements. This risk applies to the exact checkpoint.
"""

PUBLISHER_RISK_NAME = "Misinformation risk"
PUBLISHER_RISK_DESCRIPTION = "The model may produce incorrect factual statements."
PUBLISHER_RISK_RATIONALE = "This risk applies to the exact checkpoint."
PUBLISHER_RISK_QUOTE = (
    f"{PUBLISHER_RISK_NAME}. {PUBLISHER_RISK_DESCRIPTION} "
    f"{PUBLISHER_RISK_RATIONALE}"
)

OFFICIAL_CONTEXT = """---
license: custom
recommended_temperature: 0.6
---
# Exact Target System Card

## Intended Uses

The exact target is intended for customer-support assistants that draft responses for human review.

## Out-of-Scope Uses

Do not use the exact target to make autonomous medical decisions.

## Limitations

The exact target may produce inaccurate statements about rapidly changing events.

## Mitigations

Operators should verify model outputs because they may contain inaccurate factual claims.

## Generation Settings

Do not use the temperature parameter without setting top-p first.

## Recommendations

We recommend exploring README_WEIGHTS for additional checkpoints.

## License and Acceptable Use Policy

This model must not be used outside the license terms.

## Community

We recommend joining the developer community for deployment guidance.

## Limitations

### Language Ambiguity and Nuance

Language Ambiguity and Nuance.

## Base Model

### Intended Uses

The base model is intended for unrestricted text completion.

## Sibling Checkpoint

### Out-of-Scope Uses

Do not use acme/Instruct-Large for autonomous medical decisions.
"""


class Adapter:
    def resolve_revision(self, model_id, requested_revision):
        return REVISION

    def fetch_model_metadata(self, model_id, revision, *, max_bytes):
        return RemoteObject(
            FetchStatus.OK,
            json.dumps(
                {
                    "id": "acme/Instruct",
                    "sha": REVISION,
                    "pipeline_tag": "text-generation",
                    "config": {"model_type": "test", "torch_dtype": "float16"},
                    "siblings": [
                        {"rfilename": "README.md"},
                        {"rfilename": "config.json"},
                    ],
                },
                separators=(",", ":"),
                sort_keys=True,
            ).encode(),
        )

    def fetch_file(self, model_id, revision, repo_path, *, max_bytes):
        if repo_path == "README.md":
            return RemoteObject(FetchStatus.OK, README.encode())
        if repo_path == "config.json":
            return RemoteObject(
                FetchStatus.OK,
                b'{"model_type":"test","torch_dtype":"float16"}',
            )
        return RemoteObject(FetchStatus.MISSING, reason_code="not_found")


class ExtractionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "bundle"
        collect_hf_source_bundle("acme/Instruct", root, Adapter())
        self.catalog = build_source_document_catalog(replay_source_bundle(root))
        self.readme = next(
            item for item in self.catalog.documents if item.source_uri.endswith("/README.md")
        )

    def official_catalog(self, text: str = OFFICIAL_CONTEXT):
        source = replace(
            self.readme,
            source_id="official_report",
            source_uri=(
                f"https://huggingface.co/{self.catalog.target.model_id}/resolve/"
                f"{REVISION}/README.md"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
            text=text,
            content_sha256=None,
        )
        return SimpleNamespace(
            target=self.catalog.target,
            catalog_sha256="c" * 64,
            documents=(source,),
            by_id={source.source_id: source},
        )

    def test_deterministic_context_rejects_unbound_developer_report(self) -> None:
        catalog = self.official_catalog()
        source = replace(
            catalog.documents[0],
            role=SourceRole.DEVELOPER_REPORT,
            source_uri="https://example.com/acme/instruct/system-card",
            content_sha256=None,
        )
        report_catalog = SimpleNamespace(
            target=catalog.target,
            catalog_sha256="a" * 64,
            documents=(source,),
            by_id={source.source_id: source},
        )

        self.assertEqual(
            (),
            deterministic_publisher_context_candidates(report_catalog).candidates,
        )

    def proposal(self, **changes) -> QuoteProposal:
        values = {
            "source_id": self.readme.source_id,
            "field_path": "identity.summary",
            "value": "The exact target is an instruction-following language model.",
            "quote": "The exact target is an instruction-following language model.",
            "claim_entity": f"acme/Instruct@{REVISION}",
            "relation": RelationToTarget.EXACT_TARGET,
            "benchmark_scope": None,
            "origin": "source_stated",
        }
        values.update(changes)
        return QuoteProposal(**values)

    def batch(self, *proposals: QuoteProposal) -> ExtractionBatch:
        return ExtractionBatch.build(
            target=self.catalog.target,
            source_catalog_sha256=self.catalog.catalog_sha256,
            provider="Together",
            inference_config_sha256="b" * 64,
            proposals=proposals,
        )

    @staticmethod
    def checker(candidate, gate):
        return ProseCheckerDecision.for_candidate(
            candidate,
            gate=gate,
            checker="deepseek/deepseek-v4-flash-0731",
            method="strict_schema_semantic_check",
            status=DecisionStatus.ACCEPTED,
            reason="semantic_check_supported",
        )

    def accepting_checks(self, candidate):
        return tuple(
            self.checker(candidate, gate)
            for gate in (
                GateName.ENTITY_SCOPE,
                GateName.FIELD_FIT,
                GateName.VALUE_SUPPORT,
            )
        )

    def test_bounded_windows_are_deterministic_and_ephemeral(self) -> None:
        windows = build_source_windows(self.readme, window_chars=500, overlap=50)
        self.assertEqual(1, len(windows))
        self.assertLessEqual(len(windows[0].excerpt), 500)
        self.assertEqual(windows, build_source_windows(self.readme, window_chars=500, overlap=50))
        self.assertEqual(windows, build_use_risk_windows(self.readme, windows=windows))
        self.assertFalse(hasattr(windows[0], "to_dict"))
        self.assertNotIn("/Users/", repr(windows[0]))
        with self.assertRaises(ExtractionError):
            build_source_windows(self.readme, window_chars=100, overlap=0)

        blank_sources = (
            replace(
                self.readme,
                source_id="blank_source_a",
                text=" ",
                content_sha256=None,
            ),
            replace(
                self.readme,
                source_id="blank_source_b",
                text="\n",
                content_sha256=None,
            ),
        )
        self.assertNotEqual(blank_sources[0].sha256, blank_sources[1].sha256)
        for source in blank_sources:
            with self.subTest(source_id=source.source_id), self.assertRaisesRegex(
                ExtractionError, "no normalized text"
            ):
                build_source_windows(source)

    def test_quote_materialization_recomputes_coordinates_and_section_context(self) -> None:
        proposal = self.proposal()
        result = materialize_quote_batch(self.batch(proposal), self.catalog)
        self.assertEqual(1, len(result.candidates))
        candidate = result.candidates[0]
        evidence = candidate.evidence[0]
        self.assertTrue(evidence.verified)
        self.assertEqual(("Model Overview",), evidence.section_path)
        self.assertEqual(ProposalStatus.MATERIALIZED, result.outcomes[0].status)
        decisions = self.accepting_checks(candidate)
        gate = evaluate_claim_gate(candidate, self.catalog.documents, decisions)
        self.assertTrue(gate.projection_eligible)

    def test_same_readme_sibling_quote_requires_independent_entity_attribution(self) -> None:
        catalog = self.official_catalog()
        source = catalog.documents[0]
        quote = "Do not use acme/Instruct-Large for autonomous medical decisions."
        proposal = self.proposal(
            source_id=source.source_id,
            field_path="use_and_risk.out_of_scope_uses[0]",
            value=quote,
            quote=quote,
            # Adversarial extractor output: the source is the target README, but
            # both the quote and its enclosing section concern a sibling.
            claim_entity=f"acme/Instruct@{REVISION}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        candidate = materialize_quote_batch(
            ExtractionBatch.build(
                target=catalog.target,
                source_catalog_sha256=catalog.catalog_sha256,
                provider="Together",
                inference_config_sha256="b" * 64,
                proposals=(proposal,),
            ),
            catalog,
        ).candidates[0]
        self.assertEqual(
            (
                "Exact Target System Card",
                "Sibling Checkpoint",
                "Out-of-Scope Uses",
            ),
            candidate.evidence[0].section_path,
        )

        gate = evaluate_claim_gate(
            candidate,
            catalog.documents,
            (
                ProseCheckerDecision.for_candidate(
                    candidate,
                    gate=GateName.ENTITY_SCOPE,
                    checker="deepseek/deepseek-v4-flash-0731",
                    method="bounded_openrouter_entity_scope",
                    status=DecisionStatus.WITHHELD,
                    reason="wrong_entity",
                ),
                self.checker(candidate, GateName.FIELD_FIT),
                self.checker(candidate, GateName.VALUE_SUPPORT),
            ),
        )

        self.assertFalse(gate.projection_eligible)
        self.assertEqual(
            "wrong_entity",
            next(
                item
                for item in gate.decisions
                if item.gate is GateName.ENTITY_SCOPE
            ).reason,
        )

    def test_publisher_context_wrapper_is_constructed_locally_not_by_provider(self) -> None:
        description = (
            "The model may produce incorrect answers in personalized assistant responses."
        )
        proposal = self.proposal(
            field_path="use_and_risk.limitations[0]",
            value=description,
            quote=description,
        )
        candidate = materialize_quote_batch(self.batch(proposal), self.catalog).candidates[0]
        self.assertEqual(description, candidate.value["description"])
        self.assertEqual("publisher_reported", candidate.value["origin"])
        self.assertEqual([self.readme.source_id], candidate.value["source_refs"])
        self.assertTrue(candidate.value["context_id"].startswith("context:"))
        self.assertNotIn(candidate.value["context_id"], README)
        self.assertEqual(
            ("Model Overview", "Limitations"), candidate.evidence[0].section_path
        )
        gate = evaluate_claim_gate(
            candidate,
            self.catalog.documents,
            self.accepting_checks(candidate),
        )
        self.assertTrue(gate.projection_eligible)
        with self.assertRaisesRegex(ExtractionError, "item index"):
            self.proposal(field_path="use_and_risk.limitations", value=description)

        with self.assertRaisesRegex(ExtractionError, "publisher-stated"):
            self.proposal(
                field_path="use_and_risk.mitigations[0]",
                value="The publisher recommends human review.",
                quote="The publisher recommends human review.",
                origin="source_derived",
            )

    def test_publisher_risk_wrapper_is_constructed_locally_and_gate_accepts(self) -> None:
        proposal_value = {
            "name": PUBLISHER_RISK_NAME,
            "description": PUBLISHER_RISK_DESCRIPTION,
            "applicability_rationale": PUBLISHER_RISK_RATIONALE,
        }
        proposal = self.proposal(
            field_path="use_and_risk.identified_risks[0]",
            value=proposal_value,
            quote=PUBLISHER_RISK_QUOTE,
        )
        candidate = materialize_quote_batch(
            self.batch(proposal), self.catalog
        ).candidates[0]
        self.assertEqual("publisher_reported", candidate.value["identification_origin"])
        self.assertIsNone(candidate.value["taxonomy"])
        self.assertTrue(candidate.value["risk_id"].startswith("publisher-risk:"))
        self.assertEqual([self.readme.source_id], candidate.value["source_refs"])
        self.assertEqual("source_binding", candidate.value["mapping_provenance"]["method"])
        self.assertEqual("generated_unreviewed", candidate.value["review_status"])
        self.assertNotIn("risk_id", proposal.value)
        self.assertNotIn(candidate.value["risk_id"], README)
        gate = evaluate_claim_gate(
            candidate,
            self.catalog.documents,
            self.accepting_checks(candidate),
        )
        self.assertTrue(gate.projection_eligible)

        with self.assertRaisesRegex(ExtractionError, "closed shape"):
            self.proposal(
                field_path="use_and_risk.identified_risks[0]",
                value={**proposal_value, "risk_id": "provider-invented"},
                quote=PUBLISHER_RISK_QUOTE,
            )
        with self.assertRaisesRegex(ExtractionError, "publisher-stated"):
            self.proposal(
                field_path="use_and_risk.identified_risks[0]",
                value=proposal_value,
                quote=PUBLISHER_RISK_QUOTE,
                origin="source_derived",
            )

    def test_supported_quote_cannot_cover_a_different_numeric_value(self) -> None:
        proposal = self.proposal(
            field_path="evaluation.results_summary",
            value="The reported exact-target score is 99.0 on ExampleBench.",
            quote="The reported exact-target score is 73.5 on ExampleBench.",
        )
        candidate = materialize_quote_batch(self.batch(proposal), self.catalog).candidates[0]
        gate = evaluate_claim_gate(
            candidate,
            self.catalog.documents,
            self.accepting_checks(candidate),
        )
        self.assertFalse(gate.projection_eligible)
        self.assertEqual(
            "complete_value_not_in_evidence",
            next(item for item in gate.decisions if item.gate is GateName.VALUE_SUPPORT).reason,
        )

    def test_nonmatching_quote_remains_an_immutable_candidate_for_gate_withholding(self) -> None:
        proposal = self.proposal(quote="A paraphrase absent from the frozen source.")
        candidate = materialize_quote_batch(self.batch(proposal), self.catalog).candidates[0]
        self.assertFalse(candidate.evidence[0].verified)
        gate = evaluate_claim_gate(
            candidate,
            self.catalog.documents,
            self.accepting_checks(candidate),
        )
        coordinate = next(
            item for item in gate.decisions if item.gate is GateName.COORDINATE_INTEGRITY
        )
        self.assertEqual(DecisionStatus.WITHHELD, coordinate.status)
        self.assertEqual("quote_coordinates_unverified", coordinate.reason)

    def test_unavailable_or_structured_source_proposal_is_visible_not_materialized(self) -> None:
        missing = self.proposal(source_id="src_" + "f" * 24)
        structured_source = next(item for item in self.catalog.documents if item.data is not None)
        wrong_kind = self.proposal(source_id=structured_source.source_id)
        result = materialize_quote_batch(self.batch(missing, wrong_kind), self.catalog)
        self.assertEqual((), result.candidates)
        self.assertEqual(
            {ProposalStatus.SOURCE_UNAVAILABLE, ProposalStatus.SOURCE_KIND_MISMATCH},
            {item.status for item in result.outcomes},
        )

    def test_closed_registry_discovers_replayable_structured_candidates(self) -> None:
        result = deterministic_structured_candidates(self.catalog)
        fields = {item.field_path for item in result.candidates}
        self.assertTrue(
            {
                "identity.model_id",
                "identity.revision",
                "identity.model_type",
                "model_details.architecture_type",
                "model_details.precision",
            }
            <= fields
        )
        for candidate in result.candidates:
            gate = evaluate_claim_gate(candidate, self.catalog.documents)
            self.assertTrue(gate.projection_eligible, candidate.field_path)

    def test_deterministic_official_context_is_exact_scoped_and_gate_eligible(self) -> None:
        catalog = self.official_catalog()
        result = deterministic_publisher_context_candidates(catalog)
        by_field = {item.field_path: item for item in result.candidates}
        self.assertEqual(
            {
                "use_and_risk.intended_uses[0]",
                "use_and_risk.out_of_scope_uses[0]",
                "use_and_risk.limitations[0]",
                "use_and_risk.mitigations[0]",
            },
            set(by_field),
        )
        serialized = json.dumps([item.to_dict() for item in result.candidates])
        for denied in (
            "recommended_temperature",
            "temperature parameter",
            "README_WEIGHTS",
            "license terms",
            "developer community",
            "Language Ambiguity and Nuance",
            "unrestricted text completion",
            "Instruct-Large",
        ):
            self.assertNotIn(denied, serialized)
        self.assertNotIn("identified_risks", serialized)
        normalized_source = normalize_ws(catalog.documents[0].text)
        for candidate in result.candidates:
            evidence = candidate.evidence[0]
            description = candidate.value["description"]
            self.assertEqual(RelationToTarget.EXACT_TARGET, candidate.relation)
            self.assertTrue(evidence.verified)
            self.assertEqual(
                evidence.quote,
                normalized_source[evidence.char_start : evidence.char_end],
            )
            self.assertEqual(description, evidence.quote)
            gate = evaluate_claim_gate(
                candidate,
                catalog.documents,
                self.accepting_checks(candidate),
            )
            self.assertTrue(gate.projection_eligible, candidate.field_path)

    def test_mixed_llama_use_sentence_is_split_by_exact_checkpoint_stage(self) -> None:
        mixed = (
            "Instruction tuned text only models are intended for assistant-like "
            "chat, whereas pretrained models can be adapted for a variety of "
            "natural language generation tasks."
        )
        source_text = (
            f"# Model Card\n\n## Intended Use\n\n"
            f"**Intended Use Cases** {mixed}\n"
        )
        expected = {
            "meta-llama/Llama-3.1-8B": (
                "pretrained models can be adapted for a variety of natural "
                "language generation tasks."
            ),
            "meta-llama/Llama-3.1-8B-Instruct": (
                "Instruction tuned text only models are intended for "
                "assistant-like chat"
            ),
        }
        for model_id, clause in expected.items():
            with self.subTest(model_id=model_id):
                target = TargetIdentity(model_id, REVISION)
                source = replace(
                    self.readme,
                    source_id="llama_publisher_readme",
                    source_uri=(
                        f"https://huggingface.co/{model_id}/resolve/"
                        f"{REVISION}/README.md"
                    ),
                    role=SourceRole.HUGGING_FACE_SNAPSHOT,
                    target=target,
                    text=source_text,
                    content_sha256=None,
                )
                catalog = SimpleNamespace(
                    target=target,
                    catalog_sha256=hashlib.sha256(
                        model_id.encode("utf-8")
                    ).hexdigest(),
                    documents=(source,),
                    by_id={source.source_id: source},
                )
                result = deterministic_publisher_context_candidates(catalog)
                self.assertEqual(1, len(result.candidates))
                candidate = result.candidates[0]
                self.assertEqual(
                    "use_and_risk.intended_uses[0]", candidate.field_path
                )
                self.assertEqual(clause, candidate.value["description"])
                self.assertEqual(clause, candidate.evidence[0].quote)
                self.assertTrue(candidate.evidence[0].verified)
                self.assertNotEqual(mixed, candidate.value["description"])

        unrelated = TargetIdentity("meta-llama/Llama-3.1-8B-Instruct", REVISION)
        source = replace(
            self.readme,
            source_id="unrelated_publisher_readme",
            source_uri="https://example.com/acme/model-card",
            role=SourceRole.DEVELOPER_REPORT,
            target=unrelated,
            text=source_text,
            content_sha256=None,
        )
        catalog = SimpleNamespace(
            target=unrelated,
            catalog_sha256="e" * 64,
            documents=(source,),
            by_id={source.source_id: source},
        )
        self.assertEqual(
            (), deterministic_publisher_context_candidates(catalog).candidates
        )

        for model_id in (
            "meta-llama/Llama-3.1-999B",
            "meta-llama/Llama-3.1-999B-Instruct",
            "meta-llama/Llama-3.1-8.5B-Instruct",
        ):
            with self.subTest(unregistered_model_id=model_id):
                target = TargetIdentity(model_id, REVISION)
                unregistered_source = replace(
                    source,
                    source_id="unregistered_llama_readme",
                    source_uri=(
                        f"https://huggingface.co/{model_id}/resolve/"
                        f"{REVISION}/README.md"
                    ),
                    role=SourceRole.HUGGING_FACE_SNAPSHOT,
                    target=target,
                    content_sha256=None,
                )
                unregistered_catalog = SimpleNamespace(
                    target=target,
                    catalog_sha256=hashlib.sha256(model_id.encode()).hexdigest(),
                    documents=(unregistered_source,),
                    by_id={unregistered_source.source_id: unregistered_source},
                )
                self.assertEqual(
                    (),
                    deterministic_publisher_context_candidates(
                        unregistered_catalog
                    ).candidates,
                )

        wrong_host = replace(
            source,
            source_id="wrong_host_publisher_readme",
            source_uri=(
                f"https://unrelated.example/{unrelated.model_id}/resolve/"
                f"{REVISION}/README.md"
            ),
            role=SourceRole.HUGGING_FACE_SNAPSHOT,
        )
        catalog = SimpleNamespace(
            target=unrelated,
            catalog_sha256="f" * 64,
            documents=(wrong_host,),
            by_id={wrong_host.source_id: wrong_host},
        )
        self.assertEqual(
            (), deterministic_publisher_context_candidates(catalog).candidates
        )

    def test_deterministic_context_rejects_sentence_initial_pronouns(self) -> None:
        ambiguous = self.official_catalog(
            "# System Card\n\n## Limitations\n\n"
            "The benchmark contains English prompts. "
            "It may not represent other languages.\n"
        )
        self.assertEqual(
            (),
            deterministic_publisher_context_candidates(ambiguous).candidates,
        )

        superficially_grounded = self.official_catalog(
            "# System Card\n\n## Limitations\n\n"
            "Models generate responses from learned statistical patterns. "
            "They may generate incorrect factual statements.\n"
        )
        self.assertEqual(
            (),
            deterministic_publisher_context_candidates(
                superficially_grounded
            ).candidates,
        )

        non_initial = self.official_catalog(
            "# System Card\n\n## Limitations\n\n"
            "During deployment, it may produce incorrect factual statements.\n"
        )
        self.assertEqual(
            (),
            deterministic_publisher_context_candidates(non_initial).candidates,
        )

    def test_deterministic_context_rejects_unknown_nested_entity_heading(self) -> None:
        for heading in ("Falcon", "OtherModel", "Example-Base"):
            with self.subTest(heading=heading):
                catalog = self.official_catalog(
                    "# System Card\n\n## Limitations\n\n"
                    f"### {heading}\n\n"
                    "The model may produce incorrect factual statements.\n"
                )
                self.assertEqual(
                    (),
                    deterministic_publisher_context_candidates(catalog).candidates,
                )

    def test_deterministic_mitigation_requires_explicit_target_reference(self) -> None:
        unrelated_outputs = self.official_catalog(
            "# System Card\n\n## Mitigations\n\n"
            "Operators should verify benchmark outputs because they may be inaccurate. "
            "Operators should review dataset outputs because they may contain sensitive data.\n"
        )
        self.assertEqual(
            (),
            deterministic_publisher_context_candidates(unrelated_outputs).candidates,
        )

        explicit_target = self.official_catalog(
            "# System Card\n\n## Mitigations\n\n"
            "Operators should verify this model's outputs because they may be inaccurate.\n"
        )
        candidates = deterministic_publisher_context_candidates(
            explicit_target
        ).candidates
        self.assertEqual(1, len(candidates))
        self.assertEqual("use_and_risk.mitigations[0]", candidates[0].field_path)

    def test_deterministic_context_uses_only_root_hub_readme_and_preserves_provider_field(self) -> None:
        hub_context = deterministic_publisher_context_candidates(self.catalog)
        self.assertTrue(hub_context.candidates)
        self.assertEqual(
            {"use_and_risk.limitations"},
            {
                item.field_path.rsplit("[", 1)[0]
                for item in hub_context.candidates
            },
        )
        self.assertTrue(
            all(
                item.evidence[0].source_role is SourceRole.HUGGING_FACE_SNAPSHOT
                for item in hub_context.candidates
            )
        )
        other_snapshot = replace(
            self.readme,
            source_id="declared_safety",
            source_uri=self.readme.source_uri.removesuffix("README.md") + "SAFETY.md",
            text=(
                "# Intended Uses\n\nThe exact target is intended for autonomous "
                "decision making in high-impact settings.\n"
            ),
            content_sha256=None,
        )
        other_catalog = SimpleNamespace(
            target=self.catalog.target,
            catalog_sha256="d" * 64,
            documents=(other_snapshot,),
            by_id={other_snapshot.source_id: other_snapshot},
        )
        self.assertEqual(
            (),
            deterministic_publisher_context_candidates(other_catalog).candidates,
        )

        catalog = self.official_catalog()
        intended = (
            "The exact target is intended for customer-support assistants that "
            "draft responses for human review."
        )
        provider = QuoteProposal(
            source_id=catalog.documents[0].source_id,
            field_path="use_and_risk.intended_uses[0]",
            value=intended,
            quote=intended,
            claim_entity=f"acme/Instruct@{REVISION}",
            relation=RelationToTarget.EXACT_TARGET,
        )
        batch = ExtractionBatch.build(
            target=catalog.target,
            source_catalog_sha256=catalog.catalog_sha256,
            provider="Together",
            inference_config_sha256="b" * 64,
            proposals=(provider,),
        )
        provider_candidate = materialize_quote_batch(batch, catalog).candidates[0]
        unaccepted_gate = evaluate_claim_gate(
            provider_candidate,
            catalog.documents,
            (),
        )
        deterministic = deterministic_publisher_context_candidates(
            catalog, existing_gate_records=(unaccepted_gate,)
        )
        self.assertIn(
            "use_and_risk.intended_uses",
            {item.field_path.rsplit("[", 1)[0] for item in deterministic.candidates},
        )

        accepted_gate = evaluate_claim_gate(
            provider_candidate,
            catalog.documents,
            self.accepting_checks(provider_candidate),
        )
        self.assertTrue(accepted_gate.projection_eligible)
        deterministic = deterministic_publisher_context_candidates(
            catalog, existing_gate_records=(accepted_gate,)
        )
        self.assertNotIn(
            "use_and_risk.intended_uses",
            {item.field_path.rsplit("[", 1)[0] for item in deterministic.candidates},
        )
        self.assertEqual(
            {
                "use_and_risk.out_of_scope_uses[0]",
                "use_and_risk.limitations[0]",
                "use_and_risk.mitigations[0]",
            },
            {item.field_path for item in deterministic.candidates},
        )

    def test_frozen_pilot_context_allowlist_is_precision_locked(self) -> None:
        pilot = (
            Path(__file__).resolve().parents[2]
            / "model-card-system"
            / "pilot"
        )
        roster_path = pilot / "roster12" / "targets.txt"
        bundle_root = pilot / "bundles"
        if not roster_path.is_file() or not bundle_root.is_dir():
            self.skipTest("the frozen 12-target pilot corpus is not available")

        llama_values = {
            (
                "use_and_risk.intended_uses[0]",
                "Llama 3.1 is intended for commercial and research use in multiple languages.",
            ),
            (
                "use_and_risk.out_of_scope_uses[0]",
                "Use in any manner that violates applicable laws or regulations (including trade compliance laws).",
            ),
            (
                "use_and_risk.out_of_scope_uses[1]",
                "Use in any other way that is prohibited by the Acceptable Use Policy and Llama 3.1 Community License.",
            ),
            (
                "use_and_risk.out_of_scope_uses[2]",
                "Use in languages beyond those explicitly referenced as supported in this model card**.",
            ),
        }
        expected = {
            "meta-llama/Llama-3.1-8B": llama_values
            | {
                (
                    "use_and_risk.intended_uses[1]",
                    "pretrained models can be adapted for a variety of natural "
                    "language generation tasks.",
                )
            },
            "meta-llama/Llama-3.1-8B-Instruct": llama_values
            | {
                (
                    "use_and_risk.intended_uses[1]",
                    "Instruction tuned text only models are intended for "
                    "assistant-like chat",
                )
            },
        }
        observed: dict[str, set[tuple[str, str]]] = {}
        serialized_candidates: list[str] = []
        roster = tuple(
            line.strip()
            for line in roster_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        self.assertEqual(12, len(roster))
        for entry in roster:
            model_id, revision = entry.rsplit("@", 1)
            prefix = model_id.casefold().replace("/", "-")
            matches = tuple(
                path
                for path in bundle_root.iterdir()
                if path.is_dir()
                and path.name.startswith(prefix)
                and path.name.endswith(revision[:12])
            )
            self.assertEqual(1, len(matches), entry)
            bundle = json.loads(
                (
                    matches[0] / "source_bundle" / "source-bundle.json"
                ).read_text(encoding="utf-8")
            )
            readme = next(
                item for item in bundle["files"] if item["name"] == "README.md"
            )
            self.assertEqual(
                readme["sha256"],
                hashlib.sha256(readme["content"].encode("utf-8")).hexdigest(),
            )
            target = TargetIdentity(model_id, revision)
            source = SourceDocument(
                source_id="pilot_readme",
                source_uri=readme["source_uri"],
                role=SourceRole.HUGGING_FACE_SNAPSHOT,
                source_revision=revision,
                target=target,
                text=readme["content"],
                content_sha256=readme["sha256"],
            )
            catalog = SimpleNamespace(
                target=target,
                catalog_sha256=hashlib.sha256(entry.encode("utf-8")).hexdigest(),
                documents=(source,),
                by_id={source.source_id: source},
            )
            result = deterministic_publisher_context_candidates(catalog)
            values = {
                (item.field_path, item.value["description"])
                for item in result.candidates
            }
            observed[model_id] = values
            serialized_candidates.extend(
                json.dumps(item.to_dict(), sort_keys=True)
                for item in result.candidates
            )

        self.assertEqual(expected, {key: value for key, value in observed.items() if value})
        self.assertEqual(10, sum(len(value) for value in observed.values()))
        joined = "\n".join(serialized_candidates)
        for denied in (
            "greedy decoding",
            "README_WEIGHTS",
            "Language Ambiguity and Nuance",
            "looking forward to engaging with the community",
            "whereas pretrained models",
        ):
            self.assertNotIn(denied, joined)

    def test_provider_value_boundary_uses_json_strings_and_rejects_duplicates(self) -> None:
        raw = {
            "proposals": [
                {
                    "source_id": self.readme.source_id,
                    "field_path": "evaluation.benchmark_scores[0]",
                    "value_json": json.dumps(
                        {
                            "benchmark": "ExampleBench",
                            "metric": "accuracy",
                            "score": 73.5,
                            "setting": "zero-shot",
                        }
                    ),
                    "quote": "The reported exact-target score is 73.5 on ExampleBench.",
                    "claim_entity": f"acme/Instruct@{REVISION}",
                    "relation": "exact_target",
                    "origin": "source_stated",
                }
            ]
        }
        proposal = proposals_from_provider_value(raw)[0]
        self.assertEqual(73.5, proposal.value["score"])
        self.assertEqual(
            {
                "benchmark": "ExampleBench",
                "metric": "accuracy",
                "setting": "zero-shot",
            },
            proposal.benchmark_scope,
        )
        bad = json.loads(json.dumps(raw))
        bad["proposals"][0]["value_json"] = '{"score":73.5,"score":99.0}'
        with self.assertRaisesRegex(ExtractionError, "invalid canonical JSON"):
            proposals_from_provider_value(bad)
        schema = extraction_response_schema()
        self.assertTrue(schema["strict"])
        self.assertFalse(schema["schema"]["additionalProperties"])
        self.assertEqual(
            MAX_PROVIDER_PROPOSALS,
            schema["schema"]["properties"]["proposals"]["maxItems"],
        )
        self.assertEqual(8, MAX_PROVIDER_PROPOSALS)
        item_schema = schema["schema"]["properties"]["proposals"]["items"]
        self.assertFalse(item_schema["additionalProperties"])
        properties = item_schema["properties"]
        self.assertEqual(128, properties["source_id"]["maxLength"])
        self.assertEqual(
            MAX_PROVIDER_FIELD_PATH_CHARS,
            properties["field_path"]["maxLength"],
        )
        self.assertEqual(
            MAX_PROVIDER_VALUE_JSON_CHARS,
            properties["value_json"]["maxLength"],
        )
        self.assertEqual(MAX_PROVIDER_QUOTE_CHARS, properties["quote"]["maxLength"])
        self.assertEqual(
            MAX_PROVIDER_ENTITY_CHARS,
            properties["claim_entity"]["maxLength"],
        )
        self.assertNotIn("benchmark_scope_json", properties)

        wrong_parameter_type = json.loads(json.dumps(raw))
        wrong_parameter_type["proposals"][0].update(
            {
                "field_path": "model_details.num_parameters",
                "value_json": "7",
                "quote": "The model has 7B parameters.",
            }
        )
        with self.assertRaisesRegex(
            ValueError, "model_details.num_parameters violates"
        ):
            proposals_from_provider_value(wrong_parameter_type)

        unindexed_list = json.loads(json.dumps(raw))
        unindexed_list["proposals"][0].update(
            {
                "field_path": "model_details.modalities",
                "value_json": '["text"]',
                "quote": "Modalities: text.",
            }
        )
        with self.assertRaisesRegex(ExtractionError, "item index"):
            proposals_from_provider_value(unindexed_list)
        self.assertTrue(
            list(
                Draft202012Validator(schema["schema"]).iter_errors(unindexed_list)
            )
        )

        too_many = {"proposals": raw["proposals"] * (MAX_PROVIDER_PROPOSALS + 1)}
        with self.assertRaisesRegex(ExtractionError, "proposal count"):
            proposals_from_provider_value(too_many)

    def test_provider_scalar_recovery_matches_the_live_together_shape(self) -> None:
        raw = {
            "proposals": [
                {
                    "source_id": self.readme.source_id,
                    "field_path": "identity.summary",
                    "value_json": (
                        "The exact target is an instruction-following language model."
                    ),
                    "quote": (
                        "The exact target is an instruction-following language model."
                    ),
                    "claim_entity": f"acme/Instruct@{REVISION}",
                    "relation": "exact_target",
                    "origin": "source_stated",
                }
            ]
        }
        proposal = proposals_from_provider_value(raw)[0]
        self.assertEqual(raw["proposals"][0]["value_json"], proposal.value)
        self.assertIsNone(proposal.benchmark_scope)

        raw["proposals"][0]["field_path"] = "evaluation.benchmark_scores[0]"
        with self.assertRaisesRegex(ExtractionError, "invalid canonical JSON"):
            proposals_from_provider_value(raw)

    def test_provider_raw_use_risk_prose_is_typed_and_structured_lists_fail_closed(self) -> None:
        raw = {
            "proposals": [
                {
                    "source_id": self.readme.source_id,
                    "field_path": "use_and_risk.limitations[0]",
                    "value_json": "May produce inaccurate factual statements.",
                    "quote": "May produce inaccurate factual statements.",
                    "claim_entity": f"acme/Instruct@{REVISION}",
                    "relation": "exact_target",
                    "origin": "source_stated",
                }
            ]
        }
        proposal = proposals_from_provider_value(raw)[0]
        self.assertEqual(raw["proposals"][0]["value_json"], proposal.value)
        raw["proposals"][0]["field_path"] = "model_details.modalities[0]"
        with self.assertRaisesRegex(ExtractionError, "invalid canonical JSON"):
            proposals_from_provider_value(raw)

    def test_persisted_quote_batches_enforce_provider_bounds_and_absence_rules(self) -> None:
        cases = (
            {"source_id": "s" * 129},
            {"quote": "q" * (MAX_PROVIDER_QUOTE_CHARS + 1)},
            {"claim_entity": "e" * (MAX_PROVIDER_ENTITY_CHARS + 1)},
            {"value": "v" * MAX_PROVIDER_VALUE_JSON_CHARS},
            {"benchmark_scope": {"detail": "s" * MAX_PROVIDER_SCOPE_JSON_CHARS}},
            {"value": "Not specified"},
            {"value": "Not applicable"},
        )
        for changes in cases:
            with self.subTest(changes=tuple(changes)), self.assertRaises(ExtractionError):
                self.proposal(**changes)

        prefix = "model_details.modalities["
        exact_path = (
            prefix
            + "1" * (MAX_PROVIDER_FIELD_PATH_CHARS - len(prefix) - 1)
            + "]"
        )
        self.assertEqual(MAX_PROVIDER_FIELD_PATH_CHARS, len(exact_path))
        self.proposal(field_path=exact_path, value="text", quote="text")
        with self.assertRaisesRegex(ExtractionError, "field_path exceeds"):
            self.proposal(
                field_path=exact_path[:-1] + "1]",
                value="text",
                quote="text",
            )

        with self.assertRaisesRegex(ExtractionError, "scope must be an object"):
            self.proposal(benchmark_scope=[])

        proposals = tuple(
            self.proposal(value=f"value-{index}", quote=f"quote-{index}")
            for index in range(MAX_EXTRACTION_BATCH_PROPOSALS + 1)
        )
        with self.assertRaisesRegex(ExtractionError, "proposal bound"):
            self.batch(*proposals)

    def test_batch_round_trip_is_content_addressed_and_contains_no_source_body(self) -> None:
        batch = self.batch(self.proposal())
        restored = ExtractionBatch.from_dict(batch.to_dict())
        self.assertEqual(batch, restored)
        serialized = json.dumps(batch.to_dict())
        self.assertNotIn("The reported exact-target score", serialized)
        self.assertNotIn("provider response", serialized.casefold())
        padded = batch.to_dict()
        padded["proposals"][0]["quote"] = " " * MAX_PROVIDER_QUOTE_CHARS + "x"
        with self.assertRaisesRegex(ExtractionError, "quote"):
            ExtractionBatch.from_dict(padded)
        invalid_scope = batch.to_dict()
        invalid_scope["proposals"][0]["benchmark_scope"] = []
        with self.assertRaisesRegex(ExtractionError, "scope must be an object"):
            ExtractionBatch.from_dict(invalid_scope)
        with self.assertRaises(ExtractionError):
            replace(batch, source_catalog_sha256="0" * 64)

    def test_rejection_indexes_are_bounded_by_the_original_item_count(self) -> None:
        proposal = self.proposal()
        rejection = ProviderProposalRejection(
            proposal_index=1,
            proposal_sha256="c" * 64,
            reason="proposal_contract_invalid",
        )
        batch = ExtractionBatch.build(
            target=self.catalog.target,
            source_catalog_sha256=self.catalog.catalog_sha256,
            provider="Together",
            inference_config_sha256="b" * 64,
            proposals=(proposal,),
            rejections=(rejection,),
        )
        self.assertEqual(batch, ExtractionBatch.from_dict(batch.to_dict()))

        invalid = batch.to_dict()
        invalid["rejections"][0]["proposal_index"] = 2
        with self.assertRaisesRegex(ExtractionError, "rejections are not canonical"):
            ExtractionBatch.from_dict(invalid)

        with self.assertRaisesRegex(ExtractionError, "rejections are not canonical"):
            ExtractionBatch.build(
                target=self.catalog.target,
                source_catalog_sha256=self.catalog.catalog_sha256,
                provider="Together",
                inference_config_sha256="b" * 64,
                proposals=(),
                rejections=(rejection,),
            )

    def test_stale_catalog_or_wrong_model_fails_before_materialization(self) -> None:
        batch = self.batch(self.proposal())
        stale_batch = ExtractionBatch.build(
            target=batch.target,
            source_catalog_sha256="0" * 64,
            provider=batch.provider,
            inference_config_sha256=batch.inference_config_sha256,
            proposals=batch.proposals,
        )
        with self.assertRaisesRegex(ExtractionError, "stale"):
            materialize_quote_batch(stale_batch, self.catalog)
        with self.assertRaisesRegex(ExtractionError, "unauthorized"):
            replace(batch, inference_model="another/model")


if __name__ == "__main__":
    unittest.main()
