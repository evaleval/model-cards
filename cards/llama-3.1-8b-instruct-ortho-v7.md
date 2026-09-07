# Model Card: llama\-3\.1\-8b\-instruct\-ortho\-v7

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-8b\-instruct\-ortho\-v7\.json](<./llama-3.1-8b-instruct-ortho-v7.json>)<br>
SHA-256: `79765707c40a50c5d17742662c23c8ecc716381b665d9b638a06fef69504a95a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | lodrick\-the\-lafted/llama\-3\.1\-8b\-instruct\-ortho\-v7 |
| Name | llama\-3\.1\-8b\-instruct\-ortho\-v7 |
| Developed by | lodrick\-the\-lafted \(Hub organization\) |
| License | wtfpl |
| Release date | 2024\-07\-25 \(Hugging Face repository creation date\) |
| Version | 6b7673cd78398c3a8c92f8e759aaae6409e96978 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | llama 3\.1 ortho v7 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is the result of orthogonalization or abliteration attempts applied to llama\-3\.1\-8b\-instruct, using variations of a method for eliciting latent behaviors in language models\. Different vectors were tried, with variations in where the new refusal boundaries lie\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 29 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The developer notes that none of the tested models appear to be fully jailbroken\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/lodrick\-the\-lafted/llama\-3\.1\-8b\-instruct\-ortho\-v7](<https://huggingface.co/lodrick-the-lafted/llama-3.1-8b-instruct-ortho-v7>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | The card reports safety evaluations only as &\#x27;none of the tested models appear to be fully jailbroken&\#x27;, which is a narrow jailbreak test and does not measure other risks such as hallucination or data privacy, so the selected metric may incompletely measure the risk\. | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
