# Model Card: Qwen3\-8B\-Base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen3\-8b\-base\.json](<./qwen3-8b-base.json>)<br>
SHA-256: `3c019128a6b8a619db5975fe9ba2a6d24573b0744d04131e8003d4abebae47b6`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen3\-8B\-Base |
| Name | Qwen3\-8B\-Base |
| Developed by | Qwen |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Version | 49e3418fbbbca6ecbdf9608b4d22e5a407081db4 |
| Summary | Qwen3\-8B\-Base is listed with 8\.2B parameters and a 32,768 context window; model class Causal Language Models; repository stage Pretraining\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | qwen3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,190,735,360 total stored parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(README\-declared context length\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 15\.26 GiB estimated tensor payload \(16,381,470,720 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text<br>model stage: pretrained/base |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Pretraining scale: 36 trillion tokens; language coverage: 119; content areas include code, STEM, reasoning, books, multilingual, and synthetic material\. |
| Training data size | 36 trillion tokens |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Public Hugging Face repository with declared weight files |
| Downloads | 431,067 at frozen Hugging Face metadata snapshot |
| Likes | 118 at frozen Hugging Face metadata snapshot |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen3\-8B\-Base/blob/49e3418fbbbca6ecbdf9608b4d22e5a407081db4/README\.md](<https://huggingface.co/Qwen/Qwen3-8B-Base/blob/49e3418fbbbca6ecbdf9608b4d22e5a407081db4/README.md>) |
| Technical report | [https://arxiv\.org/abs/2505\.09388](<https://arxiv.org/abs/2505.09388>) |
| Code repository | [https://github\.com/QwenLM/Qwen3](<https://github.com/QwenLM/Qwen3>) |
| Citation | @misc\{qwen3technicalreport,<br>      title=\{Qwen3 Technical Report\}, <br>      author=\{Qwen Team\},<br>      year=\{2025\},<br>      eprint=\{2505\.09388\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2505\.09388\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
