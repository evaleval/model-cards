# Model Card: Qwen2\.5\-Coder\-14B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-coder\-14b\.json](<./qwen2.5-coder-14b.json>)<br>
SHA-256: `d54917509f130aefd07359993b9258d8e1ec758dd4c5282a5e11dfa4ba314aa7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-Coder\-14B |
| Name | Qwen2\.5\-Coder\-14B |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-11\-08 \(Hugging Face repository creation date\) |
| Version | f2ad5164aade432d6d56c24bb71589184d5d613d |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-14B (base model; Kind: finetune) |
| Model family | Qwen2\.5 Coder |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,770,033,664 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,540,133,960 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a pretrained base model; the documentation advises against using it directly for conversations and recommends applying post\-training such as SFT, RLHF, or continued pretraining, or fill\-in\-the\-middle tasks\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 157,808 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 88 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HumanEval | Not specified | 64\.0 | Not specified | Not reported |
| HumanEval | Not specified | 57\.9 | Not specified | Not reported |
| MBPP MBPP\+ | Not specified | 66\.7 | Not specified | Not reported |
| BigCodeBench | Not specified | 51\.8 | Not specified | Not reported |
| BigCodeBench | Not specified | 22\.3 | Not specified | Not reported |
| Python | Not specified | 64\.0 | Not specified | Not reported |
| Python | Not specified | 80\.5 | Not specified | Not reported |
| Python | Not specified | 47\.7 | Not specified | Not reported |
| Python | Not specified | 81\.7 | Not specified | Not reported |
| C\+\+ | Not specified | 69\.6 | Not specified | Not reported |
| C\# | Not specified | 63\.3 | Not specified | Not reported |
| C\# | Not specified | 66\.4 | Not specified | Not reported |
| C\# | Not specified | 91\.1 | Not specified | Not reported |
| Java | Not specified | 46\.8 | Not specified | Not reported |
| Java | Not specified | 54\.7 | Not specified | Not reported |
| Java | Not specified | 85\.7 | Not specified | Not reported |
| PHP | Not specified | 64\.6 | Not specified | Not reported |
| TS | Not specified | 69\.2 | Not specified | Not reported |
| Bash | Not specified | 39\.9 | Not specified | Not reported |
| JS | Not specified | 61\.5 | Not specified | Not reported |
| Average | Not specified | 59\.9 | Not specified | Not reported |
| Average ∗ | Not specified | 87\.7 | Not specified | Not reported |
| Average | Not specified | 55\.4 | Not specified | Not reported |
| Average | Not specified | 86\.1 | Not specified | Not reported |
| Average | Not specified | 36\.1 | Not specified | Not reported |
| Average | Not specified | 65\.8 | Not specified | Not reported |
| Average | Not specified | 79\.0 | Not specified | Not reported |
| Humaneval\-FIM Java JavaScript | Not specified | 91\.0 | Not specified | Not reported |
| Humaneval\-FIM Java JavaScript | Not specified | 88\.5 | Not specified | Not reported |
| TypeScript | Not specified | 52\.9 | Not specified | Not reported |
| TypeScript | Not specified | 86\.0 | Not specified | Not reported |
| Chunk Completion | Not specified | 56\.9 | Not specified | Not reported |
| Chunk Completion | Not specified | 81\.8 | Not specified | Not reported |
| Function completion | Not specified | 15\.4 | Not specified | Not reported |
| Function completion | Not specified | 49\.8 | Not specified | Not reported |
| Line | Not specified | 90\.1 | Not specified | Not reported |
| Line | Not specified | 14\.1 | Not specified | Not reported |
| Function | Not specified | 59\.5 | Not specified | Not reported |
| Function | Not specified | 63\.4 | Not specified | Not reported |
| API | Not specified | 87\.3 | Not specified | Not reported |
| API | Not specified | 50\.6 | Not specified | Not reported |
| MATH 4\-shot | Not specified | 52\.8 | 4\-shot | Not reported |
| GSM8K 4\-shot | Not specified | 88\.7 | 4\-shot | Not reported |
| MMLUSTEM 5\-shot | Not specified | 73\.9 | 5\-shot | Not reported |
| TheoremQA 5\-shot | Not specified | 39\.6 | 5\-shot | Not reported |
| MMLU | Not specified | 75\.2 | Not specified | Not reported |
| MMLU | Not specified | 49\.3 | Not specified | Not reported |
| MMLU | Not specified | 72\.4 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-Coder\-14B](<https://huggingface.co/Qwen/Qwen2.5-Coder-14B>) |
| Technical report | [https://arxiv\.org/abs/2409\.12186](<https://arxiv.org/abs/2409.12186>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5\-Coder](<https://github.com/QwenLM/Qwen2.5-Coder>) |
| Citation | @article\{hui2024qwen2,<br>      title=\{Qwen2\. 5\-Coder Technical Report\},<br>      author=\{Hui, Binyuan and Yang, Jian and Cui, Zeyu and Yang, Jiaxi and Liu, Dayiheng and Zhang, Lei and Liu, Tianyu and Zhang, Jiajun and Yu, Bowen and Dang, Kai and others\},<br>      journal=\{arXiv preprint arXiv:2409\.12186\},<br>      year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | Documentation advises against using the pretrained base model directly for conversations and recommends post\-training, so users who deploy it as\-is may over\-trust its outputs\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model's output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model's output when the model's output is likely incorrect\. Under\-reliance is the opposite, where the person doesn't trust the model but should\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | The card describes a base text\-generation model with no reported safety or factuality evaluations, so it can produce ungrounded or fabricated text\. | Hallucinations generate factually inaccurate or untruthful content relative to the model's training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
