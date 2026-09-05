# Model Card: DeepSeek\-V3\-Base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-v3\-base\.json](<./deepseek-v3-base.json>)<br>
SHA-256: `3e0272da3241c0457fcaec4d61b7479cf6b23387d549bacd229ac0241e5853d1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | deepseek\-ai/DeepSeek\-V3\-Base |
| Name | DeepSeek\-V3\-Base |
| Developed by | deepseek\-ai \(Hub organization\) |
| Release date | 2024\-12\-25 \(Hugging Face repository creation date\) |
| Version | afb92e1fa402c2be2a9eb085312bb02e0384d6c7 |
| Summary | DeepSeek\-V3 is a large Mixture\-of\-Experts language model with 671B total parameters and 37B activated per token\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | DeepSeek V3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 684,531,386,000 parameters \(safetensors metadata\) |
| Context length | 163,840 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F8\_E4M3 \(safetensors weight dtype\) |
| Model size | 641\.3 GiB of safetensors weights \(688,586,727,753 bytes\) in F8\_E4M3 |
| Input / output | Text input<br>Text output |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The DeepSeek\-V3 family was pre\-trained on 14\.8 trillion diverse and high\-quality tokens in its tokenizer\. |
| Training data size | 14\.8 trillion tokens |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 8,118 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 1,706 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that DeepSeek\-V3 surpasses other open\-source models and is on par with leading closed\-source models in comprehensive evaluations\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| English | Not specified | 95\.3 | Not specified | Not reported |
| Code | Not specified | 65\.2 | Not specified | Not reported |
| Math | Not specified | 89\.3 | Not specified | Not reported |
| Chinese | Not specified | 76\.3 | Not specified | Not reported |
| Multilingual | Not specified | 79\.4 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/deepseek\-ai/DeepSeek\-V3\-Base](<https://huggingface.co/deepseek-ai/DeepSeek-V3-Base>) |
| Technical report | [https://arxiv\.org/abs/2412\.19437](<https://arxiv.org/abs/2412.19437>) |
| Code repository | [https://github\.com/deepseek\-ai/DeepSeek\-V3](<https://github.com/deepseek-ai/DeepSeek-V3>) |
| Citation | @misc\{deepseekai2024deepseekv3technicalreport,<br>      title=\{DeepSeek\-V3 Technical Report\}, <br>      author=\{DeepSeek\-AI\},<br>      year=\{2024\},<br>      eprint=\{2412\.19437\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2412\.19437\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
