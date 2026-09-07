# Model Card: \*\*Gauss\-Opus\-14B\-R999\*\*

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gauss\-opus\-14b\-r999\.json](<./gauss-opus-14b-r999.json>)<br>
SHA-256: `1a20de6b0bbaaceab2f1ad6313c7d72e897ab09eb011e3719b66dea4ff584801`

## Identity

| Field | Value |
| --- | --- |
| Model ID | prithivMLmods/Gauss\-Opus\-14B\-R999 |
| Name | \*\*Gauss\-Opus\-14B\-R999\*\* |
| Developed by | prithivMLmods \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2025\-03\-03 \(Hugging Face repository creation date\) |
| Version | 9afffe850012930627d52009505314f52b66f08c |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-14B\-Instruct (base model; Kind: finetune) |
| Model family | Gauss Opus R999 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,770,033,664 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,540,133,904 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on specialized datasets in mathematics, physics, and formal logic\. |
| Adaptations | The model is a fine\-tune using specialized datasets in mathematics, physics, and formal logic, with an emphasis on structured, high\-accuracy outputs\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 29 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/prithivMLmods/Gauss\-Opus\-14B\-R999](<https://huggingface.co/prithivMLmods/Gauss-Opus-14B-R999>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
