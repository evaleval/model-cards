# Model Card: Llama\-3\.2\-1B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.2\-1b\.json](<./llama-3.2-1b.json>)<br>
SHA-256: `0f6f8486afff41e5176af4359b0b414bbf40b43105dc9d45f134e9e77a8cdfe5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.2\-1B |
| Name | Llama\-3\.2\-1B |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3\.2 |
| Release date | 2024\-09\-18 \(Hugging Face repository creation date\) |
| Version | 4e20de362430cd3b72f300e6b0f18e50e7166e08 |
| Summary | A 1B\-parameter multilingual generative language model from the Llama 3\.2 collection, available in pretrained and instruction\-tuned variants\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama 3\.2 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 1,235,814,400 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.3 GiB of safetensors weights \(2,471,645,608 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 1,308,768 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 2,567 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that this model outperforms many available open\-source and closed chat models on common industry benchmarks\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | accuracy | 32\.2 | 5\-shot | Not reported |
| MMLU | accuracy | 39\.8 | 5\-shot | Not reported |
| AGIEval English | accuracy | 23\.3 | 3\-5 shot | Not reported |
| ARC\-Challenge | accuracy | 32\.8 | 25\-shot | Not reported |
| SQuAD | exact match | 49\.2 | 1\-shot | Not reported |
| QuAC | F1 | 37\.9 | 1\-shot | Not reported |
| DROP | F1 | 28\.0 | 3\-shot | Not reported |
| Needle in Haystack | exact match | 96\.8 | 0\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.2\-1B](<https://huggingface.co/meta-llama/Llama-3.2-1B>) |
| Code repository | [https://github\.com/meta\-llama/llama](<https://github.com/meta-llama/llama>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`, `risks.possible_risks`.
