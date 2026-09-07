# Model Card: MISCHIEVOUS\-12B\-Mix\_0\.6v

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mischievous\-12b\-mix\_0\.6v\.json](<./mischievous-12b-mix_0.6v.json>)<br>
SHA-256: `4552bf5031202658d8aa296013336e428c4e009e6a678ff14d320259c3882eed`

## Identity

| Field | Value |
| --- | --- |
| Model ID | bamec66557/MISCHIEVOUS\-12B\-Mix\_0\.6v |
| Name | MISCHIEVOUS\-12B\-Mix\_0\.6v |
| Developed by | bamec66557 \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-12\-19 \(Hugging Face repository creation date\) |
| Version | 62920dbb46420a1ab2a4bdbca49d9212683bbef3 |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | bamec66557/MISCHIEVOUS\-12B\-Mix\_0\.4v (base model; Kind: merge)<br>bamec66557/MISCHIEVOUS\-12B\-Mix\_III\_IV\_V (base model; Kind: merge) |
| Model family | MISCHIEVOUS Mix 0\.6v |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 12,247,802,880 parameters \(safetensors metadata\) |
| Context length | 1,024,000 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 22\.8 GiB of safetensors weights \(24,495,648,064 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of bamec66557/MISCHIEVOUS\-12B\-Mix\_III\_IV\_V and bamec66557/MISCHIEVOUS\-12B\-Mix\_0\.4v, produced with the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 14 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/bamec66557/MISCHIEVOUS\-12B\-Mix\_0\.6v](<https://huggingface.co/bamec66557/MISCHIEVOUS-12B-Mix_0.6v>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Evasion attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/evasion-attack.html>) | text\-only dense decoder\-only model merged from pre\-trained language models with no reported safety evaluation or input filtering \-&gt; evasion attacks on text inputs are plausible | Evasion attacks attempt to make a model output incorrect results by slightly perturbing the input data sent to the trained model\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | open\-weight text\-output model with no reported evaluations or usage guidance \-&gt; users may over\- or under\-rely on its outputs | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
