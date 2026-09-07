# Model Card: Dolphin 2\.9\.2 Qwen2 72B 🐬

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [dolphin\-2\.9\.2\-qwen2\-72b\.json](<./dolphin-2.9.2-qwen2-72b.json>)<br>
SHA-256: `c30d1c043a86ddf74157a7c1812fd720a47f0237537eb2d3515eacca00b163b7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | cognitivecomputations/dolphin\-2\.9\.2\-qwen2\-72b |
| Name | Dolphin 2\.9\.2 Qwen2 72B 🐬 |
| Developed by | dphn \(Hub organization\) |
| License | other |
| Release date | 2024\-05\-27 \(Hugging Face repository creation date\) |
| Version | 5fdf999df3464a95c6387386f827e93227f3fa60 |
| Summary | Dolphin 2\.9\.2 is a model with a variety of instruction, conversational, and coding skills\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-72B (base model; Kind: finetune) |
| Model family | dolphin 2\.9\.2 qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 72,706,203,648 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 135\.4 GiB of safetensors weights \(145,412,518,832 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was trained with full fine\-tuning on parameters selected by Laser Scanner, using the ChatML prompt template format\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 723 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 179 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that Dolphin\-2\.9\.2 possesses a range of instruction\-following, conversational, and coding capabilities, and also notes initial agentic abilities and function\-calling support\. |
| Safety evaluations | The developer describes the model as uncensored, with alignment and bias removed from the dataset, and states that it will be highly compliant with requests, including unethical ones\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/cognitivecomputations/dolphin\-2\.9\.2\-qwen2\-72b](<https://huggingface.co/cognitivecomputations/dolphin-2.9.2-qwen2-72b>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Direct instructions attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/direct-instructions-attack.html>) | Card states the model is uncensored, with alignment and bias removed, and highly compliant with requests including unethical ones \-&gt; direct instructions for harmful content are plausibly effective\. | Prompts, questions, or requests designed to elicit undesirable responses from the application\. This approach directly instructs the model to engage in the undesired behavior\. |
| [Jailbreaking](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/jailbreaking.html>) | Open\-weight model explicitly described as uncensored with alignment removed \-&gt; no guardrails to bypass, but the card&\#x27;s own safety evaluation indicates jailbreaking\-style restricted actions are not prevented\. | A jailbreaking attack attempts to break through the guardrails established in the model to perform restricted actions\. |
| [Harmful output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-output.html>) | Card states it will be highly compliant with requests, including unethical ones \-&gt; plausible generation of language leading to physical harm\. | A model might generate language that leads to physical harm\.  The language might include overtly violent, covertly dangerous, or otherwise indirectly unsafe statements\. |
| [Toxic output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/toxic-output.html>) | Card states alignment and bias were removed from the dataset and the model is uncensored \-&gt; plausible hateful, abusive, profane, or obscene output\. | Toxic output occurs when the model produces hateful, abusive, and profane \(HAP\) or obscene content\. This also includes behaviors like bullying\. |
| [Dangerous use](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/dangerous-use.html>) | Open\-weight checkpoint with reported high compliance with unethical requests \-&gt; plausible intentional use to harm people\. | Generative AI models might be used with the sole intention of harming people\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
