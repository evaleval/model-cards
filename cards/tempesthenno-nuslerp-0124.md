# Model Card: tempesthenno\-nuslerp\-0124

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [tempesthenno\-nuslerp\-0124\.json](<./tempesthenno-nuslerp-0124.json>)<br>
SHA-256: `a3f05a11601ff9e0ec0a8717276422339fdc7f84585d7755f075fd4ebc14bd61`

## Identity

| Field | Value |
| --- | --- |
| Model ID | sthenno/tempesthenno\-nuslerp\-0124 |
| Name | tempesthenno\-nuslerp\-0124 |
| Developed by | sthenno \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2025\-01\-27 \(Hugging Face repository creation date\) |
| Version | c56e973dc29da88b42dadcc5af54a3d3f58d036c |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | sthenno\-com/miscii\-14b\-1225 (base model; Kind: merge)<br>sthenno/tempesthenno\-ppo\-ckpt40 (base model; Kind: merge) |
| Model family | tempesthenno nuslerp |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,765,947,904 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.5 GiB of safetensors weights \(29,531,962,384 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge produced with the NuSLERP merge method\. The merge included the models listed in the accompanying YAML configuration\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 25 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 4 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/sthenno/tempesthenno\-nuslerp\-0124](<https://huggingface.co/sthenno/tempesthenno-nuslerp-0124>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only architecture, merge method, and license; no training data, training details, or evaluation results are reported for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The model is a merge of pre\-trained models via mergekit, but the card does not describe the provenance or usage terms of the underlying training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only text\-to\-text modality and open\-weight access, with no intended\-use or deployment context, so relevant risks are undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information is provided about how the training data for the merged base models was collected, curated, or used\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
