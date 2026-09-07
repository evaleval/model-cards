# Model Card: Llama\-3\.2\-SUN\-1B\-chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.2\-sun\-1b\-chat\.json](<./llama-3.2-sun-1b-chat.json>)<br>
SHA-256: `ac867df8a3e64575f587f5c451ec20aa56801d5690ccf1720135eff7e4122b25`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meditsolutions/Llama\-3\.2\-SUN\-1B\-chat |
| Name | Llama\-3\.2\-SUN\-1B\-chat |
| Developed by | meditsolutions \(Hub organization\) |
| Model type | text\-generation |
| License | llama3\.2 |
| Release date | 2024\-11\-03 \(Hugging Face repository creation date\) |
| Version | af0dfce759ebf16446dff41229e1f73e0b34ac58 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Llama\-3\.2\-1B\-Instruct (base model; Kind: quantized) |
| Model family | Llama 3\.2 SUN |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,498,482,688 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.8 GiB of safetensors weights \(2,996,982,344 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on open datasets from Hugging Face, including open subsets of SFT datasets that permit commercial use\. |
| Adaptations | The model incorporates supervised fine\-tuning and uses the MedIT\-mesh technique for layer meshing\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 52 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meditsolutions/Llama\-3\.2\-SUN\-1B\-chat](<https://huggingface.co/meditsolutions/Llama-3.2-SUN-1B-chat>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card gives only high\-level facts \(architecture, fine\-tuning on open HF subsets, MedIT\-mesh\) and reports no evaluations, so the checkpoint&\#x27;s design/evaluation process is insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | It says fine\-tuning data are &\#x27;open subsets of SFT datasets that permit commercial use&\#x27; but does not identify the datasets or verify their origin/usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The summary does not describe how the fine\-tuning data were collected, curated, or used, making training\-data documentation incomplete\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only &\#x27;text\-generation&\#x27; as the primary task and gives no intended\-use or out\-of\-scope guidance, leaving downstream risk definition open\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
