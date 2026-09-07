# Model Card: cursa\-o1\-7b\-v1\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [cursa\-o1\-7b\-v1\.1\.json](<./cursa-o1-7b-v1.1.json>)<br>
SHA-256: `8497392c86a4207b3f64994e74f8e23c4acb25dd3a583b28aa14189229b716ce`

## Identity

| Field | Value |
| --- | --- |
| Model ID | marcuscedricridia/cursa\-o1\-7b\-v1\.1 |
| Name | cursa\-o1\-7b\-v1\.1 |
| Developed by | marcuscedricridia \(Hub organization\) |
| Release date | 2025\-02\-28 \(Hugging Face repository creation date\) |
| Version | 7932d91ce03991a94866f4d7291c9866b3733906 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | marcuscedricridia/Abus\-7B\-Instruct (base model; Kind: merge)<br>marcuscedricridia/post\-cursa\-o1 (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,612,756,480 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,225,551,792 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of marcuscedricridia/pre\-cursa\-o1\-v1\.2 and marcuscedricridia/post\-cursa\-o1, combined using the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 19 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/marcuscedricridia/cursa\-o1\-7b\-v1\.1](<https://huggingface.co/marcuscedricridia/cursa-o1-7b-v1.1>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | open\-weight text model with no stated data or usage guardrails, and the card names a merge of instruct/post\-trained checkpoints, so prompts sent to it may include copyrighted material without mitigation\. | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
