# Model Card: LLaMA\-2\-vicuna\-7b\-slerp

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-2\-vicuna\-7b\-slerp\.json](<./llama-2-vicuna-7b-slerp.json>)<br>
SHA-256: `1d947ef0ede54ac128f9026b7fbba985c2acd80303cbe57d975dd24aadaec413`

## Identity

| Field | Value |
| --- | --- |
| Model ID | laislemke/LLaMA\-2\-vicuna\-7b\-slerp |
| Name | LLaMA\-2\-vicuna\-7b\-slerp |
| Developed by | laislemke \(Hub organization\) |
| License | llama2 |
| Release date | 2024\-07\-03 \(Hugging Face repository creation date\) |
| Version | 610a00e5e1c0c9bce6378820c3b76f69162b4bf5 |
| Summary | LLaMA\-2\-vicuna\-7b\-slerp is a merge of lmsys/vicuna\-7b\-v1\.5 and togethercomputer/LLaMA\-2\-7B\-32K created with LazyMergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | lmsys/vicuna\-7b\-v1\.5 (base model; Kind: merge)<br>togethercomputer/LLaMA\-2\-7B\-32K (base model; Kind: merge) |
| Model family | LLaMA 2 vicuna slerp |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 6,738,415,616 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 12\.6 GiB of safetensors weights \(13,476,864,936 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This checkpoint is a merge of LLaMA\-2\-vicuna\-7b\-slerp and other models, created using LazyMergekit with the slerp merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 27 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/laislemke/LLaMA\-2\-vicuna\-7b\-slerp](<https://huggingface.co/laislemke/LLaMA-2-vicuna-7b-slerp>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only merge recipe and architecture; no training data, evaluation, or development details for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Merge of two open\-weight models with no stated provenance or verification of the underlying training data lineage\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not define intended use or deployment context for this text\-to\-text merged model\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
