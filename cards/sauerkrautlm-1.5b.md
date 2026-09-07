# Model Card: VAGO solutions SauerkrautLM\-1\.5b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [sauerkrautlm\-1\.5b\.json](<./sauerkrautlm-1.5b.json>)<br>
SHA-256: `d5f3bfec5667d572a184c6c11b2849cfc64230c1a6e793976526fb03d14095d7`

## Identity

| Field | Value |
| --- | --- |
| Model ID | VAGOsolutions/SauerkrautLM\-1\.5b |
| Name | VAGO solutions SauerkrautLM\-1\.5b |
| Developed by | VAGOsolutions \(Hub organization\) |
| Model type | A finetuned model based on Qwen/Qwen2\-1\.5B\. |
| License | apache\-2\.0 |
| Release date | 2024\-06\-12 \(Hugging Face repository creation date\) |
| Version | 8f5170f03e6b0355dd920adc3a7e65d0417ee14e |
| Summary | SauerkrautLM\-1\.5b is a finetuned version of Qwen/Qwen2\-1\.5B\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | SauerkrautLM |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,543,714,304 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.9 GiB of safetensors weights \(3,087,467,144 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model is a German\-language continuous pretraining of the base model, using Spectrum CPT on 25% of layers\. |
| Training data size | 6\.1 billion German tokens |
| Adaptations | The model was fine\-tuned with supervised fine\-tuning \(SFT\) on 700K samples over 3 epochs, then aligned with direct preference optimization \(DPO\) on 70K samples\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 112 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 10 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Human evaluations | The developer reports that in German RAG evaluation the model is on par with 8\-billion\-parameter models and, at 1\.5 billion parameters, is well\-suited for mobile deployment on smartphones and tablets\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/VAGOsolutions/SauerkrautLM\-1\.5b](<https://huggingface.co/VAGOsolutions/SauerkrautLM-1.5b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only high\-level training data \(German CPT, 700K SFT, 70K DPO\) and no details on data sources, curation, or evaluation methodology, so design/development transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card states German\-language continuous pretraining and SFT/DPO sample counts but does not document the training/tuning dataset contents, sources, or curation details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card does not describe where the German CPT, SFT, or DPO data came from or their usage terms, so data origin and traceability are uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | The card claims German RAG performance on par with 8B models but does not report evaluation breadth or data coverage, so generalization beyond that setting is unclear\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
