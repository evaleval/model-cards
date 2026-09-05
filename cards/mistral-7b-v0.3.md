# Model Card: Mistral\-7B\-v0\.3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-7b\-v0\.3\.json](<./mistral-7b-v0.3.json>)<br>
SHA-256: `34077fb1d837061e84f501b1fd49d4759c35ab0cd208641ab28d9199c25eeb25`

## Identity

| Field | Value |
| --- | --- |
| Model ID | mistralai/Mistral\-7B\-v0\.3 |
| Name | Mistral\-7B\-v0\.3 |
| Developed by | mistralai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-22 \(Hugging Face repository creation date\) |
| Version | caa1feb0e54d415e2df31207e5f4e273e33509b1 |
| Summary | Mistral\-7B\-v0\.3 is a large language model based on Mistral\-7B\-v0\.2 with an extended vocabulary\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Mistral v0\.3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,248,023,552 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.0 GiB of safetensors weights \(28,992,159,440 bytes\) in BF16 |
| Input / output | Text input<br>Text output |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | Mistral\-7B\-v0\.3 extends the vocabulary of Mistral\-7B\-v0\.2 to 32,768 tokens\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 130,279 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 592 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/mistralai/Mistral\-7B\-v0\.3](<https://huggingface.co/mistralai/Mistral-7B-v0.3>) |
| Code repository | [https://github\.com/mistralai/mistral\-inference](<https://github.com/mistralai/mistral-inference>) |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
