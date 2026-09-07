# Model Card: Phi\-Line\_14B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [phi\-line\_14b\.json](<./phi-line_14b.json>)<br>
SHA-256: `861b23f436f8ff04adb75359fc2c8aa6f763a53ef99097bfe63bd18e9a00bc3c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | SicariusSicariiStuff/Phi\-Line\_14B |
| Name | Phi\-Line\_14B |
| Developed by | SicariusSicariiStuff \(Hub organization\) |
| Model type | Role\-play, creative writing, and general tasks\. |
| License | mit |
| Release date | 2025\-02\-17 \(Hugging Face repository creation date\) |
| Version | eae63cb78aa4366bfa61f2d04af350eb567d50fc |
| Summary | A roleplay\-focused model with strong general task performance\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | microsoft/phi\-4 (base model; Kind: finetune) |
| Model family | Phi Line |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,659,507,200 parameters \(safetensors metadata\) |
| Context length | 16,384 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.3 GiB of safetensors weights \(29,319,057,064 bytes\) in BF16 |
| Input / output | Text input<br>Text output |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on the same dataset used for Phi\-lthy\. |
| Adaptations | The model was trained with the same training parameters used for Phi\-lthy\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 78 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 19 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports the model is substantially more intelligent than its base, while noting a trade\-off in reduced creativity and a less unpredictable tone\. |
| Safety evaluations | The developer reports low refusal rates in roleplay and assistant tasks, describing the model as permissive in roleplay contexts\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/SicariusSicariiStuff/Phi\-Line\_14B](<https://huggingface.co/SicariusSicariiStuff/Phi-Line_14B>) |
| Citation | @llm\{Phi\-Line\_14B,<br>  author = \{SicariusSicariiStuff\},<br>  title = \{Phi\-Line\_14B\},<br>  year = \{2025\},<br>  publisher = \{Hugging Face\},<br>  url = \{https://huggingface\.co/SicariusSicariiStuff/Phi\-Line\_14B\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
