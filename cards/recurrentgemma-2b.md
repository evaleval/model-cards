# Model Card: recurrentgemma\-2b

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [recurrentgemma\-2b\.json](<./recurrentgemma-2b.json>)<br>
SHA-256: `43ff43d1abb0d4745b7554c1204b1e9e46bb56b4c51f506fee544231dc149b4a`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/recurrentgemma\-2b |
| Name | recurrentgemma\-2b |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2024\-04\-06 \(Hugging Face repository creation date\) |
| Version | 3620f4ca9c5d16ee56c00180474a3201ec7f734a |

## Lineage

| Field | Value |
| --- | --- |
| Model family | recurrentgemma |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 2,682,862,080 parameters \(safetensors metadata\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 10\.0 GiB of safetensors weights \(10,731,506,136 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The 2B base RecurrentGemma checkpoint was trained on the same data and with the same processing as the Gemma model family\. |
| Adaptations | This is the 2B base version of RecurrentGemma, so no post\-training or alignment is described for this checkpoint\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 2,924 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 99 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that RecurrentGemma models perform comparably to Gemma models while being faster during inference and requiring less memory, especially on long sequences\. |
| Safety evaluations | The developer states that ethics and safety evaluation results are within acceptable thresholds for internal policies covering child safety, content safety, representational harms, memorization, and large\-scale harms\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| MMLU | top\-1 | 38\.4 | 5\-shot | Not reported |
| HellaSwag | Not specified | 71\.0 | 0\-shot | Not reported |
| PIQA | Not specified | 78\.5 | 0\-shot | Not reported |
| SocialIQA | Not specified | 51\.8 | 0\-shot | Not reported |
| BoolQ | Not specified | 71\.3 | 0\-shot | Not reported |
| WinoGrande | score | 67\.8 | Not specified | Not reported |
| CommonsenseQA | Not specified | 63\.7 | 7\-shot | Not reported |
| OpenBookQA | Not specified | 51\.8 | Not specified | Not reported |
| ARC\-e | Not specified | 78\.8 | Not specified | Not reported |
| ARC\-c | Not specified | 52\.0 | Not specified | Not reported |
| TriviaQA | Not specified | 52\.5 | 5\-shot | Not reported |
| Natural Questions | Not specified | 11\.5 | 5\-shot | Not reported |
| HumanEval | pass@1 | 21\.3 | Not specified | Not reported |
| MBPP | Not specified | 28\.8 | 3\-shot | Not reported |
| GSM8K | Not specified | 13\.4 | maj@1 | Not reported |
| MATH | Not specified | 11\.0 | 4\-shot | Not reported |
| AGIEval | Not specified | 39\.3 | Not specified | Not reported |
| BIG\-Bench | Not specified | 55\.2 | Not specified | Not reported |
| Average | Not specified | 56\.1 | Not specified | Not reported |
| RealToxicity | Not specified | 9\.8 | Not specified | Not reported |
| BOLD | Not specified | 52\.3 | Not specified | Not reported |
| CrowS\-Pairs | top\-1 | 41\.1 | Not specified | Not reported |
| BBQ Ambig | top\-1 | 62\.6 | Not specified | Not reported |
| BBQ Disambig | top\-1 | 58\.4 | Not specified | Not reported |
| Winogender | top\-1 | 55\.1 | Not specified | Not reported |
| TruthfulQA | Not specified | 42\.7 | Not specified | Not reported |
| WinoBias 12 | Not specified | 56\.4 | Not specified | Not reported |
| WinoBias 22 | Not specified | 75\.4 | Not specified | Not reported |
| Toxigen | Not specified | 50\.0 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/recurrentgemma\-2b](<https://huggingface.co/google/recurrentgemma-2b>) |
| Citation | @article\{recurrentgemma\_2024,<br>    title=\{RecurrentGemma\},<br>    url=\{\},<br>    DOI=\{\},<br>    publisher=\{Kaggle\},<br>    author=\{Griffin Team, Alexsandar Botev and Soham De and Samuel L Smith and Anushan Fernando and George\-Christian Muraru and Ruba Haroun and Leonard Berrada et al\.\},<br>    year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | gated base text model trained on the same data as Gemma with no post\-training or alignment described \-&gt; users may input copyrighted text into prompts, and the card does not describe mitigation for IP in prompts | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | gated base text model with no post\-training or alignment described \-&gt; users may input confidential information into prompts, and the card does not describe mitigation for confidential data in prompts | Confidential information might be included as a part of the prompt that is sent to the model\. |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | base text\-generation model trained on large web\-scale data with no post\-training or alignment described \-&gt; may generate factually inaccurate or ungrounded text | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | base text model with no post\-training or alignment described and only developer\-reported safety evaluations \-&gt; users may over\-trust its outputs in downstream decision\-making without evidence of reliability | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | reported safety evaluations are only stated to be within internal thresholds for broad categories, with no metrics or details provided \-&gt; the card&\#x27;s risk testing may not fully measure the relevant risks | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
