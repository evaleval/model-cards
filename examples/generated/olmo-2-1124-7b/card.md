# Model Card: OLMo-2-1124-7B

> Generated development output. It has not been human-reviewed and is not a release.

- Exact target: `allenai/OLMo-2-1124-7B@7df9a82518afdecae4e8c026b27adccc8c1f0032`
- Artifact: `card_2ea8cac1e07d39b0d29d4c72`
- Schema: v5
- Field coverage: 66.7%
- Generated bindings: 35 accepted, 6 withheld
- Automated audit annotation: no blocking support or scope finding among projected claims
- Audit record in public export: no
- Human review: not run

The automated source audit found no blocking support or scope finding among projected claims. A conflicting score for the DROP benchmark remained withheld. Omission checks, human review, and release checks are outstanding.

## Identity

- **model id:** allenai/OLMo-2-1124-7B
- **name:** OLMo-2-1124-7B
- **developed by:** Allen Institute for AI (Ai2)
- **model type:** a Transformer style autoregressive language model
- **license:** apache-2.0 (Hub-declared) — https://huggingface.co/allenai/OLMo-2-1124-7B/blob/7df9a82518afdecae4e8c026b27adccc8c1f0032/README.md
- **release date:** *Not specified*
- **version:** 7df9a82518afdecae4e8c026b27adccc8c1f0032
- **summary:** OLMo-2-1124-7B — a Transformer style autoregressive language model

## Lineage

- **base models:** *Not specified*
- **model family:** OLMo 2
- **derivatives:** *Not specified*

## Specifications

- **architecture type:** dense decoder-only
- **num parameters:** 7,298,617,344 parameters (safetensors metadata)
- **context length:** 4,096 tokens (README-reported context length)
- **precision:** Predominantly F32 by safetensors parameter-count metadata
- **modalities:** input: text, output: text
- **model stage:** base

## Training Context

- **training data:** Pretraining Stage 1: [OLMo-Mix-1124](https://huggingface.co/datasets/allenai/olmo-mix-1124); Pretraining Stage 2: [Dolmino-Mix-1124](https://huggingface.co/datasets/allenai/dolmino-mix-1124) (README-reported Base-model column).
- **training data size:** Pretraining Stage 1: 4 trillion tokens (1 epoch); Pretraining Stage 2: 50B tokens (3 runs) merged (README-reported Base-model column; no aggregate total inferred).
- **data cutoff:** *Not specified*
- **adaptations:** *Not specified*

## Access And Adoption

- **access type:** open-weight
- **downloads:** 84,909 downloads (Hub 30-day window, as of 2026-08-29)

## Evaluation

- **results summary:** *Not specified*

### Benchmark Scores

| Benchmark | Metric | Score | Split | Setting |
| --- | --- | ---: | --- | --- |
| ARC-Challenge | accuracy | 79.8 | Test | shots=5; chain_of_thought=False; reported_protocol_metric_column=pmi; formulation=best reported of MCF and CF; normalization=pmi |
| HellaSwag | accuracy | 83.8 | Val | shots=5; chain_of_thought=False; reported_protocol_metric_column=char; formulation=best reported of MCF and CF; normalization=char |
| WinoGrande | accuracy | 77.2 | Val | shots=5; chain_of_thought=False; reported_protocol_metric_column=none; formulation=best reported of MCF and CF; normalization=none |
| MMLU | accuracy | 63.7 | Test | shots=5; chain_of_thought=False; reported_protocol_metric_column=char; formulation=MCF only |
| Natural Questions | f1 | 36.9 | Val | shots=5; chain_of_thought=False; reported_protocol_metric_column=F1 |
| AGIEval English | accuracy | 50.4 | Test | shots=1; chain_of_thought=False; reported_protocol_metric_column=MCF; formulation=MCF only |
| GSM8K | exact_match | 67.5 | Test | shots=8; chain_of_thought=True; reported_protocol_metric_column=EM |
| MMLU-Pro | accuracy | 31 | Test | shots=5; chain_of_thought=False; reported_protocol_metric_column=MCF; formulation=MCF only |
| TriviaQA | f1 | 78 | Val | shots=5; chain_of_thought=False; reported_protocol_metric_column=F1 |

- **related model scores:** *Not specified*
- **human evals:** *Not specified*
- **safety evals:** *Not specified*
- **evaluation sources:** *Not specified*

## Links

- **model card:** https://huggingface.co/allenai/OLMo-2-1124-7B/tree/7df9a82518afdecae4e8c026b27adccc8c1f0032
- **system card:** *Not specified*
- **tech report:** https://arxiv.org/abs/2501.00656
- **code repository:** https://github.com/allenai/OLMo

## Provenance And Quality

- Coverage score: 0.666667
- Missing fields: identity.release_date, lineage.base_models, lineage.derivatives, training_context.data_cutoff, training_context.adaptations, evaluation.results_summary, evaluation.related_model_scores, evaluation.human_evals, evaluation.safety_evals, evaluation.evaluation_sources, links.system_card
- Flagged fields: evaluation.benchmark_scores, evaluation.results_summary, identity.summary, training_context.adaptations, training_context.data_cutoff
- Generation summary and source-manifest hashes remain in `card.json`.
- Field-level evidence remains in the non-public source artifact.
