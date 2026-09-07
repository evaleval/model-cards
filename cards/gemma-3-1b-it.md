# Model Card: gemma\-3\-1b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-1b\-it\.json](<./gemma-3-1b-it.json>)<br>
SHA-256: `76cd5590f750fbc19198c6b59725a8e48372299047049e4d83e686d630f64740`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-1b\-it |
| Name | gemma\-3\-1b\-it |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2025\-03\-10 \(Hugging Face repository creation date\) |
| Version | dcc83ea841ab6100d6b47a070329e1ba4cf78752 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-3\-1b\-pt (base model; Kind: finetune) |
| Model family | gemma 3 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 999,885,952 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 1\.9 GiB of safetensors weights \(1,999,811,208 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The target checkpoint was trained on a text dataset assembled from a wide variety of sources\. |
| Adaptations | The model is instruction\-tuned, so chat templates must be applied to inputs before use\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 2,504,623 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1,133 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model was evaluated across a broad range of datasets and metrics to assess various aspects of text generation\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-1b\-it](<https://huggingface.co/google/gemma-3-1b-it>) |
| Technical report | [https://arxiv\.org/abs/2503\.19786](<https://arxiv.org/abs/2503.19786>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only broad evaluation across datasets/metrics and a vague &\#x27;wide variety of sources&\#x27; for training data, with no design/evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Training data is described only as &\#x27;assembled from a wide variety of sources&\#x27; with no dataset details, curation, or composition information\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card does not identify the sources or ownership/usage terms of the text data, so provenance is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or misuse guidance for this instruction\-tuned text model, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
