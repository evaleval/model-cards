# Pipeline figure

`model-card-pipeline.tex` is the authoritative source. It adapts the visual grammar of
the shipped Auto-BenchmarkCards pipeline figure to the implemented Model Cards content
path. The output is a generated card and binding ledger, not a published card.

Build the vector PDF and 600 dpi PNG with these commands.

```sh
latexmk -pdf -interaction=nonstopmode -halt-on-error model-card-pipeline.tex
pdftoppm -png -r 600 -singlefile \
  model-card-pipeline.pdf model-card-pipeline
```

The palette is Ink `#1A1A1A`, Ink60 `#6E6E6E`, Rule `#D9D9D9`, and Blue700
`#1F4E9C`. The figure uses native TikZ shapes and TeX Gyre Termes through `newtx`.

## Caption

> Model Card generation pipeline. The system fixes one model revision, freezes the
> available source bundle, records evidence candidates with their source span, claimed
> entity, and relation to the target. Accepted bindings populate 33 documentation
> fields; five provenance and quality fields are derived. Withheld bindings remain in
> the ledger, unsupported fields stay Not specified, and human release review is
> pending.
