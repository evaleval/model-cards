# Model Card: Yi\-1\.5\-6B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [yi\-1\.5\-6b\-chat\.json](<./yi-1.5-6b-chat.json>)<br>
SHA-256: `f2c89f0bc27aec5d92798a2c6cc03cd54fcc872e0df8eccde9512079ba9b25e6`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 01\-ai/Yi\-1\.5\-6B\-Chat |
| Name | Yi\-1\.5\-6B\-Chat |
| Developed by | 01\-ai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-11 \(Hugging Face repository creation date\) |
| Version | 771924d1c83d67527d665913415d7086f11ea9c0 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Yi\-1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 6,061,035,520 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 11\.3 GiB of safetensors weights \(12,122,104,808 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 4,988 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 42 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/01\-ai/Yi\-1\.5\-6B\-Chat](<https://huggingface.co/01-ai/Yi-1.5-6B-Chat>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card only states architecture, access, license, and family, with no reported training data, evaluation, or safety documentation, so the checkpoint&\#x27;s design and development process is insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe how training data was collected, curated, or used, so training data transparency is lacking for this checkpoint\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or deployment context for this open\-weight chat model, so relevant risks cannot be defined as use changes\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
