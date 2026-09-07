# Model Card: XinYuan\-Qwen2\-7B\-0917

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [xinyuan\-qwen2\-7b\-0917\.json](<./xinyuan-qwen2-7b-0917.json>)<br>
SHA-256: `8aa7f9641d42786b68519237485a9fb765b82a110332fa97d73881c9ae014274`

## Identity

| Field | Value |
| --- | --- |
| Model ID | thomas\-yanxin/XinYuan\-Qwen2\-7B\-0917 |
| Name | XinYuan\-Qwen2\-7B\-0917 |
| Developed by | thomas\-yanxin \(Hub organization\) |
| License | other |
| Release date | 2024\-09\-17 \(Hugging Face repository creation date\) |
| Version | bbbeafd1003c4d5e13f09b7223671957384b961a |
| Summary | The model is designed to demonstrate that the quality of the MT\-SFT\-ShareGPT dataset is sufficient, supporting the idea that data quality alone can determine model usefulness\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | XinYuan Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,864 bytes\) in BF16 |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on thomas\-yanxin/MT\-SFT\-ShareGPT, a dataset used to validate whether data quality alone is sufficient for strong results\. |
| Adaptations | The model was adapted through supervised fine\-tuning \(SFT\), with the finding that careful data governance and extraction can substantially improve model results\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 35 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that a better data governance approach, even with only supervised fine\-tuning, can greatly improve model results\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/thomas\-yanxin/XinYuan\-Qwen2\-7B\-0917](<https://huggingface.co/thomas-yanxin/XinYuan-Qwen2-7B-0917>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
