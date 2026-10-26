# REFLEX/0.1 experimental `anomaly-basic` dialect — M0 contract

**Status:** experimental, unapproved, non-clinical. This file freezes semantics for
this **prototype only**; it is **not** a qualified MantleOS Book or review decision.

## Scope and authority

- Python 3.11+ standard library only; separate from MantleOS production, KPP and historical sources.
- Compiler only accepts strict JSON typed IR. Never `eval`, imports or generated Python.
- VM reads only passed-in snapshot bytes. No current clock, network, filesystem, provider or host action inside execution.
- Results are `NORMAL`, `ANOMALY`, `UNKNOWN` and `REQUEST_REVIEW`. `review_requested`
  is a report field, **not a queued job or authorization**.
- Artifact digest binds bytes, NOT publisher identity, consent, installation or operator approval.
- Named `read:input_name` capabilities are descriptive; an authorized host must approve
  input access separately. Unknown outputs may not silently route to `NORMAL` or `ANOMALY`.

## Canonical IR

Required **exact top-level keys**: `schema`, `book`, `id`, `inputs`, `preconditions`,
`predicate`, `outcomes`, `on_anomaly`, `capabilities`, `limits`.

`schema="mantle.reflex-ir/0.1"`, `book={"id":"reflex","edition":"0.1","dialect":"anomaly-basic"}`.
A dotted lowercase program ID is required. `inputs` maps 1..32 lowercase identifiers to
`Int`, `GeoFix`, or `Region`. Source-size limit: 65536 bytes. Duplicate JSON keys,
non-NFC strings, floating-point JSON numbers, noninteger values, invalid Unicode,
unrecognized fields, unsupported Books and unbounded integer values are refused.
Canonical bytes: UTF-8 JSON; lexicographically sorted keys; no whitespace; Unicode
preserved; integer decimal literals; normalized NFC input only; SHA-256 over exact bytes.

`limits` requires all of: `max_nodes` (1..256), `max_input_bytes` (1..65536),
`max_instructions` (1..512), `max_result_bytes` (1..2048). The host must apply
any **elapsed-time** and **allocation** limit externally; this prototype does not
promise hostile-input process isolation or OS resource sandboxing.

## Inputs and spatial limitations

Input envelope: `{"schema":"mantle.reflex-input/0.1","clock_utc":"...Z","values":{...}}`.
Clock is **injected** and in whole-second `YYYY-MM-DDTHH:MM:SSZ` UTC. Values may be absent;
undeclared extra values are refused. All coordinates are signed integer microdegrees.

- `Int`: signed 32-bit integer.
- `GeoFix`: exact `type`, `lat_e6`, `lon_e6`, `accuracy_m`, `observed_at`, `source`.
  `type=GeoFix`, accuracy is a nonnegative integer metres estimate; timestamp UTC;
  `source` must start `synthetic:`. Valid global coordinate ranges, but latitudes outside
  ±55° **evaluate UNKNOWN** in this prototype.
- `Region`: exact `type`, `crs`, `lat_min_e6`, `lat_max_e6`, `lon_min_e6`, `lon_max_e6`.
  `type=Region`, `crs=WGS84-E6-RECT/0.1`; nonempty non-antimeridian-crossing
  rectangle with latitudes restricted to ±55°. Missing region => UNKNOWN.
- `outside_region`: a **conservative synthetic rectangle approximation, not a
  geographic fence**. Coordinates use integer microdegrees. For latitudes ±55°,
  prototype uses deliberately conservative lower bounds of **110000 m per degree
  latitude and 50000 m per degree longitude**. It returns TRUE when separation
  outside any boundary is larger than the fix accuracy, FALSE only when fix is
  inside with margin exceeding accuracy on all sides, otherwise UNKNOWN. Actual
  geodesic correctness is **not verified**. Do not use to make real-world location
  or safety decisions.

## Three-valued logic and preconditions

Strong Kleene logic: `not3(T)=F`, `not3(F)=T`, `not3(U)=U`;
`and3`=FALSE if any operand FALSE, else UNKNOWN if any UNKNOWN, else TRUE;
`or3`=TRUE if any TRUE, else UNKNOWN if any UNKNOWN, else FALSE.

Supported operators:

- `literal` Bool3: `{"op":"literal","value":"TRUE"}`.
- `known`: TRUE for supplied input, FALSE for missing input. Deliberate absence test.
- `compare_eq`: exact Int constant or Int input operands, no coercion.
- `compare_range`: closed inclusive `[min,max]` Int range.
- `outside_region`: GeoFix and Region input references.
- `and`, `or`: 2..16 predicates each; `not`: unary predicate.

