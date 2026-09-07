# Model Card: tempesthenno\-fusion\-0309

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [tempesthenno\-fusion\-0309\.json](<./tempesthenno-fusion-0309.json>)<br>
SHA-256: `e729627631c77e59c06510c04c63178117969efe35e61973f19b7d132da752d8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | sthenno/tempesthenno\-fusion\-0309 |
| Name | tempesthenno\-fusion\-0309 |
| Developed by | sthenno \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-03\-08 \(Hugging Face repository creation date\) |
| Version | 62827e57e10bb9a2ec7d545b303ee82131dedefb |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | sthenno\-com/miscii\-14b\-0218 (base model; Kind: merge)<br>sthenno/tempesthenno\-sft\-0309\-ckpt10 (base model; Kind: merge) |
| Model family | tempesthenno fusion |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,765,947,904 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 55\.0 GiB of safetensors weights \(59,063,857,880 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/sthenno/tempesthenno\-fusion\-0309](<https://huggingface.co/sthenno/tempesthenno-fusion-0309>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, license, and mergekit merge; no training data, training procedure, or evaluation results are documented for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card states it is a merge of pre\-trained language models created using mergekit but does not document the provenance of the merged base models&\#x27; training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information is provided about how training data was collected, curated, or used for the merged model or its components\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card specifies only text\-to\-text modality and open\-weight access, with no intended\-use or out\-of\-scope\-use description\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
