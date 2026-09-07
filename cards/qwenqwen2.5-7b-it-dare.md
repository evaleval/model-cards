# Model Card: QwenQwen2\.5\-7B\-IT\-Dare

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwenqwen2\.5\-7b\-it\-dare\.json](<./qwenqwen2.5-7b-it-dare.json>)<br>
SHA-256: `24627b61fb29cd2e32e6efc9e047bb7fd183c898e62f3d8d525e8e7caaad065c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | ehristoforu/QwenQwen2\.5\-7B\-IT\-Dare |
| Name | QwenQwen2\.5\-7B\-IT\-Dare |
| Developed by | ehristoforu \(Hub organization\) |
| Release date | 2025\-01\-29 \(Hugging Face repository creation date\) |
| Version | 376d1c82e6fd973fb927f8540535d39e8f4c6168 |
| Summary | A merged language model created with mergekit, combining pre\-trained models\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B\-Instruct (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,612,756,480 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,225,551,456 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a merge of multiple models, produced using the DARE TIES merge method with Qwen/Qwen2\.5\-7B\-Instruct as the base\. |
| Adaptations | The model was merged using the DARE TIES merge method, with Qwen/Qwen2\.5\-7B\-Instruct as the base model\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 14 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/ehristoforu/QwenQwen2\.5\-7B\-IT\-Dare](<https://huggingface.co/ehristoforu/QwenQwen2.5-7B-IT-Dare>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only merge recipe \(DARE TIES, base Qwen/Qwen2\.5\-7B\-Instruct\) and no evaluation or training\-data details for this checkpoint, so inner workings and development/evaluation process are undocumented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not document how the constituent models&\#x27; training data were collected, curated, or used; it only names the base model and merge method\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | The merged model&\#x27;s training data are not accessible from the card; only the base model name and merge method are given, limiting data\-based explanations of outputs\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the card only states that the model is a DARE TIES merge of multiple pre\-trained models, the content of the training data behind generated outputs is not traceable\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card defines no intended uses or use limitations for this open\-weight text\-in/text\-out model, so relevant risks cannot be scoped to a specific deployment\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
