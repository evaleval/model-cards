# Model Card: MaziyarPanahi/calme\-3\.1\-baguette\-3b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [calme\-3\.1\-baguette\-3b\.json](<./calme-3.1-baguette-3b.json>)<br>
SHA-256: `a7f8d3d15bf9e4c057436a56636943cf5e406f74b9ff21d468a3d4685cbd514f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | MaziyarPanahi/calme\-3\.1\-baguette\-3b |
| Name | MaziyarPanahi/calme\-3\.1\-baguette\-3b |
| Developed by | MaziyarPanahi \(Hub organization\) |
| Model type | Text\-generation model |
| License | other |
| Release date | 2024\-11\-07 \(Hugging Face repository creation date\) |
| Version | 2029e36e5764f04cfe2f57a09af64ceab52ec9fb |
| Summary | This model is a fine\-tuned iteration of Qwen/Qwen2\.5\-3B, optimized for general\-domain performance in French and English\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-3B (base model; Kind: finetune) |
| Model family | calme 3\.1 baguette |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,085,383,680 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 5\.7 GiB of safetensors weights \(6,170,816,984 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned from Qwen/Qwen2\.5\-3B using two French instruction datasets: MaziyarPanahi/french\_instruct\_sharegpt and MaziyarPanahi/calme\-legalkit\-v0\.2\. |
| Adaptations | It is a fine\-tuned iteration of Qwen/Qwen2\.5\-3B, adapted to improve general\-domain performance in French and English\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 32 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/MaziyarPanahi/calme\-3\.1\-baguette\-3b](<https://huggingface.co/MaziyarPanahi/calme-3.1-baguette-3b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | open\-weight fine\-tune with license &\#x27;other&\#x27; and no documentation of governance or evaluation details in the card | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
