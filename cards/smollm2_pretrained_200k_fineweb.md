# Model Card: smollm2\_pretrained\_200k\_fineweb

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\_pretrained\_200k\_fineweb\.json](<./smollm2_pretrained_200k_fineweb.json>)<br>
SHA-256: `84a4dcd9defa581d9c4295f01e59f3651c726eb39d685f9dd391b7253076c703`

## Identity

| Field | Value |
| --- | --- |
| Model ID | FlofloB/smollm2\_pretrained\_200k\_fineweb |
| Name | smollm2\_pretrained\_200k\_fineweb |
| Developed by | FlofloB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-08 \(Hugging Face repository creation date\) |
| Version | c3086ab3555e766f0b3903b8b9a1a290e3e25f3d |

## Lineage

| Field | Value |
| --- | --- |
| Base models | HuggingFaceTB/SmolLM2\-135M (base model; Kind: finetune) |
| Model family | smollm2 pretrained 200k fineweb |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 134,515,008 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 0\.5 GiB of safetensors weights \(538,090,408 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a pre\-trained version of HuggingFaceTB/SmolLM2\-135M, trained on the first 200,000 samples from the Fineweb dataset dump CC\-MAIN\-2024\-18\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/FlofloB/smollm2\_pretrained\_200k\_fineweb](<https://huggingface.co/FlofloB/smollm2_pretrained_200k_fineweb>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card states the model was trained on the first 200,000 samples from a Fineweb dump \(CC\-MAIN\-2024\-18\), but gives no provenance details or verification of the source/usage terms for those samples\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card names the dataset and sample count but does not document collection, curation, filtering, or preprocessing details for the 200,000 Fineweb samples\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card provides no information about how the Fineweb samples were collected, curated, or used to train this checkpoint, making model behavior harder to explain\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Training on only the first 200,000 samples from one Fineweb dump may not represent the broader population or the full diversity of the source corpus, potentially limiting generalization\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
