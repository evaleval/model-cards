# Model Card: Son\-of\-Rhodia

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [son\-of\-rhodia\.json](<./son-of-rhodia.json>)<br>
SHA-256: `7980aadef74b58b1ce5cea0b2a6f7461141c257ecd15c4c9d5d290b4d0433052`

## Identity

| Field | Value |
| --- | --- |
| Model ID | TheDrunkenSnail/Son\-of\-Rhodia |
| Name | Son\-of\-Rhodia |
| Developed by | TheDrunkenSnail \(Hub organization\) |
| License | other |
| Release date | 2024\-12\-31 \(Hugging Face repository creation date\) |
| Version | ec3433a851285073574387b459c4661183ad4dc6 |
| Summary | A merge of pretrained language models created with mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Infermatic/MN\-12B\-Inferor\-v0\.1 (base model; Kind: merge)<br>allura\-org/MN\-12b\-RP\-Ink (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 12,247,782,400 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 22\.8 GiB of safetensors weights \(24,495,607,104 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This checkpoint is a SLERP merge of Infermatic/MN\-12B\-Inferor\-v0\.1 and allura\-org/MN\-12b\-RP\-Ink\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 3 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/TheDrunkenSnail/Son\-of\-Rhodia](<https://huggingface.co/TheDrunkenSnail/Son-of-Rhodia>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only merge recipe and license; no training data, evaluation, or intended\-use details for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not state what data the merged base models were trained on or how it was collected/curated\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not define intended use or downstream tasks for this open\-weight text model, so relevant risks are unspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
