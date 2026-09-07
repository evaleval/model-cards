# Model Card: slu\-14

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [slu\-14\.json](<./slu-14.json>)<br>
SHA-256: `a2b1bb8510488d4f837d1901ebdbde418a5c38ded5fbc43a817ec53cc594a6b4`

## Identity

| Field | Value |
| --- | --- |
| Model ID | jaspionjader/slu\-14 |
| Name | slu\-14 |
| Developed by | jaspionjader \(Hub organization\) |
| Release date | 2025\-02\-01 \(Hugging Face repository creation date\) |
| Version | fe53372aaac2ae2ca734f795ef18abab135738a1 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | jaspionjader/slu\-10 (base model; Kind: merge)<br>jaspionjader/slu\-11 (base model; Kind: merge)<br>jaspionjader/slu\-12 (base model; Kind: merge)<br>jaspionjader/slu\-13 (base model; Kind: merge) |
| Model family | slu 14 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,336 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge created with the Model Stock merge method, using jaspionjader/slu\-13 as the base\. The merge included jaspionjader/slu\-12, jaspionjader/slu\-10, and jaspionjader/slu\-11\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 14 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/jaspionjader/slu\-14](<https://huggingface.co/jaspionjader/slu-14>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
