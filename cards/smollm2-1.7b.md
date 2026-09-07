# Model Card: SmolLM2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\-1\.7b\.json](<./smollm2-1.7b.json>)<br>
SHA-256: `1288755625c0ca87ab395d55efe83385887c74843c0f1a991539c269f91e2ebb`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM2\-1\.7B |
| Name | SmolLM2 |
| Developed by | HuggingFaceTB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-10\-30 \(Hugging Face repository creation date\) |
| Version | effd688a12921b4cc83e3312b6feb579f70f9c71 |
| Summary | A state\-of\-the\-art small language model that is lightweight enough to run on\-device while handling a wide range of tasks\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | SmolLM2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,711,376,384 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 3\.2 GiB of safetensors weights \(3,422,777,952 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | SmolLM2 was pretrained on about 11 trillion tokens combining web text with specialized math, code, and instruction\-following data, including FineWeb\-Edu, DCLM, The Stack, and newly curated mathematics and coding datasets\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 382,575 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 159 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HellaSwag | Not specified | 68\.7 | Not specified | Not reported |
| ARC | Not specified | 60\.5 | Not specified | Not reported |
| PIQA | Not specified | 77\.6 | Not specified | Not reported |
| MMLU\-Pro | Not specified | 19\.4 | Not specified | Not reported |
| CommonsenseQA | Not specified | 43\.6 | Not specified | Not reported |
| TriviaQA | Not specified | 36\.7 | Not specified | Not reported |
| Winogrande | Not specified | 59\.4 | Not specified | Not reported |
| OpenBookQA | Not specified | 42\.2 | Not specified | Not reported |
| Natural Questions | Not specified | 8\.7 | Not specified | Not reported |
| MATH | Not specified | 11\.6 | 4\-shot | Not reported |
| HumanEval | Not specified | 22\.6 | Not specified | Not reported |
| Average\-Real | Not specified | 31\.67 | Not specified | Not reported |
| Average\-All | Not specified | 32\.61 | Not specified | Not reported |
| Recall | Not specified | 36\.38 | Not specified | Not reported |
| RAG | Not specified | 47\.17 | Not specified | Not reported |
| ICL | Not specified | 23\.2 | Not specified | Not reported |
| Re\-rank | Not specified | 23\.31 | Not specified | Not reported |
| LongQA | Not specified | 33 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM2\-1\.7B](<https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B>) |
| Technical report | [https://arxiv\.org/abs/2502\.02737](<https://arxiv.org/abs/2502.02737>) |
| Code repository | [https://github\.com/huggingface/smollm](<https://github.com/huggingface/smollm>) |
| Citation | @misc\{allal2025smollm2smolgoesbig,<br>      title=\{SmolLM2: When Smol Goes Big \-\- Data\-Centric Training of a Small Language Model\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Gabriel Martín Blázquez and Guilherme Penedo and Lewis Tunstall and Andrés Marafioti and Hynek Kydlíček and Agustín Piqueres Lajarín and Vaibhav Srivastav and Joshua Lochner and Caleb Fahlgren and Xuan\-Son Nguyen and Clémentine Fourrier and Ben Burtenshaw and Hugo Larcher and Haojun Zhao and Cyril Zakka and Mathieu Morlon and Colin Raffel and Leandro von Werra and Thomas Wolf\},<br>      year=\{2025\},<br>      eprint=\{2502\.02737\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2502\.02737\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | open\-weight pretrained on 11T tokens from web, math, code, and instruction data with no dataset\-level provenance details in the card | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | card names broad corpora \(FineWeb\-Edu, DCLM, The Stack, curated math/code sets\) but does not document collection, curation, or synthetic generation details | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | training\-data documentation lacks details about how the 11T\-token mix was collected, curated, and used, making model behavior harder to explain | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | card only says it handles a wide range of tasks and is lightweight for on\-device use, without specifying intended uses or limitations | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | pretrained on web\-scale corpora \(FineWeb\-Edu, DCLM, The Stack\) that can contain historical and societal biases, with no debiasing or bias evaluation reported | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
