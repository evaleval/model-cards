# Model Card: pre\-cursa\-o1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [pre\-cursa\-o1\.json](<./pre-cursa-o1.json>)<br>
SHA-256: `d0b4f9099d5ba3850d0f3a840b4063e892acebce641afc34a6631fd75d47ced5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | marcuscedricridia/pre\-cursa\-o1 |
| Name | pre\-cursa\-o1 |
| Developed by | marcuscedricridia \(Hub organization\) |
| Release date | 2025\-02\-27 \(Hugging Face repository creation date\) |
| Version | 2912216a41a29bb0cbc2f0234f26c8bd4aeaed74 |
| Summary | This is a merged language model created with mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | marcuscedricridia/absolute\-o1\-7b (base model; Kind: merge)<br>marcuscedricridia/cursa\-o1\-7b (base model; Kind: merge)<br>marcuscedricridia/sbr\-o1\-7b (base model; Kind: merge) |
| Model family | pre cursa o1 |

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
| Adaptations | This model is a merge created with the TIES merge method, using marcuscedricridia/cursa\-o1\-7b as the base\. The merged models are marcuscedricridia/absolute\-o1\-7b and marcuscedricridia/sbr\-o1\-7b\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/marcuscedricridia/pre\-cursa\-o1](<https://huggingface.co/marcuscedricridia/pre-cursa-o1>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card only states that the model is a mergekit TIES merge of two named 7B models and gives no design, training, or evaluation documentation, so the checkpoint itself lacks transparency about its development and inner workings\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe how the base or merged models' training data was collected, curated, or used, so training\-data transparency is lacking for this checkpoint\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card names the merged and base models but provides no information about the origin, ownership, or usage terms of the data used to train them, making data provenance uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card identifies the model only as a text\-to\-text merged language model and does not define intended uses, leaving the relevant risk profile unspecified\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
