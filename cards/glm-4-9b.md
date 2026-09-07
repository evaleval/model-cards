# Model Card: GLM\-4\-9B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [glm\-4\-9b\.json](<./glm-4-9b.json>)<br>
SHA-256: `e69ce1a3d70bce11c5082cefaa0bfcd6140bdad115159ddec8e8f71ef9f27203`

## Identity

| Field | Value |
| --- | --- |
| Model ID | THUDM/glm\-4\-9b |
| Name | GLM\-4\-9B |
| Developed by | zai\-org \(Hub organization\) |
| License | other |
| Release date | 2024\-06\-04 \(Hugging Face repository creation date\) |
| Version | 8cd2b585357ba9e702647ac4e6fa4fafe5cc7bee |
| Summary | An open\-source GLM\-4 series language model released by Zhipu AI\. |

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
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | GLM\-4\-9B is the open\-source version of the latest\-generation GLM\-4 pretrained model series from Zhipu AI\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 9,768 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 144 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports benchmark results for the GLM\-4\-9B base model on several typical tasks, with scores of 74\.7 on MMLU, 77\.1 on C\-Eval, 34\.3 on GPQA, 84\.0 on GSM8K, 30\.4 on MATH, and 70\.1 on HumanEval\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 74\.7 | Not specified | Not reported |
| C\-Eval | Not specified | 77\.1 | Not specified | Not reported |
| GPQA | Not specified | 34\.3 | Not specified | Not reported |
| GSM8K | Not specified | 84\.0 | Not specified | Not reported |
| MATH | Not specified | 30\.4 | Not specified | Not reported |
| HumanEval | Not specified | 70\.1 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/THUDM/glm\-4\-9b](<https://huggingface.co/THUDM/glm-4-9b>) |
| Technical report | [https://arxiv\.org/abs/2406\.12793](<https://arxiv.org/abs/2406.12793>) |
| Code repository | [https://github\.com/THUDM/GLM\-4](<https://github.com/THUDM/GLM-4>) |
| Citation | @misc\{glm2024chatglm,<br>      title=\{ChatGLM: A Family of Large Language Models from GLM\-130B to GLM\-4 All Tools\}, <br>      author=\{Team GLM and Aohan Zeng and Bin Xu and Bowen Wang and Chenhui Zhang and Da Yin and Diego Rojas and Guanyu Feng and Hanlin Zhao and Hanyu Lai and Hao Yu and Hongning Wang and Jiadai Sun and Jiajie Zhang and Jiale Cheng and Jiayi Gui and Jie Tang and Jing Zhang and Juanzi Li and Lei Zhao and Lindong Wu and Lucen Zhong and Mingdao Liu and Minlie Huang and Peng Zhang and Qinkai Zheng and Rui Lu and Shuaiqi Duan and Shudan Zhang and Shulin Cao and Shuxun Yang and Weng Lam Tam and Wenyi Zhao and Xiao Liu and Xiao Xia and Xiaohan Zhang and Xiaotao Gu and Xin Lv and Xinghan Liu and Xinyi Liu and Xinyue Yang and Xixuan Song and Xunkai Zhang and Yifan An and Yifan Xu and Yilin Niu and Yuantao Yang and Yueyan Li and Yushi Bai and Yuxiao Dong and Zehan Qi and Zhaoyu Wang and Zhen Yang and Zhengxiao Du and Zhenyu Hou and Zihan Wang\},<br>      year=\{2024\},<br>      eprint=\{2406\.12793\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{id='cs\.CL' full\_name='Computation and Language' is\_active=True alt\_name='cmp\-lg' in\_archive='cs' is\_general=False description='Covers natural language processing\. Roughly includes material in ACM Subject Class I\.2\.7\. Note that work on artificial languages \(programming languages, logics, formal systems\) that does not explicitly address natural\-language issues broadly construed \(natural\-language processing, computational linguistics, speech, text retrieval, etc\.\) is not appropriate for this area\.'\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark scores and basic training data description; no details on design, development, or evaluation process for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card states training data only as 'open\-source version of the latest\-generation GLM\-4 pretrained model series' with no collection, curation, or composition details\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card does not specify intended or disallowed uses, despite being an open\-weight base text model that can be adapted to many downstream tasks\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
