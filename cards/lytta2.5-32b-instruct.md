# Model Card: Lytta 2\.5 32B Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [lytta2\.5\-32b\-instruct\.json](<./lytta2.5-32b-instruct.json>)<br>
SHA-256: `c27b7a2ba1bda16f38624868b5d598e834223c455185deb9324d22fb0ebf9231`

## Identity

| Field | Value |
| --- | --- |
| Model ID | maldv/Lytta2\.5\-32B\-Instruct |
| Name | Lytta 2\.5 32B Instruct |
| Developed by | maldv \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-02 \(Hugging Face repository creation date\) |
| Version | 3e2f949e16f5cc807d04786c2c08a0552850acc6 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | NextGLab/ORANSight\_Qwen\_32B\_Instruct (base model; Kind: finetune) |
| Model family | Lytta2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 32,763,876,352 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 61\.0 GiB of safetensors weights \(65,527,841,840 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports disappointment with the model, describing it as worse than expected, disobedient, and suited mainly to unconventional or NSFW creative writing\. |
| Human evaluations | The developer&\#x27;s stated assessment is that the model is worse than expected, unhinged, completely disobedient, highly intelligent and creative, and probably only suitable for bizarre NSFW or outlandish creative writing\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/maldv/Lytta2\.5\-32B\-Instruct](<https://huggingface.co/maldv/Lytta2.5-32B-Instruct>) |
| Citation | @misc\{lytta2\.5\-32b\-instruct,<br>    title = \{Lytta 2\.5 32B Instruct\},<br>    url = \{https://huggingface\.co/maldv/Lytta2\.5\-32B\-Instruct\},<br>    author = \{Praxis Maldevide\},<br>    month = \{January\},<br>    year = \{2025\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
