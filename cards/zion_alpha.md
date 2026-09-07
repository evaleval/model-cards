# Model Card: Zion\_Alpha

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [zion\_alpha\.json](<./zion_alpha.json>)<br>
SHA-256: `0a86d37ca2632fb0272e637a31b24a92cf8ea39c30335057fc6212695cf0e922`

## Identity

| Field | Value |
| --- | --- |
| Model ID | SicariusSicariiStuff/Zion\_Alpha |
| Name | Zion\_Alpha |
| Developed by | SicariusSicariiStuff \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-05\-19 \(Hugging Face repository creation date\) |
| Version | 18f80198842939b5898bb50a7e76a5e2c1015177 |
| Summary | Zion\_Alpha is presented as the first REAL Hebrew model in the world\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Zion Alpha |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,498,016 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was not fine\-tuned for any tasks, but it understands and comprehends Hebrew\. |
| Adaptations | The model was fine\-tuned using SOTA techniques and insights from underwater basket weaving; it was not fine\-tuned for any tasks yet\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 119 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | As of 04 June 2024, the developer reported that Zion\_Alpha achieved the highest SNLI score among open\-source Hebrew models, with a score of 84\.05, surpassing most models by a large margin\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/SicariusSicariiStuff/Zion\_Alpha](<https://huggingface.co/SicariusSicariiStuff/Zion_Alpha>) |
| Citation | @llm\{Zion\_Alpha,<br>  author = \{SicariusSicariiStuff\},<br>  title = \{Zion\_Alpha\},<br>  year = \{2024\},<br>  publisher = \{Hugging Face\},<br>  url = \{https://huggingface\.co/SicariusSicariiStuff/Zion\_Alpha\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
