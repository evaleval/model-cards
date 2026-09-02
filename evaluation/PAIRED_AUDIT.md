# Offline paired failure audit

`paired_audit.py` places current Model Card engineering measurements beside the
failure categories reported for Auto-BenchmarkCards. It does not treat the two
systems as a common benchmark: they document different objects, use different
schemas and sampling designs, and do not share a valid rate denominator.

The harness reads only existing JSON/CSV artifacts. It has no network or model
client and cannot make provider calls.

## Inputs

At least one named condition is required. A condition is a privacy-safe
`model-card-quality-report/v3` file produced by `modelcards report`.

- With one condition, the harness audits its aggregate metrics and verifies its
  paired replay record when present.
- With two conditions, their target requests and per-target `inputs` surface
  digests must match exactly. The report then includes mechanical count deltas
  in `condition_B - condition_A` direction. A delta is not an accuracy or
  superiority result.
- The released Auto-BenchmarkCards `eval/results_summary.json` supplies source
  support, source-relative omission, candidate-risk, and warning context.
- The released `eval/s150/screen/verifier_ratings.csv` supplies counts of
  verifier-confirmed, screen-raised findings by the paper's six broad labels.
  Those counts do not estimate prevalence or screen recall.
- The optional `baseline-full-engineering-read/v1` artifact records the small
  source-parity comparison already available for three canaries. Its reference
  gate is not human truth.
- Optional completed labels use the row-oriented
  `model-card-paired-audit-labels/v1` format. This is an adjudicated audit export,
  distinct from the per-reviewer `annotation.schema.json` packet. Each row includes
  factual support, source binding, assignment, omission, conflict, risk, and warning
  decisions and names only an opaque `target_blind_id`.
- Completed labels require a private `model-card-paired-audit-target-map/v1` file.
  The map binds each opaque target ID to one exact quality-report request so the
  harness can verify complete coverage. It must cover every report target one-to-one,
  and paired conditions must expose the same item IDs for every opaque target.

All input paths, including the private target map, are reduced to SHA-256 receipts in
the output; local paths, exact target identities, and source text are not copied.

## Example command

Run from the repository root after supplying a local quality report and the released
Auto-BenchmarkCards summary and verifier-label files. Choose a new output path because
the harness refuses to overwrite an audit. Paths below are placeholders; the public
repository does not ship private run artifacts or a sibling paper checkout.

```sh
python3 evaluation/paired_audit.py \
  --condition current=/path/to/model-card-quality-report.json \
  --auto-benchmarkcards-summary /path/to/auto-benchmarkcards/eval/results_summary.json \
  --auto-benchmarkcards-verifier-labels /path/to/auto-benchmarkcards/eval/s150/screen/verifier_ratings.csv \
  --identical-source-engineering-read /path/to/baseline-full-engineering-read.json \
  --labels evaluation/paired-audit-labels-template.json \
  --output /path/to/new-paired-failure-audit.json
```

When `--labels` names an `annotation_complete` record, also pass the private map:

```sh
python3 evaluation/paired_audit.py \
  --condition A=/path/to/condition-a-quality-report.json \
  --condition B=/path/to/condition-b-quality-report.json \
  --labels /private/path/completed-paired-labels.json \
  --target-map /private/path/paired-audit-target-map.json \
  --output /path/to/new-paired-audit.json
```

The map validates against
[`paired-audit-target-map.schema.json`](paired-audit-target-map.schema.json). Keep the
map under an ignored private run directory; public labels contain only opaque IDs.

For a true paired engineering comparison, pass two quality reports:

```sh
python3 evaluation/paired_audit.py \
  --condition A=/path/to/condition-a-quality-report.json \
  --condition B=/path/to/condition-b-quality-report.json \
  --output /path/to/new-paired-audit.json
```

The command fails if the conditions do not contain the same targets or their
frozen input-surface digests differ.

## What is measurable now

The checked run artifacts support deterministic counts for:

- coordinate, entity-scope, field-fit, and value-support gate dispositions;
- mechanically detected wrong entity, checkpoint, relation, field, and score
  row conditions;
- omissions relative to the frozen candidate inventory and explicit conflict
  visibility;
- FactReasoner atom/field coverage, support, contradiction, neutral,
  unavailable, and source-limited outcomes;
- risk-context grounding, taxonomy mapping, and applicability dispositions; and
- input parity, replay stability, and paired count changes.

With complete labels and their private target map, the audit additionally reports
the human source-binding distribution and warning precision/recall for the supplied,
fully covered item universe. It rejects a missing condition, target, or paired item.

These are pipeline measurements. In particular, `atoms_decided / atoms_total`
can be 100% when every outcome is `unavailable`, so the audit separately reports
informative coverage excluding unavailable outcomes. A zero mechanical finding
count does not establish a zero error count.

The Auto-BenchmarkCards summary is reported as reference context only. Its
`wrong-section-splice` label is intentionally not split retrospectively into
wrong entity, checkpoint, relation, field, or score row. Doing so would create
labels the verifier did not provide.

## What still needs blinded human annotation

The following cannot be established from pipeline artifacts alone:

- factual support and correctness of source binding;
- whether an accepted or withheld item truly has the wrong entity, checkpoint,
  relation, destination field, or score row;
- omissions beyond the source material and candidate inventory inspected;
- conflict-detection recall and whether a visible conflict is useful;
- whether mapped risks are grounded, applicable, or misattributed; and
- warning precision and recall over a protocol-fixed universe containing both
  warned and non-warned items.

`paired-audit-labels.schema.json` defines that future labelled universe, and
`paired-audit-labels-template.json` is deliberately empty. The harness computes
warning precision and recall only for an `annotation_complete`, blinded record
whose annotator confirmation is complete and whose private target map proves full,
matched condition coverage. It never interprets the empty template as a result.
