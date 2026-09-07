# Model Card: OpenChat\-3\.5\-0106\_8\.11B\_36Layers\-Appended

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [openchat\-3\.5\-0106\_8\.11b\_36layers\-appended\.json](<./openchat-3.5-0106_8.11b_36layers-appended.json>)<br>
SHA-256: `b0f358deb21eb01a019c90165723d2ba5b196ed81bf8b1045f58beba74aa0b83`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Pretergeek/OpenChat\-3\.5\-0106\_8\.11B\_36Layers\-Appended |
| Name | OpenChat\-3\.5\-0106\_8\.11B\_36Layers\-Appended |
| Developed by | Pretergeek \(Hub organization\) |
| Model type | Text\-generation model\. |
| License | apache\-2\.0 |
| Release date | 2024\-07\-26 \(Hugging Face repository creation date\) |
| Version | 5a109a47db845ccf4b0e2f2f236425d9b7e97cb7 |
| Summary | A text\-generation model produced by merging OpenChat\-3\.5\-0106 with an appended block\-expansion variation\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | openchat/openchat\-3\.5\-0106 (base model; Kind: finetune) |
| Model family | OpenChat 3\.5 36Layers Appended |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,114,196,480 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.1 GiB of safetensors weights \(16,228,430,992 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was created by merging components using a passthrough merge method with a variation of the Block Expansion method from LLaMA Pro\. It has not yet received additional training, so it is expected to perform close to the original model\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 32 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Pretergeek/OpenChat\-3\.5\-0106\_8\.11B\_36Layers\-Appended](<https://huggingface.co/Pretergeek/OpenChat-3.5-0106_8.11B_36Layers-Appended>) |
| Citation | @misc\{wu2024llamaproprogressivellama,<br>      title=\{LLaMA Pro: Progressive LLaMA with Block Expansion\}, <br>      author=\{Chengyue Wu and Yukang Gan and Yixiao Ge and Zeyu Lu and Jiahao Wang and Ye Feng and Ying Shan and Ping Luo\},<br>      year=\{2024\},<br>      eprint=\{2401\.02415\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2401\.02415\}, <br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture and merge method, with no training data, evaluation, or safety documentation for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not state what data was used to train or merge the model, so training data provenance and curation are undocumented\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card only says &\#x27;text\-generation&\#x27; and gives no intended\-use or misuse guidance, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
