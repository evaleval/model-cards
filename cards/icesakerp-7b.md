# Model Card: IceSakeRP\-7b \(IceSakeV12\)

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [icesakerp\-7b\.json](<./icesakerp-7b.json>)<br>
SHA-256: `80dd0ea0d2a7f34464fb164afbb007657025741ddcfaea740a834c831e4ec688`

## Identity

| Field | Value |
| --- | --- |
| Model ID | icefog72/IceSakeRP\-7b |
| Name | IceSakeRP\-7b \(IceSakeV12\) |
| Developed by | icefog72 \(Hub organization\) |
| License | cc\-by\-nc\-4\.0 |
| Release date | 2024\-07\-07 \(Hugging Face repository creation date\) |
| Version | 921cce90016c06e8a9a9c0e7f3442b109d980d0d |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Ppoyaa/KunoichiVerse\-7B (base model; Kind: merge)<br>crestf411/daybreak\-kunoichi\-2dpo\-7b (base model; Kind: merge)<br>icefog72/IceCocoaRP\-7b (base model; Kind: merge)<br>icefog72/IceSakeV8RP\-7b (base model; Kind: merge) |
| Model family | IceSakeRP |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,241,732,096 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 13\.5 GiB of safetensors weights \(14,483,497,736 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | This checkpoint is a merge of pre\-trained language models created using mergekit\. |
| Adaptations | The model was merged using the SLERP merge method\. The following models were included in the merge\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 24 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 15 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/icefog72/IceSakeRP\-7b](<https://huggingface.co/icefog72/IceSakeRP-7b>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card only states it is a merge of pre\-trained models via SLERP and lists merged models, with no reported design details, training/evaluation documentation, or inner\-workings information\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card says the checkpoint is a merge of pre\-trained language models but provides no traceability of the underlying training data, ownership, or usage terms for the merged components\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card specifies only text\-to\-text modality and open\-weight access, with no intended\-use or deployment context, so downstream uses and associated risks are undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card gives no information about how the training data for the merged base models was collected, curated, or used, only naming the merged models\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Model usage rights restrictions](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/model-usage-rights.html>) | The checkpoint is released under cc\-by\-nc\-4\.0, which restricts commercial use, so usage rights are explicitly restricted\. | Terms of service, licenses, or other rules restrict the use of certain models\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
