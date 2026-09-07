# Model Card: Qwen1\.5\-0\.5B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-0\.5b\.json](<./qwen1.5-0.5b.json>)<br>
SHA-256: `a1ed48cf29a93a0c71e84167ade2b8bc71e697d66aca03ea0365c636112a480d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-0\.5B |
| Name | Qwen1\.5\-0\.5B |
| Developed by | Qwen \(Hub organization\) |
| Model type | Transformer\-based decoder\-only language model |
| License | other |
| Release date | 2024\-01\-22 \(Hugging Face repository creation date\) |
| Version | 8f445e3628f3500ee69f24e1303c9f10f5342a39 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 619,570,176 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 1\.2 GiB of safetensors weights \(1,239,173,352 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The base model is not recommended for direct text generation; post\-training such as SFT, RLHF, or continued pretraining is suggested before use\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 53,528 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 175 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer\-reported results for Qwen1\.5\-0\.5B show scores of 39\.2 on MMLU, 50\.5 on C\-Eval, 22\.0 on GSM8K, 3\.1 on MATH, 12\.2 on HumanEval, 6\.8 on MBPP, 18\.3 on BBH, and 46\.6 on CMMLU\. Additional reported scores include 26\.98 on Exams, 44\.08 on Understanding, 3\.13 on Math, and 9\.17 on Translation\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 39\.2 | Not specified | Not reported |
| C\-Eval | Not specified | 50\.5 | Not specified | Not reported |
| GSM8K | Not specified | 22\.0 | Not specified | Not reported |
| MATH | Not specified | 3\.1 | Not specified | Not reported |
| Math | Not specified | 3\.13 | Not specified | Not reported |
| HumanEval | Not specified | 12\.2 | Not specified | Not reported |
| MBPP | Not specified | 6\.8 | Not specified | Not reported |
| BBH | Not specified | 18\.3 | Not specified | Not reported |
| CMMLU | Not specified | 46\.6 | Not specified | Not reported |
| Exams | Not specified | 26\.98 | Not specified | Not reported |
| Understanding | Not specified | 44\.08 | Not specified | Not reported |
| Translation | Not specified | 9\.17 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-0\.5B](<https://huggingface.co/Qwen/Qwen1.5-0.5B>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |
| Citation | @article\{qwen,<br>  title=\{Qwen Technical Report\},<br>  author=\{Jinze Bai and Shuai Bai and Yunfei Chu and Zeyu Cui and Kai Dang and Xiaodong Deng and Yang Fan and Wenbin Ge and Yu Han and Fei Huang and Binyuan Hui and Luo Ji and Mei Li and Junyang Lin and Runji Lin and Dayiheng Liu and Gao Liu and Chengqiang Lu and Keming Lu and Jianxin Ma and Rui Men and Xingzhang Ren and Xuancheng Ren and Chuanqi Tan and Sinan Tan and Jianhong Tu and Peng Wang and Shijie Wang and Wei Wang and Shengguang Wu and Benfeng Xu and Jin Xu and An Yang and Hao Yang and Jian Yang and Shusheng Yang and Yang Yao and Bowen Yu and Hongyi Yuan and Zheng Yuan and Jianwei Zhang and Xingxuan Zhang and Yichang Zhang and Zhenru Zhang and Chang Zhou and Jingren Zhou and Xiaohuan Zhou and Tianhang Zhu\},<br>  journal=\{arXiv preprint arXiv:2309\.16609\},<br>  year=\{2023\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `risks.possible_risks`.
