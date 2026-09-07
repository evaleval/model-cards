# Model Card: Qwen2\.5\-Coder\-14B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-coder\-14b\-instruct\.json](<./qwen2.5-coder-14b-instruct.json>)<br>
SHA-256: `c6e7838ed24901c0003e2d83a13b637a09a189e089cdac5e1ee1f07bd85a347c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-Coder\-14B\-Instruct |
| Name | Qwen2\.5\-Coder\-14B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-11\-06 \(Hugging Face repository creation date\) |
| Version | aedcc2d42b622764e023cf882b6652e646b95671 |
| Summary | This repository contains the instruction\-tuned 14B Qwen2\.5\-Coder model, an official aligned model that can chat directly\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-Coder\-14B (base model; Kind: finetune) |
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
| Adaptations | The model underwent pretraining and post\-training stages\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,919,973 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 184 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HumanEval | score | 89\.6 | Not specified | Not reported |
| HumanEval | score | 87\.2 | Not specified | Not reported |
| MBPP | score | 86\.2 | Not specified | Not reported |
| MBPP | score | 72\.8 | Not specified | Not reported |
| BigCodeBench | score | 48\.4 | Not specified | Not reported |
| BigCodeBench | score | 22\.2 | Not specified | Not reported |
| LiveCodeBench Pass@1 | pass@1 | 23\.4 | Not specified | Not reported |
| Python | Not specified | 89\.0 | Not specified | Not reported |
| Java | Not specified | 79\.7 | Not specified | Not reported |
| C\+\+ | Not specified | 85\.1 | Not specified | Not reported |
| C\# | Not specified | 84\.2 | Not specified | Not reported |
| TS | Not specified | 86\.8 | Not specified | Not reported |
| JS | Not specified | 84\.5 | Not specified | Not reported |
| PHP | Not specified | 80\.1 | Not specified | Not reported |
| Bash | Not specified | 47\.5 | Not specified | Not reported |
| Average | Not specified | 79\.6 | Not specified | Not reported |
| MATH | Not specified | 66\.8 | Not specified | Not reported |
| MATH | Not specified | 50\.0 | Not specified | Not reported |
| GSM8K | Not specified | 94\.2 | Not specified | Not reported |
| GSM8K | Not specified | 71\.7 | Not specified | Not reported |
| GaoKao2023en | Not specified | 66\.0 | Not specified | Not reported |
| GaoKao2023en | Not specified | 55\.6 | Not specified | Not reported |
| OlympiadBench | Not specified | 40\.1 | Not specified | Not reported |
| OlympiadBench | Not specified | 66\.5 | Not specified | Not reported |
| CollegeMath | Not specified | 47\.3 | Not specified | Not reported |
| CollegeMath | Not specified | 66\.2 | Not specified | Not reported |
| AIME24 | Not specified | 10\.0 | Not specified | Not reported |
| AIME24 | Not specified | 36\.8 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-Coder\-14B\-Instruct](<https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2409\.12186](<https://arxiv.org/abs/2409.12186>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5\-Coder](<https://github.com/QwenLM/Qwen2.5-Coder>) |
| Citation | @article\{hui2024qwen2,<br>      title=\{Qwen2\. 5\-Coder Technical Report\},<br>      author=\{Hui, Binyuan and Yang, Jian and Cui, Zeyu and Yang, Jiaxi and Liu, Dayiheng and Zhang, Lei and Liu, Tianyu and Zhang, Jiajun and Yu, Bowen and Dang, Kai and others\},<br>      journal=\{arXiv preprint arXiv:2409\.12186\},<br>      year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | Instruction\-tuned text\-output chat model with no reported evaluation of factual accuracy or grounding; code generation can produce plausible but incorrect code\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | Instruction\-tuned chat model that can directly answer coding questions; no reported calibration or human\-AI decision support evaluation, so users may over\-trust generated code\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | Open\-weight chat model accepts text prompts; users may paste proprietary or sensitive code into prompts, and the card reports no data handling or privacy safeguards\. | Confidential information might be included as a part of the prompt that is sent to the model\. |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | Open\-weight code model accepts text prompts; users may paste copyrighted code or other IP into prompts, and the card reports no IP protections\. | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | Dense decoder\-only 14B model with pretraining and post\-training; card reports no efficiency or environmental impact information\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
