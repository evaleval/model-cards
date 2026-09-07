# Model Card: AceInstruct\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [aceinstruct\-7b\.json](<./aceinstruct-7b.json>)<br>
SHA-256: `114194b732d1d73ec578ce554d050f659e6fc39bec1baf8aa26509927c140ace`

## Identity

| Field | Value |
| --- | --- |
| Model ID | nvidia/AceInstruct\-7B |
| Name | AceInstruct\-7B |
| Developed by | nvidia \(Hub organization\) |
| Model type | text\-generation |
| License | cc\-by\-nc\-4\.0 |
| Release date | 2025\-01\-15 \(Hugging Face repository creation date\) |
| Version | 3bbb14f63afd2dc890c7932bfffb4f6dc3bfa1e8 |
| Summary | AceInstruct is a family of supervised fine\-tuned models for coding, mathematics, and general\-purpose tasks\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | AceInstruct |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,864 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a fine\-tune of Qwen2\.5\-Base, trained with general SFT datasets\. |
| Adaptations | The model was produced by supervised fine\-tuning \(SFT\) on general SFT datasets, starting from Qwen2\.5\-Base\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 398 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 22 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HumanEval | Not specified | 85\.37 | Not specified | Not reported |
| MBPP | Not specified | 74\.32 | Not specified | Not reported |
| GSM8K | Not specified | 93\.10 | Not specified | Not reported |
| MATH | Not specified | 76\.40 | Not specified | Not reported |
| MMLU | Not specified | 74\.68 | Not specified | Not reported |
| MMLU Pro | Not specified | 54\.50 | Not specified | Not reported |
| Average | Not specified | 76\.40 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/nvidia/AceInstruct\-7B](<https://huggingface.co/nvidia/AceInstruct-7B>) |
| Citation | @article\{acemath2024,<br>  title=\{AceMath: Advancing Frontier Math Reasoning with Post\-Training and Reward Modeling\},<br>  author=\{Liu, Zihan and Chen, Yang and Shoeybi, Mohammad and Catanzaro, Bryan and Ping, Wei\},<br>  journal=\{arXiv preprint\},<br>  year=\{2024\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
