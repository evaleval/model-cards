# Model Card: Qwen3\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen3\-8b\.json](<./qwen3-8b.json>)<br>
SHA-256: `281a767a87f245696445c08dce4692651e8deb9fd2ed1aa391590fd778776f11`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen3\-8B |
| Name | Qwen3\-8B |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-04\-27 \(Hugging Face repository creation date\) |
| Version | b968826d9c46dd6066d109eabc6255188de91218 |
| Summary | Qwen3\-8B is one of six open\-weighted dense models in the Qwen3 family, released under the Apache 2\.0 license\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen3\-8B\-Base (base model; Kind: finetune) |
| Model family | Qwen3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,190,735,360 parameters \(safetensors metadata\) |
| Context length | 40,960 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.3 GiB of safetensors weights \(16,381,516,776 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 13,232,997 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 1,342 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

_No specified fields are available in the publication data._

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
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
| Model card | [https://huggingface\.co/Qwen/Qwen3\-8B](<https://huggingface.co/Qwen/Qwen3-8B>) |
| Technical report | [https://arxiv\.org/abs/2505\.09388](<https://arxiv.org/abs/2505.09388>) |
| Code repository | [https://github\.com/QwenLM/Qwen3](<https://github.com/QwenLM/Qwen3>) |
| Citation | @misc\{qwen3technicalreport,<br>      title=\{Qwen3 Technical Report\}, <br>      author=\{Qwen Team\},<br>      year=\{2025\},<br>      eprint=\{2505\.09388\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2505\.09388\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
