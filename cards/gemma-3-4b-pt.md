# Model Card: gemma\-3\-4b\-pt

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-4b\-pt\.json](<./gemma-3-4b-pt.json>)<br>
SHA-256: `2ec90840b344d23ef03e8cb080220ee33b88bf301fc71cd54bf605168ec2d34b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | google/gemma\-3\-4b\-pt |
| Name | gemma\-3\-4b\-pt |
| Developed by | Google DeepMind |
| Model type | image\-text\-to\-text |
| License | gemma |
| Version | cc012e0a6d0787b4adcc0fa2c4da74402494554d |
| Summary | The publisher describes gemma\-3\-4b\-pt as a pretrained, multimodal, open\-weight model with text\-and\-image input and text output\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | gemma3 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | multimodal \(topology unspecified\) |
| Num parameters | 4,300,079,472 total stored parameters \(safetensors metadata\) |
| Context length | 128K tokens \(README\-declared context length\) |
| Precision | bfloat16 stored tensor weights \(safetensors parameter\-count metadata\) |
| Model size | 8\.01 GiB estimated tensor payload \(8,600,158,944 bytes; from safetensors dtype counts\) |
| Input / output | input: image and text<br>output: text<br>model stage: pretrained/base |

## Training Context

| Field | Value |
| --- | --- |
| Training data | Publisher\-listed source categories: web documents, code, mathematics, images\. Language coverage is reported above 140 languages\. |
| Training data size | 4B model: 4 trillion tokens |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | Gated Hugging Face repository with declared weight files |
| Downloads | 74,127 at frozen Hugging Face metadata snapshot |
| Likes | 160 at frozen Hugging Face metadata snapshot |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The frozen README provides 41 exact\-target benchmark scores; examples: HellaSwag: 77\.2; BoolQ: 72\.3; PIQA: 79\.6\. |
| Safety evaluations | The README reports Gemma\-family, all\-model\-size improvements over earlier releases for child safety, content safety, representational harms, and ungrounded inference\. The tests omitted safety filters and used English prompts; the source does not provide PT/IT\- or checkpoint\-specific results\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| HellaSwag | README\-reported score | 77\.2 | 10\-shot | Not reported |
| BoolQ | README\-reported score | 72\.3 | 0\-shot | Not reported |
| PIQA | README\-reported score | 79\.6 | 0\-shot | Not reported |
| SocialIQA | README\-reported score | 51\.9 | 0\-shot | Not reported |
| TriviaQA | README\-reported score | 65\.8 | 5\-shot | Not reported |
| Natural Questions | README\-reported score | 20\.0 | 5\-shot | Not reported |
| ARC\-c | README\-reported score | 56\.2 | 25\-shot | Not reported |
| ARC\-e | README\-reported score | 82\.4 | 0\-shot | Not reported |
| WinoGrande | README\-reported score | 64\.7 | 5\-shot | Not reported |
| BIG\-Bench Hard | README\-reported score | 50\.9 | few\-shot | Not reported |
| DROP | README\-reported score | 60\.1 | 1\-shot | Not reported |
| MMLU | README\-reported score | 59\.6 | 5\-shot | Not reported |
| MMLU \(Pro COT\) | README\-reported score | 29\.2 | 5\-shot | Not reported |
| AGIEval | README\-reported score | 42\.1 | 3\-5\-shot | Not reported |
| MATH | README\-reported score | 24\.2 | 4\-shot | Not reported |
| GSM8K | README\-reported score | 38\.4 | 8\-shot | Not reported |
| GPQA | README\-reported score | 15\.0 | 5\-shot | Not reported |
| MBPP | README\-reported score | 46\.0 | 3\-shot | Not reported |
| HumanEval | README\-reported score | 36\.0 | 0\-shot | Not reported |
| MGSM | README\-reported score | 34\.7 | Benchmark Results; setting not stated | Not reported |
| Global\-MMLU\-Lite | README\-reported score | 57\.0 | Benchmark Results; setting not stated | Not reported |
| WMT24\+\+ | ChrF | 48\.4 | Benchmark Results; setting not stated | Not reported |
| FloRes | README\-reported score | 39\.2 | Benchmark Results; setting not stated | Not reported |
| XQuAD \(all\) | README\-reported score | 68\.0 | Benchmark Results; setting not stated | Not reported |
| ECLeKTic | README\-reported score | 11\.0 | Benchmark Results; setting not stated | Not reported |
| IndicGenBench | README\-reported score | 57\.2 | Benchmark Results; setting not stated | Not reported |
| COCOcap | README\-reported score | 102 | Benchmark Results; setting not stated | Not reported |
| DocVQA | README\-reported score | 72\.8 | Benchmark Results; setting not stated | val |
| InfoVQA | README\-reported score | 44\.1 | Benchmark Results; setting not stated | val |
| MMMU \(pt\) | README\-reported score | 39\.2 | Benchmark Results; setting not stated | Not reported |
| TextVQA | README\-reported score | 58\.9 | Benchmark Results; setting not stated | val |
| RealWorldQA | README\-reported score | 45\.5 | Benchmark Results; setting not stated | Not reported |
| ReMI | README\-reported score | 27\.3 | Benchmark Results; setting not stated | Not reported |
| AI2D | README\-reported score | 63\.2 | Benchmark Results; setting not stated | Not reported |
| ChartQA | README\-reported score | 63\.6 | Benchmark Results; setting not stated | Not reported |
| VQAv2 | README\-reported score | 63\.9 | Benchmark Results; setting not stated | Not reported |
| BLINK | README\-reported score | 38\.0 | Benchmark Results; setting not stated | Not reported |
| OKVQA | README\-reported score | 51\.0 | Benchmark Results; setting not stated | Not reported |
| TallyQA | README\-reported score | 42\.5 | Benchmark Results; setting not stated | Not reported |
| SpatialSense VQA | README\-reported score | 50\.9 | Benchmark Results; setting not stated | Not reported |
| CountBenchQA | README\-reported score | 26\.1 | Benchmark Results; setting not stated | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-4b\-pt/blob/cc012e0a6d0787b4adcc0fa2c4da74402494554d/README\.md](<https://huggingface.co/google/gemma-3-4b-pt/blob/cc012e0a6d0787b4adcc0fa2c4da74402494554d/README.md>) |
| Technical report | [https://goo\.gle/Gemma3Report](<https://goo.gle/Gemma3Report>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.release_date`, `lineage.base_models`, `lineage.derivatives`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.human_evals`, `links.system_card`, `links.code_repository`.
