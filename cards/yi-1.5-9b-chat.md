# Model Card: Yi\-1\.5\-9B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [yi\-1\.5\-9b\-chat\.json](<./yi-1.5-9b-chat.json>)<br>
SHA-256: `9cccf14b5a08d09b89bcfa3cd56b09c8ac19ca2f185cc9d3d09260e2f81b8ded`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 01\-ai/Yi\-1\.5\-9B\-Chat |
| Name | Yi\-1\.5\-9B\-Chat |
| Developed by | 01\-ai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-10 \(Hugging Face repository creation date\) |
| Version | 1a0fc698cf883c4f5c325f026ca79f0ebd9955a5 |
| Summary | Yi\-1\.5 is an upgraded version of Yi\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Yi\-1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,829,407,232 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 16\.4 GiB of safetensors weights \(17,658,864,984 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 16,227 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 149 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Yi\-1\.5\-9B\-Chat achieves the best results among open\-source models of comparable size\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/01\-ai/Yi\-1\.5\-9B\-Chat](<https://huggingface.co/01-ai/Yi-1.5-9B-Chat>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark claim and license, with no documentation of design, development, or evaluation process for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not state intended use or usage restrictions for this open\-weight chat model, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe training data collection, curation, or use for Yi\-1\.5\-9B\-Chat, so training data transparency is lacking\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
