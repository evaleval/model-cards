# Model Card: OLMo\-2\-1124\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [olmo\-2\-1124\-7b\-instruct\.json](<./olmo-2-1124-7b-instruct.json>)<br>
SHA-256: `aa6d1b2b7d4df2a784806c806ddf37e39432405595a3c5396ae67fc7b78a856c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allenai/OLMo\-2\-1124\-7B\-Instruct |
| Name | OLMo\-2\-1124\-7B\-Instruct |
| Developed by | allenai \(Hub organization\) |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Release date | 2024\-12\-18 \(Hugging Face repository creation date\) |
| Version | 470b1fba1ae01581f270116362ee4aa1b97f4c84 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | allenai/OLMo\-2\-1124\-7B\-DPO (base model; Kind: finetune) |
| Model family | OLMo 2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,298,617,344 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.6 GiB of safetensors weights \(14,597,276,128 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The OLMo 2 7B Instruct November 2024 checkpoint was post\-trained on an OLMo\-specific variant of the Tülu 3 dataset, used for supervised finetuning, DPO, and RLVR training\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 61,617 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 50 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer\-reported results for OLMo\-2\-7B\-1124\-Instruct include an average score of 54\.8, with notable scores on GSM8k \(85\.1\), IFEval \(72\.3\), MMLU \(61\.3\), DROP \(60\.5\), TruthQA \(56\.5\), MATH \(32\.5\), AlpacaEval \(29\.1\), and PopQA \(23\.2\)\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Average | Not specified | 54\.8 | Not specified | Not reported |
| AlpacaEval | Not specified | 29\.1 | Not specified | Not reported |
| DROP | Not specified | 60\.5 | Not specified | Not reported |
| GSM8k | Not specified | 85\.1 | Not specified | Not reported |
| IFEval | Not specified | 72\.3 | Not specified | Not reported |
| MATH | Not specified | 32\.5 | Not specified | Not reported |
| MMLU | Not specified | 61\.3 | Not specified | Not reported |
| PopQA | Not specified | 23\.2 | Not specified | Not reported |
| TruthQA | Not specified | 56\.5 | Not specified | Not reported |
| AVG | Not specified | 56\.5 | Not specified | Not reported |
| AE2 | Not specified | 29\.1 | Not specified | Not reported |
| IFE | Not specified | 72\.3 | Not specified | Not reported |
| PQA | Not specified | 23\.2 | Not specified | Not reported |
| TQA | Not specified | 56\.5 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/allenai/OLMo\-2\-1124\-7B\-Instruct](<https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2501\.00656](<https://arxiv.org/abs/2501.00656>) |
| Code repository | [https://github\.com/allenai/OLMo](<https://github.com/allenai/OLMo>) |
| Citation | @article\{olmo20242olmo2furious,<br>      title=\{2 OLMo 2 Furious\}, <br>      author=\{Team OLMo and Pete Walsh and Luca Soldaini and Dirk Groeneveld and Kyle Lo and Shane Arora and Akshita Bhagia and Yuling Gu and Shengyi Huang and Matt Jordan and Nathan Lambert and Dustin Schwenk and Oyvind Tafjord and Taira Anderson and David Atkinson and Faeze Brahman and Christopher Clark and Pradeep Dasigi and Nouha Dziri and Michal Guerquin and Hamish Ivison and Pang Wei Koh and Jiacheng Liu and Saumya Malik and William Merrill and Lester James V\. Miranda and Jacob Morrison and Tyler Murray and Crystal Nam and Valentina Pyatkin and Aman Rangapur and Michael Schmitz and Sam Skjonsberg and David Wadden and Christopher Wilhelm and Michael Wilson and Luke Zettlemoyer and Ali Farhadi and Noah A\. Smith and Hannaneh Hajishirzi\},<br>      year=\{2024\},<br>      eprint=\{2501\.00656\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2501\.00656\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
