# Public reference core

The `model_cards` package is the source-free policy core extracted from the larger
research workflow. It turns pre-collected candidate values and evidence into a Model
Card artifact for one exact revision. It does not collect sources, search the web, or
call a model provider.

The package provides the schema, typed binding ledger, scope policy, deterministic
projection, append-only review events, and static output used to test the central
scientific contract.

## Install and test

```sh
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

Python 3.9 or newer is sufficient. Runtime code has no third-party dependencies and
all tests run offline.

## Build and inspect a fixture

The CLI fixture is synthetic and lives under `tests/fixtures`. It tests scope handling;
it is not presented as a generated research result.

```sh
python3 -m model_cards build tests/fixtures/synthetic-input.json \
  --json build/synthetic-card.json \
  --html build/synthetic-card.html

python3 -m model_cards inspect build/synthetic-card.json
python3 -m model_cards inspect build/synthetic-card.json \
  --field training_context.training_data_size
```

The family-wide training quantity in the fixture is retained as a withheld binding.
The exact-target field stays `Not specified`.

## Scientific contract

The rendered card is a projection of the evidence ledger. A proposed value is accepted
only when its source scope, relation to the target, field policy, and evidence
verification agree. Non-target evidence remains inspectable as withheld evidence.
Malformed or non-verbatim evidence is rejected.

The relation rules are deliberately narrow.

- Target-owned identity, specification, training, access, evaluation, and link fields
  require exact-target evidence from a source scoped to the same revision.
- A declared base-model relation may populate `lineage.base_models`.
- Family facts do not transfer to an individual checkpoint.
- Comparison and sibling relations may populate score-free external links, but not the
  target model's evaluation scores.
- EvalEval records are link and discovery evidence, not authority for
  checkpoint-specific scores.

Conflicting accepted values do not use last-write-wins. The field remains unfilled and
appears in `provenance_and_quality.flagged_fields`.

Schema v5 fixes the 38 section and field names. `validate_complete_card` checks that
shared structural contract. `validate_core_card` also checks the narrower value profile
emitted by this lean binding core. The checked-in research examples preserve
the full generator's value shapes and are not round-tripped through the lean core.

Artifacts record source revisions, SHA-256 digests, quote coordinates, and structured
pointers without requiring public source documents. `verify_artifact_sources` can
replay the evidence against separately held sources before export.

## Review semantics

A review command writes a new artifact and appends one event. It does not alter the
generation-time binding or prior events.

```sh
python3 -m model_cards review INPUT.json BINDING_ID \
  --action withhold \
  --reason needs_check \
  --output REVIEWED.json
```

The current public core records the action and reason but does not invent a reviewer
identity. Named human roles and release approval belong to the review protocol that is
still being prepared.

## Public example export

Full research artifacts can contain source text, local paths, provider traces, and audit
records. The public exporter copies only the generated `card` projection, scans it for
private structure and paths, and writes a canonical digest record.

```sh
python3 -m model_cards.public_example FULL_ARTIFACT.json examples/generated/slug \
  --status development \
  --automated-audit projected_claim_support_scope_passed
```

The output directory contains `card.json`, `card.md`, and `public-export.json`. The
export fails if blocked keys, local paths, credentials, private run names, or source
content appear in the projection. Audit results are operator-supplied annotations from
non-public audit records; the export states that boundary rather than embedding those
records.

## Composer dependency

The core uses two Composer primitives. They are whitespace and
typographic-punctuation normalization, and case-sensitive exact-substring
verification. Their small MIT-licensed implementation is included in
`model_cards/quote.py`; see [NOTICE.md](../NOTICE.md).
There is no runtime Git or adjacent-repository dependency.

## Boundary

This package can validate, project, inspect, review, and render supplied bindings. It
does not yet expose the complete source collector, document extraction, model-assisted
composition, EAV/FactReasoner audit, batch runner, or release workflow used by the local
research system.
