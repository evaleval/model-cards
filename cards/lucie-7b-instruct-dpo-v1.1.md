# Model Card: Lucie\-7B\-Instruct\-DPO\-v1\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [lucie\-7b\-instruct\-dpo\-v1\.1\.json](<./lucie-7b-instruct-dpo-v1.1.json>)<br>
SHA-256: `74159a4ebf282892d0996ef6757df4d2338a7605b9d45e1d45610d499b692cbc`

## Identity

| Field | Value |
| --- | --- |
| Model ID | jpacifico/Lucie\-7B\-Instruct\-DPO\-v1\.1 |
| Name | Lucie\-7B\-Instruct\-DPO\-v1\.1 |
| Developed by | jpacifico \(Hub organization\) |
| Model type | LLM |
| License | apache\-2\.0 |
| Release date | 2025\-02\-17 \(Hugging Face repository creation date\) |
| Version | fafa7a6cb5f5f064af4089236ec996a6825d9313 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Lucie v1\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 6,706,958,336 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 12\.5 GiB of safetensors weights \(13,413,950,224 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint was DPO fine\-tuned on the jpacifico/french\-orca\-dpo\-pairs\-revised RLHF dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 20 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The model does not include any moderation mechanism\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/jpacifico/Lucie\-7B\-Instruct\-DPO\-v1\.1](<https://huggingface.co/jpacifico/Lucie-7B-Instruct-DPO-v1.1>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports no safety evaluations and no moderation mechanism, and gives no details on DPO data filtering or evaluation, so model design/evaluation transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names only the DPO dataset \(jpacifico/french\-orca\-dpo\-pairs\-revised RLHF\) and does not document its contents, filtering, or generation process\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The DPO dataset is a revised RLHF dataset with no stated origin, ownership, or transformation details, making provenance hard to verify\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Improper data curation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-curation.html>) | The card does not describe curation or filtering of the DPO pairs, so label errors or conflicting information in the tuning data cannot be ruled out\. | Improper collection, generation, and preparation of training or tuning data can result in data label errors, conflicting information or misinformation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only &\#x27;Primary task: LLM&\#x27; and does not define intended or prohibited uses, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
