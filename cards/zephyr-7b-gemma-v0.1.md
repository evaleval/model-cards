# Model Card: Zephyr 7B Gemma

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [zephyr\-7b\-gemma\-v0\.1\.json](<./zephyr-7b-gemma-v0.1.json>)<br>
SHA-256: `33dd6220f41477820ed10ea06a7b581c277c2e101bd9767b9e1afd8915dde596`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceH4/zephyr\-7b\-gemma\-v0\.1 |
| Name | Zephyr 7B Gemma |
| Developed by | HuggingFaceH4 \(Hub organization\) |
| License | other |
| Release date | 2024\-03\-01 \(Hugging Face repository creation date\) |
| Version | 03b3427d0ed07d2e0f86c0a7e53d82d4beef9540 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | HuggingFaceH4/zephyr\-7b\-gemma\-sft\-v0\.1 (base model; Kind: finetune) |
| Model family | zephyr gemma |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,537,680,896 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.9 GiB of safetensors weights \(17,075,391,360 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 106 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 124 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MT Bench⬇️ | Not specified | 7\.81 | Not specified | Not reported |
| IFEval | Not specified | 28\.76 | Not specified | Not reported |
| AGIEval | Not specified | 34\.22 | Not specified | Not reported |
| GPT4All | Not specified | 66\.37 | Not specified | Not reported |
| TruthfulQA | Not specified | 52\.19 | Not specified | Not reported |
| BigBench | Not specified | 37\.10 | Not specified | Not reported |
| Average ⬇️ | Not specified | 47\.47 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceH4/zephyr\-7b\-gemma\-v0\.1](<https://huggingface.co/HuggingFaceH4/zephyr-7b-gemma-v0.1>) |
| Code repository | [https://github\.com/huggingface/alignment\-handbook](<https://github.com/huggingface/alignment-handbook>) |
| Citation | @misc\{tunstall2023zephyr,<br>      title=\{Zephyr: Direct Distillation of LM Alignment\}, <br>      author=\{Lewis Tunstall and Edward Beeching and Nathan Lambert and Nazneen Rajani and Kashif Rasul and Younes Belkada and Shengyi Huang and Leandro von Werra and Clémentine Fourrier and Nathan Habib and Nathan Sarrazin and Omar Sanseviero and Alexander M\. Rush and Thomas Wolf\},<br>      year=\{2023\},<br>      eprint=\{2310\.16944\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.LG\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | open\-weight dense decoder\-only text model; card reports no efficiency or training footprint information, so its training/operation plausibly has environmental costs\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
