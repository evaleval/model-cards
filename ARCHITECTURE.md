# Architecture

The system generates one Model Card for one exact model revision. Its source state,
stage inputs, decisions, and outputs are content-addressed so a completed run can be
replayed without changing the evidence beneath the card. The canonical public output
is an exact seven-section JSON object; repository publication derives a deterministic
Markdown companion from those JSON bytes.

```text
MODEL[@REVISION]
        |
        v
exact Hugging Face bundle ---- declared official links
        |                              |
        |                       bounded collection
        +---------------+--------------+
                        v
              immutable source state
                        |
                        v
        structured extraction + optional quotes
                        |
                        v
             four-part claim support gate
                        |
                        v
               evidence-only composition
                        |
                        v
       FactReasoner + omission + conflict checks
                        |
                        v
             targeted repair / withholding
                        |
                        v
             local risk gate + audit artifact
                        |
                        v
                    CardArtifact
                        |
                        v
          33-field allowlisted projection
                        |
                        v
        frozen-source enrichment + provenance
                        |
                        v
        pre-withhold publication FactReasoner
                        |
                        v
        deletion-only field withholding + replay
                        |
                        v
       final FactReasoner + schema + privacy
                        |
                        v
                 public-card.json
                        |
              repository publisher
                        |
             paired JSON + Markdown
```

## Invariants

- The target is a Hugging Face namespace/name plus a resolved 40-character commit.
- Every populated source-derived field is backed by a replayable JSON pointer or
  exact text coordinates in the frozen source state.
- Each candidate names the entity it describes and its relation to the target.
  Similar names do not establish an exact-target relation.
- Claims must pass coordinate integrity, entity scope, field fit, and value support
  before they can enter composition.
- Composition receives accepted candidates, not an unrestricted source corpus.
- Conflicting accepted values and conflicting publication-source values do not use
  last-write-wins behavior; the affected field is withheld and the conflict remains
  visible in a local, content-addressed record.
- The local audit projection uses explicit absence values. The generated public
  projection instead omits an agreed field when the retained sources do not support
  a value; `Not applicable` is reserved for a field shown not to apply.
- Provider-free and provider-assisted runs are different admitted modes and cannot
  overwrite or resume one another.
- Public cards contain only the 33 agreed fields. They never expose evidence or
  provenance records, risk or environmental audit material, validation checks,
  lifecycle state, frozen source bodies, credentials, prompts, raw provider payloads,
  run paths, or journals.

## Public contract and local audit boundary

The required public section objects and their complete field allowlist are:

| Section | Fields |
| --- | --- |
| `identity` | `model_id`, `name`, `developed_by`, `model_type`, `license`, `release_date`, `version`, `summary` |
| `lineage` | `base_models`, `model_family`, `derivatives` |
| `specifications` | `architecture_type`, `num_parameters`, `context_length`, `precision`, `model_size`, `input_output` |
| `training_context` | `training_data`, `training_data_size`, `data_cutoff`, `adaptations` |
| `access_and_adoption` | `access_type`, `downloads`, `likes` |
| `evaluation` | `results_summary`, `benchmark_scores`, `human_evals`, `safety_evals` |
| `links` | `model_card`, `system_card`, `tech_report`, `code_repository`, `citation` |

Together these are exactly 33 fields. Unknown top-level sections and unknown fields
inside a section are rejected. The local audit contract is intentionally richer so
the pipeline can retain source bindings, risk and environmental material, validation,
review events, lifecycle state, and operational provenance without extending the
public schema. `publication.py` is the allowlisted audit-to-public bridge;
`publication_sources.py` adds narrowly derived values from the verified frozen source
catalog and records their provenance only in the local artifact. Guarded public prose
must not reproduce 12 consecutive normalized words from any retained source; a match
fails closed before the publication snapshot is created.

## 1. Exact source collection

`source_bundle.py` parses `MODEL[@REVISION]`, resolves the requested revision once,
and freezes a bounded set of Hugging Face inputs. The manifest records every
collected, missing, gated, or unavailable source and binds all stored bytes to the
exact target and collection limits. Replay rehashes the objects and reconstructs the
manifest identity.

For a normal networked generation, `official_discovery.py` first examines declarations
in the frozen Hub material. It normalizes URLs, restricts them to configured
publication, code, and publisher-owned hosts, and records candidates without treating
discovery as evidence. `scholarly_discovery.py` then makes one credential-free request
to each fixed OpenAlex and Semantic Scholar endpoint. Each response is capped at
512,000 bytes and five results; the combined result is capped at eight deduplicated
arXiv/DOI URLs. Search bodies are discarded, per-service failures remain explicit,
and the normalized URLs enter the official bundle only as `discovery_only` hints.
They are never fetched or made evidence-eligible without a separate exact-target
authority and relation admission. That admission is bound to the frozen target
revision and requires explicit, unambiguous resource-to-model prose; code also needs
a full immutable commit URL. Bare repositories, moving branches, family wording,
and same-line name/resource co-occurrence do not establish the relation.
`official_http.py` performs bounded,
credential-free HTTPS retrieval of publisher-declared candidates with manual redirect
validation. `official_sources.py` checks authority, ownership, relation, media type,
byte bounds, redirect trace, and ancestry before collected official material becomes
evidence-eligible.

