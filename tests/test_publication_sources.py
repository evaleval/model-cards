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
    PUBLICATION_SOURCE_RULE_NAMES,
    PUBLICATION_SOURCE_RULESET,
    PublicationEnrichmentResult,
    PublicationFieldProvenance,
    PublicationSourceError,
    SourcePointer,
    enrich_publication_card,
    replay_publication_enrichment,
)
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
):
    metadata = json.dumps(
        {
            "id": "acme/Example-Instruct",
            "modelId": "acme/Example-Instruct",
            "sha": COMMIT,
            "author": "acme",
            "pipeline_tag": "text-generation",
            "private": False,
            "gated": False,
            "createdAt": "2025-01-02T03:04:05.000Z",
            "downloads": 1234,
            "likes": 56,
            "tags": [
                "safetensors",
                "license:apache-2.0",
                "arxiv:2401.12345",
                "base_model:acme/Example-Base",
                "base_model:finetune:acme/Example-Base",
            ],
            "cardData": {
                "license": "apache-2.0",
                "datasets": ["acme/training-set"],
                "base_model": "acme/Example-Base",
            },
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
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    readme = b"""# Example Instruct

Example Instruct documentation contains this deliberately long sentence that must remain private evidence only.

- Context Length: 8,192 tokens
- [GitHub](https://github.com/acme/Example)

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
            "model_type": "example",
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
        "acme/Example-Instruct",
        destination,
        Adapter(
            metadata,
            {
                "README.md": RemoteObject(FetchStatus.OK, readme),
                "config.json": RemoteObject(FetchStatus.OK, config),
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

        def score(model_id: str, benchmark: str):
            matches = [
                item["score"]
                for item in cards[model_id]["evaluation"].get("benchmark_scores", [])
                if item["benchmark"] == benchmark
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
        self.assertEqual(69.4, score("meta-llama/Llama-3.1-8B-Instruct", "MMLU"))
        self.assertEqual(
            [
                {
                    "model_id": "meta-llama/Meta-Llama-3.1-8B",
                    "relation": "base_model",
                }
            ],
            cards["meta-llama/Llama-3.1-8B-Instruct"]["lineage"]["base_models"],
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
            with self.subTest(score_cap=model_id):
                self.assertLessEqual(
                    len(card["evaluation"].get("benchmark_scores", [])), 12
                )
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
