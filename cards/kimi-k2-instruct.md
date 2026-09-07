# Model Card: kimi\-k2\-instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [kimi\-k2\-instruct\.json](<./kimi-k2-instruct.json>)<br>
SHA-256: `bda6a29784a20df3cafc66bed215c4a7f26d6c71ddbb8a6d89c147ad40eda5b9`

## Identity

| Field | Value |
| --- | --- |
| Model ID | moonshotai/kimi\-k2\-instruct |
| Name | kimi\-k2\-instruct |
| Developed by | moonshotai \(Hub organization\) |
| Model type | Mixture\-of\-Experts \(MoE\) large language model |
| License | other |
| Release date | 2025\-07\-11 \(Hugging Face repository creation date\) |
| Version | fd1984e2b7a3350dbf7305fe73a4ede25c14de50 |

## Lineage

| Field | Value |
| --- | --- |
| Model family | kimi k2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | mixture\-of\-experts |
| Num parameters | 1,026,408,235,864 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F8\_E4M3 \(safetensors weight dtype\) |
| Model size | 958\.5 GiB of safetensors weights \(1,029,190,981,272 bytes\) in F8\_E4M3 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | Kimi\-K2\-Instruct is a post\-trained version of the base model, optimized for general\-purpose chat and agentic use, and described as a reflex\-grade model without long thinking\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 160,774 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 2,377 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Kimi\-K2\-Instruct achieves state\-of\-the\-art open\-source performance on real\-world software engineering tasks, and describes its post\-training evaluation across multiple areas\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Basic | Not specified | 98\.04 | Not specified | Not reported |
| Basic | Not specified | 100 | Not specified | Not reported |
| Basic | Not specified | 97\.28 | Not specified | Not reported |
| Basic | Not specified | 77\.84 | Not specified | Not reported |
| Base64 | Not specified | 100 | Not specified | Not reported |
| Base64 | Not specified | 96\.97 | Not specified | Not reported |
| Base64 | Not specified | 98\.48 | Not specified | Not reported |
| Base64 | Not specified | 82\.93 | Not specified | Not reported |
| Prompt Injection | Not specified | 93\.14 | Not specified | Not reported |
| Prompt Injection | Not specified | 75\.76 | Not specified | Not reported |
| Prompt Injection | Not specified | 98\.39 | Not specified | Not reported |
| Prompt Injection | Not specified | 88\.33 | Not specified | Not reported |
| Prompt Injection | Not specified | 87\.8 | Not specified | Not reported |
| Iterative Jailbreak | Not specified | 92\.16 | Not specified | Not reported |
| Iterative Jailbreak | Not specified | 57\.57 | Not specified | Not reported |
| Iterative Jailbreak | Not specified | 63\.97 | Not specified | Not reported |
| Iterative Jailbreak | Not specified | 76\.67 | Not specified | Not reported |
| Iterative Jailbreak | Not specified | 43\.9 | Not specified | Not reported |
| Crescendo | Not specified | 64\.71 | Not specified | Not reported |
| Crescendo | Not specified | 56\.06 | Not specified | Not reported |
| Crescendo | Not specified | 85\.71 | Not specified | Not reported |
| Crescendo | Not specified | 96\.67 | Not specified | Not reported |
| Crescendo | Not specified | 68\.29 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/moonshotai/kimi\-k2\-instruct](<https://huggingface.co/moonshotai/kimi-k2-instruct>) |
| Code repository | [https://github\.com/moonshotai/Kimi\-K2](<https://github.com/moonshotai/Kimi-K2>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | Card reports only high\-level post\-training and benchmark claims for kimi\-k2\-instruct, with no details on training data, evaluation methodology, or inner workings, so transparency is limited\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Lack of training data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-transparency.html>) | The card does not state how kimi\-k2\-instruct&\#x27;s training data was collected, curated, or used, making training data transparency lacking\. | Proper documentation contains information about how a model&\#x27;s data was collected, curated, and used to train a model, including any synthetic data generation processes\. Without proper documentation it might be harder to satisfactorily explain the behavior of the model\. |
| [Incomplete AI agent evaluation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incomplete-ai-agent-evaluation-agentic.html>) | The model is explicitly optimized for agentic use and reports software engineering performance, but the card gives no agentic evaluation details, so agent evaluation is incomplete\. | Evaluating the performance or accuracy or an agent is difficult because of system complexity and open\-endedness\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.citation`.
