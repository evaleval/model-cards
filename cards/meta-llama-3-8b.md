# Model Card: Meta\-Llama\-3\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [meta\-llama\-3\-8b\.json](<./meta-llama-3-8b.json>)<br>
SHA-256: `197bbeed83d872670ae63235548f981e697c22f3a998cb50adfadae84dda46cd`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Meta\-Llama\-3\-8B |
| Name | Meta\-Llama\-3\-8B |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3 |
| Release date | 2024\-04\-17 \(Hugging Face repository creation date\) |
| Version | 8cde5ca8380496c9a6cc7ef3a8b46a0372a1d920 |
| Summary | A generative text model in the Meta Llama 3 family, released in 8B and 70B sizes\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Meta Llama 3 |

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
| Training data | The model was trained on a new mix of publicly available online data\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 373,775 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 6,644 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The developer states that care was taken during model development to optimize both helpfulness and safety\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Meta\-Llama\-3\-8B](<https://huggingface.co/meta-llama/Meta-Llama-3-8B>) |
| Code repository | [https://github\.com/meta\-llama/llama3](<https://github.com/meta-llama/llama3>) |
| Citation | @article\{llama3modelcard,<br><br>  title=\{Llama 3 Model Card\},<br><br>  author=\{AI@Meta\},<br><br>  year=\{2024\},<br><br>  url = \{https://github\.com/meta\-llama/llama3/blob/main/MODEL\_CARD\.md\}<br><br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only a brief description of training data as &\#x27;a new mix of publicly available online data&\#x27; and no details on model design, development, or evaluation process, so the checkpoint lacks transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card does not document training dataset details beyond &\#x27;a new mix of publicly available online data&\#x27;, so training/tuning dataset details are insufficiently documented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data is described only as &\#x27;publicly available online data&\#x27; with no traceability of ownership, origin, or transformations, so data provenance is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the training data is an undisclosed mix of public online data, the content used to generate outputs is not accessible or attributable\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card does not state intended use or use restrictions beyond a gated access and license, so the model&\#x27;s intended use is incomplete for defining relevant risks\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`.
