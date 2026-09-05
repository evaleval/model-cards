# Model Card: gemma\-3\-4b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-4b\-it\.json](<./gemma-3-4b-it.json>)<br>
SHA-256: `e7f673de79f70258c48ce40511296f8008f684b0ac1535732d293ec78499cbc8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-4b\-it |
| Name | gemma\-3\-4b\-it |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2025\-02\-20 \(Hugging Face repository creation date\) |
| Version | 093f9f388b31de276ce2de164bdc2081324b9767 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-3\-4b\-pt (base model; Kind: finetune) |
| Model family | gemma 3 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 4,300,079,472 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 8\.0 GiB of safetensors weights \(8,600,277,880 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The 4B checkpoint was trained on a text dataset that includes a wide variety of sources: web documents in over 140 languages, code, mathematics, and images\. |
| Adaptations | The model is instruction\-tuned, so chat templates must be used to process inputs before generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 1,626,709 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 1,470 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-4b\-it](<https://huggingface.co/google/gemma-3-4b-it>) |
| Technical report | [https://arxiv\.org/abs/2404\.16816](<https://arxiv.org/abs/2404.16816>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
