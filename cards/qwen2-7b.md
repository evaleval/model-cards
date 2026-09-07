# Model Card: Qwen2\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-7b\.json](<./qwen2-7b.json>)<br>
SHA-256: `d3826b6e3ade7d8125e97354a7dd726526125993671e5a4ed6200b171babab30`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-7B |
| Name | Qwen2\-7B |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-06\-04 \(Hugging Face repository creation date\) |
| Version | 453ed1575b739b5b03ce3758b23befdb0967f40e |
| Summary | Qwen2 is a series of base and instruction\-tuned large language models in five sizes, including Qwen2\-7B\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The Qwen2 family of dense models, excluding the 0\.5B variant, was pre\-trained on a large\-scale dataset of over 7 trillion tokens\. |
| Adaptations | The base language model is not recommended for direct text generation; post\-training such as SFT, RLHF, or continued pretraining should be applied\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 247,508 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 174 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the Qwen2 family surpasses most prior open\-weight models, including Qwen1\.5, and is competitive with proprietary models across language understanding, generation, multilingual proficiency, coding, mathematics, and reasoning\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 70\.3 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 40\.0 | Not specified | Not reported |
| GPQA | Not specified | 31\.8 | Not specified | Not reported |
| Theorem QA | Not specified | 31\.1 | Not specified | Not reported |
| BBH | Not specified | 62\.6 | Not specified | Not reported |
| HellaSwag | Not specified | 80\.7 | Not specified | Not reported |
| Winogrande | Not specified | 77\.0 | Not specified | Not reported |
| ARC\-C | Not specified | 60\.6 | Not specified | Not reported |
| TruthfulQA | Not specified | 54\.2 | Not specified | Not reported |
| HumanEval | Not specified | 51\.2 | Not specified | Not reported |
| MBPP | Not specified | 65\.9 | Not specified | Not reported |
| EvalPlus | Not specified | 54\.2 | Not specified | Not reported |
| MultiPL\-E | Not specified | 46\.3 | Not specified | Not reported |
| GSM8K | Not specified | 79\.9 | Not specified | Not reported |
| MATH | Not specified | 44\.2 | Not specified | Not reported |
| C\-Eval | Not specified | 83\.2 | Not specified | Not reported |
| CMMLU | Not specified | 83\.9 | Not specified | Not reported |
| Multi\-Exam | Not specified | 59\.2 | Not specified | Not reported |
| Multi\-Understanding | Not specified | 72\.0 | Not specified | Not reported |
| Multi\-Mathematics | Not specified | 57\.5 | Not specified | Not reported |
| Multi\-Translation | Not specified | 31\.5 | Not specified | Not reported |
| Exam | Not specified | 59\.2 | Not specified | Not reported |
| Understanding | Not specified | 72\.0 | Not specified | Not reported |
| Mathematics | Not specified | 57\.5 | Not specified | Not reported |
| Translation | Not specified | 31\.5 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-7B](<https://huggingface.co/Qwen/Qwen2-7B>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only family\-level benchmark claims and no model design, training\-data, or evaluation details for this exact checkpoint, so its development/evaluation process is insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card states only that the family was pre\-trained on &\#x27;over 7 trillion tokens&\#x27; with no dataset composition, curation, or filtering details for this checkpoint\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card says the base model is not recommended for direct text generation and that post\-training should be applied, but does not define intended uses or misuse boundaries for this checkpoint\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | Because the card explicitly warns that the base model is not recommended for direct text generation, using it directly for text generation would be an improper use\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
