# Model Card: recurrentgemma\-9b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [recurrentgemma\-9b\.json](<./recurrentgemma-9b.json>)<br>
SHA-256: `9117bffbef6ba1e67288aabcd4c5fa4267d769e77d0fbabb11abcee42d8e4aaf`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/recurrentgemma\-9b |
| Name | recurrentgemma\-9b |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2024\-06\-07 \(Hugging Face repository creation date\) |
| Version | 141ed2b60cc2096ab7064582f69ed80a7d104666 |

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
| Training data | RecurrentGemma was trained on the same data and with the same data processing as the Gemma model family\. |
| Adaptations | This is the 9B base version of RecurrentGemma, so it has not undergone task\-specific fine\-tuning or alignment beyond base pretraining\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 213 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 64 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that RecurrentGemma\-9B performs comparably to Gemma\-7B despite being trained on three times fewer tokens\. |
| Safety evaluations | The developer states that ethics and safety evaluations met internal thresholds for child safety, content safety, representational harms, memorization, and large\-scale harms\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | top\-1 | 60\.5 | 5\-shot | Not reported |
| HellaSwag | Not specified | 80\.4 | 0\-shot | Not reported |
| PIQA | Not specified | 81\.3 | 0\-shot | Not reported |
| SocialIQA | Not specified | 52\.3 | 0\-shot | Not reported |
| BoolQ | Not specified | 80\.3 | 0\-shot | Not reported |
| WinoGrande | score | 73\.6 | Not specified | Not reported |
| CommonsenseQA | Not specified | 73\.2 | 7\-shot | Not reported |
| TriviaQA | Not specified | 70\.5 | 5\-shot | Not reported |
| Natural Questions | Not specified | 21\.7 | 5\-shot | Not reported |
| HumanEval | pass@1 | 31\.1 | Not specified | Not reported |
| MBPP | Not specified | 42\.0 | 3\-shot | Not reported |
| GSM8K | Not specified | 42\.6 | maj@1 | Not reported |
| MATH | Not specified | 23\.8 | 4\-shot | Not reported |
| RealToxicity | Not specified | 10\.3 | Not specified | Not reported |
| BOLD | Not specified | 47\.9 | Not specified | Not reported |
| CrowS\-Pairs | top\-1 | 38\.7 | Not specified | Not reported |
| BBQ Ambig | top\-1 | 95\.9 | Not specified | Not reported |
| BBQ Disambig | top\-1 | 78\.6 | Not specified | Not reported |
| Winogender | top\-1 | 59\.0 | Not specified | Not reported |
| TruthfulQA | Not specified | 47\.7 | Not specified | Not reported |
| WinoBias 12 | Not specified | 60\.6 | Not specified | Not reported |
| WinoBias 22 | Not specified | 90\.3 | Not specified | Not reported |
| Toxigen | Not specified | 64\.5 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/recurrentgemma\-9b](<https://huggingface.co/google/recurrentgemma-9b>) |
| Citation | @article\{recurrentgemma\_2024,<br>    title=\{RecurrentGemma\},<br>    url=\{\},<br>    DOI=\{\},<br>    publisher=\{Kaggle\},<br>    author=\{Griffin Team, Alexsandar Botev and Soham De and Samuel L Smith and Anushan Fernando and George\-Christian Muraru and Ruba Haroun and Leonard Berrada et al\.\},<br>    year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Membership inference attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/membership-inference-attack.html>) | Base model trained on Gemma data, gated access; no alignment, so probing outputs may reveal training\-data membership\. | A membership inference attack repeatedly queries a model to determine if a given input was part of the model&\#x27;s training\. More specifically, given a trained model and a data sample, an attacker appropriately samples the input space, observing outputs to deduce whether that sample was part of the model&\#x27;s training\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | Base text\-generation model without task\-specific fine\-tuning or alignment; no reported factual grounding, so it can produce factually inaccurate content\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
