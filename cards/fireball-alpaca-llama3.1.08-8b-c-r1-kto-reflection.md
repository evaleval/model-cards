# Model Card: Fireball\-Alpaca\-Llama3\.1\.08\-8B\-C\-R1\-KTO\-Reflection

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [fireball\-alpaca\-llama3\.1\.08\-8b\-c\-r1\-kto\-reflection\.json](<./fireball-alpaca-llama3.1.08-8b-c-r1-kto-reflection.json>)<br>
SHA-256: `206f934a5b94dca89c83363ee72a539bd7f60d6575e1e843a1b3f8789ee8d357`

## Identity

| Field | Value |
| --- | --- |
| Model ID | EpistemeAI2/Fireball\-Alpaca\-Llama3\.1\.08\-8B\-C\-R1\-KTO\-Reflection |
| Name | Fireball\-Alpaca\-Llama3\.1\.08\-8B\-C\-R1\-KTO\-Reflection |
| Developed by | EpistemeAI2 \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-09\-16 \(Hugging Face repository creation date\) |
| Version | 468c9458dce005e173f6bf7aa60a7d2b5aa957f1 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | EpistemeAI/Fireball\-Alpaca\-Llama3\.1\.08\-8B\-Philos\-C\-R1\-KTO\-beta (base model; Kind: finetune) |

## Specifications

| Field | Value |
| --- | --- |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on a reflection dataset, with thanks to Glaive AI, and also underwent experimental KTO fine\-tuning using the argilla/distilabel\-intel\-orca\-kto dataset\. |
| Adaptations | The model was fine\-tuned using SFT \(supervised fine\-tuning\) followed by KTO \(Kahneman\-Tversky Optimization\), a method described as making alignment easier and cheaper without compromising performance\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 0 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/EpistemeAI2/Fireball\-Alpaca\-Llama3\.1\.08\-8B\-C\-R1\-KTO\-Reflection](<https://huggingface.co/EpistemeAI2/Fireball-Alpaca-Llama3.1.08-8B-C-R1-KTO-Reflection>) |
| Code repository | [https://github\.com/meta\-llama/llama3](<https://github.com/meta-llama/llama3>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card mentions fine\-tuning on a reflection dataset with thanks to Glaive AI and experimental KTO on argilla/distilabel\-intel\-orca\-kto, but gives no details on collection, ownership, or generation of these datasets\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card states training data sources only by name/thanks and does not document how the reflection or KTO datasets were collected, curated, or generated\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides no evaluation results, no training details beyond SFT\+KTO, and no insight into model behavior or limitations\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not define intended use or out\-of\-scope uses, only modalities and license\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.num_parameters`, `specifications.context_length`, `specifications.precision`, `specifications.model_size`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
