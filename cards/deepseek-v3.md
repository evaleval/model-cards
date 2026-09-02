# Model Card: DeepSeek\-V3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-v3\.json](<./deepseek-v3.json>)<br>
SHA-256: `c333b2a20a51e339e68d81c91f211f9264d0a2a2752c71cefe231224f144dc84`

## Identity

| Field | Value |
| --- | --- |
| Model ID | deepseek\-ai/DeepSeek\-V3 |
| Name | DeepSeek\-V3 |
| Developed by | deepseek\-ai |
| Model type | text\-generation |
| License | the Model License; commercial use supported: https://huggingface\.co/deepseek\-ai/DeepSeek\-V3/blob/e815299b0bcbac849fa540c768ef21845365c9eb/LICENSE\-MODEL |
| Version | e815299b0bcbac849fa540c768ef21845365c9eb |
| Summary | DeepSeek\-V3 is listed with 671B total parameters, 37B activated parameters per token, 128K context length\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | deepseek\_v3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 684,531,386,000 total stored parameters \(safetensors metadata\); README architecture row reports 671B total model parameters, 37B activated per token |
| Context length | 128K tokens \(README\-declared context length\) |
| Precision | Predominantly FP8 E4M3 stored tensor weights; additional dtypes: bfloat16, float32 \(safetensors parameter\-count metadata\) |
| Model size | 641\.29 GiB estimated tensor payload \(688,574,839,360 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Publisher\-reported pretraining scale: 14\.8 trillion tokens; the corpus is described as diverse and quality\-filtered\. |
| Training data size | 14\.8 trillion tokens |
| Adaptations | Post\-training uses supervised fine\-tuning and reinforcement learning\. The README also describes distilling long\-chain\-of\-thought reasoning from a DeepSeek\-R1\-series model into DeepSeek\-V3\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Public Hugging Face repository with declared weight files |
| Downloads | 1,078,839 at frozen Hugging Face metadata snapshot |
| Likes | 4,177 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README provides 24 exact\-target benchmark scores; examples: MMLU: 88\.5; MMLU\-Redux: 89\.1; MMLU\-Pro: 75\.9\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | EM | 88\.5 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| MMLU\-Redux | EM | 89\.1 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| MMLU\-Pro | EM | 75\.9 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| DROP \(3\-shot F1\) | README\-reported score | 91\.6 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| IF\-Eval \(Prompt Strict\) | README\-reported score | 86\.1 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| GPQA\-Diamond | Pass@1 | 59\.1 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| SimpleQA \(Correct\) | README\-reported score | 24\.9 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| FRAMES | Acc\. | 73\.3 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| LongBench v2 | Acc\. | 48\.7 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| HumanEval\-Mul | Pass@1 | 82\.6 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| LiveCodeBench \(Pass@1\-COT\) | README\-reported score | 40\.5 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| LiveCodeBench | Pass@1 | 37\.6 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| Codeforces \(Percentile\) | README\-reported score | 51\.6 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| SWE Verified \(Resolved\) | README\-reported score | 42\.0 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| Aider\-Edit | Acc\. | 79\.7 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| Aider\-Polyglot | Acc\. | 49\.6 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| AIME 2024 | Pass@1 | 39\.2 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| MATH\-500 | EM | 90\.2 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| CNMO 2024 | Pass@1 | 43\.2 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| CLUEWSC | EM | 90\.9 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| C\-Eval | EM | 86\.5 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| C\-SimpleQA \(Correct\) | README\-reported score | 64\.8 | Standard Benchmarks \(Models larger than 67B\); setting not stated | Not reported |
| Arena\-Hard | README\-reported score | 85\.5 | Open Ended Generation Evaluation; setting not stated | Not reported |
| AlpacaEval 2\.0 | README\-reported score | 70\.0 | Open Ended Generation Evaluation; setting not stated | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/deepseek\-ai/DeepSeek\-V3/blob/e815299b0bcbac849fa540c768ef21845365c9eb/README\.md](<https://huggingface.co/deepseek-ai/DeepSeek-V3/blob/e815299b0bcbac849fa540c768ef21845365c9eb/README.md>) |
| Technical report | [https://arxiv\.org/abs/2412\.19437](<https://arxiv.org/abs/2412.19437>) |
| Code repository | [https://github\.com/deepseek\-ai/DeepSeek\-V3](<https://github.com/deepseek-ai/DeepSeek-V3>) |
| Citation | @misc\{deepseekai2024deepseekv3technicalreport,<br>      title=\{DeepSeek\-V3 Technical Report\}, <br>      author=\{DeepSeek\-AI\},<br>      year=\{2024\},<br>      eprint=\{2412\.19437\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2412\.19437\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
