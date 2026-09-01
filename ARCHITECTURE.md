# Architecture

The system generates one evidence-bound Model Card for one exact model revision. It
freezes the source material first, keeps every proposed value in a binding ledger, and
projects the public JSON card from accepted bindings. The binding ledger is the primary
record. The public card is its derived projection.

```text
model_id@resolved_revision
        |
        v
frozen local source bundle --> model and referent frame
        |                              |
        +------------------------------+
                       |
                       v
        structured extraction + quoted candidates
                       |
                       v
          evidence and assignment bindings
                       |
                       v
       composition + risk identification + audits
                       |
                       v
             append-only review and repair
                       |
                       v
             source-clean public card.json
```

## System invariants

- The target is a repository model ID paired with a resolved 40-character revision.
- Each source-derived filled field traces to a verified source span or structured
  pointer.
- Each binding names the entity described by the evidence and its relation to the
  target. Exact wording alone cannot establish the correct assignment.
- A base model, model family, sibling checkpoint, derivative, or comparison model does
  not populate an exact-target field unless the field policy permits that relation.
- Unsupported values remain `Not specified`. Fields that do not apply use
  `Not applicable`.
- Conflicting accepted values block projection for that field. Projection never picks
  the last value silently.
- Public cards are JSON. Source bodies, binding ledgers, model traces, and review logs
  remain in local source bundles and retained artifacts.

## Pipeline and data model

### 1. Fix the target and freeze the sources

The run resolves the requested model to `model_id@revision` before extraction. Source
adapters then collect the admissible publisher and evaluation material for that exact
target. Each source record stores a logical source ID, authority role, source revision,
target scope, and SHA-256 digest. The frozen bytes stay local so every later check can
replay the same input.

The source bundle is immutable for a run. A changed README, report, configuration, or
evaluation record starts a new source revision instead of changing an existing run in
place.

### 2. Build the model and referent frame

The model frame identifies the target, declared base models, family aliases, siblings,
derivatives, comparison models, benchmarks, and metrics. Extraction and validation use
this frame to resolve what each statement describes. It also prevents a family-wide
training statement or a comparison score from being assigned to the target checkpoint.

### 3. Extract candidates through two channels

Deterministic extractors read structured metadata, configuration, weight metadata,
tables, and evaluation records. Model-assisted extractors propose values from verbatim
source spans. Bounded gap retrieval can inspect a missing section when the initial pass
finds no candidate.

Both channels emit candidates into the same binding interface. A candidate contains a
schema field path, proposed value, claimed entity, target relation, source evidence,
and any benchmark or protocol scope needed to interpret the value.

### 4. Bind evidence to fields

Each binding joins a proposed value to its schema field, claimed entity, target
relation, and evaluation scope. Evidence contains either exact quote coordinates or a
structured pointer whose fragment can be replayed. Entity-Attribution Verification
(EAV) audits whether selected passages actually describe the claimed entity and
support the proposed field. It can record a referent correction before deterministic
relation gates run.

The policy gate checks the evidence, field, relation, referent, row anchor, and source
scope together. It assigns a stable disposition and reason code. Accepted bindings may
enter the card. Withheld and rejected bindings remain in the ledger for inspection.

### 5. Compose the card

Composition reads accepted bindings only. It fills the versioned JSON schema, retains
the two absence sentinels, derives provenance and coverage fields, and withholds fields
with unresolved conflicts. Narrative fields may be composed from accepted evidence.
Numeric benchmark rows come from deterministic table extraction and reconciliation.
The model-assisted composer cannot create or alter scores.

The internal `CardArtifact` contains the exact target, immutable generated bindings,
append-only review events, and the current card projection. The public card contains
the projection only.

### 6. Identify model-use risks

Source-reported intended uses, limitations, biases, risks, and mitigations enter the
normal evidence-binding path. They must satisfy the same referent and source checks as
other card fields.

The pipeline also runs model-assisted risk identification through AI Atlas Nexus
against a pinned IBM AI Risk Atlas release. Each internal candidate mapping records
the taxonomy risk ID, taxonomy name and version, use context, applicability rationale,
input field references, Nexus version, inference model, configuration digest, and
review status. The `use_and_risk.identified_risks` entries label their
`identification_origin`, so a taxonomy-identified risk cannot be mistaken for a
publisher statement. A mapping does not receive a severity or confidence value unless
a separate assessment supports it.

### 7. Validate the complete artifact

Validation runs after composition because a supported candidate can still become an
unsupported final claim, and a well-supported set of fields can still omit a fact that
the frozen sources contain.

