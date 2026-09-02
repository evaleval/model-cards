# Model Card: DeepSeek\-V3\-Base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-v3\-base\.json](<./deepseek-v3-base.json>)<br>
SHA-256: `ea53d90c6ec6cc06803c0cbdd344abf6153bdea0d7d86d9f055ad17e117eaf3f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | deepseek\-ai/DeepSeek\-V3\-Base |
| Name | DeepSeek\-V3\-Base |
| Developed by | deepseek\-ai |
| Model type | text\-generation |
| License | the Model License; commercial use supported: https://huggingface\.co/deepseek\-ai/DeepSeek\-V3\-Base/blob/afb92e1fa402c2be2a9eb085312bb02e0384d6c7/LICENSE\-MODEL |
| Version | afb92e1fa402c2be2a9eb085312bb02e0384d6c7 |
| Summary | DeepSeek\-V3\-Base is listed with 671B total parameters, 37B activated parameters per token, 128K context length\. |

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
| Input / output | input: text<br>output: text<br>model stage: pretrained/base |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Publisher\-reported pretraining scale: 14\.8 trillion tokens; the corpus is described as diverse and quality\-filtered\. |
| Training data size | 14\.8 trillion tokens |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Public Hugging Face repository with declared weight files |
| Downloads | 11,497 at frozen Hugging Face metadata snapshot |
| Likes | 1,706 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README provides 32 exact\-target benchmark scores; examples: Pile\-test: 0\.548; BBH: 87\.5; MMLU: 87\.1\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Pile\-test | BPB | 0\.548 | README table; setting not stated | Not reported |
| BBH | EM | 87\.5 | 3\-shot | Not reported |
| MMLU | Acc\. | 87\.1 | 5\-shot | Not reported |
| MMLU\-Redux | Acc\. | 86\.2 | 5\-shot | Not reported |
| MMLU\-Pro | Acc\. | 64\.4 | 5\-shot | Not reported |
| DROP | F1 | 89\.0 | 3\-shot | Not reported |
| ARC\-Easy | Acc\. | 98\.9 | 25\-shot | Not reported |
| ARC\-Challenge | Acc\. | 95\.3 | 25\-shot | Not reported |
| HellaSwag | Acc\. | 88\.9 | 10\-shot | Not reported |
| PIQA | Acc\. | 84\.7 | 0\-shot | Not reported |
| WinoGrande | Acc\. | 84\.9 | 5\-shot | Not reported |
| RACE\-Middle | Acc\. | 67\.1 | 5\-shot | Not reported |
| RACE\-High | Acc\. | 51\.3 | 5\-shot | Not reported |
| TriviaQA | EM | 82\.9 | 5\-shot | Not reported |
| NaturalQuestions | EM | 40\.0 | 5\-shot | Not reported |
| AGIEval | Acc\. | 79\.6 | 0\-shot | Not reported |
| HumanEval | Pass@1 | 65\.2 | 0\-shot | Not reported |
| MBPP | Pass@1 | 75\.4 | 3\-shot | Not reported |
| LiveCodeBench\-Base | Pass@1 | 19\.4 | 3\-shot | Not reported |
| CRUXEval\-I | Acc\. | 67\.3 | 2\-shot | Not reported |
| CRUXEval\-O | Acc\. | 69\.8 | 2\-shot | Not reported |
| GSM8K | EM | 89\.3 | 8\-shot | Not reported |
| MATH | EM | 61\.6 | 4\-shot | Not reported |
| MGSM | EM | 79\.8 | 8\-shot | Not reported |
| CMath | EM | 90\.7 | 3\-shot | Not reported |
| CLUEWSC | EM | 82\.7 | 5\-shot | Not reported |
| C\-Eval | Acc\. | 90\.1 | 5\-shot | Not reported |
| CMMLU | Acc\. | 88\.8 | 5\-shot | Not reported |
| CMRC | EM | 76\.3 | 1\-shot | Not reported |
| C3 | Acc\. | 78\.6 | 0\-shot | Not reported |
| CCPM | Acc\. | 92\.0 | 0\-shot | Not reported |
| MMMLU\-non\-English | Acc\. | 79\.4 | 5\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/deepseek\-ai/DeepSeek\-V3\-Base/blob/afb92e1fa402c2be2a9eb085312bb02e0384d6c7/README\.md](<https://huggingface.co/deepseek-ai/DeepSeek-V3-Base/blob/afb92e1fa402c2be2a9eb085312bb02e0384d6c7/README.md>) |
| Technical report | [https://arxiv\.org/abs/2412\.19437](<https://arxiv.org/abs/2412.19437>) |
| Code repository | [https://github\.com/deepseek\-ai/DeepSeek\-V3](<https://github.com/deepseek-ai/DeepSeek-V3>) |
| Citation | @misc\{deepseekai2024deepseekv3technicalreport,<br>      title=\{DeepSeek\-V3 Technical Report\}, <br>      author=\{DeepSeek\-AI\},<br>      year=\{2024\},<br>      eprint=\{2412\.19437\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2412\.19437\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
