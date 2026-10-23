# Provenance and reuse

The released `jodydugas-ctrl/mantle-os` repository is reference tissue, not a dependency.
The PNG layer geometry, RGBA encoding discipline, VCW boot/payload separation, immutable
entry hashing, and append-oriented memory model were independently reimplemented here in
the standard library. No released source file is imported at runtime.

Every adapted behavior is traceable to:

```text
source: jodydugas-ctrl/mantle-os
reference: released VCW PNG codec and entry model
target: Mantle Daemon Laboratory v0.1.0
adaptation: compact standalone codec + Git-native stack manifest
```

The specimen's `STACK.json` stores per-layer SHA-256 hashes. Receipts store parent and
child whole-stack fingerprints, and Git records the complete checkpoint ancestry.

