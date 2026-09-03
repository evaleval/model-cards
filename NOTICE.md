# Third-party notice

This repository incorporates and further develops generic mechanisms adapted or
ported from the EvalEval
[Auto-BenchmarkCards](https://github.com/evaleval/auto-benchmarkcard) work. Those
mechanisms include source discovery and collection patterns, document-structure and
field-scoped evidence handling, whitespace-normalized quote replay, evidence-only
composition, post-composition FactReasoner orchestration, targeted field repair and
withholding, and taxonomy risk-mapping orchestration.

The resulting implementation has been rewritten around the `model_cards` package's
neutral public contract, exact-revision source state, typed artifacts, fail-closed
provider runtime, privacy boundary, and command-line interface. It does not require an
Auto-BenchmarkCards checkout or import Auto-BenchmarkCards runtime modules.

The adapted Auto-BenchmarkCards material and this repository are Copyright (c) 2026
EvalEval and are used under the MIT License included in [LICENSE](LICENSE).

Optional and development dependencies remain subject to their own licenses; their
source code is not vendored by this repository.

PDF text extraction uses
[pypdf 6.4.0](https://github.com/py-pdf/pypdf/tree/6.4.0), Copyright (c)
2006-2008 Mathieu Fenniak and contributors, under the BSD 3-Clause License. The
dependency is installed from its published package and is not vendored here.
