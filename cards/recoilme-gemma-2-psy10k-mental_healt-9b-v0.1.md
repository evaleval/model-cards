# Model Card: recoilme\-gemma\-2\-psy10k\-mental\_healt\-9B\-v0\.1

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [recoilme\-gemma\-2\-psy10k\-mental\_healt\-9b\-v0\.1\.json](<./recoilme-gemma-2-psy10k-mental_healt-9b-v0.1.json>)<br>
SHA-256: `30e31ecab010f0f07211d276dc086393a5891ba5b47458d342420aa832d48a80`

## Identity

| Field | Value |
| --- | --- |
| Model ID | zelk12/recoilme\-gemma\-2\-psy10k\-mental\_healt\-9B\-v0\.1 |
| Name | recoilme\-gemma\-2\-psy10k\-mental\_healt\-9B\-v0\.1 |
| Developed by | zelk12 \(Hub organization\) |
| Release date | 2024\-10\-07 \(Hugging Face repository creation date\) |
| Version | 5bc5ca844a15f21d045999dc2535ae8936e68eec |

## Lineage

| Field | Value |
| --- | --- |
| Base models | ehristoforu/Gemma2\-9B\-it\-psy10k\-mental\_health (base model; Kind: merge)<br>recoilme/recoilme\-gemma\-2\-9B\-v0\.4 (base model; Kind: merge) |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 10,159,209,984 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 18\.9 GiB of safetensors weights \(20,318,474,544 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | This model is a merge of two Gemma\-2\-9B based checkpoints using the SLERP merge method\. The merged checkpoints are recoilme/recoilme\-gemma\-2\-9B\-v0\.4 and ehristoforu/Gemma2\-9B\-it\-psy10k\-mental\_health\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 22 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 1 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/zelk12/recoilme\-gemma\-2\-psy10k\-mental\_healt\-9B\-v0\.1](<https://huggingface.co/zelk12/recoilme-gemma-2-psy10k-mental_healt-9B-v0.1>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, merge method, and merged checkpoints, with no training data, evaluation, or intended\-use details for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card gives no intended\-use or deployment context for this mental\-health\-related merge, so downstream uses and relevant risks are undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe the data used to train or fine\-tune the merged checkpoints, leaving collection and curation undocumented\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Card names the merged checkpoints but does not document the provenance, ownership, or usage terms of their underlying training data\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | A mental\-health text model with no reported evaluation or safeguards can plausibly generate ungrounded or factually inaccurate advice\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.model_family`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
