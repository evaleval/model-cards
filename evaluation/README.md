# Held-out evaluation design

This directory defines a future human evaluation and an offline cross-instrument
engineering audit. It contains no completed annotations, reviewer identities, source
text, or new quality results. `annotation.schema.json` and
`annotation-template.json` cover each per-reviewer held-out study packet.
`paired-audit-labels.schema.json` is a distinct, row-oriented export for the
adjudicated cross-condition audit; it is not a replacement for the reviewer packet
format. Its empty template covers future blinded labels.
`item_manifest.py` now provides the artifact-bound foundation for those labels. It
builds a sealed private manifest plus two ordered, identity-redacted review phases
for each target/condition pair and one condition-neutral target sheet per target. The
checked-in schemas describe all outputs; no generated manifest, packet, target
sheet, blinding key, source excerpt, or annotation is checked in here.
`paired_audit.py` can summarize already-produced privacy-safe quality reports beside
released Auto-BenchmarkCards aggregates, but it cannot turn those unlike instruments
into a superiority result. See `PAIRED_AUDIT.md` for its input contract.

## Study question

Evaluate whether the full evidence pipeline changes the factual support and
assignment quality of generated Model Cards relative to a fixed comparison
pipeline. This is a paired engineering evaluation, not evidence that either
system is better than another research system.

The study measures six distinct outcomes:

1. **Claim support:** fully supported, partially supported, unsupported, or
   unavailable from the displayed evidence.
2. **Assignment:** exact checkpoint/entity, model relation, and destination
   field are each correct, wrong, or unclear.
3. **Source binding:** the cited source and recorded location support the
   presented claim.
4. **Omission:** an applicable, source-present fact is present, withheld with a
   visible reason, conflicting, or missed.
5. **Risk applicability:** a taxonomy-valid candidate is grounded in the card's
   use context, may apply to that context, and is not misattributed to the
   publisher.
6. **Warning utility:** a surfaced validation warning is correct and would help
   a reviewer decide what to repair or withhold.

These judgments are kept separate. For example, a quote can be genuine while
describing the wrong checkpoint, and a taxonomy-valid risk can still be
inapplicable to the documented use context.

## Sampling and blinding

- Freeze the protocol, item-order seed, and packet-release procedure before selecting
  held-out targets.
- Exclude implementation fixtures, the three canaries, the twelve-target pilot,
  and checked-in examples.
- Sample 30 previously unseen targets, stratified across base/instruction-tuned
  releases, source-rich/source-limited releases, access states, model families,
  and reported-use contexts. Do not expand this into a 200–300-card batch.
- Generate paired outputs from the same exact source-input surface. Vary only the
  preregistered treatment configuration; keep all non-treatment evaluation settings
  fixed. Randomly label the two conditions `A` and `B` independently for each target;
  retain the decoding key outside annotation packets.
- Present only bounded evidence needed for the current item. Model source bodies,
  quotations, run logs, and annotations remain under the gitignored local run
  directory.
- Randomize item order deterministically from the coordinator key and opaque packet
  identity; suppress system name, filenames, lifecycle labels, and other
  condition-revealing metadata in the reviewer view.

Each target should contribute all eligible claims up to a protocol-fixed cap,
all inferred risk candidates, all source-present omission candidates, and a
balanced sample of warnings and clear checks. Record exclusions and unavailable
evidence rather than silently dropping them.

## Annotation procedure

Two independent reviewers annotate each item using
[`annotation.schema.json`](annotation.schema.json). Reviewers first lock the
`primary` packet judgments for claim support, assignment, omissions, and risk
applicability without seeing system dispositions or warning flags. Only then may
the coordinator release the `warning_followup` packet. They may use `unclear` or `unavailable`
and must not infer facts from model memory. Disagreements are adjudicated by a
third reviewer after the independent phase; adjudication never overwrites the
original records.

The local packet builder assigns opaque study, target, claim, fact, risk, and
warning identifiers. It may attach bounded evidence in the private reviewer
interface, but the public annotation record stores only those identifiers and
categorical decisions. The row-oriented paired-label export likewise stores only
`target_blind_id`; its separately supplied target map is private execution material
and must not be published. Annotator names and contact details are out of scope.

The builder reads each completed target run's typed claim-gate, content/final
FactReasoner, omission, publication-validation, repair, risk-mapping, and pipeline
result artifacts, plus the checkpoint-scoped family-risk authorization artifact.
It verifies their existing content hashes and pipeline file
bindings before producing anything. The sealed private control manifest records the
union of semantic subjects emitted by either condition. A subject can therefore be
present in one condition and explicitly absent in the other; an absent condition
entry carries no artifact or evidence binding and does not manufacture a reviewer
item. The manifest records:

- every emitted claim, field-audit subject, Nexus risk candidate, and warning or
  clear-check subject, together with its per-condition presence state;
- exact artifact and record hashes, JSON Pointers, evidence/source hashes, and quote
  or structured coordinates. For every present native artifact binding, the builder
  resolves the JSON Pointer in the sealed artifact, requires canonical equality with
  the bound record, and records that canonical record's digest. Manifest validation
  then requires the digest to appear in the subject's native-hash inventory and the
  artifact name/hash to appear in the sealed run inventory;
