# Model Card: \*\*Bellatrix\-Tiny\-1B\-v2\*\*

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [bellatrix\-tiny\-1b\-v2\.json](<./bellatrix-tiny-1b-v2.json>)<br>
SHA-256: `2ad063d807dff4758a46a128e78e4c7ef1f3c8d121de4c4d0217f4e38d2451fd`

## Identity

| Field | Value |
| --- | --- |
| Model ID | prithivMLmods/Bellatrix\-Tiny\-1B\-v2 |
| Name | \*\*Bellatrix\-Tiny\-1B\-v2\*\* |
| Developed by | prithivMLmods \(Hub organization\) |
| License | llama3\.2 |
| Release date | 2025\-01\-26 \(Hugging Face repository creation date\) |
| Version | f36644bfbd11e57d93a62ad598ca745dcbfb9b5c |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Llama\-3\.2\-1B\-Instruct (base model; Kind: quantized) |
| Model family | Bellatrix Tiny v2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,235,814,400 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.3 GiB of safetensors weights \(2,471,645,608 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The tuned model was created with supervised fine\-tuning and reinforcement learning with human feedback\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 23 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that these models outperform many available open\-source options\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/prithivMLmods/Bellatrix\-Tiny\-1B\-v2](<https://huggingface.co/prithivMLmods/Bellatrix-Tiny-1B-v2>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only that the model outperforms many open\-source options and gives no evaluation details, design, or training\-data documentation for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe how training/fine\-tuning data was collected or curated for Bellatrix\-Tiny\-1B\-v2, only naming the base Llama\-3\.2\-1B\-Instruct\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only text\-to\-text modality and open weights, with no intended\-use or deployment\-context definition, so relevant risks are underspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
