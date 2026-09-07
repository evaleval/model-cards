# Model Card: Llama\-3\-Instruct\-8B\-ORPO\-v0\.2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\-instruct\-8b\-orpo\-v0\.2\.json](<./llama-3-instruct-8b-orpo-v0.2.json>)<br>
SHA-256: `3282c129b8f207ecd77cee7d8d801495fb2cb2171474792d4daff2b331da392b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | princeton\-nlp/Llama\-3\-Instruct\-8B\-ORPO\-v0\.2 |
| Name | Llama\-3\-Instruct\-8B\-ORPO\-v0\.2 |
| Developed by | princeton\-nlp \(Hub organization\) |
| Release date | 2024\-07\-06 \(Hugging Face repository creation date\) |
| Version | 9d66325f094b578a7cbfcd4a8e3ddd2625129650 |
| Summary | A model released alongside the SimPO preprint, which introduces Simple Preference Optimization with a Reference\-Free Reward\. |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 40 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/princeton\-nlp/Llama\-3\-Instruct\-8B\-ORPO\-v0\.2](<https://huggingface.co/princeton-nlp/Llama-3-Instruct-8B-ORPO-v0.2>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture/access and the SimPO preprint name; no training data, evaluation, or design details are documented for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not state how the model&\#x27;s training/fine\-tuning data was collected or curated, so training data transparency is lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not define intended use or deployment context, leaving downstream risk scope unspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
