# Model Card: 100k\_fineweb\_continued\_pretraining\_Qwen2\.5\-0\.5B\-Instruct\_Unsloth\_merged\_16bit

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [100k\_fineweb\_continued\_pretraining\_qwen2\.5\-0\.5b\-instruct\_unsloth\_merged\_16bit\.json](<./100k_fineweb_continued_pretraining_qwen2.5-0.5b-instruct_unsloth_merged_16bit.json>)<br>
SHA-256: `930daa51f1607b75f6127e0727e0f6a6e72a5d27711324271070e70ca7f7743a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | FlofloB/100k\_fineweb\_continued\_pretraining\_Qwen2\.5\-0\.5B\-Instruct\_Unsloth\_merged\_16bit |
| Name | 100k\_fineweb\_continued\_pretraining\_Qwen2\.5\-0\.5B\-Instruct\_Unsloth\_merged\_16bit |
| Developed by | FlofloB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-11\-28 \(Hugging Face repository creation date\) |
| Version | 318daa274d6dc8752af2208e92f6f2f6d0efd5ae |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 630,167,424 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 1\.2 GiB of safetensors weights \(1,260,367,152 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on the HuggingFaceFW/fineweb dataset\. |
| Adaptations | The model is a fine\-tune of unsloth/qwen2\.5\-0\.5b\-instruct\-bnb\-4bit\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 198 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/FlofloB/100k\_fineweb\_continued\_pretraining\_Qwen2\.5\-0\.5B\-Instruct\_Unsloth\_merged\_16bit](<https://huggingface.co/FlofloB/100k_fineweb_continued_pretraining_Qwen2.5-0.5B-Instruct_Unsloth_merged_16bit>) |
| Code repository | [https://github\.com/unslothai/unsloth](<https://github.com/unslothai/unsloth>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card names only HuggingFaceFW/fineweb and a base checkpoint, with no lineage or curation details for this exact 100k continued\-pretraining checkpoint\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card gives only the dataset name and no collection, curation, or filtering details for the 100k fineweb continued\-pretraining data\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No documentation of how the fineweb subset was collected, curated, or used for this checkpoint, making training\-data behavior hard to explain\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
