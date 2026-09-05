# Model Card: DeepSeek\-V3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-v3\.json](<./deepseek-v3.json>)<br>
SHA-256: `a40e0b8a02603400bfd38d88eb0a57a58c4234abadbbbd6ba2db64be03947dd6`

## Identity

| Field | Value |
| --- | --- |
| Model ID | deepseek\-ai/DeepSeek\-V3 |
| Name | DeepSeek\-V3 |
| Developed by | deepseek\-ai \(Hub organization\) |
| Model type | Mixture\-of\-Experts \(MoE\) language model |
| Release date | 2024\-12\-25 \(Hugging Face repository creation date\) |
| Version | e815299b0bcbac849fa540c768ef21845365c9eb |

## Lineage

| Field | Value |
| --- | --- |
| Model family | DeepSeek V3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 684,531,386,000 parameters \(safetensors metadata\) |
| Context length | 163,840 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F8\_E4M3 \(safetensors weight dtype\) |
| Model size | 641\.3 GiB of safetensors weights \(688,586,727,753 bytes\) in F8\_E4M3 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | 14\.8 trillion tokens |
| Adaptations | DeepSeek\-V3 underwent Supervised Fine\-Tuning and Reinforcement Learning after pre\-training\. It also incorporates a methodology that distills reasoning capabilities from a long\-Chain\-of\-Thought model, specifically one of the DeepSeek R1 series models, into standard LLMs\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,047,667 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 4,178 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Human evaluations | Note: English open\-ended conversation evaluations\. For AlpacaEval 2\.0, the length\-controlled win rate is used as the metric\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Multilingual | Not specified | 79\.4 | Not specified | Not reported |
| Arena\-Hard | Not specified | 85\.5 | Not specified | Not reported |
| AlpacaEval 2\.0 | Not specified | 70\.0 | Not specified | Not reported |
| MMLU | exact match | 88\.5 | Not specified | Not reported |
| MMLU\-Redux | exact match | 89\.1 | Not specified | Not reported |
| MMLU\-Pro | exact match | 75\.9 | Not specified | Not reported |
| DROP | F1 | 91\.6 | 3\-shot | Not reported |
| IF\-Eval | Not specified | 86\.1 | Not specified | Not reported |
| GPQA\-Diamond | pass@1 | 59\.1 | Not specified | Not reported |
| SimpleQA | Not specified | 24\.9 | Not specified | Not reported |
| FRAMES | accuracy | 73\.3 | Not specified | Not reported |
| LongBench v2 | accuracy | 48\.7 | Not specified | Not reported |
| HumanEval\-Mul | pass@1 | 82\.6 | Not specified | Not reported |
| LiveCodeBench | pass@1 | 40\.5 | COT | Not reported |
| LiveCodeBench | pass@1 | 37\.6 | Not specified | Not reported |
| Codeforces | Not specified | 51\.6 | Not specified | Not reported |
| SWE Verified | Not specified | 42\.0 | Not specified | Not reported |
| Aider\-Edit | accuracy | 79\.7 | Not specified | Not reported |
| Aider\-Polyglot | accuracy | 49\.6 | Not specified | Not reported |
| AIME 2024 | pass@1 | 39\.2 | Not specified | Not reported |
| MATH\-500 | exact match | 90\.2 | Not specified | Not reported |
| CNMO2024 | pass@1 | 43\.2 | Not specified | Not reported |
| CLUEWSC | exact match | 90\.9 | Not specified | Not reported |
| C\-Eval | exact match | 86\.5 | Not specified | Not reported |
| C\-SimpleQA | Not specified | 64\.8 | Not specified | Not reported |
| Chat | Not specified | 96\.9 | Not specified | Not reported |
| Chat\-Hard | Not specified | 79\.8 | Not specified | Not reported |
| Safety | Not specified | 87 | Not specified | Not reported |
| Reasoning | Not specified | 84\.3 | Not specified | Not reported |
| Average | Not specified | 87 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/deepseek\-ai/DeepSeek\-V3](<https://huggingface.co/deepseek-ai/DeepSeek-V3>) |
| Technical report | [https://arxiv\.org/abs/2412\.19437](<https://arxiv.org/abs/2412.19437>) |
| Code repository | [https://github\.com/deepseek\-ai/DeepSeek\-V3](<https://github.com/deepseek-ai/DeepSeek-V3>) |
| Citation | @misc\{deepseekai2024deepseekv3technicalreport,<br>      title=\{DeepSeek\-V3 Technical Report\}, <br>      author=\{DeepSeek\-AI\},<br>      year=\{2024\},<br>      eprint=\{2412\.19437\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2412\.19437\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.safety_evals`, `links.system_card`.
