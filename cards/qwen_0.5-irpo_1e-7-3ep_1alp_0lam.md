# Model Card: Qwen\_0\.5\-IRPO\_1e\-7\-3ep\_1alp\_0lam

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen\_0\.5\-irpo\_1e\-7\-3ep\_1alp\_0lam\.json](<./qwen_0.5-irpo_1e-7-3ep_1alp_0lam.json>)<br>
SHA-256: `3856855f7aa77a2aef7f8ba30ed08c34caa42b9e966f659895f41e9a6337eb92`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen\_0\.5\-IRPO\_1e\-7\-3ep\_1alp\_0lam |
| Name | Qwen\_0\.5\-IRPO\_1e\-7\-3ep\_1alp\_0lam |
| Developed by | JayHyeon \(Hub organization\) |
| Model type | Fine\-tuned language model |
| Release date | 2025\-01\-09 \(Hugging Face repository creation date\) |
| Version | a67e92b345a9088967f1e55d7c2dd06a1f0a73b1 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep (base model; Kind: finetune) |
| Model family | Qwen\_0\.5\-IRPO\_1e\-7\-3ep\_1alp\_0lam |

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
| Downloads | 11 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/JayHyeon/Qwen\_0\.5\-IRPO\_1e\-7\-3ep\_1alp\_0lam](<https://huggingface.co/JayHyeon/Qwen_0.5-IRPO_1e-7-3ep_1alp_0lam>) |
| Citation | @inproceedings\{rafailov2023direct,<br>    title        = \{\{Direct Preference Optimization: Your Language Model is Secretly a Reward Model\}\},<br>    author       = \{Rafael Rafailov and Archit Sharma and Eric Mitchell and Christopher D\. Manning and Stefano Ermon and Chelsea Finn\},<br>    year         = 2023,<br>    booktitle    = \{Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 \- 16, 2023\},<br>    url          = \{http://papers\.nips\.cc/paper\_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7\-Abstract\-Conference\.html\},<br>    editor       = \{Alice Oh and Tristan Naumann and Amir Globerson and Kate Saenko and Moritz Hardt and Sergey Levine\},<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only minimal architecture/task/access info and no design, development, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card names a base/family and fine\-tuning hyperparameters but does not document training data collection, curation, or synthetic generation\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only &\#x27;Fine\-tuned language model&\#x27; with no intended\-use or deployment scope, so downstream risk assessment is incomplete\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
