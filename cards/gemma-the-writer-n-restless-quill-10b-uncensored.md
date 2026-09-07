# Model Card: Gemma\-The\-Writer\-N\-Restless\-Quill\-10B\-Uncensored

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-the\-writer\-n\-restless\-quill\-10b\-uncensored\.json](<./gemma-the-writer-n-restless-quill-10b-uncensored.json>)<br>
SHA-256: `dae0645c41d0f835345f829d10987c4c1a78698a1fb8016a2078a0ecc5baeb54`

## Identity

| Field | Value |
| --- | --- |
| Model ID | DavidAU/Gemma\-The\-Writer\-N\-Restless\-Quill\-10B\-Uncensored |
| Name | Gemma\-The\-Writer\-N\-Restless\-Quill\-10B\-Uncensored |
| Developed by | DavidAU \(Hub organization\) |
| Release date | 2024\-10\-30 \(Hugging Face repository creation date\) |
| Version | 71b9cadcda7b387979822f52faceb93ccaf36213 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-2\-9b\-it (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 10,034,486,784 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 18\.7 GiB of safetensors weights \(20,069,032,912 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 134 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 7 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/DavidAU/Gemma\-The\-Writer\-N\-Restless\-Quill\-10B\-Uncensored](<https://huggingface.co/DavidAU/Gemma-The-Writer-N-Restless-Quill-10B-Uncensored>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Social hacking attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/social-hacking-attack.html>) | Uncensored open\-weight chat model \(Gemma\-The\-Writer\-N\-Restless\-Quill\-10B\-Uncensored\) with no reported safety evaluation \-&gt; manipulative role\-play prompts may elicit harmful content\. | Manipulative prompts that use social engineering techniques, such as role\-playing or hypothetical scenarios, to persuade the model into generating harmful content\. |
| [Harmful output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-output.html>) | The checkpoint name includes &\#x27;Uncensored&\#x27; and no safety evaluation is reported, so it plausibly generates violent or otherwise unsafe language\. | A model might generate language that leads to physical harm\.  The language might include overtly violent, covertly dangerous, or otherwise indirectly unsafe statements\. |
| [Prompt leaking](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/prompt-leaking.html>) | Open\-weight model derived from google/gemma\-2\-9b\-it; if it retains an instruct system prompt, unrestricted access enables prompt extraction attempts\. | &\#x27;A prompt leak attack attempts to extract a model&\#x27;s system prompt \(also known as the system message\)\.&\#x27; |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
