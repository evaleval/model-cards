# Model Card: Qwen2\.5\-32B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-32b\.json](<./qwen2.5-32b.json>)<br>
SHA-256: `e30c99d44a1c58ec16c1427e5f459e93b3edfb29db8c7878644faec8082c879a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-32B |
| Name | Qwen2\.5\-32B |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-09\-15 \(Hugging Face repository creation date\) |
| Version | 1818d35814b8319459f4bd55ed1ac8709630f003 |
| Summary | Qwen2\.5\-32B is a base 32B model in the Qwen2\.5 series, reintroduced as part of a significant update to the Qwen family\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 32,763,876,352 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 61\.0 GiB of safetensors weights \(65,527,841,752 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The target checkpoint is a pretrained base model; the readme identifies its training stage as pretraining\. The cited pretraining corpus description applies to the Qwen2 comparison model, not to this checkpoint, so it is not used as a fact for this model\. |
| Adaptations | The model is a base language model that has been pretrained but not aligned to human preferences; the readme advises against using base models for conversations and suggests applying post\-training such as SFT, RLHF, or continued pretraining\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 63,487 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 181 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-32B](<https://huggingface.co/Qwen/Qwen2.5-32B>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card summary provides no information about the model&\#x27;s design, development, or evaluation process, so the checkpoint lacks transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card summary describes a base model that is not aligned to human preferences and advises against using it for conversations, but does not define a specific intended use, leaving downstream uses and associated risks undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | The card summary explicitly advises against using the base model for conversations and recommends post\-training such as SFT, RLHF, or continued pretraining, so using it directly for chat would be improper usage\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
