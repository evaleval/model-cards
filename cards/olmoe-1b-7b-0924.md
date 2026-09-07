# Model Card: OLMoE\-1B\-7B\-0924

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [olmoe\-1b\-7b\-0924\.json](<./olmoe-1b-7b-0924.json>)<br>
SHA-256: `74dfd52066910b0be3819471af6e5b3009ff6ac6d972579b72f312d21c573a4d`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allenai/OLMoE\-1B\-7B\-0924 |
| Name | OLMoE\-1B\-7B\-0924 |
| Developed by | allenai \(Hub organization\) |
| Model type | Mixture\-of\-Experts language model |
| License | apache\-2\.0 |
| Release date | 2024\-07\-20 \(Hugging Face repository creation date\) |
| Version | 6d84c48581ece794365f2b8e9cfb043c68ade9c5 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | OLMoE |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 6,919,161,856 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 12\.9 GiB of safetensors weights \(13,838,721,960 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was pretrained on the OLMoE\-mix\-0924 dataset, as stated in the Hugging Face readme and the associated GitHub instructions\. |
| Adaptations | The base model was further adapted to create an instruct version; the readme also documents SFT, DPO, and KTO adaptation recipes, and the released checkpoint is used as the starting point for adaptation\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 124,737 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 148 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | Not specified | 54\.1 | Not specified | Not reported |
| HellaSwag | Not specified | 80\.0 | Not specified | Not reported |
| ARC\-Chall\. | Not specified | 62\.1 | Not specified | Not reported |
| ARC\-Easy | Not specified | 84\.2 | Not specified | Not reported |
| PIQA | Not specified | 79\.8 | Not specified | Not reported |
| WinoGrande | Not specified | 70\.2 | Not specified | Not reported |
| Avg\. | Not specified | 39\.7 | Not specified | Not reported |
| Avg\. | Not specified | 39\.8 | Not specified | Not reported |
| MMLU | Not specified | 54\.3 | 0\-shot CoT | Not reported |
| MMLU | Not specified | 54\.6 | 0\-shot CoT | Not reported |
| PopQA | Not specified | 21\.0 | 15\-shot | Not reported |
| PopQA | Not specified | 20\.6 | 15\-shot | Not reported |
| TruthfulQA | Not specified | 44\.7 | 6\-shot | Not reported |
| TruthfulQA | Not specified | 49\.1 | 6\-shot | Not reported |
| BigBenchHard | Not specified | 36\.6 | 3\-shot CoT | Not reported |
| BigBenchHard | Not specified | 36\.8 | 3\-shot CoT | Not reported |
| DROP | Not specified | 34\.7 | 3\-shot | Not reported |
| DROP | Not specified | 34\.5 | 3\-shot | Not reported |
| MATH | Not specified | 8\.2 | 4\-shot CoT | Not reported |
| GSM8K | Not specified | 42\.5 | 8\-shot CoT | Not reported |
| GSM8K | Not specified | 47\.4 | 8\-shot CoT | Not reported |
| HumanEval | pass@10 | 63\.7 | Not specified | Not reported |
| HumanEval | pass@10 | 63\.0 | Not specified | Not reported |
| HumanEval\+ | pass@10 | 57\.4 | Not specified | Not reported |
| HumanEval\+ | pass@10 | 58\.9 | Not specified | Not reported |
| IFEval | Not specified | 41\.2 | Not specified | Not reported |
| IFEval | Not specified | 45\.3 | Not specified | Not reported |
| AlpacaEval 2 | Not specified | 6\.4 | Not specified | Not reported |
| AlpacaEval 2 | Not specified | 7\.5 | Not specified | Not reported |
| Safety | Not specified | 65\.8 | Not specified | Not reported |
| Safety | Not specified | 51\.4 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/allenai/OLMoE\-1B\-7B\-0924](<https://huggingface.co/allenai/OLMoE-1B-7B-0924>) |
| Technical report | [https://arxiv\.org/abs/2409\.02060](<https://arxiv.org/abs/2409.02060>) |
| Code repository | [https://github\.com/allenai/OLMoE](<https://github.com/allenai/OLMoE>) |
| Citation | @misc\{muennighoff2024olmoeopenmixtureofexpertslanguage,<br>      title=\{OLMoE: Open Mixture\-of\-Experts Language Models\}, <br>      author=\{Niklas Muennighoff and Luca Soldaini and Dirk Groeneveld and Kyle Lo and Jacob Morrison and Sewon Min and Weijia Shi and Pete Walsh and Oyvind Tafjord and Nathan Lambert and Yuling Gu and Shane Arora and Akshita Bhagia and Dustin Schwenk and David Wadden and Alexander Wettig and Binyuan Hui and Tim Dettmers and Douwe Kiela and Ali Farhadi and Noah A\. Smith and Pang Wei Koh and Amanpreet Singh and Hannaneh Hajishirzi\},<br>      year=\{2024\},<br>      eprint=\{2409\.02060\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2409\.02060\}, <br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | OLMoE\-1B\-7B\-0924 is a 1B\-parameter open\-weight text\-generation model pretrained on OLMoE\-mix\-0924 with no reported evaluation or guardrails in the card summary, so it can plausibly produce factually inaccurate or untruthful text\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
