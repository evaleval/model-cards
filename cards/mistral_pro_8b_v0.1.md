# Model Card: Mistral\_Pro\_8B\_v0\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\_pro\_8b\_v0\.1\.json](<./mistral_pro_8b_v0.1.json>)<br>
SHA-256: `8b03b3a2650b05f4783a9d9ecdeeb033bdc9e499de758cd7a0932023a5d0bc2f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | TencentARC/Mistral\_Pro\_8B\_v0\.1 |
| Name | Mistral\_Pro\_8B\_v0\.1 |
| Developed by | TencentARC \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-02\-22 \(Hugging Face repository creation date\) |
| Version | 366f159fc5b314ba2a955209d2bca4600f84dac0 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Mistral Pro |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,986,628,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 16\.7 GiB of safetensors weights \(17,973,298,416 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 118 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 67 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that Mistral\_Pro\_8B\_v0\.1 shows strong results across several benchmarks\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/TencentARC/Mistral\_Pro\_8B\_v0\.1](<https://huggingface.co/TencentARC/Mistral_Pro_8B_v0.1>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark strength and architecture, with no documentation of design, development, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of testing diversity](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-testing-diversity.html>) | Reported results are only benchmark scores, with no indication of diverse socio\-technical testing or input from multiple disciplines\. | AI model risks are socio\-technical, so their testing needs input from a broad set of disciplines and diverse testing practices\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card gives no information about training data collection, curation, or use, making training\-data transparency lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only text\-to\-text modality and open\-weight access, with no intended\-use definition to scope relevant risks\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
