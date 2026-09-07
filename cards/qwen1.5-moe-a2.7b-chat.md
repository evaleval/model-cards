# Model Card: Qwen1\.5\-MoE\-A2\.7B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-moe\-a2\.7b\-chat\.json](<./qwen1.5-moe-a2.7b-chat.json>)<br>
SHA-256: `b5bfbb66d6c75fe0964bb7e63a41f84dba6110e6ff8a8b59d5c9959e4464a820`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-MoE\-A2\.7B\-Chat |
| Name | Qwen1\.5\-MoE\-A2\.7B\-Chat |
| Developed by | Qwen \(Hub organization\) |
| License | other |
| Release date | 2024\-03\-14 \(Hugging Face repository creation date\) |
| Version | ec052fda178e241c7c443468d2fa1db6618996be |
| Summary | Qwen1\.5\-MoE\-A2\.7B is a small mixture\-of\-experts model that activates only 2\.7 billion parameters while matching the performance of state\-of\-the\-art 7B models such as Mistral 7B and Qwen1\.5\-7B\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 MoE A2\.7B |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 14,315,784,192 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 26\.7 GiB of safetensors weights \(28,632,144,944 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The target checkpoint was pretrained on a large amount of data, as stated in the model card\. |
| Adaptations | The model was post\-trained with supervised finetuning and direct preference optimization\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 43,177 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 133 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Human evaluations | For the chat model, the developer reports testing with MT\-Bench instead of traditional benchmarks\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-MoE\-A2\.7B\-Chat](<https://huggingface.co/Qwen/Qwen1.5-MoE-A2.7B-Chat>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only MT\-Bench for the chat model and no details of design/evaluation for this checkpoint, so inner workings and evaluation process are insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card says only &\#x27;pretrained on a large amount of data&\#x27; with no dataset details for this checkpoint, so training/tuning data documentation is insufficient\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Open\-weight checkpoint with &\#x27;other&\#x27; license and no data source/ownership details makes traceability of training data usage terms uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card gives no intended\-use or misuse statement for this chat checkpoint, so relevant risks cannot be defined as use changes\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
