# Model Card: Qwen1\.5\-32B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-32b\.json](<./qwen1.5-32b.json>)<br>
SHA-256: `5de713f4a1898bdec0945a9f7cfcadbc08d4c6f0bff724798e96c3a7d5450620`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-32B |
| Name | Qwen1\.5\-32B |
| Developed by | Qwen \(Hub organization\) |
| License | other |
| Release date | 2024\-04\-01 \(Hugging Face repository creation date\) |
| Version | cefef80dc06a65f89d1d71d0adbc56d335ca2490 |
| Summary | Qwen1\.5 is a series of decoder\-only language models available in multiple sizes, including the 32B variant\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 32,512,218,112 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 60\.6 GiB of safetensors weights \(65,024,525,272 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a base language model and is not intended for direct text generation; the documentation recommends applying post\-training techniques such as SFT, RLHF, or continued pretraining before use\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 10,012 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 85 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-32B](<https://huggingface.co/Qwen/Qwen1.5-32B>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |
| Citation | @article\{qwen,<br>  title=\{Qwen Technical Report\},<br>  author=\{Jinze Bai and Shuai Bai and Yunfei Chu and Zeyu Cui and Kai Dang and Xiaodong Deng and Yang Fan and Wenbin Ge and Yu Han and Fei Huang and Binyuan Hui and Luo Ji and Mei Li and Junyang Lin and Runji Lin and Dayiheng Liu and Gao Liu and Chengqiang Lu and Keming Lu and Jianxin Ma and Rui Men and Xingzhang Ren and Xuancheng Ren and Chuanqi Tan and Sinan Tan and Jianhong Tu and Peng Wang and Shijie Wang and Wei Wang and Shengguang Wu and Benfeng Xu and Jin Xu and An Yang and Hao Yang and Jian Yang and Shusheng Yang and Yang Yao and Bowen Yu and Hongyi Yuan and Zheng Yuan and Jianwei Zhang and Xingxuan Zhang and Yichang Zhang and Zhenru Zhang and Chang Zhou and Jingren Zhou and Xiaohuan Zhou and Tianhang Zhu\},<br>  journal=\{arXiv preprint arXiv:2309\.16609\},<br>  year=\{2023\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, modality, and family; no design, training, or evaluation details for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states the base model is not intended for direct text generation and recommends post\-training before use, leaving intended use undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for Qwen1\.5\-32B\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | Card explicitly says the base model is not intended for direct text generation, so using it directly for generation would be improper\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
