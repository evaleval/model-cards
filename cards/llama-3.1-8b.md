# Model Card: Llama\-3\.1\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-8b\.json](<./llama-3.1-8b.json>)<br>
SHA-256: `332535c5f0e1431287e92c82e26d02dc126677c470b1cba439b9157ecb9060cd`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.1\-8B |
| Name | Llama\-3\.1\-8B |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3\.1 |
| Release date | 2024\-07\-14 \(Hugging Face repository creation date\) |
| Version | d04e592bb4f6aa9cfee91e2e20afa771667e1d4b |
| Summary | A multilingual large language model from the Llama 3\.1 collection, available in 8B, 70B, and 405B sizes and supporting text in/text out\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama 3\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint was trained on a new mix of publicly available online data\. |
| Training data size | 15T\+ tokens |
| Data cutoff | December 2023 |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 513,485 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 2,416 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that the Llama 3\.1 instruction\-tuned text\-only models, including the 8B variant, are optimized for multilingual dialogue and outperform many open\-source and closed chat models on common industry benchmarks\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.1\-8B](<https://huggingface.co/meta-llama/Llama-3.1-8B>) |
| Code repository | [https://github\.com/meta\-llama/llama3](<https://github.com/meta-llama/llama3>) |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
