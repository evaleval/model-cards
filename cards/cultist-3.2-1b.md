# Model Card: Cultist\-3\.2\-1B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [cultist\-3\.2\-1b\.json](<./cultist-3.2-1b.json>)<br>
SHA-256: `237d568d3db0fd9f9a608dcdb5d80a6897d8755261499289a7efadabae0982de`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Novaciano/Cultist\-3\.2\-1B |
| Name | Cultist\-3\.2\-1B |
| Developed by | Novaciano \(Hub organization\) |
| Release date | 2025\-03\-09 \(Hugging Face repository creation date\) |
| Version | ddd59dbafd2e4536907fb32c4dc825343aeaabea |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Novaciano/Sigil\-Of\-Satan\-3\.2\-1B (base model; Kind: merge)<br>jtatman/llama\-3\.2\-1b\-lewd\-mental\-occult (base model; Kind: merge) |
| Model family | Cultist 3\.2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,498,482,688 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.8 GiB of safetensors weights \(2,996,982,344 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of pretrained language models, created using mergekit with the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 21 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Novaciano/Cultist\-3\.2\-1B](<https://huggingface.co/Novaciano/Cultist-3.2-1B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only mergekit/SLERP merge of pretrained LMs and no training/evaluation documentation, so inner workings and development process are undocumented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card does not state the provenance or license terms of the merged base models&\#x27; training data, only names the merged model and source repos\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information is provided about collection, curation, or use of training data for the merged models, making training\-data documentation absent\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Toxic output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/toxic-output.html>) | The named source &\#x27;lewd\-mental\-occult&\#x27; and &\#x27;Sigil\-Of\-Satan&\#x27; suggest the merge may produce obscene or occult\-themed content, and no safety evaluation is reported\. | Toxic output occurs when the model produces hateful, abusive, and profane \(HAP\) or obscene content\. This also includes behaviors like bullying\. |
| [Jailbreaking](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/jailbreaking.html>) | Open\-weight merged model with no reported guardrails or safety evaluation can be used to bypass alignment protections\. | A jailbreaking attack attempts to break through the guardrails established in the model to perform restricted actions\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
