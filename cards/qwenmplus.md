# Model Card: Qwenmplus

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwenmplus\.json](<./qwenmplus.json>)<br>
SHA-256: `eb3d72d7b23c5b2c3398c5a78b7d44941ebdac3d4a0198cb24c12b754348e75c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | sumink/Qwenmplus |
| Name | Qwenmplus |
| Developed by | sumink \(Hub organization\) |
| License | other |
| Release date | 2025\-01\-03 \(Hugging Face repository creation date\) |
| Version | 2f6d29692e18a32bc179e81d09d4ecdefefb85d8 |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,543,299,584 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 5\.7 GiB of safetensors weights \(6,173,236,544 bytes\) in F32 |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on a custom dataset named subset5, containing prompt\-response pairs that include diverse mathematical problems and solutions as well as general prompt\-response pairs, with tokenization up to a maximum sequence length of 128 tokens\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 11 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer provides example input\-output pairs that illustrate the model generating concise, informative answers, including accurate mathematical problem solving\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/sumink/Qwenmplus](<https://huggingface.co/sumink/Qwenmplus>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
