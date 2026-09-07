# Model Card: \`StableLM 2 12B Chat\`

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [stablelm\-2\-12b\-chat\.json](<./stablelm-2-12b-chat.json>)<br>
SHA-256: `ccaea007052fdf0e1a67cbfb425cab737dd8dbc65f37c22b4641bb2755c77ac9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | stabilityai/stablelm\-2\-12b\-chat |
| Name | \`StableLM 2 12B Chat\` |
| Developed by | stabilityai \(Hub organization\) |
| License | other |
| Release date | 2024\-04\-04 \(Hugging Face repository creation date\) |
| Version | b6b62cd451b84e848514c00fafa66d9ead9297c5 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | stablelm 2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 12,143,185,920 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 22\.6 GiB of safetensors weights \(24,286,613,840 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The chat model was trained on a mixture of open datasets from the HuggingFace Hub plus an internal safety dataset, including SFT, safety, and preference datasets\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 465 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 88 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer\-reported results for this model include an MT Bench score of 8\.15 ± 0\.08 and an average of 68\.45 across several standard benchmarks, with the 12B chat model outperforming smaller variants\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MT Bench | Not specified | 8\.15 ± 0\.08 | Not specified | Not reported |
| Average | Not specified | 68\.45 | Not specified | Not reported |
| ARC Challenge | Not specified | 65\.02 | 25\-shot | Not reported |
| HellaSwag | Not specified | 86\.06 | 10\-shot | Not reported |
| MMLU | Not specified | 61\.14 | 5\-shot | Not reported |
| TruthfulQA | Not specified | 62\.00 | 0\-shot | Not reported |
| Winogrande | Not specified | 78\.77 | 5\-shot | Not reported |
| GSM8K | Not specified | 57\.70 | 5\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/stabilityai/stablelm\-2\-12b\-chat](<https://huggingface.co/stabilityai/stablelm-2-12b-chat>) |
| Technical report | [https://arxiv\.org/abs/2402\.17834](<https://arxiv.org/abs/2402.17834>) |
| Citation | @article\{bellagente2024stable,<br>  title=\{Stable LM 2 1\.6 B Technical Report\},<br>  author=\{Bellagente, Marco and Tow, Jonathan and Mahan, Dakota and Phung, Duy and Zhuravinskyi, Maksym and Adithyan, Reshinth and Baicoianu, James and Brooks, Ben and Cooper, Nathan and Datta, Ashish and others\},<br>  journal=\{arXiv preprint arXiv:2402\.17834\},<br>  year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only aggregate benchmark scores and a broad description of training data \(mixture of open datasets plus an internal safety dataset\) with no details on design, development, or evaluation process, so the checkpoint lacks model transparency\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card says the chat model was trained on a mixture of open datasets plus an internal safety dataset but does not document the composition, curation, or proportions of those datasets, so training/tuning dataset details are insufficient\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card states training data is a mixture of open datasets from the HuggingFace Hub plus an internal safety dataset, but does not provide traceable origin or usage terms for the internal dataset or the exact mixture, so data provenance is uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data contamination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-contamination.html>) | The card reports benchmark results \(MT Bench and standard benchmarks\) but does not state whether the training mixture was checked against those benchmarks, so contamination of evaluation data cannot be ruled out\. | Data contamination occurs when incorrect data is used for training\. For example, data that is not aligned with model&\#x27;s purpose or data that is already set aside for other development tasks such as testing and evaluation\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
