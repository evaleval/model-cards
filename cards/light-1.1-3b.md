# Model Card: light\-1\.1\-3B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [light\-1\.1\-3b\.json](<./light-1.1-3b.json>)<br>
SHA-256: `c0650f03e3146c9d80eea25ca3fbaf9c5ad53723ade6031c8cc89dc917a6eff7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Sakalti/light\-1\.1\-3B |
| Name | light\-1\.1\-3B |
| Developed by | Sakalti \(Hub organization\) |
| License | other |
| Release date | 2025\-01\-07 \(Hugging Face repository creation date\) |
| Version | 1eda1a75e2575cc65bf340289446b9cb41990539 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Sakalti/light\-3B (base model; Kind: finetune) |
| Model family | light 1\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,085,938,688 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 5\.7 GiB of safetensors weights \(6,171,926,568 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was trained with Unsloth and Hugging Face's TRL library, which the source states enabled two\-fold faster training\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 16 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Sakalti/light\-1\.1\-3B](<https://huggingface.co/Sakalti/light-1.1-3B>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
