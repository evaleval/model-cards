# Model Card: SmolLM\-360M\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm\-360m\-instruct\.json](<./smollm-360m-instruct.json>)<br>
SHA-256: `cd4f760da0e421dac30e9416031415362872a36e9fc9ad87023d870dab77f567`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM\-360M\-Instruct |
| Name | SmolLM\-360M\-Instruct |
| Developed by | HuggingFaceTB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-07\-15 \(Hugging Face repository creation date\) |
| Version | 73b7144f76331266f5f45d5642fd8da653583b13 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | HuggingFaceTB/SmolLM\-360M (base model; Kind: quantized) |
| Model family | SmolLM |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 361,821,120 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 0\.7 GiB of safetensors weights \(723,674,912 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 13,914 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 89 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the v0\.2 checkpoint of SmolLM\-360M\-Instruct beats its v0\.1 predecessor in 63\.3% of AlpacaEval comparisons\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM\-360M\-Instruct](<https://huggingface.co/HuggingFaceTB/SmolLM-360M-Instruct>) |
| Citation | @misc\{allal2024SmolLM,<br>      title=\{SmolLM \- blazingly fast and remarkably powerful\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Leandro von Werra and Thomas Wolf\},<br>      year=\{2024\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only a single AlpacaEval comparison and no design, training\-data, or evaluation details for this checkpoint, so model transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document the training or tuning dataset for SmolLM\-360M\-Instruct, so data transparency is limited\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only text\-in/text\-out and open weights without specifying intended use or deployment context, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Open\-weight checkpoint with no training\-data provenance or retrieval mechanism, so outputs cannot be traced to training content\. | The content of the training data used for generating the model's output is not accessible\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
