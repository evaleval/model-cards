# Architecture

One target, `model_id@revision`, becomes one card. Every stage below either produces a
value with a source and an entity, or refuses one and says why.

```
collect -> frame -> Stage A -> gates -> EAV -> Stage B -> checks -> risks -> export
           (who is    (verbatim  (what a    (audit) (write from  (leaf,     (atlas) (34 fields,
            who)       quotes)    field may          accepted     excerpt,           Markdown,
                                  take)              evidence)    factuality)        inspector)
```

## collect

The Hugging Face snapshot at the pinned commit: README, `config.json`, model metadata
including `createdAt`, the safetensors byte count, likes, downloads, tags, `base_model`
tags and the model-index. Then the paper, then the developer's own GitHub README, then
the developer pages the README links, then the Every Eval Ever record for this exact id.

The paper is the part that goes wrong quietly. A derivative repository usually carries its
base model's arXiv tag, and Hub tags are sometimes simply wrong: Qwen3-8B tags the YaRN
paper. So every arXiv id the repository offers is a candidate, from its tags, from the
BibTeX in its README, and from the links in its prose, and each is put through a title
gate that asks whether the paper introduces this model, refers to its family, or is
unrelated. An unrelated tag is dropped unread. Every candidate that was tried stays in
the manifest with its verdict.

When the repository and its declared base point at no paper at all, which is true of most
flagship checkpoints on the Hub, OpenAlex and Semantic Scholar are searched for one. A
searched hit passes the same title gate plus two rules a tag does not need, because a tag
is a claim by the developer and a search result is a guess by an index: the family name
must be the title's own subject, with nothing continuing the name after it and nothing but
a determiner in front of it, and a generation stated in the title must be this
checkpoint's own. That is what separates "The Llama 3 Herd of Models" from "Code Llama",
"LLaMA-Adapter", "Llama 2", "Llama-3.1-FoundationAI-SecurityLLM-Reasoning-8B" and "Model
Inversion Attacks on Llama 3", all of which an index will offer for a Llama 3.2
checkpoint. A fetch that fails is recorded as a failure, never as an unrelated paper.

A gated repository degrades to what it will serve, usually the README alone, and the
manifest names each absent channel with a reason. Paper text is cached per arXiv id, so a
base checkpoint and its instruct variant extract their shared report once.

The output is one replayable bundle per target, with a SHA-256 per file.

## frame

A typed graph of who is who: the target at its pinned revision with its name spellings,
the base models from the structured tags, the family, sibling checkpoints, comparison
models, benchmarks and metrics. Structured edges come from the Hub. Edges a language model
proposes are kept only when the name occurs literally in a source. Each document declares
a default referent: a README is about the target, a family paper is about the family.

## Stage A

One structured extraction call per source and one bounded gap pass, each with a
server-enforced schema and a token cap. Every quote is verified against the bundle's own
bytes, and its section, region and table anchors are recomputed from offsets rather than
taken from the model. Referent resolution is quote-first: a claimed target is corroborated
against the quote, not obeyed.

A reply cut off by the token cap never closes its array, so the complete objects in it are
salvaged and the incomplete tail is discarded. A call that stopped on length is counted in
the card's telemetry rather than read as an empty source.

## deterministic channel

What does not need a language model does not get one: `config.json`, the safetensors
metadata, the Hub manifest, the `base_model` tags, the README frontmatter, the BibTeX
block, downloads and likes with their snapshot date. Score rows come from the tables
directly, in both orientations: one row per model with the target's row read across, and
one row per benchmark with the target's column read down, which is how technical reports
write them. The cell is selected by exact match against the target's own aliases, so a
neighbouring column belonging to a sibling is never read.

## gates

Every evidence item gets its relation to the target: `exact_target`, `base`, `derivative`,
`sibling_or_comparison`, `family` or `unknown`. Then the field decides what it can take.

Score fields keep `exact_target` only, and a benchmark score needs a row anchor naming the
target. Numeric fields refuse `base`, `derivative`, `sibling_or_comparison` and `unknown`.
A family statement is governed by a per-field policy: a base checkpoint whose own paper
introduces the family may carry its training context, recorded as relation `family` so the
scope stays visible on the binding; a derivative may not, and no numeric or score field is
on that list. Lineage is structured-channel only.

Two rules exist because a benchmark-shaped resolver cannot see them. A sentence whose
subject is a model deictic ("this model", "we release") belongs to the document's default
referent, never to a model merely named later in it: without that guard, "Our model
outperforms Llama 3.1 8B" has exactly one model name in it and rebinds to Llama. And a
sentence naming the target and another model is a comparison, which is the target's own
fact only when the target is the subject.

Nothing is dropped to a counter. Every refusal becomes a withheld binding carrying the
quote, the relation and the reason.

## EAV and Stage B

A second pass audits the high-stakes items, then the gates are reapplied. The writer sees
only accepted evidence and the established deterministic values, never the sources, and a
validator repair loop keeps it inside the contract.

## checks

- **leaf support** every number and entity name in a value must appear in a cited quote or
  in what the structured channel already fixed. This catches the quote that says 73.5
  against a value that says 99.0 without a model call.
- **source excerpt** a guarded prose field that reproduces twelve consecutive words of a
  source, or twenty-four characters in a script that does not delimit words with spaces,
  is withheld. It is a copy, not a synthesis.
- **final claim** a FactReasoner pass over the prose fields against the frozen bundle,
  non-blocking. It decomposes each value into atomic claims and scores them with an NLI
  model, and a contradiction FLAGS the field in `provenance_and_quality.flagged_fields`
  rather than removing it: the entailment model is referent-blind, and the first two
  contradictions it reported were both false. It needs token logprobs, and it records that
  it did not run, and why, when the serving route has none. A validation step that is
  quietly absent reads exactly like one that passed.

## risks

The finished card, not the sources, is what the risk stage reads. The card's own use-case
fields go to the Risk Atlas Nexus detector, which proposes candidate entries of the IBM AI
Risk Atlas; the proposal is nondeterministic, so it is drawn up to three times and the union is
taken. A structured selection call then keeps at most five, each with a justification, and
every kept row binds to its entry in the frozen copy of the taxonomy that travels in the
source bundle, by JSON pointer. A risk is therefore a selection from a fixed vocabulary
with a traceable definition, not a sentence about the model, and the faithfulness judge
does not grade it.

## ledger and export

One `BindingRecord` per value, accepted and withheld alike, with the target, the field,
the value, the claim entity, the relation, the benchmark scope, the evidence span, the
origin, the verifier action and the reason. The card is the projection of the accepted
bindings and nothing else, which the artifact validator enforces in both directions.

The export is the 34 public fields, validated against the published schema, with the
Markdown companion carrying the SHA-256 of the exact JSON bytes, plus a static HTML
inspector where every field links to its span.

## running many

Each target composes in its own process under a deadline the runner enforces. This is not
tidiness: a twelve-target run once stopped for six and a half hours with sockets to the
provider still open and every worker blocked inside a raw SSL read, past the HTTP client's
own read timeout, which never fired. A thread in that state cannot be interrupted from
inside the process. Out of process also gives each target its own usage log by
construction and keeps a crash in a native dependency from taking the run down.

The runner carries a per-card and a per-run spend ceiling computed from the handler's own
usage records, resumes on a card that loads, and writes one run manifest with the bundle
digests, the composer and pipeline commits, the serving route, the prompts fingerprint and
the totals.
