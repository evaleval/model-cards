# Architecture

The system generates one JSON Model Card for one exact model revision. Its source
state, stage inputs, decisions, and outputs are content-addressed so a completed run
can be replayed without changing the evidence beneath the card.

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
           risk gate + final audits + privacy
                        |
                        v
         CardArtifact --------> public-card.json
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
- Conflicting accepted values do not use last-write-wins behavior; the affected field
  is withheld.
- Unsupported fields remain `Not specified`. `Not applicable` is reserved for fields
  shown not to apply.
- Provider-free and provider-assisted runs are different admitted modes and cannot
  overwrite or resume one another.
- Public cards contain portable source references and locators, never frozen source
  bodies, credentials, prompts, raw provider payloads, run paths, or journals.

## 1. Exact source collection

`source_bundle.py` parses `MODEL[@REVISION]`, resolves the requested revision once,
and freezes a bounded set of Hugging Face inputs. The manifest records every
collected, missing, gated, or unavailable source and binds all stored bytes to the
exact target and collection limits. Replay rehashes the objects and reconstructs the
manifest identity.

For a normal networked generation, `official_discovery.py` examines declarations in
the frozen Hub material. It normalizes URLs, restricts them to configured publication,
code, and publisher-owned hosts, and records candidates without treating discovery as
evidence. `official_http.py` performs bounded, credential-free HTTPS retrieval with
manual redirect validation. `official_sources.py` checks authority, ownership,
relation, media type, byte bounds, redirect trace, and ancestry before collected
official material becomes evidence-eligible.

`official_documents.py` converts eligible JSON, HTML, Markdown, and plain text into
typed documents. Unsupported PDFs and malformed or unavailable material remain
explicit load records. The current bridge does not extract PDF text.

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

`claim_gate.py` applies the same ordered interface to every candidate:

1. `coordinate_integrity` replays the pointer or quote.
2. `entity_scope` enforces the claimed entity and target relation.
3. `field_fit` checks that the evidence belongs in the proposed contract field.
4. `value_support` checks that the complete proposed value follows from that evidence.

The first two gates are deterministic. Structured values also receive deterministic
field and value checks. Provider-assisted quote candidates receive normalized semantic
decisions for the latter gates. A withheld gate remains in `claim-gates.json` but
cannot enter the composition plan.

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
composition, FactReasoner, and omission artifacts.

## 5. Risks

Publisher-reported uses, limitations, biases, risks, and mitigations use the normal
evidence-binding path. They are not interchangeable with taxonomy inferences.

`risk_mapping.py` provides an optional adapter for AI Atlas Nexus 1.2.4 and its pinned
IBM AI Risk Atlas snapshot. The Nexus dependency is loaded only when the exact package
version is installed on Python 3.11 or newer. Taxonomy candidates require accepted use
context, a valid risk identifier, an applicability rationale, supporting field
references, and an applicability decision. Public entries label their origin as
`taxonomy_identified`; they cannot masquerade as publisher statements or confirmed
harms. An unavailable dependency or checker produces an unavailable stage, not a
replacement taxonomy result.

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

`public_export.py` projects the typed artifact to one JSON card and validates the
projection against the packaged Draft 2020-12 schema. `privacy.py` independently
audits proposed public files for schema drift, non-finite or ambiguous JSON, source
bodies, credentials, authenticated URLs, machine paths, provider material, forbidden
file types, and unsafe symlinks.

## 7. Provider-assisted orchestration

`orchestration.py` is invoked only by `generate --provider Together`. The CLI,
adapters, and orchestration admission reject every other provider; every assisted call uses exactly
`deepseek/deepseek-v4-flash-0731` through OpenRouter. It extracts bounded quote
candidates from each eligible text document once, obtains normalized field-fit and
value-support decisions, supplies a FactReasoner checker, and, when the pinned risk
dependency is available, supplies the Nexus risk interfaces.

`provider.py` and `run_ledger.py` enforce a single append-only `usage.jsonl` ledger,
the USD 25 and 300-call run caps, route freshness, structured JSON output, and at most
two retries after explicit 429/5xx responses. A transport outcome that may have sent a
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

Provider mode is intentionally absent from the batch command. This prevents separate
targets from fragmenting the one-run global accounting boundary.

## 8. Run state and replay

`run_state.py` owns the immutable run manifest and append-only stage journal. Every
stage records its input digests, output digest, status, reason code, and closed
metrics. `pipeline-result.json` references the canonical stage artifacts and is
verified against the journal and filesystem before reuse.

`run_summary.py` produces `audit-view.json` and `usage-summary.json`. They expose stage
counts, repair counts, validation status, and cost/latency totals without source text,
prompts, or raw ledger rows. `quality_report.py` re-verifies complete batch artifact
chains and aggregates the same body-free measures. With a paired replay it also
compares value, artifact, decision, validation, risk, omission, privacy, and
cost/latency surfaces.

## Artifact layout

| Artifact | Role | Public-card content? |
| --- | --- | --- |
| `source-bundle/`, `official-source-bundle/` | Frozen bytes and closed manifests | No |
| `source-state.json`, `source-catalog.json` | Combined immutable source identity | No |
| `extraction.json`, `claim-gates.json` | Candidates and support decisions | No |
| `composition*.json`, `factreasoner*.json`, `omissions*.json` | Before/after repair projections and audits | No |
| `repairs.json`, `risk-mapping.json`, `privacy.json` | Repair, taxonomy, and publication checks | No |
| `card-artifact.json` | Bindings, reviews, validation, and derived card | No |
| `public-card.json` | Contract-valid source-clean projection | Yes |
| `run-manifest.json`, `journal.jsonl`, `pipeline-result.json` | Run and artifact integrity chain | No |
| `audit-view.json`, `usage-summary.json` | Body-free operational summaries | No |
| `quality-report.json` | Body-free batch or paired-replay aggregate | Separate publishable report |

## Package map

| Modules | Responsibility |
| --- | --- |
| `contract.py`, `schema.py` | Neutral public contract, absence values, and runtime validation |
| `source_bundle.py`, `hf_adapter.py` | Exact-revision Hugging Face collection and replay |
| `official_discovery.py`, `official_http.py`, `official_sources.py`, `official_documents.py` | Declared official-source boundary |
| `source_state.py`, `combined_sources.py`, `source_documents.py` | Immutable source state and typed catalogs |
| `extraction.py`, `claim_gate.py`, `composer.py` | Candidate extraction, support checks, and evidence-only projection |
| `factreasoner.py`, `findings.py`, `field_repair.py` | Atomic factuality, omission/conflict audits, and targeted repair |
| `risk_mapping.py` | Pinned taxonomy integration and applicability gate |
| `provider.py`, `provider_adapters.py`, `run_ledger.py`, `orchestration.py` | Exact provider route, bounded calls, normalized decisions, and accounting |
| `artifact.py`, `review.py`, `public_export.py`, `privacy.py` | Typed artifact, append-only review, export, and publication boundary |
| `run_state.py`, `pipeline.py`, `run_summary.py`, `quality_report.py` | End-to-end execution, resume, summaries, and batch aggregation |
| `cli.py` | `collect`, `generate`, `batch`, `report`, inspection, review, repair-record, validation, and export commands |

## Verification

```sh
PYTHONPATH=src python3 -m pytest -q
PYTHONPATH=src python3 -m model_cards schema > build/model-card.schema.json
PYTHONPATH=src python3 -m model_cards validate cards/olmo-2-1124-7b.json
```

The default suite uses fixtures and injected transports. It does not issue paid
provider calls. The repository's example publishing path is described in
[README.md](README.md) and implemented by `scripts/publish_examples.py`.
