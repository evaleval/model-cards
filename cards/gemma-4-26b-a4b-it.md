# Model Card: gemma\-4\-26b\-a4b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-4\-26b\-a4b\-it\.json](<./gemma-4-26b-a4b-it.json>)<br>
SHA-256: `41f5dac8f599cda0e4ec1740ceece85170d6da957f60450e08a23f4de64cb6a6`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-4\-26b\-a4b\-it |
| Name | gemma\-4\-26b\-a4b\-it |
| Developed by | google \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2026\-03\-11 \(Hugging Face repository creation date\) |
| Version | 4d7ae4984b7db7de8f8457170b3f1a419ee76d52 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-4\-26B\-A4B (base model; Kind: finetune) |
| Model family | gemma 4 a4b |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 25,805,936,206 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 48\.1 GiB of safetensors weights \(51,612,009,916 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The release includes both pre\-trained and instruction\-tuned open\-weight variants\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 8,307,671 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1,481 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Human evaluations | The developer reports that the 26B model ranks sixth on the Arena AI text leaderboard\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU Pro | Not specified | 82\.6% | Not specified | Not reported |
| AIME 2026 no tools | Not specified | 88\.3% | Not specified | Not reported |
| LiveCodeBench v6 | Not specified | 77\.1% | Not specified | Not reported |
| Codeforces ELO | Elo | 1718 | Not specified | Not reported |
| GPQA Diamond | Not specified | 82\.3% | Not specified | Not reported |
| Tau2 | Not specified | 68\.2% | Not specified | Not reported |
| HLE no tools | Not specified | 8\.7% | Not specified | Not reported |
| HLE with search | Not specified | 17\.2% | Not specified | Not reported |
| BigBench Extra Hard | Not specified | 64\.8% | Not specified | Not reported |
| MMMLU | Not specified | 86\.3% | Not specified | Not reported |
| MMMU Pro | Not specified | 73\.8% | Not specified | Not reported |
| OmniDocBench 1\.5 | Not specified | 0\.149 | Not specified | Not reported |
| MATH\-Vision | Not specified | 82\.4% | Not specified | Not reported |
| MedXPertQA MM | Not specified | 58\.1% | Not specified | Not reported |
| MRCR v2 8 needle 128k | Not specified | 44\.1% | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-4\-26b\-a4b\-it](<https://huggingface.co/google/gemma-4-26b-a4b-it>) |
| Code repository | [https://github\.com/bebechien/gemma](<https://github.com/bebechien/gemma>) |
| Citation | @misc\{gemmateam2026gemma4,<br>      title=\{Gemma 4 Technical Report\}, <br>      author=\{Gemma Team\},<br>      year=\{2026\},<br>      eprint=\{2607\.02770\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2607\.02770\}, <br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `risks.possible_risks`.
