# Model Card: ConfigurableSOLAR\-10\.7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [configurablesolar\-10\.7b\.json](<./configurablesolar-10.7b.json>)<br>
SHA-256: `6170039ef5c99ef2fc8c3048bc9179fc9df31d310985db8629231f2a771a85d0`

## Identity

| Field | Value |
| --- | --- |
| Model ID | vicgalle/ConfigurableSOLAR\-10\.7B |
| Name | ConfigurableSOLAR\-10\.7B |
| Developed by | vicgalle \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-03\-10 \(Hugging Face repository creation date\) |
| Version | c5c844a7447d952d1a959b2542fb3aeec5e85133 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | ConfigurableSOLAR |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 10,731,524,096 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 20\.0 GiB of safetensors weights \(21,463,098,376 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a fine\-tune of a base LLM, trained on the vicgalle/configurable\-system\-prompt\-multitask dataset using the configurable safety tuning \(CST\) approach\. |
| Adaptations | The model was fine\-tuned with configurable safety tuning \(CST\), as described in the cited arXiv paper, on the vicgalle/configurable\-system\-prompt\-multitask dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 80 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 3 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/vicgalle/ConfigurableSOLAR\-10\.7B](<https://huggingface.co/vicgalle/ConfigurableSOLAR-10.7B>) |
| Citation | @misc\{gallego2024configurable,<br>      title=\{Configurable Safety Tuning of Language Models with Synthetic Preference Data\}, <br>      author=\{Victor Gallego\},<br>      year=\{2024\},<br>      eprint=\{2404\.00495\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
