# Model Card: Qwen2\.5\-7B\-it\-restore

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-7b\-it\-restore\.json](<./qwen2.5-7b-it-restore.json>)<br>
SHA-256: `280ebb449153a85e0a0a53f24f85f8b7eef4e0d39d6c36c28960bae9b9ee0184`

## Identity

| Field | Value |
| --- | --- |
| Model ID | YOYO\-AI/Qwen2\.5\-7B\-it\-restore |
| Name | Qwen2\.5\-7B\-it\-restore |
| Developed by | YOYO\-AI \(Hub organization\) |
| Model type | Text generation model\. |
| License | apache\-2\.0 |
| Release date | 2025\-03\-10 \(Hugging Face repository creation date\) |
| Version | c45b9a94190dfdbc24c2e3fb183072738a8a5d97 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B (base model; Kind: merge)<br>Qwen/Qwen2\.5\-7B\-Instruct (base model; Kind: merge) |

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

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 20 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/YOYO\-AI/Qwen2\.5\-7B\-it\-restore](<https://huggingface.co/YOYO-AI/Qwen2.5-7B-it-restore>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, task, modalities, access, and license; no training data, training details, or evaluation results are reported for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only &\#x27;Text generation model&\#x27; with no intended\-use or misuse guidance, leaving downstream uses undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for Qwen2\.5\-7B\-it\-restore\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card does not describe the origin, ownership, or generation of data used for this checkpoint, so provenance is untraceable from the card\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because no training data is documented, the content sources behind the model&\#x27;s outputs cannot be attributed\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
