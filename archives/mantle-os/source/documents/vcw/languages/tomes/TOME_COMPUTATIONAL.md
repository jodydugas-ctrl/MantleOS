================================================================================
TOME: COMPUTATIONAL
BOOK: computational-thought
DIALECT: generic-python
================================================================================

A four-stream VCW language for computational thought — letting an AppAI think
IN PYTHON's structure rather than about Python's spelling. Python is the
renderer target (the phenotype); the stored computation is the memory. This
Tome encodes computation, not Python tokens: `if`, indentation, and punctuation
are NOT the program — IF, CONDITION, GREATER, TRUE_BRANCH, ... ARE.

--------------------------------------------------------------------------------
A. LAYER + SOURCE ANALYSIS
--------------------------------------------------------------------------------
LAYER_ID:     brain-procedures
SUBSTRATE:    cube-band
TISSUE:       brain
SOURCE_CLASS: COMPUTATION

Semantic units: primitive root, structural role, value class, form/arity,
                reference, literal.
Relationships: parent/child (the tree); role to parent; left/right operands;
               condition/branch; tool/argument (via references).
Order: SEMANTIC. Children follow parents in declared preorder; child order
       is semantic.
Data vs roots: names, string literals, integers, floats are DATA — they ride
               DATA frames referenced by REFERENCE roles. Never a permanent
               root per variable name.

--------------------------------------------------------------------------------
B. DECISION
--------------------------------------------------------------------------------
DECISION: REFINE
Justification: the computational-thought specimen (v0.1) already fits this
Tome's lane questions and preorder-tree framing. Refinement (not CREATE):
extend the vocabulary under the specimen's candidate-extension policy —
add BIND, GET, SET, NAME-ref, concrete data-frame handling — and let a corpus
drive root elimination (can X be composed from the others?). Creating a new
Book after the specimen already survives the lane/framing test would be waste.

--------------------------------------------------------------------------------
C. BOOK IDENTITY
--------------------------------------------------------------------------------
book_id:        computational-thought
book_edition:   0.1
dialect_id:     generic-python
dialect_edition: 0.1
category:       COMPUTATION
status:         CANDIDATE

--------------------------------------------------------------------------------
D. LANE CONTRACT
--------------------------------------------------------------------------------
R  what computational primitive is this node?
G  what role does it play relative to its parent?
B  what value / reference class is it?
A  what structural form / arity does it have?

Lane test: one sentence per lane; every registry value answers its lane; no
value answers a different lane; each decodes without undeclared context.

--------------------------------------------------------------------------------
E. REGISTRIES (from the specimen; extension candidates marked "+")
--------------------------------------------------------------------------------
R — COMPUTATIONAL ROOT (frozen for v0.1 self-test)
    01 INPUT   02 ZERO   03 IF   04 GREATER   05 MULTIPLY   06 SUBTRACT
    + 0b NAME   0c CONSTANT   0d BIND   0e GET   0f SET
    + 10 ADD  11 DIVIDE  12 MODULO  13 POWER  14 NEGATE
    + 20 EQUAL  21 NOT_EQUAL  22 LESS  23 LESS_EQUAL  24 GREATER_EQUAL  25 NOT
    + 30 AND  31 OR
    + 40 SEQUENCE  41 CALL  42 RETURN  43 FUNCTION  44 EACH  45 REPEAT
    + 50 COLLECTION  51 INDEX  52 ATTRIBUTE
    + 60 TRY  61 RAISE  62 CATCH
    (candidates are not proven primitives until decomposition tests pass)

G — STRUCTURAL ROLE (frozen)
    01 ROOT   02 CONDITION   03 TRUE_BRANCH   04 FALSE_BRANCH   05 LEFT   06 RIGHT
    + 07 TARGET  08 VALUE  09 ARGUMENT  0a FUNCTION  0b BODY  0c ITEM
    + 0d ITERABLE  0e TEST  0f RESULT  10 NAME_ROLE  11 INDEX_ROLE
    + 12 ATTRIBUTE_ROLE  13 EXCEPTION  14 HANDLER  15 DEFAULT
    Roles are tree relationships, NOT verbs.

B — VALUE CLASS (frozen)
    01 VALUE   02 PREDICATE   03 CONTROL   04 OPERATION
    + 05 REFERENCE  06 LITERAL  07 FUNCTION_VALUE  08 COLLECTION_VALUE
    + 09 ITERATOR  0a EXCEPTION_VALUE  0b TYPE_VALUE  0c EFFECT

A — FORM / ARITY (frozen)
    01 LEAF (0 children)   02 BINARY (2)   03 TERNARY (3)
    + 04 UNARY   05 VARIADIC   06 BLOCK   07 REFERENCE
    A deployment must verify physically usable Alpha values before freezing
    (carrier lane-mapping).

--------------------------------------------------------------------------------
F. COMPOSITION + FRAMING
--------------------------------------------------------------------------------
framing_id:   preorder-tree-v1
One program-expression is a PREORDER TREE RUN:
  1. first semantic record is the root;
  2. each record declares its arity in A;
  3. children immediately follow the parent in preorder;
  4. G declares the child's role relative to its parent;
  5. the run ends at the VCW frame boundary;
  6. the decoder consumes exactly the child count implied recursively by A;
  7. extra trailing records are invalid.
