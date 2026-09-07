# Model Card: Mistral\-7B\-Instruct\-v0\.2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mistral\-7b\-instruct\-v0\.2\.json](<./mistral-7b-instruct-v0.2.json>)<br>
SHA-256: `7e480521cd929fb0cbf87a73c04d189631667f1a3484f6007364919645f0f881`

## Identity

| Field | Value |
| --- | --- |
| Model ID | mistralai/Mistral\-7B\-Instruct\-v0\.2 |
| Name | Mistral\-7B\-Instruct\-v0\.2 |
| Developed by | mistralai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2023\-12\-11 \(Hugging Face repository creation date\) |
| Version | 63a8b081895390a26e140280378bc85ec8bce07a |
| Summary | Mistral\-7B\-Instruct\-v0\.2 is a 7\-billion\-parameter instruct fine\-tuned language model, positioned as a cost\-effective endpoint serving a minor release of Mistral 7B Instruct\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Mistral |

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

| Field | Value |
| --- | --- |
| Training data | The Mistral\-7B\-Instruct\-v0\.2 model is an instruction fine\-tuned version of Mistral\-7B\-v0\.2\. |
| Adaptations | The model is an instruct fine\-tune of Mistral\-7B\-v0\.2, and instruction fine\-tuning is applied by surrounding prompts with \[INST\] and \[/INST\] tokens\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,266,011 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 3,207 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports a score of 7\.6 on MT\-Bench for this model\. |
| Safety evaluations | The developer states the model does not have any moderation mechanisms\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/mistralai/Mistral\-7B\-Instruct\-v0\.2](<https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2>) |
| Technical report | [https://arxiv\.org/abs/2310\.06825](<https://arxiv.org/abs/2310.06825>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only MT\-Bench score and states no moderation mechanisms, with no details on design, development, or evaluation process \-&gt; lack of model transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Jailbreaking](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/jailbreaking.html>) | Open\-weight instruct model with no moderation mechanisms \-&gt; jailbreaking\. | A jailbreaking attack attempts to break through the guardrails established in the model to perform restricted actions\. |
| [Direct instructions attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/direct-instructions-attack.html>) | Open\-weight instruct model with no moderation mechanisms \-&gt; direct instructions attack\. | Prompts, questions, or requests designed to elicit undesirable responses from the application\. This approach directly instructs the model to engage in the undesired behavior\. |
| [Harmful output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-output.html>) | Open\-weight instruct model with no moderation mechanisms \-&gt; harmful output\. | A model might generate language that leads to physical harm\.  The language might include overtly violent, covertly dangerous, or otherwise indirectly unsafe statements\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.code_repository`, `links.citation`.
