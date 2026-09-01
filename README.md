# EvalEval Model Cards

EvalEval Model Cards is a small offline reference implementation for
evaluation-focused cards about one exact model revision. It keeps the rendered
card separate from an immutable field-level evidence ledger, so unsupported or
wrong-scope candidates remain inspectable without becoming target facts.

This first baseline provides:

- the complete 38-field Model Card schema v5;
- exact `model_id` plus resolved 40-character revision identity;
- typed quoted and structured evidence bindings;
- explicit exact-target, base-model, derivative-model, family,
  sibling-checkpoint, comparison-model, and unresolved relations;
- fail-closed acceptance, withholding, and rejection;
- deterministic projection and stable binding identifiers;
- append-only review events with no invented reviewer identity;
- JSON and self-contained static HTML output; and
- a dependency-free offline command-line interface.

It intentionally does not collect sources, search the web, call a model
provider, or run evaluations. The included example is entirely synthetic.

## Install and test

Python 3.9 or newer is sufficient. The package has no runtime dependencies.

```sh
python3 -m pip install -e .
```

The single project test command is:

```sh
python3 -m unittest discover -s tests -v
```

All tests and examples run offline.

## Synthetic end-to-end example

Build a JSON artifact and static inspection page:

```sh
python3 -m model_cards build examples/synthetic-input.json \
  --json build/synthetic-card.json \
  --html build/synthetic-card.html
```

Inspect the result or focus on one field:

```sh
python3 -m model_cards inspect build/synthetic-card.json
python3 -m model_cards inspect build/synthetic-card.json \
  --field training_context.training_data_size
```

The synthetic family-wide training quantity is deliberately retained as a
withheld binding. It remains visible in both outputs while the exact-target
field stays `Not specified`.

## Scientific contract

The card is a projection, not the primary evidence record. A candidate becomes
an accepted target fact only when its source scope, relation, field policy, and
evidence verification agree. Verified but non-target evidence is withheld;
malformed or non-verbatim evidence is rejected. Neither state is silently
dropped.

Artifacts retain source revisions, SHA-256 digests, exact coordinates, and
structured pointers without embedding full source documents. Call
`verify_artifact_sources` with separately held sources to replay every quote
and structured fragment before export.

The relation rules are intentionally narrow:

- Target-owned identity, specification, training, access, evaluation, and link
  fields require `exact_target` evidence from a source explicitly scoped to the
  same model revision. Hugging Face metadata and snapshot sources must also use
  that exact revision; developer-code sources must use a resolved commit.
- `lineage.base_models` accepts an explicit structured `base_model` relation.
- The v5 `lineage.derivatives` field is an exact-target aggregate; individual
  derivative rows are not projected by this schema.
- Family facts never transfer to a checkpoint. A target's declared membership
  in a family is instead an exact-target claim about that target.
- Comparison and sibling relations may populate only score-free external links
  in `evaluation.related_model_scores`.
- EEE is link and index evidence, not authority for checkpoint-specific scores.

Conflicting accepted values do not use last-write-wins. The field remains
unfilled and the conflict appears in `provenance_and_quality.flagged_fields`.
The five quality fields are computed directly from the substantive ledger and
do not receive recursive evidence bindings.

## Source roles

The baseline models these source roles without distributing collected source
content:

| Role | Intended use |
| --- | --- |
| Exact Hugging Face metadata | Model identity and explicit structured facts at a resolved revision |
| Selected Hugging Face snapshot file | Exact-revision developer text |
| Developer report | A report explicitly associated with the target |
| Pinned developer code | Developer-owned documentation with explicit target scope |
| EEE index | Links and external-record discovery only |
| Synthetic input | Redistributable tests and examples |

Broad discovery, third-party commentary, mirrors, generic leaderboards, and
API-only ingestion are outside this baseline.

## Composer dependency decision

The lean core needs exactly two Composer primitives:

- whitespace and typographic-punctuation normalization; and
- case-sensitive exact substring verification.

The public Auto-BenchmarkCards package does not expose the generic schema
runtime used by the earlier prototype. Importing that larger runtime would also
make this offline package unnecessarily heavy. The two required public
MIT-licensed functions are therefore included as the small local kernel in
`model_cards/quote.py`; see [NOTICE.md](NOTICE.md). There is no runtime Git or
adjacent-repository dependency.

## Review semantics

A review command always writes a new artifact. It appends `accept`, `withhold`,
or `reassign` and leaves the generated bindings and prior events unchanged:

```sh
python3 -m model_cards review INPUT.json BINDING_ID \
  --action withhold --reason needs_check --output REVIEWED.json
```

This baseline records no person, team, or role on an event. A future review
protocol can define those semantics separately without changing the scientific
binding core.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
