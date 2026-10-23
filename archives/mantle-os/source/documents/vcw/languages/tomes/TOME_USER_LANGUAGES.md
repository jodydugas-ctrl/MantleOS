================================================================================
TOME: USER LANGUAGES
BOOK: user-language
DIALECT: english-user-chat
================================================================================

A four-stream VCW language for user dialogue — preserving BOTH what the user
said (exact utterance) AND what it meant (structured interpretation). The two
are different memories and must never be silently merged.

--------------------------------------------------------------------------------
A. LAYER + SOURCE ANALYSIS
--------------------------------------------------------------------------------
LAYER_ID:     conversation
SUBSTRATE:    cube-band
TISSUE:       conversation
SOURCE_CLASS: COMMUNICATION

Semantic units: utterance, speaker, turn, clause, reference, intent, uncertainty.
Relationships: speaker owns utterance; clause carries predicate/arguments;
               reference links entities across turns.
Order: SEMANTIC. Turn sequence is the conversation; order matters.
Data vs roots: the exact words are DATA (they ride an exact-utterance frame);
               discourse/intent units are the semantic structure. The user's
               raw text never becomes a root.

--------------------------------------------------------------------------------
B. DECISION
--------------------------------------------------------------------------------
DECISION: CREATE
Justification: no existing Book preserves both the exact utterance and the
structured interpretation as linked, separately-decodable records. The
operational Tome stores claims/evidence/force; it does not store "the user
literally said these words" beside "the AppAI interpreted a request." That
pair is the point of this Tome. Measured ground: communication class absent
from the heritage corpus.

--------------------------------------------------------------------------------
C. BOOK IDENTITY
--------------------------------------------------------------------------------
book_id:        user-language
book_edition:   0.1
dialect_id:     english-user-chat
dialect_edition: 0.1
category:       COMMUNICATION
status:         CANDIDATE

--------------------------------------------------------------------------------
D. LANE CONTRACT
--------------------------------------------------------------------------------
R  what lexical / semantic unit is present?
G  what discourse role does it play?
B  why is it believed?
A  what follows from it?

Lane test: one sentence per lane; every registry value answers its lane; no
value answers a different lane; each decodes without undeclared context.

--------------------------------------------------------------------------------
E. REGISTRIES (candidate design — to be locked by corpus)
--------------------------------------------------------------------------------
R — UNIT
    01 UTTERANCE   02 SPEAKER   03 TURN   04 CLAUSE
    05 PREDICATE   06 PARTICIPANT   07 REFERENCE   08 INTENT   09 UNCERTAINTY

G — DISCOURSE ROLE
    00 END   01 HEAD   02 SPEAKER_OF   03 UTTERANCE_OF   04 PREDICATE_OF
    05 SUBJECT   06 OBJECT   07 MODIFIER   08 REFERS_TO   09 INTENT_OF
    0a QUALIFIES   7f PARITY

B — EVIDENCE
    00 INHERIT   01 DIRECT (the AppAI heard it)   06 REPORTED (relayed)
    09 UNKNOWN
    Rule: HEAD may not use 00.

A — FORCE
    00 INHERIT   0d MAY (interpretation may be revisited)
    02 MUST (honor a user instruction within Body policy)
    04 NEVER (a user prohibition within Body policy)
    0f QUOTE (the exact words, carried verbatim)
    Rule: HEAD may not use 00.

--------------------------------------------------------------------------------
F. COMPOSITION + FRAMING
--------------------------------------------------------------------------------
framing_id:   ordered-sequence-v1
Each turn is a LINKED PAIR of frames:
  frame 1  exact-utterance frame — the user's words, QUOTE-forced, verbatim.
  frame 2  interpretation frame — clauses, predicate, participants, intent,
           uncertainty, with a REFERS_TO link back to frame 1.
Turn order is semantic. The exact utterance is never replaced by its
interpretation; they are two memories, linked.

--------------------------------------------------------------------------------
G. CANONICAL DATA MODEL
--------------------------------------------------------------------------------
turn := { "seq": int,                    # semantic order
          "speaker": "user"|"app"|"system",
          "exact_text_ref": "sha256:<hex>",     # -> exact-utterance DATA frame
          "interpretation": { "clauses": [ {"predicate": str,
                                            "subject": str, "object": str,
                                            "modifiers": [str] } ],
                              "intent": str,
                              "uncertainty": "DIRECT"|"UNKNOWN"|...,
                              "evidence": "DIRECT"|"REPORTED"|...,
                              "force": "MAY"|"MUST"|"NEVER"|"QUOTE" } }
