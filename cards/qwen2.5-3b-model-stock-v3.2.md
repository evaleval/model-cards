# Model Card: Qwen2\.5\-3B\-Model\-Stock\-v3\.2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-3b\-model\-stock\-v3\.2\.json](<./qwen2.5-3b-model-stock-v3.2.json>)<br>
SHA-256: `9499f18307ff91d496e8cd592139da61e9ef998d96a29f7a766fd71bfd7f14b1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | bunnycore/Qwen2\.5\-3B\-Model\-Stock\-v3\.2 |
| Name | Qwen2\.5\-3B\-Model\-Stock\-v3\.2 |
| Developed by | bunnycore \(Hub organization\) |
| Release date | 2025\-02\-25 \(Hugging Face repository creation date\) |
| Version | 6deeacbec222c4d286936bcddd966d26a10939e9 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-3B\-Instruct (base model; Kind: merge)<br>bunnycore/QwQen\-3B\-LCoT (base model; Kind: merge)<br>bunnycore/Qwen\-2\.5\-3b\-R1\-lora\_model\-v\.1 (base model; Kind: merge)<br>bunnycore/Qwen\-2\.5\-s1k\-R1\-lora\-v1\.1 (base model; Kind: merge)<br>bunnycore/Qwen2\.5\-3B\-Model\-Stock\-v2 (base model; Kind: merge)<br>bunnycore/Qwen2\.5\-3B\-RP\-Thinker\-V2 (base model; Kind: merge) |
| Model family | Qwen2\.5 Model Stock v3\.2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,395,993,600 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 6\.3 GiB of safetensors weights \(6,792,036,960 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge created with mergekit using the Model Stock merge method, with Qwen/Qwen2\.5\-3B\-Instruct as the base\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 16 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/bunnycore/Qwen2\.5\-3B\-Model\-Stock\-v3\.2](<https://huggingface.co/bunnycore/Qwen2.5-3B-Model-Stock-v3.2>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only merge recipe and base model, with no reported evaluations, training data, or intended\-use details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Merge of multiple named models via mergekit; card does not document provenance or usage terms of the component models' training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not state intended use or deployment context for the merged model, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of testing diversity](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-testing-diversity.html>) | No evaluation or testing information is reported for this checkpoint, so socio\-technical testing across disciplines is absent\. | AI model risks are socio\-technical, so their testing needs input from a broad set of disciplines and diverse testing practices\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