Preconditions are either `fresh(input:GeoFix,max_age_seconds:1..86400)` or
`quality_at_least(input:GeoFix,max_accuracy_m:1..100000)`; the latter precisely
means `accuracy_m <= max_accuracy_m` (smaller uncertainty is better). Missing,
future, expired or inadequate quality yield UNKNOWN, **not FALSE**. Any
`outside_region` input must have both guards. Guards have **priority over the predicate**: if any guard is not TRUE,
final Bool3 is UNKNOWN even when the predicate itself is FALSE. Otherwise the
predicate Bool3 is the result. This prevents stale/poor quality NORMAL reports. `outcomes` requires true, false and
unknown enum mappings. Mapping `unknown` to `NORMAL`/`ANOMALY` is refused.
`on_anomaly` is `NONE` or `REQUEST_REVIEW`, purely an output flag.

## Bytecode ABI and integrity

Binary frame: 4-byte magic `RFX1`, 4-byte big-endian unsigned byte length,
32-byte SHA-256(payload), and compact canonical UTF-8 JSON payload. Max framed
payload length: 65536 bytes. Payload `schema=mantle.reflex-bytecode/0.1`,
`abi=reflex-vm/0.1`, `program_sha256`, full `ir` and `instructions`. Decoder
must independently validate program and regenerate exact instructions; mismatched
bytecode is refused even if an attacker recomputes the payload digest. No mutable
registers, branches, loops, external imports, recursive calls or side effects.

Instruction vocabulary: `PUSH_BOOL3`, `LOAD_INPUT`, `LOAD_CONST`, `CHECK_KNOWN`,
`CHECK_FRESH`, `CHECK_QUALITY`, `GEO_OUTSIDE`, `EQ`, `RANGE`, `AND3`, `OR3`,
`NOT3`, `GUARD3`, `BRANCH3`, `HALT`. `BRANCH3` chooses a declared result, does not jump.
Every compiled program terminates by `HALT`, and code length is bounded statically.

A trace contains VM version, program SHA-256, input SHA-256, executed instruction
indices, result and refusal code. It never includes raw observation values.
A successful `verify` command means structural/integrity validation only.

## Refusal code registry

| Code | Reason |
| --- | --- |
| `E_JSON` | JSON syntax issue |
| `E_DUPLICATE_KEY` | Repeated object member |
| `E_TEXT` | Invalid UTF-8/NFC/source text |
| `E_NUMBER` | JSON fractional number/NaN/overflow |
| `E_TYPE` | Invalid type/constant |
| `E_SHAPE` | Unexpected/absent fields |
| `E_EDITION` | Unrecognized schema or Book |
| `E_ID` | Invalid program identifier |
| `E_INPUT_REF` | Undeclared input |
| `E_RANGE` | Invalid integer range/geometry |
| `E_TIMESTAMP` | Invalid or ambiguous timestamp |
| `E_SOURCE` | Non-synthetic observation source |
| `E_GUARD` | Missing required freshness/quality precondition |
| `E_DUPLICATE` | Duplicate precondition |
| `E_DEPTH` | Excessive JSON or AST depth |
| `E_LIMIT` | Illegal/exceeded declared static budget |
| `E_SIZE` | Declared payload/input/result size exceeded |
| `E_OPCODE` | Unsupported operator/instruction |
| `E_CAPABILITY` | Wrong/extra/undeclared read right |
| `E_AUTHORITY` | Attempted implicit authority / unknown outcome misrouting |
| `E_BINARY` | Invalid binary header/frame |
| `E_INTEGRITY` | Digest or compiled instruction mismatch |
| `E_VM` | Runtime internal state failure |
| `E_IO` | CLI filesystem I/O failure |

## Unresolved before qualification

1. True geodesic geometry, accuracy uncertainty model, CRS registry and fixtures.
2. Unit/decimal/quantity/timestamp/duration/region variants and `delta`/`select` operators.
3. Cross-platform canonical Unicode and interpreter conformance, fixed VM ABI governance.
4. Wall-clock/allocation caps in host process, hostile-input fuzz, crash/recovery.
5. Independent approval signatures, stale-dependency checks, registry/rollback.
6. Carrier adapter, KPP upstream acceptance, Body integration, performance comparisons.

All these are **blocked/unsupported**, not silently present. Do not install this code
in a Body or use it for patient/safety-related inferences.

## M0 review candidate clarifications

