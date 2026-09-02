# Model Card: Mistral\-7B\-Instruct\-v0\.3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-7b\-instruct\-v0\.3\.json](<./mistral-7b-instruct-v0.3.json>)<br>
SHA-256: `f63de372ee01789d2ecc24c7de581c44d0b9bc02df76b969045ff274269827de`

## Identity

| Field | Value |
| --- | --- |
| Model ID | mistralai/Mistral\-7B\-Instruct\-v0\.3 |
| Name | Mistral\-7B\-Instruct\-v0\.3 |
| Developed by | mistralai |
| Model type | mistral config model type |
| License | apache\-2\.0 |
| Version | c170c708c41dac9275d15a8fff4eca08d52bab71 |
| Summary | The publisher README identifies Mistral\-7B\-Instruct\-v0\.3 as a post\-trained checkpoint for model inference\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | mistralai/Mistral\-7B\-v0\.3 (base model) |
| Model family | mistral |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,248,023,552 total stored parameters \(safetensors metadata\) |
| Context length | 32,768 positions \(config max\_position\_embeddings; implementation limit, not an independently verified context window\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 13\.50 GiB estimated tensor payload \(14,496,047,104 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text<br>model stage: instruction\-tuned |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | Instruction fine\-tuning was applied to Mistral\-7B\-v0\.3\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Public Hugging Face repository with declared weight files |
| Downloads | 2,999,981 at frozen Hugging Face metadata snapshot |
| Likes | 2,834 at frozen Hugging Face metadata snapshot |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/mistralai/Mistral\-7B\-Instruct\-v0\.3/blob/c170c708c41dac9275d15a8fff4eca08d52bab71/README\.md](<https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3/blob/c170c708c41dac9275d15a8fff4eca08d52bab71/README.md>) |
| Code repository | [https://github\.com/mistralai/mistral\-inference](<https://github.com/mistralai/mistral-inference>) |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
