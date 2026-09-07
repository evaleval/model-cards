# Model Card: gemma\-2\-27b\-it

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-2\-27b\-it\.json](<./gemma-2-27b-it.json>)<br>
SHA-256: `7483552517d1b09555603516de0f367b7e639b868b2d8ee49c84c493208594f1`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-2\-27b\-it |
| Name | gemma\-2\-27b\-it |
| Developed by | google \(Hub organization\) |
| Model type | Text\-to\-text, decoder\-only large language model\. |
| License | gemma |
| Release date | 2024\-06\-24 \(Hugging Face repository creation date\) |
| Version | aaf20e6b9f4c0fcf043f6fb2a2068419086d77b0 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | google/gemma\-2\-27b (base model; Kind: finetune) |
| Model family | gemma 2 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 27,227,128,320 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 50\.7 GiB of safetensors weights \(54,454,316,552 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on a text dataset drawn from a wide variety of sources\. |
| Adaptations | The instruction\-tuned model uses a chat template that must be followed for conversational use\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 35,328 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 573 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model was evaluated on a broad set of text\-generation datasets and metrics covering different aspects of generation quality\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| RealToxicity | Not specified | 8\.84 | Not specified | Not reported |
| CrowS\-Pairs | top\-1 | 36\.67 | Not specified | Not reported |
| BBQ Ambig | top\-1 | 85\.99 | 1\-shot | Not reported |
| BBQ Disambig | top\-1 | 86\.94 | Not specified | Not reported |
| Winogender | top\-1 | 77\.22 | Not specified | Not reported |
| TruthfulQA | Not specified | 51\.60 | Not specified | Not reported |
| Winobias 12 | Not specified | 81\.94 | Not specified | Not reported |
| Winobias 22 | Not specified | 97\.22 | Not specified | Not reported |
| Toxigen | Not specified | 38\.42 | Not specified | Not reported |
| Elo | Elo | 1218 | Not specified | Not reported |
| Elo | Elo | 1127 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-2\-27b\-it](<https://huggingface.co/google/gemma-2-27b-it>) |
| Technical report | [https://arxiv\.org/abs/2408\.00118](<https://arxiv.org/abs/2408.00118>) |
| Code repository | [https://github\.com/huggingface/local\-gemma](<https://github.com/huggingface/local-gemma>) |
| Citation | @article\{gemma\_2024,<br>    title=\{Gemma\},<br>    url=\{https://www\.kaggle\.com/m/3301\},<br>    DOI=\{10\.34740/KAGGLE/M/3301\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only broad &\#x27;wide variety of sources&\#x27; for training data and generic &\#x27;broad set&\#x27; of evaluations, with no dataset details, evaluation results, or design/development documentation, so transparency about this checkpoint is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Confidential information in data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-information-in-data.html>) | Training data is described only as drawn from a wide variety of sources, with no filtering or deduplication of confidential or personal information stated, so the checkpoint plausibly contains confidential information in its training data\. | Confidential information might be included as part of the data that is used to train or tune the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | The card gives no information about the composition or representativeness of the training data, so the checkpoint may not generalize to all real\-world text distributions\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