- each condition's exact pipeline-result, frozen-source-input, and treatment-surface
  receipts, which must match its quality-report target before human results are
  accepted;
- the complete family-membership, checkpoint-applicability, and authorized-context
  chain for every family-derived Nexus input;
- per-condition gate disposition, field-scoped FactReasoner outcomes, and repair
  predecessor/selected hashes; and
- the digest of each phased reviewer payload and its fixed randomized order.

Item and evidence IDs are HMAC-derived from a coordinator-owned key, so the public
packet does not expose native candidate IDs. Exact model IDs/revisions, source URIs,
source hashes, and filesystem paths are absent from reviewer packets. Bounded
evidence values are target- and URL-redacted. To make entity/checkpoint/relation
judgments possible, the builder emits a separate controlled target sheet containing
only the exact model ID, immutable revision, and assignment instruction. It contains
no A/B condition, implementation identity, source identity, or local path. Reviewers
receive the target sheet alongside each independently presented A/B packet. The exact
target is therefore available for assignment judgments while treatment and system
identity remain blinded. Packets
and target sheets should still remain in the private study workspace because packets
contain evidence excerpts; "public" here means the reviewer-facing half of the
private/public split, not a repository publication.

Primary field packets omit the pipeline's candidate count, source-presence decision,
omission disposition, and warning flag. Reviewers must judge the bounded evidence
itself. Every Nexus candidate, including one withheld by the applicability gate,
carries evidence resolved from its exact use contexts and supporting claims. An
accepted public derivation adds projection lineage but is not required for review
evidence.

Create a 32-byte key in a mode-0600 file and run, for example:

```sh
python3 evaluation/item_manifest.py \
  --run A:target-blind-001=/private/runs/condition-a/target-001 \
  --run B:target-blind-001=/private/runs/condition-b/target-001 \
  --study-unit-id study-unit-001 \
  --blinding-key-file /private/evaluation/blinding.key \
  --private-manifest /private/evaluation/item-manifest.json \
  --public-packet-dir /private/evaluation/reviewer-packets
```

Repeat `--run` for every target. A single-condition census supplies exactly one `A`
run per opaque target; a paired comparison supplies exactly one `A` and one `B` run
per target. Thus the published-card census is represented by twelve `A:...=...`
arguments. Paired runs must have identical target/source bindings across conditions.
The command also requires a non-symlink key and new output paths. The manifest is
written mode 0600 and all outputs are immutable: reruns must use new paths. Each
condition produces one `*-primary.json` and one `*-warning_followup.json`, containing
only subjects present in that condition; each target also produces one
condition-neutral `*-target.json` sheet. Do not release the follow-up packet until
the primary judgments for that packet have been locked.

The manifest's `warning_present` values are system facts, not reviewer labels. The
paired-label export omits that field; the audit derives it from the sealed private
manifest when computing warning confusion counts.

The adjudicated row export is kind-scoped. Claim rows populate support,
source-binding, and assignment fields; benchmark-score claims additionally populate
`score_row`; field rows populate omission and conflict visibility; risk rows populate
grounding and applicability; warning rows populate `actionable_error`. Every other
label must be `not_applicable`. The audit enforces these invariants and computes each
distribution only over its eligible item kind, with explicit denominators. Completed
labels cover exactly the `(condition, target, item)` triples marked present in the
control manifest. No label row is permitted or required for an explicitly absent
condition subject, so label and metric universes remain condition-specific.

This item universe is exhaustive over emitted run artifacts and their frozen
candidate inventories. It is not an independent inventory of everything available
in the source material. Consequently, it cannot by itself estimate missed source
opportunities, document thinness, omission recall beyond the frozen candidates, or
risk-retrieval recall. Those claims require a separately constructed, blinded
source-opportunity inventory whose items exist independently of either system's
outputs.

This foundation likewise does not yet ask reviewers for a direct paper failure
category/materiality label, separate taxonomy-validity and publisher-attribution
labels, or a pre/post repair benefit/harm label. The manifest binds the necessary
risk and repair artifacts, but those judgments require a preregistered extension to
the annotation instrument before they can support comparative claims.

## Analysis plan

Report target-level denominators and missingness for every metric. The primary
paired outcomes are unsupported-claim rate, wrong-assignment rate,
source-binding error rate, source-present omission rate, grounded/applicable
risk rate, and useful-warning rate. Report condition-specific rates and paired
differences with target-clustered bootstrap confidence intervals. Use paired
tests only when their assumptions and preregistered endpoints are satisfied.

Report inter-reviewer agreement before adjudication for every categorical task
(Krippendorff's alpha, plus a prevalence-robust coefficient when labels are
highly imbalanced). Publish the adjudication rate and uncertainty rate. Do not
collapse `unavailable` into `unsupported`, or `unclear` into an error.

Before any results are described, verify that:

- the source bundles replay and paired source-input digests match exactly;
- treatment digests differ only where required by the preregistered contrast;
- no target used during development entered the held-out sample;
- packet identifiers map one-to-one to immutable local artifacts;
- every annotation file validates against the checked-in schema; and
- no private source material appears in the public repository.

[`annotation-template.json`](annotation-template.json) intentionally has empty
task arrays and `completed: false`. It is not a human result.
