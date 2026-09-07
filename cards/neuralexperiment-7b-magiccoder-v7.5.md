# Model Card: NeuralExperiment\-7b\-MagicCoder\-v7\.5

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [neuralexperiment\-7b\-magiccoder\-v7\.5\.json](<./neuralexperiment-7b-magiccoder-v7.5.json>)<br>
SHA-256: `e8072a2efd9516da961a2ba07ead3ac3367d7d866a51b07cd3abefb8cb6c0c97`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Kukedlc/NeuralExperiment\-7b\-MagicCoder\-v7\.5 |
| Name | NeuralExperiment\-7b\-MagicCoder\-v7\.5 |
| Developed by | Kukedlc \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-03\-07 \(Hugging Face repository creation date\) |
| Version | e8dd4d528c33695e65fdf3781f17301428114647 |
| Summary | An experimental AI model trained on three datasets for logical reasoning, mathematics, and programming\. |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,497,728 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on three datasets: microsoft/orca\-math\-word\-problems\-200k for mathematical word problems, ise\-uiuc/Magicoder\-Evol\-Instruct\-110K for code generation and understanding, and sahil2801/CodeAlpaca\-20k for programming challenges and logical reasoning\. |
| Adaptations | The fine\-tuning process started from the last layer \(layer 31\) and moved backward, using a gradually decreasing learning rate\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 8,410 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 7 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model performs well on logical puzzles and mathematical problems, particularly ones with misleading or non\-obvious solutions that it initially found difficult\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Kukedlc/NeuralExperiment\-7b\-MagicCoder\-v7\.5](<https://huggingface.co/Kukedlc/NeuralExperiment-7b-MagicCoder-v7.5>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only broad dataset names and a backward fine\-tuning schedule, with no details on evaluation methodology or inner workings, so transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names three public datasets but gives no documentation of their contents, preprocessing, or filtering, so training\-data transparency is insufficient\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not state intended or out\-of\-scope uses, despite being an open\-weight text model applicable to many tasks, so usage definition is incomplete\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Open\-weight model with no documentation of training\-data provenance or retrieval mechanisms means generated outputs cannot be traced to specific training content\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Poor model accuracy](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/poor-model-accuracy.html>) | Reported results are limited to qualitative claims about puzzles and math problems, with no quantitative accuracy or benchmark evidence, so insufficient performance validation is plausible\. | Poor model accuracy occurs when a model&\#x27;s performance is insufficient to the task it was designed for\. Low accuracy might occur if the model is not correctly engineered, or if the model&\#x27;s expected inputs change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
