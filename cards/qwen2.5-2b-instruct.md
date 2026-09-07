# Model Card: Qwen2\.5\-2B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-2b\-instruct\.json](<./qwen2.5-2b-instruct.json>)<br>
SHA-256: `e843540b251cc989fb3f87c6b54e59037b3ca70d1b407b0610a3ae0bd4627828`

## Identity

| Field | Value |
| --- | --- |
| Model ID | win10/Qwen2\.5\-2B\-Instruct |
| Name | Qwen2\.5\-2B\-Instruct |
| Developed by | win10 \(Hub organization\) |
| Release date | 2024\-10\-11 \(Hugging Face repository creation date\) |
| Version | 6cc7fca3447d50772978d2d7dec255abdc73d54b |
| Summary | The model is a merge of several models created with LazyMergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-1\.5B\-Instruct (base model; Kind: finetune) |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 2,900,235,776 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 5\.4 GiB of safetensors weights \(5,800,542,152 bytes\) in BF16 |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a merge of other models, created using LazyMergekit\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 23 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/win10/Qwen2\.5\-2B\-Instruct](<https://huggingface.co/win10/Qwen2.5-2B-Instruct>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states the model is a merge created with LazyMergekit and gives no training data, evaluation, or development details, so the checkpoint itself lacks transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not document how the merged model&\#x27;s training data was collected, curated, or used, so training data transparency is lacking for this checkpoint\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Lack of testing diversity](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-testing-diversity.html>) | The card reports no evaluations or testing practices for this merged checkpoint, so there is no evidence of diverse socio\-technical testing\. | AI model risks are socio\-technical, so their testing needs input from a broad set of disciplines and diverse testing practices\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or usage definition for this merged model, leaving downstream risk assessment underspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
