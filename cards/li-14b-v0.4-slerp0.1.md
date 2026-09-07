# Model Card: li\-14b\-v0\.4\-slerp0\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [li\-14b\-v0\.4\-slerp0\.1\.json](<./li-14b-v0.4-slerp0.1.json>)<br>
SHA-256: `9ff2c78c9d58040a184e5ee049cede89cedf3bf841ee3702239318489ec5b262`

## Identity

| Field | Value |
| --- | --- |
| Model ID | wanlige/li\-14b\-v0\.4\-slerp0\.1 |
| Name | li\-14b\-v0\.4\-slerp0\.1 |
| Developed by | wanlige \(Hub organization\) |
| Release date | 2025\-02\-24 \(Hugging Face repository creation date\) |
| Version | 166c1a4f3252150d3a791e5669fa24d49054767e |

## Lineage

| Field | Value |
| --- | --- |
| Base models | sthenno\-com/miscii\-14b\-0218 (base model; Kind: merge)<br>wanlige/li\-14b\-v0\.4 (base model; Kind: merge) |
| Model family | li v0\.4 slerp0\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,765,947,904 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,531,962,384 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge created with the SLERP merge method, combining wanlige/li\-14b\-v0\.4 and sthenno\-com/miscii\-14b\-0218\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 24 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 7 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/wanlige/li\-14b\-v0\.4\-slerp0\.1](<https://huggingface.co/wanlige/li-14b-v0.4-slerp0.1>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, merge method, and base model names; no training/evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Merge of two named 14B models with no stated training data sources or verification of their provenance\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | No documentation of training or tuning dataset details for the merged checkpoint or its components\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | No training data access is provided for the merged model or its base models\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Training data content is not accessible, so outputs cannot be attributed to specific training sources\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
