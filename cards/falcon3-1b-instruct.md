# Model Card: Falcon3\-1B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [falcon3\-1b\-instruct\.json](<./falcon3-1b-instruct.json>)<br>
SHA-256: `fb8a49ac16993830a40975ffd06a316abeabf4b03368d333aa77b56d31b478a6`

## Identity

| Field | Value |
| --- | --- |
| Model ID | tiiuae/Falcon3\-1B\-Instruct |
| Name | Falcon3\-1B\-Instruct |
| Developed by | tiiuae \(Hub organization\) |
| Model type | Transformer\-based causal decoder\-only architecture\. |
| License | other |
| Release date | 2024\-12\-14 \(Hugging Face repository creation date\) |
| Version | 28ba2251970a01dd1edc7ba7dad2eb71216ccfdf |
| Summary | Falcon3\-1B\-Instruct is an instruction\-tuned language model focused on reasoning, language understanding, instruction following, code, and mathematics\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | tiiuae/Falcon3\-1B\-Base (base model; Kind: finetune) |
| Model family | Falcon3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,669,408,768 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 3\.1 GiB of safetensors weights \(3,338,836,632 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Falcon3\-1B\-Instruct was post\-trained on 1\.2 million samples covering STEM, conversational, code, safety, and function call data\. |
| Training data size | 1\.2 million samples |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 10,799 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 46 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports strong performance on reasoning, language understanding, instruction following, code, and mathematics tasks\. |
| Human evaluations | The developer reports an MT\-Bench average score of 5\.4 for this model\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/tiiuae/Falcon3\-1B\-Instruct](<https://huggingface.co/tiiuae/Falcon3-1B-Instruct>) |
| Citation | @misc\{Falcon3,<br>    title = \{The Falcon 3 Family of Open Models\},<br>    url = \{https://huggingface\.co/blog/falcon3\},<br>    author = \{Falcon\-LLM Team\},<br>    month = \{December\},<br>    year = \{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
