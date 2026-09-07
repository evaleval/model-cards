# Model Card: DeepSeek\-V3

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-v3\.json](<./deepseek-v3.json>)<br>
SHA-256: `3f965263e48d047d949ae4fabb3eb0b97bc1ec1a524c1225fd56c38aa8c7bdef`

## Identity

| Field | Value |
| --- | --- |
| Model ID | deepseek\-ai/DeepSeek\-V3 |
| Name | DeepSeek\-V3 |
| Developed by | deepseek\-ai \(Hub organization\) |
| Model type | Mixture\-of\-Experts \(MoE\) language model |
| Release date | 2024\-12\-25 \(Hugging Face repository creation date\) |
| Version | e815299b0bcbac849fa540c768ef21845365c9eb |
| Summary | DeepSeek\-V3 is a large Mixture\-of\-Experts language model with 671B total parameters and 37B activated per token\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | DeepSeek V3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 684,531,386,000 parameters \(safetensors metadata\) |
| Context length | 163,840 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F8\_E4M3 \(safetensors weight dtype\) |
| Model size | 641\.3 GiB of safetensors weights \(688,586,727,753 bytes\) in F8\_E4M3 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | 14\.8 trillion tokens |
| Adaptations | DeepSeek\-V3 underwent supervised fine\-tuning and reinforcement learning after pre\-training\. It also incorporated the FIM strategy during pre\-training, and reasoning capabilities were distilled from a DeepSeek R1 series model into DeepSeek\-V3, incorporating verification and reflection patterns\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 1,039,268 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 4,180 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | DeepSeek\-V3 is reported to outperform other open\-source models and to be competitive with leading closed\-source models across comprehensive evaluations\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | exact match | 88\.5 | Not specified | Not reported |
| MMLU\-Redux | exact match | 89\.1 | Not specified | Not reported |
| MMLU\-Pro | exact match | 75\.9 | Not specified | Not reported |
| DROP | F1 | 91\.6 | 3\-shot | Not reported |
| IF\-Eval | Not specified | 86\.1 | Not specified | Not reported |
| GPQA\-Diamond | pass@1 | 59\.1 | Not specified | Not reported |
| SimpleQA | Not specified | 24\.9 | Not specified | Not reported |
| FRAMES | accuracy | 73\.3 | Not specified | Not reported |
| LongBench v2 | accuracy | 48\.7 | Not specified | Not reported |
| HumanEval\-Mul | pass@1 | 82\.6 | Not specified | Not reported |
| LiveCodeBench | pass@1 | 40\.5 | COT | Not reported |
| LiveCodeBench | pass@1 | 37\.6 | Not specified | Not reported |
| Codeforces | Not specified | 51\.6 | Not specified | Not reported |
| SWE Verified | Not specified | 42\.0 | Not specified | Not reported |
| Aider\-Edit | accuracy | 79\.7 | Not specified | Not reported |
| Aider\-Polyglot | accuracy | 49\.6 | Not specified | Not reported |
| AIME 2024 | pass@1 | 39\.2 | Not specified | Not reported |
| MATH\-500 | exact match | 90\.2 | Not specified | Not reported |
| CNMO 2024 | pass@1 | 43\.2 | Not specified | Not reported |
| CLUEWSC | exact match | 90\.9 | Not specified | Not reported |
| C\-Eval | exact match | 86\.5 | Not specified | Not reported |
| C\-SimpleQA | Not specified | 64\.8 | Not specified | Not reported |
| Arena\-Hard | Not specified | 85\.5 | Not specified | Not reported |
| AlpacaEval 2\.0 | Not specified | 70\.0 | Not specified | Not reported |
| CNMO2024 | pass@1 | 43\.2 | Not specified | Not reported |
| Chat | Not specified | 96\.9 | Not specified | Not reported |
| Chat\-Hard | Not specified | 79\.8 | Not specified | Not reported |
| Safety | Not specified | 87 | Not specified | Not reported |
| Reasoning | Not specified | 84\.3 | Not specified | Not reported |
| Average | Not specified | 87 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/deepseek\-ai/DeepSeek\-V3](<https://huggingface.co/deepseek-ai/DeepSeek-V3>) |
| Technical report | [https://arxiv\.org/abs/2412\.19437](<https://arxiv.org/abs/2412.19437>) |
| Code repository | [https://github\.com/deepseek\-ai/DeepSeek\-V3](<https://github.com/deepseek-ai/DeepSeek-V3>) |
| Citation | @misc\{deepseekai2024deepseekv3technicalreport,<br>      title=\{DeepSeek\-V3 Technical Report\}, <br>      author=\{DeepSeek\-AI\},<br>      year=\{2024\},<br>      eprint=\{2412\.19437\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2412\.19437\}, <br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, task, and broad post\-training steps \(SFT, RL, FIM, R1 distillation\) without details on inner workings or evaluation limitations\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not describe training or fine\-tuning dataset composition, curation, or synthetic data generation, so dataset details are insufficiently documented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | No information is provided about the origin, ownership, or usage terms of the training data, making traceability uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only that it is a language model and gives no intended\-use or deployment scope, leaving downstream risk definitions open\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | No dataset details or bias evaluations are reported for a large pretrained/fine\-tuned MoE model, so historical/societal biases in its training data cannot be ruled out\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
