# Model Card: gemma\-2\-27b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-2\-27b\.json](<./gemma-2-27b.json>)<br>
SHA-256: `bfacbe97c8415a5a66e763afda14ac6379a0436a0211f99344d30896439801dc`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-2\-27b |
| Name | gemma\-2\-27b |
| Developed by | google \(Hub organization\) |
| Model type | text\-to\-text, decoder\-only large language model |
| License | gemma |
| Release date | 2024\-06\-24 \(Hugging Face repository creation date\) |
| Version | 938270f5272feb02779b55c2bb2fffdd0f53ff0c |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma 2 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 27,227,128,320 parameters \(safetensors metadata\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 101\.4 GiB of safetensors weights \(108,908,573,008 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The target checkpoint is a 27B model trained from scratch on 13 trillion tokens of primarily\-English data\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 10,192 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 211 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the 27B model performs best in its size category and is competitive with a larger model trained for longer, based on evaluations across a large collection of datasets and metrics\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | top\-1 | 75\.2 | 5\-shot | Not reported |
| HellaSwag | Not specified | 86\.4 | 10\-shot | Not reported |
| PIQA | Not specified | 83\.2 | 0\-shot | Not reported |
| SocialIQA | Not specified | 53\.7 | 0\-shot | Not reported |
| BoolQ | Not specified | 84\.8 | 0\-shot | Not reported |
| WinoGrande | score | 83\.7 | Not specified | Not reported |
| ARC\-e | Not specified | 88\.6 | 0\-shot | Not reported |
| ARC\-c | Not specified | 71\.4 | 25\-shot | Not reported |
| TriviaQA | Not specified | 83\.7 | 5\-shot | Not reported |
| Natural Questions | Not specified | 34\.5 | 5\-shot | Not reported |
| HumanEval | pass@1 | 51\.8 | Not specified | Not reported |
| MBPP | Not specified | 62\.6 | 3\-shot | Not reported |
| GSM8K | Not specified | 74\.0 | 5\-shot | Not reported |
| MATH | Not specified | 42\.3 | 4\-shot | Not reported |
| AGIEval | Not specified | 55\.1 | 5\-shot | Not reported |
| BIG\-Bench | Not specified | 74\.9 | 3\-shot CoT | Not reported |
| MMLU | Not specified | 75\.2 | Not specified | Not reported |
| GSM8K | Not specified | 74 | Not specified | Not reported |
| ARC\-c | Not specified | 71\.4 | Not specified | Not reported |
| HellaSwag | Not specified | 86\.4 | Not specified | Not reported |
| DROP | F1 | 74\.2 | 3\-shot | Not reported |
| BBH | Not specified | 74\.9 | 3\-shot CoT | Not reported |
| Winogrande | Not specified | 83\.7 | 5\-shot | Not reported |
| SIQA | Not specified | 53\.7 | 0\-shot | Not reported |
| NQ | Not specified | 34\.5 | 5\-shot | Not reported |
| Average | Not specified | 74\.4 | Not specified | Not reported |
| Average | Not specified | 69\.4 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-2\-27b](<https://huggingface.co/google/gemma-2-27b>) |
| Technical report | [https://arxiv\.org/abs/2408\.00118](<https://arxiv.org/abs/2408.00118>) |
| Code repository | [https://github\.com/huggingface/local\-gemma](<https://github.com/huggingface/local-gemma>) |
| Citation | @article\{gemma\_2024,<br>    title=\{Gemma\},<br>    url=\{https://www\.kaggle\.com/m/3301\},<br>    DOI=\{10\.34740/KAGGLE/M/3301\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | 27B model trained from scratch on 13 trillion tokens \-&gt; substantial compute and energy use\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
