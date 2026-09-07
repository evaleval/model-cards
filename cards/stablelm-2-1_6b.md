# Model Card: \`Stable LM 2 1\.6B\`

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [stablelm\-2\-1\_6b\.json](<./stablelm-2-1_6b.json>)<br>
SHA-256: `3d0ae5756729fa3fedcfba8ef2d7dcc2ece2552580e05d751c879056b2f9c326`

## Identity

| Field | Value |
| --- | --- |
| Model ID | stabilityai/stablelm\-2\-1\_6b |
| Name | \`Stable LM 2 1\.6B\` |
| Developed by | stabilityai \(Hub organization\) |
| License | other |
| Release date | 2024\-01\-18 \(Hugging Face repository creation date\) |
| Version | f499ead74c53749bd93cebc6ce8bc0d7bdf1eaef |

## Lineage

| Field | Value |
| --- | --- |
| Model family | stablelm 2 1 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,644,515,328 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 3\.1 GiB of safetensors weights \(3,289,069,520 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The base Stable LM 2 1\.6B model was pre\-trained on a filtered mixture of open\-source datasets from the HuggingFace Hub, including Falcon RefinedWeb extract, RedPajama\-Data and The Pile without the Books3 subset, and StarCoder, supplemented with multilingual data from CulturaX, particularly its OSCAR corpora, and restructured data in the style of Yuan &amp; Liu\. |
| Adaptations | The model is a base pre\-trained model; the documentation recommends fine\-tuning it for downstream tasks\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 6,434 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 196 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/stabilityai/stablelm\-2\-1\_6b](<https://huggingface.co/stabilityai/stablelm-2-1_6b>) |
| Code repository | [https://github\.com/Stability\-AI/StableLM](<https://github.com/Stability-AI/StableLM>) |
| Citation | @article\{bellagente2024stable,<br>  title=\{Stable LM 2 1\.6 B Technical Report\},<br>  author=\{Bellagente, Marco and Tow, Jonathan and Mahan, Dakota and Phung, Duy and Zhuravinskyi, Maksym and Adithyan, Reshinth and Baicoianu, James and Brooks, Ben and Cooper, Nathan and Datta, Ashish and others\},<br>  journal=\{arXiv preprint arXiv:2402\.17834\},<br>  year=\{2024\}<br>\} |

## Risks

_No specified fields are available in the publication data._

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `risks.possible_risks`.
