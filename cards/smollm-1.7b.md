# Model Card: SmolLM

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm\-1\.7b\.json](<./smollm-1.7b.json>)<br>
SHA-256: `24bf55e11b67aaa37f0d94480de512658c26cc7b38a365c285c4db4446953f63`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM\-1\.7B |
| Name | SmolLM |
| Developed by | HuggingFaceTB \(Hub organization\) |
| Model type | small language model |
| License | apache\-2\.0 |
| Release date | 2024\-07\-14 \(Hugging Face repository creation date\) |
| Version | d7449ff7241c863f3e8accc475155f0f97afa011 |
| Summary | SmolLM\-1\.7B is a small language model in the SmolLM series\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | SmolLM |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,711,376,384 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 6\.4 GiB of safetensors weights \(6,845,530,528 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | Pretraining used 1T tokens\. |
| Adaptations | The repository contains a converted version of the latest trained model\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 69,104 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 184 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that SmolLM models perform well relative to other models of similar size on benchmarks that assess common sense reasoning and world knowledge\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM\-1\.7B](<https://huggingface.co/HuggingFaceTB/SmolLM-1.7B>) |
| Citation | @misc\{allal2024SmolLM,<br>      title=\{SmolLM \- blazingly fast and remarkably powerful\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Leandro von Werra and Thomas Wolf\},<br>      year=\{2024\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only task, architecture, and benchmark results, with no documentation of training data, development process, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not state how training data was collected, curated, or used for SmolLM\-1\.7B, so training\-data transparency is lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says &\#x27;small language model&\#x27; and does not define intended uses or limitations, leaving downstream risk assessment open\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
