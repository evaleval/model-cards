# EvalEval Model Cards

EvalEval Model Cards builds an evaluation-focused card for one exact model
revision from a prepared source specification. Every proposed field keeps its
source revision, digest, evidence location, and relation to the target model.

> **Current status**
>
> The offline evidence, policy, review-event, and rendering core works. It
> produces deterministic JSON and static HTML from prepared JSON inputs.
> Source collection, candidate extraction, semantic claim-support checks, and
> a human review protocol are still being built. The examples are fictional
> demonstrations, not reviewed documentation of real models.

![Model Card pipeline](docs/figures/model-card-pipeline.svg)

*Only policy-accepted bindings fill the card. Every constructed binding remains
in the evidence ledger, including wrong-scope, conflicting, and unverifiable
claims.*

## See the workflow

The public core makes four decisions visible.

1. **Fix the target.** A card belongs to one `namespace/model` at one resolved
   40-character revision.
2. **Bind evidence.** A candidate links a proposed value and schema field to an
   exact quote or JSON Pointer. The binding also retains the source role,
   revision, digest, and relation to the target.
3. **Apply policy.** Field, source role, relation, and target scope determine
   whether the binding is accepted, withheld, or rejected. Conflicting
   accepted values leave the field unfilled.
4. **Inspect the artifact.** The output contains the 38-field schema v5 card,
   its evidence ledger, and append-only review events.

The [pipeline note](docs/PIPELINE.md) gives the input contract, source roles,
decision rules, quality boundary, and next build phase.

## Look at the examples

All three examples are fictional and run offline.

| Example | Decision under test | Files |
| --- | --- | --- |
| Mixed evidence | Exact-target fields enter the card. A family quantity is withheld. A score-free comparison link is retained. | [input](examples/synthetic-input.json) · [JSON](examples/cards/mixed-evidence/card.json) · [HTML](examples/cards/mixed-evidence/card.html) |
| Family scope | An explicit base model is accepted. A family-wide training quantity does not transfer to the checkpoint. | [input](examples/cards/family-scope/input.json) · [JSON](examples/cards/family-scope/card.json) · [HTML](examples/cards/family-scope/card.html) |
| Conflicting sources | Two exact-revision sources disagree. The disputed field stays `Not specified` and both bindings remain visible. | [input](examples/cards/conflicting-sources/input.json) · [JSON](examples/cards/conflicting-sources/card.json) · [HTML](examples/cards/conflicting-sources/card.html) |

The [example guide](examples/cards/README.md) records the expected result for
each case. These cards test mechanism and policy. They are not evidence of
real-world card quality.

## Run it

Python 3.9 or newer is sufficient. The package has no runtime dependencies.

```sh
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

Build a fresh copy of the mixed-evidence example.

```sh
python3 -m model_cards build examples/synthetic-input.json \
  --json build/mixed-evidence.json \
  --html build/mixed-evidence.html
```

Inspect the artifact or one field.

```sh
python3 -m model_cards inspect build/mixed-evidence.json
python3 -m model_cards inspect build/mixed-evidence.json \
  --field training_context.training_data_size
```

The CLI refuses to overwrite an existing output.

## What is reliable today

- Exact target identity, revision-format checks, and declared-revision equality
- Typed quoted and structured evidence coordinates
- Source revision and SHA-256 retention
- Narrow relation and source-role policy
- Deterministic projection and stable binding identifiers
- Conflict handling without last-write-wins
- Append-only review events
- JSON and self-contained static HTML output
- Offline tests and examples

The source documents themselves are not embedded in an artifact. They can be
held separately and replayed with `verify_artifact_sources` before export.

## Current boundary

An exact quote match or resolved JSON Pointer proves where a fragment came
from. It does not prove that the fragment supports the proposed value or that
the value belongs in the chosen field. That semantic check is the main missing
publication gate.

The current implementation also starts from prepared sources and candidates.
It does not search, download model files, call a model provider, or run an
evaluation. Schema v5 is fixed in code with 33 substantive fields and five
computed quality fields. Review events exist, while reviewer roles and a human
review protocol do not.

## Uses

- Audit one prepared card for one model revision. Trace any projected value to
  its source fragment, relation decision, and conflict state.
- Study documentation gaps across a reviewed card collection. Compare which
  fields are missing or disputed without discarding field-level provenance.

The first use works with the current core. The second requires the real-model
pilot, semantic support gate, and review protocol described below.

## Next build phase

1. Add a semantic claim-support gate with adversarial tests.
2. Add a pinned Hugging Face adapter for exact-revision metadata and selected
   snapshot files.
3. Run a local three-model pilot, fix the failure classes, then expand to a
   twelve-model evaluation set.
4. Define the human review protocol and report field-level precision, scope
   errors, abstentions, coverage, and review time.
5. Separate schema profiles from the core so that new fields can be proposed
   without weakening the provenance contract.

Useful contributions include source adapters, deterministic pointer-to-field
mappings, adversarial scope fixtures, semantic support checks, schema-profile
proposals, evaluation protocols, and research uses for a future card
collection.

## License and provenance

The project is MIT licensed. See [LICENSE](LICENSE). Two small quote-matching
primitives adapted from Auto-BenchmarkCards are documented in
[NOTICE.md](NOTICE.md). The package has no runtime dependency on that project.
