# Model Cards

Model Cards turns primary documentation about an AI model into a structured JSON
record. Its sources can include official model pages, technical reports, configuration
files, evaluation results, and safety documentation. Each populated field points to
evidence about the model it describes. Unsupported fields remain `Not specified`.

Each card describes a specific model release. Information about a base model, related
checkpoint, model family, or comparison system is kept separate unless a source
explicitly connects it to the documented model.

![Model Card generation pipeline](assets/model-card-pipeline.png)

*The pipeline selects a model release, collects its sources, links proposed values to
supporting evidence, and composes the card from verified claims. The vector
[PDF](assets/model-card-pipeline.pdf) and
[LaTeX source](assets/model-card-pipeline.tex) are included.*

## What the pipeline produces

The resulting JSON Model Card is organized into the following sections.

| Section | Contents |
| --- | --- |
| Identity | Model ID, developer, model type, release, license, and summary |
| Lineage | Base models, family membership, and derivatives, with explicit relations |
| Specifications | Architecture, parameter count, context length, precision, modalities, and model stage |
| Training context | Training data, scale, cutoff, and adaptations |
| Access and adoption | Access conditions and available adoption indicators |
| Evaluation | Results for the documented model, related-model results, human and safety evaluations, and evaluation sources |
| Links | Model card, system card, technical report, and code repository |
| Uses and risks | Intended and out-of-scope uses, limitations, known biases, candidate risks, and mitigations |
| Provenance and quality | Source references, flagged and missing fields, coverage, and generation details |

Field-to-source references connect each documented claim to a stable public source.
The local research record keeps the supporting evidence, conflicts, excluded
candidates, and review history needed to reproduce decisions. Source copies, prompts,
provider traces, audit material, and local execution records remain private.

## Pipeline

### 1. Select the model release

Generation begins by selecting the model release or checkpoint to document. The
workflow records its canonical identifier and verifies throughout the pipeline that
sources, evaluation results, and review decisions refer to that model.

### 2. Collect and preserve the sources

The collector retrieves the available primary sources and saves a fixed local copy of
each source with version and retrieval information. A typical source set contains the
Hugging Face model page, README, configuration and weight metadata, a relevant
technical report, developer documentation, and the matching EvalEval record. EvalEval
contributes identifiers and discovery links. It cannot establish model scores without
evidence for the documented release. Collection failures and unavailable source types
remain visible during validation and review.

### 3. Map model lineage and evaluations

Before extracting values, the workflow identifies the documented model, base models,
family, sibling variants, comparison systems, benchmarks, metrics, datasets, and named
evaluation settings. Relations enter the map only when supported by source evidence
or explicit metadata. Similar names alone do not establish a model relation. This map
prevents a score for an instruction-tuned variant or a training quantity for a model
family from being assigned to the documented checkpoint without explicit support.

### 4. Extract evidence through two channels

Structured extraction reads fields from version-specific metadata, configuration
files, weight metadata, model-index records, and matching evaluation records.
Model-assisted extraction proposes verbatim passages from prose sources such as model
READMEs, reports, and developer documentation. Missing core fields can trigger further
retrieval from approved source types.

Each quotation must occur exactly in the saved source. Each structured claim must
resolve to a recorded pointer and value. Extraction proposes evidence. It does not
decide that the evidence belongs in the card.

### 5. Verify evidence and assign fields

Every candidate records its destination field, the model or entity it describes, its
relation to the documented model, its source location, and the relevant section or
table. Evaluation candidates also record the benchmark, subset, split, metric,
protocol, and table row when the source provides them.

Entity-Attribution Verification checks whether a passage is actually about the
named model and whether it supports the proposed field. Deterministic checks then
verify the model relation, source suitability, table context, and evaluation setting.
Valid corrections are recorded. Wrong, ambiguous, or unsupported assignments remain
in the ledger but do not enter the card.

### 6. Compose the JSON card

The composer receives only evidence that passed the previous checks. It does not
receive the unfiltered source set. It fills the JSON fields, preserves `Not specified`
for unsupported information, and uses `Not applicable` only when a field genuinely
does not apply. A controlled repair loop checks parsing, field types, allowed values,
list structure, citations, and absence markers.

Benchmark rows are extracted and reconciled against their table and evaluation
setting. Free-form model output does not create or alter scores.

### 7. Identify use-context risks

