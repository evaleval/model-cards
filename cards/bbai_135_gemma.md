# Model Card: BBAI\_135\_Gemma

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [bbai\_135\_gemma\.json](<./bbai_135_gemma.json>)<br>
SHA-256: `4954b30b6767d3fc586b788ba7b1d02af928d077fa176a2fde78a97c02abb29a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Supichi/BBAI\_135\_Gemma |
| Name | BBAI\_135\_Gemma |
| Developed by | Supichi \(Hub organization\) |
| Release date | 2025\-02\-26 \(Hugging Face repository creation date\) |
| Version | 487cc6e1636bc7eda7c9ba19cd066890144397cf |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 19,299,635,712 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 35\.9 GiB of safetensors weights \(38,599,313,136 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of allknowingroger/Gemma2Slerp2\-27B and allknowingroger/Gemma2Slerp3\-27B, combined with the SLERP merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 15 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Supichi/BBAI\_135\_Gemma](<https://huggingface.co/Supichi/BBAI_135_Gemma>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | open\-weight text model with no stated use restrictions or data provenance \-&gt; users may include copyrighted material in prompts | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