| Layer | Operates on | Question answered | Failure action |
| --- | --- | --- | --- |
| Source replay | Source manifest and evidence coordinates | Do the hashes, spans, pointers, and derivations reproduce against the frozen bundle? | Reject the affected binding |
| Schema checks | Public projection | Are sections, field types, enums, absence values, and required metadata valid? | Block release |
| Entity-Attribution Verification | Candidate bindings | Does this value describe this entity, field, row, and protocol? | Withhold or reassign |
| Numeric reconciliation | Score rows and quantitative fields | Do value, unit, metric, setting, split, and source row agree? | Withhold the row |
| Final-claim audit | Composed card claims and their own citations | Does the final wording follow from the evidence attached to that field? | Repair or withhold the field |
| FactReasoner | Atomic claims and the frozen source bundle | What support or contradiction does retrieval find for each claim? | Flag unsupported claims for repair or review |
| Conflict checks | Accepted bindings | Do accepted values disagree for the same scoped field? | Leave the field unfilled |
| Omission audit | Frozen sources and projected card | Which source-present facts were lost during extraction or composition? | Add candidates and rerun the affected gates |
| Risk-mapping gate | Candidate risk mappings | Does the risk ID exist in the pinned taxonomy, and do the use context, rationale, field references, and review state support the mapping? | Reject or retain as unreviewed |

These layers have separate jobs. Entity-Attribution Verification establishes
assignment before composition. The final-claim audit checks the wording produced after
composition. FactReasoner decomposes narrative output into atomic claims, retrieves
matching passages from the frozen bundle, and records support and contradiction
probabilities. It does not decide whether a taxonomy risk applies to a use case. The
omission audit searches for source-present content that no projected claim covers.

### 8. Repair, review, and release

Validators emit field-level findings with stable codes. A repair pass reads only the
affected fields and evidence, adds a new candidate or review event, and reruns the
relevant gates. Supported fields remain unchanged. This makes repair bounded and keeps
the generation history inspectable.

Human review is append-only. A reviewer can accept, withhold, or reassign a binding and
must record a reason. Release approval records the reviewer identity and the artifact
version reviewed. High-risk use mappings can require a second signoff. Export runs only
after the release gates pass.

## Local and public artifacts

| Artifact | Contents | Location |
| --- | --- | --- |
| Frozen source bundle | Exact source bytes, revisions, hashes, and collection metadata | Local only |
| Full `CardArtifact` | Target, generated card, binding ledger, evidence coordinates, validation findings, and review history | Local only |
| Public Model Card | Source-clean JSON projection with public provenance metadata | Repository `cards/` directory |

The repository export excludes source bodies, local filesystem paths, credentials,
working notes, prompts and responses, provider traces, and private audit records. The
v6 contract adds a field-to-source index with logical source IDs, public source URIs,
revisions, digests, typed locators, claimed entities, and target relations. It never
contains the source bundle, evidence text, or full binding ledger.

`public_export.py` enforces the current v5 boundary and writes one JSON file without
Markdown or audit sidecars. A v6 release additionally requires validation of its
fail-closed metadata shape, typed public locators, cross-references, and pinned
taxonomy records, followed by a recursive privacy scan over the complete projection.

## Package modules

The `src/model_cards` package holds the source-free policy and artifact core. The
modules form the stable interface used by collection, composition, audit, and release
orchestration.

| Module | Responsibility |
| --- | --- |
| `models.py` | Typed targets, sources, evidence, bindings, dispositions, and review events |
| `quote.py` | Text normalization and exact substring matching for quoted evidence |
| `bindings.py` | Quote and structured binding construction, stable IDs, JSON Pointer replay, and source verification |
| `policy.py` | Fail-closed field, source-role, revision, and target-relation rules |
| `artifact.py` | Immutable artifacts, review folding, conflict handling, and deterministic card projection |
| `schema.py` | Versioned field vocabulary, value shapes, list indexing, and absence semantics |
| `review.py` | Append-only accept, withhold, and reassign operations |
| `render.py` | Deterministic internal JSON and static HTML inspection views |
| `public_export.py` | JSON-only public export plus privacy and integrity checks |
| `cli.py` | Offline build, inspect, render, and review commands |

The full collector, model-assisted composer, validation orchestration, risk mapping,
and release workflow integrate through these interfaces. Checked-in cards remain
unchanged generation outputs until the complete path regenerates them. Schema
revisions are explicit for the same reason. Existing v5 cards are not edited after the
fact to imitate fields introduced by a later schema.

## Developer commands

Python 3.9 or newer is supported. The core runs offline and has no runtime dependency
on a model provider.

```sh
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
python3 -m model_cards --help
```

The synthetic fixture exercises exact-target scope, withheld evidence, projection,
inspection, and review without using research sources.

```sh
python3 -m model_cards build tests/fixtures/synthetic-input.json \
  --json build/synthetic-artifact.json \
  --html build/synthetic-artifact.html

python3 -m model_cards inspect build/synthetic-artifact.json
python3 -m model_cards inspect build/synthetic-artifact.json \
  --field training_context.training_data_size
```

Review creates a new artifact and leaves the input untouched.

```sh
python3 -m model_cards review INPUT.json BINDING_ID \
  --action withhold \
  --reason needs_check \
  --output REVIEWED.json
```

Public export accepts a retained full artifact and writes one source-clean card.

```sh
python3 -m model_cards.public_export LOCAL_ARTIFACT.json cards/model-name.json
```

Run directly from the source tree when an editable install is not available.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m model_cards --help
```
