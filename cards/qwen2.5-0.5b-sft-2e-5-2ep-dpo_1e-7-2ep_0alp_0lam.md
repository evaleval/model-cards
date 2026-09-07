# Model Card: Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPO\_1e\-7\-2ep\_0alp\_0lam

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-0\.5b\-sft\-2e\-5\-2ep\-dpo\_1e\-7\-2ep\_0alp\_0lam\.json](<./qwen2.5-0.5b-sft-2e-5-2ep-dpo_1e-7-2ep_0alp_0lam.json>)<br>
SHA-256: `57cb3c2d23e6ad26855dd55cdf4da9b4433743d5b7d75eaba8de782de488c4d2`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPO\_1e\-7\-2ep\_0alp\_0lam |
| Name | Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPO\_1e\-7\-2ep\_0alp\_0lam |
| Developed by | JayHyeon \(Hub organization\) |
| Release date | 2025\-01\-06 \(Hugging Face repository creation date\) |
| Version | 338a87eaf84f8f843abfc765fa761f4aadfa650d |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 494,032,768 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 1\.8 GiB of safetensors weights \(1,976,161,736 bytes\) in F32 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 11 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPO\_1e\-7\-2ep\_0alp\_0lam](<https://huggingface.co/JayHyeon/Qwen2.5-0.5B-SFT-2e-5-2ep-DPO_1e-7-2ep_0alp_0lam>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card summary provides only the model name and architecture, with no documentation of design, development, or evaluation process, so the checkpoint itself lacks transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card summary does not state how the training/fine\-tuning data was collected, curated, or used, so training data transparency is lacking for this checkpoint\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card summary gives no intended\-use or misuse definition for this checkpoint, so downstream usage risks are undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
