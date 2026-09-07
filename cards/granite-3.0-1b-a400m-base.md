# Model Card: Granite\-3\.0\-1B\-A400M\-Base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [granite\-3\.0\-1b\-a400m\-base\.json](<./granite-3.0-1b-a400m-base.json>)<br>
SHA-256: `7539497d376db9ac570e296175869b30b01882ce307b2419a0a7b7eff463badf`

## Identity

| Field | Value |
| --- | --- |
| Model ID | ibm\-granite/granite\-3\.0\-1b\-a400m\-base |
| Name | Granite\-3\.0\-1B\-A400M\-Base |
| Developed by | ibm\-granite \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-10\-03 \(Hugging Face repository creation date\) |
| Version | d91cbed802d85eb1b32374623331f6ab2b37403a |

## Lineage

| Field | Value |
| --- | --- |
| Model family | granite 3\.0 a400m |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 1,384,956,928 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 5\.2 GiB of safetensors weights \(5,539,854,072 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model has not undergone any safety alignment, so it may produce problematic outputs\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 25,384 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 7 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The model has not undergone safety alignment, so it may produce problematic outputs\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/ibm\-granite/granite\-3\.0\-1b\-a400m\-base](<https://huggingface.co/ibm-granite/granite-3.0-1b-a400m-base>) |
| Code repository | [https://github\.com/ibm\-granite/granite\-3\.0\-language\-models](<https://github.com/ibm-granite/granite-3.0-language-models>) |
| Citation | @misc\{granite\-models,<br>  author = \{author 1, author2, \.\.\.\},<br>  title = \{\},<br>  journal = \{\},<br>  volume = \{\},<br>  year = \{2024\},<br>  url = \{https://arxiv\.org/abs/0000\.00000\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | open\-weight base model with no safety alignment and no reported safety evaluations \-&gt; users may over\-trust its outputs despite lack of alignment | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`.
