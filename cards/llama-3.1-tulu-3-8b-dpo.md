# Model Card: Llama\-3\.1\-Tulu\-3\-8B\-DPO

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [llama\-3\.1\-tulu\-3\-8b\-dpo\.json](<./llama-3.1-tulu-3-8b-dpo.json>)<br>
SHA-256: `19b601e4151bfd7c31047cda0a942c0404518328b4fde8adb97647172339caff`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allenai/Llama\-3\.1\-Tulu\-3\-8B\-DPO |
| Name | Llama\-3\.1\-Tulu\-3\-8B\-DPO |
| Developed by | allenai \(Hub organization\) |
| License | llama3\.1 |
| Release date | 2024\-11\-20 \(Hugging Face repository creation date\) |
| Version | a7beb67e33ffd01cc87ac3b46cadc1000985b8db |
| Summary | A fully open instruction\-following model from the Tülu 3 family, with open data, code, and training recipes\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | allenai/Llama\-3\.1\-Tulu\-3\-8B\-SFT (base model; Kind: finetune) |
| Model family | Llama 3\.1 Tulu 3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,326,784 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,687,448 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 9,558 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 30 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/allenai/Llama\-3\.1\-Tulu\-3\-8B\-DPO](<https://huggingface.co/allenai/Llama-3.1-Tulu-3-8B-DPO>) |
| Technical report | [https://arxiv\.org/abs/2411\.15124](<https://arxiv.org/abs/2411.15124>) |
| Code repository | [https://github\.com/allenai/open\-instruct](<https://github.com/allenai/open-instruct>) |
| Citation | @article\{lambert2024tulu3,<br>  title = \{Tülu 3: Pushing Frontiers in Open Language Model Post\-Training\},<br>  author = \{<br>    Nathan Lambert and <br>    Jacob Morrison and <br>    Valentina Pyatkin and <br>    Shengyi Huang and <br>    Hamish Ivison and <br>    Faeze Brahman and <br>    Lester James V\. Miranda and <br>    Alisa Liu and <br>    Nouha Dziri and <br>    Shane Lyu and <br>    Yuling Gu and <br>    Saumya Malik and <br>    Victoria Graf and <br>    Jena D\. Hwang and <br>    Jiangjiang Yang and<br>    Ronan Le Bras and<br>    Oyvind Tafjord and<br>    Chris Wilhelm and<br>    Luca Soldaini and <br>    Noah A\. Smith and <br>    Yizhong Wang and <br>    Pradeep Dasigi and <br>    Hannaneh Hajishirzi<br>  \},<br>  year = \{2024\},<br>  email = \{tulu@allenai\.org\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card summary provides only architecture, modality, access, and license; no documentation of design, development, or evaluation process is stated for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card summary does not state how training/fine\-tuning data was collected, curated, or used for this checkpoint, despite being an open\-data family model\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card summary describes it only as a fully open instruction\-following model with no stated intended use or deployment context, so relevant risks are undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
