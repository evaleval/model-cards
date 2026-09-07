# Model Card: BBAI270V4

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [bbai270v4\.json](<./bbai270v4.json>)<br>
SHA-256: `ee684931a7d7388a8a41c32ecaa72533b7bf31a01dd8cebb3f7cacd7203b18f3`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Amaorynho/BBAI270V4 |
| Name | BBAI270V4 |
| Developed by | Amaorynho \(Hub organization\) |
| Release date | 2025\-02\-26 \(Hugging Face repository creation date\) |
| Version | 8896a9c03756dd01a912121946c9f838cebe3c63 |
| Summary | A merged large language model built from pre\-trained language models using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B (base model; Kind: merge)<br>Qwen/Qwen2\.5\-Math\-7B (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,856 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a SLERP merge of Qwen/Qwen2\.5\-7B and Qwen/Qwen2\.5\-Math\-7B with equal weights, using the Qwen/Qwen2\.5\-7B as the base model and bfloat16 dtype\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen2 outperforms most prior open\-weight models, including Qwen1\.5, and is competitive with proprietary models across diverse benchmarks covering language understanding, generation, multilingual proficiency, coding, mathematics, and reasoning\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Amaorynho/BBAI270V4](<https://huggingface.co/Amaorynho/BBAI270V4>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card only reports that the model is a SLERP merge of Qwen2\.5\-7B and Qwen2\.5\-Math\-7B with equal weights, but provides no evaluation results or design details for this exact checkpoint, so its behavior and development process are insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe the training data used for the merged model or the data curation/collection process for the base models, so training data transparency is lacking\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only that it is a text\-to\-text model and reports generic Qwen2 family results, without defining intended or supported uses for this exact checkpoint, so relevant risks cannot be scoped\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Unrepresentative risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-risk-testing.html>) | The reported results are for the Qwen2 family, not for this exact merged checkpoint, so any risk/performance testing implied by the card is not representative of this model\. | Testing is unrepresentative when the test inputs are mismatched with the inputs that are expected during deployment\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
