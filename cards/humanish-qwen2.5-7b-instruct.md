# Model Card: Humanish\-Qwen2\.5\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [humanish\-qwen2\.5\-7b\-instruct\.json](<./humanish-qwen2.5-7b-instruct.json>)<br>
SHA-256: `04cfa0052e3b77b5f394b576a8a5b2b8cb7cc31f3b3315d483d205d4dc623774`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HumanLLMs/Humanish\-Qwen2\.5\-7B\-Instruct |
| Name | Humanish\-Qwen2\.5\-7B\-Instruct |
| Developed by | HumanLLMs \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2024\-10\-05 \(Hugging Face repository creation date\) |
| Version | 7cab6062ab32fa984f51d4bf0254472b2b320362 |
| Summary | A fine\-tuned version of Qwen/Qwen2\.5\-7B\-Instruct, optimized to generate more human\-like and conversational responses\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\.5\-7B\-Instruct (base model; Kind: finetune) |
| Model family | Humanish Qwen2\.5 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,864 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on a dataset of 10,884 samples spanning 256 topics, generated with LLaMA 3 models\. |
| Training data size | 10,884 samples across 256 topics\. |
| Adaptations | The fine\-tuning used Low\-Rank Adaptation \(LoRA\) and Direct Preference Optimization \(DPO\)\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 103 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 13 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HumanLLMs/Humanish\-Qwen2\.5\-7B\-Instruct](<https://huggingface.co/HumanLLMs/Humanish-Qwen2.5-7B-Instruct>) |
| Citation | @misc\{çalık2025enhancinghumanlikeresponseslarge,<br>      title=\{Enhancing Human\-Like Responses in Large Language Models\}, <br>      author=\{Ethem Yağız Çalık and Talha Rüzgar Akkuş\},<br>      year=\{2025\},<br>      eprint=\{2501\.05032\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2501\.05032\}, <br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card states fine\-tuning data only as 10,884 samples spanning 256 topics generated with LLaMA 3 models, with no dataset details or documentation of synthetic generation\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Fine\-tuning on only 10,884 synthetic LLaMA 3\-generated samples across 256 topics may not capture real\-world conversational complexity and can limit generalization\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card does not provide traceability for the synthetic fine\-tuning data, including ownership, source, or generation verification\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | Fine\-tuning on synthetic LLaMA 3\-generated data can propagate or introduce hallucinated content, and the card reports no hallucination evaluation\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Bias may be inherited from the LLaMA 3\-generated synthetic fine\-tuning data or the base model, and the card reports no bias evaluation\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |

---

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
