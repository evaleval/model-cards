# Model Card: GLM\-4\-9B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [glm\-4\-9b\-chat\.json](<./glm-4-9b-chat.json>)<br>
SHA-256: `89d6035d661abfadbaf44fcb5cfb0265533460d7530ff211e307f7136ecde155`

## Identity

| Field | Value |
| --- | --- |
| Model ID | THUDM/glm\-4\-9b\-chat |
| Name | GLM\-4\-9B\-Chat |
| Developed by | zai\-org \(Hub organization\) |
| License | other |
| Release date | 2024\-06\-04 \(Hugging Face repository creation date\) |
| Version | bd8234fe5e0c09c48637a92abb0c797cb5fa0e73 |
| Summary | GLM\-4\-9B\-Chat is the open\-source chat version of the GLM\-4 series, released by Zhipu AI\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | glm 4 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 9,399,951,392 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 17\.5 GiB of safetensors weights \(18,799,941,256 bytes\) in BF16 |
| Input / output | Text input and text output for multi\-turn dialogue<br>Web browsing<br>Code execution<br>Custom tool calls \(Function Call\)<br>Long\-text reasoning with up to 128K context |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | GLM\-4\-9B\-Chat is described as a human\-preference\-aligned version of GLM\-4\-9B, and also supports multi\-turn dialogue, web browsing, code execution, custom tool calls, and long\-text reasoning with up to 128K context\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 87,991 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 708 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that GLM\-4\-9B and its human\-preference\-aligned version GLM\-4\-9B\-Chat show strong performance across datasets covering semantics, mathematics, reasoning, code, and knowledge\. |
| Human evaluations | The developer reports evaluations of GLM\-4\-9B\-Chat on classic tasks, long\-text ability via LongBench\-Chat, six multilingual datasets compared with Llama\-3\-8B\-Instruct, and the Berkeley Function Calling Leaderboard\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| AlignBench\-v2 | Not specified | 6\.61 | Not specified | Not reported |
| MT\-Bench | Not specified | 8\.35 | Not specified | Not reported |
| IFEval | Not specified | 69\.0 | Not specified | Not reported |
| MMLU | Not specified | 72\.4 | Not specified | Not reported |
| C\-Eval | Not specified | 75\.6 | Not specified | Not reported |
| GSM8K | Not specified | 79\.6 | Not specified | Not reported |
| HumanEval | Not specified | 71\.8 | Not specified | Not reported |
| NCB | Not specified | 32\.2 | Not specified | Not reported |
| M\-MMLU | Not specified | 56\.6 | Not specified | Not reported |
| FLORES | Not specified | 28\.8 | Not specified | Not reported |
| MGSM | Not specified | 65\.3 | Not specified | Not reported |
| XWinograd | Not specified | 73\.1 | Not specified | Not reported |
| XStoryCloze | Not specified | 90\.7 | Not specified | Not reported |
| XCOPA | Not specified | 80\.1 | Not specified | Not reported |
| Overall Acc\. | accuracy | 81\.00 | Not specified | Not reported |
| AST Summary | Not specified | 80\.26 | Not specified | Not reported |
| Exec Summary | Not specified | 84\.40 | Not specified | Not reported |
| Relevance | Not specified | 87\.92 | Not specified | Not reported |
| BBH | Not specified | 76\.3 | Not specified | Not reported |
| GPQA | Not specified | 28\.8 | Not specified | Not reported |
| Logic | Not specified | 6\.01 | Not specified | Not reported |
| Language | Not specified | 6\.69 | Not specified | Not reported |
| Chinese | Not specified | 7\.26 | Not specified | Not reported |
| QA | Not specified | 7\.97 | Not specified | Not reported |
| Writing | Not specified | 7\.59 | Not specified | Not reported |
| Role Play | Not specified | 8\.1 | Not specified | Not reported |
| Professional | Not specified | 7\.52 | Not specified | Not reported |
| Overall | Not specified | 7\.01 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/THUDM/glm\-4\-9b\-chat](<https://huggingface.co/THUDM/glm-4-9b-chat>) |
| Technical report | [https://arxiv\.org/abs/2406\.12793](<https://arxiv.org/abs/2406.12793>) |
| Code repository | [https://github\.com/THUDM/GLM\-4](<https://github.com/THUDM/GLM-4>) |
| Citation | @misc\{glm2024chatglm,<br>      title=\{ChatGLM: A Family of Large Language Models from GLM\-130B to GLM\-4 All Tools\}, <br>      author=\{Team GLM and Aohan Zeng and Bin Xu and Bowen Wang and Chenhui Zhang and Da Yin and Diego Rojas and Guanyu Feng and Hanlin Zhao and Hanyu Lai and Hao Yu and Hongning Wang and Jiadai Sun and Jiajie Zhang and Jiale Cheng and Jiayi Gui and Jie Tang and Jing Zhang and Juanzi Li and Lei Zhao and Lindong Wu and Lucen Zhong and Mingdao Liu and Minlie Huang and Peng Zhang and Qinkai Zheng and Rui Lu and Shuaiqi Duan and Shudan Zhang and Shulin Cao and Shuxun Yang and Weng Lam Tam and Wenyi Zhao and Xiao Liu and Xiao Xia and Xiaohan Zhang and Xiaotao Gu and Xin Lv and Xinghan Liu and Xinyi Liu and Xinyue Yang and Xixuan Song and Xunkai Zhang and Yifan An and Yifan Xu and Yilin Niu and Yuantao Yang and Yueyan Li and Yushi Bai and Yuxiao Dong and Zehan Qi and Zhaoyu Wang and Zhen Yang and Zhengxiao Du and Zhenyu Hou and Zihan Wang\},<br>      year=\{2024\},<br>      eprint=\{2406\.12793\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{id=&\#x27;cs\.CL&\#x27; full\_name=&\#x27;Computation and Language&\#x27; is\_active=True alt\_name=&\#x27;cmp\-lg&\#x27; in\_archive=&\#x27;cs&\#x27; is\_general=False description=&\#x27;Covers natural language processing\. Roughly includes material in ACM Subject Class I\.2\.7\. Note that work on artificial languages \(programming languages, logics, formal systems\) that does not explicitly address natural\-language issues broadly construed \(natural\-language processing, computational linguistics, speech, text retrieval, etc\.\) is not appropriate for this area\.&\#x27;\}<br>\} |

## Risks

_No AI Risk Atlas entry was selected for this checkpoint._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.safety_evals`, `links.system_card`, `risks.possible_risks`.
