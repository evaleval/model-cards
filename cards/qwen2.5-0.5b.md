# Model Card: Qwen2\.5\-0\.5B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-0\.5b\.json](<./qwen2.5-0.5b.json>)<br>
SHA-256: `266b82cf595236bca652deff075a8b0f61ed0a3281dd2b88fb37cbb1ec2fb21d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-0\.5B |
| Name | Qwen2\.5\-0\.5B |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal Language Models |
| License | apache\-2\.0 |
| Release date | 2024\-09\-15 \(Hugging Face repository creation date\) |
| Version | 060db6499f32faf8b98477b0a26969ef7d8b9987 |
| Summary | The Qwen2\.5 series includes base language models that are pre\-trained but not aligned to human preferences, alongside instruction\-tuned variants for chat and agent tasks; this repository hosts the base 0\.5B model\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 494,032,768 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 0\.9 GiB of safetensors weights \(988,097,824 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint is a base pretraining\-stage model; the evidence identifies the training stage as pretraining but does not name a specific dataset\. |
| Adaptations | The model is a base language model that has not been aligned to human preferences; the documentation advises against using it directly for conversations and recommends post\-training such as SFT, RLHF, or continued pretraining\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,688,938 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 443 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-0\.5B](<https://huggingface.co/Qwen/Qwen2.5-0.5B>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card states the checkpoint is a base pretraining\-stage model but does not name a specific dataset or provide evaluation details, so there is insufficient documentation of design, development, and evaluation\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card identifies the training stage as pretraining but does not name a specific dataset or describe data collection/curation, limiting transparency about training data\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card advises against using the base model directly for conversations and recommends post\-training, but does not define a concrete intended use, so relevant risks are not specified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | The card explicitly advises against using the base model directly for conversations, so using it that way would be improper usage\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
