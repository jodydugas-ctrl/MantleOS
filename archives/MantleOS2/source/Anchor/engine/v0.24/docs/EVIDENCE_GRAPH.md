# SCAN Evidence Graph Contract v0.2

## Authority

`scan_index.sqlite` is the canonical scan database. JSON and Markdown outputs are projections or interchange forms of the same identities.

## Core object classes

- `SPECIMEN`
- `FILE`
- `EVIDENCE`
- `ANATOMICAL_OBJECT`
- `GRAPH_RELATION`
- `FINDING`
- `BEHAVIOR`
- `ARTERY`
- `NERVE`
- `CAPABILITY`
- `INTERPRETATION`
- `RECONSTRUCTION_ANCHOR`

New classes may be added without erasing old evidence.

## Semantic relation vocabulary

Overlay-facing semantic relations use a typed vocabulary. v0.2 includes:

- `contains`
- `contains_evidence`
- `supports`
- `derived_from`
- `contradicts`
- `enters`
- `observed_by`
- `requires`
- `supports_anchor`
- `source_of`
- `targets`
- `alternate_route_to`
- `implements`
- `produces_feedback`
- `changes_state`
- `crosses_boundary`

Substrate adapters may still emit structural edge kinds such as `dispatches_to`, `emits`, `includes`, and other deterministic relations. New semantic vocabulary should be added deliberately rather than by free-form overlay prose.

## Proof direction

Preferred positive justification direction:

`source/file -> evidence -> extracted claim -> semantic claim -> reconstruction anchor`

`why` walks backward over positive proof relations. `impact` walks forward. `contradicts` remains visible but is not counted as positive support.

## First-class evidence

Evidence identity and evidence class are distinct. `DIRECT` alone is not certification-grade provenance.

Where bytes are available, an evidence object retains:

- source file ID;
- source path;
- line range where mechanically recoverable;
- extractor identity;
- evidence class;
- excerpt;
- source SHA-256 associated with the evidence projection.

The integrity audit detects when the evidence digest and current FILE object digest diverge.

## Integrity gate

`scan-body audit` mechanically reports:

- dangling relation endpoints;
- invalid evidence references;
- missing evidence source files;
- source digest mismatches;
- orphan evidence;
- claim-bearing semantic objects without evidence paths;
- reconstruction anchors without evidence paths;
- dangling completeness parents/evidence;
- positive proof cycles.

The audit never silently repairs these conditions.

## Surface closure

Human surfaces are separately projected into `surface_closure.json`. Closure status describes scanner knowledge:

- `BOUND`: handler mechanically reachable;
- `PARTIAL`: route detected but closure incomplete;
- `UNRESOLVED`: no route mechanically established.

This avoids confusing a visible QAction or button declaration with a proven semantic behavior.

## Projection coherence

`projection_manifest.json` records byte counts and SHA-256 hashes for emitted projections. Semantic overlay ingestion must refresh affected projections and the manifest. Stale projections are a packaging defect, not evidence about the specimen.

## Contradictions

Contradictory evidence is preserved. Later synthesis may downgrade or invalidate dependent interpretations, but historical evidence is not deleted merely to make the graph internally comfortable.

## Completeness

Completeness is a vector of named dimensions. R1 adds evidence-integrity, evidence-traceability, and nested human-surface-binding closure. No single percentage replaces explicit `MAPPED`, `PARTIAL`, `BLOCKED`, `NOT_APPLICABLE`, and `UNKNOWN` states.

## M3B deep closure

Binding closure and effect closure are separate measurements. A surface may be bound to a handler while remaining semantically `PARTIAL` because the current scan has not yet established an effect, state change, NEST boundary, extension receptor, presented surface, or feedback terminal.

`effect_closure.json` is a projection from the canonical graph. Example routes refer to stable edge and node identities already present in `scan_index.sqlite`. Compiler-assisted C++ evidence remains distinguishable from fallback extraction through parser/extractor provenance and coverage state.
