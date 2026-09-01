# Model Cards

Model Cards builds machine-readable documentation for an exact model revision. The
workflow starts from versioned primary sources, produces a JSON card, and retains a
separate evidence ledger. The ledger supports claim tracing, correction, and release
review. Every included fact must be supported by the frozen source bundle and assigned
to the model, checkpoint, and field it actually describes. Evaluation claims must
also retain their evaluation setting.

The unit of analysis is `model_id@revision`. Evidence about a base model, sibling
checkpoint, family, or comparison system does not automatically become evidence about
the target. When the available sources do not support a field, the card says
`Not specified`.

This README defines the end-to-end pipeline contract. The checked-in cards are v5
outputs from before the v6 use-and-risk stage.

![Model Card generation pipeline](assets/model-card-pipeline.png)

*The central generation path fixes one model revision, freezes its source bundle,
binds candidate values to scoped evidence, and composes the card from accepted
bindings. The vector [PDF](assets/model-card-pipeline.pdf) and
[LaTeX source](assets/model-card-pipeline.tex) are included.*

## What the pipeline produces

The public deliverable is one JSON Model Card. The target schema v6 draft organizes
the record into the following sections.

| Section | Contents |
| --- | --- |
| Identity | Exact model ID and revision, developer, model type, release, license, and summary |
| Lineage | Base models, family membership, and derivatives, with explicit relations |
| Specifications | Architecture, parameter count, context length, precision, modalities, and model stage |
| Training context | Training data, scale, cutoff, and adaptations |
| Access and adoption | Access conditions and available adoption indicators |
| Evaluation | Target-specific benchmark results, related-model results, human and safety evaluations, and evaluation sources |
| Links | Model card, system card, technical report, and code repository |
| Uses and risks | Intended and out-of-scope uses, limitations, known biases, candidate risks, and mitigations |
| Provenance and quality | Source manifest, flagged and missing fields, coverage, schema version, and generation metadata |

Under the v6 contract, the public card will retain a safe field-to-source index with
logical source IDs, revisions, digests, and typed locators. The retained research
artifact contains the full source inventory, evidence text, binding ledger, conflicts,
withheld candidates, and review history needed to reproduce decisions. Frozen source
files, prompts, provider traces, audit material, and local execution metadata remain
private and are never part of the public export.

## Pipeline

### 1. Fix the target revision

Generation begins with one exact target. For a Hugging Face model, the workflow
resolves the requested revision to a commit and records the canonical
`owner/model@commit` identifier before collecting evidence. Later phases reject a
card, source record, or review action that refers to a different target.

### 2. Freeze the source bundle

The collector retrieves the available primary sources and stores immutable local
copies with revision information, retrieval metadata, and SHA-256 digests. A typical
bundle contains the exact Hugging Face snapshot, README, configuration and weight
metadata, a verified technical report, pinned developer documentation, and an
exact-ID EvalEval record. EvalEval contributes identifiers and discovery links. It
cannot establish checkpoint scores without revision-specific evidence. Collection
failures and missing source classes remain visible in the run state.

### 3. Build the model and evaluation frame

Before extracting values, the workflow identifies the target, base models, family,
sibling variants, comparison systems, benchmarks, metrics, datasets, and named
evaluation settings. Relations enter the frame only when supported by source evidence
or explicit metadata. Similar names alone do not establish a model relation. This
frame prevents a score for an instruction-tuned variant or a training quantity
for a model family from being assigned to the target checkpoint without explicit
support.

### 4. Extract evidence through two channels

Structured extraction reads fields from pinned metadata, configuration files, weight
metadata, model-index records, and exact-ID evaluation records. Model-assisted
extraction proposes verbatim passages from prose sources such as model READMEs,
reports, and developer documentation. Missing core fields can trigger bounded
retrieval from the already admitted source classes.

Each quotation must occur exactly in the frozen source. Each structured claim must
resolve to a recorded pointer and value. Extraction proposes evidence; it does not
decide that the evidence belongs in the card.

### 5. Bind evidence to fields and referents

Every candidate records its destination field, claimed entity, relation to the
target, source coordinates or structured pointer, and relevant section or table
anchors. Evaluation candidates also carry benchmark, version, subset, split, metric,
protocol, and row scope when the source provides them.

Entity-Attribution Verification checks whether a passage is actually about the
claimed entity and whether it supports the proposed field. Deterministic policy gates
then enforce exact-target, lineage, source-role, row-anchor, and evaluation-scope
rules. A valid referent correction is recorded. Wrong, ambiguous, or unsupported
assignments are withheld in the ledger.

### 6. Compose the JSON card

The composer receives accepted bindings, including bindings created from deterministic
structured extraction. It does not receive the unfiltered source bundle. It fills
schema fields, preserves `Not specified` for unsupported information, and uses
`Not applicable` only when the field genuinely does not apply. Parsing, type, enum,
list-shape, citation, and absence-value checks run inside a bounded repair loop.

Benchmark scores follow a stricter route. Rows are extracted and reconciled
deterministically against their table and protocol scope. Free-form model output does
not create score rows.

### 7. Identify use-context risks

