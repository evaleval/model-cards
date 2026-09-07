# Model Card: Qwen2\-0\.5B\-Abyme\-merge3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-0\.5b\-abyme\-merge3\.json](<./qwen2-0.5b-abyme-merge3.json>)<br>
SHA-256: `3eb729567ffc7a589a238a01f10dc049a35293df5fb244c74da0d85c3928851f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | CoolSpring/Qwen2\-0\.5B\-Abyme\-merge3 |
| Name | Qwen2\-0\.5B\-Abyme\-merge3 |
| Developed by | CoolSpring \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-07\-27 \(Hugging Face repository creation date\) |
| Version | cf6c8001e857ee3575882d4b0cc920ec40ac2a32 |
| Summary | Qwen2\-0\.5B\-Abyme\-merge3 is a merged model created with LazyMergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | CoolSpring/Qwen2\-0\.5B\-Abyme (base model; Kind: merge)<br>Qwen/Qwen2\-0\.5B\-Instruct (base model; Kind: merge) |
| Model family | Qwen2 Abyme merge3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 629,647,744 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 1\.2 GiB of safetensors weights \(1,259,328,080 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a merge of other models, created with LazyMergekit using the dare\_ties merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 26 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/CoolSpring/Qwen2\-0\.5B\-Abyme\-merge3](<https://huggingface.co/CoolSpring/Qwen2-0.5B-Abyme-merge3>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | open\-weight text model with no reported data filtering or usage restrictions \-&gt; users may include copyrighted material in prompts | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | open\-weight text model with no reported data handling safeguards \-&gt; users may send confidential information in prompts | Confidential information might be included as a part of the prompt that is sent to the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
