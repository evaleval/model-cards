# Model Card: Qwen2\.5\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-7b\-instruct\.json](<./qwen2.5-7b-instruct.json>)<br>
SHA-256: `2eb456470e67f6ff8f61ba09f73a5c3be071ca235a0ea8b8d834867839728b49`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-7B\-Instruct |
| Name | Qwen2\.5\-7B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| Model type | Causal language model |
| License | apache\-2\.0 |
| Release date | 2024\-09\-16 \(Hugging Face repository creation date\) |
| Version | a09a35458c702b33eeacc393d103063234e8bc28 |
| Summary | An instruction\-tuned 7B causal language model in the Qwen2\.5 series, released by Qwen and usable through Hugging Face Transformers, vLLM, and compatible tool\-calling interfaces\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B (base model; Kind: finetune) |
| Model family | Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,888 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The checkpoint underwent both pretraining and post\-training stages\. |
| Adaptations | The model&\#x27;s training included both pretraining and post\-training stages\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 11,049,595 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1,584 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-7B\-Instruct](<https://huggingface.co/Qwen/Qwen2.5-7B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5](<https://github.com/QwenLM/Qwen2.5>) |
| Citation | @misc\{qwen2\.5,<br>    title = \{Qwen2\.5: A Party of Foundation Models\},<br>    url = \{https://qwenlm\.github\.io/blog/qwen2\.5/\},<br>    author = \{Qwen Team\},<br>    month = \{September\},<br>    year = \{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, training stages, and access; no evaluation results, training\-data details, or safety testing are documented for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card states the model underwent pretraining and post\-training but gives no dataset composition, curation, or synthetic\-data details for this checkpoint\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information is provided about how training data were collected, curated, or used, making model behavior harder to explain\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card lists only &\#x27;causal language model&\#x27; as the task and gives no intended\-use or deployment context, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
