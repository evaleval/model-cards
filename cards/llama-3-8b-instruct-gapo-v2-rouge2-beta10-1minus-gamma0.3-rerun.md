# Model Card: llama\-3\-8b\-instruct\-gapo\-v2\-rouge2\-beta10\-1minus\-gamma0\.3\-rerun

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\-8b\-instruct\-gapo\-v2\-rouge2\-beta10\-1minus\-gamma0\.3\-rerun\.json](<./llama-3-8b-instruct-gapo-v2-rouge2-beta10-1minus-gamma0.3-rerun.json>)<br>
SHA-256: `0f5683a4fc32b0bcd814c71a0fdd69b5237df388520e783533de4cbb33da3f8e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Jimmy19991222/llama\-3\-8b\-instruct\-gapo\-v2\-rouge2\-beta10\-1minus\-gamma0\.3\-rerun |
| Name | llama\-3\-8b\-instruct\-gapo\-v2\-rouge2\-beta10\-1minus\-gamma0\.3\-rerun |
| Developed by | Jimmy19991222 \(Hub organization\) |
| License | llama3 |
| Release date | 2024\-09\-14 \(Hugging Face repository creation date\) |
| Version | e9692d8dbe30273839763757aa9ef07a5fcf0c59 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Meta\-Llama\-3\-8B\-Instruct (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 19 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Jimmy19991222/llama\-3\-8b\-instruct\-gapo\-v2\-rouge2\-beta10\-1minus\-gamma0\.3\-rerun](<https://huggingface.co/Jimmy19991222/llama-3-8b-instruct-gapo-v2-rouge2-beta10-1minus-gamma0.3-rerun>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, modality, access, and license; no training data, evaluation, or development details are stated for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of testing diversity](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-testing-diversity.html>) | No reported evaluations or testing practices are documented for this checkpoint, so testing diversity cannot be established\. | AI model risks are socio\-technical, so their testing needs input from a broad set of disciplines and diverse testing practices\. |
| [Unrepresentative risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-risk-testing.html>) | No deployment context or evaluation data is described, so any risk testing would be unrepresentative relative to unspecified intended use\. | Testing is unrepresentative when the test inputs are mismatched with the inputs that are expected during deployment\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card does not state intended use or downstream tasks, leaving the relevant risk profile undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe training data collection, curation, or synthetic generation for this checkpoint\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `specifications.model_size`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
