# Model Card: frqwen2\.5\-from7b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [frqwen2\.5\-from7b\-it\.json](<./frqwen2.5-from7b-it.json>)<br>
SHA-256: `3bd1abfba097f5191ce4d20b075ee17223de031cabc6f73919d6436d2144c217`

## Identity

| Field | Value |
| --- | --- |
| Model ID | ehristoforu/frqwen2\.5\-from7b\-it |
| Name | frqwen2\.5\-from7b\-it |
| Developed by | ehristoforu \(Hub organization\) |
| Release date | 2025\-01\-17 \(Hugging Face repository creation date\) |
| Version | b8ebb360a763020f3bf0bbf0115e42a9d325b7e0 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B\-Instruct (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 13,206,143,488 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 24\.6 GiB of safetensors weights \(26,412,358,848 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a merge created with the passthrough merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 21 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/ehristoforu/frqwen2\.5\-from7b\-it](<https://huggingface.co/ehristoforu/frqwen2.5-from7b-it>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states architecture, modality, and merge method; no training data, evaluation, or intended\-use details are reported for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card gives no intended or non\-intended use for this merged instruct model, so downstream risk scope is undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document the datasets used for the base model or the merge, leaving training/tuning data details absent\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
