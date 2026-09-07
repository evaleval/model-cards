# Model Card: ✨ Falcon\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [falcon\-7b\-instruct\.json](<./falcon-7b-instruct.json>)<br>
SHA-256: `d58f0d9c9d13e3cb75764ab8d6710c01782aa624bd5f876436fbd8c9b83adc48`

## Identity

| Field | Value |
| --- | --- |
| Model ID | tiiuae/falcon\-7b\-instruct |
| Name | ✨ Falcon\-7B\-Instruct |
| Developed by | tiiuae \(Hub organization\) |
| Model type | Causal decoder\-only language model\. |
| License | apache\-2\.0 |
| Release date | 2023\-04\-25 \(Hugging Face repository creation date\) |
| Version | 8782b5c5d8c9290412416618f36a133653e85285 |
| Summary | Falcon\-7B\-Instruct is a 7\-billion\-parameter causal decoder\-only model developed by TII, initialized from Falcon\-7B and fine\-tuned on a blend of chat and instruction datasets\. |

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
| Training data | Falcon\-7B\-Instruct was fine\-tuned from Falcon\-7B on a mixture of chat and instruct datasets\. |
| Adaptations | Falcon\-7B\-Instruct is a fine\-tuned version of Falcon\-7B, adapted on a mixture of instruct and chat datasets\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 31,696 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1,032 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The developer notes that Falcon\-7B\-Instruct was trained mostly on English data and therefore may not generalize appropriately to other languages, and that because it was trained on large\-scale web corpora it may carry stereotypes and biases commonly encountered online\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/tiiuae/falcon\-7b\-instruct](<https://huggingface.co/tiiuae/falcon-7b-instruct>) |
| Citation | @article\{falcon40b,<br>  title=\{\{Falcon\-40B\}: an open large language model with state\-of\-the\-art performance\},<br>  author=\{Almazrouei, Ebtesam and Alobeidli, Hamza and Alshamsi, Abdulaziz and Cappelli, Alessandro and Cojocaru, Ruxandra and Debbah, Merouane and Goffinet, Etienne and Heslow, Daniel and Launay, Julien and Malartic, Quentin and Noune, Badreddine and Pannier, Baptiste and Penedo, Guilherme\},<br>  year=\{2023\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only high\-level training data description \(fine\-tuned on a mixture of chat and instruct datasets\) and no detailed documentation of data composition, filtering, or evaluation process\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Card states model was trained mostly on English data and therefore may not generalize appropriately to other languages, indicating training data not representative of all potential users/languages\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Decision bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/decision-bias.html>) | Card states large\-scale web corpora may carry stereotypes and biases commonly encountered online, which can unfairly advantage/disadvantage groups in model decisions\. | Decision bias occurs when one group is unfairly advantaged over another due to decisions of the model\. This might be caused by biases in the data and also amplified as a result of the model&\#x27;s training\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card does not provide traceable provenance for the chat/instruct mixture used in fine\-tuning, only a vague description of the blend\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
