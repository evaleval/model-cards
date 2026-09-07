# Model Card: SmolLM2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\-135m\.json](<./smollm2-135m.json>)<br>
SHA-256: `227dca41fd559442e2f310ca237db9e7d9102656931ffa4bbc7efe598f66fcb5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM2\-135M |
| Name | SmolLM2 |
| Developed by | HuggingFaceTB \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-10\-31 \(Hugging Face repository creation date\) |
| Version | 93efa2f097d58c2a74874c7e644dbc9b0cee75a2 |
| Summary | SmolLM2 is a family of compact language models available in three sizes: 135M, 360M, and 1\.7B parameters\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | SmolLM2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 134,515,008 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 0\.3 GiB of safetensors weights \(269,060,552 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 2,563,448 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 230 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that SmolLM2 shows clear gains over SmolLM1, especially in instruction following, knowledge, and reasoning\. |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM2\-135M](<https://huggingface.co/HuggingFaceTB/SmolLM2-135M>) |
| Technical report | [https://arxiv\.org/abs/2502\.02737](<https://arxiv.org/abs/2502.02737>) |
| Citation | @misc\{allal2025smollm2smolgoesbig,<br>      title=\{SmolLM2: When Smol Goes Big \-\- Data\-Centric Training of a Small Language Model\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Gabriel Martín Blázquez and Guilherme Penedo and Lewis Tunstall and Andrés Marafioti and Hynek Kydlíček and Agustín Piqueres Lajarín and Vaibhav Srivastav and Joshua Lochner and Caleb Fahlgren and Xuan\-Son Nguyen and Clémentine Fourrier and Ben Burtenshaw and Hugo Larcher and Haojun Zhao and Cyril Zakka and Mathieu Morlon and Colin Raffel and Leandro von Werra and Thomas Wolf\},<br>      year=\{2025\},<br>      eprint=\{2502\.02737\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2502\.02737\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only architecture, size, license, and high\-level gains; no details on training data, evaluation, or limitations for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card does not describe data collection, curation, or composition for SmolLM2\-135M, so training\-data transparency is lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card states only that it is a text\-to\-text language model and does not define intended or prohibited uses, leaving downstream risk scope undefined\. | Since foundation models can be used for many purposes, a model&\#x27;s intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
