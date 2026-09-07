# Model Card: Qwen2\.5\-3B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-3b\-instruct\.json](<./qwen2.5-3b-instruct.json>)<br>
SHA-256: `609c5630e67442fcf0a405d7a2fa643590473c828c9a729b985c45c3305c07ce`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-3B\-Instruct |
| Name | Qwen2\.5\-3B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal language model |
| License | other |
| Release date | 2024\-09\-17 \(Hugging Face repository creation date\) |
| Version | aa8e72537993ba99e69dfaafa59ed015b17504d1 |
| Summary | Qwen2\.5\-3B\-Instruct is the instruction\-tuned 3B model in the Qwen2\.5 series, a dense decoder\-only causal language model supporting long contexts and tool calling\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-3B (base model; Kind: finetune) |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,085,938,688 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 5\.7 GiB of safetensors weights \(6,171,926,992 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model underwent both pretraining and post\-training stages\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 6,815,899 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 561 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer points to a blog for detailed evaluation results and states that instruction\-tuned versions were evaluated across benchmarks for capabilities and human preferences\. |
| Human evaluations | The developer reports evaluating instruction\-tuned versions across benchmarks, including human preferences, with detailed results in a blog\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-3B\-Instruct](<https://huggingface.co/Qwen/Qwen2.5-3B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only a blog link for detailed evaluation results and no design/development details for this checkpoint, so documentation of model design and evaluation is insufficient\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for Qwen2\.5\-3B\-Instruct, only states pretraining and post\-training stages\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | Open\-weight checkpoint with no training data access or dataset documentation, limiting explanations of outputs\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Training data content is not accessible from the card, so outputs cannot be traced to specific training data\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card lacks information on how data was collected, curated, and used for pretraining/post\-training, making behavior harder to explain\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`.
