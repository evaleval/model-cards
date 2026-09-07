# Model Card: Qwen2\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\-7b\-instruct\.json](<./qwen2-7b-instruct.json>)<br>
SHA-256: `0d567e5f2690e4f4d064db3c8f675a4affa5d217f522f0bd3210dd817aa137f4`

## Identity

| Field | Value |
| --- | --- |
| Model ID | Qwen/Qwen2\-7B\-Instruct |
| Name | Qwen2\-7B\-Instruct |
| Developed by | Qwen \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-06\-04 \(Hugging Face repository creation date\) |
| Version | f2826a00ceef68f0f2b946d945ecc0477ce4450c |
| Summary | An instruction\-tuned 7B Qwen2 language model, part of a series that includes base and instruction\-tuned models for chat and agent purposes; the 7B Instruct variant supports extended context lengths up to 128K tokens\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-7B (base model; Kind: finetune) |
| Model family | Qwen2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,872 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Adaptations | The model was post\-trained with supervised fine\-tuning and direct preference optimization after pretraining on a large corpus\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 388,915 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 687 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that Qwen2\-7B\-Instruct remains competitive against recently released state\-of\-the\-art models, with particularly strong results on coding and Chinese\-language benchmarks\. The model also handles contexts up to 128k tokens nearly flawlessly\. |
| Human evaluations | The developer states that Qwen2\-7B\-Instruct shows advantages over recently released state\-of\-the\-art models, with especially strong performance on coding and Chinese\-related metrics\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| TheroemQA | Not specified | 25\.3 | Not specified | Not reported |
| MT\-Bench | Not specified | 8\.41 | Not specified | Not reported |
| Evalplus | Not specified | 70\.3 | Not specified | Not reported |
| LiveCodeBench | Not specified | 26\.6 | Not specified | Not reported |
| C\-Eval | Not specified | 77\.2 | Not specified | Not reported |
| AlignBench | Not specified | 7\.21 | Not specified | Not reported |
| Theorem QA | Not specified | 25\.3 | Not specified | Not reported |
| LiveCodeBench v1 | Not specified | 26\.6 | Not specified | Not reported |
| MixEval | Not specified | 76\.5 | Not specified | Not reported |
| IFEval strict\-prompt | Not specified | 54\.7 | Not specified | Not reported |
| Knowledge | Not specified | 61\.54 | Not specified | Not reported |
| Knowledge | Not specified | 73\.75 | Not specified | Not reported |
| Exam | Not specified | 66\.66 | Not specified | Not reported |
| Comprehension | Not specified | 59\.63 | Not specified | Not reported |
| Comprehension | Not specified | 63\.09 | Not specified | Not reported |
| Coding | Not specified | 34\.74 | Not specified | Not reported |
| Coding | Not specified | 36\.41 | Not specified | Not reported |
| Reasoning | Not specified | 58\.22 | Not specified | Not reported |
| Avg\. | Not specified | 56\.96 | Not specified | Not reported |
| Avg\. | Not specified | 62\.23 | Not specified | Not reported |
| IFEval | Not specified | 54\.7 | Not specified | Not reported |
| IFEval | Not specified | 53\.7 | Not specified | Not reported |
| IFEval | Not specified | \-1\.0 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/Qwen/Qwen2\-7B\-Instruct](<https://huggingface.co/Qwen/Qwen2-7B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2407\.10671](<https://arxiv.org/abs/2407.10671>) |
| Code repository | [https://github\.com/QwenLM/Qwen2](<https://github.com/QwenLM/Qwen2>) |
| Citation | @article\{qwen2,<br>  title=\{Qwen2 Technical Report\},<br>  year=\{2024\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | instruction\-tuned chat model with reported strong coding/Chinese benchmarks but no reported factuality or grounding evaluation \-&gt; hallucination risk in open\-ended text generation | Hallucinations generate factually inaccurate or untruthful content relative to the model&\#x27;s training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.safety_evals`, `links.system_card`.
