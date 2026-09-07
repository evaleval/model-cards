# Model Card: loki\-v0\.1\-virtuoso

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [loki\-v0\.1\-virtuoso\.json](<./loki-v0.1-virtuoso.json>)<br>
SHA-256: `f7ecac808df9bf225a10d5db00c631518660d008dbaa5863694ed59291a45955`

## Identity

| Field | Value |
| --- | --- |
| Model ID | neopolita/loki\-v0\.1\-virtuoso |
| Name | loki\-v0\.1\-virtuoso |
| Developed by | neopolita \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-22 \(Hugging Face repository creation date\) |
| Version | 4d884bbc57fd00e74772d554449bed7cfccc1c2a |

## Lineage

| Field | Value |
| --- | --- |
| Base models | arcee\-ai/Virtuoso\-Small (base model; Kind: finetune) |
| Model family | loki virtuoso |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,770,033,664 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,540,133,960 bytes\) in BF16 |

## Training Context

_No specified fields are available in the publication data._

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
| Model card | [https://huggingface\.co/neopolita/loki\-v0\.1\-virtuoso](<https://huggingface.co/neopolita/loki-v0.1-virtuoso>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, access, license, and family; no design, training, or evaluation documentation for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not state how training data was collected, curated, or generated for loki\-v0\.1\-virtuoso\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | No information about training data origin, ownership, or transformations is provided for this open\-weight checkpoint\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not define intended use or deployment context for loki\-v0\.1\-virtuoso, leaving downstream risk scope unspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
