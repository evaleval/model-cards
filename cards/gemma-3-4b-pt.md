# Model Card: gemma\-3\-4b\-pt

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [gemma\-3\-4b\-pt\.json](<./gemma-3-4b-pt.json>)<br>
SHA-256: `389111514504136abe7825f1b73d859e049e162f84b6c932df432b88c091ac96`

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
| Model family | gemma 3 pt |

## Specifications

| Field | Value |
| --- | --- |
| Num parameters | 4,300,079,472 parameters \(safetensors metadata\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 8\.0 GiB of safetensors weights \(8,600,277,880 bytes\) in BF16 |
| Input / output | input: image, text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | gated |
| Downloads | 75,826 downloads \(Hub 30\-day window, as of 2026\-09\-04\) |
| Likes | 160 likes on the Hub \(as of 2026\-09\-04\) |

## Evaluation

_No specified fields are available in the publication data._

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| \[HellaSwag\]\[hellaswag\] | Not specified | 77\.2 | Not specified | Not reported |
| \[BoolQ\]\[boolq\] | Not specified | 72\.3 | Not specified | Not reported |
| \[PIQA\]\[piqa\] | Not specified | 79\.6 | Not specified | Not reported |
| \[SocialIQA\]\[socialiqa\] | Not specified | 51\.9 | Not specified | Not reported |
| \[TriviaQA\]\[triviaqa\] | Not specified | 65\.8 | Not specified | Not reported |
| \[Natural Questions\]\[naturalq\] | Not specified | 20\.0 | Not specified | Not reported |
| \[ARC\-c\]\[arc\] | Not specified | 56\.2 | Not specified | Not reported |
| \[ARC\-e\]\[arc\] | Not specified | 82\.4 | Not specified | Not reported |
| \[WinoGrande\]\[winogrande\] | Not specified | 64\.7 | Not specified | Not reported |
| \[BIG\-Bench Hard\]\[bbh\] | Not specified | 50\.9 | Not specified | Not reported |
| \[DROP\]\[drop\] | Not specified | 60\.1 | Not specified | Not reported |
| \[MMLU\]\[mmlu\] | Not specified | 59\.6 | Not specified | Not reported |
| \[MMLU\]\[mmlu\] | Not specified | 29\.2 | COT | Not reported |
| \[AGIEval\]\[agieval\] | Not specified | 42\.1 | Not specified | Not reported |
| \[MATH\]\[math\] | Not specified | 24\.2 | Not specified | Not reported |
| \[GSM8K\]\[gsm8k\] | Not specified | 38\.4 | Not specified | Not reported |
| \[GPQA\]\[gpqa\] | Not specified | 15\.0 | Not specified | Not reported |
| \[MBPP\]\[mbpp\] | Not specified | 46\.0 | Not specified | Not reported |
| \[HumanEval\]\[humaneval\] | Not specified | 36\.0 | Not specified | Not reported |
| \[MGSM\]\[mgsm\] | Not specified | 34\.7 | Not specified | Not reported |
| \[Global\-MMLU\-Lite\]\[global\-mmlu\-lite\] | Not specified | 57\.0 | Not specified | Not reported |
| \[WMT24\+\+\]\[wmt24pp\] | Not specified | 48\.4 | Not specified | Not reported |
| \[FloRes\]\[flores\] | Not specified | 39\.2 | Not specified | Not reported |
| \[XQuAD\]\[xquad\] | Not specified | 68\.0 | Not specified | Not reported |
| \[ECLeKTic\]\[eclektic\] | Not specified | 11\.0 | Not specified | Not reported |
| \[IndicGenBench\]\[indicgenbench\] | Not specified | 57\.2 | Not specified | Not reported |
| \[COCOcap\]\[coco\-cap\] | Not specified | 102 | Not specified | Not reported |
| \[DocVQA\]\[docvqa\] | Not specified | 72\.8 | Not specified | Not reported |
| \[InfoVQA\]\[info\-vqa\] | Not specified | 44\.1 | Not specified | Not reported |
| \[MMMU\]\[mmmu\] | Not specified | 39\.2 | Not specified | Not reported |
| \[TextVQA\]\[textvqa\] | Not specified | 58\.9 | Not specified | Not reported |
| \[RealWorldQA\]\[realworldqa\] | Not specified | 45\.5 | Not specified | Not reported |
| \[ReMI\]\[remi\] | Not specified | 27\.3 | Not specified | Not reported |
| \[AI2D\]\[ai2d\] | Not specified | 63\.2 | Not specified | Not reported |
| \[ChartQA\]\[chartqa\] | Not specified | 63\.6 | Not specified | Not reported |
| \[VQAv2\]\[vqav2\] | Not specified | 63\.9 | Not specified | Not reported |
| \[BLINK\]\[blinkvqa\] | Not specified | 38\.0 | Not specified | Not reported |
| \[OKVQA\]\[okvqa\] | Not specified | 51\.0 | Not specified | Not reported |
| \[TallyQA\]\[tallyqa\] | Not specified | 42\.5 | Not specified | Not reported |
| \[SpatialSense VQA\]\[ss\-vqa\] | Not specified | 50\.9 | Not specified | Not reported |
| \[CountBenchQA\]\[countbenchqa\] | Not specified | 26\.1 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/google/gemma\-3\-4b\-pt](<https://huggingface.co/google/gemma-3-4b-pt>) |
| Technical report | [https://arxiv\.org/abs/2404\.16816](<https://arxiv.org/abs/2404.16816>) |
| Citation | @article\{gemma\_2025,<br>    title=\{Gemma 3\},<br>    url=\{https://goo\.gle/Gemma3Report\},<br>    publisher=\{Kaggle\},<br>    author=\{Gemma Team\},<br>    year=\{2025\}<br>\} |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.summary`, `lineage.base_models`, `lineage.derivatives`, `specifications.architecture_type`, `specifications.context_length`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.code_repository`.
