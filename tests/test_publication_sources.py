from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
import unicodedata

from model_cards.publication_schema import (
    blank_publication_card,
    publication_coverage,
    validate_publication_card,
)
from model_cards.publication_sources import (
    PUBLICATION_CONFLICT_VERSION,
    PUBLICATION_SOURCE_RULE_NAMES,
    PUBLICATION_SOURCE_RULESET,
    PublicationEnrichmentResult,
    PublicationConflictRecord,
    PublicationFieldProvenance,
    PublicationSourceError,
    SourcePointer,
    enrich_publication_card,
    replay_publication_enrichment,
)
from model_cards.claim_gate import evaluate_claim_gate
from model_cards.extraction import deterministic_structured_candidates
from model_cards.family_risk import select_config_family_membership
from model_cards.source_bundle import (
    FetchStatus,
    RemoteObject,
    collect_hf_source_bundle,
    replay_source_bundle,
)
from model_cards.source_documents import build_source_document_catalog


COMMIT = "a" * 40


class Adapter:
    def __init__(self, metadata: bytes, files: dict[str, RemoteObject]) -> None:
        self.metadata = metadata
        self.files = files

    def resolve_revision(self, model_id: str, requested_revision: str | None) -> str:
        return COMMIT

    def fetch_model_metadata(
        self, model_id: str, revision: str, *, max_bytes: int
    ) -> RemoteObject:
        return RemoteObject(FetchStatus.OK, self.metadata)

    def fetch_file(
        self,
        model_id: str,
        revision: str,
        repo_path: str,
        *,
        max_bytes: int,
    ) -> RemoteObject:
        return self.files.get(
            repo_path,
            RemoteObject(FetchStatus.MISSING, reason_code="not_found"),
        )


