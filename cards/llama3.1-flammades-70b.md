# Model Card: Llama3\.1\-Flammades\-70B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama3\.1\-flammades\-70b\.json](<./llama3.1-flammades-70b.json>)<br>
SHA-256: `23a37ac9244d6956ac30efd9e7cc28b3a9be17d2b0b588757fc667c8c2f92cca`

## Identity

| Field | Value |
| --- | --- |
| Model ID | flammenai/Llama3\.1\-Flammades\-70B |
| Name | Llama3\.1\-Flammades\-70B |
| Developed by | flammenai \(Hub organization\) |
| Model type | Text Generation |
| License | llama3\.1 |
| Release date | 2024\-10\-12 \(Hugging Face repository creation date\) |
| Version | 0ee8e705aa98233ee0d099098ee8e838d0ffb426 |
| Summary | A text\-generation model produced by ORPO tuning on two H100 GPUs for three epochs\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | nbeerbower/Llama3\.1\-Gutenberg\-Doppel\-70B (base model; Kind: finetune) |
| Model family | Llama3\.1 Flammades |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 70,553,706,496 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 131\.4 GiB of safetensors weights \(141,107,497,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was tuned with ORPO for 3 epochs on 2x H100 hardware\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 31 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/flammenai/Llama3\.1\-Flammades\-70B](<https://huggingface.co/flammenai/Llama3.1-Flammades-70B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, tuning method, and hardware; no training data, evaluation, or intended\-use details are stated\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe how the ORPO tuning data was collected, curated, or used, so training\-data documentation is missing\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card lists only 'Text Generation' as primary task and gives no intended or prohibited uses, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
