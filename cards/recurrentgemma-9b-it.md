# Model Card: recurrentgemma\-9b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [recurrentgemma\-9b\-it\.json](<./recurrentgemma-9b-it.json>)<br>
SHA-256: `ba218b6a026123efb55286d29d16ec8ddc249a0bc7e714e51cf40c38ee796a5f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/recurrentgemma\-9b\-it |
| Name | recurrentgemma\-9b\-it |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2024\-06\-07 \(Hugging Face repository creation date\) |
| Version | c079e8183308ba41c6f9454291d27a16bc0bbb23 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | recurrentgemma |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 9,628,553,216 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 17\.9 GiB of safetensors weights \(19,257,191,752 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is the 9B instruction version of RecurrentGemma, indicating instruction tuning was applied\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 374 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 55 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that ethics and safety evaluation results fall within acceptable thresholds for internal policies covering child safety, content safety, representational harms, memorization, and large\-scale harms\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Safety | win rate | 59\.9% | Not specified | Not reported |
| Instruction Following | win rate | 59\.3% | Not specified | Not reported |
| BOLD | score | 39\.8 | Not specified | Not reported |
| BOLD | score | 47\.9 | Not specified | Not reported |
| TruthfulQA | score | 38\.6 | Not specified | Not reported |
| TruthfulQA | score | 47\.7 | Not specified | Not reported |
| Winobias 12 | score | 61\.5 | Not specified | Not reported |
| Winobias 12 | score | 60\.6 | Not specified | Not reported |
| Winobias 22 | score | 90\.2 | Not specified | Not reported |
| Winobias 22 | score | 90\.3 | Not specified | Not reported |
| Toxigen | score | 58\.8 | Not specified | Not reported |
| Toxigen | score | 64\.5 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/recurrentgemma\-9b\-it](<https://huggingface.co/google/recurrentgemma-9b-it>) |
| Citation | @article\{recurrentgemma\_2024,<br>    title=\{RecurrentGemma\},<br>    url=\{\},<br>    DOI=\{\},<br>    publisher=\{Kaggle\},<br>    author=\{Griffin Team, Soham De, Samuel L Smith, Anushan Fernando, Alex Botev, George\-Christian Muraru, Ruba Haroun, Leonard Berrada et al\.\},<br>    year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | The card is for an instruction\-tuned 9B text model with gated access and no stated use\-case restrictions, so it could plausibly be used for purposes beyond its intended design\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | The model is a text\-input, text\-output instruction\-tuned model with gated access; users may send prompts containing confidential information, and the card does not report any mitigation for prompt data handling\. | Confidential information might be included as a part of the prompt that is sent to the model\. |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | As a text instruction model, users can include copyrighted or otherwise protected text in prompts, and the card does not report any filtering or safeguards against such input\. | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Data privacy rights alignment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-privacy-rights.html>) | The card reports memorization evaluation but does not describe data\-subject rights mechanisms, so the text model may reproduce or process personal information from training data in ways that implicate privacy rights\. | Applicable laws can establish data subject rights such as opt\-out rights, right to access, and right to be forgotten\. Synthetic data might raise unique concerns, such as the potential for reidentification of individuals from seemingly anonymous synthetic data\. Data subject rights might also be relevant in scenarios where synthetic data is derived from sensitive or personal information\. |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | The card provides limited documentation \(no training\-data details or governance process\) and uses a gated license, making accountability for model outputs and development choices harder to establish\. | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
