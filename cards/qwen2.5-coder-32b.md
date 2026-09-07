# Model Card: Qwen2\.5\-Coder\-32B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-coder\-32b\.json](<./qwen2.5-coder-32b.json>)<br>
SHA-256: `1d6d02cd03316b70a42a6aed175dcb2e6a137f227e54cba2ffddb029dea6fb1d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-Coder\-32B |
| Name | Qwen2\.5\-Coder\-32B |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-11\-08 \(Hugging Face repository creation date\) |
| Version | 2e12b5f7bc878d424d222e224ed40aee564ec45f |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-32B (base model; Kind: finetune) |
| Model family | Qwen2\.5 Coder |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 32,763,876,352 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 61\.0 GiB of safetensors weights \(65,527,841,688 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a pretrained base model built on Qwen2\.5, trained on 5\.5 trillion tokens including source code, text\-code grounding, synthetic data, and other data\. |
| Training data size | 5\.5 trillion tokens |
| Adaptations | The model is a pretraining\-stage base model; no post\-training or alignment is applied\. The documentation recommends applying post\-training such as SFT, RLHF, or continued pretraining before conversational use\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,681 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 160 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen2\.5\-Coder\-32B is the current state\-of\-the\-art open\-source code LLM, with coding abilities matching GPT\-4o\. It also achieves state\-of\-the\-art code completion performance on five benchmarks: Humaneval\-Infilling, CrossCodeEval, CrossCodeLongEval, RepoEval, and SAFIM\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HumanEval | Not specified | 65\.9 | Not specified | Not reported |
| HumanEval | Not specified | 60\.4 | Not specified | Not reported |
| MBPP MBPP\+ | Not specified | 68\.2 | Not specified | Not reported |
| BigCodeBench | Not specified | 53\.6 | Not specified | Not reported |
| BigCodeBench | Not specified | 26\.4 | Not specified | Not reported |
| Python | Not specified | 65\.9 | Not specified | Not reported |
| Python | Not specified | 81\.5 | Not specified | Not reported |
| Python | Not specified | 49\.2 | Not specified | Not reported |
| Python | Not specified | 82\.1 | Not specified | Not reported |
| C\+\+ | Not specified | 68\.3 | Not specified | Not reported |
| C\# | Not specified | 68\.4 | Not specified | Not reported |
| C\# | Not specified | 68\.0 | Not specified | Not reported |
| C\# | Not specified | 91\.6 | Not specified | Not reported |
| Java | Not specified | 70\.9 | Not specified | Not reported |
| Java | Not specified | 56\.4 | Not specified | Not reported |
| Java | Not specified | 86\.6 | Not specified | Not reported |
| PHP | Not specified | 64\.6 | Not specified | Not reported |
| TS | Not specified | 66\.0 | Not specified | Not reported |
| Bash | Not specified | 39\.9 | Not specified | Not reported |
| JS | Not specified | 67\.1 | Not specified | Not reported |
| Average | Not specified | 63\.9 | Not specified | Not reported |
| Average ∗ | Not specified | 88\.3 | Not specified | Not reported |
| Average | Not specified | 57\.1 | Not specified | Not reported |
| Average | Not specified | 86\.8 | Not specified | Not reported |
| Average | Not specified | 36\.9 | Not specified | Not reported |
| Average | Not specified | 66\.4 | Not specified | Not reported |
| Average | Not specified | 51\.6 | Not specified | Not reported |
| Average | Not specified | 78\.5 | Not specified | Not reported |
| Humaneval\-FIM Java JavaScript | Not specified | 91\.0 | Not specified | Not reported |
| Humaneval\-FIM Java JavaScript | Not specified | 89\.4 | Not specified | Not reported |
| TypeScript | Not specified | 54\.9 | Not specified | Not reported |
| TypeScript | Not specified | 87\.0 | Not specified | Not reported |
| Chunk Completion | Not specified | 57\.3 | Not specified | Not reported |
| Chunk Completion | Not specified | 82\.1 | Not specified | Not reported |
| Function completion | Not specified | 16\.4 | Not specified | Not reported |
| Function completion | Not specified | 50\.8 | Not specified | Not reported |
| Line | Not specified | 90\.5 | Not specified | Not reported |
| Line | Not specified | 13\.6 | Not specified | Not reported |
| Function | Not specified | 57\.5 | Not specified | Not reported |
| Function | Not specified | 65\.1 | Not specified | Not reported |
| API | Not specified | 87\.6 | Not specified | Not reported |
| MATH 4\-shot | Not specified | 57\.2 | 4\-shot | Not reported |
| GSM8K 4\-shot | Not specified | 91\.1 | 4\-shot | Not reported |
| MMLUSTEM 5\-shot | Not specified | 75\.1 | 5\-shot | Not reported |
| TheoremQA 5\-shot | Not specified | 43\.1 | 5\-shot | Not reported |
| MMLU | Not specified | 79\.1 | Not specified | Not reported |
| MMLU | Not specified | 50\.4 | Not specified | Not reported |
| MMLU | Not specified | 77\.5 | Not specified | Not reported |
| HellaSwag | Not specified | 83\.0 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-Coder\-32B](<https://huggingface.co/Qwen/Qwen2.5-Coder-32B>) |
| Technical report | [https://arxiv\.org/abs/2409\.12186](<https://arxiv.org/abs/2409.12186>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5\-Coder](<https://github.com/QwenLM/Qwen2.5-Coder>) |
| Citation | @article\{hui2024qwen2,<br>      title=\{Qwen2\. 5\-Coder Technical Report\},<br>      author=\{Hui, Binyuan and Yang, Jian and Cui, Zeyu and Yang, Jiaxi and Liu, Dayiheng and Zhang, Lei and Liu, Tianyu and Zhang, Jiajun and Yu, Bowen and Dang, Kai and others\},<br>      journal=\{arXiv preprint arXiv:2409\.12186\},<br>      year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `risks.possible_risks`.
