# Model Card: llama32\_3B\_en\_emo\_300\_stp

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama32\_3b\_en\_emo\_300\_stp\.json](<./llama32_3b_en_emo_300_stp.json>)<br>
SHA-256: `72fe9903f76f0b6a1daa06a07331fba35783bdd0b57bfecb8be6f87e7a3cfdd9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | iFaz/llama32\_3B\_en\_emo\_300\_stp |
| Name | llama32\_3B\_en\_emo\_300\_stp |
| Developed by | iFaz \(Hub organization\) |
| Model type | text\-generation\-inference |
| License | apache\-2\.0 |
| Release date | 2025\-03\-07 \(Hugging Face repository creation date\) |
| Version | 55c889bfaa908ca773e8ccab084ebe9b6f00d3dc |
| Summary | A Llama\-based model fine\-tuned for English emotion classification using Unsloth and Hugging Face TRL, optimized for faster training\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | llama |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,301,122,646 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | U8 \(safetensors weight dtype\) |
| Model size | 2\.1 GiB of safetensors weights \(2,242,762,539 bytes\) in U8 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a fine\-tune of unsloth/llama\-3\.2\-3b\-instruct\-bnb\-4bit, trained with Unsloth and Hugging Face&\#x27;s TRL library\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 20 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/iFaz/llama32\_3B\_en\_emo\_300\_stp](<https://huggingface.co/iFaz/llama32_3B_en_emo_300_stp>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, task, and fine\-tuning method; no training data details, evaluation results, or safety testing are reported for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not describe the emotion\-classification fine\-tuning dataset, its composition, or its provenance\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Fine\-tuned for English emotion classification but no dataset representativeness or coverage information is reported, so the tuning data may not represent the target population\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | No information about the fine\-tuning data is provided, so historical or societal biases in the emotion\-classification training data cannot be ruled out\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Poor model accuracy](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/poor-model-accuracy.html>) | No evaluation results are reported for the emotion\-classification task, so the checkpoint&\#x27;s accuracy on that task is unsubstantiated\. | Poor model accuracy occurs when a model&\#x27;s performance is insufficient to the task it was designed for\. Low accuracy might occur if the model is not correctly engineered, or if the model&\#x27;s expected inputs change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
