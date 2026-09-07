# Model Card: RuDolph\-Hermes\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [rudolph\-hermes\-7b\.json](<./rudolph-hermes-7b.json>)<br>
SHA-256: `e6f5a4a4e12f79822f64b3f72c31a033f343b347bcd16001a1332f94a85dacbe`

## Identity

| Field | Value |
| --- | --- |
| Model ID | theprint/RuDolph\-Hermes\-7B |
| Name | RuDolph\-Hermes\-7B |
| Developed by | theprint \(Hub organization\) |
| Release date | 2024\-11\-10 \(Hugging Face repository creation date\) |
| Version | 17e7f62a5da34d8caa7d1b8213779df3ce198af3 |
| Summary | RuDolph\-Hermes\-7B is a conversational model created as an homage to the Dolphin and OpenHermes versions of Mistral 7B\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | dphn/dolphin\-2\.2\.1\-mistral\-7b (base model; Kind: merge)<br>teknium/OpenHermes\-2\.5\-Mistral\-7B (base model; Kind: merge) |
| Model family | RuDolph Hermes |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,748,480 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,530,776 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a merge of two pre\-trained language models: cognitivecomputations/dolphin\-2\.2\.1\-mistral\-7b and teknium/OpenHermes\-2\.5\-Mistral\-7B\. |
| Adaptations | The model is a merge created with mergekit, using the SLERP merge method with a Sigmoid\-inspired curve\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 24 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/theprint/RuDolph\-Hermes\-7B](<https://huggingface.co/theprint/RuDolph-Hermes-7B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only merge recipe and base model names; no training/evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Checkpoint is a merge of two open\-weight models; card does not trace the provenance of their training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document the training or tuning datasets of the merged base models\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | No training data is provided for the merged checkpoint, limiting explanations of its outputs\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the training data of the merged base models is not accessible, output content cannot be attributed to sources\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
