# Model Card: OLMo\-2\-1124\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [olmo\-2\-1124\-7b\-instruct\.json](<./olmo-2-1124-7b-instruct.json>)<br>
SHA-256: `752b4f83a3c1ae794b03d8b538731055ae6f2fd5bcc121080a28af34080ad5bd`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allenai/OLMo\-2\-1124\-7B\-Instruct |
| Name | OLMo\-2\-1124\-7B\-Instruct |
| Developed by | allenai \(Hub organization\) |
| Model type | Text generation model\. |
| License | apache\-2\.0 |
| Release date | 2024\-12\-18 \(Hugging Face repository creation date\) |
| Version | 470b1fba1ae01581f270116362ee4aa1b97f4c84 |
| Summary | OLMo 2 7B Instruct is a post\-trained language model built from the OLMo\-2 7B November 2024 base through supervised finetuning, DPO, and RLVR\. |

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

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 61,617 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 50 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer\-reported table lists the instruct model&\#x27;s scores across a set of benchmarks, with an average of 54\.8 and notable results such as 85\.1 on GSM8k and 72\.3 on IFEval\. |

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

Unavailable agreed fields (not specified in the publication data): `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
