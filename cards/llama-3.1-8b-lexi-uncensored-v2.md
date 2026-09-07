# Model Card: Llama\-3\.1\-8B\-Lexi\-Uncensored\-V2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-8b\-lexi\-uncensored\-v2\.json](<./llama-3.1-8b-lexi-uncensored-v2.json>)<br>
SHA-256: `10631fd163e853f590b588676ca842382900d831bbbeb4094cf23cfc1778baed`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Orenguteng/Llama\-3\.1\-8B\-Lexi\-Uncensored\-V2 |
| Name | Llama\-3\.1\-8B\-Lexi\-Uncensored\-V2 |
| Developed by | Orenguteng \(Hub organization\) |
| Model type | A text\-generation model based on Llama\-3\.1\-8B\-Instruct\. |
| License | llama3\.1 |
| Release date | 2024\-08\-09 \(Hugging Face repository creation date\) |
| Version | f4617caeabd21f1820ac89bd125c80eda70901a7 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama\-3\.1\-8B\-Instruct |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,376 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is derived from Llama\-3\.1\-8b\-Instruct, so it inherits that instruct\-tuned base and its license terms\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 12,825 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 319 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Safety evaluations | The model is described as uncensored and highly compliant with requests, including unethical ones, so developers are advised to add their own alignment layer before deploying it as a service\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Orenguteng/Llama\-3\.1\-8B\-Lexi\-Uncensored\-V2](<https://huggingface.co/Orenguteng/Llama-3.1-8B-Lexi-Uncensored-V2>) |
| Code repository | [https://github\.com/meta\-llama/llama\-models](<https://github.com/meta-llama/llama-models>) |
| Citation | The model card states that Lexi is licensed under Meta&\#x27;s Llama license and grants permission for any use, including commercial use, provided it complies with Meta&\#x27;s Llama\-3\.1 license\. |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Harmful output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-output.html>) | Card states the model is uncensored and highly compliant with unethical requests, so it can generate language that leads to physical harm\. | A model might generate language that leads to physical harm\.  The language might include overtly violent, covertly dangerous, or otherwise indirectly unsafe statements\. |
| [Direct instructions attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/direct-instructions-attack.html>) | Card states the model is highly compliant with requests including unethical ones, so direct prompts asking for undesirable behavior are likely to elicit it\. | Prompts, questions, or requests designed to elicit undesirable responses from the application\. This approach directly instructs the model to engage in the undesired behavior\. |
| [Jailbreaking](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/jailbreaking.html>) | Card states the model is uncensored and advises adding an alignment layer, indicating it lacks guardrails that jailbreaking would bypass\. | A jailbreaking attack attempts to break through the guardrails established in the model to perform restricted actions\. |
| [Dangerous use](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/dangerous-use.html>) | Card states the model is highly compliant with unethical requests and open\-weight, enabling intentional use to harm people\. | Generative AI models might be used with the sole intention of harming people\. |
| [Toxic output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/toxic-output.html>) | Card states the model is uncensored, so it may produce hateful, abusive, profane, or obscene content\. | Toxic output occurs when the model produces hateful, abusive, and profane \(HAP\) or obscene content\. This also includes behaviors like bullying\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`.
