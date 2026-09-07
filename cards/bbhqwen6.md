# Model Card: bbhqwen6

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [bbhqwen6\.json](<./bbhqwen6.json>)<br>
SHA-256: `9077dfcd01ec55ea35e42fe2e734c4e5c1d5ae487c2a7beb538f53cd072a63f8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | sumink/bbhqwen6 |
| Name | bbhqwen6 |
| Developed by | sumink \(Hub organization\) |
| Model type | Adjective ordering classification |
| Release date | 2025\-02\-25 \(Hugging Face repository creation date\) |
| Version | 1b75baaea3ec9cabe8998ea5f3ee2cdb60d3de27 |
| Summary | A fine\-tuned Qwen2\.5\-3B model for the BBH Hyperbaton adjective ordering task\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2\.5\-3B |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,085,938,688 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 11\.5 GiB of safetensors weights \(12,343,804,032 bytes\) in F32 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 10 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/sumink/bbhqwen6](<https://huggingface.co/sumink/bbhqwen6>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Evasion attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/evasion-attack.html>) | The checkpoint is a fine\-tuned classifier for the BBH Hyperbaton adjective ordering task; evasion attacks that slightly perturb input word order or phrasing could make the model output incorrect adjective\-ordering classifications\. | Evasion attacks attempt to make a model output incorrect results by slightly perturbing the input data sent to the trained model\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | The card reports only a narrow adjective\-ordering classification task with no accuracy or uncertainty metrics, so users may over\-trust its outputs in downstream grammar/style decisions or under\-trust it without stated performance evidence\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | The card summary provides no reported evaluations or risk metrics for this exact checkpoint, so any risk assessment based on the card would be incomplete or potentially measuring the wrong risk for the narrow task\. | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `lineage.base_models`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
