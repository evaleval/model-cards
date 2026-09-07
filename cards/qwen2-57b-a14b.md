# Model Card: Qwen2\-57B\-A14B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-57b\-a14b\.json](<./qwen2-57b-a14b.json>)<br>
SHA-256: `f2ff4a27a34cdbd683dd28b673175ae9d87c5f903d2fea9a27a4904069192990`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-57B\-A14B |
| Name | Qwen2\-57B\-A14B |
| Developed by | Qwen \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2024\-05\-22 \(Hugging Face repository creation date\) |
| Version | f29d6a182178ddf39f68f403361779b2d37fdce8 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2 A14B |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 57,408,658,944 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 106\.9 GiB of safetensors weights \(114,818,032,896 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a base language model; the readme does not name the specific pretraining corpus for this checkpoint\. |
| Adaptations | The model is a base language model released without post\-training; the readme recommends applying post\-training such as SFT, RLHF, or continued pretraining before use for text generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 9,830 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 58 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Human evaluations | The developer reports automatic evaluations of the base model covering natural language understanding, general question answering, coding, mathematics, scientific knowledge, reasoning, and multilingual capability\. The reported scores include MMLU 76\.5, HumanEval 53\.0, GSM8K 80\.7, C\-Eval 87\.7, and Multi\-Exam 65\.5\. |
| Safety evaluations | The developer reports a safety evaluation measuring the proportion of harmful responses generated for multilingual unsafe queries in categories including Illegal Activity, Fraud, Pornography, and Privacy Violence\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 76\.5 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 43\.0 | Not specified | Not reported |
| GPQA | Not specified | 34\.3 | Not specified | Not reported |
| Theorem QA | Not specified | 33\.5 | Not specified | Not reported |
| BBH | Not specified | 67\.0 | Not specified | Not reported |
| HellaSwag | Not specified | 85\.2 | Not specified | Not reported |
| Winogrande | Not specified | 79\.5 | Not specified | Not reported |
| ARC\-C | Not specified | 64\.1 | Not specified | Not reported |
| TruthfulQA | Not specified | 57\.7 | Not specified | Not reported |
| HumanEval | Not specified | 53\.0 | Not specified | Not reported |
| MBPP | Not specified | 71\.9 | Not specified | Not reported |
| EvalPlus | Not specified | 57\.2 | Not specified | Not reported |
| MultiPL\-E | Not specified | 49\.8 | Not specified | Not reported |
| GSM8K | Not specified | 80\.7 | Not specified | Not reported |
| MATH | Not specified | 43\.0 | Not specified | Not reported |
| C\-Eval | Not specified | 87\.7 | Not specified | Not reported |
| CMMLU | Not specified | 88\.5 | Not specified | Not reported |
| Multi\-Exam | Not specified | 65\.5 | Not specified | Not reported |
| Multi\-Understanding | Not specified | 77\.0 | Not specified | Not reported |
| Multi\-Mathematics | Not specified | 62\.3 | Not specified | Not reported |
| Multi\-Translation | Not specified | 34\.5 | Not specified | Not reported |
| QPS | Not specified | 9\.40 | Not specified | Not reported |
| Exam | Not specified | 65\.5 | Not specified | Not reported |
| Understanding | Not specified | 77\.0 | Not specified | Not reported |
| Mathematics | Not specified | 62\.3 | Not specified | Not reported |
| Translation | Not specified | 34\.5 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-57B\-A14B](<https://huggingface.co/Qwen/Qwen2-57B-A14B>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | The card reports a safety evaluation measuring the proportion of harmful responses to multilingual unsafe queries, but the model is a base model released without post\-training and the readme recommends post\-training before use, so the reported safety metric may not measure the risks of the final use | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `links.system_card`, `links.tech_report`.
