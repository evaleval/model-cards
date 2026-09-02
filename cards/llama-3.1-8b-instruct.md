# Model Card: Llama\-3\.1\-8B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-8b\-instruct\.json](<./llama-3.1-8b-instruct.json>)<br>
SHA-256: `4cdfe9f5f004f5ce86d1d3e6f685f43a337014aa1e286fcb078f766527927c45`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.1\-8B\-Instruct |
| Name | Llama\-3\.1\-8B\-Instruct |
| Developed by | Meta |
| Model type | text\-generation |
| License | A custom commercial license, the Llama 3\.1 Community License, is available at: https://github\.com/meta\-llama/llama\-models/blob/main/models/llama3\_1/LICENSE |
| Release date | July 23, 2024 |
| Version | 0e9e39f249a16976918f6564b8830bc894c89659 |
| Summary | The publisher describes Llama\-3\.1\-8B\-Instruct as an instruction\-tuned, multilingual model with text input and output\. |

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
| Input / output | input: Multilingual Text<br>output: Multilingual Text and code<br>supported languages: English, German, French, Italian, Portuguese, Hindi, Spanish, and Thai<br>model stage: instruction\-tuned |

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
| Results summary | The frozen README provides 17 exact\-target benchmark scores; examples: MMLU: 69\.4; MMLU \(CoT\): 73\.0; MMLU\-Pro \(CoT\): 48\.3\. |
| Safety evaluations | The publisher reports family/system\-level adversarial safety evaluation and recurring red teaming covering CBRNE, child\-safety, and cyber risks; this section does not state a checkpoint\-specific numeric safety score\. |

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
| API\-Bank | acc | 82\.6 | 0 shots | Not reported |
| BFCL | acc | 76\.1 | 0 shots | Not reported |
| Gorilla Benchmark API Bench | acc | 8\.2 | 0 shots | Not reported |
| Nexus | macro\_avg/acc | 38\.5 | 0 shots | Not reported |
| Multilingual MGSM \(CoT\) | em | 68\.9 | 0 shots | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.1\-8B\-Instruct/blob/0e9e39f249a16976918f6564b8830bc894c89659/README\.md](<https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/blob/0e9e39f249a16976918f6564b8830bc894c89659/README.md>) |
| Code repository | [https://github\.com/meta\-llama/llama](<https://github.com/meta-llama/llama>) |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
