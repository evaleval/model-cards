# Model Card: Ice0\.27\-06\.11\-RP

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [ice0\.27\-06\.11\-rp\.json](<./ice0.27-06.11-rp.json>)<br>
SHA-256: `4a40c5dabcf556ad94fadcbb0c820cec574d29b70e4bdbfe09b41e185ff65c66`

## Identity

| Field | Value |
| --- | --- |
| Model ID | icefog72/Ice0\.27\-06\.11\-RP |
| Name | Ice0\.27\-06\.11\-RP |
| Developed by | icefog72 \(Hub organization\) |
| Release date | 2024\-11\-06 \(Hugging Face repository creation date\) |
| Version | f2c78e71b59e0d36475217e3f265bc135f7c8505 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Ice0\.27 06\.11 RP |

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
| Adaptations | The model is a merge created with the SLERP merge method\. The merge included the models Ice0\.15\-06\.11\-RP\-orpo and IceSakeV12\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/icefog72/Ice0\.27\-06\.11\-RP](<https://huggingface.co/icefog72/Ice0.27-06.11-RP>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
