# Model Card: 🔬 Einstein\-v4\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [einstein\-v4\-7b\.json](<./einstein-v4-7b.json>)<br>
SHA-256: `4f262976857c4f25676f41b88a5789a2bb134afbd66b4af898072c73ffa99818`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Weyaxi/Einstein\-v4\-7B |
| Name | 🔬 Einstein\-v4\-7B |
| Developed by | Weyaxi \(Hub organization\) |
| License | other |
| Release date | 2024\-02\-22 \(Hugging Face repository creation date\) |
| Version | d88824fd98e515f944fd3eafbbfb231d6b850edd |
| Summary | A full fine\-tuned version of Mistral\-7B\-v0\.1 on diverse datasets\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | mistralai/Mistral\-7B\-v0\.1 (base model; Kind: finetune) |
| Model family | Einstein v4 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,748,480 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a full fine\-tune of mistralai/Mistral\-7B\-v0\.1, trained for 1\.5 epochs using axolotl on 7xRTX3090 \+ 1xRTXA6000\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 96 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 48 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Weyaxi/Einstein\-v4\-7B](<https://huggingface.co/Weyaxi/Einstein-v4-7B>) |
| Citation | The model card thanks the dataset authors mentioned in its datasets section\. |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card states training on &\#x27;diverse datasets&\#x27; but gives no dataset names, sources, or usage terms, so provenance is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card lacks documentation of how the &\#x27;diverse datasets&\#x27; were collected, curated, or used, limiting explanation of model behavior\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, base model, and training setup, with no evaluation results or design/development details\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | Open\-weight full fine\-tune of Mistral\-7B\-v0\.1 with no reported evaluations or intended\-use restrictions could be used for purposes it was not designed for\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `specifications.model_size`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
