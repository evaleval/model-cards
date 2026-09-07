# Model Card: Qwen2\.5\-Coder\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-coder\-7b\-instruct\.json](<./qwen2.5-coder-7b-instruct.json>)<br>
SHA-256: `e38e969faf9677e1d867fec74dda51e63b33d5a3b46a968063d2189d52bcf42b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-Coder\-7B\-Instruct |
| Name | Qwen2\.5\-Coder\-7B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-09\-17 \(Hugging Face repository creation date\) |
| Version | c03e6d358207e414f1eca0bb1891e29f1db0e242 |
| Summary | This repository contains the instruction\-tuned 7B Qwen2\.5\-Coder model, a code\-specific causal language model in the Qwen2\.5\-Coder series\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-Coder\-7B (base model; Kind: finetune) |
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
| Adaptations | The model card states its training stage as pretraining and post\-training\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 2,301,302 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 792 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the 7B instruct model showed exceptional accuracy in code generation and outperformed other instruct models of comparable size, with notable scores of 41\.0% on the full BigCodeBench subset and 18\.2% on the hard subset\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HumanEval | score | 88\.4 | Not specified | Not reported |
| HumanEval | score | 84\.1 | Not specified | Not reported |
| MBPP | score | 83\.5 | Not specified | Not reported |
| MBPP | score | 71\.7 | Not specified | Not reported |
| BigCodeBench | score | 41\.0 | Not specified | Not reported |
| BigCodeBench | score | 18\.2 | Not specified | Not reported |
| LiveCodeBench Pass@1 | pass@1 | 18\.2 | Not specified | Not reported |
| Python | Not specified | 87\.8 | Not specified | Not reported |
| Java | Not specified | 76\.5 | Not specified | Not reported |
| C\+\+ | Not specified | 75\.6 | Not specified | Not reported |
| C\# | Not specified | 80\.3 | Not specified | Not reported |
| TS | Not specified | 81\.8 | Not specified | Not reported |
| JS | Not specified | 83\.2 | Not specified | Not reported |
| PHP | Not specified | 78\.3 | Not specified | Not reported |
| Bash | Not specified | 48\.7 | Not specified | Not reported |
| Average | Not specified | 76\.5 | Not specified | Not reported |
| MATH | Not specified | 66\.8 | Not specified | Not reported |
| MATH | Not specified | 42\.5 | Not specified | Not reported |
| GSM8K | Not specified | 86\.7 | Not specified | Not reported |
| GSM8K | Not specified | 68\.7 | Not specified | Not reported |
| GaoKao2023en | Not specified | 60\.5 | Not specified | Not reported |
| GaoKao2023en | Not specified | 45\.6 | Not specified | Not reported |
| OlympiadBench | Not specified | 29\.8 | Not specified | Not reported |
| OlympiadBench | Not specified | 58\.6 | Not specified | Not reported |
| CollegeMath | Not specified | 43\.5 | Not specified | Not reported |
| CollegeMath | Not specified | 61\.4 | Not specified | Not reported |
| AIME24 | Not specified | 10\.0 | Not specified | Not reported |
| AIME24 | Not specified | 35\.6 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-Coder\-7B\-Instruct](<https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2409\.12186](<https://arxiv.org/abs/2409.12186>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5\-Coder](<https://github.com/QwenLM/Qwen2.5-Coder>) |
| Citation | @article\{hui2024qwen2,<br>      title=\{Qwen2\. 5\-Coder Technical Report\},<br>      author=\{Hui, Binyuan and Yang, Jian and Cui, Zeyu and Yang, Jiaxi and Liu, Dayiheng and Zhang, Lei and Liu, Tianyu and Zhang, Jiajun and Yu, Bowen and Dang, Kai and others\},<br>      journal=\{arXiv preprint arXiv:2409\.12186\},<br>      year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | instruction\-tuned code model reports only code\-generation benchmark scores and no factuality/grounding evaluation, so it can plausibly generate plausible but incorrect code or explanations\. | Hallucinations generate factually inaccurate or untruthful content relative to the model's training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | developer reports exceptional accuracy in code generation, which can encourage users to trust generated code without sufficient verification\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model's output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model's output when the model's output is likely incorrect\. Under\-reliance is the opposite, where the person doesn't trust the model but should\. |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | open\-weight code model trained on code can be prompted with copyrighted code snippets, and the card does not report any filtering or IP safeguards\. | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | open\-weight code assistant can be used in development contexts where users paste proprietary source code into prompts, and the card reports no data\-handling protections\. | Confidential information might be included as a part of the prompt that is sent to the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
