# Model Cards

`modelcards` generates one evidence-bound Model Card for one exact Hugging Face
model revision. It freezes bounded source inputs, extracts only replayable claims,
composes from claims that pass field-scoped gates, and retains the evidence and
checks in a local audit record. The public result is the agreed seven-section card
as JSON; repository publication also creates a deterministic Markdown companion
from that exact JSON.

The public contract is deliberately closed. It has exactly these 33 allowed fields:

| Section | Fields |
| --- | --- |
| `identity` | `model_id`, `name`, `developed_by`, `model_type`, `license`, `release_date`, `version`, `summary` |
| `lineage` | `base_models`, `model_family`, `derivatives` |
| `specifications` | `architecture_type`, `num_parameters`, `context_length`, `precision`, `model_size`, `input_output` |
| `training_context` | `training_data`, `training_data_size`, `data_cutoff`, `adaptations` |
| `access_and_adoption` | `access_type`, `downloads`, `likes` |
| `evaluation` | `results_summary`, `benchmark_scores`, `human_evals`, `safety_evals` |
| `links` | `model_card`, `system_card`, `tech_report`, `code_repository`, `citation` |

All seven section objects are present. Generated projections omit an agreed field
when the retained sources do not support a value; they do not invent one. Evidence,
provenance, risk, environmental information, validation results, lifecycle state,
and other operational metadata remain in local audit artifacts and are never public
card fields.

Public prose is concise derived content, not an evidence-quotation channel. The
frozen-source enrichment stage rejects a candidate if any guarded prose field copies
12 consecutive normalized words from a retained source. Exact source spans remain
only in the ignored local run artifacts; links, identifiers, citations, and structured
score rows retain their publication-specific forms.

Evidence about a base model, sibling checkpoint, family, or comparison model cannot
silently populate an exact-target field. Local automated lifecycle state uses only
`generated_unreviewed` or `generated_validated`; neither means that a person reviewed,
approved, or released the card, and neither value appears in the public card.

![Model Card generation pipeline](assets/model-card-pipeline.png)

The vector [PDF](assets/model-card-pipeline.pdf) and
[LaTeX source](assets/model-card-pipeline.tex) for the figure are included.

## Install

The core package supports Python 3.9 or newer.

```sh
python3 -m pip install -e .
modelcards --help
```

The optional AI Atlas Nexus integration is pinned to `ai-atlas-nexus==1.2.4`.
It requires Python 3.11 or newer and the `risk` extra:

```sh
python3 -m pip install -e '.[risk]'
```

Without that exact dependency, the taxonomy stage reports itself as unavailable;
the core package does not substitute another taxonomy release.

## Generate one card

Pass a Hugging Face model ID, optionally followed by a branch, tag, ref, or exact
commit. Collection resolves it once to a 40-character commit and binds all later
artifacts to that exact target.

```sh
modelcards generate MODEL[@REVISION] --output RUN_DIR
```

The normal networked command performs two bounded collection steps:

1. It freezes selected Hugging Face metadata and files for the resolved revision.
2. It discovers links declared in that frozen material and attempts bounded HTTPS
   collection from the allowlisted publication, code, and declared publisher hosts.

Official-source discovery is declaration-driven. It is not a general web or
scholarly search. Unsafe URLs, redirects, media types, ownership mismatches, size
limits, and unavailable responses are recorded rather than treated as evidence.

Generation without `--provider` does not make paid calls. If the FactReasoner
checker required for the composed claims is unavailable, that gate is recorded as
`unavailable` and the card remains `generated_unreviewed`; deterministic checks do
not promote it past that missing gate.

### Exact offline replay

A verified frozen Hugging Face bundle can be replayed without network access. Add
its ancestry-bound official bundle to replay the combined source state; omit it for
an explicitly Hugging-Face-only replay.

```sh
modelcards generate MODEL@EXACT_COMMIT \
  --offline-bundle HF_BUNDLE \
  --offline-official-bundle OFFICIAL_BUNDLE \
  --output REPLAY_RUN
```

The command rejects target, revision, bundle, source-state, and resume drift. A run
directory admitted in provider-free or provider-assisted mode cannot be resumed in
the other mode.

### Explicit provider-assisted mode

Provider-assisted extraction and semantic checking are opt-in:

```sh
OPENROUTER_API_KEY=... modelcards generate MODEL[@REVISION] \
  --provider Together \
  --output RUN_DIR
```

