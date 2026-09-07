# Model Card: Llama\_3\.2\_3b\_Kermes\_v2\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\_3\.2\_3b\_kermes\_v2\.1\.json](<./llama_3.2_3b_kermes_v2.1.json>)<br>
SHA-256: `ecae87d19ae6dd49ead345c4e28f777e35ed065613b4c08bbbcbf8f9993121cd`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Nexesenex/Llama\_3\.2\_3b\_Kermes\_v2\.1 |
| Name | Llama\_3\.2\_3b\_Kermes\_v2\.1 |
| Developed by | Nexesenex \(Hub organization\) |
| License | llama3\.2 |
| Release date | 2025\-02\-13 \(Hugging Face repository creation date\) |
| Version | fd1d8e47ccf9191d8b4e61fbd930ce54d5e7a8e3 |
| Summary | A merge of pre\-trained language models built with mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Nexesenex/Llama\_3\.2\_3b\_Kermes\_0\.20 (base model; Kind: merge)<br>SaisExperiments/Evil\-Alpaca\-3B\-L3\.2 (base model; Kind: merge)<br>dphn/Dolphin3\.0\-Llama3\.2\-3B (base model; Kind: merge) |
| Model family | Llama 3\.2 Kermes v2\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,212,749,824 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 6\.0 GiB of safetensors weights \(6,425,528,792 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a merge, not a conventionally trained model; its components are the base model Nexesenex/Llama\_3\.2\_3b\_Kermes\_0\.20 and the merged\-in models cognitivecomputations/Dolphin3\.0\-Llama3\.2\-3B and SaisExperiments/Evil\-Alpaca\-3B\-L3\.2\. |
| Adaptations | The model was produced by the Model Stock merge method, with the base model Nexesenex/Llama\_3\.2\_3b\_Kermes\_0\.20 and the two listed models included in the merge at equal weight, normalized and in float16\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 25 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that perplexity continued to decrease, ARC scores remained stable, and the model stayed coherent even at long contexts, while retaining an unhinged style\. |
| Human evaluations | The developer&\#x27;s readme states the model remains quite coherent even at 10k\+ context, while still being quite unhinged\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Nexesenex/Llama\_3\.2\_3b\_Kermes\_v2\.1](<https://huggingface.co/Nexesenex/Llama_3.2_3b_Kermes_v2.1>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
