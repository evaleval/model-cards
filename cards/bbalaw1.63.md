# Model Card: BBALAW1\.63

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [bbalaw1\.63\.json](<./bbalaw1.63.json>)<br>
SHA-256: `0cfd82f14e4ba4e81374889b70b0da41b317653642067bbf72ac0a973fbbab09`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Lawnakk/BBALAW1\.63 |
| Name | BBALAW1\.63 |
| Developed by | Lawnakk \(Hub organization\) |
| Model type | Language model merge created with mergekit\. |
| Release date | 2025\-02\-28 \(Hugging Face repository creation date\) |
| Version | 5e60f6aa903178906c57cacd0149db10bbda945f |
| Summary | A merged language model produced by combining pre\-trained models with mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Lawnakk/BBALAW1\.61 (base model; Kind: merge)<br>bunnycore/Qwen\-2\.5\-7B\-Deep\-Stock\-v4 (base model; Kind: merge) |
| Model family | mergekit merge |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,612,756,480 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,225,551,792 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a merge of two other models, created using the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 16 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Lawnakk/BBALAW1\.63](<https://huggingface.co/Lawnakk/BBALAW1.63>) |
| Code repository | [https://github\.com/naver\-ai/model\-stock](<https://github.com/naver-ai/model-stock>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states it is a mergekit SLERP merge of two named models with no architecture, training data, or evaluation details, so inner workings and design/evaluation process are undocumented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | As a merge of two pre\-trained models, the card gives no information about the provenance or traceability of the underlying training data used by the base models\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card does not document training or tuning dataset details for the merged model or its components, only names the merged models\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the card provides no training\-data content or source information for the merged components, outputs cannot be traced back to specific training data\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card only labels the model as a language model merge and gives no intended\-use or downstream\-task definition, leaving relevant risks undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
