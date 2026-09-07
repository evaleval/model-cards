# Model Card: XinYuan\-Qwen2\-7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [xinyuan\-qwen2\-7b\.json](<./xinyuan-qwen2-7b.json>)<br>
SHA-256: `42b26a1dd4d49c338e97d9d25c192f6e63e0d2088d21f51637deb12b9a4086c1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | thomas\-yanxin/XinYuan\-Qwen2\-7B |
| Name | XinYuan\-Qwen2\-7B |
| Developed by | thomas\-yanxin \(Hub organization\) |
| License | other |
| Release date | 2024\-08\-21 \(Hugging Face repository creation date\) |
| Version | c62d83eee2f4812ac17fc17d307f4aa1a77c5359 |
| Summary | A model created to demonstrate the usability of the MT\-SFT\-ShareGPT dataset, emphasizing data quality\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | XinYuan Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,864 bytes\) in BF16 |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on the MT\-SFT\-ShareGPT dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 22 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that a better data governance approach, even with only supervised fine\-tuning, can greatly improve model results\. |
| Human evaluations | The developer reports results from an OpenCompass evaluation\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/thomas\-yanxin/XinYuan\-Qwen2\-7B](<https://huggingface.co/thomas-yanxin/XinYuan-Qwen2-7B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card only names MT\-SFT\-ShareGPT and gives no collection/curation details, so training\-data transparency is limited\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Open\-weight release with only a dataset name and no source/usage\-term traceability for MT\-SFT\-ShareGPT raises provenance uncertainty\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card describes a general dense decoder\-only model and reports only evaluation results, with no stated intended use or use restrictions\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
