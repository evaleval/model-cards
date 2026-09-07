# Model Card: Barcenas\-3b\-GRPO

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [barcenas\-3b\-grpo\.json](<./barcenas-3b-grpo.json>)<br>
SHA-256: `2c30a7c87b392a5e6417ad03e25037d62e16645f4d17f98b3e0c515ddf38c015`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Danielbrdz/Barcenas\-3b\-GRPO |
| Name | Barcenas\-3b\-GRPO |
| Developed by | Danielbrdz \(Hub organization\) |
| Model type | text\-generation |
| License | llama3\.2 |
| Release date | 2025\-02\-08 \(Hugging Face repository creation date\) |
| Version | 643e7615446a20d9ffe7cb66b88a6791cc6ae1eb |
| Summary | Barcenas 3b GRPO |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Llama\-3\.2\-3B\-Instruct (base model; Kind: finetune) |
| Model family | Barcenas GRPO |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,212,749,824 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 6\.0 GiB of safetensors weights \(6,425,528,792 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on the openai/gsm8k dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 20 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that the model was created to test the GRPO training approach introduced in DeepSeek R1\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Danielbrdz/Barcenas\-3b\-GRPO](<https://huggingface.co/Danielbrdz/Barcenas-3b-GRPO>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Membership inference attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/membership-inference-attack.html>) | Trained on openai/gsm8k and open\-weight, so an attacker can run the checkpoint locally and perform membership inference on that known public training dataset\. | A membership inference attack repeatedly queries a model to determine if a given input was part of the model&\#x27;s training\. More specifically, given a trained model and a data sample, an attacker appropriately samples the input space, observing outputs to deduce whether that sample was part of the model&\#x27;s training\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
