# Model Card: Llama3\.1\-8B\-drill

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama3\.1\-8b\-drill\.json](<./llama3.1-8b-drill.json>)<br>
SHA-256: `09954fdd5354b11d73137888fda4c0ebfaacacfd7d056472f258e56fad0870ac`

## Identity

| Field | Value |
| --- | --- |
| Model ID | agentlans/Llama3\.1\-8B\-drill |
| Name | Llama3\.1\-8B\-drill |
| Developed by | agentlans \(Hub organization\) |
| Model type | Instruction\-following language model |
| Release date | 2024\-12\-27 \(Hugging Face repository creation date\) |
| Version | a319513617fcb9dd0567b4c18a32def76256140e |
| Summary | A merge of high\-scoring Llama 3\.1 8B models on the IFEval task, intended to follow instructions well\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama3\.1 drill |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,336 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 22 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model turned out to be mediocre compared to its parent models, even on the IFEval task, and suggests considering those models instead\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/agentlans/Llama3\.1\-8B\-drill](<https://huggingface.co/agentlans/Llama3.1-8B-drill>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | The card reports the model is mediocre compared to its parent models even on IFEval, so users may over\-trust it as an instruction\-following model or under\-trust it despite its intended task\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model's output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model's output when the model's output is likely incorrect\. Under\-reliance is the opposite, where the person doesn't trust the model but should\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
