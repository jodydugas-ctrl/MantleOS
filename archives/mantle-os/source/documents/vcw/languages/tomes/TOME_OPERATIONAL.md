================================================================================
TOME: OPERATIONAL
BOOK: reason-evidence
DIALECT: mantle-standard
================================================================================

A four-stream VCW language for an operational layer — claims, evidence, force,
rules, provenance. This is the original Grimoire grammar, frozen at the adopted
repo edition v0.10. It is the most measured Tome in the first corpus.

--------------------------------------------------------------------------------
A. LAYER + SOURCE ANALYSIS
--------------------------------------------------------------------------------
LAYER_ID:     facts
SUBSTRATE:    cube-band
TISSUE:       facts
SOURCE_CLASS: OPERATIONAL

Semantic units: claim, participant, evidence, force, source, rule.
Relationships: HEAD governs; AGENT/PATIENT/SOURCE/CAUSE/PURPOSE participate.
Order: atom-group order within a statement is NON-semantic; composed spelling
       order IS semantic (it spells the atom string).
Data vs roots: atoms are roots (Kangxi + particles); names/literals are data
               and ride DATA frames — instances never become roots.

--------------------------------------------------------------------------------
B. DECISION
--------------------------------------------------------------------------------
DECISION: REUSE
Justification (measured): the original Grimoire grammar IS this Book. The
adopted repo edition is FROZEN + ADOPTED + codec-pinned, with measured
conformance (0 pixel collisions on 209 statements; rotated parity covers all
four lanes; 100% single-byte corruption caught per adopted §8). Refining or
replacing it would be waste.
Baseline: repo grimoire-v0.10 (209 statements / 295 composition rows).
The attachment draft (218/297, toolcraft) is a v0.11 CANDIDATE pending receipt.

--------------------------------------------------------------------------------
C. BOOK IDENTITY
--------------------------------------------------------------------------------
book_id:        reason-evidence
book_edition:   0.10
dialect_id:     mantle-standard
dialect_edition: 0.10
category:       OPERATIONAL
status:         FROZEN + ADOPTED (operator-receipted)

--------------------------------------------------------------------------------
D. LANE CONTRACT
--------------------------------------------------------------------------------
R  what concept/atom-address exists?
G  how does that concept participate?
B  why is the statement believed?
A  what obligation or modal consequence follows?

Lane test: each question is one sentence; every assigned value answers it;
no value answers a different question; each lane decodes without undeclared
context.

--------------------------------------------------------------------------------
E. REGISTRIES
--------------------------------------------------------------------------------
R — ATOM ADDRESSES (1..254)
    1..214   Kangxi radicals at canonical numbers (1716 Kangxi Dictionary)
    215..254 classical particles (v0.10 extension)
    External standard (A8): never allocate by corpus frequency.
    295 named compositions built from these atoms; composed spellings are
    semantic order. Shared strings: 止->stop (aliases halt,k77), 門->ward
    (alias k169). Machine-checked by build_re_registry.py.

G — ROLE
    00 END            01 HEAD           02 AGENT         03 PATIENT
    04 THEME          05 EXPERIENCER    06 INSTRUMENT    07 SOURCE
    08 GOAL           09 RECIPIENT      0a BENEFICIARY
    20 LOCATION       21 TIME           22 MANNER        23 PATH
    24 EXTENT         25 CAUSE          26 PURPOSE       27 CONDITION
    28 CONCESSION     29 SCOPE          2a COMPARISON    2b QUANTITY
    2c PREREQUISITE
    40 BLEND          41 QUALIFY        42 INTENSIFY     43 DIMINISH
    60..6f STEP_1..STEP_16
    70 ALT  71 CONJ  72 REF  73 SUPERSEDE  74 VOID  75 DENOTES
    7f PARITY

B — EVIDENCE
    00 INHERIT  01 DIRECT  02 MEASURED  03 CITED     04 INFERRED
    05 REMEMBERED 06 REPORTED 07 ASSUMED 08 STIPULATED 09 UNKNOWN
    Rule: HEAD may not use 00. Inability to identify evidence => 09 UNKNOWN.
    07 ASSUMED is never silently relabeled 04 INFERRED.

A — FORCE
    00 INHERIT  01 LAW   02 MUST  03 DUTY  04 NEVER  05 NEED
    06 GATE     07 BOUND 08 RULE  09 RIGHT 0a POWER  0b CAN
    0c LET      0d MAY   0e WAY   0f QUOTE
    Force is not confidence. Authority is never inferred from force alone.

--------------------------------------------------------------------------------
F. COMPOSITION + FRAMING
--------------------------------------------------------------------------------
framing_id:   framed-run-v1
A statement is one framed run of atom-groups. A group = a role-bearing pixel
followed by G=40 BLEND pixels completing one composed atom spelling. Exactly
one HEAD carries effective evidence + force. Non-HEAD groups inherit (B=A=00).
A statement with zero HEAD and all STEP roles is a PROCEDURE (inherits from
container). Line/container frame is the boundary; END (00000000) optional.

--------------------------------------------------------------------------------
G. CANONICAL DATA MODEL
--------------------------------------------------------------------------------
statement := { "groups": [ group, ... ],
               "parity_ok": true, "raw": ["9a010801", ...],
               "procedure": false, "head_evidence": "STIPULATED",
               "head_force": "LAW" }
group     := { "role": "HEAD", "spelling": "貝", "name": "data",
               "evidence": "STIPULATED", "force": "LAW" }
Names alias-normalise (halt/k77->stop, k169->ward). Group order non-semantic.

