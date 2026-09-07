# Model Card: gemma\-3n\-e2b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3n\-e2b\.json](<./gemma-3n-e2b.json>)<br>
SHA-256: `336857b2db030b025ee6251653e4956bf7985bb71126b384d9346c3b0bd22188`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3n\-e2b |
| Name | gemma\-3n\-e2b |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2025\-06\-12 \(Hugging Face repository creation date\) |
| Version | c0ad2723802bade99f427667a609a03ae17a6a66 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-3n\-E4B (base model; Kind: finetune) |
| Model family | gemma 3n e2b |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 5,439,438,272 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 10\.1 GiB of safetensors weights \(10,879,085,840 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint was trained on a broad mixture of sources totaling approximately 11 trillion tokens\. |
| Training data size | Approximately 11 trillion tokens\. |
| Adaptations | The repository provides one sub\-model, with access to custom\-sized models via the Mix\-and\-Match method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 607 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 96 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the E2B sub\-model is already extracted for direct download and offers up to 2x faster inference, while the E4B main model provides the highest capabilities\. The architecture shares middle\-layer keys and values from local and global attention with all top layers, yielding a 2x prefill improvement over Gemma 3 4B\. Strong translation results are reported for English into and from Spanish, French, Italian, and Portuguese, and on a Google Pixel Edge TPU the model shows a 13x speedup with quantization, 46% fewer parameters, and a 4x smaller memory footprint with higher vision\-language accuracy\. |
| Safety evaluations | The developer reports that the models were evaluated against categories relevant to ethics and safety, including child safety and content safety\. Child safety evaluation covered text\-to\-text and image\-to\-text prompts addressing child safety policies, including child sexual abuse and exploitation\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3n\-e2b](<https://huggingface.co/google/gemma-3n-e2b>) |
| Citation | @article\{gemma\_3n\_2025,<br>    title=\{Gemma 3n\},<br>    url=\{https://ai\.google\.dev/gemma/docs/gemma\-3n\},<br>    publisher=\{Google DeepMind\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | Card reports child safety and content safety evaluations but no evaluation for other risks such as hallucination or privacy, so the reported safety testing may be incomplete for the model's broad multimodal use\. | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
