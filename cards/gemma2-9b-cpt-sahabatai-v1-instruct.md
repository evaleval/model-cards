# Model Card: Gemma2 9B CPT Sahabat\-AI v1 Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma2\-9b\-cpt\-sahabatai\-v1\-instruct\.json](<./gemma2-9b-cpt-sahabatai-v1-instruct.json>)<br>
SHA-256: `6e83940d45633e933fb68b9f8c4807c09c4eef9678a99f1851e978fcef3656e6`

## Identity

| Field | Value |
| --- | --- |
| Model ID | GoToCompany/gemma2\-9b\-cpt\-sahabatai\-v1\-instruct |
| Name | Gemma2 9B CPT Sahabat\-AI v1 Instruct |
| Developed by | GoToCompany \(Hub organization\) |
| Model type | Decoder model\. |
| License | gemma |
| Release date | 2024\-11\-06 \(Hugging Face repository creation date\) |
| Version | ca19cec82a7d2bdba20020e1bebf296417cfc3ee |
| Summary | An Indonesian\-focused instruction\-tuned model built from continued pretraining on Gemma2, fine\-tuned on hundreds of thousands of Indonesian and dialect instruction\-completion pairs\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | GoToCompany/gemma2\-9b\-cpt\-sahabatai\-v1\-base (base model; Kind: finetune) |
| Model family | gemma2 cpt sahabatai v1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 9,241,705,984 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 17\.2 GiB of safetensors weights \(18,483,466,448 bytes\) in BF16 |
| Input / output | Text input<br>Text output<br>Languages: English, Indonesian, Javanese, Sundanese |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a fine\-tune of Gemma2 9B, trained on synthetic instructions and publicly available instructions hand\-curated by the team with native\-speaker assistance\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 154 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 47 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports evaluating the model on general language capabilities and instruction\-following capabilities\. |
| Safety evaluations | The developer states that the model has not been aligned for safety\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/GoToCompany/gemma2\-9b\-cpt\-sahabatai\-v1\-instruct](<https://huggingface.co/GoToCompany/gemma2-9b-cpt-sahabatai-v1-instruct>) |
| Citation | @inproceedings\{koto\-etal\-2023\-indommlu,<br>    title = "Large Language Models Only Pass Primary School Exams in \{I\}ndonesia: A Comprehensive Test on \{I\}ndo\{MMLU\}",<br>    author = "Fajri Koto and Nurul Aisyah and Haonan Li and Timothy Baldwin",<br>    booktitle = "Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing \(EMNLP\)",<br>    month = December,<br>    year = "2023",<br>    address = "Singapore",<br>    publisher = "Association for Computational Linguistics",<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports no details on model design, training, or evaluation process beyond a brief summary, and the developer states the model has not been aligned for safety\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card describes training data only as synthetic instructions and hand\-curated public instructions, without dataset sizes, curation details, or synthetic generation process\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not document how the Indonesian/dialect instruction data was collected, curated, or used, nor the synthetic data generation process\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | The model is fine\-tuned on synthetic instructions and hand\-curated public instructions, which may not capture the full complexity of real\-world Indonesian/dialect language use\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | The fine\-tuning data consists of synthetic and hand\-curated public instructions, which can inherit or amplify societal and historical biases\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
