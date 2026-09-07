# Model Card: Yi\-6B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [yi\-6b\.json](<./yi-6b.json>)<br>
SHA-256: `b4a8443d1b0123642d11507c60e89010070d356b2bb7620beb4c3f11866af7e2`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 01\-ai/Yi\-6B |
| Name | Yi\-6B |
| Developed by | 01\-ai \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2023\-11\-01 \(Hugging Face repository creation date\) |
| Version | 80080be87ec5a0103f643195f2d9003b8068941b |
| Summary | Yi\-6B is one of the first two bilingual English/Chinese base models released in the Yi series, with 6B parameters\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | Yi series |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 6,061,035,520 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 11\.3 GiB of safetensors weights \(12,122,104,832 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The 6B model is one of two bilingual English/Chinese base models in the first public release\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 32,741 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 375 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/01\-ai/Yi\-6B](<https://huggingface.co/01-ai/Yi-6B>) |
| Citation | @misc\{ai2024yi,<br>    title=\{Yi: Open Foundation Models by 01\.AI\},<br>    author=\{01\. AI and : and Alex Young and Bei Chen and Chao Li and Chengen Huang and Ge Zhang and Guanwei Zhang and Heng Li and Jiangcheng Zhu and Jianqun Chen and Jing Chang and Kaidong Yu and Peng Liu and Qiang Liu and Shawn Yue and Senbin Yang and Shiming Yang and Tao Yu and Wen Xie and Wenhao Huang and Xiaohui Hu and Xiaoyi Ren and Xinyao Niu and Pengcheng Nie and Yuchi Xu and Yudong Liu and Yue Wang and Yuxuan Cai and Zhenyu Gu and Zhiyuan Liu and Zonghong Dai\},<br>    year=\{2024\},<br>    eprint=\{2403\.04652\},<br>    archivePrefix=\{arXiv\},<br>    primaryClass=\{cs\.CL\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, parameter count, and bilingual base\-model status; no training\-data details, evaluation results, or design/development process are documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card states training data only as &\#x27;bilingual English/Chinese base models&\#x27; with no dataset composition, collection, curation, or filtering details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Open\-weight bilingual base model with no stated data sources or traceability for the English/Chinese training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Base text\-generation model with no documentation of training\-data content, so outputs cannot be traced back to specific sources\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card lists only &\#x27;text\-generation&\#x27; as the primary task and gives no intended\-use or misuse guidance for this open\-weight base model\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
