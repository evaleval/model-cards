# Model Card: Qwen2\.5\-1\.5B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-1\.5b\.json](<./qwen2.5-1.5b.json>)<br>
SHA-256: `fa0d63caae91473912e0696ea30a5837008a0112729302a951c3299696f5cb57`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-1\.5B |
| Name | Qwen2\.5\-1\.5B |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal language model |
| License | apache\-2\.0 |
| Release date | 2024\-09\-15 \(Hugging Face repository creation date\) |
| Version | 8faed761d45a263340a0528343f099c05c9a4323 |
| Summary | The base 1\.5B Qwen2\.5 model, a causal language model\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,543,714,304 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.9 GiB of safetensors weights \(3,087,467,144 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint is a base language model produced during the pretraining stage, before any alignment to human preferences\. |
| Adaptations | The model is a base, unaligned language model; the documentation advises against using it directly for conversations and recommends applying post\-training such as SFT, RLHF, or continued pretraining\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,075,947 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 212 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-1\.5B](<https://huggingface.co/Qwen/Qwen2.5-1.5B>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only architecture, task, and license, with no evaluation results or training\-data details, so the checkpoint's behavior and limitations are not transparently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card states it is a pretraining checkpoint but gives no information about data collection, curation, or composition, making training\-data transparency insufficient\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card says it is a base unaligned model and advises against direct conversational use, but does not define a concrete intended use or downstream risk context\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | The card explicitly advises against using the base model directly for conversations and recommends post\-training, so using it as\-is for chat would be improper usage\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
