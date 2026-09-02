# Model Card: Qwen3\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen3\-8b\.json](<./qwen3-8b.json>)<br>
SHA-256: `bf767a04a1a678c228d18c14bad9e3d6abffe1ecaa40b1e87a3e204ad52f1f76`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen3\-8B |
| Name | Qwen3\-8B |
| Developed by | Qwen |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Version | b968826d9c46dd6066d109eabc6255188de91218 |
| Summary | Qwen3\-8B is listed with 8\.2B parameters and a 32,768 natively and 131,072 tokens with YaRN context window; model class Causal Language Models; repository stage Pretraining &amp; Post\-training\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen3\-8B\-Base (base model) |
| Model family | qwen3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,190,735,360 total stored parameters \(safetensors metadata\) |
| Context length | 32,768 tokens natively; 131,072 tokens with YaRN \(README\-declared context length\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 15\.26 GiB estimated tensor payload \(16,381,470,720 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | Pretraining &amp; Post\-training |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Public Hugging Face repository with declared weight files |
| Downloads | 13,632,574 at frozen Hugging Face metadata snapshot |
| Likes | 1,334 at frozen Hugging Face metadata snapshot |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen3\-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/README\.md](<https://huggingface.co/Qwen/Qwen3-8B/blob/b968826d9c46dd6066d109eabc6255188de91218/README.md>) |
| Technical report | [https://arxiv\.org/abs/2505\.09388](<https://arxiv.org/abs/2505.09388>) |
| Code repository | [https://github\.com/QwenLM/Qwen3](<https://github.com/QwenLM/Qwen3>) |
| Citation | @misc\{qwen3technicalreport,<br>      title=\{Qwen3 Technical Report\}, <br>      author=\{Qwen Team\},<br>      year=\{2025\},<br>      eprint=\{2505\.09388\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2505\.09388\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
