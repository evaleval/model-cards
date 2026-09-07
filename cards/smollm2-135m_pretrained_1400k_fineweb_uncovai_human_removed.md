# Model Card: smollm2\-135M\_pretrained\_1400k\_fineweb\_uncovai\_human\_removed

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\-135m\_pretrained\_1400k\_fineweb\_uncovai\_human\_removed\.json](<./smollm2-135m_pretrained_1400k_fineweb_uncovai_human_removed.json>)<br>
SHA-256: `ed0d3786b45814f1ebc5820aa8dc552914496a68832f06a29ef59ef4558475fd`

## Identity

| Field | Value |
| --- | --- |
| Model ID | FlofloB/smollm2\-135M\_pretrained\_1400k\_fineweb\_uncovai\_human\_removed |
| Name | smollm2\-135M\_pretrained\_1400k\_fineweb\_uncovai\_human\_removed |
| Developed by | FlofloB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-28 \(Hugging Face repository creation date\) |
| Version | f2851eedb367100fa0ca50ed25ff610a83713de2 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | FlofloB/smollm2\-135M\_pretrained\_1200k\_fineweb\_uncovai\_human\_removed (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 134,515,008 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 0\.5 GiB of safetensors weights \(538,090,408 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/FlofloB/smollm2\-135M\_pretrained\_1400k\_fineweb\_uncovai\_human\_removed](<https://huggingface.co/FlofloB/smollm2-135M_pretrained_1400k_fineweb_uncovai_human_removed>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | open\-weight 135M dense decoder\-only model trained on 1400k steps of FineWeb data; training a model of this size on this scale still consumes compute/energy, and the card reports no efficiency or environmental mitigations\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
