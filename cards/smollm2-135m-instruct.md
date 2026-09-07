# Model Card: SmolLM2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\-135m\-instruct\.json](<./smollm2-135m-instruct.json>)<br>
SHA-256: `8b4a31e175dea884e32f1723c6244fd31c09bc04b6bc90a5c81a245c4805ed0d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM2\-135M\-Instruct |
| Name | SmolLM2 |
| Developed by | HuggingFaceTB \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2024\-10\-31 \(Hugging Face repository creation date\) |
| Version | 12fd25f77366fa6b3b4b768ec3050bf629380bac |
| Summary | SmolLM2 is a family of compact language models available in three sizes: 135M, 360M, and 1\.7B parameters\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | HuggingFaceTB/SmolLM2\-135M (base model; Kind: quantized) |
| Model family | SmolLM2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 134,515,008 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 0\.3 GiB of safetensors weights \(269,060,552 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The instruct version was developed through supervised fine\-tuning \(SFT\) using public datasets and curated datasets, followed by Direct Preference Optimization \(DPO\) on UltraFeedback\. |
| Adaptations | The instruct version was developed through supervised fine\-tuning \(SFT\) using public datasets and curated datasets, followed by Direct Preference Optimization \(DPO\) on UltraFeedback\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,350,354 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 413 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MT\-Bench | Not specified | 19\.8 | Not specified | Not reported |
| HellaSwag | Not specified | 40\.9 | Not specified | Not reported |
| ARC | Not specified | 37\.3 | Not specified | Not reported |
| PIQA | Not specified | 66\.3 | Not specified | Not reported |
| MMLU | Not specified | 29\.3 | Not specified | Not reported |
| BBH | Not specified | 28\.2 | 3\-shot | Not reported |
| GSM8K | Not specified | 1\.4 | 5\-shot | Not reported |
| MTB | Not specified | 6\.11 | Not specified | Not reported |
| GSM8K | Not specified | 47\.54 | Not specified | Not reported |
| MATH | Not specified | 19\.64 | Not specified | Not reported |
| ARC\-C | Not specified | 42\.49 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 19\.06 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM2\-135M\-Instruct](<https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2502\.02737](<https://arxiv.org/abs/2502.02737>) |
| Code repository | [https://hf\.co/collections/HuggingFaceTB/smollm2\-6723884218bcda64b34d7db9](<https://hf.co/collections/HuggingFaceTB/smollm2-6723884218bcda64b34d7db9>) |
| Citation | @misc\{allal2025smollm2smolgoesbig,<br>      title=\{SmolLM2: When Smol Goes Big \-\- Data\-Centric Training of a Small Language Model\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Gabriel Martín Blázquez and Guilherme Penedo and Lewis Tunstall and Andrés Marafioti and Hynek Kydlíček and Agustín Piqueres Lajarín and Vaibhav Srivastav and Joshua Lochner and Caleb Fahlgren and Xuan\-Son Nguyen and Clémentine Fourrier and Ben Burtenshaw and Hugo Larcher and Haojun Zhao and Cyril Zakka and Mathieu Morlon and Colin Raffel and Leandro von Werra and Thomas Wolf\},<br>      year=\{2025\},<br>      eprint=\{2502\.02737\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2502\.02737\}, <br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `risks.possible_risks`.
