# Model Card: Qwen2\.5\-0\.5B\-SFT\-2e\-5\-5ep\-MDPO\_5e\-7\_3ep\_0alp\_0lam\_1ep

> This is an automated candidate generated from public sources. It has not been human-reviewed or released as an official model card.

Paired JSON: [qwen2\.5\-0\.5b\-sft\-2e\-5\-5ep\-mdpo\_5e\-7\_3ep\_0alp\_0lam\_1ep\.json](<./qwen2.5-0.5b-sft-2e-5-5ep-mdpo_5e-7_3ep_0alp_0lam_1ep.json>)<br>
SHA-256: `953644d5dd0a358ccff4645ba2a750165c890e876e44d614de63442cfd8142bb`

## Identity

| Field | Value |
| --- | --- |
| Model ID | JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-5ep\-MDPO\_5e\-7\_3ep\_0alp\_0lam\_1ep |
| Name | Qwen2\.5\-0\.5B\-SFT\-2e\-5\-5ep\-MDPO\_5e\-7\_3ep\_0alp\_0lam\_1ep |
| Developed by | JayHyeon \(Hub organization\) |
| Release date | 2024\-12\-31 \(Hugging Face repository creation date\) |
| Version | 0565f9723b4d12663e25664b2b81c0111562c739 |

## Lineage

_No specified fields are available in the publication data._

## Specifications

| Field | Value |
| --- | --- |
| Architecture type | dense decoder\-only |
| Num parameters | 494,032,768 parameters \(safetensors metadata\) |
| Context length | 32,768 tokens \(config\.json max\_position\_embeddings\) |
| Precision | F32 \(safetensors weight dtype\) |
| Model size | 1\.8 GiB of safetensors weights \(1,976,161,736 bytes\) in F32 |

## Training Context

_No specified fields are available in the publication data._

## Access and Adoption

| Field | Value |
| --- | --- |
| Access type | open\-weight |
| Downloads | 15 downloads \(Hub 30\-day window, as of 2026\-09\-06\) |
| Likes | 0 likes on the Hub \(as of 2026\-09\-06\) |

## Evaluation

_No specified fields are available in the publication data._

## Links

| Field | Value |
| --- | --- |
| Model card | [https://huggingface\.co/JayHyeon/Qwen2\.5\-0\.5B\-SFT\-2e\-5\-5ep\-MDPO\_5e\-7\_3ep\_0alp\_0lam\_1ep](<https://huggingface.co/JayHyeon/Qwen2.5-0.5B-SFT-2e-5-5ep-MDPO_5e-7_3ep_0alp_0lam_1ep>) |

## Risks

### Possible Risks

_Entries of the IBM AI Risk Atlas selected from what this card's own fields say. They are a taxonomy mapping, not statements found in the sources._

| Risk | Why it applies here | Description |
| --- | --- | --- |
| [Membership inference attack](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/membership-inference-attack.html>) | open\-weight dense decoder\-only model; card reports no training\-data protections or evaluation against membership inference, so an attacker with local access can query it to test whether samples were in training\. | A membership inference attack repeatedly queries a model to determine if a given input was part of the model&\#x27;s training\. More specifically, given a trained model and a data sample, an attacker appropriately samples the input space, observing outputs to deduce whether that sample was part of the model&\#x27;s training\. |
| [Legal accountability](<https://www.ibm.com/docs/en/watsonx/saas?topic=SSYOK8/wsj/ai-risk-atlas/legal-accountability.html>) | checkpoint name encodes a complex SFT/MDPO training recipe but the card gives no documentation of data provenance, synthetic\-data use, or governance, making accountability hard to establish\. | Determining who is responsible for an AI model is challenging without good documentation and governance processes\. The use of synthetic data in model development adds further complexity, since the lack of standardized frameworks for recording synthetic data design choices and verification steps makes accountability harder to establish\. |

---

Unavailable agreed fields (not specified in the publication data): `identity.model_type`, `identity.license`, `identity.summary`, `lineage.base_models`, `lineage.model_family`, `lineage.derivatives`, `specifications.input_output`, `training_context.training_data`, `training_context.training_data_size`, `training_context.data_cutoff`, `training_context.adaptations`, `evaluation.results_summary`, `evaluation.benchmark_scores`, `evaluation.human_evals`, `evaluation.safety_evals`, `links.system_card`, `links.tech_report`, `links.code_repository`, `links.citation`.
