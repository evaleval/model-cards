# Model Card: Granite\-3\.1\-8B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [granite\-3\.1\-8b\-instruct\.json](<./granite-3.1-8b-instruct.json>)<br>
SHA-256: `c8afcb510c3dfdc95007c766fc4f9d07cc8c8a28aa1f026ecbccc06576986a8d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | ibm\-granite/granite\-3\.1\-8b\-instruct |
| Name | Granite\-3\.1\-8B\-Instruct |
| Developed by | ibm\-granite \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-12\-06 \(Hugging Face repository creation date\) |
| Version | 4009206d5fc95d2e65a7b7633e159d6e97e25d35 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | ibm\-granite/granite\-3\.1\-8b\-base (base model; Kind: finetune) |
| Model family | granite 3\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,170,848,256 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.2 GiB of safetensors weights \(16,341,738,616 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Granite\-3\.1\-8B\-Instruct was fine\-tuned from Granite\-3\.1\-8B\-Base using a combination of permissively licensed open\-source instruction datasets, internally collected synthetic datasets for long\-context problems, and small amounts of human\-curated data\. |
| Adaptations | The model was developed with supervised fine\-tuning, reinforcement learning alignment, and model merging, using a structured chat format\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 33,174 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 168 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports benchmark results for Granite\-3\.1\-8B\-Instruct across two sets of evaluations, with scores varying by task category\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/ibm\-granite/granite\-3\.1\-8b\-instruct](<https://huggingface.co/ibm-granite/granite-3.1-8b-instruct>) |
| Code repository | [https://github\.com/ibm\-granite/granite\-3\.1\-language\-models](<https://github.com/ibm-granite/granite-3.1-language-models>) |
| Citation | @misc\{granite\-models,<br>  author = \{author 1, author2, \.\.\.\},<br>  title = \{\},<br>  journal = \{\},<br>  volume = \{\},<br>  year = \{2024\},<br>  url = \{https://arxiv\.org/abs/0000\.00000\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card lists only broad data categories \(open\-source instruction datasets, synthetic long\-context data, small human\-curated data\) without dataset details or synthetic generation documentation\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Fine\-tuning relies on synthetic long\-context datasets, which may not capture real\-world complexity and nuances\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data is described as permissively licensed open\-source plus synthetic and human\-curated data, but the card does not provide traceability or verification of sources and usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Fine\-tuning from base model on open\-source and synthetic datasets can inherit or exacerbate historical/societal biases, but no bias evaluation is reported\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports benchmark scores by task category but provides no details on evaluation methodology, inner workings, or design decisions\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
