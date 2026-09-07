# Model Card: MagnusIntellectus\-12B\-v1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [magnusintellectus\-12b\-v1\.json](<./magnusintellectus-12b-v1.json>)<br>
SHA-256: `cd5eca593bd7ac1e842310143a4e5fe82ff13580c53563588d37c9ef87976f80`

## Identity

| Field | Value |
| --- | --- |
| Model ID | GalrionSoftworks/MagnusIntellectus\-12B\-v1 |
| Name | MagnusIntellectus\-12B\-v1 |
| Developed by | GalrionSoftworks \(Hub organization\) |
| Model type | Text generation model\. |
| License | apache\-2\.0 |
| Release date | 2024\-08\-13 \(Hugging Face repository creation date\) |
| Version | d7bc1d7552588ea3ccc619aa766ff4a4e4c633c2 |
| Summary | A text\-generation model created as a merge of other models\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | UsernameJustAnother/Nemo\-12B\-Marlin\-v5 (base model; Kind: merge)<br>anthracite\-org/magnum\-v2\-12b (base model; Kind: merge) |
| Model family | MagnusIntellectus v1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 12,247,782,400 parameters \(safetensors metadata\) |
| Context length | 1,024,000 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 22\.8 GiB of safetensors weights \(24,495,607,104 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | MagnusIntellectus is a merge of other models, created with LazyMergekit using the TIES merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 43 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 5 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/GalrionSoftworks/MagnusIntellectus\-12B\-v1](<https://huggingface.co/GalrionSoftworks/MagnusIntellectus-12B-v1>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only merge recipe and architecture; no training data, evaluation, or development details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card states it is a merge of other models but does not document the provenance or usage terms of the underlying training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information about how training data was collected, curated, or used is provided in the card\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says text generation and does not define intended use or use limitations\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
