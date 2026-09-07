# Model Card: Gemma\-Evo\-10B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-evo\-10b\.json](<./gemma-evo-10b.json>)<br>
SHA-256: `25dbabb0fc9f8630e72706e691d94dcd5a88c1a8adaa3e025ecdba8867d7ceb7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Aashraf995/Gemma\-Evo\-10B |
| Name | Gemma\-Evo\-10B |
| Developed by | Aashraf995 \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-12\-13 \(Hugging Face repository creation date\) |
| Version | 5ec9c5763ca6662dd897cd292e08014ec10b0d74 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | gmonsoon/SahabatAI\-Lion\-9B\-TIES\-v1 (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 10,159,209,984 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 18\.9 GiB of safetensors weights \(20,318,474,544 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge created with the Model Stock merge method, using allknowingroger/GemmaSlerp5\-10B as the base and including the listed models in the merge\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 26 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 5 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Aashraf995/Gemma\-Evo\-10B](<https://huggingface.co/Aashraf995/Gemma-Evo-10B>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
