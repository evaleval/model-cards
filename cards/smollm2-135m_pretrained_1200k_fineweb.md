# Model Card: smollm2\-135M\_pretrained\_1200k\_fineweb

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\-135m\_pretrained\_1200k\_fineweb\.json](<./smollm2-135m_pretrained_1200k_fineweb.json>)<br>
SHA-256: `c1188290be17d795acf27a6465c2382aaf7e1d4c71f4944b663eddfc71996447`

## Identity

| Field | Value |
| --- | --- |
| Model ID | FlofloB/smollm2\-135M\_pretrained\_1200k\_fineweb |
| Name | smollm2\-135M\_pretrained\_1200k\_fineweb |
| Developed by | FlofloB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-12 \(Hugging Face repository creation date\) |
| Version | d886605e0d45787f492f628fd0ea72c27f205f83 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | FlofloB/smollm2\-135M\_pretrained\_1000k\_fineweb (base model; Kind: finetune) |
| Model family | smollm2 pretrained 1200k fineweb |

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
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/FlofloB/smollm2\-135M\_pretrained\_1200k\_fineweb](<https://huggingface.co/FlofloB/smollm2-135M_pretrained_1200k_fineweb>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, modality, license, and family; no design, training, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names FineWeb as training data but gives no dataset documentation, curation details, or data collection information\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data is only identified as FineWeb with no provenance or usage\-rights verification for this checkpoint\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states no intended use or downstream task, so relevant risks cannot be scoped for this open\-weight text model\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
