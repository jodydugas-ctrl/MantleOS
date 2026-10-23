# KPP protocol, MantleOS testbed and shared implementation

KPP is the independently maintained development protocol. MantleOS is the
creator's experimental testbed for exploring AI embodiment through code. Both
use the same mantleos implementation; the standalone kpp namespace is a facade.
Shared changes originate in KPP and are promoted identically to MantleOS.
Hosting provides no automatic synchronization.

## One Anchor model

The trusted source is `mantleos.anchors`. The only types are `BlackHole`,
`WhiteHole` and `Neutral`. A definition's type and singularity are immutable.
The source-defined singularities are:

| Definition | Type | Singularity |
| --- | --- | --- |
| BlackHole | BlackHole | Receive the declared input. |
| WhiteHole | WhiteHole | Enforce the declared boundary. |
| Neutral | Neutral | Apply the declared relationship. |
| N-RULE-ECONOMY | Neutral | Use as few rules as possible while still covering all needed variables. |

These constants describe meaning, not permission. A model or carried document
may supply contextual attributes; it cannot replace the definition by changing
or rehashing a field. `anchor.application/1` binds those attributes to a trusted
definition. Project/register views and serialized executable Anchor slots are
applications of this same model.

Recipe/3 retains its existing Neutral Anchor binding. Recipe/4 treats the
historical `anchors` field as general measurable obligations and defaults to
`anchor_binding: none`. Validation and the Functional Graph do not invoke the
Anchor model for unbound recipes. Explicit `shared-neutral` binding uses these
same definitions; there is no second Anchor family. `mantleos.kitchen.bind`
retains the complete recipe in `mantle.kpp-binding/1` without approval.

Recipe/4 implementation components record required, preferred or recommendation
choices with selected languages and rationale. Language and Anchor profile are
separate. Declaration, tool availability, executed verification and Baker
acceptance remain distinct. Rust can be declared without an execution backend.
See docs/LANGUAGE-CHOICES.md and the read-only `language-plan` command.

KPP's complete recipe validator, Pantry, workspace, Reflex, testing, GUI evidence,
Chase and Baker-acceptance workflow are implemented in `mantleos.kpp` and ship
in both distributions. Recipe acceptance is an explicit scoped workflow decision.
Passing a test or importing a recipe, graph, manifest or digest supplies no
operator, Baker or host approval. MIND proposals cannot approve themselves.

## CELL, programs and tissue

`mantleos.cells` defines `mantle.cell/2`. A CELL is the smallest unit produced by
its kernel. `chroma.rgb/1` produces one three-channel pixel;
`tape.segment/1` produces one appended record segment with its sequence. These
are kernel representations of one CELL concept, not physical and logical rivals.

`mantleos.tissue` defines `mantle.program/1` and `mantle.tissue/2`. Programs
compose behavior above CELL units. Whole-cartridge structure is
`mantle.anatomy/1`, never a CELL. No fixed organ count or package-per-composition
level rule applies. `mantleos.kpp.cells` and `.tissue` expose the exact same
functions. They do not implement alternate versions.

## Execution and discovery

`mantleos.anchor_language` and its pinned profile sources implement Anchor
execution for both distributions. `EMIT_TEXT/0.2` emits exact literals;
`NOTEPAD_LLM/1.3` requires an explicit JSON command. `AGENTIC/0.2` is a separate
hosted execution profile under the same Anchor model, with explicit host inputs
and capability boundaries. Unsupported profiles and instructions fail explicitly.
Emitted Python is data until a separately authorized host operation runs it.

The SCAN engine is `mantleos.scan`; its native report is `scan.report/1`.
`kpp.static-scan/2` is a derived workflow view retaining native source and graph
pins. KPP's HTML control listing is a supplemental declaration view, explicitly
separate from native syntax coverage. Python, JavaScript, Anchor, data and binary
extraction use the existing canonical adapters. Fidelity/depth selects evidence
views and obligations; it does not strengthen static syntax into runtime proof.
Old unbound `kpp.static-scan/1` evidence must be rescanned.

