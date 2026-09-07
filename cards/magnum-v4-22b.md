# Model Card: magnum\-v4\-22b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [magnum\-v4\-22b\.json](<./magnum-v4-22b.json>)<br>
SHA-256: `ae625f51b696bbde18a54c491b0115bbe1f86abc54c9501f5a22aa84f57342e1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | anthracite\-org/magnum\-v4\-22b |
| Name | magnum\-v4\-22b |
| Developed by | anthracite\-org \(Hub organization\) |
| Model type | text generation |
| License | other |
| Release date | 2024\-10\-20 \(Hugging Face repository creation date\) |
| Version | e412f3077a1ccd2efb9bb4fbbac5824e7eec1ff3 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | magnum v4 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 22,247,282,688 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 41\.4 GiB of safetensors weights \(44,494,624,536 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This model is a fine\-tune of Mistral\-Small\-Instruct\-2409, trained on a set of anthracite\-org datasets including c2\_logs\_32k\_mistral\-v3\_v1\.2\_no\_system, kalo\-opus\-instruct\-22k\-no\-refusal\-no\-system, kalo\-opus\-instruct\-3k\-filtered\-no\-system, nopm\_claude\_writing\_fixed, and kalo\_opus\_misc\_240827\_no\_system\. |
| Adaptations | The model is a full\-parameter fine\-tune of Mistral\-Small\-Instruct\-2409, trained for 2 epochs on 8xH100 GPUs provided by Recursal AI / Featherless AI\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 306 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 33 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/anthracite\-org/magnum\-v4\-22b](<https://huggingface.co/anthracite-org/magnum-v4-22b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data includes anthracite\-org datasets with opaque names and no stated collection/verification details, so traceability of data origin and usage terms is not established\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card lists dataset names but does not document how data was collected, curated, or used, limiting ability to explain model behavior\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides architecture and fine\-tune base but no evaluation results, training details beyond epochs/hardware, or inner\-workings insights\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | Open\-weight full\-parameter fine\-tune of Mistral\-Small\-Instruct\-2409 with 'other' license and no documentation of data rights or governance makes responsibility hard to establish\. | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
