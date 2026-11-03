# Compact Anchor design contracts

Describe the smallest set of responsibilities that covers the required variables.
Use existing BlackHole, Neutral and WhiteHole definitions with contextual attributes.
Four applications are examples, not an anatomy requirement. Implementation modules
may expand without multiplying the design responsibilities.

`anchor.design/1` contains schema, id, purpose, applications, flows, state and effects.
Applications are existing `anchor.application/1` values with responsibility attributes.
Flows declare from/to/relationship; state declares id/owner (Neutral); effects declare
id/requester/guard (WhiteHole)/confirmation. Declared structures are checked; omitted
behavior cannot be discovered or certified by this validator.

Recipe/4 may embed `anchor_design`; each required obligation references its applications
through `design_anchors`. Every application needs mandatory coverage. The existing
obligation graph owns tests, preservation and acceptance. Design binding is independent
of recipe shared-neutral binding. Existing recipes and pinned workspaces need no migration.

Run `python -m mantleos kpp design-check --recipe recipes/journal-engram-design.json`
or `design-view` with the same arguments. The kpp facade exposes the same commands.
Readable `.anchor.txt` output is design data, not an executable profile. Translate
freeform documents deliberately and review the structured contract before admission.
Use examples/anchor-design for Journal and Notepad contracts; the complete supplied
Notepad checklist remains alongside its compact structural projection. XP parity is untested.

Journal maps BH-ENCOUNTER to open/submit input validation; N-CONTINUITY to verify,
append_record/_remember/recall and atomic replay bindings; N-HOST to frame preparation,
CheckedActionExecutor, bootstrap and export; WH-INTEGRITY to verification, stale-state,
observation and broker checks. Python executes storage/transport. Qualified Anchor
profiles retain their existing semantics. Design text creates no execution capability.

New journals carry the design independently of the full unchanged PRIMER. Sessions
validate and cache its projection; preparations bind its digest. Older journals remain
readable and explicit export attaches the current default design. Materialized Body
exports preserve ANCHOR-DESIGN.json. A model, digest or transported file grants no authority.

See [cumulative satisfaction](ANCHOR-SATISFACTION.md) for opt-in candidate-bound verification, batch planning and complete design views.
