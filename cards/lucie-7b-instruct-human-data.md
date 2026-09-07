# Model Card: Lucie\-7B\-Instruct\-human\-data

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [lucie\-7b\-instruct\-human\-data\.json](<./lucie-7b-instruct-human-data.json>)<br>
SHA-256: `77eb192427b8dd22c1416411e42b437d4f420dd77855bc8e3b4df65023b3d33e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | OpenLLM\-France/Lucie\-7B\-Instruct\-human\-data |
| Name | Lucie\-7B\-Instruct\-human\-data |
| Developed by | OpenLLM\-France \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-07 \(Hugging Face repository creation date\) |
| Version | 9d61676280893f335ddbc6b1b5459c2fbb858d54 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | OpenLLM\-France/Lucie\-7B (base model; Kind: quantized) |
| Model family | Lucie human data |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 6,706,960,384 parameters \(safetensors metadata\) |
| Context length | 32,000 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 12\.5 GiB of safetensors weights \(13,413,962,016 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Lucie\-7B\-Instruct\-human\-data is trained on datasets published by third parties\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 620 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 7 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that this model&\#x27;s performance is lower than that of Lucie\-7B\-Instruct\-v1\.1, and frames its main value as demonstrating instruction fine\-tuning without relying on third\-party LLMs\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/OpenLLM\-France/Lucie\-7B\-Instruct\-human\-data](<https://huggingface.co/OpenLLM-France/Lucie-7B-Instruct-human-data>) |
| Code repository | [https://github\.com/OpenLLM\-France/Lucie\-Training](<https://github.com/OpenLLM-France/Lucie-Training>) |
| Citation | @misc\{openllm2025lucie,<br>      title=\{The Lucie\-7B LLM and the Lucie Training Dataset: Open resources for multilingual language generation\}, <br>      author=\{Olivier Gouvert and Julie Hunter and Jérôme Louradour and Christophe Cerisara and Evan Dufraisse and Yaya Sy and Laura Rivière and Jean\-Pierre Lorré and OpenLLM\-France community\},<br>      year=\{2025\},<br>      eprint=\{2503\.12294\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2503\.12294\}, <br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | open\-weight text model released under Apache\-2\.0 with no reported safety evaluations or intended\-use restrictions in the card, so it can be used for purposes other than the developer&\#x27;s stated demonstration of instruction tuning | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | card explicitly reports lower performance than Lucie\-7B\-Instruct\-v1\.1, so users may over\-trust outputs or under\-trust them without a clear performance benchmark | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |
| [Data privacy rights alignment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-privacy-rights.html>) | trained on datasets published by third parties with no stated privacy filtering or data\-subject rights handling, raising potential reidentification or rights\-alignment concerns | Applicable laws can establish data subject rights such as opt\-out rights, right to access, and right to be forgotten\. Synthetic data might raise unique concerns, such as the potential for reidentification of individuals from seemingly anonymous synthetic data\. Data subject rights might also be relevant in scenarios where synthetic data is derived from sensitive or personal information\. |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | open\-weight checkpoint trained on third\-party datasets with no documentation of data provenance or governance process, making accountability harder to establish | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
