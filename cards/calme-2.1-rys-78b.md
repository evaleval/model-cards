# Model Card: MaziyarPanahi/calme\-2\.1\-rys\-78b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [calme\-2\.1\-rys\-78b\.json](<./calme-2.1-rys-78b.json>)<br>
SHA-256: `88150c557bb1d9a0fd69035eddf32e70de92f007c43b94e6ec8f013a3268adbe`

## Identity

| Field | Value |
| --- | --- |
| Model ID | MaziyarPanahi/calme\-2\.1\-rys\-78b |
| Name | MaziyarPanahi/calme\-2\.1\-rys\-78b |
| Developed by | MaziyarPanahi \(Hub organization\) |
| Model type | text\-generation |
| License | mit |
| Release date | 2024\-08\-06 \(Hugging Face repository creation date\) |
| Version | 86f5e80c4e26a86107619d3738b2e43b1188128e |
| Summary | A fine\-tuned version of dnhkng/RYS\-XLarge aimed at advancing natural language understanding and generation\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | dnhkng/RYS\-XLarge (base model; Kind: finetune) |
| Model family | calme 2\.1 rys |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 77,965,463,552 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 290\.4 GiB of safetensors weights \(311,861,973,696 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The fine\-tune was trained on the MaziyarPanahi/truthy\-dpo\-v0\.1\-axolotl dataset\. |
| Adaptations | The model is a fine\-tuned version of dnhkng/RYS\-XLarge\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 30 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 3 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/MaziyarPanahi/calme\-2\.1\-rys\-78b](<https://huggingface.co/MaziyarPanahi/calme-2.1-rys-78b>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, base model, and dataset name; no evaluation results, training details, or data documentation are provided\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card names the fine\-tuning dataset but does not describe how it was collected, curated, or processed\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card identifies the dataset only by name and does not provide traceability of its origin, ownership, or generation process\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only a broad &\#x27;text\-generation&\#x27; task and does not define intended or non\-intended use cases\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
