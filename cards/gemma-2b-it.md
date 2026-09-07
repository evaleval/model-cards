# Model Card: gemma\-2b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-2b\-it\.json](<./gemma-2b-it.json>)<br>
SHA-256: `38aa4a7f6af5c0eafa6e549b6fdac2277c43ee4e9c1ecce84afd1eb91f30a7a9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-2b\-it |
| Name | gemma\-2b\-it |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2024\-02\-08 \(Hugging Face repository creation date\) |
| Version | 96988410cbdaeb8d5093d1ebdc5a8fb563e02bad |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 2,506,172,416 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 4\.7 GiB of safetensors weights \(5,012,363,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The 2B instruct version of the Gemma model was trained on a text dataset covering a wide variety of sources, totaling 6 trillion tokens\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 68,188 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 948 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports human preference win rates for the 2B instruction\-tuned model, including a 45% win rate against a 7B instruct model and a 60\.1% win rate in another comparison\. The model was also evaluated across a large collection of datasets and metrics covering different aspects of text generation\. |
| Human evaluations | The developer reports human preference evaluations for Gemma 2B IT, with a 45% win rate over Mistral v0\.2 7B Instruct and a 60\.1% win rate in another comparison\. |
| Safety evaluations | The developer states that ethics and safety evaluation results were within acceptable thresholds for internal policies covering child safety, content safety, representational harms, memorization, and large\-scale harms\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Safety | win rate | 56\.5% | Not specified | Not reported |
| Instruction Following | win rate | 41\.6% | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-2b\-it](<https://huggingface.co/google/gemma-2b-it>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only aggregate win rates and says safety results were within thresholds, without documenting model design, training\-data composition, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card says only that the 2B instruct version was trained on a 6\-trillion\-token text dataset covering a wide variety of sources, with no dataset composition, filtering, or documentation details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card does not state intended or prohibited uses for gemma\-2b\-it, so downstream risk assessment is incomplete for a general\-purpose text model\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
