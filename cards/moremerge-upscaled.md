# Model Card: merge

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [moremerge\-upscaled\.json](<./moremerge-upscaled.json>)<br>
SHA-256: `06f6f6a7f83d86b04a5acfc9fd1aeea0d2f9a23c74d702608d15f0fcf5d29b22`

## Identity

| Field | Value |
| --- | --- |
| Model ID | ehristoforu/moremerge\-upscaled |
| Name | merge |
| Developed by | ehristoforu \(Hub organization\) |
| Release date | 2025\-01\-27 \(Hugging Face repository creation date\) |
| Version | 2b50cf76b49db95caee5943e8ecc32237bc59a32 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | ehristoforu/moremerge (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,544,987,648 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.9 GiB of safetensors weights \(17,090,019,616 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge created with the Passthrough merge method, incorporating the model ehristoforu/moremerge\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/ehristoforu/moremerge\-upscaled](<https://huggingface.co/ehristoforu/moremerge-upscaled>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only says &\#x27;merge is a model&\#x27; with architecture and merge method, no design, training, or evaluation details\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training/tuning data for the merge, only names the base model and merge method\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card gives no intended use or task scope, so downstream risk cannot be defined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
