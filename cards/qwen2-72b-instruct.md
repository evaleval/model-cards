# Model Card: Qwen2\-72B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-72b\-instruct\.json](<./qwen2-72b-instruct.json>)<br>
SHA-256: `f623851214af386096aeb97dcfb6a719b893157ec3fe1eef06c40fb43e3c9f59`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-72B\-Instruct |
| Name | Qwen2\-72B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| Model type | text\-generation |
| License | other |
| Release date | 2024\-05\-28 \(Hugging Face repository creation date\) |
| Version | c867f763ef53f2ea9d9b31ee8501273dedd391eb |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-72B (base model; Kind: finetune) |
| Model family | Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 72,706,203,648 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 135\.4 GiB of safetensors weights \(145,412,518,888 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was pretrained on a large amount of unspecified data, then post\-trained with supervised finetuning and direct preference optimization\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 31,166 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 718 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen2\-72B\-Instruct was evaluated on 16 benchmarks across various domains, with strengths in language understanding, coding, and mathematics, and capable of handling information extraction tasks within a 128k context\. It is described as balancing better capabilities with alignment to human values, and comparisons with similar\-sized instruction\-tuned models are provided\. |
| Human evaluations | The developer reports comprehensive evaluation of Qwen2\-72B\-Instruct on 16 benchmarks across various domains\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| TheroemQA | Not specified | 44\.4 | Not specified | Not reported |
| MT\-Bench | Not specified | 9\.12 | Not specified | Not reported |
| Arena\-Hard | Not specified | 48\.1 | Not specified | Not reported |
| EvalPlus | Not specified | 79\.0 | Not specified | Not reported |
| LiveCodeBench | Not specified | 35\.7 | Not specified | Not reported |
| C\-Eval | Not specified | 83\.8 | Not specified | Not reported |
| AlignBench | Not specified | 8\.27 | Not specified | Not reported |
| Theorem QA | Not specified | 44\.4 | Not specified | Not reported |
| LiveCodeBench v1 | Not specified | 35\.7 | Not specified | Not reported |
| MixEval | Not specified | 86\.7 | Not specified | Not reported |
| IFEval strict\-prompt | Not specified | 77\.6 | Not specified | Not reported |
| Knowledge | Not specified | 76\.19 | Not specified | Not reported |
| Knowledge | Not specified | 83\.00 | Not specified | Not reported |
| Exam | Not specified | 75\.65 | Not specified | Not reported |
| Comprehension | Not specified | 74\.72 | Not specified | Not reported |
| Comprehension | Not specified | 73\.58 | Not specified | Not reported |
| Coding | Not specified | 49\.53 | Not specified | Not reported |
| Coding | Not specified | 53\.03 | Not specified | Not reported |
| Reasoning | Not specified | 70\.59 | Not specified | Not reported |
| Avg\. | Not specified | 69\.58 | Not specified | Not reported |
| Avg\. | Not specified | 72\.94 | Not specified | Not reported |
| Arabic | Not specified | 3\.86 | Not specified | Not reported |
| French | Not specified | 4\.01 | Not specified | Not reported |
| Indonesian | Not specified | 3\.83 | Not specified | Not reported |
| Japanese | Not specified | 3\.63 | Not specified | Not reported |
| Korean | Not specified | 4\.14 | Not specified | Not reported |
| Portuguese | Not specified | 3\.97 | Not specified | Not reported |
| Russian | Not specified | 4\.15 | Not specified | Not reported |
| Spanish | Not specified | 4\.1 | Not specified | Not reported |
| Thai | Not specified | 3\.75 | Not specified | Not reported |
| Vietnamese | Not specified | 3\.91 | Not specified | Not reported |
| Average | Not specified | 3\.93 | Not specified | Not reported |
| Illegal | Not specified | 0 | Not specified | Not reported |
| Fraud | Not specified | 2\.41 | Not specified | Not reported |
| Pornography | Not specified | 22\.91 | Not specified | Not reported |
| Privacy | Not specified | 2\.47 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-72B\-Instruct](<https://huggingface.co/Qwen/Qwen2-72B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | text\-generation model with reported strengths in language understanding, coding, and mathematics but no reported factuality or hallucination evaluation in the card summary | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.safety_evals`, `links.system_card`.
