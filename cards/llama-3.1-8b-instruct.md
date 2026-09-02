# Model Card: Llama\-3\.1\-8B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-8b\-instruct\.json](<./llama-3.1-8b-instruct.json>)<br>
SHA-256: `0b67e87020aec1cefa273ce08876306b3ded3eb08f90238eb60020ee601027e5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.1\-8B\-Instruct |
| Name | Llama\-3\.1\-8B\-Instruct |
| Developed by | meta\-llama |
| Model type | text\-generation |
| License | llama3\.1 |
| Release date | July 23, 2024 |
| Version | 0e9e39f249a16976918f6564b8830bc894c89659 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Meta\-Llama\-3\.1\-8B (base model) |
| Model family | llama |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 total stored parameters \(safetensors metadata\) |
| Context length | 128K tokens \(README\-declared context length\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 14\.96 GiB estimated tensor payload \(16,060,522,496 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text<br>model stage: instruction\-tuned |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Pretraining scale: ~15 trillion tokens from publisher\-described public\-source data\. Fine\-tuning sources include public instruction datasets and more than 25M synthetic examples\. |
| Training data size | ~15 trillion tokens; fine\-tuning includes over 25M synthetically generated examples |
| Data cutoff | The pretraining data has a cutoff of December 2023 |
| Adaptations | Instruction tuning combines SFT with RLHF for preference alignment, helpfulness, and safety\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Gated Hugging Face repository with declared weight files |
| Downloads | 5,945,153 at frozen Hugging Face metadata snapshot |
| Likes | 6,738 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README provides 12 exact\-target benchmark scores in this capped publication set; examples: MMLU: 69\.4; MMLU \(CoT\): 73\.0; MMLU\-Pro \(CoT\): 48\.3\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | macro\_avg/acc | 69\.4 | 5 shots | Not reported |
| MMLU \(CoT\) | macro\_avg/acc | 73\.0 | 0 shots | Not reported |
| MMLU\-Pro \(CoT\) | micro\_avg/acc\_char | 48\.3 | 5 shots | Not reported |
| IFEval | README\-reported score | 80\.4 | Benchmark scores; setting not stated | Not reported |
| ARC\-C | acc | 83\.4 | 0 shots | Not reported |
| GPQA | em | 30\.4 | 0 shots | Not reported |
| HumanEval | pass@1 | 72\.6 | 0 shots | Not reported |
| MBPP \+\+ base version | pass@1 | 72\.8 | 0 shots | Not reported |
| Multipl\-E HumanEval | pass@1 | 50\.8 | 0 shots | Not reported |
| Multipl\-E MBPP | pass@1 | 52\.4 | 0 shots | Not reported |
| GSM\-8K \(CoT\) | em\_maj1@1 | 84\.5 | 8 shots | Not reported |
| MATH \(CoT\) | final\_em | 51\.9 | 0 shots | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.1\-8B\-Instruct/blob/0e9e39f249a16976918f6564b8830bc894c89659/README\.md](<https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/blob/0e9e39f249a16976918f6564b8830bc894c89659/README.md>) |
| Code repository | [https://github\.com/meta\-llama/llama](<https://github.com/meta-llama/llama>) |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
