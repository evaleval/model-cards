# Model Card: gemma\-2\-9b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-2\-9b\.json](<./gemma-2-9b.json>)<br>
SHA-256: `655afec3a68e30ddfc4be4a04517e01762c209fbc31d470ec46059142aae6717`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-2\-9b |
| Name | gemma\-2\-9b |
| Developed by | google \(Hub organization\) |
| Model type | text\-to\-text, decoder\-only large language model |
| License | gemma |
| Release date | 2024\-06\-24 \(Hugging Face repository creation date\) |
| Version | 33c193028431c2fde6c6e51f29e6f17b60cbfac6 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma 2 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 9,241,705,984 parameters \(safetensors metadata\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 34\.4 GiB of safetensors weights \(36,966,878,040 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model card states that the model was trained on text data from a wide variety of sources\. |
| Adaptations | The model card states that the model was evaluated against a large collection of datasets and metrics to cover different aspects of text generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 68,206 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 728 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model was evaluated across a broad set of datasets and metrics covering different aspects of text generation, and that the resulting models deliver strong performance for their size, offering competitive alternatives to larger models\. |
| Safety evaluations | The developer reports that ethics and safety evaluation results were within acceptable thresholds for internal policies covering categories such as child safety, content safety, representational harms, memorization, and large\-scale harms\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | top\-1 | 71\.3 | 5\-shot | Not reported |
| HellaSwag | Not specified | 81\.9 | 10\-shot | Not reported |
| PIQA | Not specified | 81\.7 | 0\-shot | Not reported |
| SocialIQA | Not specified | 53\.4 | 0\-shot | Not reported |
| BoolQ | Not specified | 84\.2 | 0\-shot | Not reported |
| WinoGrande | score | 80\.6 | Not specified | Not reported |
| ARC\-e | Not specified | 88\.0 | 0\-shot | Not reported |
| ARC\-c | Not specified | 68\.4 | 25\-shot | Not reported |
| TriviaQA | Not specified | 76\.6 | 5\-shot | Not reported |
| Natural Questions | Not specified | 29\.2 | 5\-shot | Not reported |
| HumanEval | pass@1 | 40\.2 | Not specified | Not reported |
| MBPP | Not specified | 52\.4 | 3\-shot | Not reported |
| GSM8K | Not specified | 68\.6 | 5\-shot | Not reported |
| MATH | Not specified | 36\.6 | 4\-shot | Not reported |
| AGIEval | Not specified | 52\.8 | 5\-shot | Not reported |
| BIG\-Bench | Not specified | 68\.2 | 3\-shot CoT | Not reported |
| DROP | F1 | 69\.4 | 3\-shot | Not reported |
| BBH | Not specified | 68\.2 | 3\-shot CoT | Not reported |
| Winogrande | Not specified | 80\.6 | 5\-shot | Not reported |
| SIQA | Not specified | 53\.4 | 0\-shot | Not reported |
| NQ | Not specified | 29\.2 | 5\-shot | Not reported |
| Average | Not specified | 70\.2 | Not specified | Not reported |
| Average | Not specified | 64\.9 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-2\-9b](<https://huggingface.co/google/gemma-2-9b>) |
| Technical report | [https://arxiv\.org/abs/2408\.00118](<https://arxiv.org/abs/2408.00118>) |
| Code repository | [https://github\.com/huggingface/local\-gemma](<https://github.com/huggingface/local-gemma>) |
| Citation | @article\{gemma\_2024,<br>    title=\{Gemma\},<br>    url=\{https://www\.kaggle\.com/m/3301\},<br>    DOI=\{10\.34740/KAGGLE/M/3301\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `links.system_card`, `risks.possible_risks`.