Order is semantic in this Book.

--------------------------------------------------------------------------------
G. CANONICAL DATA MODEL
--------------------------------------------------------------------------------
node := { "root": "IF",                  # computational root (R)
          "role": "ROOT",                # role to parent (G)
          "value_class": "CONTROL",      # B
          "form": "TERNARY",             # A (arity=3)
          "children": [ node, ... ],     # preorder
          "data_ref": "sha256:<hex>" | None }   # names/literals -> DATA frame
program := node  # a single rooted tree per frame

--------------------------------------------------------------------------------
H. MANIFEST + DIGESTS
--------------------------------------------------------------------------------
schema:            vcw-book-v1
category:          COMPUTATION
allocation_policy: DIALECT-ALLOCATED
framing:           preorder-tree-v1 (order_semantic=true)
integrity:         xor-parity-rba-v1 (candidate; upgrade to rotated before FROZEN)
lane_mapping:      logical_to_carrier = identity (alpha = form/arity)
registry_digest:   computed from lanes at freeze time

--------------------------------------------------------------------------------
I. REFERENCE CODEC
--------------------------------------------------------------------------------
PENDING — CANDIDATE design. Owed: AST -> computational tree -> RGBA -> tree ->
AST round-trip (stdlib, pattern after the specimen + scaffold). Must refuse
unsupported AST nodes rather than invent.

--------------------------------------------------------------------------------
J. CONFORMANCE RULES
--------------------------------------------------------------------------------
C1  parse RGBA byte order (hex rrggbbaa).
C2  first record of a frame is the root; root role = ROOT.
C3  each node's A declares its arity; children follow in preorder.
C4  decoder consumes exactly arity-impled children; truncated structure refused.
C5  trailing records after a complete tree are invalid.
C6  names/literals ride DATA frames via REFERENCE; never inline bytes.
C7  unknown root/role/value-class/form refused (ENCODING REFUSED: <code>).
C8  unsupported AST nodes are refused, never approximated.
C9  parity verified at frame close (rotated recommended).

--------------------------------------------------------------------------------
K. SELF-TESTS (specimen vector — rotate parity to match this Tome's member)
--------------------------------------------------------------------------------
Canonical program:  lambda x: x * x if x > 0 else 0 - x
Structural round-trip: PASS (specimen v0.1)
Behavior pass on integers -100..100 (specimen proof, parity method per edition)
Full RGBA run: rerun after codec is built with the declared parity member.

--------------------------------------------------------------------------------
L. EXAMPLES
--------------------------------------------------------------------------------
Source:  def absolute(x): return 0 - x if x < 0 else x
Tree:    IF [CONTROL, TERNARY]
           CONDITION: GREATER [PREDICATE, BINARY] ( x, 0 )
           TRUE_BRANCH: SUBTRACT [OPERATION, BINARY] ( 0, x )
           FALSE_BRANCH: INPUT [VALUE, LEAF] ( x )
Names/literals (x, 0) -> DATA frames referenced; roots are computational.

--------------------------------------------------------------------------------
M. INVALID VECTORS (to be refused by the codec)
--------------------------------------------------------------------------------
unknown arity value            -> unknown-value
BINARY node with one child     -> truncated-structure
complete tree + trailing bytes -> trailing-records
unsupported AST node           -> unrepresentable
parity mismatch                -> unknown-value

--------------------------------------------------------------------------------
N. ROUND-TRIP REPORT
--------------------------------------------------------------------------------
UNMEASURED for the full codec. Owed: AST equality + behavioral equality on a
corpus, then unseen/adversarial splits.

--------------------------------------------------------------------------------
O. MEASUREMENT
--------------------------------------------------------------------------------
UNMEASURED. Owed: new_root_rate, collision_count, records_per_ast_node,
single_use_roots, unused_roots, unsupported_nodes on TRAIN/UNSEEN/ADVERSARIAL.

--------------------------------------------------------------------------------
P. KNOWN BENDS
--------------------------------------------------------------------------------
B1 STRUCTURAL  reference codec not yet written; this is a design capsule.
B2 UNMEASURED  all measurements owed; specimen covered one program only.
B3 STRUCTURAL  candidate integrity (xor-parity) leaves G uncovered; upgrade to
               rotated-parity-rgba-v1 before FROZEN.
B4 STRUCTURAL  instance data rides DATA frames; full content-address resolution
               in-pixel is the next refinement.
B5 STRUCTURAL  candidate roots may be decomposable; corpus drives elimination
               before they freeze.

--------------------------------------------------------------------------------
Q. BOOT DECLARATION + LINEAGE
--------------------------------------------------------------------------------
category: COMPUTATION
book_id: computational-thought    book_edition: 0.1
dialect_id: generic-python        dialect_edition: 0.1
framing_id: preorder-tree-v1
integrity_id: xor-parity-rba-v1   (upgrade path: rotated-parity-rgba-v1)
Lineage: REFINE of the computational-thought v0.1 specimen. Gate to FROZEN:
codec, Python-AST corpus, rotated parity, real round-trip report, root
elimination tests.
================================================================================
