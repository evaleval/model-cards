# Model Card: MaziyarPanahi/calme\-2\.1\-qwen2\-72b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [calme\-2\.1\-qwen2\-72b\.json](<./calme-2.1-qwen2-72b.json>)<br>
SHA-256: `85dd126636500d4fcab4759feaa5a508cf7038357c41a2497b92ed540b4c7b51`

## Identity

| Field | Value |
| --- | --- |
| Model ID | MaziyarPanahi/calme\-2\.1\-qwen2\-72b |
| Name | MaziyarPanahi/calme\-2\.1\-qwen2\-72b |
| Developed by | MaziyarPanahi \(Hub organization\) |
| Model type | text\-generation |
| License | other |
| Release date | 2024\-06\-08 \(Hugging Face repository creation date\) |
| Version | 6607ff9f9a5fa1878322e6b5a442783451bf92fb |
| Summary | A fine\-tuned version of Qwen/Qwen2\-72B\-Instruct, aimed at advancing natural language understanding and generation\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-72B\-Instruct (base model; Kind: finetune) |
| Model family | calme 2\.1 qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 72,699,355,136 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 135\.4 GiB of safetensors weights \(145,398,821,808 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a fine\-tune of Qwen/Qwen2\-72B\-Instruct; the base model&\#x27;s pretraining data is not specified for this fine\-tune\. |
| Adaptations | The model is a fine\-tuned version of Qwen/Qwen2\-72B\-Instruct\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 42 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 28 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/MaziyarPanahi/calme\-2\.1\-qwen2\-72b](<https://huggingface.co/MaziyarPanahi/calme-2.1-qwen2-72b>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides no evaluation results, training\-data details, or post\-training specifics for this checkpoint, so its design/development/evaluation process is insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card states the checkpoint is a fine\-tune of Qwen/Qwen2\-72B\-Instruct but does not document the fine\-tuning dataset, collection, curation, or synthetic generation\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card only says primary task is text\-generation and gives no intended\-use or deployment context, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
