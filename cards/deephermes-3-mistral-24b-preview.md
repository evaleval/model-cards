# Model Card: DeepHermes 3 \- Mistral 24B Preview

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deephermes\-3\-mistral\-24b\-preview\.json](<./deephermes-3-mistral-24b-preview.json>)<br>
SHA-256: `5b1683d6e6b897cdcd9f2282ccbc3b8a4e69ec276f9a79bb0c3c563e9108c7ca`

## Identity

| Field | Value |
| --- | --- |
| Model ID | NousResearch/DeepHermes\-3\-Mistral\-24B\-Preview |
| Name | DeepHermes 3 \- Mistral 24B Preview |
| Developed by | NousResearch \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-03\-02 \(Hugging Face repository creation date\) |
| Version | 48072dc6c0594a3198eb862c13613c4ab1119009 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | mistralai/Mistral\-Small\-24B\-Base\-2501 (base model; Kind: finetune) |
| Model family | DeepHermes 3 Mistral |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 23,572,464,640 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 43\.9 GiB of safetensors weights \(47,144,971,752 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 690 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 124 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports improvements in LLM annotation, judgement, and function calling\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/NousResearch/DeepHermes\-3\-Mistral\-24B\-Preview](<https://huggingface.co/NousResearch/DeepHermes-3-Mistral-24B-Preview>) |
| Code repository | [https://github\.com/NousResearch/Hermes\-Function\-Calling](<https://github.com/NousResearch/Hermes-Function-Calling>) |
| Citation | @misc\{<br>      title=\{DeepHermes 3 Preview\}, <br>      author=\{Teknium and Roger Jin and Chen Guang and Jai Suphavadeeprasit and Jeffrey Quesnelle\},<br>      year=\{2025\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Function calling hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/function-calling-hallucination-agentic.html>) | The card reports improvements in function calling, but does not report any evaluation of function\-call accuracy or tool\-use safety, so the checkpoint plausibly inherits the family&\#x27;s function\-calling hallucination risk\. | AI agents might make mistakes when generating function calls \(calls to tools to execute actions\)\. Those function calls might result in incorrect, unnecessary or harmful actions\. Examples: Generating wrong functions or wrong parameters for the functions\. |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card provides only architecture, modalities, license, and reported results; it does not document training data, training procedure, or evaluation details, so model transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card does not state what data was used for training or tuning, so training/tuning dataset details are undocumented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card does not describe the origin or traceability of the training data, so data provenance is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete AI agent evaluation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-ai-agent-evaluation-agentic.html>) | The card reports function\-calling improvements but provides no evaluation of agentic or tool\-use performance, leaving agent evaluation incomplete\. | Evaluating the performance or accuracy or an agent is difficult because of system complexity and open\-endedness\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
