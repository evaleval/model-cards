# Model Card: alpaca\_data\_sampled\_ifd\_5200

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [alpaca\_data\_sampled\_ifd\_5200\.json](<./alpaca_data_sampled_ifd_5200.json>)<br>
SHA-256: `ade948043cfae88b2291f03552608f85957628f422d18340cbdc8b02aa1bd78f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | godlikehhd/alpaca\_data\_sampled\_ifd\_5200 |
| Name | alpaca\_data\_sampled\_ifd\_5200 |
| Developed by | godlikehhd \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-09 \(Hugging Face repository creation date\) |
| Version | 744dc68050671f42b110bc322f0ef4d71549f067 |
| Summary | A test model for OpenLLM, trained from Qwen 2\.5 1\.5B\. |

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

| Field | Value |
| --- | --- |
| Adaptations | This model is a fine\-tune of Qwen 2\.5 1\.5B\. |

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
| Model card | [https://huggingface\.co/godlikehhd/alpaca\_data\_sampled\_ifd\_5200](<https://huggingface.co/godlikehhd/alpaca_data_sampled_ifd_5200>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card names only 'alpaca\_data\_sampled\_ifd\_5200' as training data and gives no dataset documentation, so training\-data details are not transparent\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The checkpoint is a fine\-tune of Qwen 2\.5 1\.5B on a sampled/IFD subset of alpaca data, but the card does not document the origin, transformations, or usage terms of that sampled data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Fine\-tuning on a sampled subset of alpaca data can inherit or amplify biases from that data, and the card reports no bias analysis for this checkpoint\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Training on a 5200\-sample subset of alpaca data may not represent the full distribution of real\-world instructions, and the card reports no evaluation showing generalization\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