def synthetic_catalog(
    test: unittest.TestCase,
    *,
    extra_readme: str = "",
    readme_frontmatter: str = "",
    model_id: str = "acme/Example-Instruct",
    base_model: str | None = "acme/Example-Base",
    base_model_tag_override: str | None = None,
    pipeline_tag: str | None = "text-generation",
    include_default_context: bool = True,
    config_model_type: str = "example",
    metadata_config_model_type: str | None = None,
    config_fetch_status: FetchStatus = FetchStatus.OK,
):
    tags = [
        "safetensors",
        "license:apache-2.0",
        "arxiv:2401.12345",
    ]
    card_data: dict[str, object] = {
        "license": "apache-2.0",
        "datasets": ["acme/training-set"],
    }
    if base_model is not None:
        tagged_base_model = base_model_tag_override or base_model
        tags.extend(
            (
                f"base_model:{tagged_base_model}",
                f"base_model:finetune:{tagged_base_model}",
            )
        )
        card_data["base_model"] = base_model
    metadata_value: dict[str, object] = {
            "id": model_id,
            "modelId": model_id,
            "sha": COMMIT,
            "author": "acme",
            "pipeline_tag": pipeline_tag,
            "private": False,
            "gated": False,
            "createdAt": "2025-01-02T03:04:05.000Z",
            "downloads": 1234,
            "likes": 56,
            "tags": tags,
            "cardData": card_data,
            "safetensors": {
                "parameters": {"BF16": 1_073_741_824},
                "total": 1_073_741_824,
            },
            # Deliberately unrelated to the tensor-payload derivation.
            "usedStorage": 999_999_999_999,
            "siblings": [
                {"rfilename": "README.md"},
                {"rfilename": "config.json"},
                {"rfilename": "model.safetensors"},
            ],
        }
    if metadata_config_model_type is not None:
        metadata_value["config"] = {"model_type": metadata_config_model_type}
    metadata = json.dumps(
        metadata_value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    context_line = "- Context Length: 8,192 tokens\n" if include_default_context else ""
    readme = readme_frontmatter.encode("utf-8") + b"""# Example Instruct

Example Instruct documentation contains this deliberately long sentence that must remain private evidence only.

"""
    readme += context_line.encode("utf-8") + b"""- [GitHub](https://github.com/acme/Example)

```bibtex
@misc{example2024,
  title={Example Technical Report},
  author={Acme},
  year={2024},
  eprint={2401.12345},
  archivePrefix={arXiv}
}
```
"""
    if extra_readme:
        readme += ("\n" + extra_readme + "\n").encode("utf-8")
    config = json.dumps(
        {
            "architectures": ["ExampleForCausalLM"],
            "model_type": config_model_type,
            "max_position_embeddings": 4096,
            "n_routed_experts": 8,
            "num_experts_per_tok": 2,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    temporary = tempfile.TemporaryDirectory()
    test.addCleanup(temporary.cleanup)
    destination = Path(temporary.name) / "source-bundle"
    collect_hf_source_bundle(
        model_id,
        destination,
        Adapter(
            metadata,
            {
                "README.md": RemoteObject(FetchStatus.OK, readme),
                "config.json": (
                    RemoteObject(FetchStatus.OK, config)
                    if config_fetch_status is FetchStatus.OK
                    else RemoteObject(
                        config_fetch_status, reason_code=config_fetch_status.value
                    )
                ),
            },
        ),
    )
    return build_source_document_catalog(replay_source_bundle(destination))


class PublicationSourceTests(unittest.TestCase):
    def test_source_pointers_are_closed_and_canonical(self) -> None:
        for pointer in ("source_uri", "/cardData/license", "text:0-17", "text:4-4"):
            with self.subTest(pointer=pointer):
                self.assertEqual(pointer, SourcePointer("source-1", pointer).pointer)

        for pointer in (
            "https://example.test/source",
            "cardData/license",
            "text:-1-2",
            "text:2-1",
            "text:one-two",
            "text:1-2-extra",
        ):
            with self.subTest(pointer=pointer):
                with self.assertRaises(PublicationSourceError):
                    SourcePointer("source-1", pointer)

    def test_provenance_rejects_unknown_fields_and_rules(self) -> None:
        known_rule = (
            f"{PUBLICATION_SOURCE_RULESET}/developer_from_metadata_author"
        )
        source = (SourcePointer("metadata", "/author"),)
        record = PublicationFieldProvenance(
            "identity.developed_by",
            known_rule,
            source,
        )
        self.assertIn(record.rule_name, PUBLICATION_SOURCE_RULE_NAMES)

        with self.assertRaises(PublicationSourceError):
            PublicationFieldProvenance(
                "audit.environmental_information",
                known_rule,
                source,
            )
        with self.assertRaises(PublicationSourceError):
            PublicationFieldProvenance(
                "identity.developed_by",
                f"{PUBLICATION_SOURCE_RULESET}/invented_rule",
                source,
            )

    def test_enriches_only_from_frozen_exact_target_sources(self) -> None:
        catalog = synthetic_catalog(self)
        result = enrich_publication_card(catalog)
        card = result.card
        validate_publication_card(card)

        self.assertEqual("acme/Example-Instruct", card["identity"]["model_id"])
        self.assertEqual("Example-Instruct", card["identity"]["name"])
        self.assertEqual(COMMIT, card["identity"]["version"])
        self.assertEqual("acme", card["identity"]["developed_by"])
        self.assertEqual("apache-2.0", card["identity"]["license"])
        self.assertNotIn("release_date", card["identity"])
        self.assertEqual(
            [{"model_id": "acme/Example-Base", "relation": "base_model"}],
            card["lineage"]["base_models"],
        )
        self.assertEqual("mixture-of-experts", card["specifications"]["architecture_type"])
        self.assertEqual(
            "1,073,741,824 total stored parameters (safetensors metadata)",
            card["specifications"]["num_parameters"],
        )
        self.assertEqual(
            "8,192 tokens (README-declared context length)",
            card["specifications"]["context_length"],
        )
        self.assertIn("bfloat16", card["specifications"]["precision"])
        self.assertEqual(
            "2.00 GiB estimated tensor payload (2,147,483,648 bytes; "
            "from safetensors dtype counts)",
            card["specifications"]["model_size"],
        )
        self.assertEqual(
            ["input: text", "output: text", "model stage: instruction-tuned"],
            card["specifications"]["input_output"],
        )
        self.assertIn("acme/training-set", card["training_context"]["training_data"])
        self.assertIn("declared weight files", card["access_and_adoption"]["access_type"])
        self.assertEqual(
            "https://huggingface.co/acme/Example-Instruct/blob/"
            f"{COMMIT}/README.md",
            card["links"]["model_card"],
        )
        self.assertEqual(
            "https://arxiv.org/abs/2401.12345", card["links"]["tech_report"]
        )
        self.assertEqual(
            "https://github.com/acme/Example", card["links"]["code_repository"]
        )
        self.assertIn("@misc{example2024", card["links"]["citation"])

        provenance = {item.field_path: item for item in result.provenance}
        self.assertEqual(
            ["/cardData/base_model"],
            [
                item.pointer
                for item in provenance["lineage.base_models"].sources
            ],
        )
        self.assertEqual(
            "/safetensors/parameters",
            provenance["specifications.model_size"].sources[0].pointer,
        )
        self.assertTrue(
            all(
                item.rule_name in PUBLICATION_SOURCE_RULE_NAMES
                for item in result.provenance
            )
        )
        self.assertNotIn("usedStorage", json.dumps(result.provenance_dict()))

    def test_explicit_publisher_identity_license_report_and_relation_win(self) -> None:
        catalog = synthetic_catalog(
            self,
            extra_readme="""
**Model developer**: Acme Research
**License:** A custom Model License is available at [Model Terms](https://acme.example/model-license)

[Example-Instruct Technical Report][example-report]
[example-report]: https://arxiv.org/abs/2501.54321

The Example-Instruct Large Language Model (LLM) is an instruct fine-tuned version of the Example-Base.
""",
        )

        result = enrich_publication_card(catalog)
        card = result.card
        provenance = {item.field_path: item for item in result.provenance}

        self.assertEqual("Acme Research", card["identity"]["developed_by"])
        self.assertEqual(
            "A custom Model License is available at Model Terms: "
            "https://acme.example/model-license",
            card["identity"]["license"],
        )
        self.assertEqual(
            "Example-Instruct is the publisher-documented instruction-fine-tuned "
            "version of Example-Base.",
            card["identity"]["summary"],
        )
        self.assertEqual(
            "https://arxiv.org/abs/2501.54321",
            card["links"]["tech_report"],
        )
        self.assertTrue(
            provenance["identity.developed_by"].rule_name.endswith(
                "developer_from_explicit_readme_label"
            )
        )
        self.assertTrue(
            provenance["identity.license"].rule_name.endswith(
                "license_from_explicit_readme_statement"
            )
        )
        self.assertTrue(
            provenance["links.tech_report"].rule_name.endswith(
                "technical_report_from_explicit_readme_link"
            )
        )

    def test_explicit_developer_upgrades_matching_metadata_author_in_base_card(self) -> None:
        catalog = synthetic_catalog(
            self,
            extra_readme="""
**Model developer**: Acme Research
""",
        )
        base = blank_publication_card()
        base["identity"]["developed_by"] = "acme"

        result = enrich_publication_card(catalog, base)
        provenance = {item.field_path: item for item in result.provenance}

        self.assertEqual("Acme Research", result.card["identity"]["developed_by"])
        self.assertTrue(
            provenance["identity.developed_by"].rule_name.endswith(
                "developer_from_explicit_readme_label"
            )
        )

        unrelated = deepcopy(base)
        unrelated["identity"]["developed_by"] = "Reviewed Developer"
        preserved = enrich_publication_card(catalog, unrelated)
        self.assertEqual(
            "Reviewed Developer", preserved.card["identity"]["developed_by"]
        )
        self.assertNotIn(
            "identity.developed_by",
            {item.field_path for item in preserved.provenance},
        )

    def test_explicit_prose_license_wins_over_frontmatter_identifier(self) -> None:
        catalog = synthetic_catalog(
            self,
            readme_frontmatter="---\nlicense: metadata-short-name\nauthors: metadata-author\n---\n",
            extra_readme="""
**Model developer:** Acme Weights Team
**License:** A custom weights license is available at [Model Terms](https://acme.example/weights-license)
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            "A custom weights license is available at Model Terms: "
            "https://acme.example/weights-license",
            card["identity"]["license"],
        )
        self.assertEqual("Acme Weights Team", card["identity"]["developed_by"])

    def test_explicit_license_does_not_duplicate_url_used_as_link_label(self) -> None:
        url = "https://acme.example/weights-license"
        catalog = synthetic_catalog(
            self,
            extra_readme=f"**License:** Custom model terms: [{url}]({url})",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(f"Custom model terms: {url}", card["identity"]["license"])

    def test_commercial_license_qualifier_requires_affirmative_polarity(self) -> None:
        cases = (
            (
                "Example series supports commercial use.",
                True,
            ),
            (
                "Example series does not support commercial use.",
                False,
            ),
            (
                "The Model License prohibits commercial use.",
                False,
            ),
            (
                "Commercial use is not permitted.",
                False,
            ),
            (
                "Example series doesn't allow commercial use.",
                False,
            ),
            (
                "Example series cannot permit commercial use.",
                False,
            ),
            (
                "No commercial use is allowed.",
                False,
            ),
        )
        for statement, expected in cases:
            with self.subTest(statement=statement):
                catalog = synthetic_catalog(
                    self,
                    extra_readme=(
                        "## License\n\n"
                        "The use of Example models is subject to "
                        "[the Model License](https://acme.example/model-license). "
                        f"{statement}\n"
                    ),
                )
                result = enrich_publication_card(catalog)
                value = result.card["identity"]["license"]
                self.assertEqual(
                    expected, "; commercial use supported" in value
                )
                sources = {
                    item.field_path: item.sources for item in result.provenance
                }
                self.assertEqual(
                    2 if expected else 1,
                    len(sources["identity.license"]),
                )

    def test_code_only_license_line_cannot_override_model_metadata(self) -> None:
        for qualifier in (
            "the example code only",
            "the source repository only",
            "repository tooling only",
            "this package only",
            "implementation utilities only",
        ):
            with self.subTest(qualifier=qualifier):
                catalog = synthetic_catalog(
                    self,
                    extra_readme=f"**License:** MIT for {qualifier}.",
                )

                card = enrich_publication_card(catalog).card

                self.assertEqual("apache-2.0", card["identity"]["license"])

    def test_family_named_license_under_model_scope_is_accepted(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="meta-llama/Llama-3.1-8B",
            base_model=None,
            extra_readme="""
# Llama-3.1-8B

## Model Information
**License:** A custom commercial license, the Llama 3.1 Community License, is available at: https://github.com/meta-llama/llama-models/blob/main/LICENSE
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertIn("Llama 3.1 Community License", card["identity"]["license"])

    def test_model_overview_is_generic_target_scope(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="Qwen/Qwen3-8B",
            base_model="Qwen/Qwen3-8B-Base",
            include_default_context=False,
            extra_readme="""
# Qwen3-8B

## Model Overview
- Context Length: 32,768 natively and 131,072 tokens with YaRN.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            "32,768 tokens natively; 131,072 tokens with YaRN "
            "(README-declared context length)",
            card["specifications"]["context_length"],
        )

    def test_comparison_prose_cannot_populate_target_summary_context_or_training(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Unrelated-70B-Base",
            base_model=None,
            include_default_context=False,
            extra_readme="""
## Description

Unrelated-70B-Base model is documented here. OtherModel is a multimodal,
multilingual model with text and image input and text output. For comparison,
Llama 3.1 offers a 128K context window.

For comparison, Llama 3.1 was pretrained on 15 trillion tokens.
Qwen3 is pre-trained on 36 trillion tokens.
We pre-train DeepSeek-V3 on 14.8 trillion tokens.
The 70B model was trained with 99 trillion tokens.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertNotIn("multimodal", card["identity"].get("summary", ""))
        self.assertEqual(
            "4,096 positions (config max_position_embeddings; implementation "
            "limit, not an independently verified context window)",
            card["specifications"]["context_length"],
        )
        self.assertNotIn("training_data_size", card["training_context"])

        same_sentence = synthetic_catalog(
            self,
            model_id="acme/Example-Base",
            base_model=None,
            extra_readme="""
## Description
Example-Base is documented here, while OtherModel is a multimodal,
multilingual model with text and image input and text output.
Example-Base is documented here, while OtherModel offers a 128K context window.
""",
        )
        same_sentence_card = enrich_publication_card(same_sentence).card
        self.assertNotIn(
            "multimodal", same_sentence_card["identity"].get("summary", "")
        )
        self.assertEqual(
            "4,096 positions (config max_position_embeddings; implementation "
            "limit, not an independently verified context window)",
            same_sentence_card["specifications"]["context_length"],
        )

    def test_family_adaptation_templates_cannot_populate_unrelated_target(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Unrelated-Instruct",
            base_model="acme/Unrelated-Base",
            extra_readme="""
## Release Documentation
The model used supervised finetuning, DPO, and RLVR.

It was followed by Supervised Fine-Tuning and Reinforcement Learning stages.
We introduce an innovative methodology to distill reasoning capabilities from
DeepSeek-R1 into DeepSeek-V3.
The tuned versions use supervised fine-tuning (SFT) and reinforcement learning
with human feedback (RLHF) for helpfulness and safety.
The family includes instruction-tuned variants.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertNotIn("adaptations", card["training_context"])

    def test_nested_sibling_sections_cannot_populate_family_training_fields(self) -> None:
        cases = (
            (
                "google/gemma-3-4b-pt",
                """### Training Dataset
- Web documents: RivalCorp documents
- Code: RivalCorp code
- Mathematics: RivalCorp mathematics
- Images: RivalCorp images
Over 999 languages.
""",
                ("RivalCorp", "999 languages"),
            ),
            (
                "allenai/OLMo-2-1124-7B",
                """### Stage 1: Initial Pretraining
- Dataset: RivalCorp/secret-data
- 7B Model: ~99 epochs

### Stage 2: Fine-tuning
- Dataset: RivalCorp/other-data
- Mix composition: 99% harmful material

#### Model Merging
- 7B Model: 9 versions trained on 999B mix, merged via model souping
""",
                ("RivalCorp", "99 epochs", "99%", "999B"),
            ),
            (
                "meta-llama/Llama-3.1-8B",
                """### Training Data
OtherModel was pretrained on 99 trillion tokens from private-source data.
""",
                ("99 trillion", "private-source"),
            ),
            (
                "Qwen/Qwen3-8B-Base",
                """- **Expanded Higher-Quality Pre-training Corpus:** 99 trillion
tokens across 999 languages.
""",
                ("99 trillion", "999 languages"),
            ),
        )
        for model_id, sibling_body, forbidden in cases:
            with self.subTest(model_id=model_id):
                target_name = model_id.rsplit("/", 1)[-1]
                catalog = synthetic_catalog(
                    self,
                    model_id=model_id,
                    base_model=None,
                    include_default_context=False,
                    extra_readme=(
                        f"# {target_name}\n\n## OtherModel\n\n{sibling_body}"
                    ),
                )

                card = enrich_publication_card(catalog).card
                serialized_training = json.dumps(
                    card["training_context"], sort_keys=True
                )

                for value in forbidden:
                    self.assertNotIn(value, serialized_training)
                self.assertEqual(
                    "Hugging Face dataset IDs declared in card metadata: "
                    "acme/training-set",
                    card["training_context"]["training_data"],
                )

    def test_nested_sibling_sections_cannot_populate_family_adaptations(self) -> None:
        cases = (
            (
                "allenai/OLMo-2-1124-7B-Instruct",
                "allenai/OLMo-2-1124-7B",
                """### Release Documentation
A rival checkpoint proceeds through supervised finetuning, DPO, and RLVR.
""",
            ),
            (
                "google/gemma-3-4b-it",
                "google/gemma-3-4b-pt",
                "Rival's instruction-tuned variants use a proprietary recipe.\n",
            ),
        )
        for model_id, base_model, sibling_body in cases:
            with self.subTest(model_id=model_id):
                target_name = model_id.rsplit("/", 1)[-1]
                catalog = synthetic_catalog(
                    self,
                    model_id=model_id,
                    base_model=base_model,
                    extra_readme=(
                        f"# {target_name}\n\n## OtherModel\n\n{sibling_body}"
                    ),
                )

                card = enrich_publication_card(catalog).card

                self.assertNotIn("adaptations", card["training_context"])

    def test_deepseek_adaptation_requires_both_supported_clauses(self) -> None:
        sft = (
            "DeepSeek-V3 pretraining is followed by Supervised Fine-Tuning and "
            "Reinforcement Learning stages."
        )
        distillation = (
            "We introduce an innovative methodology to distill reasoning "
            "capabilities from a DeepSeek-R1 model into DeepSeek-V3."
        )
        for name, prose in (("sft_only", sft), ("distillation_only", distillation)):
            with self.subTest(name=name):
                catalog = synthetic_catalog(
                    self,
                    model_id="deepseek-ai/DeepSeek-V3",
                    base_model="deepseek-ai/DeepSeek-V3-Base",
                    extra_readme=f"# DeepSeek-V3\n\n## Training\n\n{prose}",
                )

                card = enrich_publication_card(catalog).card

                self.assertNotIn("adaptations", card["training_context"])

        complete = synthetic_catalog(
            self,
            model_id="deepseek-ai/DeepSeek-V3",
            base_model="deepseek-ai/DeepSeek-V3-Base",
            extra_readme=(
                "# DeepSeek-V3\n\n## Training\n\n"
                f"{sft}\n\n{distillation}"
            ),
        )
        result = enrich_publication_card(complete)
        adaptation = result.card["training_context"]["adaptations"]
        sources = next(
            item.sources
            for item in result.provenance
            if item.field_path == "training_context.adaptations"
        )

        self.assertIn("supervised fine-tuning", adaptation)
        self.assertIn("distilling", adaptation)
        self.assertEqual(2, len(sources))

    def test_llama_finetuning_count_must_share_target_heading_scope(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="meta-llama/Llama-3.1-8B-Instruct",
            base_model="meta-llama/Llama-3.1-8B",
            extra_readme="""
# Llama-3.1-8B-Instruct

## Training Data
Llama 3.1 was pretrained on 15T tokens.

## OtherModel
Fine-tuning data includes over 999M synthetically generated examples.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            "15T tokens", card["training_context"]["training_data_size"]
        )

    def test_nested_sibling_safety_sections_cannot_populate_target(self) -> None:
        cases = (
            (
                "google/gemma-3-4b-pt",
                """### Ethics and Safety
#### Evaluation Results
Rival tests compare previous Gemma and cover child safety, content safety,
representational harms, and ungrounded inference without safety filters using
English language prompts.
""",
            ),
            (
                "meta-llama/Llama-3.1-8B",
                """### Responsibility & Safety
#### Evaluations
OtherModel uses adversarial evaluation and red teaming.

#### Critical and Other Risks
OtherModel considers CBRNE, child safety, and cyber risks.
""",
            ),
        )
        for model_id, sibling_body in cases:
            with self.subTest(model_id=model_id):
                target_name = model_id.rsplit("/", 1)[-1]
                catalog = synthetic_catalog(
                    self,
                    model_id=model_id,
                    base_model=None,
                    extra_readme=(
                        f"# {target_name}\n\n## OtherModel\n\n{sibling_body}"
                    ),
                )

                card = enrich_publication_card(catalog).card

                self.assertNotIn("safety_evals", card["evaluation"])

    def test_ancillary_target_prefixed_repository_is_not_code_repository(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="google/gemma-3-4b-it",
            base_model="google/gemma-3-4b-pt",
            extra_readme="""
# gemma-3-4b-it

## Links
[GitHub](https://github.com/google/gemma-3-4b-it-evaluation)
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertNotIn("code_repository", card["links"])

    def test_generic_resource_labels_cannot_override_target_links(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Unrelated-Instruct",
            base_model="acme/Unrelated-Base",
            extra_readme="""
[Technical report](https://example.com/report-about-another-model)
[GitHub](https://github.com/other-owner/other-project)
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            "https://arxiv.org/abs/2401.12345",
            card["links"]["tech_report"],
        )
        self.assertNotIn("code_repository", card["links"])

    def test_sibling_headings_cannot_override_unqualified_target_labels_or_modalities(self) -> None:
        catalog = synthetic_catalog(
            self,
            include_default_context=False,
            extra_readme="""
## OtherModel
**Model developer:** Rival Corp
**Context Length:** 128K
**Knowledge cutoff:** December 2099
**Supported languages:** Klingon

## Model Information
| Model | Input modalities | Output modalities |
| --- | --- | --- |
| Example-Base | audio | labels |
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual("acme", card["identity"]["developed_by"])
        self.assertEqual(
            "4,096 positions (config max_position_embeddings; implementation "
            "limit, not an independently verified context window)",
            card["specifications"]["context_length"],
        )
        self.assertNotIn("data_cutoff", card["training_context"])
        self.assertEqual(
            ["input: text", "output: text", "model stage: instruction-tuned"],
            card["specifications"]["input_output"],
        )

    def test_code_fence_comments_do_not_create_sibling_model_headings(self) -> None:
        catalog = synthetic_catalog(
            self,
            extra_readme="""
```python
# OtherModel
print("not a Markdown heading")
```

## Model Details
**Knowledge cutoff:** December 2023
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual("December 2023", card["training_context"]["data_cutoff"])

    def test_sibling_family_report_and_repository_links_are_rejected(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="deepseek-ai/DeepSeek-V3-Base",
            base_model=None,
            extra_readme="""
[DeepSeek-R1 Technical Report](https://example.com/deepseek-r1-report)
[GitHub](https://github.com/deepseek-ai/DeepSeek-R1)
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            "https://arxiv.org/abs/2401.12345",
            card["links"]["tech_report"],
        )
        self.assertNotIn("code_repository", card["links"])

    def test_closed_qwen_family_rules_reject_other_qwen3_tasks(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="Qwen/Qwen3-Embedding-8B-Base",
            base_model=None,
            extra_readme="""
- **Expanded Higher-Quality Pre-training Corpus:** Qwen3 is pre-trained on
  36 trillion tokens across 119 languages with code, STEM, reasoning, books,
  multilingual, and synthetic material.
Qwen3 is pre-trained on 36 trillion tokens.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertNotIn("training_data_size", card["training_context"])

    def test_explicit_base_stage_rejects_unmarked_sibling_score_column(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="deepseek-ai/DeepSeek-V3-Base",
            base_model=None,
            extra_readme="""
## Evaluation
| Benchmark | Metric | DeepSeek-V3 |
| --- | --- | ---: |
| MMLU | accuracy | 99.0 |
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertNotIn("benchmark_scores", card["evaluation"])

    def test_exact_readme_base_relation_and_change_are_projected(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Example-v0.3",
            base_model=None,
            extra_readme="""
The Example-v0.3 Large Language Model (LLM) is an Example-v0.2 with extended vocabulary.

Example-v0.3 has the following changes compared to [Example-v0.2](https://huggingface.co/acme/Example-v0.2/edit/main/README.md)
- Extended vocabulary to 32768
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            [{"model_id": "acme/Example-v0.2", "relation": "base_model"}],
            card["lineage"]["base_models"],
        )
        self.assertEqual(
            "Derived from acme/Example-v0.2; vocabulary extended to 32,768 entries.",
            card["training_context"]["adaptations"],
        )
        self.assertEqual(
            "Example-v0.3 is the publisher-documented Example-v0.2 successor with "
            "an extended vocabulary.",
            card["identity"]["summary"],
        )

    def test_unknown_config_model_type_is_not_promoted_to_model_family(self) -> None:
        catalog = synthetic_catalog(self, pipeline_tag=None)

        card = enrich_publication_card(catalog).card

        self.assertEqual("text-generation", card["identity"]["model_type"])
        self.assertNotIn("model_family", card["lineage"])

    def test_registered_publisher_config_derives_model_family(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="google/gemma-3-4b-pt",
            base_model=None,
            config_model_type="gemma3",
            metadata_config_model_type="gemma3",
        )

        result = enrich_publication_card(catalog)

        self.assertEqual("gemma3", result.card["lineage"]["model_family"])
        provenance = next(
            item
            for item in result.provenance
            if item.field_path == "lineage.model_family"
        )
        self.assertTrue(
            provenance.rule_name.endswith(
                "/model_family_from_registered_config_model_type"
            )
        )
        self.assertEqual("/model_type", provenance.sources[0].pointer)

    def test_gated_config_uses_exact_metadata_family_evidence(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="google/gemma-3-4b-pt",
            base_model=None,
            config_model_type="gemma3",
            metadata_config_model_type="gemma3",
            config_fetch_status=FetchStatus.GATED,
        )

        result = enrich_publication_card(catalog)

        self.assertEqual("gemma3", result.card["lineage"]["model_family"])
        provenance = next(
            item
            for item in result.provenance
            if item.field_path == "lineage.model_family"
        )
        self.assertEqual("/config/model_type", provenance.sources[0].pointer)

        extracted = deterministic_structured_candidates(catalog)
        candidates = tuple(
            item
            for item in extracted.candidates
            if item.field_path == "lineage.model_family"
        )
        self.assertEqual(1, len(candidates))
        self.assertEqual("/config/model_type", candidates[0].evidence[0].pointer)
        gate = evaluate_claim_gate(candidates[0], catalog.by_id)
        self.assertTrue(gate.projection_eligible)
        selected = select_config_family_membership((gate,))
        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("gemma3", selected[1].family_id)

    def test_known_architecture_in_unregistered_namespace_is_not_family_membership(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Gemma-Compatible",
            base_model=None,
            config_model_type="gemma3",
        )

        card = enrich_publication_card(catalog).card

        self.assertNotIn("model_family", card["lineage"])

    def test_model_information_modalities_and_languages_override_generic_mapping(self) -> None:
        catalog = synthetic_catalog(
            self,
            extra_readme="""
## Model Information
<table>
<tr><th>Model</th><th>Input modalities</th><th>Output modalities</th></tr>
<tr><td>Example-Instruct</td><td>Multilingual Text</td><td>Multilingual Text and code</td></tr>
</table>

**Supported languages:** English, German, and Thai.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            [
                "input: Multilingual Text",
                "output: Multilingual Text and code",
                "supported languages: English, German, and Thai",
                "model stage: instruction-tuned",
            ],
            card["specifications"]["input_output"],
        )

    def test_scoped_family_safety_evaluation_is_visible_without_model_score(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="meta-llama/Llama-3.1-8B-Instruct",
            base_model="meta-llama/Llama-3.1-8B",
            extra_readme="""
# Llama-3.1-8B-Instruct

## Responsibility & Safety
### Evaluations
The publisher used dedicated adversarial evaluation datasets.
The program also included recurring red teaming exercises.

### Critical and other risks
The assessed areas include CBRNE, Child Safety, and cyber attack enablement.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertEqual(
            "The publisher reports family/system-level adversarial safety evaluation "
            "and recurring red teaming covering CBRNE, child-safety, and cyber risks; "
            "this section does not state a checkpoint-specific numeric safety score.",
            card["evaluation"]["safety_evals"],
        )

    def test_family_safety_prose_cannot_populate_an_unrelated_target(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Unrelated-Instruct",
            base_model="acme/Unrelated-Base",
            extra_readme="""
## Ethics and Safety
### Evaluation Results
Child safety, content safety, representational harms, previous Gemma,
ungrounded inference, without safety filters, and English language prompts.

## Responsibility & Safety
### Evaluations
The publisher used adversarial evaluation and red teaming.
### Critical and other risks
The assessed areas include CBRNE, child safety, and cyber risks.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertNotIn("safety_evals", card["evaluation"])

    def test_gemma_safety_summary_requires_all_claim_markers(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="google/gemma-3-4b-it",
            base_model="google/gemma-3-4b-pt",
            extra_readme="""
# Gemma 3 model card

## Ethics and Safety
### Evaluation Results
For all areas of safety testing, we saw major improvements in child safety,
content safety, and representational harms relative to previous Gemma models.
Testing was conducted without safety filters and also found improvement in
ungrounded inference across all model sizes. The tests used only English language prompts.
""",
        )

        card = enrich_publication_card(catalog).card

        self.assertIn(
            "Gemma-family, all-model-size improvements",
            card["evaluation"]["safety_evals"],
        )
        self.assertIn(
            "does not provide PT/IT- or checkpoint-specific results",
            card["evaluation"]["safety_evals"],
        )

    def test_conflicting_base_model_metadata_is_withheld(self) -> None:
        catalog = synthetic_catalog(
            self,
            base_model="acme/Legacy-Base",
            base_model_tag_override="acme/Canonical-Base",
        )

        result = enrich_publication_card(catalog)
        card = result.card

        self.assertNotIn("base_models", card["lineage"])
        self.assertEqual(1, len(result.conflicts))
        conflict = result.conflicts[0]
        self.assertEqual("lineage.base_models", conflict.field_path)
        self.assertEqual(
            "metadata_base_model_declarations_disagree", conflict.reason
        )
        self.assertEqual(
            ["/cardData/base_model", "/tags"],
            [item.pointer for item in conflict.sources],
        )
        self.assertEqual(2, len(conflict.value_sha256s))
        self.assertEqual(
            conflict,
            PublicationConflictRecord.from_dict(conflict.to_dict()),
        )
        self.assertEqual(
            {
                "conflict_version",
                "ruleset",
                "records",
                "conflict_count",
                "conflicts_sha256",
            },
            set(result.conflicts_dict()),
        )
        self.assertEqual(
            PUBLICATION_CONFLICT_VERSION,
            result.conflicts_dict()["conflict_version"],
        )
        self.assertEqual(
            result,
            replay_publication_enrichment(catalog, expected=result),
        )
        serialized_public = json.dumps(card, sort_keys=True)
        self.assertNotIn("conflict", serialized_public.casefold())
        self.assertNotIn("value_sha256s", serialized_public)

    def test_conflicting_base_model_metadata_blocks_readme_fallback(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Example-v0.3",
            base_model="acme/Legacy-Base",
            base_model_tag_override="acme/Canonical-Base",
            extra_readme="""
The Example-v0.3 Large Language Model (LLM) is an Example-v0.2 with extended vocabulary.

Example-v0.3 follows [Example-v0.2](https://huggingface.co/acme/Example-v0.2).
""",
        )

        result = enrich_publication_card(catalog)

        self.assertNotIn("base_models", result.card["lineage"])
        self.assertEqual(
            ["metadata_base_model_declarations_disagree"],
            [conflict.reason for conflict in result.conflicts],
        )
        self.assertNotIn(
            "lineage.base_models",
            {item.field_path for item in result.provenance},
        )

    def test_conflicting_base_model_metadata_removes_draft_value(self) -> None:
        catalog = synthetic_catalog(
            self,
            base_model="acme/Legacy-Base",
            base_model_tag_override="acme/Canonical-Base",
        )
        draft = blank_publication_card()
        draft["lineage"]["base_models"] = [
            {"model_id": "acme/Legacy-Base", "relation": "base_model"}
        ]

        result = enrich_publication_card(catalog, draft)

        self.assertNotIn("base_models", result.card["lineage"])
        self.assertEqual(1, len(result.conflicts))
        self.assertNotIn(
            "lineage.base_models",
            {item.field_path for item in result.provenance},
        )

    def test_retains_all_exact_target_benchmark_rows_beyond_twelve(self) -> None:
        rows = [
            f"| Benchmark {index:02d} | accuracy | 5 | {index} | {100 + index} |"
            for index in range(1, 16)
        ]
        catalog = synthetic_catalog(
            self,
            extra_readme="\n".join(
                [
                    "## Evaluation",
                    "| Benchmark | Metric | Shots | Example-Instruct | Example-Base |",
                    "| --- | --- | ---: | ---: | ---: |",
                    *rows,
                    # Aggregate rows remain excluded, and an exact duplicate
                    # relation does not create a second benchmark tuple.
                    "| Average | accuracy | 5 | 8 | 108 |",
                    "| Benchmark 01 | accuracy | 5 | 1 | 101 |",
                ]
            ),
        )

        card = enrich_publication_card(catalog).card
        scores = card["evaluation"]["benchmark_scores"]

        self.assertEqual(15, len(scores))
        self.assertEqual(
            [f"Benchmark {index:02d}" for index in range(1, 16)],
            [item["benchmark"] for item in scores],
        )
        self.assertEqual(list(range(1, 16)), [item["score"] for item in scores])
        self.assertEqual({"accuracy"}, {item["metric"] for item in scores})
        self.assertEqual({"5 shots"}, {item["setting"] for item in scores})
        self.assertEqual(
            "The frozen README provides 15 exact-target benchmark scores; "
            "examples: Benchmark 01: 1; Benchmark 02: 2; Benchmark 03: 3.",
            card["evaluation"]["results_summary"],
        )

    def test_conflicting_duplicate_benchmark_relation_is_withheld(self) -> None:
        catalog = synthetic_catalog(
            self,
            extra_readme="""
## Evaluation
| Benchmark | Metric | Shots | Example-Instruct | Example-Base |
| --- | --- | ---: | ---: | ---: |
| Stable | accuracy | 5 | 70 | 60 |
| Stable | accuracy | 5 | 70 | 60 |
| Conflict | accuracy | 5 | 71 | 61 |
| Conflict | accuracy | 5 | 72 | 62 |
""",
        )

        result = enrich_publication_card(catalog)
        scores = result.card["evaluation"]["benchmark_scores"]

        self.assertEqual(
            [
                {
                    "benchmark": "Stable",
                    "metric": "accuracy",
                    "score": 70,
                    "setting": "5 shots",
                }
            ],
            scores,
        )
        self.assertEqual(1, len(result.conflicts))
        conflict = result.conflicts[0]
        self.assertEqual("evaluation.benchmark_scores", conflict.field_path)
        self.assertEqual("benchmark_coordinate_scores_disagree", conflict.reason)
        self.assertEqual(2, len(conflict.sources))
        self.assertTrue(
            all(item.pointer.startswith("text:") for item in conflict.sources)
        )
        self.assertEqual(2, len(conflict.value_sha256s))
        self.assertEqual(result, replay_publication_enrichment(catalog, expected=result))

    def test_exact_target_column_overrides_bad_heading_and_preserves_language(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Example-v3",
            base_model=None,
            extra_readme="""
### Instruction tuned models
#### Multilingual benchmarks
| Benchmark | Language | Example-v3 | Example-v3-Instruct |
| --- | --- | ---: | ---: |
| MMLU (5-shot, macro_avg/acc) | Portuguese | 62.12 | 70.0 |
| MMLU (5-shot, macro_avg/acc) | Spanish | 62.45 | 71.0 |
""",
        )

        scores = enrich_publication_card(catalog).card["evaluation"][
            "benchmark_scores"
        ]

        self.assertEqual(2, len(scores))
        self.assertEqual([62.12, 62.45], [item["score"] for item in scores])
        self.assertEqual({"MMLU"}, {item["benchmark"] for item in scores})
        self.assertEqual({"macro_avg/acc"}, {item["metric"] for item in scores})
        self.assertEqual(
            {
                "5 shots; language: Portuguese",
                "5 shots; language: Spanish",
            },
            {item["setting"] for item in scores},
        )

    def test_unambiguous_metric_and_split_qualifiers_are_projected(self) -> None:
        catalog = synthetic_catalog(
            self,
            extra_readme="""
## Evaluation
| Benchmark | Example-Instruct |
| --- | ---: |
| WMT24++ (ChrF) | 48.7 |
| DocVQA (val) | 72.1 |
| MMLU (Pro COT) | 61.2 |
| XQuAD (all) | 74.3 |
| MMMU (pt) | 50.4 |
""",
        )

        scores = enrich_publication_card(catalog).card["evaluation"][
            "benchmark_scores"
        ]
        by_benchmark = {item["benchmark"]: item for item in scores}

        self.assertEqual("ChrF", by_benchmark["WMT24++"]["metric"])
        self.assertEqual("val", by_benchmark["DocVQA"]["split"])
        for name in ("MMLU (Pro COT)", "XQuAD (all)", "MMMU (pt)"):
            with self.subTest(name=name):
                self.assertIn(name, by_benchmark)
                self.assertEqual(
                    "README-reported score", by_benchmark[name]["metric"]
                )

    def test_exact_model_column_wins_over_family_prefix_column(self) -> None:
        catalog = synthetic_catalog(
            self,
            model_id="acme/Example-v3",
            base_model=None,
            extra_readme="""
## Evaluation
| Benchmark | Metric | Shots | Example-v3-Base | Example-v3 |
| --- | --- | ---: | ---: | ---: |
| MMLU | accuracy | 5 | 87.1 | 88.5 |
""",
        )

        scores = enrich_publication_card(catalog).card["evaluation"][
            "benchmark_scores"
        ]

        self.assertEqual(
            [
                {
                    "benchmark": "MMLU",
                    "metric": "accuracy",
                    "score": 88.5,
                    "setting": "5 shots",
                }
            ],
            scores,
        )

    def test_withholding_is_validated_skipped_and_exactly_replayable(self) -> None:
        catalog = synthetic_catalog(self)
        withheld = ("identity.license", "links.code_repository")
        result = enrich_publication_card(
            catalog,
            withheld_fields=withheld,
        )

        self.assertNotIn("license", result.card["identity"])
        self.assertNotIn("code_repository", result.card["links"])
        self.assertTrue(
            set(withheld).isdisjoint(item.field_path for item in result.provenance)
        )
        self.assertEqual(
            result,
            replay_publication_enrichment(
                catalog,
                withheld_fields=withheld,
                expected=result,
            ),
        )

        changed = deepcopy(result.card)
        changed["identity"]["summary"] = "A fabricated replay value."
        mismatched = PublicationEnrichmentResult(changed, result.provenance)
        with self.assertRaisesRegex(PublicationSourceError, "replay card"):
            replay_publication_enrichment(
                catalog,
                withheld_fields=withheld,
                expected=mismatched,
            )

        mismatched_provenance = PublicationEnrichmentResult(
            result.card,
            result.provenance[:-1],
        )
        with self.assertRaisesRegex(PublicationSourceError, "replay provenance"):
            replay_publication_enrichment(
                catalog,
                withheld_fields=withheld,
                expected=mismatched_provenance,
            )

        mismatched_conflicts = PublicationEnrichmentResult(
            result.card,
            result.provenance,
            (
                PublicationConflictRecord(
                    field_path="evaluation.benchmark_scores",
                    reason="benchmark_coordinate_scores_disagree",
                    sources=(SourcePointer("synthetic-source", "text:0-1"),),
                    value_sha256s=("0" * 64, "1" * 64),
                ),
            ),
        )
        with self.assertRaisesRegex(PublicationSourceError, "replay conflicts"):
            replay_publication_enrichment(
                catalog,
                withheld_fields=withheld,
                expected=mismatched_conflicts,
            )

        for invalid in (
            ("links.code_repository", "identity.license"),
            ("identity.license", "identity.license"),
            ("audit.environmental_information",),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(PublicationSourceError):
                    enrich_publication_card(catalog, withheld_fields=invalid)

    def test_preserves_existing_specified_values_without_mutating_input(self) -> None:
        catalog = synthetic_catalog(self)
        existing = blank_publication_card()
        existing["identity"]["summary"] = "Human-reviewed summary."
        existing["identity"]["license"] = "Reviewed license label"
        before = deepcopy(existing)

        result = enrich_publication_card(catalog, existing)

        self.assertEqual(before, existing)
        self.assertEqual("Human-reviewed summary.", result.card["identity"]["summary"])
        self.assertEqual("Reviewed license label", result.card["identity"]["license"])
        derived_paths = {item.field_path for item in result.provenance}
        self.assertNotIn("identity.summary", derived_paths)
        self.assertNotIn("identity.license", derived_paths)

    def test_rejects_long_verbatim_source_prose_from_public_fields(self) -> None:
        catalog = synthetic_catalog(self)
        existing = blank_publication_card()
        existing["identity"]["summary"] = (
            "Example Instruct documentation contains this deliberately long sentence "
            "that must remain private evidence only."
        )

        with self.assertRaisesRegex(
            PublicationSourceError,
            "identity.summary contains a prohibited frozen-source excerpt",
        ):
            enrich_publication_card(catalog, existing)

    def test_ascii_source_excerpt_boundary_remains_twelve_words(self) -> None:
        eleven_words = "one two three four five six seven eight nine ten eleven"
        twelve_words = eleven_words + " twelve"
        catalog = synthetic_catalog(self, extra_readme=twelve_words)

        allowed = blank_publication_card()
        allowed["identity"]["summary"] = eleven_words
        result = enrich_publication_card(catalog, allowed)
        self.assertEqual(eleven_words, result.card["identity"]["summary"])

        rejected = blank_publication_card()
        rejected["identity"]["summary"] = twelve_words
        with self.assertRaisesRegex(
            PublicationSourceError,
            "identity.summary contains a prohibited frozen-source excerpt",
        ):
            enrich_publication_card(catalog, rejected)

    def test_rejects_canonically_equivalent_accented_source_prose(self) -> None:
        excerpt = (
            "Éléonore évalue naïvement douze modèles génératifs spécialisés avec "
            "précision sécurité équité transparence."
        )
        source_form = unicodedata.normalize("NFD", excerpt.upper())
        catalog = synthetic_catalog(self, extra_readme=source_form)
        existing = blank_publication_card()
        existing["identity"]["summary"] = excerpt

        with self.assertRaisesRegex(
            PublicationSourceError,
            "identity.summary contains a prohibited frozen-source excerpt",
        ):
            enrich_publication_card(catalog, existing)

    def test_rejects_cyrillic_source_prose(self) -> None:
        excerpt = (
            "Исследователи подробно проверяют новую языковую модель на качество "
            "безопасность точность устойчивость справедливость прозрачность."
        )
        catalog = synthetic_catalog(self, extra_readme=excerpt.upper())
        existing = blank_publication_card()
        existing["evaluation"]["human_evals"] = excerpt.casefold()

        with self.assertRaisesRegex(
            PublicationSourceError,
            "evaluation.human_evals contains a prohibited frozen-source excerpt",
        ):
            enrich_publication_card(catalog, existing)

    def test_rejects_cjk_source_prose_without_word_boundaries(self) -> None:
        source_excerpt = (
            "该模型使用多语言训练数据，并经过严格安全评估，"
            "确保输出稳定可靠且适用于专业研究场景。"
        )
        public_excerpt = source_excerpt.replace("，", "").replace("。", "")
        catalog = synthetic_catalog(self, extra_readme=source_excerpt)
        existing = blank_publication_card()
        existing["training_context"]["training_data"] = public_excerpt

        with self.assertRaisesRegex(
            PublicationSourceError,
            "training_context.training_data contains a prohibited frozen-source excerpt",
        ):
            enrich_publication_card(catalog, existing)

    def test_short_unicode_facts_and_link_fields_remain_allowed(self) -> None:
        accented_fact = "Modèle entraîné sur données publiques multilingues."
        cjk_fact = "支持中文文本生成与摘要"
        system_card = (
            "https://example.org/one/two/three/four/five/six/seven/eight/"
            "nine/ten/eleven/twelve/thirteen"
        )
        catalog = synthetic_catalog(
            self,
            extra_readme=(
                f"{accented_fact}\n{cjk_fact}\n"
                f"[System card]({system_card})"
            ),
        )
        existing = blank_publication_card()
        existing["identity"]["summary"] = accented_fact
        existing["training_context"]["adaptations"] = cjk_fact
        existing["links"]["system_card"] = system_card

        result = enrich_publication_card(catalog, existing)

        self.assertEqual(accented_fact, result.card["identity"]["summary"])
        self.assertEqual(
            cjk_fact,
            result.card["training_context"]["adaptations"],
        )
        self.assertEqual(system_card, result.card["links"]["system_card"])

    def test_rejects_target_identity_conflicts(self) -> None:
        catalog = synthetic_catalog(self)
        existing = blank_publication_card()
        existing["identity"]["model_id"] = "other/Model"
        with self.assertRaises(PublicationSourceError):
            enrich_publication_card(catalog, existing)

    def test_is_deterministic_and_reaches_floor_on_frozen_pilot(self) -> None:
        configured_root = os.environ.get("MODEL_CARDS_FROZEN_PILOT_ROOT")
        if configured_root is None:
            self.skipTest("set MODEL_CARDS_FROZEN_PILOT_ROOT for frozen-pilot acceptance")
        target_root = Path(configured_root)
        if not target_root.is_dir():
            self.skipTest("the configured frozen 12-target pilot is not present")
        targets = sorted(
            item for item in target_root.iterdir() if (item / "source-bundle").is_dir()
        )
        self.assertEqual(12, len(targets))
        cards = {}
        for target in targets:
            with self.subTest(target=target.name):
                catalog = build_source_document_catalog(
                    replay_source_bundle(target / "source-bundle")
                )
                first = enrich_publication_card(catalog)
                second = enrich_publication_card(catalog)
                cards[catalog.target.model_id] = first.card
                self.assertEqual(first, second)
                validate_publication_card(first.card)
                self.assertGreaterEqual(round(publication_coverage(first.card) * 33), 15)
                known_source_ids = {item.source_id for item in catalog.documents}
                for record in first.provenance:
                    self.assertTrue(record.sources)
                    self.assertTrue(
                        {item.source_id for item in record.sources} <= known_source_ids
                    )
                    if record.field_path in {
                        "identity.summary",
                        "lineage.derivatives",
                        "training_context.training_data",
                        "training_context.training_data_size",
                        "training_context.data_cutoff",
                        "training_context.adaptations",
                        "evaluation.results_summary",
                        "evaluation.benchmark_scores",
                        "evaluation.safety_evals",
                    }:
                        self.assertTrue(
                            any(item.pointer.startswith("text:") for item in record.sources),
                            record.field_path,
                        )
                    if record.field_path == "links.code_repository":
                        text_pointers = [
                            item.pointer
                            for item in record.sources
                            if item.pointer.startswith("text:")
                        ]
                        self.assertEqual(1, len(text_pointers))
                        start, end = map(
                            int, text_pointers[0][len("text:") :].split("-", 1)
                        )
                        self.assertLessEqual(end - start, 512)
                if catalog.target.model_id == "allenai/OLMo-2-1124-7B":
                    context = next(
                        item
                        for item in first.provenance
                        if item.field_path == "specifications.context_length"
                    )
                    self.assertTrue(
                        any(item.pointer.startswith("text:") for item in context.sources)
                    )
                serialized = json.dumps(first.card, sort_keys=True)
                self.assertNotIn("usedStorage", serialized)
                self.assertNotIn("environmental", serialized.casefold())
                # A mention of human reviewers or RLHF is not a human-evaluation
                # result.  None of these frozen READMEs reports an exact-target
                # human-evaluation outcome suitable for this field.
                self.assertNotIn("human_evals", first.card["evaluation"])

        rich_targets = {
            "allenai/OLMo-2-1124-7B",
            "allenai/OLMo-2-1124-7B-Instruct",
            "google/gemma-3-4b-pt",
            "google/gemma-3-4b-it",
            "deepseek-ai/DeepSeek-V3-Base",
            "deepseek-ai/DeepSeek-V3",
            "meta-llama/Llama-3.1-8B",
            "meta-llama/Llama-3.1-8B-Instruct",
            "Qwen/Qwen3-8B-Base",
            "Qwen/Qwen3-8B",
        }
        for model_id in sorted(rich_targets):
            with self.subTest(rich_target=model_id):
                self.assertGreaterEqual(
                    round(publication_coverage(cards[model_id]) * 33), 23
                )

        # This is a frozen-source completeness regression, not a mandate to
        # populate unsupported fields.  It prevents a parser change from
        # silently reintroducing the old 12-row score cap or dropping other
        # exact-target facts that are present in this retained cohort.
        self.assertEqual(
            298,
            sum(round(publication_coverage(card) * 33) for card in cards.values()),
        )
        self.assertEqual(
            153,
            sum(
                len(card["evaluation"].get("benchmark_scores", []))
                for card in cards.values()
            ),
        )

        def score(model_id: str, benchmark: str):
            matches = [
                item["score"]
                for item in cards[model_id]["evaluation"].get("benchmark_scores", [])
                if item["benchmark"] == benchmark
                and "language:" not in item["setting"]
            ]
            self.assertEqual(1, len(matches), (model_id, benchmark, matches))
            return matches[0]

        # Each parser is variant-selective: these values come from different
        # exact rows/columns in the same family README, not from neighboring
        # checkpoints.
        self.assertEqual(63.7, score("allenai/OLMo-2-1124-7B", "MMLU"))
        self.assertEqual(61.3, score("allenai/OLMo-2-1124-7B-Instruct", "MMLU"))
        self.assertEqual(
            {
                "allenai/OLMo-2-1124-7B-DPO",
                "allenai/OLMo-2-1124-7B-Instruct",
                "allenai/OLMo-2-1124-7B-RM",
                "allenai/OLMo-2-1124-7B-SFT",
            },
            {
                item["model_id"]
                for item in cards["allenai/OLMo-2-1124-7B"]["lineage"]["derivatives"]
            },
        )
        self.assertEqual(59.6, score("google/gemma-3-4b-pt", "MMLU"))
        self.assertNotIn("benchmark_scores", cards["google/gemma-3-4b-it"]["evaluation"])
        self.assertEqual(87.1, score("deepseek-ai/DeepSeek-V3-Base", "MMLU"))
        self.assertEqual(88.5, score("deepseek-ai/DeepSeek-V3", "MMLU"))
        self.assertIn(
            "FP8",
            cards["deepseek-ai/DeepSeek-V3-Base"]["specifications"]["precision"],
        )
        self.assertIn(
            "FP8",
            cards["deepseek-ai/DeepSeek-V3"]["specifications"]["precision"],
        )
        for model_id in (
            "deepseek-ai/DeepSeek-V3-Base",
            "deepseek-ai/DeepSeek-V3",
        ):
            with self.subTest(moe_parameter_count=model_id):
                value = cards[model_id]["specifications"]["num_parameters"]
                self.assertIn("684,531,386,000 total stored parameters", value)
                self.assertIn("671B total model parameters", value)
                self.assertIn("37B activated per token", value)
        self.assertEqual(66.7, score("meta-llama/Llama-3.1-8B", "MMLU"))
        multilingual_llama_scores = [
            item
            for item in cards["meta-llama/Llama-3.1-8B"]["evaluation"][
                "benchmark_scores"
            ]
            if item["benchmark"] == "MMLU" and "language:" in item["setting"]
        ]
        self.assertEqual(
            {"macro_avg/acc"},
            {item["metric"] for item in multilingual_llama_scores},
        )
        self.assertTrue(
            all(item["setting"].startswith("5 shots; ") for item in multilingual_llama_scores)
        )
        llama_languages = {
            item["setting"].rsplit("language: ", 1)[1]
            for item in cards["meta-llama/Llama-3.1-8B"]["evaluation"][
                "benchmark_scores"
            ]
            if item["benchmark"] == "MMLU" and "language:" in item["setting"]
        }
        self.assertEqual(
            {"Portuguese", "Spanish", "Italian", "German", "French", "Hindi", "Thai"},
            llama_languages,
        )
        self.assertEqual(69.4, score("meta-llama/Llama-3.1-8B-Instruct", "MMLU"))
        for model_id in (
            "meta-llama/Llama-3.1-8B",
            "meta-llama/Llama-3.1-8B-Instruct",
        ):
            with self.subTest(llama_identity=model_id):
                self.assertEqual("Meta", cards[model_id]["identity"]["developed_by"])
                self.assertIn(
                    "Llama 3.1 Community License",
                    cards[model_id]["identity"]["license"],
                )
                self.assertIn(
                    "https://github.com/meta-llama/llama-models/",
                    cards[model_id]["identity"]["license"],
                )
        for model_id in (
            "google/gemma-3-4b-pt",
            "google/gemma-3-4b-it",
        ):
            with self.subTest(gemma_identity=model_id):
                self.assertEqual(
                    "Google DeepMind", cards[model_id]["identity"]["developed_by"]
                )
                self.assertEqual(
                    "https://goo.gle/Gemma3Report",
                    cards[model_id]["links"]["tech_report"],
                )
        for model_id in (
            "deepseek-ai/DeepSeek-V3-Base",
            "deepseek-ai/DeepSeek-V3",
        ):
            with self.subTest(deepseek_identity=model_id):
                self.assertEqual(
                    "text-generation", cards[model_id]["identity"]["model_type"]
                )
                self.assertIn("Model License", cards[model_id]["identity"]["license"])
        self.assertEqual(
            [{"model_id": "mistralai/Mistral-7B-v0.2", "relation": "base_model"}],
            cards["mistralai/Mistral-7B-v0.3"]["lineage"]["base_models"],
        )
        self.assertIn(
            "vocabulary extended to 32,768 entries",
            cards["mistralai/Mistral-7B-v0.3"]["training_context"]["adaptations"],
        )
        self.assertNotIn(
            "base_models",
            cards["meta-llama/Llama-3.1-8B-Instruct"]["lineage"],
        )

        gemma_scores = {
            item["benchmark"]: item
            for item in cards["google/gemma-3-4b-pt"]["evaluation"][
                "benchmark_scores"
            ]
        }
        self.assertEqual("ChrF", gemma_scores["WMT24++"]["metric"])
        for benchmark in ("DocVQA", "InfoVQA", "TextVQA"):
            with self.subTest(gemma_split=benchmark):
                self.assertEqual("val", gemma_scores[benchmark]["split"])
        for model_id in ("google/gemma-3-4b-pt", "google/gemma-3-4b-it"):
            with self.subTest(gemma_safety_scope=model_id):
                self.assertIn(
                    "Gemma-family, all-model-size",
                    cards[model_id]["evaluation"]["safety_evals"],
                )
                self.assertIn(
                    "does not provide PT/IT- or checkpoint-specific results",
                    cards[model_id]["evaluation"]["safety_evals"],
                )
        self.assertEqual(
            "32,768 tokens natively; 131,072 tokens with YaRN "
            "(README-declared context length)",
            cards["Qwen/Qwen3-8B"]["specifications"]["context_length"],
        )
        self.assertEqual(
            "32,768 tokens (README-declared context length)",
            cards["Qwen/Qwen3-8B-Base"]["specifications"]["context_length"],
        )

        for model_id, card in cards.items():
            with self.subTest(score_rows=model_id):
                self.assertNotIn(
                    "Average",
                    {
                        item["benchmark"]
                        for item in card["evaluation"].get("benchmark_scores", [])
                    },
                )

        # Post-training prose is not allowed to leak onto the paired base card.
        self.assertNotIn(
            "adaptations", cards["deepseek-ai/DeepSeek-V3-Base"]["training_context"]
        )
        self.assertIn(
            "adaptations", cards["deepseek-ai/DeepSeek-V3"]["training_context"]
        )
        self.assertNotIn(
            "adaptations", cards["meta-llama/Llama-3.1-8B"]["training_context"]
        )
        self.assertIn(
            "adaptations",
            cards["meta-llama/Llama-3.1-8B-Instruct"]["training_context"],
        )


if __name__ == "__main__":
    unittest.main()