Source-reported intended uses, limitations, biases, risks, and mitigations enter the
same evidence-binding process as other card facts. A separate model-assisted
[AI Atlas Nexus](https://github.com/IBM/ai-atlas-nexus) stage maps the documented model
and intended deployment context to candidate risks from the
[IBM AI Risk Atlas](https://www.ibm.com/docs/en/watsonx/saas?topic=ai-risk-atlas),
whose taxonomy and tooling are described in the
[AI Risk Atlas paper](https://arxiv.org/abs/2503.05780).

Taxonomy-identified risks remain distinct from publisher statements. Each mapping
retains a stable risk ID, pinned taxonomy name and version, taxonomy snapshot digest,
description, use context, applicability rationale, triggering card fields, Nexus
version, inference model, configuration digest, review status, and mitigation
references. The mapping states why a risk may apply; it does not claim that the
publisher reported it or that harm has occurred.

The additive [schema v6 draft](schema/model-card-v6-draft.schema.json) formalizes this
section while leaving the generated v5 examples unchanged. An empty risk, limitation,
or bias list means that no entry was recorded; it is not evidence that none exists.

### 8. Run layered validation

Validation checks source presence, assignment, wording, completeness, and risk
applicability separately. Claim failures create field-level findings. Target, schema,
privacy, and release-control failures block the artifact.

### 9. Repair and re-audit

Findings enter a targeted repair queue. A repair can add a missing binding, reassign a
candidate to the correct referent or field, or withhold it. Existing supported fields
are preserved. Each change is append-only and the affected claims are replayed
against the same source bundle before the full audit runs again.

### 10. Review and release

A named reviewer inspects included values, withheld evidence, conflicts, and
source-present omissions. High-impact identity, lineage, licensing, training,
evaluation, access, and risk decisions can require a second sign-off. Release occurs
only after the schema, source, review, privacy, licensing, and quotation gates pass.
The release artifact is JSON; internal bundles and ledgers stay local.

## Validation

No single score establishes that a card follows its sources. The validation phase
combines replayable checks with separate model-based assessments.

| Gate | Question answered |
| --- | --- |
| Target and source replay | Do the target revision, source hashes, quote spans, structured pointers, and deterministic derivations still match? |
| Schema and absence checks | Does the projection satisfy the versioned field, type, enum, required-value, and absence rules? |
| Assignment policy | Is the evidence about the correct model or checkpoint, and may that source-relation pair populate this field? |
| Evaluation scope | Does each result retain the correct benchmark, row, metric, split, protocol, and comparison scope? |
| Entity-Attribution Verification | Does the evidence support this field for the entity named by the binding? |
| Final-claim entailment | Does the card's final wording follow from that claim's own citations? |
| FactReasoner | When narrative claims are split into atomic claims, what support, contradiction, or neutral evidence is found in the frozen bundle? Low-support claims return to repair or review. |
| Conflict and numeric checks | Do accepted values disagree, and do scores and derived quantities reconcile without last-write-wins behavior? |
| Omission audit | Which relevant facts are present in the sources but absent from the card? |
| Risk-mapping gate | Does the risk exist in the pinned taxonomy, and is its applicability rationale grounded in the stated use context and card fields? |
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

The workflow admits sources according to what they can establish for the exact
target.

| Source | Role | Constraint |
| --- | --- | --- |
| Hugging Face metadata, model README, config, and weight metadata | Identity, architecture, parameters, precision, links, and publisher documentation | Pinned to the exact model revision |
| Developer paper or technical report | Training, methods, limitations, and evaluation details | Verified as relevant to the target or linked with an explicit related-model relation |
| Developer GitHub documentation | Code, release, and supplementary model documentation | Pinned to a developer-owned commit |
| Official model, system, and safety cards | Intended use, limitations, safety evaluations, and mitigations | Versioned and tied to the exact target or an explicit model relation |
| Official provider documentation and changelogs | Capabilities, access, versions, and API behavior | Version and product scope must be recoverable |
| Original independent evaluation reports | External evaluation claims | Exact model version and protocol must be identified |
| Evaluation configurations and result artifacts | Benchmark scores and settings | Target, benchmark version, metric, split, and protocol must be recoverable |
| Official dataset cards | Dataset identity, version, composition, and restrictions | Must describe the dataset version actually used |
| EvalEval evaluation record | Exact-ID links and source discovery | Not authority for checkpoint-specific scores by itself |

Third-party summaries, mirrors, and unversioned leaderboards may support discovery,
but they are not target authority. Evidence from a base model or family is retained
with that relation unless the source explicitly supports inheritance by the target.

## Example cards

These JSON cards were generated by the research workflow and exported without their
private source bundles or evidence ledgers. They are examples, not hand-written
templates.

| Card | What it illustrates | Field coverage | Status |
| --- | --- | ---: | --- |
| [OLMo-2-1124-7B](cards/olmo-2-1124-7b.json) | Exact-revision identity, training context, and nine publisher-reported benchmark rows | 66.7% | Development example |
| [OLMo-2-1124-7B-Instruct](cards/olmo-2-1124-7b-instruct.json) | A derivative checkpoint with explicit base-model relations and eight benchmark rows | 63.6% | Repair required after omission audit |

Coverage reports how many documentation fields are populated; it is not a correctness
score. Both files remain exact schema-v5 projections. Cards generated under v6 will
also include the use-and-risk section. Neither checked-in card is human-reviewed or
release-approved. The Instruct file's retained omission audit also found
source-present information missing from `lineage.model_family` and
`training_context.training_data_size`.

## Repository and code

The repository contains the public, source-free components for schema handling,
evidence and binding records, exact quote and structured-pointer verification,
relation and scope policy, deterministic projection and conflict handling,
append-only review events, rendering, and sanitized JSON export. The collector,
composer, validation, and release orchestration use these interfaces. The end-to-end
generator is not yet exposed as one public command.

```text
assets/             LaTeX pipeline figure and rendered PDF/PNG
cards/              Generated public JSON cards
schema/             Versioned JSON Schema drafts
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
