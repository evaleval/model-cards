# Model Card: Qwen1\.5\-MoE\-A2\.7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-moe\-a2\.7b\.json](<./qwen1.5-moe-a2.7b.json>)<br>
SHA-256: `f087c90137dd1b2d58f0d5b03db18864bea600b9d3efad1d2e00d281ec67a876`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-MoE\-A2\.7B |
| Name | Qwen1\.5\-MoE\-A2\.7B |
| Developed by | Qwen \(Hub organization\) |
| License | other |
| Release date | 2024\-02\-29 \(Hugging Face repository creation date\) |
| Version | 1a758c50ecb6350748b9ce0a99d2352fd9fc11c9 |
| Summary | Qwen1\.5\-MoE\-A2\.7B is a small Mixture of Experts model with 2\.7 billion activated parameters that matches the performance of state\-of\-the\-art 7B models such as Mistral 7B and Qwen1\.5\-7B\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 MoE A2\.7B |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 14,315,784,192 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 26\.7 GiB of safetensors weights \(28,632,144,944 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a base language model; the documentation advises applying post\-training such as SFT, RLHF, or continued pretraining before use for text generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 614,654 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 228 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 62\.5 | Not specified | Not reported |
| GSM8K | Not specified | 61\.5 | Not specified | Not reported |
| HumanEval | Not specified | 34\.2 | Not specified | Not reported |
| Multilingual | Not specified | 40\.8 | Not specified | Not reported |
| MT\-Bench | Not specified | 7\.17 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-MoE\-A2\.7B](<https://huggingface.co/Qwen/Qwen1.5-MoE-A2.7B>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides no documentation of model design, development, training data, or evaluation details beyond architecture and parameter count\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states it is a base model and advises applying post\-training before use, but does not define intended uses or downstream tasks\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not describe training or tuning dataset details, collection, or curation\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | Card advises applying post\-training such as SFT, RLHF, or continued pretraining before text generation, so using it directly for generation would be improper\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