Source-reported intended uses, limitations, biases, risks, and mitigations enter the
same evidence-binding process as other card facts. A separate model-assisted
[AI Atlas Nexus](https://github.com/IBM/ai-atlas-nexus) stage maps the documented model
and intended deployment context to candidate risks from the
[IBM AI Risk Atlas](https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas),
whose taxonomy and tooling are described in the
[AI Risk Atlas paper](https://arxiv.org/abs/2503.05780).

Taxonomy-identified risks remain distinct from publisher statements. Each mapping
records the risk identifier, taxonomy release, use context, rationale, supporting
evidence, review status, and relevant mitigations. The mapping explains why a risk may
apply. It does not present the risk as a publisher statement or confirmed harm.

The [JSON schema](schema/model-card.schema.json) defines this section alongside the
rest of the card. An empty risk, limitation, or bias list means that no supported entry
was recorded. It does not establish that none exists.

### 8. Run layered validation

Validation checks source presence, assignment, wording, completeness, and risk
applicability separately. Claim failures create field-level findings. Model identity,
schema, privacy, and publication-control failures block the card.

### 9. Repair and re-audit

Findings enter a targeted repair queue. A repair can add missing evidence, assign a
candidate to the correct model or field, or exclude it. Existing supported fields are
preserved. Each change is recorded in the repair history. The affected claims are
checked against the same sources before the full audit runs again.

### 10. Review and release

A named reviewer inspects included values, withheld evidence, conflicts, and relevant
source facts missing from the card. High-impact identity, lineage, licensing, training,
evaluation, access, and risk decisions can require a second sign-off. Release occurs
only after the schema, source, review, privacy, licensing, and quotation gates pass.
The release output is JSON. Internal source sets and evidence ledgers stay local.

## Validation

No single score establishes that a card follows its sources. The validation phase
combines replayable checks with separate model-based assessments.

| Gate | Question answered |
| --- | --- |
| Model and source replay | Do source references, quoted passages, structured values, and derived fields still match the collected sources? |
| Schema and absence checks | Does the card satisfy the required fields, types, allowed values, and absence rules? |
| Assignment policy | Is the evidence about the correct model or checkpoint, and may that source-relation pair populate this field? |
| Evaluation scope | Does each result retain the correct benchmark, row, metric, split, protocol, and comparison scope? |
| Entity-Attribution Verification | Does the evidence support this field for the entity named by the binding? |
| Claim support | Does the card's final wording follow from that claim's own citations? |
| FactReasoner | When narrative claims are split into atomic claims, what support, contradiction, or neutral evidence is found in the saved sources? Low-support claims return to repair or review. |
| Conflict and numeric checks | Do accepted values disagree, and do scores and derived quantities reconcile without last-write-wins behavior? |
| Omission audit | Which relevant facts are present in the sources but absent from the card? |
| Risk-mapping gate | Does the risk exist in the selected taxonomy release, and is its rationale grounded in the stated use context and card fields? |
| Release and privacy checks | Does the JSON contain only approved public fields and no source text, credentials, local paths, prompts, or provider traces? |
| Review, licensing, and quotation checks | Are required decisions signed off, and may the selected source references and short quotations be released? |

The [FactReasoner paper](https://aclanthology.org/2025.findings-emnlp.785/) and
[reference implementation](https://github.com/IBM/FactReasoner) describe the
post-composition claim-support method. It decomposes text into atomic claims,
retrieves relevant context, and estimates support against that context. This
complements exact span checks and Entity-Attribution Verification. Risk mappings use
a separate gate because a taxonomy-derived risk is an inference over model and use
context, not a publisher quotation.

## Sources

The workflow admits sources according to what they can establish for the documented
model release.

| Source | Role | Constraint |
| --- | --- | --- |
| Hugging Face metadata, model README, config, and weight metadata | Identity, architecture, parameters, precision, links, and publisher documentation | Saved from the documented model release |
| Developer paper or technical report | Training, methods, limitations, and evaluation details | Verified as relevant to the documented model or linked through an explicit model relation |
| Developer GitHub documentation | Code, release, and supplementary model documentation | Taken from a fixed version of a developer-owned repository |
| Official model, system, and safety cards | Intended use, limitations, safety evaluations, and mitigations | Tied to the documented model or an explicit model relation |
| Official provider documentation and changelogs | Capabilities, access, versions, and API behavior | Version and product scope must be recoverable |
| Original independent evaluation reports | External evaluation claims | Exact model version and protocol must be identified |
| Evaluation configurations and result artifacts | Benchmark scores and settings | Documented model, benchmark version, metric, split, and protocol must be recoverable |
| Official dataset cards | Dataset identity, version, composition, and restrictions | Must describe the dataset version actually used |
| EvalEval evaluation record | Matching model links and source discovery | Not authority for model scores by itself |

Third-party summaries, mirrors, and leaderboards may support discovery, but they are
not treated as primary evidence for the documented model. Evidence from a base model
or family keeps that relation unless the source explicitly states that it also applies
to the documented model.

## Example cards

These JSON cards are examples produced by the workflow. Their private source bundles
and evidence ledgers remain local.

| Card | What it illustrates | Field coverage |
| --- | --- | ---: |
| [OLMo-2-1124-7B](cards/olmo-2-1124-7b.json) | Model identity, training context, and nine publisher-reported benchmark rows | 66.7% |
| [OLMo-2-1124-7B-Instruct](cards/olmo-2-1124-7b-instruct.json) | A derivative checkpoint with explicit base-model relations and eight benchmark rows | 63.6% |

Coverage reports how many documentation fields are populated from the available
evidence. It is not a correctness score. The examples illustrate the JSON format and
the treatment of model identity, lineage, training information, and evaluation
results. They have not completed human release review.

## Repository and code

The repository contains the public schema, generated JSON examples, pipeline figure,
Python package, tests, and architecture documentation. The code covers evidence and
assignment records, source verification, relation and evaluation-scope policy,
conflict handling, review events, rendering, and sanitized JSON export.

```text
assets/             LaTeX pipeline figure and rendered PDF/PNG
cards/              Generated public JSON cards
schema/             JSON Schema
src/model_cards/    Python package
tests/              Offline deterministic tests and synthetic fixtures
ARCHITECTURE.md      Developer architecture and privacy boundary
```

Private source bundles, research notes, prompts, local paths, provider traces, and
audit work products are excluded from this repository.

## Install and inspect

Python 3.9 or newer is sufficient for the public package.

```sh
python3 -m pip install -e .
python3 -m unittest discover -s tests -v

python3 -m model_cards build tests/fixtures/synthetic-input.json \
  --json build/synthetic-card.json \
  --html build/synthetic-card.html
python3 -m model_cards inspect build/synthetic-card.json
```

The fixture is synthetic and tests evidence assignment and withholding behavior. See
[ARCHITECTURE.md](ARCHITECTURE.md) for the data model, validation boundaries, and
developer commands.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
