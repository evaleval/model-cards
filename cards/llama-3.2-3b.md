# Model Card: Llama\-3\.2\-3B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.2\-3b\.json](<./llama-3.2-3b.json>)<br>
SHA-256: `cc2196de430b2ce5d6706987e9479b81ac4616d4cb1c659d7d21029369ba44ac`

## Identity

| Field | Value |
| --- | --- |
| Model ID | meta\-llama/Llama\-3\.2\-3B |
| Name | Llama\-3\.2\-3B |
| Developed by | meta\-llama \(Hub organization\) |
| License | llama3\.2 |
| Release date | 2024\-09\-18 \(Hugging Face repository creation date\) |
| Version | 13afe5124825b4f3751f836b40dafda64c1ed062 |
| Summary | A multilingual generative language model in the Llama 3\.2 collection, available in pretrained and instruction\-tuned variants\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Llama 3\.2 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 3,212,749,824 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 6\.0 GiB of safetensors weights \(6,425,529,048 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 355,042 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 909 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer states that this model outperforms many available open\-source and closed chat models on common industry benchmarks\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | accuracy | 58 | 5\-shot | Not reported |
| MMLU | accuracy | 54\.5 | 5\-shot | Not reported |
| AGIEval English | accuracy | 39\.2 | 3\-5 shot | Not reported |
| ARC\-Challenge | accuracy | 69\.1 | 25\-shot | Not reported |
| SQuAD | exact match | 67\.7 | 1\-shot | Not reported |
| QuAC | F1 | 42\.9 | 1\-shot | Not reported |
| DROP | F1 | 45\.2 | 3\-shot | Not reported |
| Needle in Haystack | exact match | 1 | 0\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/meta\-llama/Llama\-3\.2\-3B](<https://huggingface.co/meta-llama/Llama-3.2-3B>) |
| Code repository | [https://github\.com/meta\-llama/llama](<https://github.com/meta-llama/llama>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark outperformance and gated access, with no documentation of design, training data, or evaluation process for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not state training or tuning dataset details for Llama\-3\.2\-3B, so data collection and composition are undocumented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card describes a general multilingual text model with no stated intended\-use or deployment scope, leaving downstream risk definitions open\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
