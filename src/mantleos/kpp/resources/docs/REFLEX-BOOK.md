# Bundled REFLEX reference toolkit

`mantleos.reflex_book` is the experimental REFLEX/0.1 anomaly-basic Book,
compiler, prepared evaluator, carrier adapters, admission simulation and evidence
inspector. It is separate from KPP's `mantleos.kpp.reflex` source staging.
Python's standard library is sufficient; no model, service or MIND is required.
The specification is shipped beside the module as `SPEC.md`; synthetic source
examples are in `resources/examples`, accessible using `importlib.resources`.

From a source checkout set `PYTHONPATH=src`; installed users need no path setting.
Choose a new output directory:

```console
python -m mantleos reflex-book demo --output my-reflex-demo
python -m mantleos reflex-book inspect my-reflex-demo/fresh.json --format text
python -m mantleos reflex-book compare my-reflex-demo/fresh.json my-reflex-demo/stale.json --format json
python -m mantleos reflex-book reproduce my-reflex-demo/fresh.json
python -m mantleos reflex-book reproduce my-reflex-demo/stale.json
python -m mantleos reflex-book evaluate my-reflex-demo/program.rfx --input my-reflex-demo/input.json --output another-record.json
```

The fresh observation is 30 seconds old and yields NORMAL. Only the supplied
rule clock advances: at age 630 seconds the same observation fails the rule's
180-second freshness guard and yields UNKNOWN / OBSERVATION_STALE. Program and
observation-value digests stay equal; the input-envelope digest changes.
Observation time, injected rule clock and recorded host evaluation time remain
separate. No wall clock is consulted by the rule itself.

## Evidence contract

`mantle.reflex-evaluation/1` carries exact framed executable bytes (lowercase hex),
validated input values, trace/0.2-experimental, host evaluation timestamp, toolkit
identity, shipped-source digest, and separate executable/program/input/value/trace
digests. Its record digest excludes only itself. All are SHA-256 integrity checks,
not authentication. Records have a 524288-byte bound, strict integer/NFC JSON,
duplicate-key refusal and exact versioned structures. Existing program and input
limits remain unchanged. New artifacts use exclusive, atomic file publication.
The demo creates a new directory and cleans its own files on failure.

Inspection checks frame integrity and compiler agreement without running the
rule, following external references or loading candidate Python. The `checked`
projection shows data identity, supplied clocks, synthetic provenance claims,
guards and instruction references. `recorded_claims` contains the supplied
decision, trace and host timestamp. Text renders that same projection as indented
escaped JSON; `--format json` uses compact JSON. Control and Unicode labels are
escaped for terminal safety. No source marker implies permission.

Reproduction explicitly runs only bounded reference evaluation. It requires the
same toolkit/source digest and VM version, then compares the complete deterministic
trace. A matching trace establishes reproducibility, not historical execution,
authorship, approval or current authorization. Recomputed hashes can conceal a
forged recorded decision; reproduction reports MISMATCH for such a claim.
Comparison reports INCOMPATIBLE across programs, source revisions or VM versions.
Inspection can still display incompatible records without executing them.

## Migration and scope

The former `experiments.reflex_book` imports become `mantleos.reflex_book`.
The former `python -m experiments.reflex_book.cli ...` commands become
`python -m mantleos reflex-book ...`. Validate, compile, verify, disassemble, run,
candidate and raw/ZIP carrier commands retain their contracts. Prior review
archives remain unchanged. Synthetic binary golden vectors materialize in temporary
directories from packaged byte pins; historical fixture receipts remain test data.

`vm.prepare` verifies once; `vm.run_prepared` snapshots inputs per call. Preparation
is not approval. Raw/ZIP verification and native Cartridge/Chroma adapters require
an independently supplied expected canonical-program digest. Attachment-byte and
program digests differ. Transport never executes, installs, activates or approves.
Native Body execution is deferred; no REFLEX tissue profile is registered.

The HMAC/SQLite admission registry is an isolated simulation with deliberately
public synthetic demo credentials. It is not a production approval system or a
hostile-Python sandbox. Geometry is a conservative synthetic rectangle, not a
qualified geodesic service. UNKNOWN is predicate uncertainty, not proof about the
outcome of an external effect. No production effect or retry is introduced.

The Pantry entry is `experimental` and its bundled-module locator is data-only.
`reflex-book-review` keeps eight review obligations. The new
`reflex-reference-inspector` recipe adds inspection provenance and reproduction;
all ten begin unmet. Local delivery does not record Baker acceptance or formal
language qualification. Windows/Python 3.14 and Ubuntu/WSL2/Python 3.12 evidence
is local; other versions/platforms remain untested until separately exercised.

## Published-repository compatibility

`python -m kpp reflex-book` and `mantleos.reflex` imports now delegate to this
maintained toolkit. The earlier native-pack/native-verify/native-unpack fresh-Body
ports remain supported. The new attachment API additionally preserves an existing
Body by producing a verified copy. Both ports carry inert data; neither admits or
executes it. Existing Engram construction, Pantry repository locators and the
explicit approval-receipt field validation are preserved.
