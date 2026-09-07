# Model Card: NVIDIA\-Nemotron\-Nano\-9B\-v2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [nvidia\-nemotron\-nano\-9b\-v2\.json](<./nvidia-nemotron-nano-9b-v2.json>)<br>
SHA-256: `a26512a3b86569e3d9429d8e9341225ffc4b4d50f83d986f7fa1755f03c98cf8`

## Identity

| Field | Value |
| --- | --- |
| Model ID | nvidia/nvidia\-nemotron\-nano\-9b\-v2 |
| Name | NVIDIA\-Nemotron\-Nano\-9B\-v2 |
| Developed by | nvidia \(Hub organization\) |
| License | other |
| Release date | 2025\-08\-12 \(Hugging Face repository creation date\) |
| Version | 6533e8de2c68e4536bf7c411d7a3ce5734111476 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | nvidia/NVIDIA\-Nemotron\-Nano\-12B\-v2 (base model; Kind: finetune) |
| Model family | nvidia nemotron nano v2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,888,227,328 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 16\.6 GiB of safetensors weights \(17,776,492,512 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was trained on NVIDIA datasets including Nemotron\-Post\-Training\-Dataset\-v1 and v2, Nemotron\-Pretraining\-Dataset\-sample, Nemotron\-CC\-v2, Nemotron\-CC\-Math\-v1, and Nemotron\-Pretraining\-SFT\-v1\. |
| Adaptations | The model was trained using Megatron\-LM and NeMo\-RL\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 429,626 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 517 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model was evaluated in Reasoning\-On mode for all benchmarks except RULER, which was evaluated in Reasoning\-Off mode\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| AIME25 | Not specified | 72\.1% | Not specified | Not reported |
| MATH500 | Not specified | 97\.8% | Not specified | Not reported |
| GPQA | Not specified | 64\.0% | Not specified | Not reported |
| LCB | Not specified | 71\.1% | Not specified | Not reported |
| BFCL v3 | Not specified | 66\.9% | Not specified | Not reported |
| IFEval | Not specified | 90\.3% | Not specified | Not reported |
| HLE | Not specified | 6\.5% | Not specified | Not reported |
| RULER | Not specified | 78\.9% | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/nvidia/nvidia\-nemotron\-nano\-9b\-v2](<https://huggingface.co/nvidia/nvidia-nemotron-nano-9b-v2>) |
| Technical report | [https://arxiv\.org/abs/2508\.14444](<https://arxiv.org/abs/2508.14444>) |
| Citation | @misc\{nvidia2025nvidianemotronnano2,<br>      title=\{NVIDIA Nemotron Nano 2: An Accurate and Efficient Hybrid Mamba\-Transformer Reasoning Model\},<br>      author=\{NVIDIA\},<br>      year=\{2025\},<br>      eprint=\{2508\.14444\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2508\.14444\},<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only a short list of training datasets and benchmark names with no dataset composition, curation, or evaluation details, so the checkpoint's design and development process is insufficiently documented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | Training data is described only by dataset names \(e\.g\., Nemotron\-Post\-Training\-Dataset\-v1/v2, Nemotron\-CC\-v2\) with no origin, ownership, or generation traceability, making provenance uncertain\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not describe how the named Nemotron datasets were collected, curated, or used, so training\-data transparency is lacking\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | The card states only text\-in/text\-out and open\-weight access, with no intended\-use or misuse definition, so relevant risks cannot be scoped for downstream uses\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
