# Model Card: Yi\-1\.5\-34B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [yi\-1\.5\-34b\-chat\.json](<./yi-1.5-34b-chat.json>)<br>
SHA-256: `1d80f1bc419ba34b1c0d8dc245e5717bda638d7e45bdddc6aab2a6cb0adc21c1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 01\-ai/Yi\-1\.5\-34B\-Chat |
| Name | Yi\-1\.5\-34B\-Chat |
| Developed by | 01\-ai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-10 \(Hugging Face repository creation date\) |
| Version | fa4ffba162f20948bf77c2a30eca952bf0812b7f |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 34,388,917,248 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 64\.1 GiB of safetensors weights \(68,777,898,032 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 15,527 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 278 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/01\-ai/Yi\-1\.5\-34B\-Chat](<https://huggingface.co/01-ai/Yi-1.5-34B-Chat>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card summary provides only architecture, modality, access, and license; no design, development, or evaluation details are documented for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card summary does not document training or tuning dataset details for Yi\-1\.5\-34B\-Chat\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card summary identifies the model as a chat model but does not define intended uses, non\-intended uses, or deployment contexts\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