This mode pins OpenRouter to exactly `deepseek/deepseek-v4-flash-0731` on
`Together`. The CLI rejects every other provider, the runtime verifies the live
endpoint identity and structured-output capabilities before each send, and automatic
fallback is disabled. The runtime has a global run cap of 300 paid calls and USD 25,
permits at most two
retries after an explicit HTTP 429 or 5xx response, and stops on an uncertain send
instead of risking a duplicate. The API key, prompts, source text, and raw response
envelopes are not written to public cards or audit summaries. Private normalized
decision sidecars can contain evidence quotes and proposed values and must stay in the
run directory.

A missing key, invalid route, spend cap, uncertain send, ledger conflict, extraction
failure, or stale resume aborts the run. A safely recorded malformed, truncated, or
retry-exhausted response during an individual claim or FactReasoner check becomes an
explicit `unavailable` decision instead; it cannot count as validation and the card
remains unreviewed. Provider mode is not exposed by `modelcards batch`; run
provider-assisted targets individually so one run owns one global ledger.

## Run artifacts

Each successful run contains a content-addressed, replayable chain. The principal
files are:

| File | Purpose |
| --- | --- |
| `source-bundle/manifest.json` | Exact-revision Hugging Face source inventory |
| `official-discovery.json` | Declared official-source candidates from a networked run |
| `official-source-bundle/manifest.json` | Ancestry-bound official collection inventory, when used |
| `source-state.json`, `source-catalog.json` | Immutable combined source identity and extractable document catalog |
| `extraction.json`, `claim-gates.json` | Candidate claims and the four-part support gate |
| `composition-original.json`, `factreasoner-original.json`, `omissions-original.json` | Pre-repair audit projection and checks |
| `repairs.json`, `composition.json`, `factreasoner-content.json`, `omissions.json` | Field-targeted repair/withholding and post-repair audit-content checks |
| `risk-mapping.json` | Local publisher-use and taxonomy-risk audit; never a public-card section |
| `factreasoner-publication-original.json`, `publication-validation.json` | Enriched 33-field pre-withhold check and deletion-only public-field decisions |
| `factreasoner.json`, `privacy.json` | Final public-card FactReasoner record and privacy scan |
| `card-artifact.json`, `public-card.json` | Full typed local audit artifact and exact seven-section public projection |
| `pipeline-result.json`, `run-manifest.json`, `journal.jsonl` | Run identity, artifact hashes, and append-only stage history |
| `audit-view.json`, `usage-summary.json` | Body-free audit and cost/latency summaries |

Provider-assisted runs additionally retain `provider-orchestration.json`, a single
`usage.jsonl` accounting ledger, normalized decision sidecars, and
`provider-result.json` in the run directory. These are run records, not public-card
content.

## Inspect, validate, review, and repair records

```sh
modelcards validate RUN_DIR/public-card.json
modelcards inspect RUN_DIR/card-artifact.json
modelcards inspect RUN_DIR/card-artifact.json --field training.training_data
modelcards export RUN_DIR/card-artifact.json \
  --source-bundle FROZEN/source-bundle \
  --output exported-card.json
```

`export` does not reconstruct a card from the legacy audit projection. It requires
the pipeline's publication snapshot and replays it against the supplied frozen
bundle; add `--official-bundle` when the artifact binds combined official sources.

Generation first performs targeted repair and withholding on audit-contract fields
and records the result in `repairs.json`. After frozen-source publication enrichment,
`publication-validation.json` separately records deletion-only withholding of any
public field that receives a terminal FactReasoner repair/withhold action. Neither
stage silently rewrites a failed value. The `repair` command validates and summarizes
one extracted machine `FieldRepairRecord`; it does not turn that record into human
review:

```sh
modelcards repair FIELD_REPAIR_RECORD.json
```

The `review` command appends one explicit decision to a new artifact and leaves its
input untouched:

```sh
modelcards review INPUT_ARTIFACT.json BINDING_ID \
  --action withhold \
  --reason needs_check \
  --output REVIEWED_ARTIFACT.json
```

`accept`, `withhold`, and evidence-preserving `reassign` actions are supported.
Appending a decision does not by itself claim that an entire card was human-reviewed
or released.

## Batch generation and aggregate reports

`targets.json` is a non-empty JSON array of unique `MODEL[@REVISION]` strings.

```sh
modelcards batch targets.json --output BATCH_A
modelcards batch targets.json --output BATCH_B
modelcards report BATCH_A \
  --replay-batch BATCH_B \
  --output quality-report.json
```

Offline batch replay accepts repeatable target-specific mappings:

```sh
modelcards batch targets.json --output BATCH_A \
  --offline-bundle 'MODEL@COMMIT=HF_BUNDLE' \
  --offline-official-bundle 'MODEL@COMMIT=OFFICIAL_BUNDLE'
```

