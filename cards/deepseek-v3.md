# Model Card: DeepSeek\-V3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-v3\.json](<./deepseek-v3.json>)<br>
SHA-256: `1c7e8f8dc400140af528a07b4fda1148f9e9f7f208e8cf71df9209ce5da1b03b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | deepseek\-ai/DeepSeek\-V3 |
| Name | DeepSeek\-V3 |
| Developed by | deepseek\-ai \(Hub organization\) |
| Release date | 2024\-12\-25 \(Hugging Face repository creation date\) |
| Version | e815299b0bcbac849fa540c768ef21845365c9eb |
| Summary | DeepSeek\-V3 is a large Mixture\-of\-Experts language model that activates 37B of its 671B parameters for each token\. |

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
| Training data | DeepSeek\-V3 was pre\-trained on 14\.8 trillion diverse and high\-quality tokens in its tokenizer\. |
| Training data size | 14\.8 trillion tokens |
| Adaptations | After pre\-training, DeepSeek\-V3 underwent Supervised Fine\-Tuning and Reinforcement Learning stages\. It also incorporated a methodology that distills reasoning capabilities from a DeepSeek R1 series long\-Chain\-of\-Thought model into standard LLMs, particularly DeepSeek\-V3\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,047,667 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 4,178 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that DeepSeek\-V3 outperforms other open\-source models and is competitive with leading closed\-source models, describing it as the best\-performing open\-source model in standard evaluations\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| English | Not specified | 0\.548 | Not specified | Not reported |
| English | Not specified | 88\.5 | Not specified | Not reported |
| Code | Not specified | 65\.2 | Not specified | Not reported |
| Code | Not specified | 82\.6 | Not specified | Not reported |
| Math | Not specified | 89\.3 | Not specified | Not reported |
| Math | Not specified | 39\.2 | Not specified | Not reported |
| Chinese | Not specified | 82\.7 | Not specified | Not reported |
| Chinese | Not specified | 90\.9 | Not specified | Not reported |
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

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
