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

The four claim gates apply to extracted candidates. A separate, closed and versioned
publication ruleset computes additional fields from exact frozen metadata, structured
pointers, and scoped README rows; every such field retains local rule-and-source
provenance and must replay byte-for-byte. Those registered derivations are not
semantic gate decisions. Their final narrative claims are checked by FactReasoner
when that backend is available; an unavailable result remains `generated_unreviewed`
and does not establish support. Comparative quality claims additionally require
blinded human evaluation; a ruleset test alone is not a human correctness label.

Evidence about a base model, sibling checkpoint, family, or comparison model cannot
silently populate an exact-target field. Local automated lifecycle state uses only
`generated_unreviewed` or `generated_validated`; neither means that a person reviewed,
approved, or released the card, and neither value appears in the public card.

![Model Card generation pipeline](assets/model-card-pipeline.png)

The vector [PDF](assets/model-card-pipeline.pdf) and
[LaTeX source](assets/model-card-pipeline.tex) for the figure are included.

## Install

The core package supports Python 3.10 or newer.

```sh
python3 -m pip install -e .
modelcards --help
```

The core install pins `pypdf==6.4.0`. Official PDF sources are interpreted only
from their frozen response bytes in a child process with byte, page, text,
wall-time, CPU-time, file-output, and descriptor limits; the parser does not fetch
resources or perform OCR. The portable isolation profile does not claim a hard
address-space ceiling.

The optional AI Atlas Nexus integration is pinned to `ai-atlas-nexus==1.2.4`.
It requires Python 3.11 or newer and the `risk` extra:

```sh
python3 -m pip install -e '.[risk]'
```

Without that exact dependency, the taxonomy stage reports itself as unavailable;
the core package does not substitute another taxonomy release.

The optional IBM FactReasoner integration requires Python 3.11 or newer and is
pinned to the official IBM repository at commit
`41eb0c21baa2a8bba4030cf0d619aa00fae2ed84`:

```sh
python3 -m pip install -e '.[factreasoner]'
```

The exact OpenRouter structured checker evaluates deterministic batches of at most
64 FactReasoner requests. It runs a complete primary wave, sends only neutral
outcomes through the bounded fallback wave, and caches exact request hashes across
repeated pipeline passes. Each atom still retains its own categorical NLI relation
and cited chunk IDs. Because that endpoint does not promise token log probabilities,
the adapter declares a fixed `0.9` relation factor, runs upstream's FR1 Markov graph,
and normalizes the atom marginal with pgmpy exact variable elimination. It does not
require or execute Merlin. If the exact pinned upstream package or pgmpy cannot be
verified and imported, FactReasoner is recorded as unavailable and no FactReasoner
provider call is made.

Nexus receives only evidence-bound Model Use Contexts. Each context must start
from an accepted exact-target intended-use or out-of-scope-use claim. Accepted
model properties, limitations, and known biases may qualify that core statement;
their field paths, candidate IDs, and frozen source IDs remain attached to the
context. Exact-target properties are global qualifiers. Limitation and bias
statements are source-local: with multiple core uses they attach only when source
overlap identifies exactly one core, otherwise they are withheld from the Nexus
prompt rather than copied across every use. Qualifiers alone never trigger risk
inference, and an empty or withheld
applicability decision is not replaced with generic top-ranked risks. The private
`risk-mapping.json` retains every typed Nexus candidate and applicability decision,
not just their hashes. Quality replay loads the exact Nexus 1.2.4 catalog, rebuilds
the effective contexts and deterministic public-risk projection without provider
calls, and rejects catalog, candidate, decision, mitigation, or included-value
drift. Provider-assisted runs must use the same catalog hash admitted before any
provider call.

Publisher context has two evidence paths. A conservative deterministic pass accepts
only complete statements with an explicit model subject under closed use, limitation,
bias, risk, or mitigation sections in the pinned root README. Pronouns cannot serve as
the model subject because this local pass has no semantic coreference model. Verified
Closed heading aliases such as `Intended Usage`, `Ethical Considerations & Risks`, and
`Safety, Risks, and Limitations` use the same exact-target gate; model-family,
partial-checkpoint, sibling, and unknown nested scopes remain withheld. Verified
official developer reports remain available to the provider-assisted path, where the
normal semantic binding gates must establish checkpoint scope.
A versioned stage-disambiguation rule may select one exact contiguous clause
from a mixed base/Instruct sentence only when the pinned root Hugging Face README,
official model family, and inline intended-use label all agree; the unsplit mixed
sentence remains rejected. Provider-assisted mode adds a dedicated bounded recovery pass over source
windows with use/risk signals. Both paths preserve exact quotes and coordinates and
run the same four claim gates. Neither path adds risk fields to the public 33-field
card.

