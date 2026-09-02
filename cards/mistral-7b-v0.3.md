# Model Card: Mistral\-7B\-v0\.3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-7b\-v0\.3\.json](<./mistral-7b-v0.3.json>)<br>
SHA-256: `9927d75f63097c63ccdb47655dff496d1f645c973a589a6b0c4d869ac5325d09`

## Identity

| Field | Value |
| --- | --- |
| Model ID | mistralai/Mistral\-7B\-v0\.3 |
| Name | Mistral\-7B\-v0\.3 |
| Developed by | mistralai |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Version | caa1feb0e54d415e2df31207e5f4e273e33509b1 |
| Summary | Mistral\-7B\-v0\.3 is the publisher\-documented Mistral\-7B\-v0\.2 successor with an extended vocabulary\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | mistralai/Mistral\-7B\-v0\.2 (base model) |
| Model family | mistral |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,248,023,552 total stored parameters \(safetensors metadata\) |
| Context length | 32,768 positions \(config max\_position\_embeddings; implementation limit, not an independently verified context window\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 13\.50 GiB estimated tensor payload \(14,496,047,104 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | Derived from mistralai/Mistral\-7B\-v0\.2; vocabulary extended to 32,768 entries\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Public Hugging Face repository with declared weight files |
| Downloads | 351,307 at frozen Hugging Face metadata snapshot |
| Likes | 592 at frozen Hugging Face metadata snapshot |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/mistralai/Mistral\-7B\-v0\.3/blob/caa1feb0e54d415e2df31207e5f4e273e33509b1/README\.md](<https://huggingface.co/mistralai/Mistral-7B-v0.3/blob/caa1feb0e54d415e2df31207e5f4e273e33509b1/README.md>) |
| Code repository | [https://github\.com/mistralai/mistral\-inference](<https://github.com/mistralai/mistral-inference>) |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
