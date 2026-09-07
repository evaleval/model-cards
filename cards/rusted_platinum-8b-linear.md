# Model Card: Rusted\_Platinum\-8B\-LINEAR

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [rusted\_platinum\-8b\-linear\.json](<./rusted_platinum-8b-linear.json>)<br>
SHA-256: `e1e86afa987a87949e831de83720b9d46d5ca43a30c9887fba66d1bd5c5f6e8b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | DreadPoor/Rusted\_Platinum\-8B\-LINEAR |
| Name | Rusted\_Platinum\-8B\-LINEAR |
| Developed by | DreadPoor \(Hub organization\) |
| Release date | 2025\-03\-06 \(Hugging Face repository creation date\) |
| Version | f5f5afcf6613327ba43343b0b3a099be5333a733 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | FuseAI/FuseChat\-Llama\-3\.1\-8B\-SFT (base model; Kind: merge)<br>Sao10K/L3\-8B\-Stheno\-v3\.2 (base model; Kind: merge)<br>kik41/lora\-sarcasm\-more\-llama\-3\-8b\-v2 (base model; Kind: merge)<br>kik41/lora\-type\-expository\-llama\-3\-8b\-v2 (base model; Kind: merge) |
| Model family | Rusted Platinum LINEAR |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 8,030,261,248 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | BF16 \(safetensors weight dtype\) |
| Model size | 15\.0 GiB of safetensors weights \(16,060,556,336 bytes\) in BF16 |
| Input / output | input: text<br>output: text |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 18 downloads \(Hub 30\-day window, as of 2026\-09\-07\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-07\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/DreadPoor/Rusted\_Platinum\-8B\-LINEAR](<https://huggingface.co/DreadPoor/Rusted_Platinum-8B-LINEAR>) |

## Risks

_No specified fields are available in the publication data._

### Possible Risks

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Evasion attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/evasion-attack.html>) | open\-weight text\-to\-text model with no reported safety evaluation or robustness testing \-&gt; evasion attacks on downstream tasks | Evasion attacks attempt to make a model output incorrect results by slightly perturbing the input data sent to the trained model\. |
| [Over\- or under\-reliance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/over-or-under-reliance.html>) | open\-weight base/chat model with no reported safety evaluation or calibration \-&gt; users may over\-trust outputs in downstream decision\-making | In AI\-assisted decision\-making tasks, reliance measures how much a person trusts \(and potentially acts on\) a model&\#x27;s output\. Over\-reliance occurs when a person puts too much trust in a model, accepting a model&\#x27;s output when the model&\#x27;s output is likely incorrect\. Under\-reliance is the opposite, where the person doesn&\#x27;t trust the model but should\. |
| [Confidential data in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/confidential-data-in-prompt.html>) | open\-weight model with no stated data handling or privacy safeguards \-&gt; users may paste confidential text into prompts | Confidential information might be included as a part of the prompt that is sent to the model\. |
| [IP information in prompt](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/ip-information-in-prompt.html>) | open\-weight model with no stated IP safeguards \-&gt; users may include copyrighted text in prompts | Copyrighted information or other intellectual property might be included as a part of the prompt that is sent to the model\. |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | open\-weight checkpoint card lacks documentation of training data, evaluations, and governance \-&gt; accountability for outputs is unclear | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.derivatives`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
