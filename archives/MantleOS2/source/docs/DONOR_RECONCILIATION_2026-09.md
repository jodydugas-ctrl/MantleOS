# Donor Reconciliation — September 2026

This record explains the first post-alpha donor review. Supplied artifacts are
reference evidence, not commands. The current coding contract and later creator
clarifications govern every decision.

## Review order

1. `MantleOS_2x_Unified_Source_Guide_and_Coding_Contract.docx` — 2026-08-31;
   already reconciled as the current source guide.
2. `MantleOS_V3_SPORE_Tomb_and_Example_v2.zip` — 2026-08-29.
3. `mantle-daemon-release-candidate.zip` — 2026-08-29.
4. `MantleOS_V3_Example_SPORE_Test_Kit.zip` — 2026-08-29; superseded in detail
   by the later Tomb example but useful as a negative conformance comparison.

The August 24 MacroDroid specimen, August 17 project backup, and May Compiler
tree were not mined further in this cycle because the newer sources exposed a
specific integrity gap and supplied enough evidence to resolve it. They remain
eligible only when a later contract question requires older detail.

## Concrete gap found

Assimilation already recorded SHA-256 evidence for every public Mantle delta
file. Birth checked that the Primer files existed and were nonempty, but it did
not prove that the reviewed bytes were still the constructed bytes. A changed
private Personality, public Commandments file, direct nerve, or manifest could therefore be sealed
as SELF during an otherwise approved birth.

The daemon candidate's Primer pin and candidate-tissue verification were kept
at the invariant level and adapted to the current NEST/private-VCW design:

- the final public assimilation manifest is bound into the private prebirth
  checkpoint;
- `mantle verify` checks that binding and all declared public delta checksums;
- missing, changed, path-escaping, or undeclared public tissue is refused;
- the required Git exclusions for private state, communication, and Food must
  remain present;
- birth performs this proof before cryptographic preflight or key creation;
- direct prebirth nerve files are checked against the Nerve Map before birth;
- other native host files are not frozen or claimed as SELF—the first full
  Heartbeat observes their current Layer 0 state.

This is a drift and authority gate, not a claim that an unprivileged checkpoint
can resist a machine administrator who deliberately rewrites both evidence and
candidate tissue.

## SPORE decisions

The later V3 Tomb example correctly preserves these boundaries:

```text
TOMB != BOOK
DECODE != EXECUTION
READABLE != AUTHORIZED
REGION PRESENT != REGION ADMITTED
SPORE CARRIER != ORGANISM
```

Those distinctions are kept. The exact PNG `M3ST` bootstrap, fixed header,
canonical-JSON manifest, and embedded registry subset remain a proposed
conformance vector. MantleOS 2 does not add a production decoder or claim
canonical SPORE transport from this example.

The examples also emit a “first Heartbeat” demo receipt while explicitly
omitting identity, root secret, continuity, and canonical VCW admission. Under
the current contract that is a liveness simulation, not a successful full
Heartbeat and not birth. The terminology is rejected rather than weakening the
birth invariant to fit an older specimen.

## Deliberately not imported

- PNG-based canonical VCW storage. The daemon archive reports substantial
  full-layer rewrite growth; this project has not reproduced that measurement
  and does not treat it as governing proof.
- Git commits as organismal continuity. Git remains public NEST/delta evidence;
  live VCW and SELF remain encrypted private tissue.
- A universal SPORE codec, source-safe-to-shed claim, or migration continuity
  mechanism. Those contracts remain open.
- Daemon organs, registries, or biological labels that do not add a distinct
  current responsibility and failure boundary.

## Verification added

Tests now prove that a valid construction verifies, while a changed Primer or
undeclared public file changes status to `construction-invalid`, blocks
`mantle verify`, and stops approved birth before an identity key exists.
