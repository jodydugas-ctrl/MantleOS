# The Mantle OS documents corpus

Single documentation root. Everything user-, contributor-, and agent-facing lives here.
Never create a new documentation root elsewhere (`doc/`, `docs/`, `document/`,
`documentation/`, ...) — add to this corpus instead.

## Reading order

1. `README.md` (repo root) — the primer, in the organic language.
2. `Mantle_for_Engineers.md` — the systems-language translation layer (trust boundary,
   storage semantics, verification gates, model-integration contract).
3. `ARCHITECTURE.md` — the shape and the Phase-1/Phase-2 build path.
4. `FIELD_GUIDE.md` — the runnable manual (`python -m mantle teach` runs most of it live).
5. `AGENTS.md` (repo root) — orientation for AI agents, including the Grimoire how-to.

## Families

| Path | Contents |
| --- | --- |
| `grimoire/` | the doctrine — family index (`README.md`), `editions/`, `residency/`, `semantic-memory/` |
| `guides/` | VCW · audit · lifecycle · assimilation · visual guides |
| `research/` | bounded research charter, receipts, ADRs |
| `assets/` | diagrams |
| `mantle2/` | MantleOS 2.0 release-closure records (matrix · migration · readiness · friction ledger) |

## The Grimoire

The Grimoire is the doctrine the organism operates through — a software profile on the VCW
substrate, not a separate runtime. Agents and operators:

1. Start at [`grimoire/README.md`](grimoire/README.md) — the family index.
2. Select an edition there before loading it (new tissue: `grimoire-v0.10`; `v0.9` remains
   frozen compatibility).
3. Load by section; a partial load must say which sections are absent. Never fill missing
   Grimoire law from memory.