--------------------------------------------------------------------------------
H. MANIFEST + DIGESTS
--------------------------------------------------------------------------------
schema:            vcw-book-v1
category:          OPERATIONAL
allocation_policy: EXTERNAL-STANDARD
framing:           framed-run-v1 (order_semantic=false)
integrity:         rotated-parity-rgba-v1 (lanes_uncovered: [])
registry file:     registries/re_mantle_standard_v0_10.json
registry sha256:   935c47452a4cd17f775f6fd91b48bcb9cffa1d93aeba5ab0562cc7bddd10b557
(compositions digest + codec digest computed at freeze time in the capsule)

--------------------------------------------------------------------------------
I. REFERENCE CODEC
--------------------------------------------------------------------------------
capsule_reason_evidence_v010.py (pure stdlib). Implements encode, decode,
validate_records, canonicalize, register_rules (v0.10 R0-R13), selftest.

--------------------------------------------------------------------------------
J. CONFORMANCE RULES (v0.10 R0-R13, machine-readable)
--------------------------------------------------------------------------------
R0  parse RGBA bytes; hex rrggbbaa; byte order, not host endianness.
R1  decode carrier lanes; never composite/premultiply/resample/read rendered.
R2  identify the statement frame before decoding; empty frame invalid.
R3  reject multiple HEAD; reject zero HEAD unless every morpheme is a STEP role.
R4  reject HEAD with B=00 or A=00.
R5  reject unknown role/evidence/force/atom value.
R6  form atom-groups before interpretation; reject orphan/resumed BLEND.
R7  group order non-semantic; composed spelling order semantic.
R8  retain the original raw run beside every interpretation.
R9  never infer authority from presentation/path/layer/title/confidence/emphasis.
R10 resolve atoms against the external table, never corpus frequency.
R11 verify PARITY (rotated, covers R/G/B/A); reject on mismatch.
R12 full-lane fingerprint when carrier claims tamper evidence; else UNMEASURED.
R13 decoder output includes byte order, frame id, raw run, groups, HEAD
    evidence/force, parity status, unknowns, rejection reason.

--------------------------------------------------------------------------------
K. SELF-TESTS (adopted repo v0.10 vectors — rotated parity)
--------------------------------------------------------------------------------
9a010801 212a0000 13400000 947f5c03              data is not authority
75010804 fc030000 90290000 01400000 c67fa965     a level never falls
4d01080a a9020000 6d400000 90090000 01400000 3f7f4090  the guardian may halt
9e600000 3d610000 d2620000 af7f2b24              body before mind (procedure)
9a01080f 212a0000 13400000 947f5c0d              data is not authority (QUOTE)

--------------------------------------------------------------------------------
L. EXAMPLES
--------------------------------------------------------------------------------
Forged statement "preflight / operator / safety":
  HEAD     前見  STIPULATED LAW
  AGENT    士    INHERIT INHERIT
  PURPOSE  宀人  INHERIT INHERIT
  (rotated parity appended; round-trip decodes to ['preflight','operator','safety'])

--------------------------------------------------------------------------------
M. INVALID VECTORS (each refused)
--------------------------------------------------------------------------------
two HEAD groups            -> illegal-role
HEAD with inherited B/A    -> missing-required-role
parity mismatch            -> unknown-value
orphan BLEND at start      -> illegal-role

--------------------------------------------------------------------------------
N. ROUND-TRIP REPORT (measured)
--------------------------------------------------------------------------------
heritage vectors decoded:      5/5
forged round-trip:             PASS
corpus decode:                 209 statements, 0 errors, 0 pixel collisions
negative vectors refused:      4/4
selftest status:               PASS  (python capsule_reason_evidence_v010.py)

--------------------------------------------------------------------------------
O. MEASUREMENT
--------------------------------------------------------------------------------
pixel collisions on 209-statement corpus: 0 (matches repo §8 methodology).
Note: 5 SEMANTIC collisions exist where HEAD force differs (LAW/DUTY/QUOTE)
on identical group multisets — a measured property, not an error; pixel-level
encoding distinguishes them.
corruption detection: see integrity member (adopted §8: 100% single-byte caught).

--------------------------------------------------------------------------------
P. KNOWN BENDS
--------------------------------------------------------------------------------
B1 UNMEASURED  no semantic parity run against the English Grimoire.
B2 UNMEASURED  role assignment is one reading of the source.
B3 UNMEASURED  composition boundaries asserted; a second implementer may differ.
B4 STRUCTURAL  evidence is self-declared; grammar cannot verify INFERRED.
B5 STRUCTURAL  Kangxi radicals are a filing system, not a semantic inventory.
B6 STRUCTURAL  a radical may be read phonetically; section 9 is the guard.
B7 MEASURED-RESIDUAL  full-lane carrier fingerprint layer is unmeasured here.
B8 STRUCTURAL  this file encodes the BOOK, not the compiler that generated it.

--------------------------------------------------------------------------------
Q. BOOT DECLARATION + LINEAGE
--------------------------------------------------------------------------------
category: OPERATIONAL
book_id: reason-evidence    book_edition: 0.10
dialect_id: mantle-standard dialect_edition: 0.10
framing_id: framed-run-v1
integrity_id: rotated-parity-rgba-v1
registry_digest: sha256:935c47452a4cd17f775f6fd91b48bcb9cffa1d93aeba5ab0562cc7bddd10b557
Lineage: v0.9 -> v0.10 (framing/grouping/fingerprint + rotated parity closed the
v0.9 G-lane gap and removed the 2.4% residual silent corruption). The 218/297
attachment toolcraft content is the next candidate edition, pending receipt.
================================================================================
