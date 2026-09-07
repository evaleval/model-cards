# Model Card: Qwen1\.5\-14B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen1\.5\-14b\.json](<./qwen1.5-14b.json>)<br>
SHA-256: `580fd1e1513c213ff6263b129294e1449b4d7b28f6a7cafc4751a5c1431ded5a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen1\.5\-14B |
| Name | Qwen1\.5\-14B |
| Developed by | Qwen \(Hub organization\) |
| License | other |
| Release date | 2024\-01\-22 \(Hugging Face repository creation date\) |
| Version | dce4b190d34470818e5bec2a92cb8233aaa02ca2 |
| Summary | Qwen1\.5 is a beta release of the Qwen2 series, comprising base and chat models in multiple sizes, including the 14B variant\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Qwen1\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,167,290,880 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 26\.4 GiB of safetensors weights \(28,334,637,304 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model is a base language model; the documentation advises applying post\-training such as SFT, RLHF, or continued pretraining before using it for text generation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 15,435 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 41 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports a range of benchmark results for Qwen1\.5\-14B, including scores for exams, understanding, math, and translation, as well as additional capability evaluations\. The model also has a chat variant with separate evaluation results, but the base model's headline results are the four benchmark scores listed in the structured field\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Exams | Not specified | 55\.72 | Not specified | Not reported |
| Understanding | Not specified | 74\.10 | Not specified | Not reported |
| Math | Not specified | 49\.93 | Not specified | Not reported |
| Translation | Not specified | 31\.69 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen1\.5\-14B](<https://huggingface.co/Qwen/Qwen1.5-14B>) |
| Code repository | [https://github\.com/QwenLM/Qwen1\.5](<https://github.com/QwenLM/Qwen1.5>) |
| Citation | @article\{qwen,<br>  title=\{Qwen Technical Report\},<br>  author=\{Jinze Bai and Shuai Bai and Yunfei Chu and Zeyu Cui and Kai Dang and Xiaodong Deng and Yang Fan and Wenbin Ge and Yu Han and Fei Huang and Binyuan Hui and Luo Ji and Mei Li and Junyang Lin and Runji Lin and Dayiheng Liu and Gao Liu and Chengqiang Lu and Keming Lu and Jianxin Ma and Rui Men and Xingzhang Ren and Xuancheng Ren and Chuanqi Tan and Sinan Tan and Jianhong Tu and Peng Wang and Shijie Wang and Wei Wang and Shengguang Wu and Benfeng Xu and Jin Xu and An Yang and Hao Yang and Jian Yang and Shusheng Yang and Yang Yao and Bowen Yu and Hongyi Yuan and Zheng Yuan and Jianwei Zhang and Xingxuan Zhang and Yichang Zhang and Zhenru Zhang and Chang Zhou and Jingren Zhou and Xiaohuan Zhou and Tianhang Zhu\},<br>  journal=\{arXiv preprint arXiv:2309\.16609\},<br>  year=\{2023\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only benchmark scores and gives no details on training data, architecture internals, or evaluation methodology for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Base model card advises applying post\-training before text generation, so intended use is not fully defined for this checkpoint\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not document training or tuning dataset details for Qwen1\.5\-14B\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Poor model accuracy](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/poor-model-accuracy.html>) | Card reports only a limited set of benchmark scores and no task\-specific accuracy evidence, so performance sufficiency is not established\. | Poor model accuracy occurs when a model's performance is insufficient to the task it was designed for\. Low accuracy might occur if the model is not correctly engineered, or if the model's expected inputs change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
