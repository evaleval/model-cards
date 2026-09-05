# Model Card: gemma\-3\-4b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-4b\-it\.json](<./gemma-3-4b-it.json>)<br>
SHA-256: `5d3183841d841adde6a0f8090cfa1c87a13604bfa162d375891a87204a6dba8e`

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
| Adaptations | Instruction\-tuned models require chat templates to process inputs first\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 1,626,709 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 1,470 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model was evaluated on a large collection of datasets and metrics covering different aspects of text generation\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-4b\-it](<https://huggingface.co/google/gemma-3-4b-it>) |
| Technical report | [https://arxiv\.org/abs/2404\.16816](<https://arxiv.org/abs/2404.16816>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
