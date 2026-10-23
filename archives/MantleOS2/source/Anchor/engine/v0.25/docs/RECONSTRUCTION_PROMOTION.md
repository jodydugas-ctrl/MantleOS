# SCAN v0.19 Reconstruction Promotion Contract

M5 separates **semantic generation** from **semantic authority**.

A human or LLM may propose reconstruction meaning. SCAN does not automatically trust that proposal. The mechanical promotion gate validates the proposal against the canonical evidence graph before any behavior or reconstruction anchor is adopted.

## Proposal schema

Use `scan-reconstruction-proposal/0.1`.

Promotable object types are:

- `INTERPRETATION`
- `BEHAVIOR`
- `ARTERY`
- `NERVE`
- `CAPABILITY`
- `RECONSTRUCTION_ANCHOR`

Every promoted semantic claim must have a positive proof path to a first-class `EVIDENCE` object. A reconstruction anchor must additionally receive `supports_anchor` from a `BEHAVIOR`, `ARTERY`, `NERVE`, or `CAPABILITY`.

A behavior contract must include non-empty attributes:

- `trigger`
- `observable_response`
- `uncertainty`

A reconstruction anchor must include:

- `property`
- `fidelity_test`
- `uncertainty`

Other behavior-contract fields such as preconditions, state transition, persistence effect, cancellation/error behavior, and feedback should be supplied whenever the evidence supports them.

## Coverage discipline

A proposal may never use semantic prose to increase certainty.

A `MAPPED` anchor is rejected when its proof walk contains `PARTIAL`, `BLOCKED`, or `UNKNOWN` support. A `MAPPED` anchor is also rejected when a `contradicts` relation is visible on the proof path.

A `PARTIAL` anchor may preserve a contradiction. The contradiction remains present in `reconstruction_contract.json`; it is not reconciled away.

## Commands

```text
scan-body validate-reconstruction <db> <proposal.json> [--out validation.json]
scan-body promote-reconstruction <db> <proposal.json> --out-dir <scan-output>
scan-body reconstruction-contract <db> --out reconstruction_contract.json
```

Validation does not mutate the database. Promotion is atomic at the semantic-bundle level.

## Reconstruction contract

`reconstruction_contract.json` is a projection of canonical graph objects. For every promoted anchor it preserves:

- stable anchor identity;
- declared coverage;
- property and fidelity test;
- supporting semantic object IDs;
- reached evidence IDs;
- reached source-file IDs;
- visible contradictions;
- the current completeness vector.

A consuming agent should still use `why <RA-ID>` and `impact <EV-ID>` for high-consequence decisions.

## Sealed lineage

Never mutate an already sealed certification in order to add semantics.

Use:

```text
scan-body certify-reconstruction <package-root> <parent-cert-dir> <proposal.json> \
  --out <child-cert-dir> [--bundle child.zip]
```

The parent is verified first. The child records SHA-256 identities of the parent receipt and certification manifest, promotes the validated proposal in a copied scan database, refreshes projections, and seals a new handoff.

The lineage rule is:

**mechanical evidence remains the parent authority; semantic promotion is a traceable child layer.**
