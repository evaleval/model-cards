# Model Card: MaziyarPanahi/calme\-2\.3\-llama3\-70b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [calme\-2\.3\-llama3\-70b\.json](<./calme-2.3-llama3-70b.json>)<br>
SHA-256: `e55f5a447b5479e48d80d4f7695230ffea79f1c012cd805fca1933829e5f37e4`

## Identity

| Field | Value |
| --- | --- |
| Model ID | MaziyarPanahi/calme\-2\.3\-llama3\-70b |
| Name | MaziyarPanahi/calme\-2\.3\-llama3\-70b |
| Developed by | MaziyarPanahi \(Hub organization\) |
| Model type | text\-generation |
| License | llama3 |
| Release date | 2024\-04\-27 \(Hugging Face repository creation date\) |
| Version | bd17453eaae0e36d1e1e17da13fdd155fce91a29 |
| Summary | A DPO fine\-tune of Meta\-Llama\-3\-70B\-Instruct for text generation\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Meta\-Llama\-3\-70B\-Instruct (base model; Kind: finetune) |
| Model family | calme 2\.3 llama3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 70,553,722,880 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 131\.4 GiB of safetensors weights \(141,107,530,640 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on the MaziyarPanahi/truthy\-dpo\-v0\.1\-axolotl dataset\. |
| Adaptations | This model is a DPO fine\-tune of meta\-llama/Meta\-Llama\-3\-70B\-Instruct\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 37 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/MaziyarPanahi/calme\-2\.3\-llama3\-70b](<https://huggingface.co/MaziyarPanahi/calme-2.3-llama3-70b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, task, and training dataset name; no reported evaluations, training\-data details, or development/evaluation process for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data is named as MaziyarPanahi/truthy\-dpo\-v0\.1\-axolotl but the card gives no origin, ownership, curation, or verification details for that dataset\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe how the training data was collected, curated, or used beyond naming the dataset, limiting explainability of model behavior\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
