# Executable Invariant Registry

Mantle's proof catalogue has one live source: `REGISTRY` in
`src/mantle/audits/invariants.py`, built and validated by
`src/mantle/audits/registry.py`.

Each `InvariantSpec` carries:

- a stable proof code and human title;
- the threat-model guarantee ID it supports;
- its executable runner;
- an added marker; and
- a concern (`body`, `cognition`, `execution`, `application`, `reproduction`,
  `residency`, or `operations`).

`CONCERNS` is a derived view for focused maintenance. `TESTS` is retained only as a
derived compatibility tuple; adding to it cannot create a second registry. Stage 1,
Stage 2, `mantle prove`, `mantle doctor`, application certification, and the registry
fingerprint all consume `REGISTRY`.

The doctor verifies both directions that are mechanically knowable: every proof cited by
an enforced or detected threat row exists, and every registered invariant maps to a
declared threat-model guarantee. That is a drift check, not a semantic theorem; reviewers
still decide whether a runner proves the property claimed beside it.

Do not document a fixed registry population. The live command derives it:

```bash
python -m mantle prove
```

For guard changes, run the complementary mutation catalogue:

```bash
python tools/mutate.py
```
