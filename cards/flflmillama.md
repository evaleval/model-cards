# Model Card: flflmillama

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [flflmillama\.json](<./flflmillama.json>)<br>
SHA-256: `fbe50cc466d6d8393d52ccce9c9a110fb7f3f17047759a976c4f9c1358e68d16`

## Identity

| Field | Value |
| --- | --- |
| Model ID | sumink/flflmillama |
| Name | flflmillama |
| Developed by | sumink \(Hub organization\) |
| Release date | 2025\-02\-05 \(Hugging Face repository creation date\) |
| Version | e6e15070ab0783d5d75f6a67a57b26d86c989079 |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,212,749,824 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 6\.0 GiB of safetensors weights \(6,425,529,048 bytes\) in BF16 |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The fine\-tuned model was trained on a final dataset of 500 samples refined through FL and FLMI techniques\. |
| Training data size | 500 samples |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 13 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/sumink/flflmillama](<https://huggingface.co/sumink/flflmillama>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `specifications.input_output`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
