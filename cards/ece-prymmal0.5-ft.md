# Model Card: ECE\-PRYMMAL0\.5\-FT

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [ece\-prymmal0\.5\-ft\.json](<./ece-prymmal0.5-ft.json>)<br>
SHA-256: `250e49f99d5ba41ffa7dc3b9004dd446ad3b5987b01b5badf31b7169c6ae781e`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Youlln/ECE\-PRYMMAL0\.5\-FT |
| Name | ECE\-PRYMMAL0\.5\-FT |
| Developed by | Youlln \(Hub organization\) |
| Model type | Text\-generation model |
| License | apache\-2\.0 |
| Release date | 2024\-10\-02 \(Hugging Face repository creation date\) |
| Version | f213ab5c4ce09048b49b8747bfb813ba96fec46d |
| Summary | A text\-generation model hosted on Hugging Face under the ECE\-PRYMMAL0\.5\-FT name\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-0\.5B\-Instruct (base model; Kind: finetune) |
| Model family | ECE PRYMMAL0\.5 FT |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 494,032,768 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 1\.8 GiB of safetensors weights \(1,976,163,472 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on the databricks/databricks\-dolly\-15k dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 26 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Youlln/ECE\-PRYMMAL0\.5\-FT](<https://huggingface.co/Youlln/ECE-PRYMMAL0.5-FT>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card states only that the model was fine\-tuned on databricks/databricks\-dolly\-15k, with no details on data collection, curation, or preprocessing, so training\-data transparency is limited\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Fine\-tuning on databricks\-dolly\-15k, a small human\-written instruction dataset, can carry societal biases from its authors and examples into the model&\#x27;s text outputs\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | The checkpoint is fine\-tuned only on databricks\-dolly\-15k, so its instruction\-following behavior may not generalize to broader text\-generation domains beyond that dataset&\#x27;s scope\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card lists only &\#x27;text\-generation&\#x27; as the primary task and gives no intended\-use or out\-of\-scope guidance, leaving downstream risk assessment underspecified\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
