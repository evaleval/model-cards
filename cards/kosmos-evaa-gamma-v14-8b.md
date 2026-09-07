# Model Card: Kosmos\-EVAA\-gamma\-v14\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [kosmos\-evaa\-gamma\-v14\-8b\.json](<./kosmos-evaa-gamma-v14-8b.json>)<br>
SHA-256: `0bb1b02934dc315a6518aed808a3d202eac51fe6a1c333560170c9ef2833cb87`

## Identity

| Field | Value |
| --- | --- |
| Model ID | jaspionjader/Kosmos\-EVAA\-gamma\-v14\-8B |
| Name | Kosmos\-EVAA\-gamma\-v14\-8B |
| Developed by | jaspionjader \(Hub organization\) |
| Release date | 2024\-12\-28 \(Hugging Face repository creation date\) |
| Version | 0a4ee872602c0cc95e0cec0c49807d29ead4586f |

## Lineage

| Field | Value |
| --- | --- |
| Base models | jaspionjader/Kosmos\-EVAA\-gamma\-light\-8B (base model; Kind: merge)<br>jaspionjader/Kosmos\-EVAA\-gamma\-v13\-8B (base model; Kind: merge) |

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
| Adaptations | This model is a merge of two 8B checkpoints, jaspionjader/Kosmos\-EVAA\-gamma\-light\-8B and jaspionjader/Kosmos\-EVAA\-gamma\-v13\-8B, combined using the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/jaspionjader/Kosmos\-EVAA\-gamma\-v14\-8B](<https://huggingface.co/jaspionjader/Kosmos-EVAA-gamma-v14-8B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, merge method, and base checkpoints, with no reported evaluations or training details for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for the merged checkpoint or its source checkpoints\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states no intended use or downstream use restrictions, leaving risk scope undefined for this open\-weight text model\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
