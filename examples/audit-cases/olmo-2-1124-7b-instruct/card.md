# Model Card: OLMo-2-1124-7B-Instruct

> Audit-blocked generated output. The automated audit found source-present omissions, so this card was not promoted.

- Exact target: `allenai/OLMo-2-1124-7B-Instruct@470b1fba1ae01581f270116362ee4aa1b97f4c84`
- Artifact: `card_f02be2494070da12cb9b5abd`
- Schema: v5
- Field coverage: 63.6%
- Generated bindings: 33 accepted, 8 withheld
- Automated audit annotation: blocked
- Audit record in public export: no
- Human review: not run

The included claims were supported at their recorded qualifications, but the audit found two source-present omissions: model family and training data size. The card was not promoted.

## Identity

- **model id:** allenai/OLMo-2-1124-7B-Instruct
- **name:** OLMo-2-1124-7B-Instruct
- **developed by:** Allen Institute for AI (publisher-documented default demo prompt attribution)
- **model type:** text-generation
- **license:** apache-2.0 (Hub-declared) — https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct/blob/470b1fba1ae01581f270116362ee4aa1b97f4c84/README.md
- **release date:** *Not specified*
- **version:** 470b1fba1ae01581f270116362ee4aa1b97f4c84
- **summary:** OLMo-2-1124-7B-Instruct — text-generation

## Lineage

- **base models:** allenai/OLMo-2-1124-7B-DPO (relation: base; kind: finetune)
- **model family:** *Not specified*
- **derivatives:** *Not specified*

## Specifications

- **architecture type:** dense decoder-only
- **num parameters:** 7,298,617,344 parameters (safetensors metadata)
- **context length:** *Not specified*
- **precision:** Predominantly BF16 by safetensors parameter-count metadata
- **modalities:** input: text, output: text
- **model stage:** instruct

## Training Context

- **training data:** The model was further trained using DPO on the olmo-2-1124-7b-preference-mix dataset.
- **training data size:** *Not specified*
- **data cutoff:** *Not specified*
- **adaptations:** Post-trained (instruction-tuned) variant of the OLMo-2 7B November 2024 base model.

## Access And Adoption

- **access type:** open-weight
- **downloads:** 64,946 downloads (Hub 30-day window, as of 2026-08-29)

## Evaluation

- **results summary:** *Not specified*

### Benchmark Scores

| Benchmark | Metric | Score | Split | Setting |
| --- | --- | ---: | --- | --- |
| AlpacaEval 2 | LC Winrate | 29.1 |  | shots=0; chain_of_thought=False; chat_template=True; multiturn_icl=N/A |
| DROP | f1 | 60.5 |  | shots=3; chain_of_thought=False; chat_template=False; multiturn_icl=N/A; reported_metric=F1 |
| GSM8K | exact_match | 85.1 |  | shots=8; chain_of_thought=True; chat_template=True; multiturn_icl=True; reported_metric=EM |
| IFEval | Pass@1 (prompt; loose) | 72.3 |  | shots=0; chain_of_thought=False; chat_template=True; multiturn_icl=N/A |
| MATH | Flex EM | 32.5 |  | shots=4; chain_of_thought=True; chat_template=True; multiturn_icl=True |
| MMLU | exact_match | 61.3 |  | shots=0; chain_of_thought=True; chat_template=True; multiturn_icl=False; reported_metric=EM |
| PopQA | exact_match | 23.2 |  | shots=15; chain_of_thought=False; chat_template=True; multiturn_icl=True; reported_metric=EM |
| TruthfulQA | MC2 | 56.5 |  | shots=6; chain_of_thought=False; chat_template=True; multiturn_icl=False |

- **related model scores:** *Not specified*
- **human evals:** *Not specified*
- **safety evals:** *Not specified*
- **evaluation sources:** *Not specified*

## Links

- **model card:** https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct/tree/470b1fba1ae01581f270116362ee4aa1b97f4c84
- **system card:** *Not specified*
- **tech report:** https://arxiv.org/abs/2501.00656
- **code repository:** https://github.com/allenai/OLMo

## Provenance And Quality

- Coverage score: 0.636364
- Missing fields: identity.release_date, lineage.model_family, lineage.derivatives, specifications.context_length, training_context.training_data_size, training_context.data_cutoff, evaluation.results_summary, evaluation.related_model_scores, evaluation.human_evals, evaluation.safety_evals, evaluation.evaluation_sources, links.system_card
- Flagged fields: evaluation.benchmark_scores, evaluation.results_summary, identity.developed_by, identity.summary, lineage.model_family
- Generation summary and source-manifest hashes remain in `card.json`.
- Field-level evidence remains in the non-public source artifact.