Family-scoped publisher prose remains ineligible for public-card projection. It may
be used as private Nexus context only through a separate fail-closed bridge. The
bridge first requires an accepted exact-target `lineage.model_family` claim produced
by a closed, versioned publisher/model-ID/config-`model_type` registry; unknown or
derivative namespaces abstain. A separate structured decision must then accept that
one family statement as applicable to the exact checkpoint. The complete chain and
any unavailable or withheld decisions are retained in
`family-risk-authorizations.json` and replayed before the context can reach Nexus.

A separate deterministic allowlist handles the bundled DeepSeek `LICENSE-MODEL`
only when its Hugging Face URL, source revision, and source target all bind to the
exact checkpoint. It admits only the complete bullets under the uniquely ordered
`Attachment A` / `Use Restrictions` / explicit Model-or-Derivatives applicability
anchors as publisher-reported out-of-scope uses. Missing, duplicate, reordered, or
ambiguous anchors withhold the entire block. This does not relax the generic legal
section exclusion for README or any other document.

## Generate one card

Pass a Hugging Face model ID, optionally followed by a branch, tag, ref, or exact
commit. Collection resolves it once to a 40-character commit and binds all later
artifacts to that exact target.

```sh
modelcards generate MODEL[@REVISION] --output RUN_DIR
```

The normal networked command performs a bounded discovery-and-collection sequence:

1. It freezes selected Hugging Face metadata and files for the resolved revision.
2. It discovers links declared in that frozen material.
3. It makes exactly one credential-free query to each of OpenAlex and Semantic
   Scholar, considers at most five results from each response, and retains at most
   eight normalized arXiv or DOI locators as discovery-only hints.
4. It attempts bounded HTTPS
   collection from the allowlisted publication, code, and declared publisher hosts.

Verified publisher declarations are considered first. The scholarly searches use
fixed public endpoints, a 512,000-byte response cap, no credentials, no redirects,
and no retries. Their response bodies are not retained. Search results are never
fetched or promoted automatically: only normalized `arxiv.org/abs/...` and
`doi.org/...` URLs plus content-free per-service status telemetry are frozen, and the
official bundle records every such URL as non-evidence `discovery_only`. A separate
exact-target authority and relation check is required before a discovered paper can
be collected as evidence. Automatic relation admission requires an unambiguous
resource-to-model declaration in the frozen revision; a model name merely appearing
beside “paper” or “code” is insufficient. Code links must name a full immutable
40-hex commit, so bare repositories and branch URLs remain non-evidence. Unsafe
URLs, redirects, media types, ownership mismatches,
size limits, malformed search responses, and unavailable services are recorded
rather than treated as evidence.

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

For several provider-assisted targets, reuse one aggregate budget journal. The batch
command creates `BATCH/aggregate-budget.jsonl` by default; individual `generate`
commands can share an explicit journal:

```sh
OPENROUTER_API_KEY=... modelcards batch targets.json \
  --provider Together \
  --output BATCH

OPENROUTER_API_KEY=... modelcards generate MODEL[@REVISION] \
  --provider Together \
  --aggregate-budget-journal COHORT/aggregate-budget.jsonl \
  --output RUN_DIR
```

This mode pins OpenRouter to exactly `deepseek/deepseek-v4-flash-0731` on
`Together`. The CLI rejects every other provider, the runtime verifies the live
endpoint identity and structured-output capabilities before each send, and automatic
fallback is disabled. Each target retains its USD 25 and 300-paid-call ledger cap;
provider batches and explicitly shared journals additionally enforce USD 25 or 300
paid calls, whichever comes first, across the cohort. Before each paid request, the
shared journal reserves that send's exact route-bounded cost and one call slot, and
records no prompt, source text, credential, or local path. The runtime permits at most two
retries after an explicit HTTP 429 or 5xx response, and stops on an uncertain send
instead of risking a duplicate. The API key, prompts, source text, and raw response
envelopes are not written to public cards or audit summaries. Private normalized
decision sidecars can contain evidence quotes and proposed values and must stay in the
run directory.

