# Model Card: r1o\-et

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [r1o\-et\.json](<./r1o-et.json>)<br>
SHA-256: `63d31132a3fb7964632e81b4247abffc90b07d20f3c38a55aa7be8218c4cd07e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | marcuscedricridia/r1o\-et |
| Name | r1o\-et |
| Developed by | marcuscedricridia \(Hub organization\) |
| Release date | 2025\-03\-02 \(Hugging Face repository creation date\) |
| Version | a8ab5a8e1b27d0ac3cca9e60f40a09bc0ce547db |
| Summary | A merge of pre\-trained language models created using mergekit\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | huihui\-ai/DeepSeek\-R1\-Distill\-Qwen\-7B\-abliterated\-v2 (base model; Kind: merge)<br>marcuscedricridia/cursa\-o1\-7b (base model; Kind: merge)<br>suayptalha/Clarus\-7B\-v0\.2 (base model; Kind: merge) |
| Model family | r1o et |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,612,806,656 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,225,652,144 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The target checkpoint is a merge of pre\-trained language models; the merge included huihui\-ai/DeepSeek\-R1\-Distill\-Qwen\-7B\-abliterated\-v2 and suayptalha/Clarus\-7B\-v0\.2\. |
| Adaptations | The model is a merge created with mergekit, using the Linear DARE merge method with marcuscedricridia/cursa\-o1\-7b as the base\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/marcuscedricridia/r1o\-et](<https://huggingface.co/marcuscedricridia/r1o-et>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card gives only mergekit recipe and base components, with no reported evaluations or training\-data details for this exact checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card names the merged source models but does not document their training datasets or any synthetic data generation details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Inaccessible training data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/inaccessible-training-data.html>) | The checkpoint is a merge of pre\-trained models; the underlying training data is not accessible from the card, limiting explanation of outputs\. | Without access to the training data, the types of explanations a model can provide are limited and more likely to be incorrect\. |
| [Untraceable attribution](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/untraceable-attribution.html>) | Because the training data of the merged components is not accessible, content provenance for generated outputs cannot be traced\. | The content of the training data used for generating the model&\#x27;s output is not accessible\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only that it is a text\-to\-text model merge, with no intended\-use or misuse definition\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
