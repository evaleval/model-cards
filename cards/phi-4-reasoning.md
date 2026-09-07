# Model Card: Phi\-4\-reasoning Model Card

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [phi\-4\-reasoning\.json](<./phi-4-reasoning.json>)<br>
SHA-256: `fc0c5154ced7e72553840bc6c5b1d432bad03cdb0f5bfbd1512a0c5d0664db16`

## Identity

| Field | Value |
| --- | --- |
| Model ID | microsoft/phi\-4\-reasoning |
| Name | Phi\-4\-reasoning Model Card |
| Developed by | microsoft \(Hub organization\) |
| Model type | reasoning model |
| License | mit |
| Release date | 2025\-04\-09 \(Hugging Face repository creation date\) |
| Version | 1de18ec97600877ce63dbf60c73b998da99f0195 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | microsoft/phi\-4 (base model; Kind: finetune) |
| Model family | phi 4 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,659,507,200 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.3 GiB of safetensors weights \(29,319,042,992 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | 16B tokens, ~8\.3B unique tokens |
| Data cutoff | Static model trained on an offline dataset with cutoff dates of March 2025 and earlier for publicly available data |
| Adaptations | Phi\-4\-reasoning is a supervised fine\-tuned and reinforcement learning post\-trained reasoning model derived from Phi\-4, with additional safety post\-training via supervised fine\-tuning\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 27,743 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 227 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| AIME 24 | Not specified | 75\.3 | Not specified | Not reported |
| AIME 25 | Not specified | 62\.9 | Not specified | Not reported |
| OmniMath | Not specified | 76\.6 | Not specified | Not reported |
| GPQA\-D | Not specified | 65\.8 | Not specified | Not reported |
| LiveCodeBench | Not specified | 53\.8 | Not specified | Not reported |
| FlenQA 3K\-token subset | Not specified | 97\.7 | Not specified | Not reported |
| IFEval Strict | Not specified | 83\.4 | Not specified | Not reported |
| ArenaHard | Not specified | 73\.3 | Not specified | Not reported |
| HumanEvalPlus | Not specified | 92\.9 | Not specified | Not reported |
| MMLUPro | Not specified | 74\.3 | Not specified | Not reported |
| PhiBench 2\.21 | Not specified | 70\.6 | Not specified | Not reported |
| LCB 8 / 24 \- 1 / | pass@1 | 53\.8 | Not specified | Not reported |
| Codeforces | pass@1 | 1736 | Not specified | Not reported |
| FlenQA 3K\-token subset | pass@1 | 97\.7 | temperature 0\.8 | Not reported |
| IFEval Strict | pass@1 | 83\.4 | temperature 0\.8 | Not reported |
| ArenaHard | pass@1 | 73\.3 | temperature 0\.8 | Not reported |
| HumanEvalPlus | pass@1 | 92\.9 | temperature 0\.8 | Not reported |
| MMLUPro | pass@1 | 74\.3 | temperature 0\.8 | Not reported |
| No Context \- Precision | pass@1 | 23\.2 | temperature 0\.8 | Not reported |
| With Context \- Precision | pass@1 | 93\.8 | temperature 0\.8 | Not reported |
| No Context \- Recall | pass@1 | 4\.9 | temperature 0\.8 | Not reported |
| With Context \- Recall | pass@1 | 74\.8 | temperature 0\.8 | Not reported |
| Toxic category | pass@1 | 86\.7 | temperature 0\.8 | Not reported |
| Neutral category | pass@1 | 84\.7 | temperature 0\.8 | Not reported |
| PhiBench 2\.21 | pass@1 | 70\.6 | temperature 0\.8 | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/microsoft/phi\-4\-reasoning](<https://huggingface.co/microsoft/phi-4-reasoning>) |
| Technical report | [https://arxiv\.org/abs/2504\.21318](<https://arxiv.org/abs/2504.21318>) |
| Citation | The developer asks users to cite the Phi\-4\-reasoning Technical Report\. |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card provides only high\-level architecture and post\-training description, with no reported evaluations or details of the RL/safety SFT process, so inner workings and evaluation evidence are undocumented\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | Card states only an offline dataset with cutoff March 2025 and earlier, without collection, curation, or composition details, so training data transparency is limited\. | Proper documentation contains information about how a model's data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | Open\-weight text\-output reasoning model with no reported factual accuracy or grounding evaluations, so plausible hallucination risk in generated reasoning chains\. | Hallucinations generate factually inaccurate or untruthful content relative to the model's training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | Reasoning model outputs are likely to be trusted by users, but the card reports no calibration or human\-AI decision\-making evaluation, so over\-reliance risk is plausible\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model's output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model's output when the model's output is likely incorrect\. Under\-reliance is the opposite, where the person doesn't trust the model but should\. |
| [Incomplete usage definition](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-usage-definition.html>) | Card labels it a general reasoning model and gives no intended\-use or out\-of\-scope use cases, leaving downstream risk assessment incomplete\. | Since foundation models can be used for many purposes, a model's intended use is important for defining the relevant risks of that model\. As the use changes, the relevant risks might correspondingly change\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
