# Model Card: Qwen2\.5\-1\.5B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-1\.5b\-instruct\.json](<./qwen2.5-1.5b-instruct.json>)<br>
SHA-256: `d3c783942ed42d2ce664fba0a268dd528aba02af44385380da104f9b3b4d69e7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-1\.5B\-Instruct |
| Name | Qwen2\.5\-1\.5B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal language model\. |
| License | apache\-2\.0 |
| Release date | 2024\-09\-17 \(Hugging Face repository creation date\) |
| Version | 989aa7980e4cf806f80c7fef2b1adb7bc71aa306 |
| Summary | Instruction\-tuned 1\.5B model in the Qwen2\.5 series\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-1\.5B (base model; Kind: finetune) |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,543,714,304 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.9 GiB of safetensors weights \(3,087,467,144 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model card reports a training stage of pretraining and post\-training, indicating that the released checkpoint underwent both initial pretraining and subsequent post\-training\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 7,308,263 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 817 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-1\.5B\-Instruct](<https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `risks.possible_risks`.
