# Model Card: MaziyarPanahi/calme\-3\.2\-baguette\-3b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [calme\-3\.2\-baguette\-3b\.json](<./calme-3.2-baguette-3b.json>)<br>
SHA-256: `8d14609d74fc38ad58d098bb5b1e6e7fed4a94e499951e2322c5f3cf0e5f3711`

## Identity

| Field | Value |
| --- | --- |
| Model ID | MaziyarPanahi/calme\-3\.2\-baguette\-3b |
| Name | MaziyarPanahi/calme\-3\.2\-baguette\-3b |
| Developed by | MaziyarPanahi \(Hub organization\) |
| License | other |
| Release date | 2024\-11\-07 \(Hugging Face repository creation date\) |
| Version | 55787a3c65b2dac59b6888f4878683e1d7075580 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-3B (base model; Kind: finetune) |
| Model family | calme 3\.2 baguette |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,085,383,680 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 10\.3 GiB of safetensors weights \(11,040,403,984 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned from Qwen/Qwen2\.5\-3B using the datasets MaziyarPanahi/french\_instruct\_sharegpt and MaziyarPanahi/calme\-legalkit\-v0\.2\. |
| Adaptations | The model is a fine\-tuned iteration of Qwen/Qwen2\.5\-3B, adapted to improve performance on general tasks in French and English\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 32 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer notes that this is a very small model, so performance may be limited for some prompts and it may be sensitive to hyperparameters\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/MaziyarPanahi/calme\-3\.2\-baguette\-3b](<https://huggingface.co/MaziyarPanahi/calme-3.2-baguette-3b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card gives only a brief summary and no evaluation or safety documentation for this exact checkpoint, so its design and evaluation process are insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card names two fine\-tuning datasets but does not describe how they were collected, curated, or processed, limiting transparency about training data\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Poor model accuracy](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/poor-model-accuracy.html>) | The developer notes this is a very small model with limited performance for some prompts and sensitivity to hyperparameters, indicating possible insufficient accuracy for its intended general tasks\. | Poor model accuracy occurs when a model&\#x27;s performance is insufficient to the task it was designed for\. Low accuracy might occur if the model is not correctly engineered, or if the model&\#x27;s expected inputs change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
