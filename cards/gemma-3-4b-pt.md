# Model Card: gemma\-3\-4b\-pt

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-4b\-pt\.json](<./gemma-3-4b-pt.json>)<br>
SHA-256: `7b770f5dc2edf7704ba19eada9785cca61515cd2c6681a97b66d57cf53ac0fed`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-4b\-pt |
| Name | gemma\-3\-4b\-pt |
| Developed by | google |
| Model type | image\-text\-to\-text |
| License | gemma |
| Version | cc012e0a6d0787b4adcc0fa2c4da74402494554d |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | multimodal \(topology unspecified\) |
| Num parameters | 4,300,079,472 total stored parameters \(safetensors metadata\) |
| Context length | 128K tokens \(README\-declared context length\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 8\.01 GiB estimated tensor payload \(8,600,158,944 bytes; from safetensors dtype counts\) |
| Input / output | input: image and text<br>output: text<br>model stage: pretrained/base |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Publisher\-listed source categories: web documents, code, mathematics, images\. Language coverage is reported above 140 languages\. |
| Training data size | 4B model: 4 trillion tokens |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Gated Hugging Face repository with declared weight files |
| Downloads | 74,127 at frozen Hugging Face metadata snapshot |
| Likes | 160 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README provides 12 exact\-target benchmark scores in this capped publication set; examples: HellaSwag: 77\.2; BoolQ: 72\.3; PIQA: 79\.6\. |
| Safety evaluations | The publisher reports improvement over prior Gemma releases for child safety, content safety, representational harms, and ungrounded inference\. Testing omitted safety filters; the stated limitation is English\-only prompts\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HellaSwag | README\-reported score | 77\.2 | 10\-shot | Not reported |
| BoolQ | README\-reported score | 72\.3 | 0\-shot | Not reported |
| PIQA | README\-reported score | 79\.6 | 0\-shot | Not reported |
| SocialIQA | README\-reported score | 51\.9 | 0\-shot | Not reported |
| TriviaQA | README\-reported score | 65\.8 | 5\-shot | Not reported |
| Natural Questions | README\-reported score | 20\.0 | 5\-shot | Not reported |
| ARC\-c | README\-reported score | 56\.2 | 25\-shot | Not reported |
| ARC\-e | README\-reported score | 82\.4 | 0\-shot | Not reported |
| WinoGrande | README\-reported score | 64\.7 | 5\-shot | Not reported |
| BIG\-Bench Hard | README\-reported score | 50\.9 | few\-shot | Not reported |
| DROP | README\-reported score | 60\.1 | 1\-shot | Not reported |
| MMLU | README\-reported score | 59\.6 | 5\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-4b\-pt/blob/cc012e0a6d0787b4adcc0fa2c4da74402494554d/README\.md](<https://huggingface.co/google/gemma-3-4b-pt/blob/cc012e0a6d0787b4adcc0fa2c4da74402494554d/README.md>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
