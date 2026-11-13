# Anchor + Gate Economy — Fidelity 9 preservation decision

**Decision:** Do not add Anchor #10. Do not add Gate #20. Keep every pre-existing truth and reconfigure the 19 condition entries into **nine proposed independent Gate families**. The original 19 IDs remain as detailed condition *clauses* in `LOGICAL-CONTRACT.json` and every clause has exactly one primary Gate-family owner. Actions can pass through multiple families. The family counts are an engineering proposal, not an adopted KPP schema or mathematical optimum.

## Revised project economy rule

> Use the **fewest independently necessary Anchors AND Gates** that completely specify required input, state, transitions, ownership, effects, failures, observable outputs, and preservation. Before creating a new Anchor or Gate, analyze and, where appropriate, reconfigure the complete existing set. Never reduce the count by hiding a distinct truth, collapsing independent effect authority, or weakening a testable invariant.

An Anchor application carries a distinct responsibility; a Gate family carries an independently enforceable constraint. They are **many-to-many**: a Gate can refer to multiple AnchorApplications and an Anchor can participate in multiple Gates. A command's routing/transition clause is not automatically a new independent Gate. A Gate family is not a fourth Anchor type. WhiteHole remains the canonical runtime/build boundary role where specified.

**Canonical immutability:** KPP's source-defined `N-RULE-ECONOMY` singularity currently reads `Use as few rules as possible while still covering all needed variables.` It must not be silently changed in the pinned framework or forged by application metadata. The rule above is a proposed project-level optimization interpretation. To make it canonical, submit an explicit versioned KPP change, followed by review and MantleOS source parity checks. This artifact modifies **no canonical source file**.

## Consolidation result

| Gate family (candidate) | Primary coverage of prior condition clauses | Independent reason to remain separate |
| --- | --- | --- |
| G-ADMISSION | read, select-all | Reject malformed or undeclared commands before any state or effect |
| G-COMMIT | edit, insert, delete | Sole authoritative document mutation and revision/no-op invariants |
| G-HISTORY | undo, redo | Stack freshness, backward/forward invariants and edit replay |
| G-SESSION | new | Dirty-discard confirmation, baseline/history lifecycle |
| G-FILE-EFFECT | open, save, save-as | Host file read/write, conflict, association and verification boundary |
| G-CLIPBOARD-EFFECT | copy, cut, paste | Clipboard host read/write ordering before guarded edits |
| G-SEARCH | find, replace-one, replace-all | Literal search, selected match and atomic replace-all |
| G-UI-PROJECTION | UI-projection | UI projection must never own duplicate document truth |
| G-BUILD-CONFORMANCE | candidate-review | Offline build preservation and unskipped regression evidence |

Every runtime command also participates in G-ADMISSION; other family membership is defined in `GATE-ECONOMY.json`. The table gives each family’s *primary existing clause ownership*; it does **not** imply, for example, that file commands bypass admission or history binding.

### Why not fewer or more?

- **19 standalone gates:** 17 primarily mirror verbs rather than distinct failure domains; unnecessary conceptual duplication.
- **One monolithic gate:** Compact count, but obscures independently testable ownership/effect/failure boundaries and encourages superficial "valid" claims.
- **Nine candidates:** Distinct fault domains and evidence obligations remain independently testable while all 19 clause IDs survive. A future Scan/optimization review may discover a defensible grouping with fewer families; there is no claim of proven global minimum.
- **Tenth Anchor:** No uncovered state owner, ingress, relationship, or WhiteHole boundary was observed; adding one would violate the revised economy objective.

## Preservation properties

- Nine named AnchorApplications unchanged; original eight runtime module files and the ninth offline gate code unchanged.
- Original 17 action routes, exact payload requirements, 19 clauses and 27 draft recipe obligations retained.
- 13 state owner entries and four guarded effect categories retained.
- 32 expected stimulus-response scenarios retained and exercised by a **separate** logical reference interpreter, without importing existing Notepad implementation modules.
- Original 218 suite checks retained, with 14 additional reference/shell tests in the new prototype.

## Scope of evidence

Static coverage and a deterministic independent interpreter can disprove many omissions. They do not prove that independent LLMs, including intended frontier-model interpreters, will reliably interpret the rules, that a browser download succeeded on disk, or that the virtual file/clipboard profile matches real host behavior. Those are separate trials, and Baker acceptance plus formal KPP satisfaction remain pending.
