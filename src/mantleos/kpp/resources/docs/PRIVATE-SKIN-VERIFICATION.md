# Private Skin qualification — 2 November 2026

Status: experimental controller pilot; recipe acceptance OPEN.

## Implemented

Five Pantry contracts, a separate recipe/4 Anchor design, optional crypto dependency,
sealed canonical records and source/founding objects, incremental authenticated
retrieval metadata, owner policy checks, private MIND adapter ports, signed exact
release verification, read observation binding, replay, current Journal and explicit
historical raven-skin/1 import, sealed backup and retained-checkpoint checks.
All existing public AppAI and Journal defaults remain available.

## Current execution evidence

Focused suite: 21 tests pass on Windows/Python 3.14 with cryptography 46.0.7.
The fresh-process test reloads sealed state using a separately supplied synthetic
key. Import tests preserve exact canonical records and full originating Journal
bytes, and exercise a manufactured historical envelope and native v0.3 vault. No actual Raven content
was decrypted or copied into source control.

Benchmark: tools/private_skin_specimen.py exercises six cases, histories 0/100/1000,
with zero or 20 MiB cold objects, 20 warm encounters each. Model calls are zero;
the synthetic adapter is invoked once per ordinary encounter. Raw measurements
are in private-skin-benchmark.json. These are local overhead measurements under
concurrent verification load, not a matched comparison or an LLM latency claim.

## Open qualification and unsupported operations

- No qualified Windows/Linux separate-principal worker/controller/display ships.
  HostMind requires a trusted deployment-specific isolation checker. Its synthetic
  lambda fixture supplies no OS-isolation evidence. Existing Hermes graft is public
  PRIMER mode; it is not activated as a private host.
- No live host LLM or OpenRouter API was called. API transport behavior is tested
  through an injected synthetic response. Actual routing, billing and retention
  policy enforcement remain provider/deployment qualification tasks.
- The v0.3 raven.sealed-records/1 adapter verifies native chain/index MACs and
  preserves native origin bytes and payloads through explicit provenance mapping.
  A manufactured three-event vault (including newer experience) imports and
  replays correctly; metadata/index tampering is rejected before publication.
  Private Raven and independently produced native-vault migration remain untested.
- No independent rollback witness is provided. A retained controller checkpoint
  detects an older/divergent vault; simultaneous rollback of both is not detected.
- Operator policy management, signer/key provisioning, recovery and verification
  are controller-side operations. Sealed export excludes keys. Plain cartridge/PNG
  export is not exposed by this private pilot.
- Direct complete founding-text disclosure is refused. Semantic leakage through
  generated replies remains possible; receipts establish continuity and authority,
  not hidden reasoning or persona fidelity.

## Provenance

Prototype archive SHA256:
61d69805b354aeb3a1e5a7046cb33d8723ba5ee0a558e52de09de700b778d8ad.
309 manifest entries matched; 189 Python sources parsed during inspection. The
prototype's reported 25 Linux tests are historical evidence, not this delivery's
current test results. Its random-key sealed records, narrow socket protocol and
signed receipts informed this new implementation; private archives and keys are
not published. Existing Anchor definitions and canonical Engram semantics remain
shared. Historical MantleOS2 BodyCipher and mantle-os Immune source remain heritage.

## Regression and packaging results

Complete KPP regression: 422 tests, PASS, five documented skips (668.764 s).
Complete MantleOS regression: 544 tests, PASS, five documented skips (1112.334 s).
The skips concern Windows symlink privileges. Final focused private suite: 21 tests,
PASS (43.012 s), including cold-backup authentication, explicit provider response
labels and refusal to import unresolved Journal encounters. These late hardening changes received focused verification after the
complete regression runs had started; do not interpret the full-run timing as a
fresh qualification of every later line. None of these checks grants Baker acceptance.

KPP doctor: ready, 24 ingredients / 19 recipes. Adaptive Reflex smoke: PASS.
All five documented MantleOS walkthroughs: PASS. Both wheel and sdist builds: PASS.
Installed-wheel synthetic encounters pass with isolated Python (-I); the optional
cryptography/cffi/pycparser distributions were provisioned offline from the existing
host libraries. Missing crypto was independently observed to fail with an explicit
setup requirement. These installed checks do not establish OS principal isolation.

The read-only Windows isolation harness correctly rejected a same-user deployment:
state, key and transcript canaries were readable, and a Body memory handle was
available. No users, ACLs, services, provider credentials or remote settings changed.
Separate-principal Windows/Linux and live provider/host tests remain unqualified.

### Local synthetic measurements

Each row has 20 ordinary encounters and zero live model calls. One scripted private
MIND generation occurs per encounter. Measurements include validation and durable
commit; individual commit timing and physical disk bytes are not separately
instrumented. Results reflect concurrent local verification load and a small
synthetic PRIMER. No matched speedup or fixed LLM response time is claimed.

| Prior records | Cold object | Median local ms | p95 ms | Save ms |
| --- | --- | ---: | ---: | ---: |
| 0 | none | 16.23 | 19.62 | 10.45 |
| 0 | 20 MiB | 16.49 | 24.51 | 166.99 |
| 100 | none | 17.86 | 18.83 | 14.34 |
| 100 | 20 MiB | 17.86 | 24.47 | 139.98 |
| 1000 | none | 17.42 | 21.91 | 31.51 |
| 1000 | 20 MiB | 17.80 | 18.45 | 156.41 |

Measured implementation: `0b15fc50e487f867291bef23794e4e18ce78589d44e2f3c18af22f8764ed9c0e`.
