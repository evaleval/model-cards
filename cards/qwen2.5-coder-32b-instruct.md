# Model Card: Qwen2\.5\-Coder\-32B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-coder\-32b\-instruct\.json](<./qwen2.5-coder-32b-instruct.json>)<br>
SHA-256: `648351fc692702c8f7cce6bcf95283257140a5889bad0bdf2923a1f98bf36071`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-Coder\-32B\-Instruct |
| Name | Qwen2\.5\-Coder\-32B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-11\-06 \(Hugging Face repository creation date\) |
| Version | 381fc969f78efac66bc87ff7ddeadb7e73c218a7 |
| Summary | Qwen2\.5\-Coder\-32B\-Instruct is the instruction\-tuned 32B model in the Qwen2\.5\-Coder series, described as a current state\-of\-the\-art open\-source code model with coding capabilities comparable to GPT\-4o\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-Coder\-32B (base model; Kind: finetune) |
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
| Adaptations | The model underwent both pretraining and post\-training stages\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,703,797 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2,125 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the 32B Instruct model is the current state\-of\-the\-art open\-source code model, matching GPT\-4o on coding capabilities and achieving top open\-source performance on EvalPlus, LiveCodeBench, and BigCodeBench\. It also scores 73\.7 on Aider, 65\.9 on McEval, and 75\.2 on MdEval, with competitive performance against GPT\-4o\. |
| Human evaluations | The developer constructed an internal annotated code preference benchmark called Code Arena, similar to Arena Hard, to evaluate alignment with human preferences, and reports that the results demonstrate the model&\#x27;s advantages in preference alignment\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HumanEval | score | 92\.7 | Not specified | Not reported |
| HumanEval | score | 87\.2 | Not specified | Not reported |
| MBPP | score | 90\.2 | Not specified | Not reported |
| MBPP | score | 75\.1 | Not specified | Not reported |
| BigCodeBench | score | 49\.6 | Not specified | Not reported |
| BigCodeBench | score | 27\.0 | Not specified | Not reported |
| LiveCodeBench Pass@1 | pass@1 | 31\.4 | Not specified | Not reported |
| Python | Not specified | 92\.7 | Not specified | Not reported |
| Java | Not specified | 80\.4 | Not specified | Not reported |
| C\+\+ | Not specified | 79\.5 | Not specified | Not reported |
| C\# | Not specified | 82\.9 | Not specified | Not reported |
| TS | Not specified | 86\.8 | Not specified | Not reported |
| JS | Not specified | 85\.7 | Not specified | Not reported |
| PHP | Not specified | 78\.9 | Not specified | Not reported |
| Bash | Not specified | 48\.1 | Not specified | Not reported |
| Average | Not specified | 79\.4 | Not specified | Not reported |
| MATH | Not specified | 76\.4 | Not specified | Not reported |
| MATH | Not specified | 55\.0 | Not specified | Not reported |
| GSM8K | Not specified | 93\.0 | Not specified | Not reported |
| GSM8K | Not specified | 77\.6 | Not specified | Not reported |
| GaoKao2023en | Not specified | 68\.3 | Not specified | Not reported |
| GaoKao2023en | Not specified | 62\.3 | Not specified | Not reported |
| OlympiadBench | Not specified | 42\.5 | Not specified | Not reported |
| OlympiadBench | Not specified | 79\.9 | Not specified | Not reported |
| CollegeMath | Not specified | 47\.7 | Not specified | Not reported |
| CollegeMath | Not specified | 68\.9 | Not specified | Not reported |
| AIME24 | Not specified | 20\.0 | Not specified | Not reported |
| AIME24 | Not specified | 41\.8 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-Coder\-32B\-Instruct](<https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2409\.12186](<https://arxiv.org/abs/2409.12186>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5\-Coder](<https://github.com/QwenLM/Qwen2.5-Coder>) |
| Citation | @article\{hui2024qwen2,<br>      title=\{Qwen2\. 5\-Coder Technical Report\},<br>      author=\{Hui, Binyuan and Yang, Jian and Cui, Zeyu and Yang, Jiaxi and Liu, Dayiheng and Zhang, Lei and Liu, Tianyu and Zhang, Jiajun and Yu, Bowen and Dang, Kai and others\},<br>      journal=\{arXiv preprint arXiv:2409\.12186\},<br>      year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | open\-weight code model with no reported filtering or safety evaluation for code prompts \-&gt; users may paste copyrighted code into prompts | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | open\-weight code model with no reported data handling or privacy safeguards \-&gt; users may include confidential code or data in prompts | Confidential information might be included as a part of the prompt that is sent to the model\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | code generation model evaluated only on coding benchmarks, no factual grounding or hallucination evaluation reported \-&gt; may generate plausible but incorrect code/APIs | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | reported as state\-of\-the\-art matching GPT\-4o on coding, with no calibration or human oversight guidance \-&gt; users may over\-trust generated code | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.safety_evals`, `links.system_card`.
