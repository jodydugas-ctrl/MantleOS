# Experiment definition

## Primary hypothesis

**A Daemon can preserve stable identity and functional history across completely
destroyed local runtimes when an accepted BODY transition is represented by a verified
VCW PNG stack and a Git checkpoint, with no MIND required for the continuity path.**

This is testable: reconstruct a clean runtime, run a BODY-only Heartbeat, verify and
commit it, destroy the runtime, and compare identity, stack hashes, receipts, and Git
ancestry across repeated incarnations.

## Functional continuity

Continuity is present only when all of these are true:

1. `genome/identity.json` loads with the same stable ID after every reconstruction.
2. `genome/primer.md` is outside the experiential VCW stack and is not runtime-writable.
3. The prior VCW stack verifies before circulation and the candidate verifies before commit.
4. A Heartbeat adds exactly one expected event through Memory, not an ad-hoc file write.
5. Each receipt names the beat, parent HEAD, parent/child stack fingerprints, changed layers,
   organ participation, and `mind_invoked`.
6. The next fresh runtime can read the prior event and parent commit.
7. A crash or stale incarnation cannot replace the last accepted checkpoint.

## Non-goals for v0

Autonomous migration, self-replication, arbitrary code acquisition or execution from VCW,
credential discovery, offensive behavior, uncontrolled host assimilation, multi-agent
coordination, production availability, and medical-device claims are out of scope.

## Glossary

| Term | Meaning in this experiment |
| --- | --- |
| Daemon | The laboratory organism whose durable state is in the specimen repository. |
| SPORE | A future portable carrier concept; inspection is deferred to the arrival phase. |
| VCW | The real 800x800 RGBA PNG layer substrate and its stack manifest. |
| BODY | Deterministic organs that operate without an LLM. |
| MIND | A replaceable proposal source; absent on the continuity path. |
| NEST | The repository/runtime boundary containing the specimen. |
| Heartbeat | One ordered load, verify, circulate, mutate, verify, receipt, checkpoint, stop cycle. |
| Incarnation | One temporary runtime reconstructed from durable specimen state. |
| Dormancy | The state between Heartbeats when no runtime exists. |
| Checkpoint | A verified Git commit containing only accepted durable outputs. |
| Receipt | A machine-readable record of a transition and its evidence. |

## Evidence standard

Claims count as proven only when a test or verifier produces reproducible evidence:

- SHA-256 hashes for every layer and a canonical whole-stack fingerprint.
- PNG signature, dimensions, CRCs, VCW boot/payload parse, and manifest checks.
- JSON schema checks for identity, mission, authority, and receipts.
- Git parent/child SHAs and changed-path allowlists.
- Crash matrix results showing the last committed state remains authoritative.
- Stale-incarnation rejection when the expected parent HEAD is no longer current.
- Explicit `mind_invoked=false` for BODY-only receipts.

Logs are diagnostic; hashes, receipts, verifier output, and tests are the proof record.

## Repository tree

```text
genome/                  constitutional identity, primer, mission, authority
                         special boot law and developmental organ registry
vcw/                     real exploded PNG layers
STACK.json               self-describing VCW manifest
daemon/                  BODY, Heart, VCW codec, Git adapter, runtime, CLI
receipts/                append-only transition evidence
tests/                   unit, lifecycle, crash, concurrency, and security tests
tools/                   specimen and measurement helpers
docs/                    experiment, architecture, provenance, GitHub guide
.github/workflows/       Actions-shaped local entry point
```
