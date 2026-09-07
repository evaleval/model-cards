# Model Card: Mistral\-7B\-Base\-SFT\-KTO

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-7b\-base\-sft\-kto\.json](<./mistral-7b-base-sft-kto.json>)<br>
SHA-256: `59a6954abd1708ca4a20c9db9a0513a16b46ce956672ba0addb5e66346c61201`

## Identity

| Field | Value |
| --- | --- |
| Model ID | princeton\-nlp/Mistral\-7B\-Base\-SFT\-KTO |
| Name | Mistral\-7B\-Base\-SFT\-KTO |
| Developed by | princeton\-nlp \(Hub organization\) |
| Release date | 2024\-05\-17 \(Hugging Face repository creation date\) |
| Version | 20e67bbf5a4831d9d9423b37e741e3f2cc226157 |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,498,016 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 36 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/princeton\-nlp/Mistral\-7B\-Base\-SFT\-KTO](<https://huggingface.co/princeton-nlp/Mistral-7B-Base-SFT-KTO>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, modality, and access type, with no documentation of training data, evaluation, or development process\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
