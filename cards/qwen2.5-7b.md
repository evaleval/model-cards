# Model Card: Qwen2\.5\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-7b\.json](<./qwen2.5-7b.json>)<br>
SHA-256: `35d3ed2c29c817111fa0e675cd08bf425468cf643879a94691d497cb30bc67e8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-7B |
| Name | Qwen2\.5\-7B |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal language model |
| License | apache\-2\.0 |
| Release date | 2024\-09\-15 \(Hugging Face repository creation date\) |
| Version | d149729398750b98c0af14eb82c78cfe92750796 |
| Summary | A base 7B model in the Qwen2\.5 series, released as a causal language model\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,888 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint is a base pretraining model; its training data is not specified in the evidence items\. |
| Adaptations | The model is a base language model released without post\-training; the documentation recommends applying post\-training such as SFT, RLHF, or continued pretraining before conversational use\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 686,151 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 312 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The Qwen2\.5 family is reported to outperform Qwen2 with substantially higher scores on knowledge, coding, and mathematics benchmarks, while also improving instruction following, long\-text generation, structured\-data understanding, and structured\-output generation\. The models are described as more robust to varied system prompts and as retaining 128K\-token context support with up to 8K\-token generation and multilingual coverage of over 29 languages\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-7B](<https://huggingface.co/Qwen/Qwen2.5-7B>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card states the checkpoint is a base pretraining model but does not specify its training data, so dataset details are undocumented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card describes a base model released without post\-training and recommends applying SFT/RLHF/continued pretraining before conversational use, leaving intended use undefined for downstream deployments\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | The card explicitly recommends post\-training before conversational use, so using the base model directly for chat would be an improper use\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
