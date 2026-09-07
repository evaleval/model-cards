# Model Card: Infinity Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [infinity\-instruct\-3m\-0625\-llama3\-70b\.json](<./infinity-instruct-3m-0625-llama3-70b.json>)<br>
SHA-256: `58920b8f034a08c2e4f1b9326ccc6b68920743cf1c9f65a3cc644cd7f74cd347`

## Identity

| Field | Value |
| --- | --- |
| Model ID | BAAI/Infinity\-Instruct\-3M\-0625\-Llama3\-70B |
| Name | Infinity Instruct |
| Developed by | BAAI \(Hub organization\) |
| Model type | Supervised instruction tuning model |
| License | apache\-2\.0 |
| Release date | 2024\-07\-09 \(Hugging Face repository creation date\) |
| Version | 6d8ceada57e55cff3503191adc4d6379ff321fe2 |
| Summary | An open\-source supervised instruction\-tuning model that does not use reinforcement learning from human feedback\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Infinity Llama3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 70,553,706,496 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 131\.4 GiB of safetensors weights \(141,107,497,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a supervised instruction\-tuned version of Llama3\-70B, first trained on the foundational Infinity\-Instruct\-3M dataset and then further fine\-tuned on Infinity\-Instruct\-0625 to produce this chat model\. |
| Adaptations | The model is an open\-source supervised instruction tuning model without RLHF\. It was produced by fine\-tuning the Infinity\-Instruct\-3M\-Llama3\-70B foundational instruct model on Infinity\-Instruct\-0625\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 107 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 3 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that this model, a Llama\-3\-70B variant finetuned on the Infinity\-Instruct\-3M and Infinity\-Instruct\-0625 datasets, shows favorable AlpacaEval 2\.0 results compared with GPT4\-0613\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/BAAI/Infinity\-Instruct\-3M\-0625\-Llama3\-70B](<https://huggingface.co/BAAI/Infinity-Instruct-3M-0625-Llama3-70B>) |
| Citation | @article\{InfinityInstruct2024,<br>  title=\{Infinity Instruct\},<br>  author=\{Beijing Academy of Artificial Intelligence \(BAAI\)\},<br>  journal=\{arXiv preprint arXiv:2406\.XXXX\},<br>  year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only AlpacaEval 2\.0 results and gives no details on model design, development, or evaluation process beyond the fine\-tuning datasets\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card names Infinity\-Instruct\-3M and Infinity\-Instruct\-0625 but does not document how these datasets were collected, curated, or used\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Open\-weight model is fine\-tuned on Infinity\-Instruct datasets whose origin, ownership, and usage terms are not described in the card\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Supervised instruction tuning on large web\-derived instruction datasets without RLHF or reported bias analysis can inherit historical and societal biases from the training data\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | The card reports only AlpacaEval 2\.0 results and gives no evidence that the Infinity\-Instruct training data is representative of real\-world instruction\-following use\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
