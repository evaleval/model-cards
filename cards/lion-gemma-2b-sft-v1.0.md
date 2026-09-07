# Model Card: LION\-Gemma\-2b\-sft\-v1\.0

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [lion\-gemma\-2b\-sft\-v1\.0\.json](<./lion-gemma-2b-sft-v1.0.json>)<br>
SHA-256: `3aa14a7bb9cd663bafa6dc1782f1d58298aa3e23c070c16af0d26752c51356db`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Columbia\-NLP/LION\-Gemma\-2b\-sft\-v1\.0 |
| Name | LION\-Gemma\-2b\-sft\-v1\.0 |
| Developed by | Columbia\-NLP \(Hub organization\) |
| Release date | 2024\-07\-02 \(Hugging Face repository creation date\) |
| Version | 5dee5c19a9df145f244a0adf29df025443945c47 |
| Summary | A Gemma\-2b model fine\-tuned with supervised fine\-tuning from the LION pipeline\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | LION Gemma v1\.0 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 2,506,172,416 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 4\.7 GiB of safetensors weights \(5,012,363,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | LION\-Gemma\-2b\-sft\-v1\.0 is a supervised fine\-tuned version of gemma\-2b, produced through the LION pipeline\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 38 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that LION\-Gemma\-2b\-sft\-v1\.0 achieves scores of 2\.4 on Arena\-Hard, 7\.79 on AlpacaEval\-2, 6\.37 on MT\-Bench, and 54\.78 on OpenLLM\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Arena\-Hard | Not specified | 2\.4 | Not specified | Not reported |
| AlpacaEval\-2 | Not specified | 7\.79 | Not specified | Not reported |
| MT\-Bench | Not specified | 6\.37 | Not specified | Not reported |
| OpenLLM | Not specified | 54\.78 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Columbia\-NLP/LION\-Gemma\-2b\-sft\-v1\.0](<https://huggingface.co/Columbia-NLP/LION-Gemma-2b-sft-v1.0>) |
| Code repository | [https://github\.com/Columbia\-NLP\-Lab/LionAlignment](<https://github.com/Columbia-NLP-Lab/LionAlignment>) |
| Citation | @misc\{yu2024lionsempiricallyoptimizedapproach,<br>      title=\{LIONs: An Empirically Optimized Approach to Align Language Models\}, <br>      author=\{Xiao Yu and Qingyang Wu and Yu Li and Zhou Yu\},<br>      year=\{2024\},<br>      eprint=\{2407\.06542\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2407\.06542\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only benchmark scores and the fact of SFT via the LION pipeline, with no documentation of training data, curation, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not state how the fine\-tuning data was collected, curated, or used, so the behavior of the model cannot be satisfactorily explained\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | The card reports only generic benchmark scores and no information about the fine\-tuning data distribution, so it is plausible that the SFT data is not representative of all real\-world uses\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Lack of testing diversity](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-testing-diversity.html>) | The card reports only standard text benchmarks \(Arena\-Hard, AlpacaEval\-2, MT\-Bench, OpenLLM\) and no socio\-technical or diverse testing practices\. | AI model risks are socio\-technical, so their testing needs input from a broad set of disciplines and diverse testing practices\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
