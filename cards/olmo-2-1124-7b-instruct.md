# Model Card: OLMo\-2\-1124\-7B\-Instruct

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [olmo\-2\-1124\-7b\-instruct\.json](<./olmo-2-1124-7b-instruct.json>)<br>
SHA-256: `53f7e1c848531dc81a8442ba5e54cfaabad1563960879aef8e4ad8c6166cc246`

## Identity

| Field | Value |
| --- | --- |
| Model ID | allenai/OLMo\-2\-1124\-7B\-Instruct |
| Name | OLMo\-2\-1124\-7B\-Instruct |
| Developed by | allenai \(Hub organization\) |
| License | apache\-2\.0 |
| Release date | 2024\-12\-18 \(Hugging Face repository creation date\) |
| Version | 470b1fba1ae01581f270116362ee4aa1b97f4c84 |
| Summary | OLMo 2 is the next generation of fully open language models; this Instruct variant is post\-trained from the base OLMo\-2 7B model via supervised finetuning, DPO, and RLVR\. |

## Lineage

| Field | Value |
| --- | --- |
| Base models | allenai/OLMo\-2\-1124\-7B\-DPO (base model; Kind: finetune) |
| Model family | OLMo 2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,298,617,344 parameters \(safetensors metadata\) |
| Context length | 4,096 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 13\.6 GiB of safetensors weights \(14,597,276,128 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The OLMo 2 7B Instruct November 2024 model was fine\-tuned on an OLMo\-specific variant of the Tülu 3 dataset, with a mix that includes outputs generated from third\-party models subject to additional terms such as the Gemma Terms of Use\. |
| Adaptations | The model is a post\-trained variant of the OLMo\-2 7B November 2024 base model, having undergone supervised fine\-tuning, DPO training, and RLVR training on the Tülu 3 variant dataset\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 62,846 downloads \(Hub 30\-day window, as of 2026\-09\-05\) |
| Likes | 50 likes on the Hub \(as of 2026\-09\-05\) |

## Evaluation

| Field | Value |
| --- | --- |
| Results summary | The developer reports that the OLMo\-2\-7B\-1124\-Instruct checkpoint achieves an average score of 54\.8 across the listed evaluations, with notable results including 29\.1 on AlpacaEval, 72\.3 on IFEval, 23\.2 on PopQA, and 56\.5 on TruthQA\. |

### Benchmark Scores

| Benchmark | Metric | Score | Setting | Split |
| --- | --- | ---: | --- | --- |
| Average | Not specified | 28\.2 | Not specified | Not reported |
| Average | Not specified | 54\.8 | Not specified | Not reported |
| AlpacaEval | Not specified | 5\.2 | Not specified | Not reported |
| AlpacaEval | Not specified | 29\.1 | Not specified | Not reported |
| IFEval | Not specified | 32\.2 | Not specified | Not reported |
| IFEval | Not specified | 72\.3 | Not specified | Not reported |
| PopQA | Not specified | 17\.1 | Not specified | Not reported |
| PopQA | Not specified | 23\.2 | Not specified | Not reported |
| TruthQA | Not specified | 44\.5 | Not specified | Not reported |
| TruthQA | Not specified | 56\.5 | Not specified | Not reported |
| AVG | Not specified | 51\.4 | Not specified | Not reported |
| AVG | Not specified | 55\.9 | Not specified | Not reported |
| AVG | Not specified | 56\.5 | Not specified | Not reported |
| AE2 | Not specified | 10\.2 | Not specified | Not reported |
| AE2 | Not specified | 27\.9 | Not specified | Not reported |
| AE2 | Not specified | 29\.1 | Not specified | Not reported |
| IFE | Not specified | 66\.9 | Not specified | Not reported |
| IFE | Not specified | 73 | Not specified | Not reported |
| IFE | Not specified | 72\.3 | Not specified | Not reported |
| PQA | Not specified | 23\.6 | Not specified | Not reported |
| PQA | Not specified | 23\.5 | Not specified | Not reported |
| PQA | Not specified | 23\.2 | Not specified | Not reported |
| TQA | Not specified | 48\.6 | Not specified | Not reported |
| TQA | Not specified | 56 | Not specified | Not reported |
| TQA | Not specified | 56\.5 | Not specified | Not reported |

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/allenai/OLMo\-2\-1124\-7B\-Instruct](<https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct>) |
| Technical report | [https://arxiv\.org/abs/2501\.00656](<https://arxiv.org/abs/2501.00656>) |
| Code repository | [https://github\.com/allenai/OLMo](<https://github.com/allenai/OLMo>) |
| Citation | @article\{olmo20242olmo2furious,<br>      title=\{2 OLMo 2 Furious\}, <br>      author=\{Team OLMo and Pete Walsh and Luca Soldaini and Dirk Groeneveld and Kyle Lo and Shane Arora and Akshita Bhagia and Yuling Gu and Shengyi Huang and Matt Jordan and Nathan Lambert and Dustin Schwenk and Oyvind Tafjord and Taira Anderson and David Atkinson and Faeze Brahman and Christopher Clark and Pradeep Dasigi and Nouha Dziri and Michal Guerquin and Hamish Ivison and Pang Wei Koh and Jiacheng Liu and Saumya Malik and William Merrill and Lester James V\. Miranda and Jacob Morrison and Tyler Murray and Crystal Nam and Valentina Pyatkin and Aman Rangapur and Michael Schmitz and Sam Skjonsberg and David Wadden and Christopher Wilhelm and Michael Wilson and Luke Zettlemoyer and Ali Farhadi and Noah A\. Smith and Hannaneh Hajishirzi\},<br>      year=\{2024\},<br>      eprint=\{2501\.00656\},<br>      archivePrefix=\{arXiv\},<br>      primaryClass=\{cs\.CL\},<br>      url=\{https://arxiv\.org/abs/2501\.00656\}, <br>\} |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Hallucination](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/hallucination.html>) | Reported TruthQA score of 56\.5 and AlpacaEval 29\.1 indicate the model can produce factually inaccurate or ungrounded text, and the card does not report any hallucination mitigation\. | Hallucinations generate factually inaccurate or untruthful content relative to the model's training data or input\. Hallucinations are also sometimes referred to lack of faithfulness or lack of groundedness\. In some instances, synthetic data that is generated by large language models might include hallucinations that result in the data possibly being inaccurate, fabricated, or disconnected from reality\. Hallucinations can compromise model performance, accuracy, and relevance\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | The card reports an Instruct/chat model with moderate evaluation scores \(e\.g\., 29\.1 AlpacaEval, 72\.3 IFEval\) and no calibration or human\-decision\-making evaluation, so users could over\-trust its outputs in assisted decision\-making\. | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model's output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model's output when the model's output is likely incorrect\. Under\-reliance is the opposite, where the person doesn't trust the model but should\. |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | The model is open\-weight and was fine\-tuned on data including outputs generated from third\-party models subject to additional terms such as the Gemma Terms of Use, so users may prompt it with copyrighted or licensed material without clear IP safeguards\. | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Data privacy rights alignment](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-privacy-rights.html>) | The card states the model was fine\-tuned on the Tülu 3 variant dataset, which includes outputs from third\-party models, but it does not document whether personal data or data\-subject rights were addressed in that training data\. | Applicable laws can establish data subject rights such as opt\-out rights, right to access, and right to be forgotten\. Synthetic data might raise unique concerns, such as the potential for reidentification of individuals from seemingly anonymous synthetic data\. Data subject rights might also be relevant in scenarios where synthetic data is derived from sensitive or personal information\. |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | The card provides open\-weight access under Apache\-2\.0 and reports evaluations, but it does not document governance or accountability processes for the use of third\-party model outputs in its post\-training data\. | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`.
