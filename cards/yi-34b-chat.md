# Model Card: Yi\-34B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [yi\-34b\-chat\.json](<./yi-34b-chat.json>)<br>
SHA-256: `1739d64391c677fb9f7e1ddf86488f27b8668d2c2dfe1eca825f0977a6c301a3`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 01\-ai/Yi\-34B\-Chat |
| Name | Yi\-34B\-Chat |
| Developed by | 01\-ai \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2023\-11\-22 \(Hugging Face repository creation date\) |
| Version | cf02cb50f2a03dead2fe205766a1c5598a90bf80 |
| Summary | Yi\-34B\-Chat is a chat model in the Yi series, an open\-source family of large language models trained from scratch by 01\.AI\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Yi |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 34,388,917,248 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 64\.1 GiB of safetensors weights \(68,777,898,032 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The released chat model was trained exclusively with supervised fine\-tuning \(SFT\)\. |
| Adaptations | The released chat model was trained exclusively using supervised fine\-tuning \(SFT\)\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 24,997 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 358 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Yi\-34B\-Chat ranked second on the AlpacaEval leaderboard as of January 2024, behind GPT\-4 Turbo and ahead of models such as GPT\-4, Mixtral, and Claude\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/01\-ai/Yi\-34B\-Chat](<https://huggingface.co/01-ai/Yi-34B-Chat>) |
| Citation | @misc\{ai2024yi,<br>    title=\{Yi: Open Foundation Models by 01\.AI\},<br>    author=\{01\. AI and : and Alex Young and Bei Chen and Chao Li and Chengen Huang and Ge Zhang and Guanwei Zhang and Heng Li and Jiangcheng Zhu and Jianqun Chen and Jing Chang and Kaidong Yu and Peng Liu and Qiang Liu and Shawn Yue and Senbin Yang and Shiming Yang and Tao Yu and Wen Xie and Wenhao Huang and Xiaohui Hu and Xiaoyi Ren and Xinyao Niu and Pengcheng Nie and Yuchi Xu and Yudong Liu and Yue Wang and Yuxuan Cai and Zhenyu Gu and Zhiyuan Liu and Zonghong Dai\},<br>    year=\{2024\},<br>    eprint=\{2403\.04652\},<br>    archivePrefix=\{arXiv\},<br>    primaryClass=\{cs\.CL\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
