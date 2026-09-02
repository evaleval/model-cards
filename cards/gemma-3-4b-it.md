# Model Card: gemma\-3\-4b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-4b\-it\.json](<./gemma-3-4b-it.json>)<br>
SHA-256: `d8b795479ec12990a532195e190e55c62fee70f2d5029e9f7f749208ae7bbece`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-4b\-it |
| Name | gemma\-3\-4b\-it |
| Developed by | Google DeepMind |
| Model type | image\-text\-to\-text |
| License | gemma |
| Version | 093f9f388b31de276ce2de164bdc2081324b9767 |
| Summary | The publisher describes gemma\-3\-4b\-it as a multimodal, open\-weight model with text\-and\-image input and text output\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-3\-4b\-pt (base model) |
| Model family | gemma3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | multimodal \(topology unspecified\) |
| Num parameters | 4,300,079,472 total stored parameters \(safetensors metadata\) |
| Context length | 128K tokens \(README\-declared context length\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 8\.01 GiB estimated tensor payload \(8,600,158,944 bytes; from safetensors dtype counts\) |
| Input / output | input: image and text<br>output: text<br>model stage: instruction\-tuned |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Publisher\-described family/base pretraining context: Publisher\-listed source categories: web documents, code, mathematics, images\. Language coverage is reported above 140 languages\. |
| Training data size | Publisher\-described family/base pretraining scale: 4B model: 4 trillion tokens |
| Adaptations | Instruction\-tuned variant \(the frozen README does not specify the tuning recipe\)\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Gated Hugging Face repository with declared weight files |
| Downloads | 1,526,070 at frozen Hugging Face metadata snapshot |
| Likes | 1,467 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README reports family\-level qualitative safety\-evaluation results; see safety\_evals\. |
| Safety evaluations | The README reports Gemma\-family, all\-model\-size improvements over earlier releases for child safety, content safety, representational harms, and ungrounded inference\. The tests omitted safety filters and used English prompts; the source does not provide PT/IT\- or checkpoint\-specific results\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-4b\-it/blob/093f9f388b31de276ce2de164bdc2081324b9767/README\.md](<https://huggingface.co/google/gemma-3-4b-it/blob/093f9f388b31de276ce2de164bdc2081324b9767/README.md>) |
| Technical report | [https://goo\.gle/Gemma3Report](<https://goo.gle/Gemma3Report>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.derivatives`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.code_repository`.