The quality report verifies each typed artifact before aggregating claim outcomes,
withholding, omissions, risk-stage status, usage, cost/latency, and paired replay
stability. It also replays the frozen-source publication enrichment and provenance,
replays deletion-only publication validation, and verifies that the final
FactReasoner record accounts for all 33 public fields. It contains hashes and closed
counters, not source bodies or provider payloads. These are engineering validation
measures, not human quality judgments or evidence that this generator is better than
another system.

## Published cards

The repository publication path writes each card into `cards/` as a pair:

- `NAME.json` is the canonical seven-section public card.
- `NAME.md` is a deterministic, human-readable rendering of that JSON. It links to
  the paired JSON and records the SHA-256 of its exact bytes.

The checked-in cohort contains twelve source-backed cards:

| Family | Base / pretrained | Instruction / post-trained |
| --- | --- | --- |
| OLMo 2 | [OLMo-2-1124-7B](cards/olmo-2-1124-7b.md) | [OLMo-2-1124-7B-Instruct](cards/olmo-2-1124-7b-instruct.md) |
| Gemma 3 | [gemma-3-4b-pt](cards/gemma-3-4b-pt.md) | [gemma-3-4b-it](cards/gemma-3-4b-it.md) |
| Mistral | [Mistral-7B-v0.3](cards/mistral-7b-v0.3.md) | [Mistral-7B-Instruct-v0.3](cards/mistral-7b-instruct-v0.3.md) |
| DeepSeek V3 | [DeepSeek-V3-Base](cards/deepseek-v3-base.md) | [DeepSeek-V3](cards/deepseek-v3.md) |
| Qwen 3 | [Qwen3-8B-Base](cards/qwen3-8b-base.md) | [Qwen3-8B](cards/qwen3-8b.md) |
| Llama 3.1 | [Llama-3.1-8B](cards/llama-3.1-8b.md) | [Llama-3.1-8B-Instruct](cards/llama-3.1-8b-instruct.md) |

The regenerated cohort populates 287 of 396 possible fields: 19–28 of 33 per card,
23.92 on average, with 80 structured benchmark-score rows. The publishing command's
default substantive-card floor is 15 populated fields; honest source-limited
missingness is still omitted rather than filled with placeholders.

The Markdown is not a second factual source and is not hand-edited. The publishing
script requires each pipeline card's integrity-checked `card-artifact.json` sibling
and its frozen source bundle. It replays the publication snapshot, checks it against
all active source text, validates the JSON against the packaged public schema and
privacy boundary, copies its bytes, derives the Markdown only from the validated
card, and audits the pair before writing either destination. Repeat
`--source-bundle` in the same order as the mappings:

```sh
PYTHONPATH=src python3 scripts/publish_examples.py --force \
  --source-bundle FROZEN_A/source-bundle \
  --source-bundle FROZEN_B/source-bundle \
  RUN_A/public-card.json=cards/model-a.json \
  RUN_B/public-card.json=cards/model-b.json
```

The complete checked-in cohort can be regenerated without network or provider calls
from verified frozen bundles. This command runs the pipeline, immediately verifies
each replay, enforces a substantive-card coverage floor, and publishes the full batch
only after every JSON/Markdown pair passes:

```sh
PYTHONPATH=src python3 scripts/regenerate_frozen_examples.py \
  --pilot-root FROZEN_TARGETS \
  --run-output PRIVATE_RUN \
  --repo-root . \
  --force
```

## Scope and current limitations

- Official discovery follows declarations in the frozen Hugging Face material; it
  does not independently search the literature.
- Bounded official collection can freeze supported HTTPS responses, but the current
  official-document bridge does not extract text from PDFs.
- Provider-assisted batch execution is intentionally unavailable.
- Missing provider credentials or an unavailable FactReasoner backend are reported;
  they are not replaced with invented validation results.
- The example cards are automated candidates. This repository reports no human study,
  human annotation result, released card, independent-model comparison result, or
  demonstrated quality improvement over another generator.
- Risk mappings, environmental claims, evidence/provenance, validation results, and
  lifecycle state are local audit material. Their absence from the public schema is
  a publication-boundary decision, not evidence that a model has no risks or
  environmental effects.

The [JSON Schema](schema/model-card.schema.json) is the public contract. See
[ARCHITECTURE.md](ARCHITECTURE.md) for the typed stages, replay invariants, provider
boundary, and publication boundary.

## Test

```sh
PYTHONPATH=src python3 -m pytest -q
```

The test suite is deterministic and uses fixtures or injected transports; paid
provider calls are not part of the default tests.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
