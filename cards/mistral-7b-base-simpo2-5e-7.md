# Model Card: Mistral\-7B\-Base\-SimPO2\-5e\-7

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-7b\-base\-simpo2\-5e\-7\.json](<./mistral-7b-base-simpo2-5e-7.json>)<br>
SHA-256: `eb2bb781a62061f391ff550c291ec2e3c8a05b3f2fe60c53935171c61ee896c8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | TTTXXX01/Mistral\-7B\-Base\-SimPO2\-5e\-7 |
| Name | Mistral\-7B\-Base\-SimPO2\-5e\-7 |
| Developed by | TTTXXX01 \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-08\-30 \(Hugging Face repository creation date\) |
| Version | 7a271e3061165f4e1abfe26715c04e20c2ac935e |

## Lineage

| Field | Value |
| --- | --- |
| Base models | alignment\-handbook/zephyr\-7b\-sft\-full (base model; Kind: finetune) |
| Model family | Mistral SimPO2 5e 7 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,498,016 bytes\) in BF16 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 16 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/TTTXXX01/Mistral\-7B\-Base\-SimPO2\-5e\-7](<https://huggingface.co/TTTXXX01/Mistral-7B-Base-SimPO2-5e-7>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | open\-weight dense decoder\-only model; card gives no training footprint or efficiency info, so plausible environmental impact from training/operation is unaddressed\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
