# Model Card: DoublePotato\-Mistral\-Nemo\-13B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [doublepotato\-mistral\-nemo\-13b\.json](<./doublepotato-mistral-nemo-13b.json>)<br>
SHA-256: `783cf17ac56778598418d5ff1be1f2fe4c2e362c3bf87838b75c838db499f80f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | nbeerbower/DoublePotato\-Mistral\-Nemo\-13B |
| Name | DoublePotato\-Mistral\-Nemo\-13B |
| Developed by | nbeerbower \(Hub organization\) |
| Release date | 2025\-02\-13 \(Hugging Face repository creation date\) |
| Version | 7c00ffb0a327260101eb2957a8f5af63443870bf |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | nbeerbower/mistral\-nemo\-kartoffel\-12B (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 13,338,342,400 parameters \(safetensors metadata\) |
| Context length | 1,024,000 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 24\.8 GiB of safetensors weights \(26,676,731,296 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of pre\-trained language models created using mergekit, combined with the Passthrough merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 28 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/nbeerbower/DoublePotato\-Mistral\-Nemo\-13B](<https://huggingface.co/nbeerbower/DoublePotato-Mistral-Nemo-13B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states that the model is a mergekit merge of pre\-trained language models with no training data, training procedure, or evaluation details, so design and development documentation is insufficient\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card names only the merged component models and merge method, with no information about the provenance or usage terms of the underlying training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or misuse information beyond generic text input/output, so relevant risks cannot be defined for downstream uses\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not document how the training data for the merged base models was collected, curated, or used, limiting explainability of model behavior\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the card provides no training\-data access or content information, outputs cannot be traced to specific training sources\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
