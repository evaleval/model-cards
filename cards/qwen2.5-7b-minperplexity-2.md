# Model Card: Qwen2\.5\-7B\-minperplexity\-2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-7b\-minperplexity\-2\.json](<./qwen2.5-7b-minperplexity-2.json>)<br>
SHA-256: `942000eca5c05112831a89eb9c361bc99ade9a92ce48dcfa85b71bb7a970b3a7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | jeffmeloy/Qwen2\.5\-7B\-minperplexity\-2 |
| Name | Qwen2\.5\-7B\-minperplexity\-2 |
| Developed by | jeffmeloy \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2024\-12\-03 \(Hugging Face repository creation date\) |
| Version | 453ae2290bc7dc43e131583037edda61ab6e21db |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,864 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 23 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/jeffmeloy/Qwen2\.5\-7B\-minperplexity\-2](<https://huggingface.co/jeffmeloy/Qwen2.5-7B-minperplexity-2>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | open\-weight text\-generation model with no reported safety evaluation \-&gt; users may over\-trust its outputs | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |
| [Harmful output](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-output.html>) | open\-weight text\-generation model with no reported safety evaluation \-&gt; may generate harmful language | A model might generate language that leads to physical harm\.  The language might include overtly violent, covertly dangerous, or otherwise indirectly unsafe statements\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
