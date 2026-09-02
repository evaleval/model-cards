# Model Card: OLMo\-2\-1124\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [olmo\-2\-1124\-7b\-instruct\.json](<./olmo-2-1124-7b-instruct.json>)<br>
SHA-256: `6fc2d0b30020f94623bed390a1f69e1257da52aeaaec4da9b8af71f2e6b44f35`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allenai/OLMo\-2\-1124\-7B\-Instruct |
| Name | OLMo\-2\-1124\-7B\-Instruct |
| Developed by | allenai |
| Model type | text\-generation |
| License | apache\-2\.0 |
| Version | 470b1fba1ae01581f270116362ee4aa1b97f4c84 |
| Summary | The publisher describes OLMo\-2\-1124\-7B\-Instruct as an instruction\-tuned model\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | allenai/OLMo\-2\-1124\-7B\-DPO (base model) |
| Model family | olmo2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,298,617,344 total stored parameters \(safetensors metadata\) |
| Context length | 4,096 positions \(config max\_position\_embeddings; implementation limit, not an independently verified context window\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 13\.59 GiB estimated tensor payload \(14,597,234,688 bytes; from safetensors dtype counts\) |
| Input / output | input: text<br>output: text<br>model stage: instruction\-tuned |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Post\-training dataset IDs named in the exact\-target README: allenai/RLVR\-GSM, allenai/olmo\-2\-1124\-7b\-preference\-mix, allenai/tulu\-3\-sft\-olmo\-2\-mixture |
| Adaptations | Post\-training stages: supervised fine\-tuning, DPO, then RLVR\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Public Hugging Face repository with declared weight files |
| Downloads | 63,631 at frozen Hugging Face metadata snapshot |
| Likes | 50 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README provides 10 exact\-target benchmark scores; examples: AlpacaEval: 29\.1; BBH: 46\.6; DROP: 60\.5\. |
| Safety evaluations | README performance table reports Safety score 80\.6 \(README\-reported score; Performance; setting not stated\)\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| AlpacaEval | README\-reported score | 29\.1 | Performance; setting not stated | Not reported |
| BBH | README\-reported score | 46\.6 | Performance; setting not stated | Not reported |
| DROP | README\-reported score | 60\.5 | Performance; setting not stated | Not reported |
| GSM8k | README\-reported score | 85\.1 | Performance; setting not stated | Not reported |
| IFEval | README\-reported score | 72\.3 | Performance; setting not stated | Not reported |
| MATH | README\-reported score | 32\.5 | Performance; setting not stated | Not reported |
| MMLU | README\-reported score | 61\.3 | Performance; setting not stated | Not reported |
| Safety | README\-reported score | 80\.6 | Performance; setting not stated | Not reported |
| PopQA | README\-reported score | 23\.2 | Performance; setting not stated | Not reported |
| TruthQA | README\-reported score | 56\.5 | Performance; setting not stated | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/allenai/OLMo\-2\-1124\-7B\-Instruct/blob/470b1fba1ae01581f270116362ee4aa1b97f4c84/README\.md](<https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct/blob/470b1fba1ae01581f270116362ee4aa1b97f4c84/README.md>) |
| Technical report | [https://arxiv\.org/abs/2501\.00656](<https://arxiv.org/abs/2501.00656>) |
| Code repository | [https://github\.com/allenai/OLMo](<https://github.com/allenai/OLMo>) |
| Citation | @article\{olmo20242olmo2furious,<br>      title=\{2 OLMo 2 Furious\}, <br>      author=\{Team OLMo and Pete Walsh and Luca Soldaini and Dirk Groeneveld and Kyle Lo and Shane Arora and Akshita Bhagia and Yuling Gu and Shengyi Huang and Matt Jordan and Nathan Lambert and Dustin Schwenk and Oyvind Tafjord and Taira Anderson and David Atkinson and Faeze Brahman and Christopher Clark and Pradeep Dasigi and Nouha Dziri and Michal Guerquin and Hamish Ivison and Pang Wei Koh and Jiacheng Liu and Saumya Malik and William Merrill and Lester James V\. Miranda and Jacob Morrison and Tyler Murray and Crystal Nam and Valentina Pyatkin and Aman Rangapur and Michael Schmitz and Sam Skjonsberg and David Wadden and Christopher Wilhelm and Michael Wilson and Luke Zettlemoyer and Ali Farhadi and Noah A\. Smith and Hannaneh Hajishirzi\},<br>      year=\{2024\},<br>      eprint=\{2501\.00656\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2501\.00656\}, <br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `links.system_card`.
