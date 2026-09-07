# Model Card: Yi\-6B\-Chat

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [yi\-6b\-chat\.json](<./yi-6b-chat.json>)<br>
SHA-256: `c573bb0d2784e27abff6def8f8175e4eacee6e363185a5ed32c34af4d6d75a11`

## Identity

| Field | Value |
| --- | --- |
| Model ID | 01\-ai/Yi\-6B\-Chat |
| Name | Yi\-6B\-Chat |
| Developed by | 01\-ai \(Hub organization\) |
| Model type | Text generation\. |
| License | apache\-2\.0 |
| Release date | 2023\-11\-22 \(Hugging Face repository creation date\) |
| Version | 2dbf63b0cb7bc493c0243502c6e6111a36e3a093 |
| Summary | An open\-source large language model in the Yi series, trained from scratch by 01\.AI\. |

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
| Model size | 11\.3 GiB of safetensors weights \(12,122,104,808 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The Yi series models are bilingual language models trained on a 3T multilingual corpus\. |
| Training data size | 3T tokens |
| Data cutoff | June 2023 |
| Adaptations | The released chat model underwent supervised fine\-tuning \(SFT\)\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 29,011 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 72 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the Yi series, trained as a bilingual language model on a 3T multilingual corpus, ranks among the strongest LLMs worldwide, with strengths in language understanding, commonsense reasoning, and reading comprehension\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/01\-ai/Yi\-6B\-Chat](<https://huggingface.co/01-ai/Yi-6B-Chat>) |
| Citation | @misc\{ai2024yi,<br>    title=\{Yi: Open Foundation Models by 01\.AI\},<br>    author=\{01\. AI and : and Alex Young and Bei Chen and Chao Li and Chengen Huang and Ge Zhang and Guanwei Zhang and Heng Li and Jiangcheng Zhu and Jianqun Chen and Jing Chang and Kaidong Yu and Peng Liu and Qiang Liu and Shawn Yue and Senbin Yang and Shiming Yang and Tao Yu and Wen Xie and Wenhao Huang and Xiaohui Hu and Xiaoyi Ren and Xinyao Niu and Pengcheng Nie and Yuchi Xu and Yudong Liu and Yue Wang and Yuxuan Cai and Zhenyu Gu and Zhiyuan Liu and Zonghong Dai\},<br>    year=\{2024\},<br>    eprint=\{2403\.04652\},<br>    archivePrefix=\{arXiv\},<br>    primaryClass=\{cs\.CL\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only broad training corpus size and aggregate strengths, with no details on data sources, curation, or evaluation methodology\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card states a 3T multilingual corpus and SFT but does not document data collection, curation, or filtering for this checkpoint\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Open\-weight bilingual model trained on a 3T corpus with no traceability of data origin or usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Bilingual 3T corpus with no reported demographic or domain coverage may not represent all real\-world text populations\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Large multilingual pretraining corpus and SFT can encode societal biases, but the card reports no bias testing or mitigation\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
