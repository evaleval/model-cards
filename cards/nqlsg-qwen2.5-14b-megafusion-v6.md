# Model Card: NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v6

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [nqlsg\-qwen2\.5\-14b\-megafusion\-v6\.json](<./nqlsg-qwen2.5-14b-megafusion-v6.json>)<br>
SHA-256: `260775596bf379e3eef35592f5209b1e0ab198e6901f8a15c4a54f8bffa1d204`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v6 |
| Name | NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v6 |
| Developed by | Lunzima \(Hub organization\) |
| Model type | Text generation model |
| Release date | 2025\-02\-24 \(Hugging Face repository creation date\) |
| Version | 37c6300e2ad9a03042b28c70033bca0f7358ec41 |
| Summary | A merge of pre\-trained language models created with mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v3 (base model; Kind: merge)<br>Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v3\-alpaca\_gpt4\_zh (base model; Kind: merge)<br>Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v4 (base model; Kind: merge)<br>Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v4\-reasoning (base model; Kind: merge)<br>Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v5 (base model; Kind: merge)<br>Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v5\-reasoning (base model; Kind: merge)<br>Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v5\-roleplay (base model; Kind: merge) |
| Model family | NQLSG Qwen2\.5 MegaFusion v6 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,765,947,904 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,531,962,384 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This model is a merge of pre\-trained language models created using mergekit; the merge included the models listed in the readme\. |
| Adaptations | This model was merged using the SCE merge method with NQLSG\-Qwen2\.5\-14B\-Base2 as the base, and was created using mergekit\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 17 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Lunzima/NQLSG\-Qwen2\.5\-14B\-MegaFusion\-v6](<https://huggingface.co/Lunzima/NQLSG-Qwen2.5-14B-MegaFusion-v6>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Spreading disinformation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/spreading-disinformation.html>) | open\-weight text\-generation model merged from pre\-trained models with no reported safety evaluation or alignment \-&gt; could be used to generate misleading content at scale | Generative AI models might be used to intentionally create misleading or false information to deceive or influence a targeted audience\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