Code/Qt concurrency uses the same `mantleos.scan.discovery` implementation and
`mantle.parallel-discovery/1` three-file bundle. Qt inventories remain
`kpp.gui-inventory/2`: those declarations and pins are identical in both entry
points. Source drift, unsupported profiles, traversal and budget limits remain
explicit. Inventory, visual comparison, observed behavior, tests and acceptance
are separate evidence states.

## Body, memory, carriers and workflow products

Both distributions include the same deterministic Body, Engram, continuity,
governed evolution/rollback, app authoring, hosted handoff, cartridge and Chroma
implementations. Existing behavior remains usable without a MIND. Memory is
appended with provenance; prior executable tissue remains available for rollback.

KPP's progressive browser workspaces and Reflex/preview transfer operate through
the same canonical `mantleos.kpp` workflow in both builds. A browser checkpoint,
recipe receipt or screenshot is not a Body cartridge or a Chroma identity carrier.
The RGBA screenshot codec and the Chroma RGB tape codec serve distinct formats;
their separation does not create a second Anchor or CELL model. Transport never
transfers approval. Host independence and fresh receiving-host review remain.

## App construction and Chase

`mantleos.kpp.build` supplies the same preview-first build contract, compact
`build-step` packet and bounded host driver in both distributions. Open the first
independently useful Canvas slice while BUILDING, before generating later stages
or packaging the full portable app. Preserve the mounted Body and current user
state as reviewed modules arrive. Recheck the pinned recipe after each refinement
and refine every unmet mandatory obligation and preservation
obligation. A visible app or passing test never supplies Baker acceptance.
Review/budget/blocking stops retain the unresolved requirements and resume point.
The host still owns its real preview tools, typed release and effect permissions.
New Bodies carry the KPP preview resources and expose `python runtime.py kpp`.

## Distribution and future development

From MantleOS, use `python -m mantleos kpp --help`. From the generated standalone
project, `python -m kpp --help` reaches the same implementation. Either build can
also use the normal MantleOS API and CLI. Python 3.11–3.14 and the standard
library are required; a browser is needed for interactive browser products.

`tools/export_kpp.py` exports the canonical package, resources, tests and a small
entry-point facade into a new standalone project. `--check PROJECT` compares
every generated source file against the selected canonical source. The standalone
`tools/verify_shared.py` verifies its pinned shared source and optionally compares
an explicitly selected MantleOS checkout. Hashes detect drift; they do not
authenticate the source owner or authorize execution.

This document is the canonical common systems description. MantleOS's
`docs/kpp.md` and the standalone `SYSTEMS.md` are byte-identical published views
of it. Source and document parity are regression-tested. The standalone project
has its own Git history and contribution process and is the primary place for
ongoing development. Changes to common meaning and implementation must be reviewed
and promoted to MantleOS with matching source. Local export does
not create a GitHub repository, publish source, configure services or change
existing licenses. Component notices and source provenance accompany both builds.


## Recipe-owned organs and source revision evidence

`mantleos.kpp.organs` validates a read-only ownership/dependency projection of the
existing recipe; it adds no Anchor meanings, CELL types or approval registry.
The maintained SCAN engine supplies source observations with explicit coverage
and gaps. Real browser tests separately qualify the Notepad Save behavior profile.
Reviewed replacement and restoration use the existing workspace writer lock,
immutable retained source, source-bound evidence and append-only history. Editor
state remains owned by the deterministic Body. Managed JavaScript is not a sandbox,
and tests, source digests and transport never grant Baker acceptance. The same
implementation and example ship in both projects. See KPP's docs/ORGAN-SAVE.md.

See [artisanal construction](docs/ARTISANAL-CONSTRUCTION.md) for role-neutral Baker responsibility, optional Chase and augmentation evidence.
