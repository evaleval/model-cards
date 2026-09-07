# Model Card: RakutenAI\-7B\-chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [rakutenai\-7b\-chat\.json](<./rakutenai-7b-chat.json>)<br>
SHA-256: `e4c5b0a032a6facc791a4a6073f5f8a431d4fa9e4be9105a646baa6bdffc5d0c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Rakuten/RakutenAI\-7B\-chat |
| Name | RakutenAI\-7B\-chat |
| Developed by | Rakuten \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-03\-18 \(Hugging Face repository creation date\) |
| Version | 7093167c61a0be6161cb68928c939c03fe0ab87d |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Rakuten/RakutenAI\-7B (base model; Kind: finetune) |
| Model family | RakutenAI |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,372,804,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.7 GiB of safetensors weights \(14,745,642,040 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | RakutenAI\-7B\-instruct and RakutenAI\-7B\-chat were created by fine\-tuning the foundation model on a mix of open\-source and internally hand\-crafted datasets\. The instruction\-tuned and chat\-tuned models used the train portions of JSNLI, RTE, KUCI, BELEBELE, JCS, JNLI, Dolly\-15K, and OpenAssistant1\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 244 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 67 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Rakuten/RakutenAI\-7B\-chat](<https://huggingface.co/Rakuten/RakutenAI-7B-chat>) |
| Citation | @misc\{rakutengroup2024rakutenai7b,<br>      title=\{RakutenAI\-7B: Extending Large Language Models for Japanese\}, <br>      author=\{\{Rakuten Group, Inc\.\} and Aaron Levine and Connie Huang and Chenguang Wang and Eduardo Batista and Ewa Szymanska and Hongyi Ding and Hou Wei Chou and Jean\-François Pessiot and Johanes Effendi and Justin Chiu and Kai Torben Ohlhus and Karan Chopra and Keiji Shinzato and Koji Murakami and Lee Xiong and Lei Chen and Maki Kubota and Maksim Tkachenko and Miroku Lee and Naoki Takahashi and Prathyusha Jwalapuram and Ryutaro Tatsushima and Saurabh Jain and Sunil Kumar Yadav and Ting Cai and Wei\-Te Chen and Yandi Xia and Yuki Nakayama and Yutaka Higashiyama\},<br>      year=\{2024\},<br>      eprint=\{2403\.15484\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
