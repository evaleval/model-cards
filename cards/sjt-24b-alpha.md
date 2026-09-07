# Model Card: SJT\-24B\-Alpha

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [sjt\-24b\-alpha\.json](<./sjt-24b-alpha.json>)<br>
SHA-256: `afe374ed44e4310d796096fec5fa522dc2bb760314c7ec2c3e39f54b0169e726`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Sakalti/SJT\-24B\-Alpha |
| Name | SJT\-24B\-Alpha |
| Developed by | Sakalti \(Hub organization\) |
| Release date | 2025\-02\-02 \(Hugging Face repository creation date\) |
| Version | 273305272a361d7c5db9623bfa369f738e0b537a |
| Summary | SJT\-24B\-Alpha is a merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Sakalti/ultiima\-14B\-v0\.4 (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 24,125,080,576 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 44\.9 GiB of safetensors weights \(48,250,273,728 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 11 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Sakalti/SJT\-24B\-Alpha](<https://huggingface.co/Sakalti/SJT-24B-Alpha>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Jailbreaking](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/jailbreaking.html>) | open\-weight text model with no reported safety evaluation or guardrails in the card \-&gt; jailbreaking | A jailbreaking attack attempts to break through the guardrails established in the model to perform restricted actions\. |
| [Harmful output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-output.html>) | open\-weight text\-generation model with no reported safety evaluation \-&gt; harmful output | A model might generate language that leads to physical harm\.  The language might include overtly violent, covertly dangerous, or otherwise indirectly unsafe statements\. |
| [Dangerous use](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/dangerous-use.html>) | open\-weight model with no reported use restrictions or safety evaluation \-&gt; dangerous use | Generative AI models might be used with the sole intention of harming people\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
