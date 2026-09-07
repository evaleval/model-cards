# Model Card: MFANN\-phigments\-slerp\-V3\.2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mfann\-phigments\-slerp\-v3\.2\.json](<./mfann-phigments-slerp-v3.2.json>)<br>
SHA-256: `c0b634adbdb29106834987a6bf4a962a71efeae60d4a5f0ce5b76a2437b1d26b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | netcat420/MFANN\-phigments\-slerp\-V3\.2 |
| Name | MFANN\-phigments\-slerp\-V3\.2 |
| Developed by | netcat420 \(Hub organization\) |
| Release date | 2025\-02\-06 \(Hugging Face repository creation date\) |
| Version | f6d5df4a678f4b12d14de5a6371c4d34316e3483 |
| Summary | A merged language model created with mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | liminerity/Phigments12 (base model; Kind: merge)<br>netcat420/MFANN\-Phigments12\-slerp (base model; Kind: merge)<br>netcat420/MFANN\-phigments\-slerp\-1b (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 2,779,683,840 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 5\.2 GiB of safetensors weights \(5,559,417,368 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a merge of netcat420/MFANN\-phigments\-slerp\-1b and netcat420/MFANN\-Phigments12\-slerp, with liminerity/Phigments12 as the base\. |
| Adaptations | The model was created by merging the two listed models using the TIES merge method, with liminerity/Phigments12 as the base\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 12 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/netcat420/MFANN\-phigments\-slerp\-V3\.2](<https://huggingface.co/netcat420/MFANN-phigments-slerp-V3.2>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card only states that the model is a merge of two named models using TIES with liminerity/Phigments12 as base; it reports no evaluation, intended\-use, or design details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card gives no training\-data details for the merged checkpoint beyond the names of the merged models and base model, so the composition and provenance of the training data are undocumented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card describes the model only as a text\-to\-text merged language model and does not define intended uses, so the relevant risk profile is unspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
