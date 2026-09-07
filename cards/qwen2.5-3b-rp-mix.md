# Model Card: Qwen2\.5\-3B\-RP\-Mix

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-3b\-rp\-mix\.json](<./qwen2.5-3b-rp-mix.json>)<br>
SHA-256: `814b0956a8df649c9fe8e5006bd048c59d4ad96543deccfa416bda3df5aa5125`

## Identity

| Field | Value |
| --- | --- |
| Model ID | bunnycore/Qwen2\.5\-3B\-RP\-Mix |
| Name | Qwen2\.5\-3B\-RP\-Mix |
| Developed by | bunnycore \(Hub organization\) |
| Release date | 2024\-10\-22 \(Hugging Face repository creation date\) |
| Version | 3e3725ccbbd3ec731f92e2cb4e71bbcaa8c0ee5c |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-3B\-Instruct (base model; Kind: merge)<br>bunnycore/Qwen\-2\.5\-3b\-Rp\-lora\_model (base model; Kind: merge) |
| Model family | Qwen2\.5 RP Mix |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,397,103,616 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 6\.3 GiB of safetensors weights \(6,794,256,992 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a merge of Qwen/Qwen2\.5\-3B\-Instruct and bunnycore/Qwen\-2\.5\-3b\-Rp\-lora\_model using the passthrough merge method\. |
| Adaptations | The model was created by merging Qwen/Qwen2\.5\-3B\-Instruct with bunnycore/Qwen\-2\.5\-3b\-Rp\-lora\_model using the passthrough merge method\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 24 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/bunnycore/Qwen2\.5\-3B\-RP\-Mix](<https://huggingface.co/bunnycore/Qwen2.5-3B-RP-Mix>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | The checkpoint is an open\-weight text\-in/text\-out model for roleplay \(RP\) merges, so users may paste private or personal context into prompts with no reported confidentiality safeguards\. | Confidential information might be included as a part of the prompt that is sent to the model\. |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | The model is an open\-weight RP merge of an instruct model and a roleplay LoRA, and roleplay prompts can include copyrighted character or story text with no reported IP protections\. | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Prompt leaking](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/prompt-leaking.html>) | The model is an open\-weight text\-in/text\-out instruct/RP merge; system prompts or roleplay instructions may be extractable through prompt\-leak attacks, and no prompt\-leak evaluation is reported\. | 'A prompt leak attack attempts to extract a model's system prompt \(also known as the system message\)\.' |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | The card reports no safety or reliability evaluations for this open\-weight RP/instruct merge, so users may over\-trust its outputs in decision\-making or under\-trust them without evidence\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model's output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model's output when the model's output is likely incorrect\. Under\-reliance is the opposite, where the person doesn't trust the model but should\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
