# Model Card: OpenMath2\-Llama3\.1\-8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [openmath2\-llama3\.1\-8b\.json](<./openmath2-llama3.1-8b.json>)<br>
SHA-256: `e60f35aa0e199cff919621d34225765508a58000ccd00c25f64f84c7ffdb8a39`

## Identity

| Field | Value |
| --- | --- |
| Model ID | nvidia/OpenMath2\-Llama3\.1\-8B |
| Name | OpenMath2\-Llama3\.1\-8B |
| Developed by | nvidia \(Hub organization\) |
| License | llama3\.1 |
| Release date | 2024\-09\-30 \(Hugging Face repository creation date\) |
| Version | 0f9db814ea4acd66485b9e6679b3e58df8663875 |
| Summary | OpenMath2\-Llama3\.1\-8B is a math\-focused language model created by fine\-tuning Llama 3\.1 8B Base on the OpenMathInstruct\-2 dataset\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | meta\-llama/Llama\-3\.1\-8B (base model; Kind: finetune) |
| Model family | OpenMath2 Llama3\.1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,400 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | OpenMath2\-Llama3\.1\-8B is a fine\-tune of Llama3\.1\-8B\-Base on OpenMathInstruct\-2\. |
| Adaptations | The model was produced by fine\-tuning Llama3\.1\-8B\-Base with OpenMathInstruct\-2\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,631 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 33 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/nvidia/OpenMath2\-Llama3\.1\-8B](<https://huggingface.co/nvidia/OpenMath2-Llama3.1-8B>) |
| Code repository | [https://github\.com/meta\-llama/llama\-models](<https://github.com/meta-llama/llama-models>) |
| Citation | @article\{toshniwal2024openmath2,<br>  title   = \{OpenMathInstruct\-2: Accelerating AI for Math with Massive Open\-Source Instruction Data\},<br>  author  = \{Shubham Toshniwal and Wei Du and Ivan Moshkov and  Branislav Kisacanin and Alexan Ayrapetyan and Igor Gitman\},<br>  year    = \{2024\},<br>  journal = \{arXiv preprint arXiv:2410\.01560\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, base model, and dataset name; no training details, evaluation results, or intended\-use documentation are provided\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names OpenMathInstruct\-2 but gives no dataset composition, filtering, or synthetic\-data generation details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not state intended use, misuse, or deployment context for the math\-focused model\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
