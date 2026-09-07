# Model Card: SmolLM2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [smollm2\-1\.7b\-instruct\.json](<./smollm2-1.7b-instruct.json>)<br>
SHA-256: `f83540db8db85cc8e798cc6c3429c5fde2218f81e0d63c99afc125e69144427a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | HuggingFaceTB/SmolLM2\-1\.7B\-Instruct |
| Name | SmolLM2 |
| Developed by | HuggingFaceTB \(Hub organization\) |
| Model type | Text generation model |
| License | apache\-2\.0 |
| Release date | 2024\-10\-31 \(Hugging Face repository creation date\) |
| Version | 31b70e2e869a7173562077fd711b654946d38674 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | HuggingFaceTB/SmolLM2\-1\.7B (base model; Kind: quantized) |
| Model family | SmolLM2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 1,711,376,384 parameters \(safetensors metadata\) |
| Context length | 8,192 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 3\.2 GiB of safetensors weights \(3,422,777,952 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | SmolLM2 was pretrained on about 11 trillion tokens from a mixture of web text and specialized datasets, including FineWeb\-Edu, DCLM, The Stack, and newly curated mathematics and coding datasets\. |
| Training data size | 11 trillion tokens \(approximately two epochs on the collected datasets\) |
| Adaptations | The instruct version was developed through supervised fine\-tuning \(SFT\) using public and curated datasets, followed by Direct Preference Optimization \(DPO\) with UltraFeedback\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 223,283 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 753 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that SmolLM2\-1\.7B\-Instruct shows strong performance in instruction\-following, reasoning, and math, and also supports function calling with a score of 27% on the BFCL Leaderboard\. |
| Safety evaluations | The developer notes that SmolLM2 models primarily understand and generate English content, and that generated text may not always be factually accurate, logically consistent, or free from training\-data biases, so the models should be used as assistive tools\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MT\-Bench | Not specified | 6\.13 | Not specified | Not reported |
| OpenRewrite\-Eval | Not specified | 44\.9 | Not specified | Not reported |
| HellaSwag | Not specified | 66\.1 | Not specified | Not reported |
| ARC | Not specified | 51\.7 | Not specified | Not reported |
| PIQA | Not specified | 74\.4 | Not specified | Not reported |
| BBH | Not specified | 32\.2 | 3\-shot | Not reported |
| MATH | Not specified | 21 | 4\-shot | Not reported |
| HumanEval | Not specified | 28\.1 | Not specified | Not reported |
| MTB | Not specified | 6\.11 | Not specified | Not reported |
| GSM8K | Not specified | 47\.54 | Not specified | Not reported |
| MATH | Not specified | 19\.64 | Not specified | Not reported |
| ARC\-C | Not specified | 42\.49 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/HuggingFaceTB/SmolLM2\-1\.7B\-Instruct](<https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2502\.02737](<https://arxiv.org/abs/2502.02737>) |
| Code repository | [https://github\.com/huggingface/smollm](<https://github.com/huggingface/smollm>) |
| Citation | @misc\{allal2025smollm2smolgoesbig,<br>      title=\{SmolLM2: When Smol Goes Big \-\- Data\-Centric Training of a Small Language Model\}, <br>      author=\{Loubna Ben Allal and Anton Lozhkov and Elie Bakouch and Gabriel Martín Blázquez and Guilherme Penedo and Lewis Tunstall and Andrés Marafioti and Hynek Kydlíček and Agustín Piqueres Lajarín and Vaibhav Srivastav and Joshua Lochner and Caleb Fahlgren and Xuan\-Son Nguyen and Clémentine Fourrier and Ben Burtenshaw and Hugo Larcher and Haojun Zhao and Cyril Zakka and Mathieu Morlon and Colin Raffel and Leandro von Werra and Thomas Wolf\},<br>      year=\{2025\},<br>      eprint=\{2502\.02737\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2502\.02737\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | Card states generated text may not always be factually accurate, logically consistent, or free from training\-data biases, and the model is an open\-weight text generator\. | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | Card explicitly says the model should be used as an assistive tool because outputs may be inaccurate/inconsistent, implying risk of over\-reliance on its text generation\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |
| [Function calling hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/function-calling-hallucination-agentic.html>) | Card reports function calling support with only 27% on BFCL, indicating a concrete risk of incorrect function calls/parameters\. | AI agents might make mistakes when generating function calls \(calls to tools to execute actions\)\. Those function calls might result in incorrect, unnecessary or harmful actions\. Examples: Generating wrong functions or wrong parameters for the functions\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | Card notes the model primarily understands/generates English content and may contain training\-data biases, suggesting training data may not represent all populations/languages\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.data_cutoff`, `evaluation.human_evals`, `links.system_card`.
