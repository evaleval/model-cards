# Model Cards

One evidence-bound Model Card for one exact Hugging Face model revision.

The card documents a checkpoint, not a family and not a repository. That distinction is
the whole design. A sentence that is true of the base model, of another size in the same
release, or of a model the developer compares against is wrong on this card even though
it is true somewhere, and it is the error that automated cards make most often. Every
value here therefore carries what it was taken from and what that source was talking
about, and a value whose entity cannot be established is refused and recorded rather than
published.

## The public contract

Exactly seven sections and 33 fields, closed:

| Section | Fields |
| --- | --- |
| `identity` | `model_id`, `name`, `developed_by`, `model_type`, `license`, `release_date`, `version`, `summary` |
| `lineage` | `base_models`, `model_family`, `derivatives` |
| `specifications` | `architecture_type`, `num_parameters`, `context_length`, `precision`, `model_size`, `input_output` |
| `training_context` | `training_data`, `training_data_size`, `data_cutoff`, `adaptations` |
| `access_and_adoption` | `access_type`, `downloads`, `likes` |
| `evaluation` | `results_summary`, `benchmark_scores`, `human_evals`, `safety_evals` |
| `links` | `model_card`, `system_card`, `tech_report`, `code_repository`, `citation` |

`schema/model-card.schema.json` is the contract and `src/model_cards/publication_contract.py`
is its single definition in code; the generator imports it rather than restating it. A
field with no support is `Not specified`. A field that cannot apply to this class of model
is `Not applicable`. Neither is ever a guess.

The binding ledger, the frozen sources, the run manifest and the usage log stay local.
`assert_public_projection` refuses to let a private key, a local path or a credential
cross the export boundary, and a guarded prose field that reproduces twelve consecutive
words of a source is withheld rather than published.

## What is in the box

**The publication surface**, which a reader of a card touches:

- `publication_contract`, `publication_schema` the contract and its validator
- `public_markdown` the deterministic Markdown companion, generated from the exact JSON
  bytes and carrying their SHA-256
- `public_export` the leak guard on the export boundary
- `hf_adapter`, `source_bundle` the frozen snapshot of a repository at an exact commit

**`model_cards.core`**, the generator. It reads the Auto-BenchmarkCard composer as a
library, at the commit recorded in `composer-pin.json`; the bridge refuses a different
commit unless the caller asks for it, so a card can always say which composer wrote it.

## Running it

```sh
pip install -e '.[generate]'

# free: freeze the sources for an exact revision
modelcards collect 'allenai/OLMo-2-1124-7B@7df9a82518afdecae4e8c026b27adccc8c1f0032' \
    --bundle-dir bundles

# paid: compose the card from that frozen bundle
modelcards compose 'allenai/OLMo-2-1124-7B@7df9a82518afdecae4e8c026b27adccc8c1f0032' \
    --bundle-dir bundles --llm-usage-log runs/olmo/llm_usage.jsonl \
    --out runs/olmo/olmo.json

# the published projection, the Markdown companion, and the inspector
modelcards export runs/olmo/olmo.json --kind public --format json --out cards/olmo.json
modelcards export runs/olmo/olmo.json --kind public --format markdown --out cards/olmo.md
modelcards inspect runs/olmo/olmo.json --format html --out olmo.html

# a list of targets, four to six at a time, each in its own process under a deadline
modelcards batch targets.txt --phase both --bundle-dir bundles --out runs/batch \
    --concurrency 5 --resume
```

`modelcards inspect --format html` writes a self-contained, script-free page where every
field links to the exact span it came from, with the relation and the reason beside it,
and a section listing what was withheld and why. That page is the point: a card you cannot
click through is a set of assertions.

Serving is configured from the environment (`src/model_cards/core/route.py`) and probed
before spending with `scripts/probe_route.py`. Every call runs with a server-enforced JSON
schema, a temperature of 0 and a per-stage token cap, and every call is written to a usage
log, per card, so what a run cost is a read and not an estimate.

## The cards here

`cards/` holds twelve generated candidates: six flagship base and instruct pairs across
five developers, regenerated from a pipeline run rather than hand-edited. They are
candidates. None has been human-reviewed, and none is an official model card.

Four of them (`llama-3.1-8b*`, `gemma-3-4b-*`) carry no `architecture_type` and no
`context_length`, because those repositories are gated: the Hub returns the README to an
unauthorized token and 403 on `config.json`. The card records the absence rather than
filling it from prose, which is the behaviour this project exists to have.

## Evaluation

`src/model_cards/core/eval/` holds the instruments, each frozen by content so that its id
changes when its question does:

- **judge** whether each value is supported by the frozen sources, what entity the
  supporting sentence is really about, and whether a `Not specified` field was an honest
  abstention or a miss;
- **screen** whether the card is right, checked against the live public record, with
  categories named for the error classes above;
- **probes** candidate splices, selected by a surface rule that uses no part of the
  resolver, because a probe built on the resolver can only confirm it agrees with itself;
- **sample** a seeded stratified draw over stage, source richness and provenance.

`evaluation/` holds the human annotation schemas and the paired-audit tooling. Human
labels come from people.

## Status

This is a working generator and a set of candidates, not a released corpus. The
faithfulness judge and the screen have not been run on these twelve cards.
