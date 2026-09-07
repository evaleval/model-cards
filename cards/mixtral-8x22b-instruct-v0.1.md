# Model Card: Mixtral\-8x22B\-Instruct\-v0\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mixtral\-8x22b\-instruct\-v0\.1\.json](<./mixtral-8x22b-instruct-v0.1.json>)<br>
SHA-256: `7c2b0a8c5f6a244c98a4579fd832e02c63bf071d86f35f1ca91a596d5cf73cad`

## Identity

| Field | Value |
| --- | --- |
| Model ID | mistralai/mixtral\-8x22b\-instruct\-v0\.1 |
| Name | Mixtral\-8x22B\-Instruct\-v0\.1 |
| Developed by | mistralai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-04\-16 \(Hugging Face repository creation date\) |
| Version | cc88a6cc19fbd17d9f1c0ee0b0d70a748dce698d |

## Lineage

| Field | Value |
| --- | --- |
| Base models | mistralai/Mixtral\-8x22B\-v0\.1 (base model; Kind: finetune) |
| Model family | mixtral |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 140,630,071,296 parameters \(safetensors metadata\) |
| Context length | 65,536 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 261\.9 GiB of safetensors weights \(281,260,367,720 bytes\) in BF16 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 28,086 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 757 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/mistralai/mixtral\-8x22b\-instruct\-v0\.1](<https://huggingface.co/mistralai/mixtral-8x22b-instruct-v0.1>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, access, license, and family; no training data, evaluation, or development details are reported for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not state intended use or misuse guidance for Mixtral\-8x22B\-Instruct\-v0\.1, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not document how training/fine\-tuning data was collected, curated, or generated for this checkpoint\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
