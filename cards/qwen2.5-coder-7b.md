# Model Card: Qwen2\.5\-Coder\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-coder\-7b\.json](<./qwen2.5-coder-7b.json>)<br>
SHA-256: `a292916d757b54b10d7c48843954ef3ebd7f4aa35aea0d2b74c915ca3361dd88`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-Coder\-7B |
| Name | Qwen2\.5\-Coder\-7B |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-09\-16 \(Hugging Face repository creation date\) |
| Version | 0396a76181e127dfc13e5c5ec48a8cee09938b02 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B (base model; Kind: finetune) |
| Model family | Qwen2\.5 Coder |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,864 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model card states that the training stage is pretraining, with no post\-training or alignment adaptations described\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 580,134 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 166 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer\-reported results for Qwen2\.5\-Coder\-7B cover code completion, code reasoning, general natural language, and instruct\-model evaluations, with scores varying by task and setting\. The model&\#x27;s strongest reported figures include 86\.1 on the Line benchmark and 83\.9 on API, while math and reasoning scores are lower, such as 46\.6 on MATH 4\-shot and 34\.0 on TheoremQA 5\-shot\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HumanEval | Not specified | 61\.6 | Not specified | Not reported |
| HumanEval | Not specified | 53\.0 | Not specified | Not reported |
| MBPP MBPP\+ | Not specified | 62\.9 | Not specified | Not reported |
| BigCodeBench | Not specified | 45\.8 | Not specified | Not reported |
| BigCodeBench | Not specified | 16\.2 | Not specified | Not reported |
| Python | Not specified | 61\.6 | Not specified | Not reported |
| Python | Not specified | 79\.7 | Not specified | Not reported |
| Python | Not specified | 42\.4 | Not specified | Not reported |
| Python | Not specified | 78\.6 | Not specified | Not reported |
| C\+\+ | Not specified | 62\.1 | Not specified | Not reported |
| C\# | Not specified | 60\.8 | Not specified | Not reported |
| C\# | Not specified | 59\.7 | Not specified | Not reported |
| C\# | Not specified | 87\.9 | Not specified | Not reported |
| Java | Not specified | 53\.2 | Not specified | Not reported |
| Java | Not specified | 48\.1 | Not specified | Not reported |
| Java | Not specified | 82\.6 | Not specified | Not reported |
| PHP | Not specified | 59\.0 | Not specified | Not reported |
| TS | Not specified | 64\.2 | Not specified | Not reported |
| Bash | Not specified | 38\.6 | Not specified | Not reported |
| JS | Not specified | 60\.3 | Not specified | Not reported |
| Average | Not specified | 57\.5 | Not specified | Not reported |
| Average ∗ | Not specified | 86\.2 | Not specified | Not reported |
| Average | Not specified | 49\.3 | Not specified | Not reported |
| Average | Not specified | 83\.1 | Not specified | Not reported |
| Average | Not specified | 33\.4 | Not specified | Not reported |
| Average | Not specified | 63\.8 | Not specified | Not reported |
| Average | Not specified | 46\.3 | Not specified | Not reported |
| Average | Not specified | 75\.1 | Not specified | Not reported |
| Humaneval\-FIM Java JavaScript | Not specified | 88\.5 | Not specified | Not reported |
| Humaneval\-FIM Java JavaScript | Not specified | 87\.6 | Not specified | Not reported |
| TypeScript | Not specified | 46\.8 | Not specified | Not reported |
| TypeScript | Not specified | 83\.4 | Not specified | Not reported |
| Chunk Completion | Not specified | 52\.4 | Not specified | Not reported |
| Chunk Completion | Not specified | 79\.3 | Not specified | Not reported |
| Function completion | Not specified | 14\.4 | Not specified | Not reported |
| Function completion | Not specified | 48\.4 | Not specified | Not reported |
| Line | Not specified | 86\.1 | Not specified | Not reported |
| Line | Not specified | 13\.2 | Not specified | Not reported |
| Function | Not specified | 55\.2 | Not specified | Not reported |
| Function | Not specified | 58\.4 | Not specified | Not reported |
| API | Not specified | 83\.9 | Not specified | Not reported |
| MATH 4\-shot | Not specified | 46\.6 | 4\-shot | Not reported |
| GSM8K 4\-shot | Not specified | 83\.9 | 4\-shot | Not reported |
| MMLUSTEM 5\-shot | Not specified | 67\.6 | 5\-shot | Not reported |
| TheoremQA 5\-shot | Not specified | 34\.0 | 5\-shot | Not reported |
| MMLU | Not specified | 68\.0 | Not specified | Not reported |
| MMLU | Not specified | 40\.1 | Not specified | Not reported |
| MMLU | Not specified | 66\.6 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-Coder\-7B](<https://huggingface.co/Qwen/Qwen2.5-Coder-7B>) |
| Technical report | [https://arxiv\.org/abs/2409\.12186](<https://arxiv.org/abs/2409.12186>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5\-Coder](<https://github.com/QwenLM/Qwen2.5-Coder>) |
| Citation | @article\{hui2024qwen2,<br>      title=\{Qwen2\. 5\-Coder Technical Report\},<br>      author=\{Hui, Binyuan and Yang, Jian and Cui, Zeyu and Yang, Jiaxi and Liu, Dayiheng and Zhang, Lei and Liu, Tianyu and Zhang, Jiajun and Yu, Bowen and Dang, Kai and others\},<br>      journal=\{arXiv preprint arXiv:2409\.12186\},<br>      year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | The card reports low math/reasoning scores \(46\.6 MATH, 34\.0 TheoremQA\) for a code\-focused model, indicating plausible factual/reasoning inaccuracies in generated content\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
