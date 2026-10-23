# MantleOS 2.0.0rc1 release readiness

## Scope and authority

This report describes the reference-platform candidate. Repository certification,
application certification, immutable historical receipts, and current runtime authority
are separate. The release manifest binds the final source commit and distribution hashes;
it does not grant a resident permission to act.

## Implemented release contract

- Canonical `ResidentRuntime`, Body command dispatcher, Prime-VCW conversation recovery,
  typed hidden Body requests, sanitized provider output, receipts, and deterministic fallback.
- Mandatory `mantle-resident-v2` declaration for maintained resident certification.
- Grounded claim/evidence firewall and post-state `ActionExecutionProof` requirement.
- Native C/C++/Qt/CMake and Rust fallback scanning, typed coverage states, actual insertion
  state, GUI nerve coverage v3, and artifact-kind-specific validators.
- Germ v2, inert inspection/migration, target-bound one-shot hatch/graft authorization,
  transactional lifecycle journals, resume/quarantine, preserved rebind, and independent keys.
- Receipt-backed energy governance, bounded resource offers, face attestations, and immutable
  ancestor queries.
- Distinct NotepadNext Mantle 2 candidate and shared-runtime Organize.AppAI migration; all
  historical NotepadNext residents, spores, and audits remain untouched.
- Windows contract CI, distribution build/install smoke, artifact hashing, and release-content
  scans in addition to the Ubuntu Python 3.10-3.14 certification matrix.

## Tracked closure evidence

- `docs/MANTLE2_CONSOLIDATION_MATRIX.md` contains all 98 actual corrections and 29 friction
  events with implementation symbols, executable tests, maintained examples, and commit IDs.
- `python -m mantle prove` reports 148/148, including every named Mantle 2 invariant family
  and the matrix/friction closure check.
- Organize.AppAI commit `896a9597b89ba899cd82a5b841424ab9204ad2c9` passed 299 tests with
  four declared optional skips and its complete fake/offline demo.
- NotepadNext candidate commit `e09b61c` produces germ-v2 lifecycle evidence, independently
  minted keys, and refuses to call observed hooks applied or runtime-verified.

## Final publication gates

Final evidence is generated after the tracked documentation commit and stored in the
non-self-referential release manifest or GitHub Actions, not retrofitted into this file:

```text
python -m compileall -q src
python -m mantle prove
python -m mantle audit
python -m mantle audit-mind
python -m mantle check --fast
python -m mantle check --strict --json
python -m pytest -q
python examples/spore/vcw_conformance.py
python tools/release_scan.py
python -m build
python -m twine check dist/*
```

Publication is ready only if every command passes, a clean-environment wheel smoke succeeds,
CI is green, both worktrees are clean, and artifact hashes match the release manifest.

## Deliberate non-goals and residual risks

- The cultivated Python runner is bounded but is not a hard WASM sandbox.
- Hostile operators, malicious in-process Body code, arbitrary tool-calling MINDs, and
  multi-agent coordination remain outside this release threat boundary.
- Pure-stdlib native/Rust scanners are conservative and report unsupported syntax as gaps.
- Core ships disabled/fake resource-offer adapters; real OS credential stores are future
  optional integrations.
- PyPI publication remains a separate explicit operator decision.
