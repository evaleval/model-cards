# Model Card: nbeerbower/mistral\-nemo\-narwhal\-12B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-nemo\-narwhal\-12b\.json](<./mistral-nemo-narwhal-12b.json>)<br>
SHA-256: `26a4559af76d9c613e4ad1a80448244815cb72254a7709d8a982bab382d8b5ab`

## Identity

| Field | Value |
| --- | --- |
| Model ID | nbeerbower/mistral\-nemo\-narwhal\-12B |
| Name | nbeerbower/mistral\-nemo\-narwhal\-12B |
| Developed by | nbeerbower \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-13 \(Hugging Face repository creation date\) |
| Version | 9384d7e572a09181c79e19d934ab865f7a7d4efc |

## Lineage

| Field | Value |
| --- | --- |
| Base models | nbeerbower/Mahou\-1\.5\-mistral\-nemo\-12B\-lorablated (base model; Kind: finetune) |
| Model family | mistral nemo narwhal |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 12,247,782,400 parameters \(safetensors metadata\) |
| Context length | 1,024,000 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 22\.8 GiB of safetensors weights \(24,495,607,104 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was tuned with ORPO for one epoch using eight A100 GPUs, and the training setup included a QLoRA configuration\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/nbeerbower/mistral\-nemo\-narwhal\-12B](<https://huggingface.co/nbeerbower/mistral-nemo-narwhal-12B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, tuning recipe \(ORPO/QLoRA\), and license; no design or evaluation details are reported\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | No provenance or traceability information is given for the data used in the ORPO/QLoRA tuning\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only text\-to\-text modality and open weights, with no intended\-use or deployment context\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Unrepresentative risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-risk-testing.html>) | No evaluations or risk testing are reported, so any risk testing cannot be shown to match deployment inputs\. | Testing is unrepresentative when the test inputs are mismatched with the inputs that are expected during deployment\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
