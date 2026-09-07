# Model Card: L3\-70B\-Euryale\-v2\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [l3\-70b\-euryale\-v2\.1\.json](<./l3-70b-euryale-v2.1.json>)<br>
SHA-256: `7bc0e12ddd83df581cda1aab8f57f022fbad4e5e360ae0051c994cea8d346dd8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Sao10K/L3\-70B\-Euryale\-v2\.1 |
| Name | L3\-70B\-Euryale\-v2\.1 |
| Developed by | Sao10K \(Hub organization\) |
| License | cc\-by\-nc\-4\.0 |
| Release date | 2024\-06\-11 \(Hugging Face repository creation date\) |
| Version | 36ad832b771cd783ea7ad00ed39e61f679b1a7c6 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | L3 Euryale v2\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 70,553,706,496 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 131\.4 GiB of safetensors weights \(141,107,497,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a LoRA fine\-tune rather than a full fine\-tune, and training was performed on 8x H100 SXMs with additional training afterward\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 219 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 169 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports improved prompt adherence, better anatomy and spatial awareness, and stronger adaptation to custom reply formats\. The model is described as highly creative with many unique responses and non\-restrictive during roleplays\. |
| Human evaluations | Developer\-reported qualitative evaluations highlight better prompt adherence, improved anatomy and spatial awareness, and better adaptation to unique or custom formatting\. The model is also described as very creative with many unique swipes and not restrictive during roleplays\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Sao10K/L3\-70B\-Euryale\-v2\.1](<https://huggingface.co/Sao10K/L3-70B-Euryale-v2.1>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only qualitative developer evaluations and no dataset, training\-data, or evaluation details for this LoRA checkpoint, so design/evaluation transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document the training or fine\-tuning dataset for this LoRA, leaving tuning data details undisclosed\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | No information is provided about the provenance, ownership, or usage terms of the LoRA training data, making traceability uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | The card emphasizes non\-restrictive roleplay and creative outputs but reports no bias evaluation or dataset mitigation, so biases in the fine\-tuning data are plausible\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | Open\-weight LoRA with cc\-by\-nc\-4\.0 and non\-restrictive roleplay focus may be used outside intended/legal noncommercial or safety\-reviewed contexts\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