- The canonical JSON subset is intentionally **not** RFC 8785/JCS: fractional JSON
  numbers are refused outright; NFC text is required; bytes and digests are bound
  by this edition's exact Python serializer contract pending cross-runtime review.
- `max_input_bytes` counts the canonical reserialization of the typed input
  envelope, not the raw whitespace-bearing source. Independent raw input source
  bytes are capped at `MAX_SOURCE_BYTES=65536` before parsing.
- Direct Python `dict` API calls receive identical JSON grammar and bounds checks
  to serialized input. In-memory objects containing floats, non-NFC strings,
  integer overflows, non-string keys or unsupported members are refused.
- The static checker refuses programs whose `max_result_bytes` cannot fit every
  enumerated structured result; a branch can never silently outrun the declared
  result budget merely because the author declared a tiny number.
- The M0 review packet and pinned hashes are at `docs/reflex/M0-REVIEW.md` and
  `examples/reflex_book/golden_hashes.json`; neither is an admission receipt.

---

## Experimental M3 evidence/admission extension (24 Oct 2026; NOT a frozen Book addition)

`mantle.reflex-candidate/0.2-experimental` binds the canonical IR and binary
SHA-256, exact Book/edition/dialect and VM ABI, compiler version, declared
input/output schemas, read-only capability list, limits, bounded evidence
receipt digest and synthetic reference labels, dependency baseline digests,
proposer ID, optional predecessor candidate digest, and local-simulation scope.
The canonical digest of all fields except `candidate_sha256` becomes the
candidate identifier. The receipt is not itself independent test attestation.

`mantle.reflex-operator-receipt/0.1-experimental` contains an HMAC-SHA256 over
canonical JSON containing its exact candidate/program digest, approved read-only
capabilities, dependency pins, scope, reviewer distinct from proposer,
not-before, expiry and nonce. Only a separately trusted Python host with a
nonpublic operator key can validate authority. An unchanged REFLEX bytecode is
not made executable on a production Body by any of these records.

`mantle.reflex-registry-audit/0.1` is the audit format of a disposable SQLite
simulation, not an alternative Engram. Records are sequential SHA-256-linked;
rollback only selects a revision previously activated and still authorized.
`STALE` permanently quarantines a candidate on observed dependency changes;
new dependent versions require new candidate/approval. `REFUSED` captures
bounded denial codes without denied payloads. Local hashes detect ordinary
accidental or isolated tampering but do not protect against a privileged host
able to rewrite all records and recompute hashes.

M3 additions use the refusal codes: `E_APPROVAL`, `E_EVIDENCE`, `E_EXPIRED`,
`E_AUDIT`, `E_NOT_INSTALLED`, `E_NOT_ACTIVE`, `E_REVOKED`, `E_STALE`,
`E_DUPLICATE`, `E_ROLLBACK`, plus existing `E_AUTHORITY`/`E_INTEGRITY`.
Host work must enforce independently configured limits and security policy.
No new language-side effects, opcodes, authority grants or clinical semantics
are introduced by M3.

---

## M4 data-only carrier extension (24 October 2026; experimental and unapproved)

For the exact adapter ABI, consult `carriers/contract.py`, `carriers/raw.py` and
`carriers/zip_reflex.py`. Both transports operate exclusively on the **canonical
IR byte string**, not the `.rfx` executable or an M3 admission receipt. The
strict manifest binds program id, Book, byte count and SHA-256, with `authority`
set to `NONE`, `installed=false`, and `executable_on_decode=false`. The consumer
supplies an independent known SHA-256 of the *canonical IR* to `verify`.

- Raw framing: `RFC1 | u32be manifest_bytes | u32be program_bytes | 32-byte
  SHA256('mantle.reflex-raw/0.1-experimental\\0' || manifest || program) | manifest
  JSON | program JSON`. The quoted `\\0` denotes a literal single NUL byte.
- Strict ZIP: two exact ordered member names `manifest.json`, `program.json`;
  canonical metadata, fixed 1980 timestamp, Unix regular-file 0644, DEFLATE;
  **byte exactness in this prototype is host zlib/Python dependent**. No claim of
  portable byte-identical ZIP output across runtimes/versions before review.
- Bounds: carrier 262,144 bytes; manifest 4,096; program 65,536. No decode
  path installs or executes. New refusal codes `E_CARRIER` and `E_CANONICAL`.
- These are experimental **REFLEX-only transports**, NOT production Cartridge,
  ChromaMem v5 or VCW Books. Full M4 exit remains blocked on approval of a
  compatible real MantleOS carrier and native regression tests.

Details, test evidence and blockers: `docs/reflex/M4-REVIEW.md`.
