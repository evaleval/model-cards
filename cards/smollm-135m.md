# Model Card: SmolLM

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm\-135m\.json](<./smollm-135m.json>)<br>
SHA-256: `0934315b5573429e4e463d9553e07a8e4ba9143802c443fefa88008b4a85fcf9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM\-135M |
| Name | SmolLM |
| Developed by | HuggingFaceTB \(Hub organization\) |
| Model type | Small language model |
| License | apache\-2\.0 |
| Release date | 2024\-07\-14 \(Hugging Face repository creation date\) |
| Version | 1d461723eec654e65efdc40cf49301c89c0c92f4 |
| Summary | SmolLM\-135M is a small language model in the SmolLM series\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | SmolLM |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 134,515,008 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 0\.5 GiB of safetensors weights \(538,090,408 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The repository contains a converted version of the latest trained model\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 142,584 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 268 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that SmolLM models perform well relative to other models of similar size on benchmarks for common sense reasoning and world knowledge\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM\-135M](<https://huggingface.co/HuggingFaceTB/SmolLM-135M>) |
| Citation | @misc\{allal2024SmolLM,<br>      title=\{SmolLM \- blazingly fast and remarkably powerful\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Leandro von Werra and Thomas Wolf\},<br>      year=\{2024\},<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only broad benchmark claims and no design/evaluation details for this exact checkpoint, so documentation is insufficient to assess inner workings\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says &\#x27;small language model&\#x27; with no intended\-use or out\-of\-scope guidance, leaving downstream uses and associated risks undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for SmolLM\-135M, so data provenance and curation are not transparent\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Open\-weight checkpoint with no training\-data documentation means generated outputs cannot be traced to specific training content\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
