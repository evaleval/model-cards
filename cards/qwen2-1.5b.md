# Model Card: Qwen2\-1\.5B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-1\.5b\.json](<./qwen2-1.5b.json>)<br>
SHA-256: `eb9f9de1b9fb4ebebf25b27faa5c39dfadb6b73eb0bb2dab7221d723eded768e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-1\.5B |
| Name | Qwen2\-1\.5B |
| Developed by | Qwen \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2024\-05\-31 \(Hugging Face repository creation date\) |
| Version | 8a16abf2848eda07cc5253dec660bf1ce007ad7a |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,543,714,304 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.9 GiB of safetensors weights \(3,087,467,144 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The target checkpoint is a base language model; its pretraining data is not specified for this checkpoint\. The Qwen2 family documentation states that all Qwen2 dense models except Qwen2\-0\.5B were pre\-trained on a large\-scale dataset of over 7 trillion tokens, but that statement is about the family and does not identify the target checkpoint&\#x27;s own training data\. |
| Adaptations | The model is a base language model, and the documentation advises against using base language models directly for text generation, recommending post\-training such as SFT, RLHF, or continued pretraining instead\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 119,896 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 103 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the Qwen2 family of models generally surpasses most open\-source models and remains competitive with proprietary models across benchmarks for language understanding and other capabilities\. For the 1\.5B model specifically, the reported scores include 56\.5 on MMLU, 31\.1 on HumanEval, 58\.5 on GSM8K, and 70\.6 on C\-Eval\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 56\.5 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 21\.8 | Not specified | Not reported |
| Theorem QA | Not specified | 15\.0 | Not specified | Not reported |
| HumanEval | Not specified | 31\.1 | Not specified | Not reported |
| MBPP | Not specified | 37\.4 | Not specified | Not reported |
| GSM8K | Not specified | 58\.5 | Not specified | Not reported |
| MATH | Not specified | 21\.7 | Not specified | Not reported |
| BBH | Not specified | 37\.2 | Not specified | Not reported |
| HellaSwag | Not specified | 66\.6 | Not specified | Not reported |
| Winogrande | Not specified | 66\.2 | Not specified | Not reported |
| ARC\-C | Not specified | 43\.9 | Not specified | Not reported |
| TruthfulQA | Not specified | 45\.9 | Not specified | Not reported |
| C\-Eval | Not specified | 70\.6 | Not specified | Not reported |
| CMMLU | Not specified | 70\.3 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-1\.5B](<https://huggingface.co/Qwen/Qwen2-1.5B>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card does not specify the target checkpoint&\#x27;s pretraining data; the 7T token statement is explicitly family\-scope, so the exact training data for this checkpoint is undocumented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card describes a base language model and advises against direct use for text generation, but does not define a concrete intended use or downstream task, leaving the relevant risk context unspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | The card reports text\-generation capability and benchmark scores \(e\.g\., MMLU, GSM8K\) but no factuality or grounding evaluation, so a base text\-generation model plausibly can produce factually inaccurate content\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
