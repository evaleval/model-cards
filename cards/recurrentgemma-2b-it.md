# Model Card: recurrentgemma\-2b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [recurrentgemma\-2b\-it\.json](<./recurrentgemma-2b-it.json>)<br>
SHA-256: `590011da238dc61aa42559787c91a0c55ea285a59a6cb7e19235d3fb94d498bc`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/recurrentgemma\-2b\-it |
| Name | recurrentgemma\-2b\-it |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2024\-04\-08 \(Hugging Face repository creation date\) |
| Version | 2766eb5d4264c6c0357803990791f9ab9cd50f8e |
| Summary | The 2B instruction\-tuned version of the RecurrentGemma open language model family\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | recurrentgemma |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 2,682,862,080 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 5\.0 GiB of safetensors weights \(5,365,782,552 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | RecurrentGemma was trained on the same data and with the same data processing as the Gemma model family\. |
| Adaptations | This is the 2B instruction\-tuned version of RecurrentGemma\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 1,742 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 116 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that RecurrentGemma models perform on par with Gemma models while offering faster inference and lower memory use, especially for long sequences\. |
| Safety evaluations | The developer states that ethics and safety evaluation results met internal policy thresholds for categories including child safety, content safety, representational harms, memorization, and large\-scale harms\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| RealToxicity | Not specified | 7\.60 | Not specified | Not reported |
| BOLD | Not specified | 39\.8 | Not specified | Not reported |
| CrowS\-Pairs | top\-1 | 43\.4 | Not specified | Not reported |
| BBQ Ambig | top\-1 | 71\.1 | Not specified | Not reported |
| BBQ Disambig | top\-1 | 50\.8 | Not specified | Not reported |
| Winogender | top\-1 | 54\.7 | Not specified | Not reported |
| TruthfulQA | Not specified | 38\.6 | Not specified | Not reported |
| WinoBias 12 | Not specified | 61\.5 | Not specified | Not reported |
| WinoBias 22 | Not specified | 90\.2 | Not specified | Not reported |
| Toxigen | Not specified | 58\.8 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/recurrentgemma\-2b\-it](<https://huggingface.co/google/recurrentgemma-2b-it>) |
| Citation | @article\{recurrentgemma\_2024,<br>    title=\{RecurrentGemma\},<br>    url=\{\},<br>    DOI=\{\},<br>    publisher=\{Kaggle\},<br>    author=\{Griffin Team, Soham De, Samuel L Smith, Anushan Fernando, Alex Botev, George\-Christian Muraru, Ruba Haroun, Leonard Berrada et al\.\},<br>    year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Gated access and license restrict external inspection of the checkpoint, and the card does not disclose model internals or detailed evaluation data\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card only says RecurrentGemma was trained on the same data and processing as Gemma, without documenting collection, curation, or composition for this checkpoint\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card identifies the model as instruction\-tuned text\-to\-text but does not define intended or prohibited uses, leaving downstream risk scope unspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
