# Model Card: Meta\-Llama\-3\-70B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [meta\-llama\-3\-70b\-instruct\.json](<./meta-llama-3-70b-instruct.json>)<br>
SHA-256: `06add6362da02a965a4f8a095dee68a16c118f6f8b0d3ed370539486f7f009c2`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Meta\-Llama\-3\-70B\-Instruct |
| Name | Meta\-Llama\-3\-70B\-Instruct |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3 |
| Release date | 2024\-04\-17 \(Hugging Face repository creation date\) |
| Version | 50fd307e57011801c7833c87efa1984ddf2db42f |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Meta\-Llama\-3\-70B (base model; Kind: finetune) |
| Model family | Meta Llama 3 |

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
| Training data | The model was trained on a new mix of publicly available online data\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 57,053 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 1,524 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Meta\-Llama\-3\-70B\-Instruct](<https://huggingface.co/meta-llama/Meta-Llama-3-70B-Instruct>) |
| Code repository | [https://github\.com/meta\-llama/llama3](<https://github.com/meta-llama/llama3>) |
| Citation | @article\{llama3modelcard,<br><br>  title=\{Llama 3 Model Card\},<br><br>  author=\{AI@Meta\},<br><br>  year=\{2024\},<br><br>  url = \{https://github\.com/meta\-llama/llama3/blob/main/MODEL\_CARD\.md\}<br><br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states training on a new mix of publicly available online data with no details on design, development, or evaluation, so documentation is insufficient\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data is described only as a new mix of publicly available online data, with no traceability of sources or usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information is provided about how the online data was collected, curated, or used, making training\-data documentation lacking\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or misuse definition for this instruct model, so relevant risks cannot be scoped\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
