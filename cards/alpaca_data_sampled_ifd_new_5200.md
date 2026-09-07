# Model Card: alpaca\_data\_sampled\_ifd\_new\_5200

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [alpaca\_data\_sampled\_ifd\_new\_5200\.json](<./alpaca_data_sampled_ifd_new_5200.json>)<br>
SHA-256: `0cda447b0cf21680b7002de38a21f64c2597465918f74c4ade11a9135148a822`

## Identity

| Field | Value |
| --- | --- |
| Model ID | godlikehhd/alpaca\_data\_sampled\_ifd\_new\_5200 |
| Name | alpaca\_data\_sampled\_ifd\_new\_5200 |
| Developed by | godlikehhd \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-09 \(Hugging Face repository creation date\) |
| Version | cc169308e13b6a4f030713d9eda4ec005ebf1e16 |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,543,714,304 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.9 GiB of safetensors weights \(3,087,467,144 bytes\) in BF16 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 13 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/godlikehhd/alpaca\_data\_sampled\_ifd\_new\_5200](<https://huggingface.co/godlikehhd/alpaca_data_sampled_ifd_new_5200>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names only 'alpaca\_data\_sampled\_ifd\_new\_5200' and gives no dataset composition, collection, or curation details, so training\-data transparency is lacking\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The checkpoint is open\-weight with Apache\-2\.0, but the card does not document the provenance or usage terms of the underlying alpaca/sampled/IFD data, making traceability uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Improper data curation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-curation.html>) | The name indicates sampled/IFD\-selected alpaca data, but the card provides no curation or label\-quality information, so improper curation cannot be ruled out\. | Improper collection, generation, and preparation of training or tuning data can result in data label errors, conflicting information or misinformation\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Training on a sampled subset of alpaca data may not represent the full distribution of real\-world instructions or domains, potentially limiting generalization\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
