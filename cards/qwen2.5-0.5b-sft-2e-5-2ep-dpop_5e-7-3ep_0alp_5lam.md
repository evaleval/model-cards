# Model Card: Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPOP\_5e\-7\-3ep\_0alp\_5lam

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-0\.5b\-sft\-2e\-5\-2ep\-dpop\_5e\-7\-3ep\_0alp\_5lam\.json](<./qwen2.5-0.5b-sft-2e-5-2ep-dpop_5e-7-3ep_0alp_5lam.json>)<br>
SHA-256: `d56d8c485a0142f6b9b6ecd4863ed47abb32dda9bfa47a2b629ba042818edb5d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPOP\_5e\-7\-3ep\_0alp\_5lam |
| Name | Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPOP\_5e\-7\-3ep\_0alp\_5lam |
| Developed by | JayHyeon \(Hub organization\) |
| Model type | Fine\-tuned language model |
| Release date | 2025\-01\-02 \(Hugging Face repository creation date\) |
| Version | c89911f8d376b2504dc7ef337d366ff13fd6fbc1 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep (base model; Kind: finetune) |
| Model family | Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPOP\_5e\-7\-3ep\_0alp\_5lam |

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

| Field | Value |
| --- | --- |
| Adaptations | The model was trained with DPO \(Direct Preference Optimization\)\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 13 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-DPOP\_5e\-7\-3ep\_0alp\_5lam](<https://huggingface.co/JayHyeon/Qwen2.5-0.5B-SFT-2e-5-2ep-DPOP_5e-7-3ep_0alp_5lam>) |
| Citation | @inproceedings\{rafailov2023direct,<br>    title        = \{\{Direct Preference Optimization: Your Language Model is Secretly a Reward Model\}\},<br>    author       = \{Rafael Rafailov and Archit Sharma and Eric Mitchell and Christopher D\. Manning and Stefano Ermon and Chelsea Finn\},<br>    year         = 2023,<br>    booktitle    = \{Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 \- 16, 2023\},<br>    url          = \{http://papers\.nips\.cc/paper\_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7\-Abstract\-Conference\.html\},<br>    editor       = \{Alice Oh and Tristan Naumann and Amir Globerson and Kate Saenko and Moritz Hardt and Sergey Levine\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, adaptation \(DPO\), and access; no training data, evaluation, or intended\-use details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not state how the fine\-tuning data was collected, curated, or used for DPO, so training\-data provenance is undocumented\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says 'Fine\-tuned language model' with no intended\-use or deployment scope, so relevant risks are undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
