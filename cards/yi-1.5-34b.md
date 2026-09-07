# Model Card: Yi\-1\.5\-34B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [yi\-1\.5\-34b\.json](<./yi-1.5-34b.json>)<br>
SHA-256: `f03ab32d47405269230730fdefb19e22c5cd7de367bf4b9da5b0388b1048fb91`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 01\-ai/Yi\-1\.5\-34B |
| Name | Yi\-1\.5\-34B |
| Developed by | 01\-ai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-11 \(Hugging Face repository creation date\) |
| Version | 58a29f6dca2a4eda38821c086c29c1906114aabb |
| Summary | Yi\-1\.5 is an upgraded version of Yi\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Yi\-1\.5 |

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
| Downloads | 9,075 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 50 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Yi\-1\.5\-34B performs comparably to or better than larger models on certain benchmarks\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/01\-ai/Yi\-1\.5\-34B](<https://huggingface.co/01-ai/Yi-1.5-34B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark comparisons and architecture, with no information on training data, development process, or inner workings, so transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe how training data was collected, curated, or used, making it hard to explain model behavior\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only text\-to\-text modality and open\-weight access, without specifying intended or prohibited uses, so relevant risks vary by use\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
