# Model Card: ECE\-PRYMMAL\-YL\-6B\-SLERP\-V2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [ece\-prymmal\-yl\-6b\-slerp\-v2\.json](<./ece-prymmal-yl-6b-slerp-v2.json>)<br>
SHA-256: `e078eb8c58b4edbf6516a6abfc1bc1ec7aa49d27fd162d1fe37110ef60d7f50c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | lalainy/ECE\-PRYMMAL\-YL\-6B\-SLERP\-V2 |
| Name | ECE\-PRYMMAL\-YL\-6B\-SLERP\-V2 |
| Developed by | lalainy \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-11\-09 \(Hugging Face repository creation date\) |
| Version | 18d282d0206ae8f878a9cfa80ce4eaf042056569 |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 6,061,035,520 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 22\.6 GiB of safetensors weights \(24,244,175,656 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 28 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/lalainy/ECE\-PRYMMAL\-YL\-6B\-SLERP\-V2](<https://huggingface.co/lalainy/ECE-PRYMMAL-YL-6B-SLERP-V2>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | dense 6B decoder\-only model with open weights and no reported training/evaluation details; training and inference of such a model plausibly has carbon/water costs | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
