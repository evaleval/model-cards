# Model Card: Mistral\-7B\-Instruct\-v0\.3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-7b\-instruct\-v0\.3\.json](<./mistral-7b-instruct-v0.3.json>)<br>
SHA-256: `a901bb3aeff0768b782c82eb17b8d2c4d0442e2efafc00d088242e382527204e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | mistralai/Mistral\-7B\-Instruct\-v0\.3 |
| Name | Mistral\-7B\-Instruct\-v0\.3 |
| Developed by | mistralai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-22 \(Hugging Face repository creation date\) |
| Version | c170c708c41dac9275d15a8fff4eca08d52bab71 |
| Summary | An instruct fine\-tuned large language model based on Mistral\-7B\-v0\.3\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | mistralai/Mistral\-7B\-v0\.3 (base model; Kind: finetune) |
| Model family | Mistral v0\.3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,248,023,552 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.0 GiB of safetensors weights \(28,992,159,440 bytes\) in BF16 |
| Input / output | text input<br>text output |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 2,648,636 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 2,835 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer presents the model as a demonstration that the base model can be fine\-tuned to achieve compelling performance\. |
| Safety evaluations | The developer states that the model does not have any moderation mechanisms\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/mistralai/Mistral\-7B\-Instruct\-v0\.3](<https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3>) |
| Code repository | [https://github\.com/mistralai/mistral\-inference](<https://github.com/mistralai/mistral-inference>) |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
