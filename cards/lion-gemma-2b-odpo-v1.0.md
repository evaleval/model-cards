# Model Card: LION\-Gemma\-2b\-odpo\-v1\.0

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [lion\-gemma\-2b\-odpo\-v1\.0\.json](<./lion-gemma-2b-odpo-v1.0.json>)<br>
SHA-256: `fb2129f3d6e66cceccb8f7c0426ca2ada560883f5b128f092f3d6c52f55868b4`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Columbia\-NLP/LION\-Gemma\-2b\-odpo\-v1\.0 |
| Name | LION\-Gemma\-2b\-odpo\-v1\.0 |
| Developed by | Columbia\-NLP \(Hub organization\) |
| Release date | 2024\-06\-28 \(Hugging Face repository creation date\) |
| Version | 090d9f59c3b47ab8dd099ddd278c058aa6d2d529 |
| Summary | This model is a Gemma\-2b variant produced by the LION pipeline, fine\-tuned from an earlier DPO checkpoint using online DPO\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | LION Gemma odpo v1\.0 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 2,506,172,416 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 9\.3 GiB of safetensors weights \(10,024,708,536 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a fine\-tune of Columbia\-NLP/LION\-Gemma\-2b\-dpo\-v1\.0, trained with online DPO from the LION pipeline\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 38 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Arena\-Hard | Not specified | 5\.0 | Not specified | Not reported |
| AlpacaEval\-2 | Not specified | 9\.57 | Not specified | Not reported |
| MT\-Bench | Not specified | 6\.75 | Not specified | Not reported |
| OpenLLM | Not specified | 55\.98 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Columbia\-NLP/LION\-Gemma\-2b\-odpo\-v1\.0](<https://huggingface.co/Columbia-NLP/LION-Gemma-2b-odpo-v1.0>) |
| Code repository | [https://github\.com/Columbia\-NLP\-Lab/LionAlignment](<https://github.com/Columbia-NLP-Lab/LionAlignment>) |
| Citation | @misc\{yu2024lionsempiricallyoptimizedapproach,<br>      title=\{LIONs: An Empirically Optimized Approach to Align Language Models\}, <br>      author=\{Xiao Yu and Qingyang Wu and Yu Li and Zhou Yu\},<br>      year=\{2024\},<br>      eprint=\{2407\.06542\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2407\.06542\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only architecture, training pipeline, and base checkpoint; no reported evaluations, training\-data details, or inner\-workings documentation for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card names the base DPO checkpoint and online DPO pipeline but does not document the data used for fine\-tuning, curation, or any synthetic generation process\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not state intended uses, out\-of\-scope uses, or deployment context for this text\-to\-text model, so relevant risks are undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
