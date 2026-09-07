# Model Card: 🚀 Falcon\-40B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [falcon\-40b\.json](<./falcon-40b.json>)<br>
SHA-256: `ced00916cb5d0f3a825f54992756ee4aa6a443396c2c960b2172237a95876b09`

## Identity

| Field | Value |
| --- | --- |
| Model ID | tiiuae/falcon\-40b |
| Name | 🚀 Falcon\-40B |
| Developed by | tiiuae \(Hub organization\) |
| Model type | A causal decoder\-only language model\. |
| License | apache\-2\.0 |
| Release date | 2023\-05\-24 \(Hugging Face repository creation date\) |
| Version | 05ab2ee8d6b593bdbab17d728de5c028a7a94d83 |
| Summary | A 40\-billion\-parameter causal decoder\-only language model trained by TII on 1,000 billion tokens of RefinedWeb data augmented with curated corpora\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | falcon |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 41,835,970,560 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 77\.9 GiB of safetensors weights \(83,671,996,368 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | 1,000B tokens |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 8,938 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2,439 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that Falcon\-40B is the best open\-source model currently available and that it outperforms LLaMA, StableLM, RedPajama, MPT, etc\., as reflected on the OpenLLM Leaderboard\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/tiiuae/falcon\-40b](<https://huggingface.co/tiiuae/falcon-40b>) |
| Citation | @article\{falcon40b,<br>  title=\{\{Falcon\-40B\}: an open large language model with state\-of\-the\-art performance\},<br>  author=\{Almazrouei, Ebtesam and Alobeidli, Hamza and Alshamsi, Abdulaziz and Cappelli, Alessandro and Cojocaru, Ruxandra and Debbah, Merouane and Goffinet, Etienne and Heslow, Daniel and Launay, Julien and Malartic, Quentin and Noune, Badreddine and Pannier, Baptiste and Penedo, Guilherme\},<br>  year=\{2023\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark claims and no details on training data composition, evaluation limitations, or inner workings for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data is described as RefinedWeb augmented with curated corpora, but the card does not document provenance or usage terms for those sources\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Training on 1,000B tokens of RefinedWeb plus curated corpora may not represent all real\-world text distributions, and no evaluation of demographic or domain coverage is reported\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Lack of testing diversity](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-testing-diversity.html>) | The card reports only OpenLLM Leaderboard results and does not mention testing across diverse disciplines or social/technical evaluation practices\. | AI model risks are socio\-technical, so their testing needs input from a broad set of disciplines and diverse testing practices\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `specifications.context_length`, `training_context.training_data`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
