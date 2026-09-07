# Model Card: Llama\-3\.1\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-8b\.json](<./llama-3.1-8b.json>)<br>
SHA-256: `501dc43bcb22bd375b0a8ded7b91da8483e51f59e3f2a9317667cc96bd441ced`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.1\-8B |
| Name | Llama\-3\.1\-8B |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3\.1 |
| Release date | 2024\-07\-14 \(Hugging Face repository creation date\) |
| Version | d04e592bb4f6aa9cfee91e2e20afa771667e1d4b |
| Summary | An 8B\-parameter multilingual large language model from the Meta Llama 3\.1 collection, supporting text\-in/text\-out generation\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama 3\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint was trained on a new mix of publicly available online data\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 511,423 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 2,421 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.1\-8B](<https://huggingface.co/meta-llama/Llama-3.1-8B>) |
| Code repository | [https://github\.com/meta\-llama/llama3](<https://github.com/meta-llama/llama3>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture size, modality, and training\-data mix; no design, development, or evaluation details are reported for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Training data is described only as 'a new mix of publicly available online data' with no dataset details, curation, or documentation\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card does not provide traceability or source verification for the 'publicly available online data' mix, so data origin and usage terms are uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data usage rights restrictions](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-usage-rights.html>) | Because the training data is only broadly described as publicly available online data, the card does not establish license or terms\-of\-service compliance for that data\. | Terms of service, license compliance, or other IP issues may restrict the ability to use certain data for building models\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
