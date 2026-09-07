# Model Card: Pythia\-2\.8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [pythia\-2\.8b\.json](<./pythia-2.8b.json>)<br>
SHA-256: `ebee8c419832ec9b0629bc80b02738ff55369f06aed317ab29685052d81e32f7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | EleutherAI/pythia\-2\.8b |
| Name | Pythia\-2\.8B |
| Developed by | EleutherAI \(Hub organization\) |
| Model type | Transformer\-based Language Model |
| License | apache\-2\.0 |
| Release date | 2023\-02\-13 \(Hugging Face repository creation date\) |
| Version | 2a259cdd96a4beb1cdf467512e3904197345f6a9 |
| Summary | A transformer\-based language model from EleutherAI&\#x27;s Pythia Scaling Suite, a collection of models developed to facilitate interpretability research\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | pythia |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 2,909,427,008 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 5\.3 GiB of safetensors weights \(5,684,693,096 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Pythia\-2\.8B was trained on the Pile, a dataset that was not deduplicated before use\. |
| Adaptations | Pythia\-2\.8B has not been fine\-tuned for downstream contexts such as genre prose or commercial chatbots\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 42,344 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 35 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that, although downstream performance was not a design goal, the model matches or exceeds comparable models of similar size, including those in the OPT and GPT\-Neo suites\. |
| Human evaluations | The developer states that the model has not been fine\-tuned for common deployment contexts such as genre prose writing or commercial chatbots\. |
| Safety evaluations | The developer cautions that the model may produce socially unacceptable or undesirable text even when the prompt is not explicitly offensive\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/EleutherAI/pythia\-2\.8b](<https://huggingface.co/EleutherAI/pythia-2.8b>) |
| Code repository | [https://github\.com/EleutherAI/pythia](<https://github.com/EleutherAI/pythia>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `links.system_card`, `links.tech_report`, `links.citation`, `risks.possible_risks`.
