# Model Card: MN\-12B\-Lyra\-v3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mn\-12b\-lyra\-v3\.json](<./mn-12b-lyra-v3.json>)<br>
SHA-256: `fadf22d1618c918b3bd89ae1641077d2f3b1f8753c60f9600c738d6b98782254`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Sao10K/MN\-12B\-Lyra\-v3 |
| Name | MN\-12B\-Lyra\-v3 |
| Developed by | Sao10K \(Hub organization\) |
| License | cc\-by\-nc\-4\.0 |
| Release date | 2024\-08\-27 \(Hugging Face repository creation date\) |
| Version | c264a97097af92a1570dbe607820555ba65b355a |

## Lineage

| Field | Value |
| --- | --- |
| Model family | MN Lyra v3 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 12,247,782,400 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 22\.8 GiB of safetensors weights \(24,495,607,040 bytes\) in BF16 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 28 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 36 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Sao10K/MN\-12B\-Lyra\-v3](<https://huggingface.co/Sao10K/MN-12B-Lyra-v3>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card is minimal: only names the checkpoint, access, license, and family, with no design, development, or evaluation details\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of testing diversity](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-testing-diversity.html>) | No evaluation or testing information is reported for this checkpoint, so there is no evidence of diverse socio\-technical testing\. | AI model risks are socio\-technical, so their testing needs input from a broad set of disciplines and diverse testing practices\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card does not describe training data sources, collection, or provenance for MN\-12B\-Lyra\-v3\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No training data collection, curation, or use information is documented for this checkpoint\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only access and license, not intended use or use limitations, so downstream risk scope is undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
