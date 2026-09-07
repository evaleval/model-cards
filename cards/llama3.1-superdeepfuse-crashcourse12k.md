# Model Card: Llama3\.1\-SuperDeepFuse\-CrashCourse12K

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama3\.1\-superdeepfuse\-crashcourse12k\.json](<./llama3.1-superdeepfuse-crashcourse12k.json>)<br>
SHA-256: `54d0ee863029e6512d3151e31d3a7e2c49619fb171461ae51a24f89cbd0bb101`

## Identity

| Field | Value |
| --- | --- |
| Model ID | agentlans/Llama3\.1\-SuperDeepFuse\-CrashCourse12K |
| Name | Llama3\.1\-SuperDeepFuse\-CrashCourse12K |
| Developed by | agentlans \(Hub organization\) |
| Model type | Instruction\-tuned language model |
| License | llama3\.1 |
| Release date | 2025\-01\-24 \(Hugging Face repository creation date\) |
| Version | 7bec0a6b638a9dfbe4c74343c50886dae65067a8 |
| Summary | An 8B\-parameter instruction\-tuned language model built by fine\-tuning Llama3\.1\-SuperDeepFuse on the agentlans/crash\-course dataset\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | agentlans/Llama3\.1\-SuperDeepFuse (base model; Kind: finetune) |
| Model family | Llama3\.1 SuperDeepFuse CrashCourse12K |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | Instruction\-tuned language model |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was further fine\-tuned using LoRA with 4\-bit quantization \(bitsandbytes\), NEFTune \(noise alpha: 5\), and RS\-LoRA\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 14 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/agentlans/Llama3\.1\-SuperDeepFuse\-CrashCourse12K](<https://huggingface.co/agentlans/Llama3.1-SuperDeepFuse-CrashCourse12K>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, LoRA/4\-bit/NEFTune/RS\-LoRA adaptation, and dataset name; no design/evaluation details or inner\-workings insights for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names the crash\-course dataset but does not document its collection, curation, composition, or any synthetic generation details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Open\-weight checkpoint fine\-tuned on an external named dataset with no stated ownership, origin, transformations, or usage terms for that data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says &\#x27;instruction\-tuned language model&\#x27; and gives no intended\-use or out\-of\-scope use definition, so relevant risks are not defined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
