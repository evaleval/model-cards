# Model Card: Samantha Qwen2 7B

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [samantha\-qwen\-2\-7b\.json](<./samantha-qwen-2-7b.json>)<br>
SHA-256: `b1f36b234338954518cf16189dcc20335728b607b60be547c580ffc0d5a6f63b`

## Identity

| Field | Value |
| --- | --- |
| Model ID | macadeliccc/Samantha\-Qwen\-2\-7B |
| Name | Samantha Qwen2 7B |
| Developed by | macadeliccc \(Hub organization\) |
| Model type | AutoModelForCausalLM |
| License | apache\-2\.0 |
| Release date | 2024\-06\-15 \(Hugging Face repository creation date\) |
| Version | 59058972fa9b56d132d04589eb17cbba277c2826 |

## Lineage

| Field | Value |
| --- | --- |
| Base models | Qwen/Qwen2\-7B (base model; Kind: finetune) |
| Model family | Samantha Qwen 2 |

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 7,615,616,512 parameters \(safetensors metadata\) |
| Context length | 131,072 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F16 \(safetensors weight dtype\) |
| Model size | 14\.2 GiB of safetensors weights \(15,231,271,528 bytes\) in F16 |
| Input / output | input: text<br>output: text |

## Training Context

| Field | Value |
| --- | --- |
| Training data | The model was fine\-tuned on a mix of conversational datasets, including opus\_samantha, ultrachat\_200k, OpenHermes\-2\.5, and Claude\-3\-Opus\-Instruct\-15K, formatted in the ChatML sharegpt style\. |

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 42 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 3 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/macadeliccc/Samantha\-Qwen\-2\-7B](<https://huggingface.co/macadeliccc/Samantha-Qwen-2-7B>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Uncertain data provenance](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-provenance.html>) | The card lists multiple fine\-tuning datasets \(opus\_samantha, ultrachat\_200k, OpenHermes\-2\.5, Claude\-3\-Opus\-Instruct\-15K\) but provides no provenance or traceability details for them\. | Data provenance refers to the traceability of data \(including synthetic data\), which includes its ownership, origin, transformations, and generation\. Proving that the data is the same as the original source with correct usage terms is difficult without standardized methods for verifying data sources or generation\. |
| [Lack of data transparency](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/lack-of-data-transparency.html>) | The card names datasets but does not document their composition, filtering, or generation process, so tuning\-data details are insufficiently documented\. | Lack of data transparency might be due to insufficient documentation of training or tuning dataset details, including synthetic data generation\.  |
| [Data usage rights restrictions](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/data-usage-rights.html>) | Fine\-tuning on datasets derived from or named after other models \(e\.g\., Claude\-3\-Opus\-Instruct\-15K\) raises possible terms\-of\-service or license restrictions on using that data to build models\. | Terms of service, license compliance, or other IP issues may restrict the ability to use certain data for building models\. |
| [Copyright infringement](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/copyright-infringement.html>) | An open\-weight conversational model fine\-tuned on instruction/chat datasets may reproduce copyrighted or license\-protected text from those sources, with no reported copyright mitigation\. | A model might generate content that is similar or identical to existing work protected by copyright or covered by open\-source license agreement\. |
| [Improper usage](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/improper-usage.html>) | The card only specifies AutoModelForCausalLM text generation and reports no safety evaluations or usage restrictions, so the open\-weight model could plausibly be used outside its intended conversational purpose\. | Improper usage occurs when a model is used for a purpose that it was not originally designed for\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.summary`, `lineage.derivatives`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
