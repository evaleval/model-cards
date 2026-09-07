# Model Card: recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [recoilme\-gemma\-2\-ataraxy\-9b\-v0\.2\.json](<./recoilme-gemma-2-ataraxy-9b-v0.2.json>)<br>
SHA-256: `94e9698ca6c295dcb828bc92a72b3e1b1b0a27ee84076c841851ea6147d644eb`

## Identity

| Field | Value |
| --- | --- |
| Model ID | zelk12/recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.2 |
| Name | recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.2 |
| Developed by | zelk12 \(Hub organization\) |
| Release date | 2024\-10\-07 \(Hugging Face repository creation date\) |
| Version | f990739110a1d59262b767ad3ee06a4e69291d50 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | zelk12/recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.1\-t0\.25 (base model; Kind: merge)<br>zelk12/recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.1\-t0\.75 (base model; Kind: merge) |
| Model family | recoilme gemma 2 Ataraxy |

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
| Adaptations | The model is a merge of two listed checkpoints, combined with the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 27 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/zelk12/recoilme\-gemma\-2\-Ataraxy\-9B\-v0\.2](<https://huggingface.co/zelk12/recoilme-gemma-2-Ataraxy-9B-v0.2>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states it is a merge of two checkpoints via SLERP with no training data, evaluation, or development details, so design and evaluation process are undocumented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe how the underlying checkpoints&\#x27; training data was collected, curated, or used, and no data documentation is provided for the merge\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card names two source checkpoints but provides no traceability of their training data, ownership, or generation/transformation details beyond the SLERP merge\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | The card provides no information about training data content or attribution, so outputs cannot be traced back to specific training data\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or downstream\-use information, leaving the relevant risk scope undefined for this open\-weight text model\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
