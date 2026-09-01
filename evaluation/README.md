# Held-out evaluation design

This directory defines a future human evaluation. It contains no annotations,
reviewer identities, source text, or quality results. The checked-in JSON file is
an empty, schema-valid template only.

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

- Freeze the protocol before selecting held-out targets.
- Exclude implementation fixtures, the three canaries, the twelve-target pilot,
  and checked-in examples.
- Sample 30 previously unseen targets, stratified across base/instruction-tuned
  releases, source-rich/source-limited releases, access states, model families,
  and reported-use contexts. Do not expand this into a 200–300-card batch.
- Generate paired outputs from the same exact source bundle and configuration.
  Randomly label the two conditions `A` and `B` independently for each target;
  retain the decoding key outside annotation packets.
- Present only bounded evidence needed for the current item. Model source bodies,
  quotations, run logs, and annotations remain under the gitignored local run
  directory.
- Randomize item order and suppress system name, filenames, lifecycle labels,
  and other condition-revealing metadata in the reviewer view.

Each target should contribute all eligible claims up to a protocol-fixed cap,
all inferred risk candidates, all source-present omission candidates, and a
balanced sample of warnings and clear checks. Record exclusions and unavailable
evidence rather than silently dropping them.

## Annotation procedure

Two independent reviewers annotate each item using
[`annotation.schema.json`](annotation.schema.json). Reviewers first judge the
claim and assignment without seeing the other condition, then assess omissions,
risk applicability, and warning utility. They may use `unclear` or `unavailable`
and must not infer facts from model memory. Disagreements are adjudicated by a
third reviewer after the independent phase; adjudication never overwrites the
original records.

The local packet builder assigns opaque study, target, claim, fact, risk, and
warning identifiers. It may attach bounded evidence in the private reviewer
interface, but the public annotation record stores only those identifiers and
categorical decisions. Annotator names and contact details are out of scope.

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

- the source bundles replay and paired targets/configurations match;
- no target used during development entered the held-out sample;
- packet identifiers map one-to-one to immutable local artifacts;
- every annotation file validates against the checked-in schema; and
- no private source material appears in the public repository.

[`annotation-template.json`](annotation-template.json) intentionally has empty
task arrays and `completed: false`. It is not a human result.
