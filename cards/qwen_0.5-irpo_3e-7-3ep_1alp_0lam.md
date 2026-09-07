# Model Card: Qwen\_0\.5\-IRPO\_3e\-7\-3ep\_1alp\_0lam

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen\_0\.5\-irpo\_3e\-7\-3ep\_1alp\_0lam\.json](<./qwen_0.5-irpo_3e-7-3ep_1alp_0lam.json>)<br>
SHA-256: `f5c4084a9f44e8d3305d85f3ec2e2fe49962bb4c57ddffc5fb723dc5bae07b0e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen\_0\.5\-IRPO\_3e\-7\-3ep\_1alp\_0lam |
| Name | Qwen\_0\.5\-IRPO\_3e\-7\-3ep\_1alp\_0lam |
| Developed by | JayHyeon \(Hub organization\) |
| Release date | 2025\-01\-12 \(Hugging Face repository creation date\) |
| Version | cde396f65f5126dd17c25a7ca1f1749df260883c |

## Lineage

| Field | Value |
| --- | --- |
| Base models | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep (base model; Kind: finetune) |

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
| Downloads | 14 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/JayHyeon/Qwen\_0\.5\-IRPO\_3e\-7\-3ep\_1alp\_0lam](<https://huggingface.co/JayHyeon/Qwen_0.5-IRPO_3e-7-3ep_1alp_0lam>) |
| Citation | @inproceedings\{rafailov2023direct,<br>    title        = \{\{Direct Preference Optimization: Your Language Model is Secretly a Reward Model\}\},<br>    author       = \{Rafael Rafailov and Archit Sharma and Eric Mitchell and Christopher D\. Manning and Stefano Ermon and Chelsea Finn\},<br>    year         = 2023,<br>    booktitle    = \{Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 \- 16, 2023\},<br>    url          = \{http://papers\.nips\.cc/paper\_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7\-Abstract\-Conference\.html\},<br>    editor       = \{Alice Oh and Tristan Naumann and Amir Globerson and Kate Saenko and Moritz Hardt and Sergey Levine\},<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, modality, and access type; no design, development, or evaluation details are reported for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for this checkpoint\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | No training data access or dataset information is provided in the card summary\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because no training data content or provenance is documented, the content used to generate outputs is not accessible/traceable\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card lacks documentation of how data was collected, curated, and used to train the model\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
