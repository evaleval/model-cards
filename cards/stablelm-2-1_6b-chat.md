# Model Card: stablelm\-2\-1\_6b\-chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [stablelm\-2\-1\_6b\-chat\.json](<./stablelm-2-1_6b-chat.json>)<br>
SHA-256: `80e64c0fe55e6fc9fe155791466a981055623d815def45858b1ae067c40f6403`

## Identity

| Field | Value |
| --- | --- |
| Model ID | stabilityai/stablelm\-2\-1\_6b\-chat |
| Name | stablelm\-2\-1\_6b\-chat |
| Developed by | stabilityai \(Hub organization\) |
| License | other |
| Release date | 2024\-04\-08 \(Hugging Face repository creation date\) |
| Version | f3fe67057c2789ae1bb1fe42b038da99840d4f13 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | stablelm 2 1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,644,515,328 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 6\.1 GiB of safetensors weights \(6,578,099,872 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on a mixture of large\-scale open datasets available on the HuggingFace Hub, including publicly available and synthetic datasets\. |
| Adaptations | The model was trained using Direct Preference Optimization \(DPO\) on a mix of publicly available and synthetic datasets\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 2,519 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 34 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | Developer red\-teaming found that the model generally does not produce harmful information unless prompted, but it can hallucinate facts and may produce harmful outputs or misinformation when requested\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/stabilityai/stablelm\-2\-1\_6b\-chat](<https://huggingface.co/stabilityai/stablelm-2-1_6b-chat>) |
| Citation | @misc\{StableLM\-2\-1\.6B,<br>      url=\{\[https://huggingface\.co/stabilityai/stablelm\-2\-1\.6b\]\(https://huggingface\.co/stabilityai/stablelm\-2\-1\.6b\)\},<br>      title=\{Stable LM 2 1\.6B\},<br>      author=\{Stability AI Language Team\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
