# Model Card: llamaRAGdrama

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llamaragdrama\.json](<./llamaragdrama.json>)<br>
SHA-256: `5ed34b3a130a33f770995d13b444d845dd51216c53a2298bfa111365ca2a04f9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | kevin009/llamaRAGdrama |
| Name | llamaRAGdrama |
| Developed by | kevin009 \(Hub organization\) |
| Model type | Fine\-tuned for Q&amp;A and RAG\. |
| License | apache\-2\.0 |
| Release date | 2024\-02\-04 \(Hugging Face repository creation date\) |
| Version | 8c103ca8fa6dd9a8d3dab81b319408095e9a1ad8 |
| Summary | A fine\-tuned model for question answering and retrieval\-augmented generation, designed to remain factual and reliable in dramatic situations\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | llamaRAGdrama |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,497,728 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a fine\-tune for synthesis of text content in Q&amp;A and RAG scenarios\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 91 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 7 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Human evaluations | The model is described as remaining factual and reliable even in dramatic situations\. |
| Safety evaluations | The developer notes that the model may not be considered safe despite being designed to be truthful, and that it may retain biases and inaccuracies\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/kevin009/llamaRAGdrama](<https://huggingface.co/kevin009/llamaRAGdrama>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
