# Executed Python Anchors

A staged candidate and kpp.reflex-tests/1 suite bind to one current recipe. Original/reflex/optional-absent mandatory scripts and candidate bytes are pinned and checked before/after execution.

```text
kpp test --execute --reviewed --workspace WS --candidate CANDIDATE --suite SUITE --out NEW_REPORT.json
kpp test-check --report NEW_REPORT.json --candidate CANDIDATE --suite SUITE
```

Both flags are required. Local Python execution has no sandbox. Reports use kpp.reflex-test-report/2 and EXPLICIT_REVIEWED_LOCAL_PYTHON; older reports are unsupported. Only separate test-accept with an explicit Baker label grants scoped acceptance. Mutations invalidate it. See ADAPTIVE-INTEGRATION.md and SECURITY.md.
