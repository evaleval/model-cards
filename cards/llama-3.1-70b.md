# Model Card: Llama\-3\.1\-70B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-70b\.json](<./llama-3.1-70b.json>)<br>
SHA-256: `905346ef1521f0dbae06ada31a49e9fb3bea92d36390920b2ee66010dd222bcd`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.1\-70B |
| Name | Llama\-3\.1\-70B |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3\.1 |
| Release date | 2024\-07\-14 \(Hugging Face repository creation date\) |
| Version | 349b2ddb53ce8f2849a6c168a81980ab25258dac |
| Summary | A multilingual instruction\-tuned text\-only model optimized for dialogue and reported to outperform many open and closed chat models on common industry benchmarks\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama 3\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 70,553,706,496 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 131\.4 GiB of safetensors weights \(141,107,497,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint was trained on a new mix of publicly available online data\. |
| Data cutoff | December 2023 |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 44,557 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 437 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that the instruction\-tuned text\-only Llama 3\.1 models, including the 70B variant, are optimized for multilingual dialogue and outperform many open\-source and closed chat models on common industry benchmarks\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.1\-70B](<https://huggingface.co/meta-llama/Llama-3.1-70B>) |
| Code repository | [https://github\.com/meta\-llama/llama3](<https://github.com/meta-llama/llama3>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark claims and a generic &\#x27;new mix of publicly available online data&\#x27; with no design, development, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card states training data only as &\#x27;a new mix of publicly available online data&\#x27; with no dataset composition, curation, or filtering details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | Training data is not released or described in detail, so explanations of model behavior based on training data are limited\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card only says &\#x27;publicly available online data&\#x27; without documenting sources, ownership, or usage terms, making provenance hard to verify\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
