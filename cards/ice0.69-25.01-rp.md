# Model Card: Ice0\.69\-25\.01\-RP

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [ice0\.69\-25\.01\-rp\.json](<./ice0.69-25.01-rp.json>)<br>
SHA-256: `94aa6945338b6f7cf9b0e68fe7a1c585cd549ed4920f98bcc9ea3ad560f67e72`

## Identity

| Field | Value |
| --- | --- |
| Model ID | icefog72/Ice0\.69\-25\.01\-RP |
| Name | Ice0\.69\-25\.01\-RP |
| Developed by | icefog72 \(Hub organization\) |
| License | cc\-by\-nc\-4\.0 |
| Release date | 2025\-01\-26 \(Hugging Face repository creation date\) |
| Version | e1eca954b660c98d83a199ea0a83822471f02373 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Ice0\.69 25\.01 RP |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,498,032 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of two checkpoints, created using the SLERP merge method\. The merge included the models Ice0\.60\-18\.01\-RP and Ice0\.66\-25\.01\-RP\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 10 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/icefog72/Ice0\.69\-25\.01\-RP](<https://huggingface.co/icefog72/Ice0.69-25.01-RP>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | open\-weight text model with cc\-by\-nc\-4\.0 license and no stated data filtering or prompt controls \-&gt; users may include copyrighted material in prompts | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
