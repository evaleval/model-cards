# Model Card: FinMatcha\-3B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [finmatcha\-3b\-instruct\.json](<./finmatcha-3b-instruct.json>)<br>
SHA-256: `3c6fc6799ce2b7536d3f2d607e8ac9aa5df8cee2dda722c02f5aa44e23eccfd7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | xMaulana/FinMatcha\-3B\-Instruct |
| Name | FinMatcha\-3B\-Instruct |
| Developed by | xMaulana \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-09\-29 \(Hugging Face repository creation date\) |
| Version | e4b79163de00ac2d51c58a6c173e875d2899118b |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Llama\-3\.2\-3B\-Instruct (base model; Kind: finetune) |
| Model family | FinMatcha |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,212,749,824 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 6\.0 GiB of safetensors weights \(6,425,528,792 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint was fine\-tuned on Indonesian datasets, including NekoFi/alpaca\-gpt4\-indonesia\-cleaned, to handle Indonesian from formal to colloquial speech\. |
| Adaptations | The model is a fine\-tune on Indonesian datasets, emphasizing Indonesian language understanding and generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 30 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/xMaulana/FinMatcha\-3B\-Instruct](<https://huggingface.co/xMaulana/FinMatcha-3B-Instruct>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card only says fine\-tuned on Indonesian datasets including NekoFi/alpaca\-gpt4\-indonesia\-cleaned, with no dataset size, curation, or composition details, so training\-data transparency is limited\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Fine\-tuning on Indonesian conversational/instruction datasets, including a translated/cleaned Alpaca\-style set, may not represent the full range of Indonesian formal\-to\-colloquial speech or downstream tasks\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Fine\-tuning on a single Indonesian instruction dataset can inherit or amplify biases from that seed data and from the base Llama\-3\.2\-3B\-Instruct model, with no bias evaluation reported\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card describes Indonesian language understanding/generation but gives no intended\-use or out\-of\-scope guidance, leaving downstream risk definitions open\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
