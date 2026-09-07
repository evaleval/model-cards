# Model Card: vicuna\-7b\-v1\.5

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [vicuna\-7b\-v1\.5\.json](<./vicuna-7b-v1.5.json>)<br>
SHA-256: `615d3d9928da85dd0d99cf03bd1c483b81b133f9b95ac9460c3ee721be6ac620`

## Identity

| Field | Value |
| --- | --- |
| Model ID | lmsys/vicuna\-7b\-v1\.5 |
| Name | vicuna\-7b\-v1\.5 |
| Developed by | lmsys \(Hub organization\) |
| License | llama2 |
| Release date | 2023\-07\-29 \(Hugging Face repository creation date\) |
| Version | 3321f76e3f527bd14065daf69dad9344000a201d |

## Lineage

| Field | Value |
| --- | --- |
| Model family | vicuna v1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 35,147 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 402 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/lmsys/vicuna\-7b\-v1\.5](<https://huggingface.co/lmsys/vicuna-7b-v1.5>) |
| Code repository | [https://github\.com/lm\-sys/FastChat](<https://github.com/lm-sys/FastChat>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | open\-weight checkpoint card provides only architecture and license, with no reported training data, evaluation, or safety documentation | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.num_parameters`, `specifications.precision`, `specifications.model_size`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
