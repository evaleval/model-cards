# Model Card: Qwen2\.5\-3B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-3b\.json](<./qwen2.5-3b.json>)<br>
SHA-256: `2bbcadafc88f5e4fd34d007bde3dcfe3fa20383a0189aad9eb7f57debede37d1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-3B |
| Name | Qwen2\.5\-3B |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal language model |
| License | other |
| Release date | 2024\-09\-15 \(Hugging Face repository creation date\) |
| Version | 3aab1f1954e9cc14eb9509a215f9e5ca08227a9b |
| Summary | A base 3B\-parameter model in the Qwen2\.5 series, designed for causal language modeling and noted for strong efficiency relative to its size\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,085,938,688 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 5\.7 GiB of safetensors weights \(6,171,926,992 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint is a base pretraining model; the readme identifies its training stage as pretraining\. |
| Adaptations | The model is a base language model and is not aligned to human preferences; the readme advises against using it directly for conversations and recommends applying post\-training such as SFT, RLHF, or continued pretraining\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 302,757 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 202 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer highlights Qwen2\.5\-3B as an efficient small model that delivers strong performance with roughly 3 billion parameters, improving on its predecessors\. The model is also described as part of a family that surpasses most prior open\-weight models and remains competitive with proprietary systems across language understanding, generation, multilingual tasks, coding, mathematics, and reasoning\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-3B](<https://huggingface.co/Qwen/Qwen2.5-3B>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card summary provides only high\-level information \(architecture, training stage, family\-level claims\) and no detailed evaluation or development documentation for this exact checkpoint, so insufficient documentation of design/evaluation is plausibly raised\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card explicitly says the base model is not aligned and advises against using it directly for conversations, but it does not define a concrete intended use or downstream task, leaving the relevant risk space open\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | The card warns that this base model is not aligned to human preferences and should not be used directly for conversations, so using it as a chat model would be an improper use\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
