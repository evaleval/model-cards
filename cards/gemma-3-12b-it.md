# Model Card: gemma\-3\-12b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-12b\-it\.json](<./gemma-3-12b-it.json>)<br>
SHA-256: `9d85ad5ba9f419bfb1d25936b5878ccb257a6bc767876bdb6fba8fefb445ad17`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-12b\-it |
| Name | gemma\-3\-12b\-it |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2025\-03\-01 \(Hugging Face repository creation date\) |
| Version | 96b6f1eccf38110c56df3a15bffe176da04bfd80 |
| Summary | Gemma 3 is a lightweight, state\-of\-the\-art open model family from Google, built using the same research and technology as the Gemini models\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-3\-12b\-pt (base model; Kind: finetune) |
| Model family | gemma 3 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 12,187,325,040 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 22\.7 GiB of safetensors weights \(24,374,793,024 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on a text dataset drawn from a wide variety of sources\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 761,252 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 817 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-12b\-it](<https://huggingface.co/google/gemma-3-12b-it>) |
| Technical report | [https://arxiv\.org/abs/2503\.19786](<https://arxiv.org/abs/2503.19786>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only high\-level training data description \('text dataset drawn from a wide variety of sources'\) and no evaluation details, so design/development/evaluation process is insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card states training data only as 'text dataset drawn from a wide variety of sources' without dataset details, so training/tuning dataset documentation is insufficient\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | No training data access is provided in the card; only a vague 'wide variety of sources' description is given\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because training data is not accessible or specified, content of training data used for outputs is not traceable\. | The content of the training data used for generating the model's output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card describes modalities and family but does not define intended use or downstream tasks, leaving relevant risks undefined as use changes\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
