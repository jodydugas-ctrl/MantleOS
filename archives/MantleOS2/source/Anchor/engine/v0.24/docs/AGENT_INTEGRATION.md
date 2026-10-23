# SCAN v0.23 Agent Integration Contract

SCAN is designed to be usable as an evidence-producing component inside a larger agent without making the LLM the scanner.

## Trust boundary

The consuming agent should treat the sealed SCAN directory as **evidence substrate**, not as authority to invent missing facts.

A certification receipt has two distinct questions:

1. **Mechanical integrity:** did the SCAN package, canonical database, projections, integrity audit, and required queries pass? This is the top-level `state`.
2. **Coverage:** what regions are MAPPED, PARTIAL, BLOCKED, UNKNOWN, or NOT_APPLICABLE? This remains a vector and is never collapsed into a claim of complete understanding.

Therefore:

```text
receipt.state == PASS
```

means *the evidence handoff is mechanically trustworthy as emitted*.

It does **not** mean:

```text
all specimen behavior is known
all human surfaces are closed
all NEST abilities are proven
all reconstruction anchors are ready
```

## Recommended consuming-agent rule

A downstream agent should only assert a capability or reconstruction requirement when it can point to canonical SCAN object IDs and evidence/proof paths. When a requested answer crosses a PARTIAL/BLOCKED/UNKNOWN region, the agent should preserve that uncertainty or request a deeper scan rather than filling the gap from plausibility.

For provider-acquired specimens, prefer `certify-manifest` so repository/commit/tree and byte-acquisition provenance remain part of the sealed receipt instead of being flattened into local-path identity.

Before acting on a received handoff:

```bash
scan-body verify-certification <certification-directory>
```

Then inspect at minimum:

- `certification_receipt.json`
- `scan/completeness_vector.json`
- `scan/integrity_report.json`
- `scan/surface_closure.json`
- `scan/effect_closure.json`
- `scan/nest_capability_map.json`
- `scan/evidence_graph.json`

Use `why` to prove a selected semantic object and `impact` to determine what depends on evidence that becomes invalid.

## Non-destructive boundary

`certify` scans a local specimen read-only using the ordinary SCAN path. It creates scanner-owned database/projection/receipt artifacts outside the specimen. The certification bundle contains those derived artifacts, not a copy of the specimen source.

Runtime experimentation, instrumentation, builds, stimulation, or mutation remain separately authorized SCAN modes and are not implied by certification.

## Agent failure semantics

The downstream agent should distinguish:

- certification `FAIL`: do not trust the handoff bytes as a valid SCAN evidence package;
- certification `PASS` + coverage `PARTIAL`: evidence is valid but incomplete;
- explicit parser/acquisition gap: do not convert it to source absence;
- NEST potential capability: do not promote it to BODY ability;
- zero-row mechanical query: valid negative result for that query on that evidence body, not universal proof of absence outside covered regions.


## M5 reconstruction-aware handoffs (v0.19)

A consuming or collaborating LLM may propose semantic meaning, behavior contracts, capabilities, arteries, nerves, and reconstruction anchors. It does **not** write those claims directly into the canonical graph. The proposal crosses a deterministic promotion gate.

Use:

```bash
scan-body validate-reconstruction scan_index.sqlite proposal.json
scan-body promote-reconstruction scan_index.sqlite proposal.json --out-dir <scan-output>
```

A promotable `RECONSTRUCTION_ANCHOR` must:

- have a positive proof path to first-class evidence;
- be supported through `supports_anchor` by a typed behavior/artery/nerve/capability object;
- include a testable `property`, `fidelity_test`, and explicit `uncertainty`;
- not claim `MAPPED` if any proof dependency is `PARTIAL`, `BLOCKED`, or `UNKNOWN`;
- not claim `MAPPED` while a contradiction is visible on its proof path.

Promoted behaviors must include at least `trigger`, `observable_response`, and `uncertainty`. Rejected proposals leave the canonical graph unchanged.

`reconstruction_contract.json` is a projection, not a new authority. The downstream agent should use the IDs in that file with `why` and `impact` whenever a reconstruction decision matters.

### Sealed lineage

To add a validated semantic layer without altering a sealed mechanical handoff:

```bash
scan-body certify-reconstruction <package-root> <parent-cert-dir> proposal.json \
  --out <derived-cert-dir> [--bundle <derived.zip>]
```

The command verifies the parent first, copies its scan into a new derived handoff, promotes the proposal only if M5 validation passes, refreshes canonical projections, and seals a new certification. The child receipt stores SHA-256 identities for the parent receipt and certification manifest.

This means the agent can reason across a chain:

```text
immutable mechanical evidence -> gated semantic contract -> reconstruction implementation
```

without confusing any later interpretation with the original measured evidence. Read-only SCAN inspection commands use SQLite immutable mode so inspecting a sealed parent does not mutate its database bytes.


## M6A blind reconstruction trials (v0.20)

For reconstruction experiments, do not hand a coding agent the reconstruction certification directly. Split it first:

```text
scan-body prepare-reconstruction-trial <reconstruction-cert-dir> \
  --challenge-out <public-dir> --evaluator-out <private-dir>
```

Only the public challenge belongs in the coding agent context. The parent certification and private evaluator stay outside that context. The public package contains no original source bytes, source excerpts, canonical database, or original source paths. It does contain the source-free mechanical requirements the agent will be scored against—surface text/type, binding/effect closure, and MAPPED terminal effect/capability signatures—so blindness does not become an information-withholding trick.

After the agent creates a candidate and a challenge-bound source-isolation submission declaration, score it mechanically:

```text
scan-body score-reconstruction-trial <package-root> <private-evaluator-dir> <candidate-dir> submission.json --out <trial-dir>
```

The candidate is rescanned. SCAN compares recoverable human-surface and effect signatures rather than source similarity. Every mismatch carries an attribution domain so the orchestrating agent can decide whether to revise the reconstruction, deepen the source scan, repair the semantic contract, or improve SCAN itself.

The trial remains epistemically asymmetric: `RECONSTRUCTION_AGENT` requires strong source support and adequate candidate scan coverage. Source uncertainty and candidate scanner uncertainty remain explicit instead of being folded into a single failure score.

`fidelity_score` is convenience only. Per-anchor state, attribution, the source completeness vector, and the sealed trial receipt are authoritative.

External source isolation is only as strong as the surrounding harness. The challenge packaging itself is mechanically source-free; an agent declaration marked `DECLARED_ONLY` is not equivalent to a network/filesystem sandbox.
