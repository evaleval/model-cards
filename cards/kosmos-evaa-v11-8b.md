# Model Card: Kosmos\-EVAA\-v11\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [kosmos\-evaa\-v11\-8b\.json](<./kosmos-evaa-v11-8b.json>)<br>
SHA-256: `06977d72e080246da252dfff58c88f38d8bb05daa980604035e1a0b18a0a4233`

## Identity

| Field | Value |
| --- | --- |
| Model ID | jaspionjader/Kosmos\-EVAA\-v11\-8B |
| Name | Kosmos\-EVAA\-v11\-8B |
| Developed by | jaspionjader \(Hub organization\) |
| Release date | 2024\-12\-27 \(Hugging Face repository creation date\) |
| Version | 0d96e6e1e53814b3950a3993e7733cd9a3057114 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | jaspionjader/Auro\-Kosmos\-EVAA\-v2\.2\-8B (base model; Kind: merge)<br>jaspionjader/Kosmos\-EVAA\-v10\-8B (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,336 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a merge of two other 8B models, jaspionjader/Kosmos\-EVAA\-v10\-8B and jaspionjader/Auro\-Kosmos\-EVAA\-v2\.2\-8B, combined with the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 22 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/jaspionjader/Kosmos\-EVAA\-v11\-8B](<https://huggingface.co/jaspionjader/Kosmos-EVAA-v11-8B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | 8B dense decoder\-only model merged via SLERP; no reported efficiency or environmental mitigation in card, so training/operation footprint is plausible\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | Card is a merge of two open\-weight 8B models with no documentation of training data, evaluations, or governance, making accountability hard to establish\. | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
