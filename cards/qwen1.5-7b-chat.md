# Model Card: Qwen1\.5\-7B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-7b\-chat\.json](<./qwen1.5-7b-chat.json>)<br>
SHA-256: `748065d672269dac9af3b271fd4514dfb79f6fd731bc50970213071076190e9c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-7B\-Chat |
| Name | Qwen1\.5\-7B\-Chat |
| Developed by | Qwen \(Hub organization\) |
| Model type | A transformer\-based decoder\-only language model\. |
| License | other |
| Release date | 2024\-01\-30 \(Hugging Face repository creation date\) |
| Version | 5f4f5e69ac7f1d508f8369e977de208b4803444b |
| Summary | Qwen1\.5 is a language model series that includes decoder\-only language models of different sizes, with both base and chat variants released\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,721,324,544 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.4 GiB of safetensors weights \(15,442,693,552 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 16,449 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 186 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 61\.0 | Not specified | Not reported |
| C\-Eval | Not specified | 74\.1 | Not specified | Not reported |
| GSM8K | Not specified | 62\.5 | Not specified | Not reported |
| MATH | Not specified | 20\.3 | Not specified | Not reported |
| HumanEval | Not specified | 36\.0 | Not specified | Not reported |
| MBPP | Not specified | 37\.4 | Not specified | Not reported |
| BBH | Not specified | 40\.2 | Not specified | Not reported |
| CMMLU | Not specified | 73\.1 | Not specified | Not reported |
| Coursera | Not specified | 59\.74 | Not specified | Not reported |
| GSM | Not specified | 60\.00 | Not specified | Not reported |
| QuALITY | Not specified | 64\.36 | Not specified | Not reported |
| TOEFL | Not specified | 79\.18 | Not specified | Not reported |
| SFiction | Not specified | 62\.50 | Not specified | Not reported |
| Avg\. | Not specified | 65\.16 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-7B\-Chat](<https://huggingface.co/Qwen/Qwen1.5-7B-Chat>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |
| Citation | @article\{qwen,<br>  title=\{Qwen Technical Report\},<br>  author=\{Jinze Bai and Shuai Bai and Yunfei Chu and Zeyu Cui and Kai Dang and Xiaodong Deng and Yang Fan and Wenbin Ge and Yu Han and Fei Huang and Binyuan Hui and Luo Ji and Mei Li and Junyang Lin and Runji Lin and Dayiheng Liu and Gao Liu and Chengqiang Lu and Keming Lu and Jianxin Ma and Rui Men and Xingzhang Ren and Xuancheng Ren and Chuanqi Tan and Sinan Tan and Jianhong Tu and Peng Wang and Shijie Wang and Wei Wang and Shengguang Wu and Benfeng Xu and Jin Xu and An Yang and Hao Yang and Jian Yang and Shusheng Yang and Yang Yao and Bowen Yu and Hongyi Yuan and Zheng Yuan and Jianwei Zhang and Xingxuan Zhang and Yichang Zhang and Zhenru Zhang and Chang Zhou and Jingren Zhou and Xiaohuan Zhou and Tianhang Zhu\},<br>  journal=\{arXiv preprint arXiv:2309\.16609\},<br>  year=\{2023\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `risks.possible_risks`.