A missing key, invalid route, spend cap, uncertain send, ledger conflict, extraction
failure, or stale resume aborts the run. A safely recorded malformed, truncated, or
retry-exhausted response during an individual claim or FactReasoner check becomes an
explicit `unavailable` decision instead; it cannot count as validation and the card
remains unreviewed. Provider-assisted batch runs use one shared aggregate journal so
the cohort cannot silently multiply the paid-call ceiling across targets.

## Run artifacts

Each successful run contains a content-addressed, replayable chain. The principal
files are:

| File | Purpose |
| --- | --- |
| `source-bundle/manifest.json` | Exact-revision Hugging Face source inventory |
| `official-discovery.json` | Declared official-source candidates from a networked run |
| `scholarly-discovery.json` | Content-free OpenAlex/Semantic Scholar status and discovery-only primary locators |
| `official-source-bundle/manifest.json` | Ancestry-bound official collection inventory, when used |
| `source-state.json`, `source-catalog.json` | Immutable combined source identity and extractable document catalog |
| `extraction.json`, `claim-gates.json` | Candidate claims and the four-part support gate |
| `composition-original.json`, `factreasoner-original.json`, `omissions-original.json` | Pre-repair audit projection and checks |
| `repairs.json`, `composition.json`, `factreasoner-content.json`, `omissions.json` | Field-targeted repair/withholding and post-repair audit-content checks |
| `family-risk-authorizations.json` | Private exact-checkpoint authorization and replay for any family-scoped Nexus context |
| `risk-mapping.json` | Local publisher-use and taxonomy-risk audit; never a public-card section |
| `factreasoner-publication-original.json`, `publication-validation.json` | Enriched 33-field pre-withhold check and deletion-only public-field decisions |
| `factreasoner.json`, `privacy.json` | Final public-card FactReasoner record and privacy scan |
| `card-artifact.json`, `public-card.json` | Full typed local audit artifact and exact seven-section public projection |
| `pipeline-result.json`, `run-manifest.json`, `journal.jsonl` | Run identity, artifact hashes, and append-only stage history |
| `audit-view.json`, `usage-summary.json` | Body-free audit and cost/latency summaries |

Provider-assisted runs additionally retain `provider-orchestration.json`, a single
`usage.jsonl` accounting ledger, normalized decision sidecars, and
`provider-result.json` in the run directory. Whenever the ledger records a provider
attempt, `provider-execution.json` binds the exact pinned route and runtime, target,
source catalog, pipeline/FactReasoner/risk digests, complete usage-ledger digest and
event count, every normalized decision sidecar, and the terminal receipts for both
successful and failed attempts. It contains no prompt, source text, raw response,
credential, or absolute path. These are local run records, not public-card content. A
provider batch also retains its shared aggregate budget journal at the batch root and
a body-free summary bound into batch reporting. Exact sidecar replay is read-only:
after any interrupted reservation has been reconciled, it neither reserves nor
records another paid call.

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
`reassign` additionally requires `--gate-record` and `--source-bundle` (plus
`--official-bundle` when the gate used official evidence). The replacement must be
the exact candidate named by that record, all four gates must pass, and the gate is
replayed against the frozen sources before the event is appended. Any review change
invalidates the inherited card-level validation state. Recompute the immediate
schema, gate, and omission surface with:

```sh
modelcards audit-review REVIEWED_ARTIFACT.json \
  --source-bundle FROZEN/source-bundle \
  --prior-omissions RUN/omissions.json \
  --output REVIEW_AUDIT.json
```

That default audit is provisional: original semantic claim gates and downstream
publication, FactReasoner, risk, and privacy results remain unavailable. A
projection-neutral review retains its replay-bound publication snapshot; a review
that changes the publication projection drops the stale snapshot. To request the
fail-closed sealed verdict, supply the complete current evidence set together:

```sh
modelcards audit-review REVIEWED_ARTIFACT.json \
  --source-bundle FROZEN/source-bundle \
  --prior-omissions RUN/omissions.json \
  --claim-gates RUN/claim-gates.json \
  --publication-factreasoner RERUN/factreasoner-publication-original.json \
  --publication-validation RERUN/publication-validation.json \
  --final-factreasoner RERUN/factreasoner.json \
  --family-risk-authorizations RERUN/family-risk-authorizations.json \
  --risk-mapping RERUN/risk-mapping.json \
  --privacy RERUN/privacy.json \
  --provider-run RERUN \
  --output REVIEW_AUDIT.json
```

