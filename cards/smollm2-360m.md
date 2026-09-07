# Model Card: SmolLM2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\-360m\.json](<./smollm2-360m.json>)<br>
SHA-256: `ff47586d30a2532eb6a4ca01401c07b5a78d6f2125b2825f8fdfe65c63200f31`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM2\-360M |
| Name | SmolLM2 |
| Developed by | HuggingFaceTB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-10\-31 \(Hugging Face repository creation date\) |
| Version | f8027fd0eaeea54caa13c31d31b9fdc459c38b49 |
| Summary | SmolLM2 is a compact language model developed by Hugging Face, part of a family of efficient small models\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | SmolLM2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 361,821,120 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 0\.7 GiB of safetensors weights \(723,674,912 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | SmolLM2 was pretrained on roughly 11 trillion tokens in a multi\-stage process combining web text with specialized math, code, and instruction\-following data\. |
| Adaptations | The model was trained with a multi\-stage pretraining approach rather than a fixed dataset mixture throughout pretraining\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 486,011 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 128 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HellaSwag | Not specified | 54\.5 | Not specified | Not reported |
| ARC | Not specified | 53\.0 | Not specified | Not reported |
| PIQA | Not specified | 71\.7 | Not specified | Not reported |
| MMLU | Not specified | 35\.8 | Not specified | Not reported |
| CommonsenseQA | Not specified | 38\.0 | Not specified | Not reported |
| TriviaQA | Not specified | 16\.9 | Not specified | Not reported |
| Winogrande | Not specified | 52\.5 | Not specified | Not reported |
| OpenBookQA | Not specified | 37\.4 | Not specified | Not reported |
| GSM8K | Not specified | 3\.2 | 5\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM2\-360M](<https://huggingface.co/HuggingFaceTB/SmolLM2-360M>) |
| Technical report | [https://arxiv\.org/abs/2502\.02737](<https://arxiv.org/abs/2502.02737>) |
| Code repository | [https://github\.com/huggingface/smollm](<https://github.com/huggingface/smollm>) |
| Citation | @misc\{allal2025smollm2smolgoesbig,<br>      title=\{SmolLM2: When Smol Goes Big \-\- Data\-Centric Training of a Small Language Model\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Gabriel Martín Blázquez and Guilherme Penedo and Lewis Tunstall and Andrés Marafioti and Hynek Kydlíček and Agustín Piqueres Lajarín and Vaibhav Srivastav and Joshua Lochner and Caleb Fahlgren and Xuan\-Son Nguyen and Clémentine Fourrier and Ben Burtenshaw and Hugo Larcher and Haojun Zhao and Cyril Zakka and Mathieu Morlon and Colin Raffel and Leandro von Werra and Thomas Wolf\},<br>      year=\{2025\},<br>      eprint=\{2502\.02737\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2502\.02737\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, training scale, and data categories; no evaluation results, intended\-use restrictions, or inner\-workings details are documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card says pretraining combined web text with math, code, and instruction data but does not document dataset compositions, proportions, or sources\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Open\-weight Apache\-2\.0 checkpoint trained on ~11T tokens from unspecified web and specialized sources; no traceability of data ownership/origin is provided\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card gives no intended\-use or misuse guidance for the text\-to\-text model, leaving downstream risk scoping undefined\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
