# Model Card: gemma\-4\-e2b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-4\-e2b\.json](<./gemma-4-e2b.json>)<br>
SHA-256: `1faff306b1372c595c62cb24b900bed00a10c4bb3d88e787e1a0950ad27a724a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-4\-e2b |
| Name | gemma\-4\-e2b |
| Developed by | google \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2026\-03\-02 \(Hugging Face repository creation date\) |
| Version | d29ff6b45f081a49ee2733a859c9c9c2d95d1a6f |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma 4 e2b |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 5,123,178,051 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 9\.5 GiB of safetensors weights \(10,246,621,918 bytes\) in BF16 |
| Input / output | text<br>images<br>audio |

## Training Context

| Field | Value |
| --- | --- |
| Data cutoff | January 2025 |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 71,615 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 463 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Gemma 4 achieves large gains on STEM, multimodal, and long\-context benchmarks and is competitive with larger open frontier models in human evaluations\. The E2B and E4B variants add native audio input for speech recognition and understanding, support a 128K context window, and were trained on over 140 languages\. |
| Safety evaluations | The developer reports major improvements in every content\-safety category relative to previous Gemma models, with minimal policy violations across text\-to\-text and image\-to\-text modalities and all model sizes\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| = | WER | 0\.080 | Not specified | Not reported |
| = | WER | 0\.065 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.066 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.107 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.076 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.101 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.042 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.041 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.056 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.084 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.143 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.187 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.090 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.053 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.078 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.061 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.080 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.086 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.035 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.032 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.046 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.068 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.162 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.136 | Not specified | Not reported |
| CER ↓ \) | WER | 0\.075 | Not specified | Not reported |
| RULER | Not specified | 96\.8 | thinking | Not reported |
| RULER | Not specified | 97\.3 | thinking | Not reported |
| RULER | Not specified | 96\.4 | thinking | Not reported |
| RULER | Not specified | 95\.2 | thinking | Not reported |
| RULER | Not specified | 83\.0 | thinking | Not reported |
| LOFT Text Retrieval | Not specified | 79\.5 | thinking | Not reported |
| LOFT Text Retrieval | Not specified | 66\.3 | thinking | Not reported |
| LOFT Text Retrieval | Not specified | 66\.4 | thinking | Not reported |
| LOFT Text Retrieval | Not specified | 58\.5 | thinking | Not reported |
| LOFT Text Retrieval | Not specified | 50\.5 | thinking | Not reported |
| GraphWalks | Not specified | 82\.3 | thinking | Not reported |
| GraphWalks | Not specified | 72\.6 | thinking | Not reported |
| GraphWalks | Not specified | 71\.0 | thinking | Not reported |
| GraphWalks | Not specified | 50\.9 | thinking | Not reported |
| GraphWalks | Not specified | 4\.1 | thinking | Not reported |
| MTOB | Not specified | 52\.9 | thinking | Not reported |
| MTOB | Not specified | 50\.0 | thinking | Not reported |
| MTOB | Not specified | 45\.1 | thinking | Not reported |
| MTOB | Not specified | 37\.8 | thinking | Not reported |
| MTOB | Not specified | 15\.4 | thinking | Not reported |
| MTOB \(kgv → | Not specified | 48\.6 | thinking | Not reported |
| MTOB \(kgv → | Not specified | 45\.0 | thinking | Not reported |
| MTOB \(kgv → | Not specified | 37\.3 | thinking | Not reported |
| MTOB \(kgv → | Not specified | 34\.6 | thinking | Not reported |
| MTOB \(kgv → | Not specified | 28\.2 | thinking | Not reported |
| eng\) | Not specified | 46\.2 | thinking | Not reported |
| eng\) | Not specified | 42\.7 | thinking | Not reported |
| eng\) | Not specified | 32\.9 | thinking | Not reported |
| MMMU Pro | Not specified | 75\.8 | thinking | Not reported |
| MMMU Pro | Not specified | 73\.2 | thinking | Not reported |
| MMMU Pro | Not specified | 67\.7 | thinking | Not reported |
| MMMU Pro | Not specified | 51\.4 | thinking | Not reported |
| MMMU Pro | Not specified | 43\.2 | thinking | Not reported |
| MATH\-Vision | Not specified | 83\.4 | thinking | Not reported |
| MATH\-Vision | Not specified | 80\.3 | thinking | Not reported |
| MATH\-Vision | Not specified | 76\.7 | thinking | Not reported |
| MATH\-Vision | Not specified | 59\.2 | thinking | Not reported |
| MATH\-Vision | Not specified | 53\.0 | thinking | Not reported |
| MedXPertQAMM | Not specified | 60\.7 | thinking | Not reported |
| MedXPertQAMM | Not specified | 55\.7 | thinking | Not reported |
| MedXPertQAMM | Not specified | 47\.4 | thinking | Not reported |
| MedXPertQAMM | Not specified | 28\.7 | thinking | Not reported |
| MedXPertQAMM | Not specified | 22\.5 | thinking | Not reported |
| InfographicVQA | Not specified | 82\.8 | thinking | Not reported |
| InfographicVQA | Not specified | 77\.8 | thinking | Not reported |
| InfographicVQA | Not specified | 58\.7 | thinking | Not reported |
| InfographicVQA | Not specified | 54\.8 | thinking | Not reported |
| InfographicVQA | Not specified | 44\.6 | thinking | Not reported |
| OmniDocBench 1\.5 ↓ | Not specified | 0\.201 | thinking | Not reported |
| OmniDocBench 1\.5 ↓ | Not specified | 0\.269 | thinking | Not reported |
| OmniDocBench 1\.5 ↓ | Not specified | 0\.408 | thinking | Not reported |
| OmniDocBench 1\.5 ↓ | Not specified | 0\.307 | thinking | Not reported |
| OmniDocBench 1\.5 ↓ | Not specified | 0\.496 | thinking | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-4\-e2b](<https://huggingface.co/google/gemma-4-e2b>) |
| Code repository | [https://github\.com/bebechien/gemma](<https://github.com/bebechien/gemma>) |
| Citation | @misc\{gemmateam2026gemma4,<br>      title=\{Gemma 4 Technical Report\}, <br>      author=\{Gemma Team\},<br>      year=\{2026\},<br>      eprint=\{2607\.02770\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2607\.02770\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only aggregate benchmark and safety results, with no documentation of model design, training data, or inner workings for this checkpoint\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | Card does not describe training/tuning dataset details, collection, curation, or synthetic data generation for gemma\-4\-e2b\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | No information is provided about how the model's data was collected, curated, and used to train this checkpoint\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.adaptations`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`.
