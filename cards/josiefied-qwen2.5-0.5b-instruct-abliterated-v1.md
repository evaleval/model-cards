# Model Card: Goekdeniz\-Guelmez/Josiefied\-Qwen2\.5\-0\.5B\-Instruct\-abliterated\-v1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [josiefied\-qwen2\.5\-0\.5b\-instruct\-abliterated\-v1\.json](<./josiefied-qwen2.5-0.5b-instruct-abliterated-v1.json>)<br>
SHA-256: `d9e1967e4824e55cb2b636ae4c426780dc6c0a7c0ce9ea8443b31f63dfab820d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Goekdeniz\-Guelmez/Josiefied\-Qwen2\.5\-0\.5B\-Instruct\-abliterated\-v1 |
| Name | Goekdeniz\-Guelmez/Josiefied\-Qwen2\.5\-0\.5B\-Instruct\-abliterated\-v1 |
| Developed by | Goekdeniz\-Guelmez \(Hub organization\) |
| Model type | Text generation |
| License | apache\-2\.0 |
| Release date | 2024\-11\-17 \(Hugging Face repository creation date\) |
| Version | a42fe88f75b3ab545466ca5692fef0b4d7bc8009 |
| Summary | An abliterated and further fine\-tuned instruction model for reduced refusal behavior, with a recommended system prompt\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-0\.5B\-Instruct (base model; Kind: finetune) |
| Model family | Josiefied Qwen2\.5 abliterated v1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 630,167,424 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 1\.2 GiB of safetensors weights \(1,260,367,448 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was further fine\-tuned on a custom dataset after abliteration, aiming for reduced refusal behavior\. |
| Adaptations | The model is an abliterated model, with refusal vectors removed, and was further fine\-tuned on a custom dataset for more uncensoredness\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 97 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Goekdeniz\-Guelmez/Josiefied\-Qwen2\.5\-0\.5B\-Instruct\-abliterated\-v1](<https://huggingface.co/Goekdeniz-Guelmez/Josiefied-Qwen2.5-0.5B-Instruct-abliterated-v1>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | abliterated and further fine\-tuned instruction model for reduced refusal behavior with no reported safety evaluations \-&gt; plausible use for purposes the model was not designed for | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
