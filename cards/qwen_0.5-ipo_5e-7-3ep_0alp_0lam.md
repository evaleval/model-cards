# Model Card: Qwen\_0\.5\-IPO\_5e\-7\-3ep\_0alp\_0lam

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen\_0\.5\-ipo\_5e\-7\-3ep\_0alp\_0lam\.json](<./qwen_0.5-ipo_5e-7-3ep_0alp_0lam.json>)<br>
SHA-256: `2c599abc38c6e3198135c5afd707cb0e1ae131cbe42decce7c116b87e9bf23f9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen\_0\.5\-IPO\_5e\-7\-3ep\_0alp\_0lam |
| Name | Qwen\_0\.5\-IPO\_5e\-7\-3ep\_0alp\_0lam |
| Developed by | JayHyeon \(Hub organization\) |
| Release date | 2025\-01\-25 \(Hugging Face repository creation date\) |
| Version | 988e4c6867133c584f00c130e47dc6bd841019ca |

## Lineage

| Field | Value |
| --- | --- |
| Base models | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep (base model; Kind: finetune) |
| Model family | Qwen\_0\.5\-IPO\_5e\-7\-3ep\_0alp\_0lam |

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
| Training data | This checkpoint is a fine\-tune of JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep, trained on the trl\-lib/ultrafeedback\_binarized dataset\. |

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
| Model card | [https://huggingface\.co/JayHyeon/Qwen\_0\.5\-IPO\_5e\-7\-3ep\_0alp\_0lam](<https://huggingface.co/JayHyeon/Qwen_0.5-IPO_5e-7-3ep_0alp_0lam>) |
| Citation | @inproceedings\{rafailov2023direct,<br>    title        = \{\{Direct Preference Optimization: Your Language Model is Secretly a Reward Model\}\},<br>    author       = \{Rafael Rafailov and Archit Sharma and Eric Mitchell and Christopher D\. Manning and Stefano Ermon and Chelsea Finn\},<br>    year         = 2023,<br>    booktitle    = \{Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 \- 16, 2023\},<br>    url          = \{http://papers\.nips\.cc/paper\_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7\-Abstract\-Conference\.html\},<br>    editor       = \{Alice Oh and Tristan Naumann and Amir Globerson and Kate Saenko and Moritz Hardt and Sergey Levine\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, base checkpoint, and dataset name; no training/evaluation details or inner\-workings documentation for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names the fine\-tuning dataset but gives no dataset documentation, composition, or preprocessing details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card states it is a fine\-tune of JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep on trl\-lib/ultrafeedback\_binarized but provides no traceability of data origin, ownership, or transformations\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not state intended use or out\-of\-scope uses, so relevant risks cannot be scoped\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
