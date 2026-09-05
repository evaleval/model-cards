# Model Card: Qwen3\-8B\-Base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen3\-8b\-base\.json](<./qwen3-8b-base.json>)<br>
SHA-256: `7fc6a791a70a998e75233720e93ff3d6c586f2322812647238bc5003278414c8`

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
| Training data | The target checkpoint is a pretrained model; the cited pretraining corpus description refers to the Qwen3 family, not this checkpoint specifically, so it is not attributed as this model&\#x27;s own training data\. |
| Adaptations | The model card states the training stage is pretraining, indicating no post\-training or alignment is described for this checkpoint\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 428,960 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 118 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

_No specified fields are available in the publication data._

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
| MMLU\-Redux | Not specified | 87\.5 | Thinking | Not reported |
| GPQA\-Diamond | Not specified | 62\.0 | Thinking | Not reported |
| C\-Eval | Not specified | 83\.4 | Thinking | Not reported |
| LiveBench 2024\-11\-25 | Not specified | 67\.1 | Thinking | Not reported |
| IFEval strict prompt | Not specified | 85\.0 | Thinking | Not reported |
| Arena\-Hard | Not specified | 85\.8 | Thinking | Not reported |
| AlignBench v1\.1 | Not specified | 8\.46 | Thinking | Not reported |
| Creative Writing v3 | Not specified | 75\.0 | Thinking | Not reported |
| WritingBench | Not specified | 7\.59 | Thinking | Not reported |
| MATH\-500 | Not specified | 97\.4 | Thinking | Not reported |
| AIME&\#x27;24 | Not specified | 76\.0 | Thinking | Not reported |
| AIME&\#x27;25 | Not specified | 67\.3 | Thinking | Not reported |
| ZebraLogic | Not specified | 84\.8 | Thinking | Not reported |
| AutoLogi | Not specified | 89\.1 | Thinking | Not reported |
| BFCL v3 | Not specified | 68\.1 | Thinking | Not reported |
| LiveCodeBench v5 | Not specified | 57\.5 | Thinking | Not reported |
| Multi\-IF | Not specified | 71\.2 | Thinking | Not reported |
| INCLUDE | Not specified | 67\.8 | Thinking | Not reported |
| MMMLU 14 languages | Not specified | 74\.4 | Thinking | Not reported |
| MT\-AIME2024 | Not specified | 65\.4 | Thinking | Not reported |
| PolyMath | Not specified | 42\.7 | Thinking | Not reported |
| MLogiQA | Not specified | 69\.0 | Thinking | Not reported |
| GPQA\-Diamond C\-Eval | Not specified | 77\.9 | Non\-thinking | Not reported |
| LiveBench 2024\-11\-25 | Not specified | 53\.5 | Non\-thinking | Not reported |
| IFEval strict prompt | Not specified | 83\.0 | Non\-thinking | Not reported |
| Arena\-Hard | Not specified | 79\.6 | Non\-thinking | Not reported |
| AlignBench v1\.1 | Not specified | 8\.38 | Non\-thinking | Not reported |
| Creative Writing v3 | Not specified | 64\.5 | Non\-thinking | Not reported |
| WritingBench | Not specified | 7\.15 | Non\-thinking | Not reported |
| MATH\-500 | Not specified | 87\.4 | Non\-thinking | Not reported |
| AIME&\#x27;24 | Not specified | 29\.1 | Non\-thinking | Not reported |
| AIME&\#x27;25 | Not specified | 20\.9 | Non\-thinking | Not reported |
| ZebraLogic | Not specified | 26\.7 | Non\-thinking | Not reported |
| AutoLogi | Not specified | 76\.5 | Non\-thinking | Not reported |
| BFCL v3 | Not specified | 60\.2 | Non\-thinking | Not reported |
| LiveCodeBench v5 | Not specified | 22\.8 | Non\-thinking | Not reported |
| Multi\-IF | Not specified | 69\.2 | Non\-thinking | Not reported |
| INCLUDE | Not specified | 62\.5 | Non\-thinking | Not reported |
| MMMLU 14 languages | Not specified | 66\.9 | Non\-thinking | Not reported |
| MT\-AIME2024 | Not specified | 16\.6 | Non\-thinking | Not reported |
| PolyMath | Not specified | 18\.8 | Non\-thinking | Not reported |
| MLogiQA | Not specified | 51\.4 | Non\-thinking | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen3\-8B\-Base](<https://huggingface.co/Qwen/Qwen3-8B-Base>) |
| Technical report | [https://arxiv\.org/abs/2505\.09388](<https://arxiv.org/abs/2505.09388>) |
| Code repository | [https://github\.com/QwenLM/Qwen3](<https://github.com/QwenLM/Qwen3>) |
| Citation | @misc\{qwen3technicalreport,<br>      title=\{Qwen3 Technical Report\}, <br>      author=\{Qwen Team\},<br>      year=\{2025\},<br>      eprint=\{2505\.09388\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2505\.09388\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
