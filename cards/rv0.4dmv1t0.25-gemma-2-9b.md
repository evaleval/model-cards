# Model Card: Rv0\.4DMv1t0\.25\-gemma\-2\-9B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [rv0\.4dmv1t0\.25\-gemma\-2\-9b\.json](<./rv0.4dmv1t0.25-gemma-2-9b.json>)<br>
SHA-256: `cc67d2e38d66ad643fcc5118322766f454d26828e6b2919b825cd44f02f1783a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | zelk12/Rv0\.4DMv1t0\.25\-gemma\-2\-9B |
| Name | Rv0\.4DMv1t0\.25\-gemma\-2\-9B |
| Developed by | zelk12 \(Hub organization\) |
| Release date | 2024\-12\-31 \(Hugging Face repository creation date\) |
| Version | b72387e0304c45ebed95e89eb81a8f337c5136c8 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | recoilme/recoilme\-gemma\-2\-9B\-v0\.4 (base model; Kind: merge)<br>sam\-paech/Darkest\-muse\-v1 (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 19 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/zelk12/Rv0\.4DMv1t0\.25\-gemma\-2\-9B](<https://huggingface.co/zelk12/Rv0.4DMv1t0.25-gemma-2-9B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states it is a merge of pre\-trained language models created using mergekit, with no documentation of design, development, or evaluation process\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card does not state training data origin or lineage for the merged model, so provenance of the underlying data is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card provides no information about how training data was collected, curated, or used for the merge\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card gives no intended\-use or deployment context, only input/output text modality and architecture\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.model_family`, `lineage.derivatives`, `specifications.num_parameters`, `specifications.precision`, `specifications.model_size`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
