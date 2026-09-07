# Model Card: Ice0\.61\-18\.01\-RP

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [ice0\.61\-18\.01\-rp\.json](<./ice0.61-18.01-rp.json>)<br>
SHA-256: `18adbb5556857c3d095aa0b24071ab49e67f61b2699369db88864a5857042c56`

## Identity

| Field | Value |
| --- | --- |
| Model ID | icefog72/Ice0\.61\-18\.01\-RP |
| Name | Ice0\.61\-18\.01\-RP |
| Developed by | icefog72 \(Hub organization\) |
| Release date | 2025\-01\-18 \(Hugging Face repository creation date\) |
| Version | de7284f12936f199f64446577efcf9bfc3373cfb |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Ice0\.61 18\.01 RP |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,498,032 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a merge of two pre\-trained language models, Ice0\.55\-17\.01\-RP and Ice0\.58\-18\.01\-RP, created using mergekit\. |
| Adaptations | The model was merged using the SLERP merge method, combining the models Ice0\.55\-17\.01\-RP and Ice0\.58\-18\.01\-RP\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 11 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/icefog72/Ice0\.61\-18\.01\-RP](<https://huggingface.co/icefog72/Ice0.61-18.01-RP>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states that the checkpoint is a merge of two pre\-trained models using mergekit SLERP, with no documentation of design, development, or evaluation details\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for this checkpoint; it only names the two merged models\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card provides no information about the origin, ownership, or usage terms of the data used to train the merged component models\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or usage scope for the model, only that it is a text\-to\-text decoder\-only merge\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
