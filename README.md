# Model Cards

One evidence-bound Model Card for one exact Hugging Face model revision.

The card documents a checkpoint, not a family and not a repository. That distinction is
the whole design. A sentence that is true of the base model, of another size in the same
release, or of a model the developer compares against is wrong on this card even though
it is true somewhere, and it is the error that automated cards make most often. Every
value here therefore carries what it was taken from and what that source was talking
about, and a value whose entity cannot be established is refused and recorded rather than
published.

![The pipeline: a selected model release, multi-source collection, scoped-evidence binding, evidence-limited composition, and the card with its binding ledger](assets/model-card-pipeline.png)

1. **Selected model release.** One `model_id@revision`, never a branch.
2. **Multi-source collection.** The Hub snapshot at that commit, the paper behind a
   title gate, the developer's repository and pages, the public evaluation records; all
   frozen with hashes (`collect`).
3. **Scoped-evidence binding.** Verbatim quotes, each resolved to the entity it is about
   and admitted or refused per field (`frame`, Stage A, the gates, EAV).
4. **Evidence-limited composition.** The writer sees accepted evidence only; the leaf
   check and the excerpt guard run on what it wrote, FactReasoner does too when it is
   enabled, and the risk stage maps the finished card onto the AI Risk Atlas (Stage B,
   checks, risks).

What comes out is the card and, beside it, the ledger of every accepted and every refused
value with its reason. [ARCHITECTURE.md](ARCHITECTURE.md) walks through each stage.

## The public contract

Exactly eight sections and 34 fields, closed:

| Section | Fields |
| --- | --- |
| `identity` | `model_id`, `name`, `developed_by`, `model_type`, `license`, `release_date`, `version`, `summary` |
| `lineage` | `base_models`, `model_family`, `derivatives` |
| `specifications` | `architecture_type`, `num_parameters`, `context_length`, `precision`, `model_size`, `input_output` |
| `training_context` | `training_data`, `training_data_size`, `data_cutoff`, `adaptations` |
| `access_and_adoption` | `access_type`, `downloads`, `likes` |
| `evaluation` | `results_summary`, `benchmark_scores`, `human_evals`, `safety_evals` |
| `links` | `model_card`, `system_card`, `tech_report`, `code_repository`, `citation` |
| `risks` | `possible_risks` |

`risks.possible_risks` holds entries of the IBM AI Risk Atlas, selected for this
checkpoint from what the card itself says and bound to the frozen copy of the taxonomy in
the source bundle: the binding ledger records, for every row, the JSON pointer to its
entry, so the definition a label came from is one lookup away. It is a taxonomy selection, not a source quotation,
the Markdown says so above the table, and it is the one field the faithfulness judge does
not grade.

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
pip install -e .               # the publication surface: contract, validator, Markdown
pip install -e '.[generate]'   # plus the generator and the modelcards command, which
                               # need the composer at the commit in composer-pin.json
                               # (branch composer-library of evaleval/auto-benchmarkcard)
pip install -e '.[eval]'       # plus the Anthropic client for the paid judge and screen

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
schema, a temperature of 0 and a per-stage token cap, and every composer call is written
to a usage log, per card, so what a run cost is a read and not an estimate. FactReasoner,
when enabled, calls its own route through its own client and is accounted for separately.

## The cards here

`cards/` holds 426 generated candidates over 170 developers, from two seeded draws of
the Hugging Face models that appear in public evaluation records, plus a roster of twelve
flagship base and instruct pairs. They come from three pipeline runs on one code state
and are not hand-edited. They are candidates: none has been human-reviewed, and none is
an official model card.

They carry 1,368 benchmark score rows read out of the tables of READMEs and reports, 347
of the 426 carry AI Risk Atlas entries, and 59 carry a technical report the pipeline was
able to bind to the checkpoint rather than to its family.

51 of them carry no `architecture_type`, most of them because the repository is gated: the
Hub returns the README to an unauthorized token and 403 on `config.json`. The card records
the absence rather than filling it from prose, which is the behaviour this project exists
to have.

Every card is a JSON file and a Markdown companion named after the model. The Markdown
is generated from the exact JSON bytes and carries their SHA-256, so the two can be
checked against each other; the JSON is the contract, the Markdown is for reading.

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

`scripts/audit_sweep.py` re-checks a finished run without importing the generator: every
quote against the frozen bytes at its recorded offset, every structured pointer against
the file it names, every card against the contract. It exits non-zero on any problem, so a
run that passes it did not grade itself.

`evaluation/` holds the human annotation schemas. There is no packet builder and no
annotation in this repository; human labels come from people.

## What the pipeline does beyond reading the README

- **The paper.** A repository's arXiv tag is often the base model's, sometimes another
  paper entirely. Every candidate the repo offers goes through a title gate that decides
  whether the paper introduces this checkpoint, references its family, or is unrelated,
  and an unrelated paper is dropped unread. When neither the repo nor its declared base
  points at a paper, OpenAlex and Semantic Scholar are searched, and a searched title has
  to pass a stricter rule still: the family name must be the title's own subject and the
  generation it states must be this checkpoint's, so "Code Llama", "LLaMA-Adapter",
  "Llama 2" and a paper about attacks on Llama 3 are all refused for a Llama 3.2
  checkpoint.
- **The tables.** Benchmark scores are read deterministically from the cell that is the
  target's own, in both table orientations, with the metric and the evaluation setting
  taken from the table itself and never guessed. A column label is matched by token role,
  so the developer's own shorthand ("Gemma PT 9B", "Gemma 2 IT 9B") is read, while a
  sibling's column, a quantized re-upload's column and the other stage's table are not.
- **A second opinion on the prose.** With `MODELCARDS_FACTCHECK=1` the finished card runs
  through FactReasoner, which decomposes each prose value into atomic claims and scores
  them against the frozen sources with an NLI model. A contradiction flags the field in
  `provenance_and_quality.flagged_fields`; it does not silently remove it, because the
  entailment model is referent-blind and two of its first contradictions were false.

## Status

This is a working generator and a set of candidates, not a released corpus. The judge
and the screen are instruments here, not results: no judge output is in this repository,
and the human annotation round has not happened yet. Human labels are what would turn
candidates into a corpus.
