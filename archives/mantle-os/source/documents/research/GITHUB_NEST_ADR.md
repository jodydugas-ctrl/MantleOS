# ADR: GitHub as a Remote NEST Transport (never SELF)

**Status:** Accepted (implementation in `src/mantle/nest/` on branch `github-nest`)
**Target repository:** `jodydugas-ctrl/mantle-os` (repo ID `1258266588`)
**Schema:** `mantle-github-nest-v1` — see `documents/research/GITHUB_NEST_THREAT_MODEL.md`
and the executable invariants (`GHNEST-*`) in `src/mantle/audits/invariants.py`.

## Decision

Add GitHub as an **optional** remote NEST location for an AppAI, preserving the
existing local-directory NEST unchanged. The operator may select either a local
NEST directory or a private GitHub repository that durably carries an encrypted,
content-bound NEST.

GitHub supplies storage, events, ephemeral workers, checks, and governance. It
**never becomes the organism's SELF or runtime authority.** The Body remains
deterministic and authoritative; GitHub data and receipts enter as OTHER evidence
until verified and adopted through Mantle's existing boundaries.

## Background / forces

- The app currently resides entirely in a local NEST directory. Remote residency
  is wanted for durability and collaborator access without compromising Phase-1
  determinism or the Body-first gate.
- `python -m mantle prove` is the single, executable source of truth for
  guarantees (`src/mantle/audits/invariants.py` `REGISTRY`, validated by
  `src/mantle/audits/registry.py`). Any new guarantee must be an executable
  invariant with a red case, not prose.
- The project is pure standard library (`pyproject.toml`: `dependencies = []`).
  A remote transport must not drag in new runtime dependencies into Phase-1 core.

## Considered options

1. **Teach `Organism.save()`/`load()` to talk to GitHub directly.** Rejected:
   breaks Phase-1 determinism (HF-B08) and puts a network/SDK/credential in the
   certified Body path. Violates "Body never does network I/O."
2. **Remote NEST via materialize → local Body → publish (adopted).** The remote
   form is hydrated into a private temporary local directory first; the Body runs
   only on local bytes; then an outer residency adapter seals and publishes a
   secret-free, SELF-sealed checkpoint by exact-revision compare-and-swap.
3. **Same-repository layout (host repo is also the NEST repo).** Allowed only as
   an explicit advanced choice. Default is a separate private NEST repository per
   organism, connected by stable GitHub repository IDs. Avoids privacy,
   workflow-recursion, repository-growth, and access-control coupling.

## Consequences

- `src/mantle/nest/` is an outer, optional package. It is **never imported by**
  `mantle.core`, `mantle.organs`, or `mantle.vcw` (enforced by GHNEST-13).
- The ABODE/residency law is carried in the organism's Grimoire as a non-edition
  companion — [`residency/grimoire-residency-v1.md`](../grimoire/residency/grimoire-residency-v1.md)
  — defining `local`, `cloud`, and `github` nesting forms under one residency rule.
- Remote transport is injected; tests use a deterministic in-memory fake
  (`src/mantle/nest/fake.py`) and never need the network.
- The Body's genesis key remains the cryptographic SELF. A GitHub commit
  signature, Actions result, or App identity is technical evidence only
  (`authority.github_is_self = false`).
- All inbound GitHub events enter through Senses exactly once (GHNEST-8); all
  GitHub mutations execute through Limbs with an Action Execution Proof
  (GHNEST-7); all failures/conflicts/visibility changes route through Immune
  (GHNEST-9).
- Publication uses the git data model for one atomic multi-file commit whose ref
  advances only as a non-force fast-forward under an expected-parent CAS
  (GHNEST-6). A moved branch is a `NestConflict`, never a silent force.
- `body.json` (which carries `genesis_key`) is never uploaded. Plaintext with
  secret-shaped content is refused (GHNEST-3). The Body travels only inside an
  authenticated sealed envelope whose opening capability is never exposed to the
  MIND (GHNEST-10).
- Costs and plan-limited controls are reported honestly: `enforced`, `detected`,
  or `unavailable` (see `mantle nest doctor`).

## Verification

Smallest commands throughout; full confirmation:

```text
python -m mantle prove
python -m mantle audit
python -m mantle audit-mind
python -m mantle check --fast
python -m mantle check
git diff --check
```

Completion requires every pre-existing invariant to stay green and all `GHNEST-*`
invariants green including their red mutations.
