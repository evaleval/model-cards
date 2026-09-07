# Model Card: MT3\-Gen4\-gemma\-2\-9B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mt3\-gen4\-gemma\-2\-9b\.json](<./mt3-gen4-gemma-2-9b.json>)<br>
SHA-256: `1e8621f6093c595aaa98e2490ef8fa1544d37c2de24af6bd3f684cf135e78755`

## Identity

| Field | Value |
| --- | --- |
| Model ID | zelk12/MT3\-Gen4\-gemma\-2\-9B |
| Name | MT3\-Gen4\-gemma\-2\-9B |
| Developed by | zelk12 \(Hub organization\) |
| Model type | Text\-generation model\. |
| License | gemma |
| Release date | 2024\-12\-16 \(Hugging Face repository creation date\) |
| Version | 9cbf6e0c1b34bb1b1571824f7348f6dd85456d25 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | zelk12/MT3\-Gen4\-GBMUI\-gemma\-2\-9B (base model; Kind: merge)<br>zelk12/MT3\-Gen4\-MAMM\-gemma\-2\-9B (base model; Kind: merge) |
| Model family | MT3 Gen4 gemma 2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 10,159,209,984 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 18\.9 GiB of safetensors weights \(20,318,474,544 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of zelk12/MT3\-Gen4\-MAMM\-gemma\-2\-9B and zelk12/MT3\-Gen4\-GBMUI\-gemma\-2\-9B, combined using the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 21 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/zelk12/MT3\-Gen4\-gemma\-2\-9B](<https://huggingface.co/zelk12/MT3-Gen4-gemma-2-9B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card only lists architecture, merge method, and license, with no reported evaluations or design/development details, so the checkpoint itself lacks transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card does not document training or tuning dataset details for this checkpoint, only the two merged parent model names\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | No training data is provided or described for this checkpoint, limiting explanations of its outputs\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the card gives no training\-data content or sources, the content used to generate outputs is not accessible or traceable\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not state how data was collected, curated, or used to train this checkpoint, so its behavior is hard to explain\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
