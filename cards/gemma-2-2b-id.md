# Model Card: gemma\-2\-2b\-id

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-2\-2b\-id\.json](<./gemma-2-2b-id.json>)<br>
SHA-256: `04c9bfaf19937cd11148c4e267805e51b802704149b7abd563b44594cfd1d214`

## Identity

| Field | Value |
| --- | --- |
| Model ID | dwikitheduck/gemma\-2\-2b\-id |
| Name | gemma\-2\-2b\-id |
| Developed by | dwikitheduck \(Hub organization\) |
| License | gemma |
| Release date | 2024\-10\-24 \(Hugging Face repository creation date\) |
| Version | 1c046ade199128da926004e154698546d65e3084 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma 2 id |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Model size | 4\.9 GiB of safetensors weights \(5,228,717,200 bytes\) |
| Input / output | text in, text out |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint was trained on a 9\-million\-token Indonesian Alpaca dataset\. |
| Training data size | 9 million tokens |
| Adaptations | The model was produced by supervised fine\-tuning on an Indonesian Alpaca dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 31 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/dwikitheduck/gemma\-2\-2b\-id](<https://huggingface.co/dwikitheduck/gemma-2-2b-id>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Trained only on a 9\-million\-token Indonesian Alpaca dataset, which is a narrow synthetic/instruction dataset and may not represent the broader Indonesian language distribution or real\-world use\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Improper data curation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-curation.html>) | The card states only supervised fine\-tuning on an Indonesian Alpaca dataset with no reported curation or quality checks, so label errors or conflicting information in that dataset are plausible\. | Improper collection, generation, and preparation of training or tuning data can result in data label errors, conflicting information or misinformation\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card names the dataset as 'Indonesian Alpaca' but gives no source, ownership, or generation details, so the provenance of the tuning data is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Fine\-tuning on a small Indonesian Alpaca dataset can inherit or amplify biases present in that dataset, and no bias evaluation is reported\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card does not document how the Indonesian Alpaca dataset was collected, curated, or generated, so training\-data details are insufficient\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.num_parameters`, `specifications.precision`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
