# Model Card: DeepSeek\-R1\-Distill\-Qwen\-MFANN\-Slerp\-7b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-r1\-distill\-qwen\-mfann\-slerp\-7b\.json](<./deepseek-r1-distill-qwen-mfann-slerp-7b.json>)<br>
SHA-256: `f9e3aacbdba826b861208c0ebff604595b0c03f2152e390affd5fac6004311d2`

## Identity

| Field | Value |
| --- | --- |
| Model ID | netcat420/DeepSeek\-R1\-Distill\-Qwen\-MFANN\-Slerp\-7b |
| Name | DeepSeek\-R1\-Distill\-Qwen\-MFANN\-Slerp\-7b |
| Developed by | netcat420 \(Hub organization\) |
| Release date | 2025\-01\-23 \(Hugging Face repository creation date\) |
| Version | 12006d09cf7310f40da990ce9107bffcb2b708df |

## Lineage

| Field | Value |
| --- | --- |
| Base models | deepseek\-ai/DeepSeek\-R1\-Distill\-Qwen\-7B (base model; Kind: merge)<br>netcat420/Qwen2\.5\-Coder\-Scholar\-7B\-Abliterated\-MFANN\-Slerp\-Unretrained (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,520 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of pre\-trained language models created using mergekit, merged with the SLERP merge method\. The merge included netcat420/Qwen2\.5\-Coder\-Scholar\-7B\-Abliterated\-MFANN\-Slerp\-Unretrained and deepseek\-ai/DeepSeek\-R1\-Distill\-Qwen\-7B\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 22 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/netcat420/DeepSeek\-R1\-Distill\-Qwen\-MFANN\-Slerp\-7b](<https://huggingface.co/netcat420/DeepSeek-R1-Distill-Qwen-MFANN-Slerp-7b>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card only describes the model as a merge of two named models using SLERP and gives no evaluation or design details, so the checkpoint&\#x27;s own documentation is insufficient to understand its inner workings\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card names the merged base models but does not document the provenance or usage terms of the training data underlying those components\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe how the training data for the merged components was collected, curated, or used, making the model&\#x27;s behavior harder to explain\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states no intended use or deployment context for this text\-to\-text merge, so the relevant risks cannot be defined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Unrepresentative risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-risk-testing.html>) | The card reports no evaluations or risk testing for this exact checkpoint, so any testing that exists is not shown to match its deployment inputs\. | Testing is unrepresentative when the test inputs are mismatched with the inputs that are expected during deployment\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
