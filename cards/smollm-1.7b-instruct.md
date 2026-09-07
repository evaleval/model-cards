# Model Card: SmolLM\-1\.7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm\-1\.7b\-instruct\.json](<./smollm-1.7b-instruct.json>)<br>
SHA-256: `141735dbf07f3037aedb9931d03e76f08a168df996e200cadc8070ddfa9277b4`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM\-1\.7B\-Instruct |
| Name | SmolLM\-1\.7B\-Instruct |
| Developed by | HuggingFaceTB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-07\-15 \(Hugging Face repository creation date\) |
| Version | 69f49d9c36434d6a3f319dadc5bd3b812752b98b |

## Lineage

| Field | Value |
| --- | --- |
| Base models | HuggingFaceTB/SmolLM\-1\.7B (base model; Kind: quantized) |
| Model family | SmolLM |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,711,376,384 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 3\.2 GiB of safetensors weights \(3,422,777,952 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 8,466 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 121 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the v0\.2 models show improved topic adherence and more appropriate responses to standard prompts, including greetings and questions about their role as AI assistants\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM\-1\.7B\-Instruct](<https://huggingface.co/HuggingFaceTB/SmolLM-1.7B-Instruct>) |
| Citation | @misc\{allal2024SmolLM,<br>      title=\{SmolLM \- blazingly fast and remarkably powerful\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Leandro von Werra and Thomas Wolf\},<br>      year=\{2024\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only high\-level results and no design, development, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe how training/fine\-tuning data was collected, curated, or used for SmolLM\-1\.7B\-Instruct\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not define intended or out\-of\-scope uses for this open\-weight instruct model\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