`official_documents.py` converts eligible JSON, HTML, Markdown, plain text, and
text-bearing PDFs into typed documents. PDF extraction consumes only the already
frozen bytes, uses the exact pinned parser in a child process with byte, page, text,
wall-time, CPU-time, file-output, and descriptor limits, and records its parser
identity, limits, and output digest in the versioned catalog. Encrypted, malformed,
image-only, over-limit, or unavailable PDFs remain explicit load records; there is
no network access or OCR at this boundary. The portable profile does not claim a
hard address-space ceiling; parser transient allocation remains a documented
residual despite bounded input and retained output.

## 2. One immutable source state

`source_state.py` binds the Hugging Face bundle and, when supplied, the
ancestry-matched official bundle into one immutable identity. `combined_sources.py`
then combines their typed document catalogs. The same catalog digest is used by
extraction, claim gates, composition, FactReasoner, omissions, risk mapping, and run
verification.

An offline Hugging Face bundle alone creates `hf_only` state. Adding a verified
official bundle creates `hf_and_official` state. Resume cannot switch between them.
Provider-assisted orchestration re-verifies the complete source state after provider
decisions and before pipeline composition.

## 3. Extraction and claim support

`extraction.py` creates structured candidates from exact metadata pointers and
materializes optional quoted candidates against saved source coordinates. A
schema-shaped provider response is normalized item by item: valid peers continue,
while semantic-invalid, wrong-source, and duplicate items become index-and-digest-only
rejection records in `extraction.json`; raw rejected content cannot enter pipeline or
public artifacts. The private normalized decision sidecar still contains the
schema-shaped response and is never exported. Wire-schema failures abort the
extraction stage.

A deterministic publisher-context pass separately scans only the pinned root model
README. It admits complete statements with an explicit model subject under closed
use, limitation, bias, risk, or mitigation structure. Pronouns cannot serve as the
model subject. It rejects legal, configuration, fragment, unrecognized nested-heading,
and related-model text because deterministic coreference would be unsafe, and records
exact quote coordinates. Verified official developer reports are handled only by the
provider-assisted path and its semantic binding gates.
One versioned stage-disambiguation rule selects an exact clause from a mixed
base/Instruct intended-use sentence only when the exact Hugging Face root README,
publisher family, target stage, and inline intended-use label agree. The generic
mixed-variant guard remains fail-closed. These private candidates can form Nexus use
contexts but do not add fields to the seven-section public card.

`claim_gate.py` applies the same ordered interface to every candidate:

1. `coordinate_integrity` replays the pointer or quote.
2. `entity_scope` enforces the claimed entity and target relation.
3. `field_fit` checks that the evidence belongs in the proposed contract field.
4. `value_support` checks that the complete proposed value follows from that evidence.

Coordinate integrity and the closed source-relation policy are deterministic.
Structured values also receive deterministic entity, field, and value checks.
Every provider-assisted quote candidate receives three separately bound semantic
decisions for entity scope, field fit, and value support; document-level target
identity cannot substitute for evidence that the quoted section or table is about the
target. A missing, malformed, or failed decision withholds the candidate. A withheld
gate remains in `claim-gates.json` but cannot enter the composition plan.

## 4. Composition, audits, and repair

`composer.py` builds a complete contract-shaped card from projection-eligible claims.
It preserves field-scoped provenance and refuses conflicting values. The pre-repair
projection is saved in `composition-original.json`.

`factreasoner.py` records atomic claim checks against the same source catalog.
Supported, contradicted, neutral, and unavailable outcomes remain distinct. If a
checker is unavailable for claims that require it, the pipeline records that state and
does not count those claims as passed.

`findings.py` compares source-present candidate fields with the composed card and
records omissions and conflicts. `field_repair.py` operates only on affected fields,
replays all proposed evidence, and emits typed repair records. Contradicted or neutral
claims are withheld without an additional semantic submission; unavailable checks
remain visible for later review. The pipeline saves both the original and post-repair
composition, FactReasoner, and omission artifacts. The post-repair audit-content
record is `factreasoner-content.json`; it is distinct from the later checks of the
33-field publication projection.

## 5. Local risk audit

