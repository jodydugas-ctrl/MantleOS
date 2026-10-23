# Documentation housekeeping — 2026-08-01

## Scope

This local pass reconciled maintained README, security, architecture, field-guide,
reproduction, assimilation, example, and Grimoire-index documentation with the executable
Mantle OS `2.0.0rc1` candidate. It did not publish or modify either immutable Grimoire
edition.

## Corrections

- Replaced stale unauthenticated hatch/graft examples with the current one-shot,
  artifact/action/target-bound lifecycle authorization flow.
- Documented the resident protocol v2 session commands, the adapter-owned `/quit` command,
  requested/resolved provider evidence, and the `openrouter/free` default.
- Replaced the pre-scanner-expansion description with current Python, JavaScript/Go,
  Rust, native C/C++, Qt, resource, and CMake coverage plus `COMPLETE`, `PARTIAL`, and
  `BLOCKED` reporting.
- Updated application certification, bounded research, repository layout, security support,
  SELF reconstruction, external activation, and MIND-fusion authority descriptions.
- Corrected the Grimoire reading index: v0.10 is adopted for new tissue, v0.9 is frozen
  compatibility, and the unversioned file is the v0.9 mirror.
- Made the independent v0.10 verifier reject unsupported editions before applying v0.10
  conformance law.

## Grimoire integrity

The selected edition was `grimoire-v0.10`. Sections 0 through 13 were loaded in order; no
section was absent. The adopted edition passed the independent verifier with 254 atoms,
295 composition rows, five self-test vectors, and 209 BOOK runs.

The immutable tracked edition objects were unchanged:

| Artifact | Git blob |
| --- | --- |
| `editions/grimoire-v0.9.md` | `de7bf93d331d51f60574072b87f93f40ce9e4bb8` |
| `The Grimoire.md` v0.9 mirror | `de7bf93d331d51f60574072b87f93f40ce9e4bb8` |
| `editions/grimoire-v0.10.md` | `1b897f832607f5ffd24cc2165b7778a9435cd7e2` |

Frozen v0.9 behavior was verified through the compatibility/profile test suite and the
Mantle invariant gate, not by applying the v0.10-only independent verifier.

## Verification

| Check | Result |
| --- | --- |
| Local Markdown targets | 109 checked, 0 missing |
| Package/runtime version alignment | `2.0.0rc1` / `2.0.0rc1` |
| `compileall` | PASS |
| Grimoire focused suite | 33 passed |
| Maintained `examples/tests` suite | 79 passed, 2 skipped, 3 subtests passed |
| `python -m mantle prove` | all invariants green (dated run) |
| `python -m mantle audit` | 22/22 Stage-1 rows, all invariants, PASS |
| `python -m mantle audit-mind` | 7/7 Stage-2 rows, 23/23 Phase-1 regression, PASS |
| `python -m mantle check --fast` | 11 passed, 1 expected non-resident skip, 0 failed |
| `python -m mantle check` | 13 passed, 1 expected non-resident skip, 0 failed; PARTIAL, not certification |
| `git diff --check` | PASS |

The aggregate check remains explicitly `PARTIAL` because its reference organism is not a
host resident, so the resident-cadence row is not applicable. This housekeeping pass does
not claim certification from that result.

## Friction and prevention

The newly observed documentation/edition-tool friction is recorded as `FRICTION-015`
through `FRICTION-017` in [`FRICTION_EVENTS.md`](FRICTION_EVENTS.md).
