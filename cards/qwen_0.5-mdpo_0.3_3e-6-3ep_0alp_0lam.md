# Model Card: Qwen\_0\.5\-MDPO\_0\.3\_3e\-6\-3ep\_0alp\_0lam

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen\_0\.5\-mdpo\_0\.3\_3e\-6\-3ep\_0alp\_0lam\.json](<./qwen_0.5-mdpo_0.3_3e-6-3ep_0alp_0lam.json>)<br>
SHA-256: `64238d2f49274a796c60405facfd72a4add1dda01a5e368db0e93a74884f90ce`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen\_0\.5\-MDPO\_0\.3\_3e\-6\-3ep\_0alp\_0lam |
| Name | Qwen\_0\.5\-MDPO\_0\.3\_3e\-6\-3ep\_0alp\_0lam |
| Developed by | JayHyeon \(Hub organization\) |
| Release date | 2025\-01\-07 \(Hugging Face repository creation date\) |
| Version | a12da9d1ddf0c4347cee214f43ac448a9390929e |

## Lineage

| Field | Value |
| --- | --- |
| Base models | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep (base model; Kind: finetune) |
| Model family | Qwen\_0\.5\-MDPO\_0\.3\_3e\-6\-3ep\_0alp\_0lam |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 630,167,424 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 1\.2 GiB of safetensors weights \(1,260,367,448 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 15 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/JayHyeon/Qwen\_0\.5\-MDPO\_0\.3\_3e\-6\-3ep\_0alp\_0lam](<https://huggingface.co/JayHyeon/Qwen_0.5-MDPO_0.3_3e-6-3ep_0alp_0lam>) |
| Citation | @inproceedings\{rafailov2023direct,<br>    title        = \{\{Direct Preference Optimization: Your Language Model is Secretly a Reward Model\}\},<br>    author       = \{Rafael Rafailov and Archit Sharma and Eric Mitchell and Christopher D\. Manning and Stefano Ermon and Chelsea Finn\},<br>    year         = 2023,<br>    booktitle    = \{Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 \- 16, 2023\},<br>    url          = \{http://papers\.nips\.cc/paper\_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7\-Abstract\-Conference\.html\},<br>    editor       = \{Alice Oh and Tristan Naumann and Amir Globerson and Kate Saenko and Moritz Hardt and Sergey Levine\},<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `risks.possible_risks`.
