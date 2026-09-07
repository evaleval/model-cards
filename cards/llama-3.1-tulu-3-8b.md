# Model Card: Llama\-3\.1\-Tulu\-3\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-tulu\-3\-8b\.json](<./llama-3.1-tulu-3-8b.json>)<br>
SHA-256: `be11af657363e6cf42c48a7d2d27da8442794197d262bb85d630bc805c338a52`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allenai/Llama\-3\.1\-Tulu\-3\-8B |
| Name | Llama\-3\.1\-Tulu\-3\-8B |
| Developed by | allenai \(Hub organization\) |
| License | llama3\.1 |
| Release date | 2024\-11\-20 \(Hugging Face repository creation date\) |
| Version | 666943798adbde0b1aff34626007e26986a3c107 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | allenai/Llama\-3\.1\-Tulu\-3\-8B\-DPO (base model; Kind: finetune) |
| Model family | Llama 3\.1 Tulu 3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,326,784 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,687,448 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 7,867 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 178 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/allenai/Llama\-3\.1\-Tulu\-3\-8B](<https://huggingface.co/allenai/Llama-3.1-Tulu-3-8B>) |
| Technical report | [https://arxiv\.org/abs/2411\.15124](<https://arxiv.org/abs/2411.15124>) |
| Code repository | [https://github\.com/allenai/open\-instruct](<https://github.com/allenai/open-instruct>) |
| Citation | @article\{lambert2024tulu3,<br>  title = \{Tülu 3: Pushing Frontiers in Open Language Model Post\-Training\},<br>  author = \{<br>    Nathan Lambert and <br>    Jacob Morrison and <br>    Valentina Pyatkin and <br>    Shengyi Huang and <br>    Hamish Ivison and <br>    Faeze Brahman and <br>    Lester James V\. Miranda and <br>    Alisa Liu and <br>    Nouha Dziri and <br>    Shane Lyu and <br>    Yuling Gu and <br>    Saumya Malik and <br>    Victoria Graf and <br>    Jena D\. Hwang and <br>    Jiangjiang Yang and<br>    Ronan Le Bras and<br>    Oyvind Tafjord and<br>    Chris Wilhelm and<br>    Luca Soldaini and <br>    Noah A\. Smith and <br>    Yizhong Wang and <br>    Pradeep Dasigi and <br>    Hannaneh Hajishirzi<br>  \},<br>  year = \{2024\},<br>  email = \{tulu@allenai\.org\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card summary provides only basic architecture, modality, and license information, with no reported evaluations, training data, or safety testing details, so the checkpoint lacks sufficient documentation for transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
