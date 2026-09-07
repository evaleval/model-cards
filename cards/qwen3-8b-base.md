# Model Card: Qwen3\-8B\-Base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen3\-8b\-base\.json](<./qwen3-8b-base.json>)<br>
SHA-256: `59be76067bd5ca4c984b322fe58066632a35cc535b17668551e74acee01b53c8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen3\-8B\-Base |
| Name | Qwen3\-8B\-Base |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal language model |
| License | apache\-2\.0 |
| Release date | 2025\-04\-28 \(Hugging Face repository creation date\) |
| Version | 49e3418fbbbca6ecbdf9608b4d22e5a407081db4 |
| Summary | Qwen3\-8B\-Base is an open\-weight dense model in the Qwen3 series, released under the Apache 2\.0 license\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,190,735,360 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.3 GiB of safetensors weights \(16,381,516,776 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The Qwen3 family, which includes this checkpoint, was pre\-trained on a large multilingual corpus spanning 119 languages and dialects, totaling 36 trillion tokens, with an emphasis on high\-quality data covering coding, STEM, reasoning, books, multilingual content, and synthetic data\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 420,468 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 119 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen3 models achieve strong results across diverse benchmarks, including code generation, mathematical reasoning, and agent tasks, and that the dense base models are competitive with larger Qwen2\.5 base models, particularly in STEM, coding, and reasoning\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 76\.89 | Not specified | Not reported |
| MMLU\-Redux | Not specified | 76\.17 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 56\.73 | Not specified | Not reported |
| SuperGPQA | Not specified | 31\.64 | Not specified | Not reported |
| BBH | Not specified | 78\.40 | Not specified | Not reported |
| GPQA | Not specified | 44\.44 | Not specified | Not reported |
| GSM8K | Not specified | 89\.84 | Not specified | Not reported |
| MATH | Not specified | 60\.80 | Not specified | Not reported |
| EvalPlus | Not specified | 67\.65 | Not specified | Not reported |
| MultiPL\-E | Not specified | 58\.75 | Not specified | Not reported |
| MBPP | Not specified | 69\.80 | Not specified | Not reported |
| CRUX\-O | Not specified | 62\.00 | Not specified | Not reported |
| MGSM | Not specified | 76\.02 | Not specified | Not reported |
| MMMLU | Not specified | 75\.72 | Not specified | Not reported |
| IINCLUDE | Not specified | 59\.40 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen3\-8B\-Base](<https://huggingface.co/Qwen/Qwen3-8B-Base>) |
| Technical report | [https://arxiv\.org/abs/2505\.09388](<https://arxiv.org/abs/2505.09388>) |
| Code repository | [https://github\.com/QwenLM/Qwen3](<https://github.com/QwenLM/Qwen3>) |
| Citation | @misc\{qwen3technicalreport,<br>      title=\{Qwen3 Technical Report\}, <br>      author=\{Qwen Team\},<br>      year=\{2025\},<br>      eprint=\{2505\.09388\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2505\.09388\}, <br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `risks.possible_risks`.
