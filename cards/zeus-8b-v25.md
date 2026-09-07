# Model Card: ZEUS\-8B\-V25

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [zeus\-8b\-v25\.json](<./zeus-8b-v25.json>)<br>
SHA-256: `748296c82cb027ae54c25e2140db5ffd10357c7f4550e62d042635c1b7e1df1a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | T145/ZEUS\-8B\-V25 |
| Name | ZEUS\-8B\-V25 |
| Developed by | T145 \(Hub organization\) |
| Release date | 2025\-01\-23 \(Hugging Face repository creation date\) |
| Version | 9eb6cb27591bcd250276190153ddf9864df7c710 |
| Summary | ZEUS\-8B\-V25 is a merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Orenguteng/Llama\-3\.1\-8B\-Lexi\-Uncensored\-V2 (base model; Kind: merge)<br>VAGOsolutions/Llama\-3\.1\-SauerkrautLM\-8b\-Instruct (base model; Kind: merge)<br>arcee\-ai/Llama\-3\.1\-SuperNova\-Lite (base model; Kind: merge)<br>unsloth/Llama\-3\.1\-Storm\-8B (base model; Kind: merge)<br>unsloth/Meta\-Llama\-3\.1\-8B\-Instruct (base model; Kind: merge) |
| Model family | ZEUS V25 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,269,440 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,572,744 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 12 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/T145/ZEUS\-8B\-V25](<https://huggingface.co/T145/ZEUS-8B-V25>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only that ZEUS\-8B\-V25 is a mergekit merge of named open\-weight Llama\-3\.1 models, with no documentation of design, development, or evaluation process\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card identifies only the merged base/instruct models and gives no traceability of the training/merge data or its usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information is provided about how data was collected, curated, or used for the merge, making model behavior harder to explain\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the card does not disclose training data content, outputs cannot be traced back to specific training sources\. | The content of the training data used for generating the model's output is not accessible\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
