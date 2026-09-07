# Model Card: llama\-160m

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-160m\.json](<./llama-160m.json>)<br>
SHA-256: `af72119d2eeb17a5c823d4db02fcb5e46e96776b3940abe46c6dc1356ef0eeac`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JackFram/llama\-160m |
| Name | llama\-160m |
| Developed by | JackFram \(Hub organization\) |
| Model type | text generation |
| License | apache\-2\.0 |
| Release date | 2023\-05\-26 \(Hugging Face repository creation date\) |
| Version | aca9b687d1425f863dcf5de9a4c96e3fe36266dd |

## Lineage

| Field | Value |
| --- | --- |
| Model family | llama |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 162,417,792 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 0\.6 GiB of safetensors weights \(649,684,840 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 87,122 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 37 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that no evaluation has been conducted yet, so the model should be used with care\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/JackFram/llama\-160m](<https://huggingface.co/JackFram/llama-160m>) |
| Citation | @misc\{miao2023specinfer,<br>      title=\{SpecInfer: Accelerating Generative LLM Serving with Speculative Inference and Token Tree Verification\}, <br>      author=\{Xupeng Miao and Gabriele Oliaro and Zhihao Zhang and Xinhao Cheng and Zeyu Wang and Rae Ying Yee Wong and Zhuoming Chen and Daiyaan Arfeen and Reyna Abhyankar and Zhihao Jia\},<br>      year=\{2023\},<br>      eprint=\{2305\.09781\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
