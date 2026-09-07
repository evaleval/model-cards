# Model Card: ECE\-PRYMMAL0\.5B\-Youri

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [ece\-prymmal0\.5b\-youri\.json](<./ece-prymmal0.5b-youri.json>)<br>
SHA-256: `4d0fcf64f76a8a949354ac783434f129601781c123a48e1a80d2eb7741db0eb1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Youlln/ECE\-PRYMMAL0\.5B\-Youri |
| Name | ECE\-PRYMMAL0\.5B\-Youri |
| Developed by | Youlln \(Hub organization\) |
| Release date | 2024\-10\-07 \(Hugging Face repository creation date\) |
| Version | 1477d3deff98f35f523aa222bc0442278d464566 |
| Summary | ECE\-PRYMMAL0\.5B\-Youri is a merge of Qwen2\-0\.5B and Qwen2\.5\-0\.5B created with LazyMergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-0\.5B (base model; Kind: merge)<br>Qwen/Qwen2\.5\-0\.5B (base model; Kind: merge) |
| Model family | ECE PRYMMAL0\.5B Youri |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 630,167,424 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 1\.2 GiB of safetensors weights \(1,260,367,448 bytes\) in BF16 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Youlln/ECE\-PRYMMAL0\.5B\-Youri](<https://huggingface.co/Youlln/ECE-PRYMMAL0.5B-Youri>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, merge recipe, and access type; no design, development, evaluation, or inner\-workings documentation is reported\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not report how the merged model&\#x27;s training/merge data was collected, curated, or used, so training\-data documentation is lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card identifies base models but gives no traceability of the underlying data sources, transformations, or generation for the merge\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only that it is a model/merge and gives no intended\-use or deployment context, leaving downstream risk assessment undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