Publisher-reported uses, limitations, biases, risks, and mitigations use the normal
evidence-binding path. They are not interchangeable with taxonomy inferences.

`risk_mapping.py` provides an optional adapter for AI Atlas Nexus 1.2.4 and its pinned
IBM AI Risk Atlas snapshot. The Nexus dependency is loaded only when the exact package
version is installed on Python 3.11 or newer. Taxonomy candidates require accepted use
context, a valid risk identifier, an applicability rationale, supporting field
references, and an applicability decision. They remain in local audit artifacts and
cannot masquerade as publisher statements or confirmed harms. No risk or environmental
field crosses the public-card allowlist. An unavailable dependency or checker produces
an unavailable stage, not a replacement taxonomy result.

## 6. Lifecycle and export

`artifact.py` constructs the typed `CardArtifact` from accepted bindings, validation
checks, optional taxonomy derivations, and append-only review events. The final
lifecycle becomes `generated_validated` only when all of these automated conditions
hold:

- every included claim passes the claim-support gate;
- required FactReasoner checks pass;
- the public projection satisfies the JSON Schema;
- the risk stage passes;
- the privacy scan passes;
- no unresolved conflict or source-present omission remains.

Otherwise the lifecycle is `generated_unreviewed`. These values describe automated
pipeline state, not human review or release approval.

Lifecycle is local audit state and is not a public-card field. `publication.py`
projects the typed artifact through the exact 33-field allowlist, and
`publication_sources.py` adds only registered values replayed from the verified frozen
catalog while keeping provenance local. The enriched pre-withhold card is checked in
`factreasoner-publication-original.json`. `publication_validation.py` accounts for all
33 fields and may only delete a field with a terminal `repair_or_withhold` action; it
never rewrites a value, and immutable `identity.model_id` and `identity.version` cannot
be withheld. It then recomputes registered derivations with the blocked fields and
requires that replay to equal the deletion result exactly. The final public card is
checked again in `factreasoner.json`; no actionable result may survive that pass.

Publication enrichment also treats Hugging Face's base-model declarations as a
consensus relation. When `/cardData/base_model` and `base_model:` tags are both
present, their normalized identifier sets must agree; otherwise
`lineage.base_models` is omitted instead of choosing one metadata surface. Likewise,
two different scores at the same benchmark/metric/setting/split coordinates cause
that benchmark relation to be omitted. Both cases are recorded in the local
`publication-conflicts.json` artifact using source pointers and value hashes; neither
the competing values nor conflict metadata enter the agreed public schema.

`public_export.py` validates the resulting seven-section object against the packaged
Draft 2020-12 publication schema. `public_markdown.py` renders a human-readable
companion only from a validated public JSON object and the SHA-256 of the exact sibling
JSON bytes. `privacy.py` independently audits proposed public files for schema drift,
non-finite or ambiguous JSON, source bodies, credentials, authenticated URLs, machine
paths, provider material, forbidden file types, and unsafe symlinks. The repository
publisher preflights and audits the JSON/Markdown pair before writing either file.

## 7. Provider-assisted orchestration

`orchestration.py` is invoked by `generate --provider Together`, including each
target of a provider-assisted `batch` run. The CLI, adapters, and orchestration
admission reject every other provider; every assisted call uses exactly
`deepseek/deepseek-v4-flash-0731` through OpenRouter. It extracts bounded quote
candidates in one per-document extraction stage, using one general request and at
most one dedicated use/risk request, obtains separately normalized entity-scope,
field-fit, and value-support decisions, supplies a FactReasoner checker, and, when the
pinned risk dependency is available, supplies the Nexus risk interfaces.

`provider.py` and `run_ledger.py` enforce an append-only per-target `usage.jsonl`
ledger, the USD 25 and 300-call target caps, route freshness, structured JSON output,
and at most two retries after explicit 429/5xx responses. Provider-assisted batches
also share an append-only aggregate journal capped at USD 25 or 300 paid calls,
whichever comes first, for the entire cohort. It reserves one route-bounded cost and
call slot before each fresh send and reconciles both commitments against the per-target
ledgers after a crash. A transport outcome that may have sent a
paid request becomes `uncertain` and cannot be sent again. There is no model or route
fallback. Prompts and raw responses are not ledger fields; normalized decisions are
stored separately in the private run directory and addressed by digest. The provider
runtime version is part of each semantic request fingerprint and orchestration
admission, so retry-policy or parsing changes cannot silently reuse an older attempt.

Route, identity, authorization, budget, ledger, and uncertain-send failures remain
fatal. Safely recorded response failures during an individual claim or FactReasoner
check become explicit unavailable outcomes, so the run can retain its audit trail but
cannot claim full validation. Extraction and risk-interface response failures remain
fatal because there is no safe local decision to substitute.

