# Model Card: gemma\-3\-4b\-pt

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-4b\-pt\.json](<./gemma-3-4b-pt.json>)<br>
SHA-256: `70dc71b3a77591f98592d6eda18ef02829f26cacead0eacccc374234f9b4867f`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-4b\-pt |
| Name | gemma\-3\-4b\-pt |
| Developed by | google \(Hub organization\) |
| License | gemma |
| Release date | 2025\-02\-20 \(Hugging Face repository creation date\) |
| Version | cc012e0a6d0787b4adcc0fa2c4da74402494554d |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma 3 |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 4,300,079,472 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 8\.0 GiB of safetensors weights \(8,600,277,880 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The 4B model was trained on a text dataset covering a wide variety of sources, including web documents in over 140 languages, code, mathematics, and images\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 74,967 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 160 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the model was evaluated across a broad set of text\-generation and multimodal benchmarks, with scores listed for many datasets\. The stated results cover reasoning, knowledge, math, coding, translation, and vision\-language tasks\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HellaSwag | Not specified | 77\.2 | 10\-shot | Not reported |
| BoolQ | Not specified | 72\.3 | 0\-shot | Not reported |
| PIQA | Not specified | 79\.6 | 0\-shot | Not reported |
| SocialIQA | Not specified | 51\.9 | 0\-shot | Not reported |
| TriviaQA | Not specified | 65\.8 | 5\-shot | Not reported |
| Natural Questions | Not specified | 20\.0 | 5\-shot | Not reported |
| ARC\-c | Not specified | 56\.2 | 25\-shot | Not reported |
| ARC\-e | Not specified | 82\.4 | 0\-shot | Not reported |
| WinoGrande | Not specified | 64\.7 | 5\-shot | Not reported |
| BIG\-Bench Hard | Not specified | 50\.9 | few\-shot | Not reported |
| DROP | Not specified | 60\.1 | 1\-shot | Not reported |
| MMLU | Not specified | 59\.6 | 5\-shot | Not reported |
| MMLU | Not specified | 29\.2 | 5\-shot | Not reported |
| AGIEval | Not specified | 42\.1 | 5\-shot | Not reported |
| MATH | Not specified | 24\.2 | 4\-shot | Not reported |
| GSM8K | Not specified | 38\.4 | 8\-shot | Not reported |
| GPQA | Not specified | 15\.0 | 5\-shot | Not reported |
| MBPP | Not specified | 46\.0 | 3\-shot | Not reported |
| HumanEval | Not specified | 36\.0 | 0\-shot | Not reported |
| MGSM | Not specified | 34\.7 | Not specified | Not reported |
| Global\-MMLU\-Lite | Not specified | 57\.0 | Not specified | Not reported |
| WMT24\+\+ | Not specified | 48\.4 | Not specified | Not reported |
| FloRes | Not specified | 39\.2 | Not specified | Not reported |
| XQuAD | Not specified | 68\.0 | Not specified | Not reported |
| ECLeKTic | Not specified | 11\.0 | Not specified | Not reported |
| IndicGenBench | Not specified | 57\.2 | Not specified | Not reported |
| COCOcap | Not specified | 102 | Not specified | Not reported |
| DocVQA | Not specified | 72\.8 | Not specified | Not reported |
| InfoVQA | Not specified | 44\.1 | Not specified | Not reported |
| MMMU | Not specified | 39\.2 | Not specified | Not reported |
| TextVQA | Not specified | 58\.9 | Not specified | Not reported |
| RealWorldQA | Not specified | 45\.5 | Not specified | Not reported |
| ReMI | Not specified | 27\.3 | Not specified | Not reported |
| AI2D | Not specified | 63\.2 | Not specified | Not reported |
| ChartQA | Not specified | 63\.6 | Not specified | Not reported |
| VQAv2 | Not specified | 63\.9 | Not specified | Not reported |
| BLINK | Not specified | 38\.0 | Not specified | Not reported |
| OKVQA | Not specified | 51\.0 | Not specified | Not reported |
| TallyQA | Not specified | 42\.5 | Not specified | Not reported |
| SpatialSense VQA | Not specified | 50\.9 | Not specified | Not reported |
| CountBenchQA | Not specified | 26\.1 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-4b\-pt](<https://huggingface.co/google/gemma-3-4b-pt>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | gated access and multimodal input \(image, text\) means users may send confidential images/text to the model, but the card does not report any data\-handling safeguards\. | Confidential information might be included as a part of the prompt that is sent to the model\. |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | the model accepts image and text prompts and was trained on web documents/code/images, so users may include copyrighted or licensed material in prompts without stated protections\. | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Impact on the environment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/impact-on-the-environment.html>) | the card reports a 4B multimodal model trained on large web/code/image data, implying substantial training compute and associated energy/water use\. | AI, and large generative models in particular, might produce increased carbon emissions and increase water usage for their training and operation\. |
| [Incorrect risk testing](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/incorrect-risk-testing.html>) | the card lists benchmark scores for reasoning, knowledge, math, coding, translation, and vision\-language tasks but does not report safety or risk\-specific evaluations, so risk measurements are incomplete\. | A metric selected to measure or track a risk is incorrectly selected, incompletely measuring the risk, or measuring the wrong risk for the given context\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`.
