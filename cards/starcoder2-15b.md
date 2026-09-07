# Model Card: StarCoder2

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [starcoder2\-15b\.json](<./starcoder2-15b.json>)<br>
SHA-256: `67da358397c91c2fff5f5beea7947262d57dddf618add08eb5faa0d0308e4b9c`

## Identity

| Field | Value |
| --- | --- |
| Model ID | bigcode/starcoder2\-15b |
| Name | StarCoder2 |
| Developed by | bigcode \(Hub organization\) |
| Model type | text\-generation |
| License | bigcode\-openrail\-m |
| Release date | 2024\-02\-20 \(Hugging Face repository creation date\) |
| Version | 46d44742909c03ac8cee08eb03fdebce02e193ec |
| Summary | StarCoder2\-15B is a 15\-billion\-parameter model trained on more than 600 programming languages using The Stack v2, with opt\-out requests excluded\. |

## Lineage

| Field | Value |
| --- | --- |
| Model family | starcoder2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 15,957,889,024 parameters \(safetensors metadata\) |
| Context length | 16,384 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 59\.4 GiB of safetensors weights \(63,831,628,056 bytes\) in F32 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The StarCoder2\-15B checkpoint was trained on The Stack v2, covering 600\+ programming languages with opt\-out requests excluded, plus GitHub code and additional selected sources such as Arxiv and Wikipedia\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 4,906 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 677 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/bigcode/starcoder2\-15b](<https://huggingface.co/bigcode/starcoder2-15b>) |
| Code repository | [https://github\.com/bigcode\-project/starcoder2](<https://github.com/bigcode-project/starcoder2>) |
| Citation | @misc\{lozhkov2024starcoder,<br>      title=\{StarCoder 2 and The Stack v2: The Next Generation\}, <br>      author=\{Anton Lozhkov and Raymond Li and Loubna Ben Allal and Federico Cassano and Joel Lamy\-Poirier and Nouamane Tazi and Ao Tang and Dmytro Pykhtar and Jiawei Liu and Yuxiang Wei and Tianyang Liu and Max Tian and Denis Kocetkov and Arthur Zucker and Younes Belkada and Zijian Wang and Qian Liu and Dmitry Abulkhanov and Indraneil Paul and Zhuang Li and Wen\-Ding Li and Megan Risdal and Jia Li and Jian Zhu and Terry Yue Zhuo and Evgenii Zheltonozhskii and Nii Osae Osae Dade and Wenhao Yu and Lucas Krauß and Naman Jain and Yixuan Su and Xuanli He and Manan Dey and Edoardo Abati and Yekun Chai and Niklas Muennighoff and Xiangru Tang and Muhtasham Oblokulov and Christopher Akiki and Marc Marone and Chenghao Mou and Mayank Mishra and Alex Gu and Binyuan Hui and Tri Dao and Armel Zebaze and Olivier Dehaene and Nicolas Patry and Canwen Xu and Julian McAuley and Han Hu and Torsten Scholak and Sebastien Paquet and Jennifer Robinson and Carolyn Jane Anderson and Nicolas Chapados and Mostofa Patwary and Nima Tajbakhsh and Yacine Jernite and Carlos Muñoz Ferrandis and Lingming Zhang and Sean Hughes and Thomas Wolf and Arjun Guha and Leandro von Werra and Harm de Vries\},<br>      year=\{2024\},<br>      eprint=\{2402\.19173\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.SE\}<br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card states training data is The Stack v2 with opt\-out requests excluded, plus GitHub code and selected sources such as Arxiv and Wikipedia, but provides no standardized verification of data origin or usage terms\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Data usage rights restrictions](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-usage-rights.html>) | Open\-weight model trained on GitHub code and other web sources; the card does not document license compliance or terms\-of\-service restrictions for those sources\. | Terms of service, license compliance, or other IP issues may restrict the ability to use certain data for building models\. |
| [Copyright infringement](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/copyright-infringement.html>) | Trained on 600\+ programming languages from The Stack v2 and GitHub code, so it may generate code similar to existing copyrighted or open\-source licensed works\. | A model might generate content that is similar or identical to existing work protected by copyright or covered by open\-source license agreement\. |
| [Harmful code generation](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/harmful-code-generation.html>) | Text\-generation model trained on a large corpus of code with no reported safety evaluation, so it can plausibly generate code that causes harm or affects systems\. | Models might generate code that causes harm or unintentionally affects other systems\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card names broad sources \(The Stack v2, GitHub, Arxiv, Wikipedia\) but does not document dataset details or filtering beyond opt\-out requests\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |

---

Unavailable agreed fields (not specified in the publication data): `lineage.base_models`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`.
