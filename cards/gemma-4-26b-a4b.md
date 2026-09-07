# Model Card: gemma\-4\-26b\-a4b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-4\-26b\-a4b\.json](<./gemma-4-26b-a4b.json>)<br>
SHA-256: `fb67dd8c802a79ad7d50e7003fc544fc4442d2fd9c53f7ac9f7a7d984013050b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-4\-26b\-a4b |
| Name | gemma\-4\-26b\-a4b |
| Developed by | google \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2026\-03\-12 \(Hugging Face repository creation date\) |
| Version | 24548b62aa021d562695c04aaf7758a1ea47990b |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma 4 a4b |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 26,544,131,376 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 48\.1 GiB of safetensors weights \(51,612,009,916 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The release includes both pre\-trained and instruction\-tuned open\-weight variants\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 51,337 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 396 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Gemma 4 models are designed for frontier\-level performance at each size, targeting deployment from mobile and edge devices to consumer GPUs and workstations\. For the 26B A4B model specifically, the Mixture\-of\-Experts design activates only a 4B parameter subset during inference, making it run much faster than its 26B total might suggest\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-4\-26b\-a4b](<https://huggingface.co/google/gemma-4-26b-a4b>) |
| Code repository | [https://github\.com/bebechien/gemma](<https://github.com/bebechien/gemma>) |
| Citation | @misc\{gemmateam2026gemma4,<br>      title=\{Gemma 4 Technical Report\}, <br>      author=\{Gemma Team\},<br>      year=\{2026\},<br>      eprint=\{2607\.02770\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2607\.02770\}, <br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card summary provides only high\-level architecture and access details, with no reported evaluations or training data documentation for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card summary does not describe training or tuning dataset details for gemma\-4\-26b\-a4b\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card summary states broad deployment targets and frontier\-level performance but does not define intended uses or limitations for this checkpoint\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