The closure inputs are all-or-none. The CLI replays the original and replacement
claim gates, frozen-source publication enrichment, publication validation, and the
privacy/source-overlap scan over the actual final card. The risk lane seals only its
provider-free, no-grounded-context path by replaying the pinned taxonomy. For a
provider-assisted run, `--provider-run` must name the retained run root that produced
the supplied downstream records. The audit verifies its execution manifest, ledger,
exact sidecar inventory, receipts, and downstream hashes; then it re-runs the pinned
IBM FactReasoner graph and Nexus applicability path using replay-only structured
calls. Before/after hashes must prove that neither the ledger nor any decision
sidecar changed. Accepted or withheld family applicability decisions are replayed
from their retained provider receipts before authorized family contexts are merged
back into the Nexus input set. A
non-empty review history and passing schema, omission, FactReasoner, risk, and privacy
checks are all required for `reviewed_candidate_closed`; unavailable or stale inputs
remain explicitly provisional. Appending a decision alone never claims whole-card
review or release. Checker identity or a copied FactReasoner record alone cannot pass
closure; the retained execution chain must replay against the exact current inputs.

## Batch generation and aggregate reports

`targets.json` is a non-empty JSON array of unique `MODEL[@REVISION]` strings.

```sh
modelcards batch targets.json --output BATCH_A
modelcards batch targets.json --output BATCH_B
modelcards report BATCH_A \
  --replay-batch BATCH_B \
  --output quality-report.json
```

Offline batch replay accepts repeatable target-specific mappings. The same mappings
can be combined with `--provider Together` for one bounded provider-assisted cohort:

```sh
modelcards batch targets.json --provider Together --output BATCH_A \
  --offline-bundle 'MODEL@COMMIT=HF_BUNDLE' \
  --offline-official-bundle 'MODEL@COMMIT=OFFICIAL_BUNDLE'
```

The `model-card-quality-report/v6` report verifies each typed artifact before
aggregating claim outcomes,
withholding, omissions, risk-stage status, usage, cost/latency, and paired replay
stability. Provider-assisted reports include validated usage ledgers retained by
failed targets as well as successful ones, and bind admitted targets to the batch's
shared-budget snapshot. For any run whose provider ledger contains events, the report
also requires the result-bound `provider-execution.json` and verifies its complete
ledger, terminal-attempt sequence, and normalized-sidecar inventory. Each successful target exposes a
source-only surface digest over the exact target and immutable source identities,
plus a separate treatment/configuration digest. This permits a paired evaluation to
hold sources fixed while deliberately varying the treatment. The report also replays the frozen-source publication enrichment and provenance,
replays deletion-only publication validation, and verifies that the final
FactReasoner record accounts for all 33 public fields. Competing frozen-source values
are withheld and retained only in `publication-conflicts.json` as field/reason codes,
source pointers, and value hashes; the report exposes only body-free conflict counts
and reason distributions. It contains hashes and closed counters, not source bodies
or provider payloads. These are engineering validation
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

The regenerated cohort populates 298 of 396 possible fields: 21–28 of 33 per card,
24.83 on average, with 153 structured benchmark-score rows. The publishing command's
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

- Official discovery follows declarations in the frozen Hugging Face material and
  records bounded OpenAlex/Semantic Scholar results as discovery-only hints. It does
  not promote a search result to evidence without separate exact-target authority
  and relation proof.
- The official-document bridge extracts text-bearing PDFs, but encrypted,
  malformed, image-only, or over-limit PDFs remain explicit non-evidence records;
  image OCR is intentionally out of scope.
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
boundary, and publication boundary. The offline
[paired failure audit](evaluation/PAIRED_AUDIT.md) compares compatible engineering
counts with the released Auto-BenchmarkCards failure categories while refusing to
turn unmatched schemas or automated checks into a superiority claim.

## Test

```sh
PYTHONPATH=src python3 -m pytest -q
```

The test suite is deterministic and uses fixtures or injected transports; paid
provider calls are not part of the default tests.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE.md](NOTICE.md).