Exact request-hash sidecars are reused across pipeline passes, and FactReasoner atoms
are sent in deterministic batches of at most 64. Once any interrupted aggregate
reservation has been reconciled, an ordinary replay reuses those sidecars before
making a new reservation, so it adds neither a paid call nor a new aggregate-journal
event.

## 8. Run state and replay

`run_state.py` owns the immutable run manifest and append-only stage journal. Every
stage records its input digests, output digest, status, reason code, and closed
metrics. `pipeline-result.json` references the canonical stage artifacts, including
the publication-conflict count and digest, and is verified against the journal and
filesystem before reuse.

`run_summary.py` produces `audit-view.json` and `usage-summary.json`. They expose stage
counts, repair counts, validation status, and cost/latency totals without source text,
prompts, or raw ledger rows. `quality_report.py` re-verifies complete batch artifact
chains, replays publication enrichment/provenance/conflicts and deletion-only
validation, and
requires final FactReasoner coverage of the 33-field publication contract. With a
paired replay it also compares value, artifact, decision, validation, risk, omission,
privacy, and cost/latency surfaces.

## Artifact layout

| Artifact | Role | Public-card content? |
| --- | --- | --- |
| `source-bundle/`, `official-source-bundle/` | Frozen bytes and closed manifests | No |
| `source-state.json`, `source-catalog.json` | Combined immutable source identity | No |
| `extraction.json`, `claim-gates.json` | Candidates and support decisions | No |
| `composition*.json`, `factreasoner-original.json`, `factreasoner-content.json`, `omissions*.json` | Before/after audit-content repair projections and checks | No |
| `repairs.json`, `risk-mapping.json` | Local field repair and taxonomy audit | No |
| `factreasoner-publication-original.json`, `publication-validation.json`, `publication-conflicts.json` | Enriched pre-withhold public check, deletion-only decisions, and hashed source conflicts | No |
| `factreasoner.json`, `privacy.json` | Final public-card factuality and privacy checks | No |
| `card-artifact.json` | Bindings, reviews, validation, and derived card | No |
| `public-card.json` | Exact 33-field-allowlisted seven-section JSON projection | Yes |
| `cards/NAME.json`, `cards/NAME.md` | Published canonical JSON and its deterministic human-readable companion | Yes |
| `run-manifest.json`, `journal.jsonl`, `pipeline-result.json` | Run and artifact integrity chain | No |
| `audit-view.json`, `usage-summary.json` | Body-free operational summaries | No |
| `aggregate-budget.jsonl`, `aggregate-budget-summary.json` | Shared provider-batch cap and its batch-bound snapshot | No |
| `quality-report.json` | Body-free batch or paired-replay aggregate | Separate publishable report |

## Package map

| Modules | Responsibility |
| --- | --- |
| `contract.py`, `schema.py` | Rich local audit contract, absence values, and audit validation |
| `publication_contract.py`, `publication_schema.py`, `publication.py`, `publication_sources.py`, `publication_validation.py` | Exact 33-field public contract, allowlisted projection, frozen-source enrichment/provenance replay, and deletion-only validation |
| `source_bundle.py`, `hf_adapter.py` | Exact-revision Hugging Face collection and replay |
| `official_discovery.py`, `scholarly_discovery.py`, `official_http.py`, `official_sources.py`, `official_documents.py` | Declared and bounded scholarly discovery plus official-source boundary |
| `source_state.py`, `combined_sources.py`, `source_documents.py` | Immutable source state and typed catalogs |
| `extraction.py`, `claim_gate.py`, `composer.py` | Candidate extraction, support checks, and evidence-only projection |
| `factreasoner.py`, `findings.py`, `field_repair.py` | Atomic factuality, omission/conflict audits, and targeted repair |
| `risk_mapping.py` | Pinned taxonomy integration and applicability gate |
| `provider.py`, `provider_adapters.py`, `run_ledger.py`, `orchestration.py` | Exact provider route, bounded calls, normalized decisions, and accounting |
| `artifact.py`, `review.py`, `public_export.py`, `public_markdown.py`, `privacy.py` | Typed artifact, append-only review, frozen-source replay-bound JSON export, deterministic Markdown, and publication boundary |
| `run_state.py`, `pipeline.py`, `run_summary.py`, `quality_report.py` | End-to-end execution, resume, summaries, and batch aggregation |
| `cli.py` | `collect`, `generate`, `batch`, `report`, inspection, review, repair-record, validation, and export commands |

## Verification

```sh
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m model_cards schema > build/model-card.schema.json
PYTHONPATH=src python3 -m model_cards validate cards/NAME.json
```

The default suite uses fixtures and injected transports. It does not issue paid
provider calls. The repository's example publishing path is described in
[README.md](README.md) and implemented by `scripts/publish_examples.py`.
