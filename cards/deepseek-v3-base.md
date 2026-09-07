# Model Card: DeepSeek\-V3\-Base

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [deepseek\-v3\-base\.json](<./deepseek-v3-base.json>)<br>
SHA-256: `c2317d6ad97e9f4b90687a6efe8e7fd45b27eef314f2313f0a49f8d11c48e2a5`

## Identity

| Field | Value |
| --- | --- |
| Model ID | deepseek\-ai/DeepSeek\-V3\-Base |
| Name | DeepSeek\-V3\-Base |
| Developed by | deepseek\-ai \(Hub organization\) |
| Model type | Mixture\-of\-Experts \(MoE\) language model |
| Release date | 2024\-12\-25 \(Hugging Face repository creation date\) |
| Version | afb92e1fa402c2be2a9eb085312bb02e0384d6c7 |
| Summary | DeepSeek\-V3\-Base is a large Mixture\-of\-Experts language model with 671B total parameters and 37B activated per token\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | DeepSeek V3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 684,531,386,000 parameters \(safetensors metadata\) |
| Context length | 163,840 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F8\_E4M3 \(safetensors weight dtype\) |
| Model size | 641\.3 GiB of safetensors weights \(688,586,727,753 bytes\) in F8\_E4M3 |
| Input / output | text in, text out |

## Training Context

| Field | Value |
| --- | --- |
| Training data size | 14\.8 trillion tokens |
| Adaptations | DeepSeek\-V3 underwent Supervised Fine\-Tuning and Reinforcement Learning after pre\-training\. It also incorporated a methodology to distill reasoning capabilities from a DeepSeek R1 series long\-Chain\-of\-Thought model\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 6,009 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 1,705 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that DeepSeek\-V3 outperforms other open\-source models and is competitive with leading closed\-source models, with particularly strong results on mathematics and code benchmarks\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Pile\-test | Not specified | 0\.548 | Not specified | Not reported |
| BBH | exact match | 87\.5 | 3\-shot | Not reported |
| MMLU | accuracy | 87\.1 | 5\-shot | Not reported |
| MMLU\-Redux | accuracy | 86\.2 | 5\-shot | Not reported |
| MMLU\-Pro | accuracy | 64\.4 | 5\-shot | Not reported |
| DROP | F1 | 89\.0 | 3\-shot | Not reported |
| ARC\-Easy | accuracy | 98\.9 | 25\-shot | Not reported |
| ARC\-Challenge | accuracy | 95\.3 | 25\-shot | Not reported |
| HellaSwag | accuracy | 88\.9 | 10\-shot | Not reported |
| PIQA | accuracy | 84\.7 | 0\-shot | Not reported |
| WinoGrande | accuracy | 84\.9 | 5\-shot | Not reported |
| RACE\-Middle | accuracy | 67\.1 | 5\-shot | Not reported |
| RACE\-High | accuracy | 51\.3 | 5\-shot | Not reported |
| TriviaQA | exact match | 82\.9 | 5\-shot | Not reported |
| NaturalQuestions | exact match | 40\.0 | 5\-shot | Not reported |
| AGIEval | accuracy | 79\.6 | 0\-shot | Not reported |
| HumanEval | pass@1 | 65\.2 | 0\-shot | Not reported |
| MBPP | pass@1 | 75\.4 | 3\-shot | Not reported |
| LiveCodeBench\-Base | pass@1 | 19\.4 | 3\-shot | Not reported |
| CRUXEval\-I | accuracy | 67\.3 | 2\-shot | Not reported |
| CRUXEval\-O | accuracy | 69\.8 | 2\-shot | Not reported |
| GSM8K | exact match | 89\.3 | 8\-shot | Not reported |
| MATH | exact match | 61\.6 | 4\-shot | Not reported |
| MGSM | exact match | 79\.8 | 8\-shot | Not reported |
| CMath | exact match | 90\.7 | 3\-shot | Not reported |
| CLUEWSC | exact match | 82\.7 | 5\-shot | Not reported |
| C\-Eval | accuracy | 90\.1 | 5\-shot | Not reported |
| CMMLU | accuracy | 88\.8 | 5\-shot | Not reported |
| CMRC | exact match | 76\.3 | 1\-shot | Not reported |
| C3 | accuracy | 78\.6 | 0\-shot | Not reported |
| CCPM | accuracy | 92\.0 | 0\-shot | Not reported |
| MMMLU\-non\-English | accuracy | 79\.4 | 5\-shot | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/deepseek\-ai/DeepSeek\-V3\-Base](<https://huggingface.co/deepseek-ai/DeepSeek-V3-Base>) |
| Technical report | [https://arxiv\.org/abs/2412\.19437](<https://arxiv.org/abs/2412.19437>) |
| Code repository | [https://github\.com/deepseek\-ai/DeepSeek\-V3](<https://github.com/deepseek-ai/DeepSeek-V3>) |
| Citation | @misc\{deepseekai2024deepseekv3technicalreport,<br>      title=\{DeepSeek\-V3 Technical Report\}, <br>      author=\{DeepSeek\-AI\},<br>      year=\{2024\},<br>      eprint=\{2412\.19437\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2412\.19437\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | DeepSeek\-V3\-Base is a text\-out language model with reported benchmark strengths in math/code but no stated factuality or grounding evaluation, so it plausibly generates inaccurate or fabricated text\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | The card states a 671B\-parameter Mixture\-of\-Experts model, implying substantial compute for pretraining and operation, with no reported environmental impact assessment\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | The card reports that DeepSeek\-V3 outperforms other open\-source models and is competitive with leading closed\-source models, which could encourage users to over\-trust its outputs despite no reported calibration or reliability evaluation\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.license`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
