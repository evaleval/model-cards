# Model Card: gemma\-3\-27b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-27b\-it\.json](<./gemma-3-27b-it.json>)<br>
SHA-256: `ddb71969daeadc84cc4d1c77db1786096a17decc1a0fd5c51642c2fa74c618e3`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-27b\-it |
| Name | gemma\-3\-27b\-it |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2025\-03\-01 \(Hugging Face repository creation date\) |
| Version | 005ad3404e59d6023443cb575daa05336842228a |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-3\-27b\-pt (base model; Kind: finetune) |
| Model family | gemma 3 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 27,432,406,640 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 51\.1 GiB of safetensors weights \(54,864,980,440 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The 27B checkpoint was trained on a text dataset drawn from a wide variety of sources\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 383,527 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2,022 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-27b\-it](<https://huggingface.co/google/gemma-3-27b-it>) |
| Technical report | [https://arxiv\.org/abs/2503\.19786](<https://arxiv.org/abs/2503.19786>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card summary provides only minimal information about the 27B checkpoint \(modalities, training data source, access, license\) and no reported evaluations or design/development details, so documentation is insufficient to assess inner workings\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card states only that the 27B checkpoint was trained on a text dataset drawn from a wide variety of sources, without dataset composition, filtering, or provenance details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The summary says training data came from a wide variety of sources but gives no traceability of ownership, origin, or usage terms for those sources\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card summary does not state intended uses or use restrictions for this checkpoint beyond its modalities and license, so relevant risks cannot be scoped to specific uses\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
