# Model Card: Llama\-3\-Instruct\-8B\-SimPO\-ExPO

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\-instruct\-8b\-simpo\-expo\.json](<./llama-3-instruct-8b-simpo-expo.json>)<br>
SHA-256: `2ef66d1a1aab7a6a2535e7c8ae3f8787053775c9a38d40b2a997d94ccbe138b7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | chujiezheng/Llama\-3\-Instruct\-8B\-SimPO\-ExPO |
| Name | Llama\-3\-Instruct\-8B\-SimPO\-ExPO |
| Developed by | chujiezheng \(Hub organization\) |
| License | llama3 |
| Release date | 2024\-05\-26 \(Hugging Face repository creation date\) |
| Version | 3fcaa9fe99691659eb197487e9a343f601bf63f2 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama 3 SimPO ExPO |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 28 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 16 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The extrapolated model reports a 40\.6% win rate and 45\.8% length\-controlled win rate on AlpacaEval 2\.0, slightly ahead of the original Llama\-3\-Instruct\-8B\-SimPO model\. |
| Human evaluations | The developer reports AlpacaEval 2\.0 results for this extrapolated model: a 40\.6% win rate and a 45\.8% length\-controlled win rate\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/chujiezheng/Llama\-3\-Instruct\-8B\-SimPO\-ExPO](<https://huggingface.co/chujiezheng/Llama-3-Instruct-8B-SimPO-ExPO>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
