# Model Card: Phi\-4 Model Card

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [phi\-4\.json](<./phi-4.json>)<br>
SHA-256: `7a4cf71a863d4cd3bd54403a19d2d716bfb96a25504d84e2c15ae8f33c4a9d72`

## Identity

| Field | Value |
| --- | --- |
| Model ID | microsoft/phi\-4 |
| Name | Phi\-4 Model Card |
| Developed by | microsoft \(Hub organization\) |
| Model type | text\-generation |
| License | mit |
| Release date | 2024\-12\-11 \(Hugging Face repository creation date\) |
| Version | 2db69c1c3e91a05d2c64a3185acfbaf36f744e25 |
| Summary | Phi\-4 is a 14\-billion parameter language model focused on data quality, built from synthetic datasets, filtered public web data, and academic books and Q&amp;A datasets\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | phi 4 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 14,659,507,200 parameters \(safetensors metadata\) |
| Context length | 16,384 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 27\.3 GiB of safetensors weights \(29,319,042,992 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The training data for phi\-4 combines synthetic data, which forms the bulk of the pretraining and midtraining data, with curated high\-quality organic sources such as academic papers, educational forums, and programming tutorials, as well as filtered public documents, code, acquired academic books, Q&amp;A datasets, and high\-quality chat\-format supervised data\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 695,440 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 2,295 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that phi\-4 performs strongly for its size, especially on reasoning\-focused benchmarks, and exceeds expectations on competition mathematics relative to other models\. The model card also presents representative benchmark results where higher numbers indicate better performance\. |
| Human evaluations | The developer reports a qualitative safety evaluation conducted with Microsoft&\#x27;s independent AI Red Team, which assessed the model in average and adversarial user scenarios\. The average scenario emulated typical single\-turn and multi\-turn interactions, while the adversarial scenario tested jailbreaks, encoding\-based attacks, multi\-turn attacks, and adversarial suffix attacks\. |
| Safety evaluations | The developer reports that prior to release the model underwent quantitative safety evaluation using open\-source safety benchmarks and in\-house adversarial conversation simulation tools\. Qualitative safety evaluation was performed with Microsoft&\#x27;s independent AI Red Team in both average and adversarial user scenarios\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Recall | Not specified | 100 | Not specified | Not reported |
| Recall | Not specified | 99 | Not specified | Not reported |
| RAG | Not specified | 58\.1 | Not specified | Not reported |
| RAG | Not specified | 57\.1 | Not specified | Not reported |
| ICL | Not specified | 68 | Not specified | Not reported |
| ICL | Not specified | 77 | Not specified | Not reported |
| Re\-rank | Not specified | 65\.3 | Not specified | Not reported |
| Re\-rank | Not specified | 54\.4 | Not specified | Not reported |
| QA | Not specified | 26\.7 | Not specified | Not reported |
| QA | Not specified | 36 | Not specified | Not reported |
| Summ | Not specified | 38\.3 | Not specified | Not reported |
| Summ | Not specified | 40\.5 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/microsoft/phi\-4](<https://huggingface.co/microsoft/phi-4>) |
| Technical report | [https://arxiv\.org/abs/2412\.08905](<https://arxiv.org/abs/2412.08905>) |
| Citation | The developer asks readers to refer to the technical report for details on safety alignment\. |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Lack of model transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-model-transparency.html>) | The card reports only benchmark and safety evaluation summaries, not detailed design or evaluation process documentation, so the checkpoint&\#x27;s inner workings and evaluation details are not fully transparent\. | Lack of model transparency is due to insufficient documentation of the model design, development, and evaluation process and the absence of insights into the inner workings of the model\. |
| [Unrepresentative data](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/unrepresentative-data.html>) | The model is built largely from synthetic data and filtered public/academic sources, which may not capture the full complexity of real\-world language use\. | Unrepresentative data occurs when the training or fine\-tuning data is not sufficiently representative of the underlying population or does not measure the phenomenon of interest\. Synthetic data might not fully capture the complexity and nuances of real\-world data\. Causes include possible limitations in the seed data quality, biases in generation methods, or inadequate domain knowledge\. Thus, AI models might struggle to generalize effectively to real\-world scenarios\. |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card lists acquired academic books and filtered public documents without standardized traceability of ownership, origin, or usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data bias](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-bias.html>) | Training data includes synthetic data and curated organic sources that can inherit or amplify historical and societal biases\. | Historical and societal biases might be present in data that are used to train and fine\-tune models\. Biases can also be inherited from seed data or exacerbated by synthetic data generation methods\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card describes data categories but does not provide detailed dataset documentation or synthetic data generation details\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `links.system_card`, `links.code_repository`.
