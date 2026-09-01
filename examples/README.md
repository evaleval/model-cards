# Generated examples

The examples in `generated/` are unchanged `card` projections from real generation
runs. They are accompanied by a readable Markdown view and a small allowlisted export
record. None is human-reviewed or release-approved.

OLMo-2-1124-7B is the current non-blocked model-assisted output. Whisper Large V3 MLX
and Docling Layout Heron come from an earlier offline feasibility run and are
deliberately sparse.

`audit-cases/` is separate. It contains generated outputs that a later audit blocked.
The OLMo Instruct case is included because it exposes a real recall failure. The
sources contained two relevant facts that composition omitted.

Full artifacts are not public examples. They contain the field-level ledger, frozen
source bytes, prompts, audit material, and local execution metadata. Do not copy them,
their native HTML reports, or their source bundles into this repository.
