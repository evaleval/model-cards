# Model Card: Qwen2\.5\-Math\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-math\-7b\-instruct\.json](<./qwen2.5-math-7b-instruct.json>)<br>
SHA-256: `02a9ade88a07ef47dd02790102762c9ddbb0e279c75acc569371b947287693d3`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\.5\-Math\-7B\-Instruct |
| Name | Qwen2\.5\-Math\-7B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-09\-19 \(Hugging Face repository creation date\) |
| Version | ef9926d75ab1d54532f6a30dd5e760355eb9aa4d |
| Summary | Qwen2\.5\-Math\-7B\-Instruct is an instruction\-tuned model for chat, part of a math\-specialized series supporting Chinese and English with advanced mathematical reasoning\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-Math\-7B (base model; Kind: finetune) |
| Model family | Qwen2\.5 Math |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,888 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 54,407 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 90 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen2\.5\-Math\-7B\-Instruct outperforms the larger Qwen2\-Math\-Instruct 72B model\. With the help of a reward model, the 7B instruct model can solve up to 21 problems, demonstrating strong mathematical problem\-solving ability\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| ZH | Not specified | 66\.3 | Not specified | Not reported |
| ZH | Not specified | 92\.7 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\.5\-Math\-7B\-Instruct](<https://huggingface.co/Qwen/Qwen2.5-Math-7B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2409\.12122](<https://arxiv.org/abs/2409.12122>) |
| Code repository | [https://github\.com/QwenLM/Qwen2\.5\-Math](<https://github.com/QwenLM/Qwen2.5-Math>) |
| Citation | @article\{yang2024qwen25mathtechnicalreportmathematical,<br>  title=\{Qwen2\.5\-Math Technical Report: Toward Mathematical Expert Model via Self\-Improvement\}, <br>  author=\{An Yang and Beichen Zhang and Binyuan Hui and Bofei Gao and Bowen Yu and Chengpeng Li and Dayiheng Liu and Jianhong Tu and Jingren Zhou and Junyang Lin and Keming Lu and Mingfeng Xue and Runji Lin and Tianyu Liu and Xingzhang Ren and Zhenru Zhang\},<br>  journal=\{arXiv preprint arXiv:2409\.12122\},<br>  year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only benchmark\-style math problem\-solving results and gives no documentation of design, training data, or evaluation process for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card summary does not describe the training or fine\-tuning datasets used for Qwen2\.5\-Math\-7B\-Instruct\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card describes a general math chat/instruct model but does not define intended use cases or limitations, leaving downstream risk assessment underspecified\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
