# Model Card: Meta\-Llama\-3\-70B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [meta\-llama\-3\-70b\.json](<./meta-llama-3-70b.json>)<br>
SHA-256: `ec2065412142bd5c45ba461c1229f932e314126603a0cf6c41bb5e9bfc7f2097`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Meta\-Llama\-3\-70B |
| Name | Meta\-Llama\-3\-70B |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3 |
| Release date | 2024\-04\-17 \(Hugging Face repository creation date\) |
| Version | c82494877ce7f6d7d317c56ec081328e382c72fe |

## Lineage

| Field | Value |
| --- | --- |
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
| Downloads | 121,609 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 879 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The developer states that care was taken to optimize helpfulness and safety during model development\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Meta\-Llama\-3\-70B](<https://huggingface.co/meta-llama/Meta-Llama-3-70B>) |
| Code repository | [https://github\.com/meta\-llama/llama3](<https://github.com/meta-llama/llama3>) |
| Citation | @article\{llama3modelcard,<br><br>  title=\{Llama 3 Model Card\},<br><br>  author=\{AI@Meta\},<br><br>  year=\{2024\},<br><br>  url = \{https://github\.com/meta\-llama/llama3/blob/main/MODEL\_CARD\.md\}<br><br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only a vague statement that care was taken to optimize helpfulness and safety, with no details on design, development, or evaluation process for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Training data is described only as &\#x27;a new mix of publicly available online data&\#x27; with no dataset details, curation, or composition information\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The summary does not provide traceability or verification of the online data sources, ownership, or usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card does not state intended or out\-of\-scope uses for this checkpoint, leaving downstream risk assessment underspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`.
