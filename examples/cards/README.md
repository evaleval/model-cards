# Synthetic Model Card examples

These examples test the workflow's decisions. They do not document real
models. Every organization, model, report, measurement, URL, and source record
is fictional.

Each example has a prepared input specification, a deterministic JSON artifact,
and a self-contained HTML inspection page. The rendered artifacts do not embed
the complete source documents from their inputs.

## Mixed evidence

Files include the [input](../synthetic-input.json),
[JSON artifact](mixed-evidence/card.json), and
[HTML inspection page](mixed-evidence/card.html).

This case combines exact metadata, exact-revision text, a fictional benchmark
row, an index link, and a comparison-model link. Thirteen bindings are accepted.
One family-wide training quantity is withheld, so
`training_context.training_data_size` remains `Not specified`.

## Family scope

Files include the [input](family-scope/input.json),
[JSON artifact](family-scope/card.json), and
[HTML inspection page](family-scope/card.html).

The exact checkpoint declares its family and an explicit base model. Those
claims enter their permitted fields. A report states a training quantity for
the family. Its coordinates verify, but its `model_family` relation causes the
binding to be withheld from the checkpoint card.

## Conflicting sources

Files include the [input](conflicting-sources/input.json),
[JSON artifact](conflicting-sources/card.json), and
[HTML inspection page](conflicting-sources/card.html).

Two exact-revision metadata records propose different context lengths. Both
bindings pass the current individual policy. Projection flags both with
`conflicting_accepted_values` and leaves `specifications.context_length` as
`Not specified`.

## Regenerate in a temporary directory

The CLI refuses to overwrite outputs. These commands leave the committed files
untouched.

```sh
tmp_dir="$(mktemp -d)"

python3 -m model_cards build examples/synthetic-input.json \
  --json "$tmp_dir/mixed-evidence.json" \
  --html "$tmp_dir/mixed-evidence.html"

python3 -m model_cards build examples/cards/family-scope/input.json \
  --json "$tmp_dir/family-scope.json" \
  --html "$tmp_dir/family-scope.html"

python3 -m model_cards build examples/cards/conflicting-sources/input.json \
  --json "$tmp_dir/conflicting-sources.json" \
  --html "$tmp_dir/conflicting-sources.html"
```

The test suite rebuilds every example and compares it byte for byte with the
committed JSON and HTML outputs.
