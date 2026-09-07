# Model Card: magnum\-v2\-72b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [magnum\-v2\-72b\.json](<./magnum-v2-72b.json>)<br>
SHA-256: `0685f4d7302cac982a04fd42a3e9c6bd16de8f249666929b23512752203a58fb`

## Identity

| Field | Value |
| --- | --- |
| Model ID | anthracite\-org/magnum\-v2\-72b |
| Name | magnum\-v2\-72b |
| Developed by | anthracite\-org \(Hub organization\) |
| License | other |
| Release date | 2024\-08\-18 \(Hugging Face repository creation date\) |
| Version | c6a1f2afbd378eb2d9a6d74396efa0f09a91f04c |
| Summary | This is the seventh model in a series aimed at replicating the prose quality of Claude 3 models, specifically Sonnet and Opus\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-72B\-Instruct (base model; Kind: finetune) |
| Model family | magnum v2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 72,706,203,648 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 135\.4 GiB of safetensors weights \(145,412,518,832 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was produced by full\-parameter fine\-tuning of Qwen\-2 72B Instruct for two epochs using 8x AMD Instinct MI300X accelerators\. Training used a weight decay of 0\.01 and a peak learning rate of 4e\-6, with sample packing for 16k tokens\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 91 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 40 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/anthracite\-org/magnum\-v2\-72b](<https://huggingface.co/anthracite-org/magnum-v2-72b>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides no evaluation results, training data details, or inner\-workings info for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card does not state the provenance or usage terms of the fine\-tuning data used to adapt Qwen\-2 72B Instruct\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says it aims to replicate prose quality of Claude 3 models and gives no intended\-use or misuse definition\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card gives no documentation of the fine\-tuning dataset, its collection, curation, or synthetic\-data generation\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Model usage rights restrictions](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/model-usage-rights.html>) | License is listed only as &\#x27;other&\#x27; with no terms stated, leaving usage restrictions unclear\. | Terms of service, licenses, or other rules restrict the use of certain models\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
