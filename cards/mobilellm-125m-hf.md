# Model Card: MobileLLM\-125M\-HF

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [mobilellm\-125m\-hf\.json](<./mobilellm-125m-hf.json>)<br>
SHA-256: `5fd70438ebc76f9aa245d4987b5b8dc3ebbdd5716ed20191870a8cd52451ca40`

## Identity

| Field | Value |
| --- | --- |
| Model ID | vonjack/MobileLLM\-125M\-HF |
| Name | MobileLLM\-125M\-HF |
| Developed by | vonjack \(Hub organization\) |
| License | cc\-by\-nc\-4\.0 |
| Release date | 2024\-11\-15 \(Hugging Face repository creation date\) |
| Version | 95290dd6b5d7fa616e6921ba0e35c5ff259fb8d1 |
| Summary | A Hugging Face conversion of the MobileLLM 125M checkpoint, a sub\-billion parameter language model optimized for on\-device use\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | MobileLLM |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 124,635,456 parameters \(safetensors metadata\) |
| Context length | 2,048 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 0\.2 GiB of safetensors weights \(249,301,128 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 82 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 3 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the 125M checkpoint improves zero\-shot commonsense reasoning accuracy by 2\.7% over the previous best 125M model\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/vonjack/MobileLLM\-125M\-HF](<https://huggingface.co/vonjack/MobileLLM-125M-HF>) |
| Technical report | [https://arxiv\.org/abs/2402\.14905](<https://arxiv.org/abs/2402.14905>) |
| Code repository | [https://github\.com/facebookresearch/MobileLLM](<https://github.com/facebookresearch/MobileLLM>) |
| Citation | Liu, Zechun, Zhao, Changsheng, Iandola, Forrest, Lai, Chen, Tian, Yuandong, Fedorov, Igor, Xiong, Yunyang, Chang, Ernie, and Shi, Yangyang\. MobileLLM: Optimizing Sub\-billion Parameter Language Models for On\-Device Use Cases\. arXiv:2402\.14905\. |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only architecture, access, license, and a single accuracy gain; it does not document design/evaluation details or inner workings, so transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not state how the training data was collected, curated, or used, so training\-data transparency is lacking\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card gives no intended\-use or deployment context beyond 'on\-device use' \[family\-scope\], so relevant risks cannot be defined for specific downstream uses\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Model usage rights restrictions](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/model-usage-rights.html>) | The cc\-by\-nc\-4\.0 license restricts use to non\-commercial purposes, which is a concrete usage\-rights restriction\. | Terms of service, licenses, or other rules restrict the use of certain models\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
