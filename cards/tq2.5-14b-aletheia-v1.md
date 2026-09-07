# Model Card: TQ2\.5\-14B\-Aletheia\-v1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [tq2\.5\-14b\-aletheia\-v1\.json](<./tq2.5-14b-aletheia-v1.json>)<br>
SHA-256: `4bd487506b8019977d477d42a33ee641313746cdc8d744e7c4e203a0316897a7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allura\-org/TQ2\.5\-14B\-Aletheia\-v1 |
| Name | TQ2\.5\-14B\-Aletheia\-v1 |
| Developed by | allura\-org \(Hub organization\) |
| Model type | Roleplay and story generation hybrid model\. |
| License | apache\-2\.0 |
| Release date | 2024\-12\-19 \(Hugging Face repository creation date\) |
| Version | c7fbe91dbdb85161464f87c261b588dbf674e514 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | allura\-org/TQ2\.5\-14B\-Neon\-v1 (base model; Kind: merge)<br>allura\-org/TQ2\.5\-14B\-Sugarquill\-v1 (base model; Kind: merge) |
| Model family | TQ2\.5 Aletheia v1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,770,033,664 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,540,133,904 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of allura\-org/TQ2\.5\-14B\-Neon\-v1 and allura\-org/TQ2\.5\-14B\-Sugarquill\-v1, combined using the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 26 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 8 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/allura\-org/TQ2\.5\-14B\-Aletheia\-v1](<https://huggingface.co/allura-org/TQ2.5-14B-Aletheia-v1>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, merge method, and license; no training data, evaluation, or safety documentation for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card states it is a SLERP merge of two named open\-weight models but provides no traceability of their training data or usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training/tuning dataset details for either base model or the merged checkpoint\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Harmful output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-output.html>) | Open\-weight roleplay/story generation model with no reported safety evaluation or guardrails can plausibly generate harmful language\. | A model might generate language that leads to physical harm\.  The language might include overtly violent, covertly dangerous, or otherwise indirectly unsafe statements\. |
| [Spreading disinformation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/spreading-disinformation.html>) | Open\-weight text generation model for roleplay/story generation with no reported misuse evaluation can be used to create misleading/false narratives\. | Generative AI models might be used to intentionally create misleading or false information to deceive or influence a targeted audience\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
