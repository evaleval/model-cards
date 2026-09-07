# Model Card: CodeMind\-Llama3\-8B\-unsloth\_v2\-merged

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [codemind\-llama3\-8b\-unsloth\_v2\-merged\.json](<./codemind-llama3-8b-unsloth_v2-merged.json>)<br>
SHA-256: `becb56d831cb5e16fe2f24112922503b157c52edf55d238bea90fb51062bc4cb`

## Identity

| Field | Value |
| --- | --- |
| Model ID | LimYeri/CodeMind\-Llama3\-8B\-unsloth\_v2\-merged |
| Name | CodeMind\-Llama3\-8B\-unsloth\_v2\-merged |
| Developed by | LimYeri \(Hub organization\) |
| Model type | text generation |
| License | apache\-2\.0 |
| Release date | 2024\-06\-04 \(Hugging Face repository creation date\) |
| Version | d4ec745f8279e3ac6d41709153c21cc077e66385 |
| Summary | The model is a Llama\-based text\-generation model that was trained with Unsloth and Hugging Face&\#x27;s TRL library\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | unsloth/llama\-3\-8b\-Instruct\-bnb\-4bit (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on the LimYeri/LeetCode\_Python\_Solutions dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 25 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/LimYeri/CodeMind\-Llama3\-8B\-unsloth\_v2\-merged](<https://huggingface.co/LimYeri/CodeMind-Llama3-8B-unsloth_v2-merged>) |
| Code repository | [https://github\.com/unslothai/unsloth](<https://github.com/unslothai/unsloth>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Harmful code generation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-code-generation.html>) | Fine\-tuned on LeetCode\_Python\_Solutions and generates code, so it may produce code that causes harm or unintended effects\. | Models might generate code that causes harm or unintentionally affects other systems\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names the dataset but provides no documentation of its collection, curation, or filtering, so dataset details are insufficiently documented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | The card does not provide access to the training data content, so outputs cannot be traced to specific training examples\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Poor model accuracy](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/poor-model-accuracy.html>) | The card reports no evaluation results for the fine\-tuned checkpoint, so its accuracy on code\-generation tasks is unverified\. | Poor model accuracy occurs when a model&\#x27;s performance is insufficient to the task it was designed for\. Low accuracy might occur if the model is not correctly engineered, or if the model&\#x27;s expected inputs change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.model_family`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
