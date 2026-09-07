# Model Card: Qwen1\.5\-1\.8B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-1\.8b\.json](<./qwen1.5-1.8b.json>)<br>
SHA-256: `f2d89229ed7fb6638d356a2ff730e1e390a02d6acc8e42ca5297ca540b99013d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-1\.8B |
| Name | Qwen1\.5\-1\.8B |
| Developed by | Qwen \(Hub organization\) |
| License | other |
| Release date | 2024\-01\-22 \(Hugging Face repository creation date\) |
| Version | 7846de7ed421727b318d6605a0bfab659da2c067 |
| Summary | Qwen1\.5 is a family of open\-source base and chat language models available in multiple sizes, including the 1\.8B variant\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,836,828,672 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 3\.4 GiB of safetensors weights \(3,673,690,696 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 14,628 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 59 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen1\.5\-1\.8B achieves scores of 46\.8 on MMLU, 59\.7 on C\-Eval, 38\.4 on GSM8K, 10\.1 on MATH, 20\.1 on HumanEval, 18\.0 on MBPP, 24\.2 on BBH, and 57\.8 on CMMLU\. Additional reported results include 33\.57 on Exams, 48\.37 on Understanding, 6\.47 on Math, and 16\.19 on Translation\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 46\.8 | Not specified | Not reported |
| C\-Eval | Not specified | 59\.7 | Not specified | Not reported |
| GSM8K | Not specified | 38\.4 | Not specified | Not reported |
| MATH | Not specified | 10\.1 | Not specified | Not reported |
| Math | Not specified | 6\.47 | Not specified | Not reported |
| HumanEval | Not specified | 20\.1 | Not specified | Not reported |
| MBPP | Not specified | 18\.0 | Not specified | Not reported |
| BBH | Not specified | 24\.2 | Not specified | Not reported |
| CMMLU | Not specified | 57\.8 | Not specified | Not reported |
| Exams | Not specified | 33\.57 | Not specified | Not reported |
| Understanding | Not specified | 48\.37 | Not specified | Not reported |
| Translation | Not specified | 16\.19 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-1\.8B](<https://huggingface.co/Qwen/Qwen1.5-1.8B>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |
| Citation | @article\{qwen,<br>  title=\{Qwen Technical Report\},<br>  author=\{Jinze Bai and Shuai Bai and Yunfei Chu and Zeyu Cui and Kai Dang and Xiaodong Deng and Yang Fan and Wenbin Ge and Yu Han and Fei Huang and Binyuan Hui and Luo Ji and Mei Li and Junyang Lin and Runji Lin and Dayiheng Liu and Gao Liu and Chengqiang Lu and Keming Lu and Jianxin Ma and Rui Men and Xingzhang Ren and Xuancheng Ren and Chuanqi Tan and Sinan Tan and Jianhong Tu and Peng Wang and Shijie Wang and Wei Wang and Shengguang Wu and Benfeng Xu and Jin Xu and An Yang and Hao Yang and Jian Yang and Shusheng Yang and Yang Yao and Bowen Yu and Hongyi Yuan and Zheng Yuan and Jianwei Zhang and Xingxuan Zhang and Yichang Zhang and Zhenru Zhang and Chang Zhou and Jingren Zhou and Xiaohuan Zhou and Tianhang Zhu\},<br>  journal=\{arXiv preprint arXiv:2309\.16609\},<br>  year=\{2023\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark scores and basic architecture, with no documentation of design, development, training data, or evaluation process for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not describe training or fine\-tuning dataset details for Qwen1\.5\-1\.8B, so training data composition and curation are undocumented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only text input/output and open\-weight access, without specifying intended use or deployment context, so relevant risks are undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
