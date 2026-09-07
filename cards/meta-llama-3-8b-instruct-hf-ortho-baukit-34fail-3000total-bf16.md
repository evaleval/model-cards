# Model Card: meta\-llama\-3\-8b\-instruct\-hf\-ortho\-baukit\-34fail\-3000total\-bf16

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [meta\-llama\-3\-8b\-instruct\-hf\-ortho\-baukit\-34fail\-3000total\-bf16\.json](<./meta-llama-3-8b-instruct-hf-ortho-baukit-34fail-3000total-bf16.json>)<br>
SHA-256: `45c5f9fea2ae668138c4a797839e07831dfeaac1eaafcad02b52e2337d9df6d2`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Edgerunners/meta\-llama\-3\-8b\-instruct\-hf\-ortho\-baukit\-34fail\-3000total\-bf16 |
| Name | meta\-llama\-3\-8b\-instruct\-hf\-ortho\-baukit\-34fail\-3000total\-bf16 |
| Developed by | Edgerunners \(Hub organization\) |
| License | cc\-by\-nc\-4\.0 |
| Release date | 2024\-05\-12 \(Hugging Face repository creation date\) |
| Version | 4b8290f9ef1f7d33df282d3764f795af4e64022c |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is an implementation of the refusal direction method from the cited Alignment Forum paper, applied to Llama 3 8B Instruct using an updated Baukit implementation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 27 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that this version produced 34 refusals across 3,000 orthogonality tests, a refusal count consistent with the other versions in the same series\. |
| Safety evaluations | The developer reports 34 refusals out of 3,000 orthogonality tests, noting this is in line with the other versions in the series\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Edgerunners/meta\-llama\-3\-8b\-instruct\-hf\-ortho\-baukit\-34fail\-3000total\-bf16](<https://huggingface.co/Edgerunners/meta-llama-3-8b-instruct-hf-ortho-baukit-34fail-3000total-bf16>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | The card&\#x27;s only reported safety evaluation is a refusal count on 3,000 orthogonality tests, which measures refusal behavior rather than the specific safety risks of an open\-weight refusal\-direction model, so the selected metric may be incomplete for this checkpoint\. | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
