# Model Card: L\-MChat\-7b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [l\-mchat\-7b\.json](<./l-mchat-7b.json>)<br>
SHA-256: `c581f933a3d88e5989f0f984506113c3976f130f24d73f3d0a85f9d8eb634216`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Artples/L\-MChat\-7b |
| Name | L\-MChat\-7b |
| Developed by | Artples \(Hub organization\) |
| Model type | Text generation |
| License | apache\-2\.0 |
| Release date | 2024\-04\-02 \(Hugging Face repository creation date\) |
| Version | b034f6dcbd8094c04f730071ea4a75e5c9ea19ac |
| Summary | L\-MChat\-7b is a merge of the following models: |

## Lineage

| Field | Value |
| --- | --- |
| Base models | FuseAI/FuseChat\-7B\-VaRM (base model; Kind: merge)<br>Nexusflow/Starling\-LM\-7B\-beta (base model; Kind: merge) |
| Model family | L MChat |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,748,480 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,530,808 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a merge of Nexusflow/Starling\-LM\-7B\-beta layers 0\-32 and FuseAI/FuseChat\-7B\-VaRM layers 0\-32, using slerp with FuseAI/FuseChat\-7B\-VaRM as the base model\. |
| Adaptations | The model is produced by a slerp merge of two 7B models: Nexusflow/Starling\-LM\-7B\-beta and FuseAI/FuseChat\-7B\-VaRM, with FuseAI/FuseChat\-7B\-VaRM as the base model\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 8,514 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Artples/L\-MChat\-7b](<https://huggingface.co/Artples/L-MChat-7b>) |
| Citation | The model card states the model is licensed under Apache 2\.0 but cannot be used to directly compete with OpenAI\. |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only reports that the model is a slerp merge of two 7B models and gives no evaluation results, training data details, or intended\-use documentation\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe how the underlying training data for either merged model was collected, curated, or used, so training\-data transparency is lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only &\#x27;Primary task: Text generation&\#x27; and does not define intended or prohibited uses, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
