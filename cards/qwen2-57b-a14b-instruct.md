# Model Card: Qwen2\-57B\-A14B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-57b\-a14b\-instruct\.json](<./qwen2-57b-a14b-instruct.json>)<br>
SHA-256: `eba8d5305b4aa6cffbe9250c17c3450272211dcb59e6cca5cdf78deb3f159d81`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-57B\-A14B\-Instruct |
| Name | Qwen2\-57B\-A14B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| Model type | Instruction\-tuned Mixture\-of\-Experts language model\. |
| License | apache\-2\.0 |
| Release date | 2024\-06\-04 \(Hugging Face repository creation date\) |
| Version | 50896d66b39f1425d63720541a66c7df13e053c0 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-57B\-A14B (base model; Kind: finetune) |
| Model family | Qwen2 A14B |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 57,408,658,944 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 106\.9 GiB of safetensors weights \(114,818,032,896 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was pretrained on a large amount of unspecified data, then post\-trained with supervised finetuning and direct preference optimization\. |
| Adaptations | The model was post\-trained with supervised finetuning and direct preference optimization after pretraining\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 12,607 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 83 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen2\-57B\-A14B\-Instruct handles contexts up to 64K tokens proficiently and supports a context length of up to 65,536 tokens\. It is also described as generally surpassing most open\-source models and showing competitiveness against proprietary models across benchmarks for language understanding and language generation\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 75\.4 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 52\.8 | Not specified | Not reported |
| GPQA | Not specified | 34\.3 | Not specified | Not reported |
| TheroemQA | Not specified | 33\.1 | Not specified | Not reported |
| MT\-Bench | Not specified | 8\.55 | Not specified | Not reported |
| HumanEval | Not specified | 79\.9 | Not specified | Not reported |
| MBPP | Not specified | 70\.9 | Not specified | Not reported |
| MultiPL\-E | Not specified | 66\.4 | Not specified | Not reported |
| EvalPlus | Not specified | 71\.6 | Not specified | Not reported |
| LiveCodeBench | Not specified | 25\.5 | Not specified | Not reported |
| GSM8K | Not specified | 79\.6 | Not specified | Not reported |
| C\-Eval | Not specified | 80\.5 | Not specified | Not reported |
| AlignBench | Not specified | 7\.36 | Not specified | Not reported |
| MMLU MMLU\-Pro | Not specified | 75\.4 | Not specified | Not reported |
| Knowledge | Not specified | 64\.15 | Not specified | Not reported |
| Knowledge | Not specified | 76\.80 | Not specified | Not reported |
| Exam | Not specified | 73\.67 | Not specified | Not reported |
| Comprehension | Not specified | 67\.52 | Not specified | Not reported |
| Comprehension | Not specified | 67\.92 | Not specified | Not reported |
| Coding | Not specified | 40\.66 | Not specified | Not reported |
| Coding | Not specified | 42\.37 | Not specified | Not reported |
| Reasoning | Not specified | 59\.89 | Not specified | Not reported |
| Avg\. | Not specified | 61\.63 | Not specified | Not reported |
| Avg\. | Not specified | 66\.03 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-57B\-A14B\-Instruct](<https://huggingface.co/Qwen/Qwen2-57B-A14B-Instruct>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | Instruction\-tuned open\-weight chat model with reported benchmark strengths but no reported factuality/grounding evaluation; long 65K context increases surface for generating plausible but ungrounded content\. | Hallucinations generate factually inaccurate or untruthful content relative to the model's training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | Model is described as surpassing most open\-source models and competitive with proprietary models, which can encourage over\-reliance in downstream use, while no human\-AI decision or calibration evidence is reported\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model's output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model's output when the model's output is likely incorrect\. Under\-reliance is the opposite, where the person doesn't trust the model but should\. |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | Large Mixture\-of\-Experts model pretrained on a large amount of data and supporting 65K\-token contexts; training and long\-context inference plausibly increase energy/water use\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
