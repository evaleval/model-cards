# Model Card: \`StableLM Zephyr 3B\`

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [stablelm\-zephyr\-3b\.json](<./stablelm-zephyr-3b.json>)<br>
SHA-256: `c72eab91413815b806f95fbccdf971fd5533add1d2e90a67cb4287694cea4988`

## Identity

| Field | Value |
| --- | --- |
| Model ID | stabilityai/stablelm\-zephyr\-3b |
| Name | \`StableLM Zephyr 3B\` |
| Developed by | stabilityai \(Hub organization\) |
| License | other |
| Release date | 2023\-11\-21 \(Hugging Face repository creation date\) |
| Version | fe1fd5e36ccb8cb2cb1dc225ab6d2962692b9837 |
| Summary | StableLM Zephyr 3B is a 3 billion parameter instruction\-tuned language model trained with publicly available and synthetic datasets using Direct Preference Optimization, with evaluation based on MT Bench and Alpaca\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | stablelm zephyr |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 2,795,443,200 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 5\.2 GiB of safetensors weights \(5,590,927,496 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 13,268 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 261 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | StableLM Zephyr 3B is a 3 billion parameter instruction\-tuned model trained with DPO on public and synthetic datasets; the developer reports MT\-Bench and AlpacaEval results for this model\. |
| Safety evaluations | The developer evaluated the model on 488 malicious prompts using standard harmfulness protocols, reporting that it reduced harmful outputs by 55 compared with Zephyr\-7b\-β as judged by GPT\-4\. Internal red teaming found the model generally avoids harmful information unless prompted, but can produce potentially harmful outputs or misinformation when requested\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MT\-Bench | score | 6\.64 | Not specified | Not reported |
| AlpacaEval | win rate | 76\.00 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/stabilityai/stablelm\-zephyr\-3b](<https://huggingface.co/stabilityai/stablelm-zephyr-3b>) |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`, `risks.possible_risks`.
