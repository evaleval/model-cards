# Model Card: Reasoning\-0\.5b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [reasoning\-0\.5b\.json](<./reasoning-0.5b.json>)<br>
SHA-256: `77f674879417add350eec085fe8f588b5366f3bf69707a5f2ee06ada54b82941`

## Identity

| Field | Value |
| --- | --- |
| Model ID | KingNish/Reasoning\-0\.5b |
| Name | Reasoning\-0\.5b |
| Developed by | KingNish \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-10\-05 \(Hugging Face repository creation date\) |
| Version | ec3c31a7907fee84c792b95ab3de597ee1e6521d |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-0\.5B\-Instruct (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 494,032,768 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 0\.9 GiB of safetensors weights \(988,097,536 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on the KingNish/reasoning\-base\-20k dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 46 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 31 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model performed very well, attributing this to a reasoning\-then\-generation behavior similar to o1, with reasoning performed separately and not included in the final response\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/KingNish/Reasoning\-0\.5b](<https://huggingface.co/KingNish/Reasoning-0.5b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only a qualitative 'performed very well' result and no evaluation details, so design/evaluation process is insufficiently documented for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card names the fine\-tuning dataset but does not document how KingNish/reasoning\-base\-20k was collected, curated, or used\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Fine\-tuning on a single 20k reasoning dataset may not represent the diversity of real\-world inputs the open\-weight model will encounter\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card gives no provenance or usage terms for KingNish/reasoning\-base\-20k, so traceability of the fine\-tuning data is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
