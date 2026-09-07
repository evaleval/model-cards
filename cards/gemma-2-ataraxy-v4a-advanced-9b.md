# Model Card: Gemma\-2\-Ataraxy\-v4a\-Advanced\-9B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-2\-ataraxy\-v4a\-advanced\-9b\.json](<./gemma-2-ataraxy-v4a-advanced-9b.json>)<br>
SHA-256: `51f7f6d06e2f50acff408727eb892a9d335cff72547ab8e42805389e48c3e7ea`

## Identity

| Field | Value |
| --- | --- |
| Model ID | lemon07r/Gemma\-2\-Ataraxy\-v4a\-Advanced\-9B |
| Name | Gemma\-2\-Ataraxy\-v4a\-Advanced\-9B |
| Developed by | lemon07r \(Hub organization\) |
| Release date | 2024\-10\-14 \(Hugging Face repository creation date\) |
| Version | a571ddc57ab176a50268b2d14f1735c04b8610f9 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | lemon07r/Gemma\-2\-Ataraxy\-v3\-Advanced\-9B (base model; Kind: merge)<br>zelk12/recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.1\-t0\.25 (base model; Kind: merge) |
| Model family | Gemma\-2\-Ataraxy |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 10,159,209,984 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 18\.9 GiB of safetensors weights \(20,318,474,544 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of lemon07r/Gemma\-2\-Ataraxy\-v3\-Advanced\-9B and zelk12/recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.1\-t0\.25, combined using the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 30 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 5 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/lemon07r/Gemma\-2\-Ataraxy\-v4a\-Advanced\-9B](<https://huggingface.co/lemon07r/Gemma-2-Ataraxy-v4a-Advanced-9B>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card only states that the model is a merge of two named checkpoints using SLERP, with no documentation of training data, evaluation, or intended use\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card describes a merge of two pre\-trained models but provides no information about the provenance or usage terms of the underlying training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card gives no details about the training or tuning datasets of the merged components, so training data documentation is absent\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card does not state any intended use or downstream task for the merged model, leaving the relevant risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
