# Model Card: 🚀 Falcon\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [falcon\-7b\.json](<./falcon-7b.json>)<br>
SHA-256: `bb3db35c11871b0e1b019f958cf683f8cf25238149787c741ae5ab9ea8efbc93`

## Identity

| Field | Value |
| --- | --- |
| Model ID | tiiuae/falcon\-7b |
| Name | 🚀 Falcon\-7B |
| Developed by | tiiuae \(Hub organization\) |
| Model type | Causal decoder\-only language model\. |
| License | apache\-2\.0 |
| Release date | 2023\-04\-24 \(Hugging Face repository creation date\) |
| Version | ec89142b67d748a1865ea4451372db8313ada0d8 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | falcon |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,217,189,760 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.4 GiB of safetensors weights \(14,434,402,976 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | 1,500B tokens |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 418,072 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1,105 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model outperforms comparable open\-source models such as MPT\-7B, StableLM, and RedPajama, attributing this to training on 1,500B tokens of RefinedWeb enhanced with curated corpora\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/tiiuae/falcon\-7b](<https://huggingface.co/tiiuae/falcon-7b>) |
| Citation | @article\{falcon40b,<br>  title=\{\{Falcon\-40B\}: an open large language model with state\-of\-the\-art performance\},<br>  author=\{Almazrouei, Ebtesam and Alobeidli, Hamza and Alshamsi, Abdulaziz and Cappelli, Alessandro and Cojocaru, Ruxandra and Debbah, Merouane and Goffinet, Etienne and Heslow, Daniel and Launay, Julien and Malartic, Quentin and Noune, Badreddine and Pannier, Baptiste and Penedo, Guilherme\},<br>  year=\{2023\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only task/architecture/access and a broad comparison result, with no documentation of training data composition, evaluation methodology, or limitations\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training uses 1,500B tokens of RefinedWeb enhanced with curated corpora, but the card does not describe the provenance or usage terms of these corpora\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.context_length`, `training_context.training_data`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
