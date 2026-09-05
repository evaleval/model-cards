# Held-out human evaluation

This directory holds the contracts for a human annotation study. It holds no completed
annotations, no reviewer identities, no source text and no results, and it never will:
human labels come from people.

- `annotation.schema.json` and `annotation-template.json`: one record per reviewer per
  card, with the six judgments kept separate.
- `reviewer-packet.schema.json`: the identity-redacted packet a reviewer is given.

## What the study asks

A card can be wrong in ways that do not look alike, so the judgments are separate and a
reviewer answers each on its own:

1. **Claim support** is the value fully supported, partly supported, unsupported, or not
   decidable from the evidence shown.
2. **Assignment** are the entity, the relation to the target, and the destination field
   each right, wrong or unclear. A quote can be genuine and still describe the wrong
   checkpoint; that is this project's central error class and it has its own question.
3. **Source binding** does the cited source, at the recorded location, support the claim.
4. **Omission** was an applicable, source-present fact present, withheld with a visible
   reason, in conflict, or simply missed. A card that withholds everything scores
   perfectly on support and badly here, which is the point of asking both.
5. **Risk applicability**, where a card carries risk material.
6. **Warning utility** would a surfaced warning actually help a reviewer decide.

## Packets

Packets are built from a drawn sample, never before one exists, and never from the cards
that happened to look interesting. `scripts/run_eval.py sample` draws a seeded stratified
sample over stage (base or instruct), source richness, and provenance (flagship or
community), with any paired targets first. The packet builder is written against that
sample and the binding ledger of the cards in it.

There is no packet builder checked in right now. The previous one was written against a
pipeline that no longer exists, and a builder that cannot run is worse than none: it
reads as a capability the repository does not have.

## Blinding

A reviewer sees the card and the evidence, not which pipeline produced it and not the
model's identity where the design calls for redaction. That constraint belongs in the
packet builder, and it is why the packet schema carries a blind id rather than the
target.
