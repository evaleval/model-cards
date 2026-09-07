# Model Card: miniclaus\-qw1\.5B\-UNAMGS\-GRPO

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [miniclaus\-qw1\.5b\-unamgs\-grpo\.json](<./miniclaus-qw1.5b-unamgs-grpo.json>)<br>
SHA-256: `0c603678d831ceb20f165b96ce4c89309bf61dc9bfc1f59a1bd2e0a5dd73b155`

## Identity

| Field | Value |
| --- | --- |
| Model ID | fblgit/miniclaus\-qw1\.5B\-UNAMGS\-GRPO |
| Name | miniclaus\-qw1\.5B\-UNAMGS\-GRPO |
| Developed by | fblgit \(Hub organization\) |
| License | other |
| Release date | 2025\-02\-03 \(Hugging Face repository creation date\) |
| Version | 2cece3ef7556d100b194107e72cf46dd6ac04bc3 |
| Summary | This version is trained with reinforcement learning using GRPO on the GSM8k dataset for 1400 steps\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | fblgit/miniclaus\-qw1\.5B\-UNAMGS (base model; Kind: finetune) |
| Model family | miniclaus qw1\.5B UNAMGS GRPO |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,543,714,304 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 2\.9 GiB of safetensors weights \(3,087,467,144 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This version was trained with RL using GRPO on GSM8k for 1400 steps, also using MGS and UNA \(MLP\)\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 20 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 5 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that this checkpoint shows increased scores on GSM, GPQA, and MUSR relative to other checkpoints, and that it achieves the best marks among them\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/fblgit/miniclaus\-qw1\.5B\-UNAMGS\-GRPO](<https://huggingface.co/fblgit/miniclaus-qw1.5B-UNAMGS-GRPO>) |
| Citation | @misc\{miniclaus\-qw15,<br>  title=\{MiniClaus: 1\.5B UNAMGS\}, <br>  author=\{Xavier Murias\},<br>  year=\{2024\},<br>  publisher = \{HuggingFace\},<br>  journal = \{HuggingFace repository\},<br>  howpublished = \{\\url\{https://huggingface\.co/fblgit/miniclaus\-qw1\.5B\-UNAMGS\}\},<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only aggregate benchmark scores and training recipe \(GRPO, GSM8k, 1400 steps, MGS/UNA\) with no documentation of design choices, evaluation details, or inner workings, and license is only &\#x27;other&\#x27;\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card states RL training on GSM8k but does not document data collection, curation, or preprocessing, so training\-data provenance is not transparent\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Overfitting](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/overfitting.html>) | Trained with RL for 1400 steps on GSM8k, a narrow math dataset, which can lead to memorization of that benchmark and poor generalization to other math tasks\. | Overfitting occurs when a model or algorithm memorizes and fits too closely or exactly to its training data\. Overfitting results in a model that might not be able to make accurate predictions or conclusions from any data other than the training data and potentially fails in unexpected scenarios\. Overfitting is also related to model collapse, which involves repeatedly training generative models on synthetic data that is generated with LLMs causing the model to lose information and become less accurate\. |
| [Data contamination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-contamination.html>) | RL training on GSM8k and reported gains on GSM, GPQA, and MUSR create risk that evaluation benchmarks overlap with training data, especially GSM8k itself\. | Data contamination occurs when incorrect data is used for training\. For example, data that is not aligned with model&\#x27;s purpose or data that is already set aside for other development tasks such as testing and evaluation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
