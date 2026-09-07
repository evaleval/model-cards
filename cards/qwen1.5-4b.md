# Model Card: Qwen1\.5\-4B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-4b\.json](<./qwen1.5-4b.json>)<br>
SHA-256: `38d0759677db932c8e4e66126984d27d3152de341711262ee2ac569638a7a553`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-4B |
| Name | Qwen1\.5\-4B |
| Developed by | Qwen \(Hub organization\) |
| License | other |
| Release date | 2024\-01\-22 \(Hugging Face repository creation date\) |
| Version | a66363a0c24e2155c561e4b53c658b1d3965474e |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 3,950,369,280 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 7\.4 GiB of safetensors weights \(7,900,793,992 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a base language model, and the documentation advises applying post\-training techniques such as SFT, RLHF, or continued pretraining before using it for text generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 19,205 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 37 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 56\.1 | Not specified | Not reported |
| C\-Eval | Not specified | 67\.6 | Not specified | Not reported |
| GSM8K | Not specified | 57\.0 | Not specified | Not reported |
| MATH | Not specified | 10\.0 | Not specified | Not reported |
| Math | Not specified | 21\.33 | Not specified | Not reported |
| HumanEval | Not specified | 25\.6 | Not specified | Not reported |
| MBPP | Not specified | 29\.2 | Not specified | Not reported |
| BBH | Not specified | 32\.5 | Not specified | Not reported |
| CMMLU | Not specified | 66\.7 | Not specified | Not reported |
| Exams | Not specified | 41\.43 | Not specified | Not reported |
| Understanding | Not specified | 59\.76 | Not specified | Not reported |
| Translation | Not specified | 23\.34 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-4B](<https://huggingface.co/Qwen/Qwen1.5-4B>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |
| Citation | @article\{qwen,<br>  title=\{Qwen Technical Report\},<br>  author=\{Jinze Bai and Shuai Bai and Yunfei Chu and Zeyu Cui and Kai Dang and Xiaodong Deng and Yang Fan and Wenbin Ge and Yu Han and Fei Huang and Binyuan Hui and Luo Ji and Mei Li and Junyang Lin and Runji Lin and Dayiheng Liu and Gao Liu and Chengqiang Lu and Keming Lu and Jianxin Ma and Rui Men and Xingzhang Ren and Xuancheng Ren and Chuanqi Tan and Sinan Tan and Jianhong Tu and Peng Wang and Shijie Wang and Wei Wang and Shengguang Wu and Benfeng Xu and Jin Xu and An Yang and Hao Yang and Jian Yang and Shusheng Yang and Yang Yao and Bowen Yu and Hongyi Yuan and Zheng Yuan and Jianwei Zhang and Xingxuan Zhang and Yichang Zhang and Zhenru Zhang and Chang Zhou and Jingren Zhou and Xiaohuan Zhou and Tianhang Zhu\},<br>  journal=\{arXiv preprint arXiv:2309\.16609\},<br>  year=\{2023\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only minimal architecture/modality/access info and no design, training, or evaluation details for Qwen1\.5\-4B\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card describes a base model and advises post\-training before text generation, but does not define intended uses or downstream risk contexts\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training dataset details, collection, curation, or synthetic data generation for this checkpoint\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | Open\-weight checkpoint card gives no access to training data, limiting explainability of outputs\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No documentation of how training data was collected, curated, or used is stated in the card\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
