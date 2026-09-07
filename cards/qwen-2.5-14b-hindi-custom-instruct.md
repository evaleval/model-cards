# Model Card: Qwen\-2\.5\-14B\-Hindi\-Custom\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen\-2\.5\-14b\-hindi\-custom\-instruct\.json](<./qwen-2.5-14b-hindi-custom-instruct.json>)<br>
SHA-256: `4f17e56981e953b30f2b74643d8b208bab4aef99ca04e131482961d5681a278e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 1\-800\-LLMs/Qwen\-2\.5\-14B\-Hindi\-Custom\-Instruct |
| Name | Qwen\-2\.5\-14B\-Hindi\-Custom\-Instruct |
| Developed by | 1\-800\-LLMs \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-02\-05 \(Hugging Face repository creation date\) |
| Version | 05b8099d33cc43eb065ab4aadb13c5362e1c3cbe |

## Lineage

| Field | Value |
| --- | --- |
| Base models | unsloth/Qwen2\.5\-14B (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 14,770,033,664 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,540,133,960 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 0 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/1\-800\-LLMs/Qwen\-2\.5\-14B\-Hindi\-Custom\-Instruct](<https://huggingface.co/1-800-LLMs/Qwen-2.5-14B-Hindi-Custom-Instruct>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card summary provides only model identity, modalities, gated access, and license; no design, development, or evaluation details are stated for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card summary does not document training or tuning dataset details for Qwen\-2\.5\-14B\-Hindi\-Custom\-Instruct\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card summary does not state intended use or target task for this Hindi custom instruct model, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
