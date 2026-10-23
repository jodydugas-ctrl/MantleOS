================================================================================
TOME: SPORE
BOOK: agent-instruction
DIALECT: spore-standard
================================================================================

A four-stream VCW language for a layer that must know how to BE a spore — a
self-contained agent carrying identity, one task, one append-only conversation,
tools, authority rules, and limits. This Tome does not teach a layer to think
in Python or English; it teaches a layer to be a spore.

--------------------------------------------------------------------------------
A. LAYER + SOURCE ANALYSIS
--------------------------------------------------------------------------------
LAYER_ID:     spore-top-half
SUBSTRATE:    spore-png  (the PNG's top-half colour field IS the VCW layer)
TISSUE:       agent-instructions
SOURCE_CLASS: AGENT

Semantic units: identity, task, turn, tool, protocol, authority, limit.
Relationships: HOLDER owns; SUBJECT references payload; RULE governs behavior.
Order: SEMANTIC. A conversation is an ordered sequence of turns; order matters.
Data vs roots: identity names, task text, conversation content are DATA — they
               ride content-addressed DATA frames and are referenced by hash.
               Only the instruction atoms (IDENTITY/TASK/TURN/...) are roots.

Forged from the live spore source (src/mantle/spore.py): BOOTLOADER_TEXT,
TOOLS_PROTOCOL, AUTHORITY, ROLE_MAP, update_protocol, full_rule, transport.

--------------------------------------------------------------------------------
B. DECISION
--------------------------------------------------------------------------------
DECISION: CREATE
Justification: a native AGENT grammar lets a spore REASON OVER ITS OWN LAW —
identity/task/turns/tools/authority as decodable structure, not opaque JSON.
Measured ground: the existing carrier keeps behavior as quoted JSON inside a
generic frame; reasoning across it is impossible without a native grammar.
IMPORTANT (reuse law honored): the DEFAULT for an ordinary spore remains REUSE
of the proven QUOTE-framed carrier. Forge this native Book only when the layer
must reason over its own law (self-auditing spores, machine-readable protocol,
cross-spore reference). Creation is earned, not automatic.

--------------------------------------------------------------------------------
C. BOOK IDENTITY
--------------------------------------------------------------------------------
book_id:        agent-instruction
book_edition:   0.1
dialect_id:     spore-standard
dialect_edition: 0.1
category:       AGENT
status:         CANDIDATE

--------------------------------------------------------------------------------
D. LANE CONTRACT
--------------------------------------------------------------------------------
R  what identity / instruction / conversation atom is present?
G  what behavioral role does the group play?
B  why is this believed?
A  what must the agent DO?

Lane test: one sentence per lane; every registry value answers its lane; no
value answers a different lane; each decodes without undeclared context.

--------------------------------------------------------------------------------
E. REGISTRIES
--------------------------------------------------------------------------------
R — INSTRUCTION ATOM
    01 IDENTITY   02 TASK   03 TURN   04 PROTOCOL   05 AUTHORITY   06 DATA_REF

G — BEHAVIORAL ROLE
    00 END   01 HEAD   02 HOLDER (whose record: spore|user|app|tool)
    03 SUBJECT (what it is about; payload ref)   04 NAME   05 RULE
    7f PARITY

B — EVIDENCE
    00 INHERIT   01 DIRECT (creator-attested)   05 REMEMBERED (recorded history)
    08 STIPULATED (declared protocol/authority)   0f QUOTED (the bytes themselves)
    Rule: HEAD may not use 00.

A — FORCE
    00 INHERIT   02 MUST (agent must perform / protocol must hold)
    04 NEVER (agent must never: mutate-in-place, overwrite, spawn-when-full)
    06 GATE (condition gating action, e.g. on FULL)
    08 RULE (standing rule)   0f QUOTE (carried as data, no governing force)
    Rule: HEAD may not use 00.

--------------------------------------------------------------------------------
F. COMPOSITION + FRAMING
--------------------------------------------------------------------------------
framing_id:   ordered-sequence-v1
One framed statement per agent record; frames in declared order; order semantic.
A statement = HEAD (atom + evidence + force) + HOLDER + SUBJECT(ref) + PARITY.
Payload bytes ride DATA frames and are referenced by content hash; a statement
never inlines payload bytes.

--------------------------------------------------------------------------------
G. CANONICAL DATA MODEL
--------------------------------------------------------------------------------
layer := [ record, ... ]   # ordered
record := { "seq": int,               # semantic order
            "atom": "IDENTITY"|"TASK"|"TURN"|"PROTOCOL"|"AUTHORITY",
            "holder": "spore"|"user"|"app"|"tool",
            "evidence": "DIRECT"|"REMEMBERED"|"STIPULATED"|"QUOTED",
            "force": "MUST"|"NEVER"|"GATE"|"RULE"|"QUOTE",
            "data_ref": "sha256:<hex>" }
DATA frames := { "sha256:<hex>": "<utf-8 payload text>" }  # content-addressed

--------------------------------------------------------------------------------
H. MANIFEST + DIGESTS
--------------------------------------------------------------------------------
schema:            vcw-book-v1
category:          AGENT
allocation_policy: FIXED
framing:           ordered-sequence-v1 (order_semantic=true)
integrity:         xor-parity-rba-v1 (lanes_uncovered: ["G"])   # candidate member
lane_mapping:      logical_to_carrier = identity
registry_digest:   computed from lanes in capsule (status CANDIDATE)

--------------------------------------------------------------------------------
I. REFERENCE CODEC
--------------------------------------------------------------------------------
capsule_agent_instruction_v0.1.py (pure stdlib). encode / decode /
validate_records / canonicalize / to_hex / from_hex / selftest. Round-trip
passes; 4 invalid vectors refused.

--------------------------------------------------------------------------------
J. CONFORMANCE RULES
--------------------------------------------------------------------------------
S1  frame = HEAD + HOLDER + SUBJECT + PARITY; exactly one parity, terminal.
S2  HEAD carries nonzero evidence and force.
S3  record order (seq) is semantic; a layer out of order is ambiguous-composition.
S4  payload bytes are DATA-frame content; a statement must not inline them.
S5  HOLDER must be a declared holder; unknown atom/role/evidence/force refused.
S6  every statement frame must close with a verifying parity.
S7  presence is not authority; a QUOTE-forced rule exerts no governing force.

--------------------------------------------------------------------------------
K. SELF-TESTS (real encoded bytes from the running capsule)
--------------------------------------------------------------------------------
Sample model (identity / task / one turn / protocol), 4 frames, 16 pixels:

  01010102 01020000 a6030000 a67f0102     IDENTITY spore DIRECT MUST   ref a6
  02010102 01020000 c8030000 cb7f0102     TASK     spore DIRECT MUST   ref c8
  0301050f 02020000 3e030000 3f7f050f     TURN     user  REMEMBERED QUOTE ref 3e
  04010804 03020000 9e030000 997f0804     PROTOCOL app   STIPULATED NEVER ref 9e

DATA frame refs (content hashes):
  identity  sha256:a6953d2c70778e1f5ae3501d...
  task      sha256:c88102731ce2eef09dbedce9e...
  turn0     sha256:3e4a08d95246a3a697a6e0b59...
  protocol  sha256:9eb3449f4e49d6910db636674...

--------------------------------------------------------------------------------
L. EXAMPLES
--------------------------------------------------------------------------------
Source: "Files.AppAI — a file-organizing spore" (identity)
Canonical: {seq:0, atom:IDENTITY, holder:spore, evidence:DIRECT, force:MUST,
            data_ref: sha256:a6953d2c...}
Records:  01010102 01020000 a6030000 a67f0102
Decoded:  atom=IDENTITY holder=spore evidence=DIRECT force=MUST (ref byte a6)

--------------------------------------------------------------------------------
M. INVALID VECTORS (each refused)
--------------------------------------------------------------------------------
unknown atom value in HEAD   -> unknown-value
truncated final frame        -> truncated-structure
parity mismatch (flip a lane)-> unknown-value
HEAD inheriting evidence     -> missing-required-role

--------------------------------------------------------------------------------
N. ROUND-TRIP REPORT (measured)
--------------------------------------------------------------------------------
statements:            4    pixels: 16
round-trip (encode->hex->decode->structural equality): PASS
invalid vectors refused: 4/4
selftest status:       PASS  (python capsule_agent_instruction_v0.1.py)

--------------------------------------------------------------------------------
O. MEASUREMENT
--------------------------------------------------------------------------------
This is a CANDIDATE dialect from a 4-statement sample. records_per_structure =
4 pixels/statement (HEAD+HOLDER+SUBJECT+PARITY). No corpus, no unseen/adversarial
split yet — those measurements are owed before FROZEN.
Integrity member xor-parity-rba-v1 leaves the G lane uncovered (measured in
audit: ~68.7% of G flips caught). See Known Bends B2.

--------------------------------------------------------------------------------
P. KNOWN BENDS
--------------------------------------------------------------------------------
B1 STRUCTURAL  data_ref collapses to a 1-byte projection in the pixel run; the
               full content hash round-trips through the DATA frames, not the
               pixels. Full content-addressed reference is the next refinement.
B2 STRUCTURAL  integrity member xor-parity-rba-v1 does not cover the G lane; a
               role-byte flip onto another valid role decodes silently. The
               candidate should be upgraded to rotated-parity-rgba-v1 before
               FROZEN (as the operational Tome already uses).
B3 UNMEASURED  no corpus / unseen / adversarial split; 4-statement sample only.
B4 STRUCTURAL  codec digest is a placeholder until freeze.

--------------------------------------------------------------------------------
Q. BOOT DECLARATION + LINEAGE
--------------------------------------------------------------------------------
category: AGENT
book_id: agent-instruction    book_edition: 0.1
dialect_id: spore-standard    dialect_edition: 0.1
framing_id: ordered-sequence-v1
integrity_id: xor-parity-rba-v1   (upgrade path: rotated-parity-rgba-v1)
Lineage: forged from SPORE-PNG v2 carrier source. Default for ordinary spores
remains the proven QUOTE-framed carrier; this native Book is for spores that
must reason over their own law. Upgrade to rotated parity + a real corpus are
the gate to FROZEN.
================================================================================
