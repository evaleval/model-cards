# Model Card: kimi\-k2\.6

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [kimi\-k2\.6\.json](<./kimi-k2.6.json>)<br>
SHA-256: `2979b51c6af8372a4fbef99991f5716d6575948f0749ded08a4f74933641d9ed`

## Identity

| Field | Value |
| --- | --- |
| Model ID | moonshotai/kimi\-k2\.6 |
| Name | kimi\-k2\.6 |
| Developed by | moonshotai \(Hub organization\) |
| License | other |
| Release date | 2026\-04\-14 \(Hugging Face repository creation date\) |
| Version | 7eb5002f6aadc958aed6a9177b7ed26bb94011bb |

## Lineage

| Field | Value |
| --- | --- |
| Model family | kimi k2\.6 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 1,026,879,376,368 parameters \(safetensors metadata\) |
| Precision | I32 \(safetensors weight dtype\) |
| Model size | 554\.3 GiB of safetensors weights \(595,177,988,208 bytes\) in I32 |
| Input / output | input: image, text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 599,946 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1,601 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The developer reports that Kimi K2\.6 delivers measurable improvements in real\-world reliability, including enhanced safety awareness during extended research tasks\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/moonshotai/kimi\-k2\.6](<https://huggingface.co/moonshotai/kimi-k2.6>) |
| Technical report | [https://arxiv\.org/abs/2602\.02276](<https://arxiv.org/abs/2602.02276>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only a one\-line safety claim and no design, training, or evaluation details for this exact checkpoint, so documentation is insufficient to assess its risks\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not describe training or tuning data for kimi\-k2\.6, so dataset composition and provenance are undocumented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only broad image/text\-to\-text modalities and open weights, without specifying intended or prohibited uses, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.code_repository`, `links.citation`.
