# Model Card: merge

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [arliai\-rpmax\-v1\.3\-merge\-13\.3b\.json](<./arliai-rpmax-v1.3-merge-13.3b.json>)<br>
SHA-256: `76ff2854c85eec217622f007a6fba26cca0b5aebfb1c9905572d375d844d30d5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | win10/ArliAI\-RPMax\-v1\.3\-merge\-13\.3B |
| Name | merge |
| Developed by | win10 \(Hub organization\) |
| Model type | merge of pre\-trained language models |
| Release date | 2024\-11\-16 \(Hugging Face repository creation date\) |
| Version | 4d3ed351827f1afc1652e13aafeb1eae79b8f562 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | win10/ArliAI\-RPMax\-v1\.3\-merge\-8B (base model; Kind: finetune) |
| Model family | ArliAI RPMax v1\.3 merge |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 13,264,949,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 24\.7 GiB of safetensors weights \(26,529,958,536 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a merge produced with the passthrough merge method, combining the model win10/ArliAI\-RPMax\-v1\.3\-merge\-8B\. The merge process can adjust input model embedding matrices to match the output vocabulary and combines per\-model embeddings according to the selected merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 14 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/win10/ArliAI\-RPMax\-v1\.3\-merge\-13\.3B](<https://huggingface.co/win10/ArliAI-RPMax-v1.3-merge-13.3B>) |
| Code repository | [https://github\.com/cg123/mergekit](<https://github.com/cg123/mergekit>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`, `risks.possible_risks`.
