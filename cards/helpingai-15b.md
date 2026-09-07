# Model Card: HelpingAI\-15B: Emotionally Intelligent Conversational AI

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [helpingai\-15b\.json](<./helpingai-15b.json>)<br>
SHA-256: `1291efddf5e557c4289af5b5a5d2bbd2281898aee55bb80cb170b8d86bacfe62`

## Identity

| Field | Value |
| --- | --- |
| Model ID | OEvortex/HelpingAI\-15B |
| Name | HelpingAI\-15B: Emotionally Intelligent Conversational AI |
| Developed by | HelpingAI \(Hub organization\) |
| License | other |
| Release date | 2024\-07\-11 \(Hugging Face repository creation date\) |
| Version | 99638764d5aa79bfe64a7ef77e3d27e7caecbf51 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | HelpingAI |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 15,322,583,040 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 28\.5 GiB of safetensors weights \(30,645,242,968 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The HelpingAI\-15B checkpoint was trained with supervised learning on large dialogue datasets that include emotional labeling\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 73 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 13 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that HelpingAI\-15B reaches an Emotional Quotient of 96\.79, which they describe as surpassing almost all AI models in emotional intelligence\. |
| Human evaluations | The developer reports an Emotional Quotient of 96\.79 for HelpingAI\-15B, stating it surpasses almost all AI models in emotional intelligence\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/OEvortex/HelpingAI\-15B](<https://huggingface.co/OEvortex/HelpingAI-15B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only an aggregate Emotional Quotient of 96\.79 and gives no details of model design, development, or evaluation process, so the checkpoint lacks transparency about how this metric was produced\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card says only that training used supervised learning on large dialogue datasets with emotional labeling, without documenting dataset composition, provenance, or curation\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Training on large dialogue datasets with emotional labeling may not represent the full diversity of real\-world emotional expression, and the card provides no evidence of coverage across populations or contexts\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Emotionally labeled dialogue datasets can encode societal and cultural biases about emotion expression, and the card reports no bias analysis or mitigation\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | The reported Emotional Quotient of 96\.79 is used as evidence of emotional intelligence but is a single proprietary metric that may not measure the actual risk\-relevant capabilities or limitations of the model\. | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
