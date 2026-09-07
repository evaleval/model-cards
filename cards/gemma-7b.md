# Model Card: gemma\-7b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-7b\.json](<./gemma-7b.json>)<br>
SHA-256: `50df8ebc5d22123a438c2e6f1cb5cda493b1dc0d3233749a97359492fe66a9c3`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-7b |
| Name | gemma\-7b |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2024\-02\-08 \(Hugging Face repository creation date\) |
| Version | ff6768d9368919a1f025a54f9f5aa0ee591730bb |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 8,537,680,896 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.9 GiB of safetensors weights \(17,075,391,360 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | 6 trillion tokens |
| Adaptations | This is the 7B base version of the Gemma model, with no post\-training or alignment described\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 35,125 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 3,404 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model was evaluated across a large collection of datasets and metrics covering different aspects of text generation, with structured evaluations and internal red\-teaming\. Safety and ethics evaluation results are described as within acceptable thresholds for internal policies on categories such as child safety, content safety, representational harms, memorization, and large\-scale harms\. |
| Human evaluations | The developer reports structured evaluations and internal red\-teaming testing of relevant content policies, conducted by multiple teams with different goals and human evaluation metrics\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| ARC\-c | Not specified | 61\.9 | Not specified | Not reported |
| HellaSwag | Not specified | 82\.2 | Not specified | Not reported |
| MMLU | Not specified | 64\.6 | Not specified | Not reported |
| TruthfulQA | Not specified | 44\.8 | Not specified | Not reported |
| Winogrande | Not specified | 79 | Not specified | Not reported |
| GSM8K | Not specified | 50\.9 | Not specified | Not reported |
| Average | Not specified | 63\.8 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-7b](<https://huggingface.co/google/gemma-7b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only that gemma\-7b is a 7B base version with no post\-training or alignment described and gives no details on architecture, training data, or inner workings\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details, only reports evaluation results and red\-teaming\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | Training data is not accessible from the card, limiting the types of explanations the model can provide and making them more likely to be incorrect\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because training data content is not accessible, the content used for generating the model's output cannot be traced\. | The content of the training data used for generating the model's output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card describes gemma\-7b as a base model with no post\-training or alignment and does not define intended uses, so relevant risks change depending on downstream use\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.data_cutoff`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
