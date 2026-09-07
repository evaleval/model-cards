# Model Card: Kosmos\-8B\-v1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [kosmos\-8b\-v1\.json](<./kosmos-8b-v1.json>)<br>
SHA-256: `b95682920049de13687d1bbe17e3e733bafb45a5f6ae7c915b6195f747a97cd5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Khetterman/Kosmos\-8B\-v1 |
| Name | Kosmos\-8B\-v1 |
| Developed by | Khetterman \(Hub organization\) |
| Release date | 2024\-11\-22 \(Hugging Face repository creation date\) |
| Version | 16ad5242ca89c6901fae1f41033f00ce455f4be0 |
| Summary | Kosmos\-8B\-v1 is a merge of 14 models created with mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Arkana08/LexiMaid\-L3\-8B (base model; Kind: merge)<br>Arkana08/Mythorica\-L3\-8B (base model; Kind: merge)<br>Casual\-Autopsy/L3\-Luna\-8B (base model; Kind: merge)<br>IlyaGusev/saiga\_llama3\_8b (base model; Kind: merge)<br>Khetterman/CursedMatrix\-8B\-v9 (base model; Kind: merge)<br>SicariusSicariiStuff/LLAMA\-3\_8B\_Unaligned\_BETA (base model; Kind: merge)<br>ZeroXClem/L3SAO\-Mix\-SuperHermes\-NovaPurosani\-8B (base model; Kind: merge)<br>ZeroXClem/Llama\-3\-Aetheric\-Hermes\-Lexi\-Smaug\-8B (base model; Kind: merge)<br>ZeroXClem/Llama3\.1\-TheiaFire\-DarkFusion\-8B (base model; Kind: merge)<br>aloobun/CosmicBun\-8B\-DPO (base model; Kind: merge)<br>bluuwhale/L3\-SthenoMaidBlackroot\-8B\-V1 (base model; Kind: merge)<br>invisietch/L3\.1\-EtherealRainbow\-v1\.0\-rc1\-8B (base model; Kind: merge)<br>jeiku/Average\_Normie\_v3\.69\_8B (base model; Kind: merge) |
| Model family | Kosmos v1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,336 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a merge of 14 models created using mergekit, with a multistep process and remerge with some model variations for best result\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 20 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Khetterman/Kosmos\-8B\-v1](<https://huggingface.co/Khetterman/Kosmos-8B-v1>) |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
