# Model Card: gen\-inst\-1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gen\-inst\-1\.json](<./gen-inst-1.json>)<br>
SHA-256: `1cf941a0b6a3c77f92093b9339c0038c2d758fd1cc39f9188632418b634776be`

## Identity

| Field | Value |
| --- | --- |
| Model ID | dwikitheduck/gen\-inst\-1 |
| Name | gen\-inst\-1 |
| Developed by | dwikitheduck \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-11\-18 \(Hugging Face repository creation date\) |
| Version | 7d90c00b735d18da65ebef8fd7e6d79a908c55b0 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-14B\-Instruct (base model; Kind: finetune) |
| Model family | gen inst 1 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 14,770,033,664 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,540,133,960 bytes\) in BF16 |
| Input / output | text input<br>text output |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a fine\-tune of Qwen/Qwen2\.5\-14B\-Instruct, trained on the dwikitheduck/genesist\-inst dataset with completion\-style examples\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 0 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports a single evaluation loss of 1\.0180 on the evaluation set\. Broader benchmark comparisons in the source describe a different model family and are not attributed to this checkpoint\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/dwikitheduck/gen\-inst\-1](<https://huggingface.co/dwikitheduck/gen-inst-1>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
