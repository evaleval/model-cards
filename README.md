# Model Cards

Model Cards is a research workflow for generating evaluation-focused documentation
for one exact model revision. This repository contains real generated card
projections, the project overview, and the source-free evidence and policy core. The
collector and model-assisted composer used for the current candidates are not in this
repository.

The workflow combines pinned official sources, binds proposed values to the model,
checkpoint, evaluation setting, and supporting evidence, and keeps conflicts or
uncertain assignments visible instead of turning them into facts.

The unit of analysis is `model_id@revision`. A result reported for a base model,
sibling checkpoint, family, or comparison model does not become a fact about the
target checkpoint. Unsupported fields remain `Not specified`.

![Model Card generation pipeline](docs/figures/model-card-pipeline.png)

*The system fixes one model revision, freezes the available source bundle, and binds
candidate claims to their source and target relation. Accepted bindings populate 33
documentation fields; five provenance and quality fields are derived. Withheld
evidence stays in the full artifact's ledger. Human release review is not part of the
completed pipeline yet. The figure is also available as
[vector PDF](docs/figures/model-card-pipeline.pdf) and
[LaTeX source](docs/figures/model-card-pipeline.tex).*

## Real generated examples

The files below were projected directly from artifacts produced by the working
local research pipeline. They are not hand-written examples. The full artifacts,
source bundles, prompts, audit records, and local execution metadata are not in this
repository.

### Current model-assisted candidates

| Example | What it shows | Coverage | Status |
| --- | --- | ---: | --- |
| [OLMo-2-1124-7B](examples/generated/olmo-2-1124-7b/card.md) ([JSON](examples/generated/olmo-2-1124-7b/card.json)) | Nine publisher-reported score rows and six withheld bindings | 66.7% | No blocking support or scope finding among projected claims; omission checks and human review remain open |
| [OLMo-2-1124-7B-Instruct](examples/audit-cases/olmo-2-1124-7b-instruct/card.md) ([JSON](examples/audit-cases/olmo-2-1124-7b-instruct/card.json)) | Eight score rows and eight withheld bindings | 63.6% | Audit blocked promotion because two source-present facts were omitted |

### Historical feasibility outputs

The earlier six-target offline feasibility run produced sparse engineering artifacts.
Two representative outputs are included here and kept out of the current-candidate
table.

- [Whisper Large V3 MLX](examples/generated/whisper-large-v3-mlx/card.md)
  ([JSON](examples/generated/whisper-large-v3-mlx/card.json)), 24.2% coverage and no
  human review.
- [Docling Layout Heron](examples/generated/docling-layout-heron/card.md)
  ([JSON](examples/generated/docling-layout-heron/card.json)), 24.2% coverage, two
  wrong-scope candidates withheld, and no human review.

Every example directory contains a readable `card.md`, the unchanged generated
`card.json` projection, and a small `public-export.json` record. The record binds the
projection to its original artifact by SHA-256 without publishing the artifact or its
sources. The examples preserve the generator's value shapes and are not rewritten to
fit the narrower public binding core. Audit labels are export annotations; the audit
records remain local. Synthetic data is used only in `tests/fixtures`.

## Pipeline

1. **Exact model revision.** Generation starts from one Hugging Face model ID and a
   resolved 40-character revision. The target identity is fixed before any field is
   filled.

2. **Multi-source collection.** Available official sources are pinned and frozen
   locally. The source bundle is an input to generation and audit, not a public
   repository artifact.

3. **Scoped-evidence binding.** Candidate values carry a source span or structured
   pointer, a claimed entity, and a relation to the target. Deterministic span and
   structure checks plus a field-level evidence verifier test support and assignment.
   A verified quote about the wrong checkpoint is still the wrong evidence.

4. **Evidence-limited composition.** Accepted bindings populate 33 documentation
   fields. Conflicts, ambiguous assignments, and unsupported values stay withheld or
   `Not specified`. Five provenance and quality fields are then derived. The result is
   a generated card plus a field-level binding ledger.

Human review and release approval follow generation. No example in this repository has
completed that step.

## Sources

Four first-party and project-owned source classes are currently admitted.

| Source | Current role | Constraint |
| --- | --- | --- |
| Hugging Face metadata, model card, config, and safetensors metadata | Identity, architecture, parameters, precision, links | Pinned to the exact model revision |
| Developer paper or technical report | Training and evaluation details | The report must be verified as relevant to the target or an explicit related model |
| Developer GitHub documentation | Code and supplementary model documentation | Pinned to a developer-owned commit |
| EvalEval evaluation record | Exact-ID links and record discovery | Not authority for checkpoint-specific scores |

The next useful additions are official system and safety cards, official provider
documentation and changelogs for API models, original independent evaluation reports,
evaluation configurations and result artifacts, and official dataset cards. Evaluation
sources must identify the exact target and protocol. Dataset sources must identify the
dataset and version actually used.

Third-party summaries, mirrors, and unversioned leaderboards may help discovery but are
not target authority. Base-model prose is not inherited unless the source states the
relation explicitly.

## Current state

Status on 2026-09-01 is two model-assisted candidates and six earlier deterministic
feasibility outputs. Planned targets beyond the OLMo pair have not been generated.

- OLMo Base currently has the highest field coverage among the model-assisted
  candidates. It fills 22 of 33 documentation fields and contains nine score rows. Its
  automated audit found no blocking support or scope issue among projected claims, but
  omission checks, human review, and public release checks remain open.
- OLMo Instruct fills 21 of 33 substantive fields and contains eight score rows. Its
  audit blocked promotion because source-present facts were lost during composition.
- A separate earlier feasibility run produced six sparse deterministic cards. Those
  artifacts test identity, scoping, abstention, and export behavior; they do not
  establish final card quality.

The complete collector and model-assisted composer are not in this repository. The
public code validates supplied bindings, applies scope policy, projects cards, records
review events, and renders outputs. It does not run the full pipeline end to end.

## What the project is for

- **Inspect and correct one card in the full workflow.** A reviewer with the retained
  artifact can trace a field to its source and target relation, then accept, reassign,
  or withhold the binding.
- **Compare related checkpoints safely.** A Base/Instruct pair can be compared without
  silently transferring training quantities or evaluation rows between checkpoints.
- **Study documentation gaps.** A collection of cards can show which training,
  evaluation, safety, or provenance fields are consistently undocumented.

The checked-in card projections support comparison and gap inspection. They do not
contain the private field-level evidence ledger.

## Repository map

- `examples/generated/` contains the three public generated examples.
- `examples/audit-cases/` contains real outputs that failed a later audit.
- `docs/figures/` contains the LaTeX pipeline figure, PDF, and PNG.
- `model_cards/` contains the source-free evidence and policy core.
- `tests/fixtures/` contains synthetic data used only for deterministic tests.
- [docs/reference-core.md](docs/reference-core.md) documents the public core and CLI.

## Run the public core

Python 3.9 or newer is sufficient. The package has no runtime dependencies.

```sh
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
```

The test suite runs offline. For the scientific contract, review semantics, and CLI
examples, see [the reference-core documentation](docs/reference-core.md).

## Next work

The immediate sequence is to repair and re-audit the OLMo Instruct card, generate the
next source-ready targets, add named human review, and move a smaller end-to-end
generator into this repository.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
