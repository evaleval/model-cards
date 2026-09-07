# Model Card: granite\-7b\-base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [granite\-7b\-base\.json](<./granite-7b-base.json>)<br>
SHA-256: `7e9eda3e173d91568fe06726e70946da74c2a613e2299bd07302c6342baa8f54`

## Identity

| Field | Value |
| --- | --- |
| Model ID | ibm\-granite/granite\-7b\-base |
| Name | granite\-7b\-base |
| Developed by | ibm\-granite \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-04\-19 \(Hugging Face repository creation date\) |
| Version | 3694001fa74a2aa9a6eff07774cbcb68b73e78f2 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | granite |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 6,738,415,616 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 25\.1 GiB of safetensors weights \(26,953,696,096 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,652 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 29 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports evaluation results for the model across a range of benchmarks, including MMLU, ARC, Boolq, Copa, HellaSwag, Openbookqa, Piqa, Sciq, Winogrande, Truthfulqa, and GSM8k\. Scores vary by task, with higher performance on Sciq and Copa and lower performance on GSM8k and Truthfulqa\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 0\.43 | zero shot | Not reported |
| MMLU | Not specified | 0\.50 | 5\-shot | Not reported |
| Arc challenge | Not specified | 0\.44 | Not specified | Not reported |
| Arc easy | Not specified | 0\.71 | Not specified | Not reported |
| Boolq | Not specified | 0\.76 | Not specified | Not reported |
| Copa | Not specified | 0\.83 | Not specified | Not reported |
| Hellaswag | Not specified | 0\.74 | Not specified | Not reported |
| Openbookqa | Not specified | 0\.42 | Not specified | Not reported |
| Piqa | Not specified | 0\.79 | Not specified | Not reported |
| Sciq | Not specified | 0\.91 | Not specified | Not reported |
| Winogrande | Not specified | 0\.67 | Not specified | Not reported |
| Truthfulqa | Not specified | 0\.39 | Not specified | Not reported |
| GSM8k | Not specified | 0\.11 | 8\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/ibm\-granite/granite\-7b\-base](<https://huggingface.co/ibm-granite/granite-7b-base>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only benchmark scores and architecture/access/license, with no documentation of design, development, training data, or evaluation process, so the checkpoint plausibly raises lack of model transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | The card summary does not provide access to training data, so explanations of model outputs are limited and more likely to be incorrect\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | The card summary does not disclose training data content, so the content used to generate outputs is not accessible/traceable\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card summary lacks information about how training data was collected, curated, or used, making model behavior harder to explain\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
