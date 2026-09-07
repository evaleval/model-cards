# Model Card: Ice0\.80\-03\.02\-RP

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [ice0\.80\-03\.02\-rp\.json](<./ice0.80-03.02-rp.json>)<br>
SHA-256: `2624b5b90327f7afd4697609d3c73618aad4ba45c3787a35fd05f9a56b0e7045`

## Identity

| Field | Value |
| --- | --- |
| Model ID | icefog72/Ice0\.80\-03\.02\-RP |
| Name | Ice0\.80\-03\.02\-RP |
| Developed by | icefog72 \(Hub organization\) |
| Release date | 2025\-02\-03 \(Hugging Face repository creation date\) |
| Version | 2aad3cb184adcef0a9d5f1c7a38511c3908bbc29 |
| Summary | A merged language model created with mergekit from pre\-trained language models\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Ice0\.80 03\.02 RP |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,498,032 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of two checkpoints, created using the SLERP merge method\. The merged checkpoints are named Ice0\.77\-02\.02\-RP and Ice0\.79\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/icefog72/Ice0\.80\-03\.02\-RP](<https://huggingface.co/icefog72/Ice0.80-03.02-RP>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
