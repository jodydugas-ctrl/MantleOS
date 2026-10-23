# Changelog

All notable release-level changes are documented here.

## [Unreleased]

### Added — Body-governed memory consolidation

- Added scheduled retrospective cognition ("sleep") that revisits bounded prior experience and appends later interpretation without rewriting original memory.
- Consolidation remains inferred, Body-validated, append-only, and unable to promote facts; failed/refused passes do not advance the consolidation cursor.
- Added executable consolidation authority, history-integrity, retry, and idempotency proofs.

### Documentation and repository hygiene

- Reconciled maintained README and guide examples with target-bound hatch/graft
  authorization, resident protocol v2 commands, current scanner coverage, and the
  2.0.0rc1 security posture.
- Clarified that Grimoire v0.10 is the adopted profile for new tissue, v0.9 remains a
  frozen compatibility profile, and the unversioned edition file is a v0.9 mirror.
- Made the independent v0.10 verifier refuse legacy editions before applying incompatible
  parity and ordering rules.

### Changed - de-identification and distribution hygiene

- Removed residual personal data from the distribution: the assimilation census
  (`examples/hermes-mantle-addon/docs/assimilation/host_census.json`) carried an
  email-shaped file-hash key (now a neutral filename with refreshed digests), and
  the pirate spore's VCW payload `identity.author` still carried the operator's
  name (regenerated from canonical state with collective attribution, integrity
  verified). Complements the earlier repo-wide de-identification pass (PR #47).

### Added - MantleOS 2.0.0rc1 platform consolidation

- Added the canonical resident protocol v2 command runtime, grounded claim/evidence
  contracts, typed fusion authorization, Body action proofs, and deterministic
  provider fallback behavior.
- Expanded read-only assimilation with coverage states, native C/C++ and Qt scanning,
  CMake/UI/QRC topology, Rust fallback scanning, and explicit parser-gap evidence.
- Added target-bound one-shot lifecycle authorization for external hatch and graft,
  same-parent staging journals, symlink-escape refusal, Stage-1 verification, and
  atomic promotion, plus deterministic resume/quarantine and preserved rebind.
- Added safe inert spore inspection and Mantle 2 migration guidance while preserving
  independently minted genesis keys and separating integrity from activation authority.
- Added receipt-backed energy ceilings, bounded disabled/fake resource-offer adapters,
  visible face attestations, optional non-authorizing lineage attestations, and immutable
  ancestor queries.
- Added Windows contract CI, wheel/sdist build and clean-install smoke, artifact manifests,
  and tracked-content credential/private-path scanning.
- Migrated maintained NotepadNext and Organize.AppAI candidates to the shared resident
  contracts while preserving every historical resident and receipt.

### Breaking changes

- `mantle-germ-v2` is the only germ schema accepted for Mantle 2 activation. Legacy germs,
  spores, and residents remain inspectable and must use the explicit inert `migrate-*`
  commands before activation or certification.
- Maintained residents must declare `mantle-resident-v2`; legacy command/event dialects
  are refused by Mantle 2 certification.

### Changed — faster certification evidence paths

- Accelerated the canonical standard-library SPORE PNG reader without changing RGBA bytes,
  geometry, corruption refusals, or the Pillow-independent self-hosting boundary. Added exact
  filter reconstruction and malformed-row invariants plus targeted decoder mutants.
- Grimoire v0.10 invariant rows now share one immutable, source-bound conformance fixture per
  suite execution while retaining every named verdict and the independent verifier comparison.
- Closed-world strict certification runs the complete invariant suite once and binds its ordered
  results to a fresh run nonce and tracked-source digest between separate Stage-1 and Stage-2 row
  verdicts. Standalone stage commands remain complete by default.
- Added a bounded, read-only benchmark harness whose append-only results are explicitly
  non-authoritative performance evidence.

### Added — Grimoire v0.10 adoption for new tissue

- Added concurrent v0.9 compatibility and v0.10 Grimoire drivers, explicit profile
  persistence, profile-aware new spores, and an operator-authorized Body-owned adoption
  receipt. Existing v0.9 carriers are never reinterpreted; research and adoption remain
  separate authority events.

### Added — Body-owned rolling context

- Added opt-in `rolling-prefix` context with a private VCW ledger, canonical
  model-visible envelopes, exact request hashes, commit-last source cursors, provider
  usage/cache receipts, conservative token budgeting, deterministic generation rollover,
  multi-lane keys, and corruption recovery. The historical snapshot prompt remains the
  default and its bytes are unchanged.
- Added explicit context-band migration, optional structured `ModelRequest` /
  `ModelResponse` transport support behind the existing `model(prompt) -> text` contract,
  focused unit tests, nine executable `CONTEXT-*` invariants, tamper proofs, and the
  Rolling Context guide.

### Security — memory guarantees clarified

- Separated **history integrity** from **insertion provenance** throughout the VCW
  documentation. Entry hashes and generation seals detect rewritten history; they do not
  authenticate which in-process organ inserted a new valid row. This is a documented
  trust-boundary decision, not a new storage format or behavior change.

### Changed — documentation reorganization (no code changes; historical 1.4.0 entry)

- **Two on-ramps for specialists.** Added `AGENTS.md` at the repo root — an orientation
  file for AI agents that explains the two jobs the biological framework does (it draws a
  boundary you can see, and every organ name maps to real work) and how to use the
  Grimoire. Added `documents/Mantle_for_Engineers.md` — a systems-language translation
  layer (trust boundary, storage semantics, verification gates, the model-integration
  contract, and a full term-mapping table) for engineers and AI specialists who want the
  architecture before the metaphor.
- **The README is the primer.** Folded `documents/PRIMER.md` into `README.md` and removed
  it, so there is one biological entry document with only the two specialized doors
  branching off it. The README now carries the plain-language on-ramp, the creed and
  cosmology, the organism lens, the ontology glossary, and the six principles.
- **Removed README redundancy.** The reproduction mechanics (cache-ghost and its four
  laws, the per-module facet map, cache receipts), the applet-body commands and bands, and
  the detailed Path A/B build procedure now point to their canonical homes
  (`documents/REPRODUCTION.md`, `documents/Mantle_Applet_Bodies.md`,
  `documents/ARCHITECTURE.md`) instead of duplicating them. The organic wording is
  unchanged.

## [1.4.0] — 2026-07-23

### Changed — the streamlining release: one artifact, one door, one reading order

- **The spore is THE artifact.** A spore PNG may now carry a **germ** — the complete
  AppAI build document (the former egg schema) — plus a build note any coding agent can
  read to grow the app with or without Mantle installed. `mantle spore pack` packs a
  germ into a spore; `examples/spores/` ships generated germ spores.
- **One birth door.** `mantle hatch <spore.png|germ.json>` is the single birth command;
  `hatch-spore` is absorbed. `egg.py` folded into the hatchery
  (`validate_germ`/`load_germ`; both `mantle-germ-v1` and legacy `mantle-egg-v1`
  formats are accepted). `hatch_from_spore` moved beside the incubator it always called.
- **Assimilation emits a spore.** `mantle assimilate <host> --spore=out.png` condenses
  the read-only dissection into the host's germ spore. A graft is a spore aimed at a
  host: `load_graft` accepts graft-germ spores.
- **Rebirth simplified.** One heirloom law (carried or immune-logged, never silent), one
  carry rule for both heirloom bands; `vault.py` folded into the Reproduction organ
  module that always owned the tissue. On-disk formats unchanged; ancestors stay
  readable.
- **Docs consolidated.** One reading order (README → `mantle teach`); the README
  absorbs the Primer, Doctrine, Organism Lens, and Positioning;
  ARCHITECTURE.md absorbs the architecture note and the Part 1/2 build+audit
  narratives; REPRODUCTION.md is the canonical reproduction + rebirth doctrine; the
  VCW guide absorbs the anatomical atlas and compliance tiers. The Grimoire gained a
  scope banner (§7/§9 are the Mantle-binding sections).
- **Counts are derived, never hardcoded.** The doctor's docs-vs-code gate now fails if
  any document hardcodes an invariant count; `mantle prove` prints the live count.
- **Legacy imports fail visibly.** The doctor now rejects Python imports of the removed
  `mantle.egg` module; callers load germs through `mantle.hatchery`.
- **Phenotype example follows maintained surfaces.** The walkthrough loads its germ through
  the hatchery and wears the Notepad AppAI as its second face.
- **CLI dispatch is table-driven**; underscore aliases are derived.

### Removed

- The vendored duplicate of the entire repository inside the Hermes addon
  (`examples/hermes-mantle-addon/vendor/`, 9.9 MB). The addon loads the runtime from
  `MANTLE_ADDON_RUNTIME_ROOT`, its install-time `runtime/` copy, or the repo checkout.
- The self-referential optimization-audit layer: `optimize_audit.py`,
  `documents/refinement/`, and 21 unregistered meta-invariant functions.
- Scratch notes (`New_Commandments.txt`), the NotepadNext lifecycle zip (superseded by
  `assimilate --spore`), and fourteen merged documentation files.
- The standalone Reference Agent and Spreadsheet Agent browser demos, their duplicate
  `egg.author` / `egg.hatch` primitives, and their dedicated smoke test.

### Added

- Invariant **SPORE-3** (germ round trip): germ → spore → hatch → certified body whose
  vault returns the same germ, with the key minted, never derived.
- `assimilator.emit_spore`, `spore.pack_germ`, and the unified `hatchery.hatch`.
- Plug-and-play Hermes addon installer and `/mind <prompt>` command for one explicit, unscheduled
  AppAI cognition pulse through Hermes's active host LLM.
- VCW persistence for content-withheld interactive MIND markers, hash-only request/response traces,
  and redacted usage receipts without storing the raw user prompt or model answer.

### Security

- All standing laws re-proven unchanged: keys minted at birth (never derived from a
  spore), foreign conversation ingested as INFERRED through Senses, the Stage-1 gate
  mandatory on every birth path, do-no-harm census on every graft, and the heirloom
  carry across rebirth.
- Interactive MIND contact remains transient and user-directed; it does not attach the Brain, start
  autonomous cognition, or bypass independent production-fusion authority.
- Echoed prompts are returned to the requesting surface but never written to any VCW band or
  resident artifact.
- VCW layer decoding now verifies PNG chunk CRCs, enforces the fixed layer profile, bounds compressed
  and expanded data, validates embedded layer identity, and rejects malformed or overlapping cube
  topology before allocation.
- Cube checkpoints now use collision-free same-directory stages and sync the staged file, published
  file, and parent directory around atomic replacement; failed saves remove their private stage and
  preserve the previous valid cube.

## [1.3.0] — 2026-07-15

### Added

- Reversible, receipt-backed MIND fusion and authority-free defusion lifecycle.
- Exactly one fixed 600-second cognitive scheduler per fused resident, with separate queued
  nociceptive wakeups.
- Hermes-native cognition through the host-owned `PluginContext.llm` provider/model abstraction.
- Rolling token/cost budgets, one addon dispatch through host-owned fallback/retries, request
  timeouts, outage handling, conservative unknown-usage charging, serialized cognition, and
  redacted usage receipts.
- Distinct Ed25519-authenticated operator and guardian approval verification using verifier-only
  public keys for production fusion.
- Controlled offline attach → heartbeat → defuse → post-defusion Stage-1 acceptance coverage.
- Complete tracked 146-file Mantle OS snapshot in the Hermes addon example.

### Changed

- Observer hooks now drive non-cognitive Body pulses; they cannot accidentally invoke the MIND
  between natural heartbeats.
- Stage-1 and readiness evidence are explicitly separate from production fusion authority.
- Runtime/security certification contains 90 executable invariants. Mutable repository
  optimization ledgers and version snapshots remain advisory tooling instead of blocking organism
  certification.
- Release readiness is separate from deployment activation: the software can be published while
  production fusion remains dormant and fail-closed.

### Security

- Persistence rejects symlink roots, parent components, and destination artifacts while preserving
  owner-only atomic replacement and the addon's trusted descriptor boundary.
- Caller-authored approval JSON cannot authorize fusion without two distinct authenticated,
  target-bound signatures.
- Model receipts exclude prompts, responses, credentials, and raw exception text.
- Reproduction remains disabled and requires a separate future design and authorization.

## [1.0.0] — 2026-06-25

- First stable Mantle OS release: deterministic Body, VCW persistence, Stage-1/Stage-2 gates,
  tamper proofs, and the Grimoire methodology.

[1.3.0]: https://github.com/jodydugas-ctrl/mantle-os/compare/v1.0.0...v1.3.0
[1.0.0]: https://github.com/jodydugas-ctrl/mantle-os/releases/tag/v1.0.0
