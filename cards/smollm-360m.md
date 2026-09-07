# Model Card: SmolLM

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm\-360m\.json](<./smollm-360m.json>)<br>
SHA-256: `74d99e8a1416160988da58436f6e939bd84f9cbd2d4224ca291fbba84d2ade3d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM\-360M |
| Name | SmolLM |
| Developed by | HuggingFaceTB \(Hub organization\) |
| Model type | Small language model |
| License | apache\-2\.0 |
| Release date | 2024\-07\-14 \(Hugging Face repository creation date\) |
| Version | 59f7ef243ee09a72cbc14cb054393a3e3b771d41 |
| Summary | This is the SmolLM\-360M |

## Lineage

| Field | Value |
| --- | --- |
| Model family | SmolLM |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 361,821,120 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 1\.3 GiB of safetensors weights \(1,447,317,080 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The repository contains a converted version of the latest trained model\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 7,452 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 73 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that SmolLM models perform competitively against other models of similar size on benchmarks that assess common sense reasoning and world knowledge\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM\-360M](<https://huggingface.co/HuggingFaceTB/SmolLM-360M>) |
| Citation | @misc\{allal2024SmolLM,<br>      title=\{SmolLM \- blazingly fast and remarkably powerful\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Leandro von Werra and Thomas Wolf\},<br>      year=\{2024\},<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, size, and benchmark claims; no training data, development, or evaluation details are documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe how training data was collected, curated, or used, so training data transparency is lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says &\#x27;small language model&\#x27; and gives no intended\-use or misuse definition, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
