# Model Card: MaziyarPanahi/calme\-2\.2\-qwen2\-72b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [calme\-2\.2\-qwen2\-72b\.json](<./calme-2.2-qwen2-72b.json>)<br>
SHA-256: `72da8f38b4c9479f9be76fb7ef2679b8dbe88bd1d69b58b2e02b968549c458d9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | MaziyarPanahi/calme\-2\.2\-qwen2\-72b |
| Name | MaziyarPanahi/calme\-2\.2\-qwen2\-72b |
| Developed by | MaziyarPanahi \(Hub organization\) |
| Model type | Text generation model\. |
| License | other |
| Release date | 2024\-07\-09 \(Hugging Face repository creation date\) |
| Version | fe3e03d0f1fae3781cf64f63b3a87f1738390e98 |
| Summary | A fine\-tuned version of Qwen/Qwen2\-72B\-Instruct, aimed at advancing natural language understanding and generation\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-72B (base model; Kind: finetune) |
| Model family | calme 2\.2 qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 72,706,203,648 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 135\.4 GiB of safetensors weights \(145,412,518,832 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on the MaziyarPanahi/truthy\-dpo\-v0\.1\-axolotl dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 43 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 5 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The model is a fine\-tuned version of Qwen/Qwen2\-72B\-Instruct, intended to improve natural language understanding and generation\. The developer aimed for a versatile model that performs well across many benchmarks and real\-world applications\. Its post\-training process follows the same approach as calme\-2\.1\-qwen2\-72b, with different parameters and a longer training period\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/MaziyarPanahi/calme\-2\.2\-qwen2\-72b](<https://huggingface.co/MaziyarPanahi/calme-2.2-qwen2-72b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports no training/evaluation details beyond naming the fine\-tuning dataset and following a prior recipe, so inner workings and evaluation process are undocumented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card names only the fine\-tuning dataset \(truthy\-dpo\-v0\.1\-axolotl\) and gives no collection, curation, or composition details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card does not describe the origin, ownership, or transformations of the truthy\-dpo\-v0\.1\-axolotl data, so provenance is not established\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card says the model is versatile and aimed at many real\-world applications but does not define intended use or misuse boundaries\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
