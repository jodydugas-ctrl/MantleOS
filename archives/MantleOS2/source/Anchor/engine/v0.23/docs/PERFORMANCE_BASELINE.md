# SCAN v0.17 Local Performance / Resume Baseline

This is a **measured development-environment baseline**, not a cross-platform performance guarantee and not a substitute for scanning a large real application.

## Environment

- Engine: `0.17.0`
- Python: `3.13.5`
- Specimen: scanner-owned synthetic C++/Qt-ish tree
- Files: `321`
- Declared source bytes: `46,479`
- Aggregate limits: disabled for this benchmark

## Cold run

- elapsed: `4.5326 s`
- nodes: `963`
- edges: `601`
- evidence: `961`
- extraction cache: `0 hits / 1,542 misses`

## Unchanged warm rerun

- elapsed: `0.5398 s`
- extraction cache: `1,542 hits / 0 misses`
- integrity: `MAPPED / 0 issues`
- aggregate budget: not triggered

The warm run demonstrates that unchanged extraction work is content/version-cache reusable across a second scan into the same canonical output. A dedicated regression separately verifies that a budget-limited partial scan can be rerun unbounded and complete while reusing valid cache entries.

## Interpretation boundary

These measurements support PR8 load/resume engineering, but they do **not** close the production gate by themselves. Remaining performance evidence should include complete real C++/Qt repositories, materially larger byte/graph loads, and platform/Python-version measurements on the declared support matrix.