exact-utterance DATA frames := { "sha256:<hex>": "<exact utf-8 text>" }

--------------------------------------------------------------------------------
H. MANIFEST + DIGESTS
--------------------------------------------------------------------------------
schema:            vcw-book-v1
category:          COMMUNICATION
allocation_policy: DIALECT-ALLOCATED
framing:           ordered-sequence-v1 (order_semantic=true)
integrity:         xor-parity-rba-v1 (candidate; upgrade to rotated before FROZEN)
lane_mapping:      logical_to_carrier = identity
registry_digest:   computed from lanes at freeze time

--------------------------------------------------------------------------------
I. REFERENCE CODEC
--------------------------------------------------------------------------------
PENDING — CANDIDATE design. The working codec is owed before this Tome is
usable. (Pattern after capsule_reason_evidence_v010.py: frame encode/decode,
BLEND composition, parity, DATA-frame references.)

--------------------------------------------------------------------------------
J. CONFORMANCE RULES
--------------------------------------------------------------------------------
U1  every turn is a linked pair: exact-utterance frame + interpretation frame.
U2  the exact utterance is QUOTE-forced; it exerts no governing force.
U3  turn order (seq) is semantic; out-of-order is ambiguous-composition.
U4  the interpretation frame must REFERS_TO its exact-utterance frame.
U5  the exact utterance must never be replaced by its interpretation.
U6  HEAD carries nonzero evidence; evidence 07 ASSUMED never relabeled.
U7  unknown unit/role/evidence/force refused; empty frame invalid.

--------------------------------------------------------------------------------
K. SELF-TESTS
--------------------------------------------------------------------------------
PENDING with the codec (must include: one multi-clause turn round-trip;
one turn where interpretation differs from literal text; refusal on unlinked
interpretation; refusal on replaced utterance).

--------------------------------------------------------------------------------
L. EXAMPLES (design)
--------------------------------------------------------------------------------
Source:  User: "Please open the report, but do not delete the original file."
Frame 1 (exact):   speaker=user, text=<verbatim>, force=QUOTE
Frame 2 (interp):  clause1 predicate=open object=report intent=request
                   clause2 predicate=delete object=original_file force=NEVER
                   evidence=DIRECT
                   link REFERS_TO -> frame 1

--------------------------------------------------------------------------------
M. INVALID VECTORS (to be refused by the codec)
--------------------------------------------------------------------------------
interpretation frame with no exact-utterance link
exact utterance overwritten by its interpretation
out-of-order turn sequence
HEAD with inherited evidence

--------------------------------------------------------------------------------
N. ROUND-TRIP REPORT
--------------------------------------------------------------------------------
UNMEASURED — codec pending. This section must be filled with real numbers
before the Tome advances past CANDIDATE.

--------------------------------------------------------------------------------
O. MEASUREMENT
--------------------------------------------------------------------------------
UNMEASURED. Owed: corpus of real user turns; round_trip_success; exact-vs-
interpretation agreement; unknown_rate; records_per_turn.

--------------------------------------------------------------------------------
P. KNOWN BENDS
--------------------------------------------------------------------------------
B1 STRUCTURAL  reference codec not yet written; this is a design capsule.
B2 UNMEASURED  all measurements owed; no corpus yet.
B3 STRUCTURAL  candidate integrity (xor-parity) leaves G uncovered; upgrade to
               rotated-parity-rgba-v1 before FROZEN.
B4 STRUCTURAL  clause/intent extraction from free text is an interpretation
               step; the Book stores the result, it does not guarantee the
               interpretation was correct (evidence channel carries that).

--------------------------------------------------------------------------------
Q. BOOT DECLARATION + LINEAGE
--------------------------------------------------------------------------------
category: COMMUNICATION
book_id: user-language    book_edition: 0.1
dialect_id: english-user-chat    dialect_edition: 0.1
framing_id: ordered-sequence-v1
integrity_id: xor-parity-rba-v1   (upgrade path: rotated-parity-rgba-v1)
Lineage: fresh CREATE for the first corpus. Next step: write the reference
codec + a real conversation corpus, then measure. Gate to FROZEN: codec,
corpus, rotated parity, real round-trip report.
================================================================================
