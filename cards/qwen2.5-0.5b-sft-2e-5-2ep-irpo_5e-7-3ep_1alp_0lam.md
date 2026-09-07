# Model Card: Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-IRPO\_5e\-7\-3ep\_1alp\_0lam

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-0\.5b\-sft\-2e\-5\-2ep\-irpo\_5e\-7\-3ep\_1alp\_0lam\.json](<./qwen2.5-0.5b-sft-2e-5-2ep-irpo_5e-7-3ep_1alp_0lam.json>)<br>
SHA-256: `732cd89231e050019b50c03d25e9ddeb7737bb2b6479953ef01e123430342f1e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-IRPO\_5e\-7\-3ep\_1alp\_0lam |
| Name | Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-IRPO\_5e\-7\-3ep\_1alp\_0lam |
| Developed by | JayHyeon \(Hub organization\) |
| Model type | Fine\-tuned language model |
| Release date | 2025\-01\-02 \(Hugging Face repository creation date\) |
| Version | 8e123c07a2773ab109d8f81b0f9b36fb28ad8f75 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep (base model; Kind: finetune) |
| Model family | Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-IRPO\_5e\-7\-3ep\_1alp\_0lam |

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
| Adaptations | The model was trained with DPO\. |

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
| Model card | [https://huggingface\.co/JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-2ep\-IRPO\_5e\-7\-3ep\_1alp\_0lam](<https://huggingface.co/JayHyeon/Qwen2.5-0.5B-SFT-2e-5-2ep-IRPO_5e-7-3ep_1alp_0lam>) |
| Citation | @inproceedings\{rafailov2023direct,<br>    title        = \{\{Direct Preference Optimization: Your Language Model is Secretly a Reward Model\}\},<br>    author       = \{Rafael Rafailov and Archit Sharma and Eric Mitchell and Christopher D\. Manning and Stefano Ermon and Chelsea Finn\},<br>    year         = 2023,<br>    booktitle    = \{Advances in Neural Information Processing Systems 36: Annual Conference on Neural Information Processing Systems 2023, NeurIPS 2023, New Orleans, LA, USA, December 10 \- 16, 2023\},<br>    url          = \{http://papers\.nips\.cc/paper\_files/paper/2023/hash/a85b405ed65c6477a4fe8302b5e06ce7\-Abstract\-Conference\.html\},<br>    editor       = \{Alice Oh and Tristan Naumann and Amir Globerson and Kate Saenko and Moritz Hardt and Sergey Levine\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, base checkpoint, and DPO dataset; no reported evaluations, training details, or safety results for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card names the fine\-tuning dataset but does not document collection, curation, filtering, or preprocessing for this checkpoint\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Fine\-tuned only on ultrafeedback\_binarized, a preference dataset, with no evidence of coverage of downstream tasks or populations\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | DPO on a single preference dataset can inherit or amplify biases in that data; card reports no bias analysis or mitigation\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only &\#x27;fine\-tuned language model&\#x27; with no intended\-use or out\-of\-scope\-use definition, so relevant risks are undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
