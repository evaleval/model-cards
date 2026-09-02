# Model Card: Llama\-3\.1\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-8b\.json](<./llama-3.1-8b.json>)<br>
SHA-256: `0ba7baa8351a41b05985aa6acf73db2e7967394bf8b7c2a4355fc9a0d29508e5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.1\-8B |
| Name | Llama\-3\.1\-8B |
| Developed by | meta\-llama |
| Model type | text\-generation |
| License | llama3\.1 |
| Release date | July 23, 2024 |
| Version | d04e592bb4f6aa9cfee91e2e20afa771667e1d4b |

## Lineage

| Field | Value |
| --- | --- |
| Model family | llama |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 total stored parameters \(safetensors metadata\) |
| Context length | 128K tokens \(README\-declared context length\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 14\.96 GiB estimated tensor payload \(16,060,522,496 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Pretraining scale: ~15 trillion tokens from publisher\-described public\-source data\. |
| Training data size | ~15 trillion tokens |
| Data cutoff | The pretraining data has a cutoff of December 2023 |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Gated Hugging Face repository with declared weight files |
| Downloads | 572,431 at frozen Hugging Face metadata snapshot |
| Likes | 2,402 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README provides 12 exact\-target benchmark scores in this capped publication set; examples: MMLU: 66\.7; MMLU\-Pro \(CoT\): 37\.1; AGIEval English: 47\.8\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | macro\_avg/acc\_char | 66\.7 | 5 shots | Not reported |
| MMLU\-Pro \(CoT\) | macro\_avg/acc\_char | 37\.1 | 5 shots | Not reported |
| AGIEval English | average/acc\_char | 47\.8 | 3\-5 shots | Not reported |
| CommonSenseQA | acc\_char | 75\.0 | 7 shots | Not reported |
| Winogrande | acc\_char | 60\.5 | 5 shots | Not reported |
| BIG\-Bench Hard \(CoT\) | average/em | 64\.2 | 3 shots | Not reported |
| ARC\-Challenge | acc\_char | 79\.7 | 25 shots | Not reported |
| TriviaQA\-Wiki | em | 77\.6 | 5 shots | Not reported |
| SQuAD | em | 77\.0 | 1 shots | Not reported |
| QuAC \(F1\) | f1 | 44\.9 | 1 shots | Not reported |
| BoolQ | acc\_char | 75\.0 | 0 shots | Not reported |
| DROP \(F1\) | f1 | 59\.5 | 3 shots | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.1\-8B/blob/d04e592bb4f6aa9cfee91e2e20afa771667e1d4b/README\.md](<https://huggingface.co/meta-llama/Llama-3.1-8B/blob/d04e592bb4f6aa9cfee91e2e20afa771667e1d4b/README.md>) |
| Code repository | [https://github\.com/meta\-llama/llama](<https://github.com/meta-llama/llama>) |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
