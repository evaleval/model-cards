# Model Card: Qwen2\-72B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-72b\.json](<./qwen2-72b.json>)<br>
SHA-256: `ec5ebbacddb1b6393a5158bc1fb9f56fa393f13bf720820ef1f01849e2429c7c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-72B |
| Name | Qwen2\-72B |
| Developed by | Qwen \(Hub organization\) |
| License | other |
| Release date | 2024\-05\-22 \(Hugging Face repository creation date\) |
| Version | 5f149cae83c11c408a953dec64b12e7e662e8cb9 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 72,706,203,648 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 135\.4 GiB of safetensors weights \(145,412,518,888 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The Qwen2 dense model family, excluding the 0\.5B variant, was pre\-trained on a large\-scale dataset of over 7 trillion tokens\. |
| Adaptations | The base language model is not recommended for direct text generation; post\-training such as SFT, RLHF, or continued pretraining is suggested\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 10,809 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 199 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 84\.2 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 55\.6 | Not specified | Not reported |
| GPQA | Not specified | 37\.9 | Not specified | Not reported |
| Theorem QA | Not specified | 43\.1 | Not specified | Not reported |
| BBH | Not specified | 82\.4 | Not specified | Not reported |
| HellaSwag | Not specified | 87\.6 | Not specified | Not reported |
| WindoGrande | Not specified | 85\.1 | Not specified | Not reported |
| ARC\-C | Not specified | 68\.9 | Not specified | Not reported |
| TruthfulQA | Not specified | 54\.8 | Not specified | Not reported |
| HumanEval | Not specified | 64\.6 | Not specified | Not reported |
| MBPP | Not specified | 76\.9 | Not specified | Not reported |
| EvalPlus | Not specified | 65\.4 | Not specified | Not reported |
| MultiPL\-E | Not specified | 59\.6 | Not specified | Not reported |
| GSM8K | Not specified | 89\.5 | Not specified | Not reported |
| MATH | Not specified | 51\.1 | Not specified | Not reported |
| C\-Eval | Not specified | 91\.0 | Not specified | Not reported |
| CMMLU | Not specified | 90\.1 | Not specified | Not reported |
| Mulit\-Exam | Not specified | 76\.6 | Not specified | Not reported |
| Multi\-Understanding | Not specified | 80\.7 | Not specified | Not reported |
| Multi\-Mathematics | Not specified | 76\.0 | Not specified | Not reported |
| Multi\-Translation | Not specified | 37\.8 | Not specified | Not reported |
| Winogrande | Not specified | 85\.1 | Not specified | Not reported |
| Exam | Not specified | 76\.6 | Not specified | Not reported |
| Understanding | Not specified | 80\.7 | Not specified | Not reported |
| Mathematics | Not specified | 76\.0 | Not specified | Not reported |
| Translation | Not specified | 37\.8 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-72B](<https://huggingface.co/Qwen/Qwen2-72B>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `risks.possible_risks`.
