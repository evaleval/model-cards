# Model Card: Inf\-Silent\-Kunoichi\-v0\.2\-2x7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [inf\-silent\-kunoichi\-v0\.2\-2x7b\.json](<./inf-silent-kunoichi-v0.2-2x7b.json>)<br>
SHA-256: `7d40c1d2e4b7a9a7f131e8a04561bcd93d3fa20e1a2de13b7ee621bbb233186b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Jacoby746/Inf\-Silent\-Kunoichi\-v0\.2\-2x7B |
| Name | Inf\-Silent\-Kunoichi\-v0\.2\-2x7B |
| Developed by | Jacoby746 \(Hub organization\) |
| Model type | Text generation |
| License | apache\-2\.0 |
| Release date | 2024\-09\-19 \(Hugging Face repository creation date\) |
| Version | 9fecaed853b9528a9e2e486d60b54e08ed16f955 |
| Summary | A test merge of 7B models made for learning purposes\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | BAAI/Infinity\-Instruct\-7M\-Gen\-mistral\-7B (base model; Kind: merge)<br>SanjiWatsuki/Kunoichi\-7B (base model; Kind: merge)<br>uukuguy/speechless\-instruct\-mistral\-7b\-v0\.2 (base model; Kind: merge) |
| Model family | Inf Silent Kunoichi |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 12,879,155,200 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 24\.0 GiB of safetensors weights \(25,758,361,912 bytes\) in F16 |
| Input / output | text input<br>text output |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was merged using mergekit\-moe\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Jacoby746/Inf\-Silent\-Kunoichi\-v0\.2\-2x7B](<https://huggingface.co/Jacoby746/Inf-Silent-Kunoichi-v0.2-2x7B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only merge ingredients and architecture; no training/evaluation details for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only &\#x27;text generation&\#x27; and &\#x27;made for learning purposes&\#x27; without defining intended use or misuse boundaries\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card lists merged base models but does not document the provenance or usage terms of their training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not describe training/tuning datasets or any synthetic data generation for this checkpoint\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
