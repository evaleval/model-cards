# Model Card: Qwen2\-0\.5B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-0\.5b\.json](<./qwen2-0.5b.json>)<br>
SHA-256: `0da98bf3d1769ca368a448cbd58faa974dd1d11b5fda0d4df5c12526b0ef7fde`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-0\.5B |
| Name | Qwen2\-0\.5B |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-31 \(Hugging Face repository creation date\) |
| Version | 91d2aff3f957f99e4c74c962f2f408dcc88a18d8 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 494,032,768 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 0\.9 GiB of safetensors weights \(988,097,824 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Qwen2\-0\.5B was pre\-trained on a 12 trillion token dataset\. |
| Adaptations | The model is a base language model; the documentation advises applying post\-training such as SFT, RLHF, or continued pretraining before using it for text generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 823,089 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 170 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the Qwen2 family outperforms most prior open\-weight models, including Qwen1\.5, and is competitive with proprietary models across language understanding, generation, multilingual proficiency, coding, mathematics, and reasoning\. Smaller Qwen2 models are also said to outcompete state\-of\-the\-art models of similar or larger sizes\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 45\.4 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 14\.7 | Not specified | Not reported |
| Theorem QA | Not specified | 8\.9 | Not specified | Not reported |
| HumanEval | Not specified | 22\.0 | Not specified | Not reported |
| MBPP | Not specified | 22\.0 | Not specified | Not reported |
| GSM8K | Not specified | 36\.5 | Not specified | Not reported |
| MATH | Not specified | 10\.7 | Not specified | Not reported |
| BBH | Not specified | 28\.4 | Not specified | Not reported |
| HellaSwag | Not specified | 49\.3 | Not specified | Not reported |
| Winogrande | Not specified | 56\.8 | Not specified | Not reported |
| ARC\-C | Not specified | 31\.5 | Not specified | Not reported |
| TruthfulQA | Not specified | 39\.7 | Not specified | Not reported |
| C\-Eval | Not specified | 58\.2 | Not specified | Not reported |
| CMMLU | Not specified | 55\.1 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-0\.5B](<https://huggingface.co/Qwen/Qwen2-0.5B>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only broad 12T token pretraining and family\-level benchmark claims, with no dataset composition, training details, or evaluation specifics for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card states a 12 trillion token dataset but does not document its composition, sources, filtering, or any synthetic data generation details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card describes a base model and advises applying post\-training before text generation, but does not define intended or prohibited uses for this checkpoint\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | Because the card explicitly advises post\-training before use for text generation, using the base model directly for generation would be an improper usage\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
