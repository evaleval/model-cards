# Model Card: wide\_3b\_sft\_stage1\.2\-ss1\-expert\_formatted\_text

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [wide\_3b\_sft\_stage1\.2\-ss1\-expert\_formatted\_text\.json](<./wide_3b_sft_stage1.2-ss1-expert_formatted_text.json>)<br>
SHA-256: `353fcf9b2957db92cd11a6f9ec4b117857393141b15d10f8d392de0724a78ea0`

## Identity

| Field | Value |
| --- | --- |
| Model ID | ontocord/wide\_3b\_sft\_stage1\.2\-ss1\-expert\_formatted\_text |
| Name | wide\_3b\_sft\_stage1\.2\-ss1\-expert\_formatted\_text |
| Developed by | ontocord \(Hub organization\) |
| Release date | 2025\-03\-06 \(Hugging Face repository creation date\) |
| Version | 1343c0ad6de8bba0e926a12bc839cdfed9336d2d |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,759,289,344 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 14\.0 GiB of safetensors weights \(15,037,168,640 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 15 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/ontocord/wide\_3b\_sft\_stage1\.2\-ss1\-expert\_formatted\_text](<https://huggingface.co/ontocord/wide_3b_sft_stage1.2-ss1-expert_formatted_text>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card summary provides only architecture and access type, with no reported evaluations, training data, or intended\-use details, so the checkpoint&\#x27;s design and evaluation process are insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card summary does not state an intended use or task for this text\-to\-text model, leaving downstream use and therefore relevant risks undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card summary gives no information about how training data was collected, curated, or generated, making it hard to explain model behavior\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
