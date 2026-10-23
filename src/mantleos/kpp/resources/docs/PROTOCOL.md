# Shared protocol and optional Anchor integration

KPP supplies the development workflow; MantleOS supplies an experimental testbed.
Recipe/3 keeps its shared Neutral binding. Recipe/4 defaults to general obligations
without Anchor binding; explicit binding uses the same authoritative model.

# Current contracts

## Recipe: kpp.recipe/3 (retained)

Required: schema, id, goal, mode (composition/chase/hybrid/transformation), tissue (anchor/python/javascript/mixed/unspecified), integer fidelity 1..32, described target, ingredients, nonempty anchors, product_kind (biosoftware/bioagent/appai/conventional), delivery_mode (artifact/progressive-web), and boolean capabilities agent/mind/mantleos_splice.

BioAgent requires agent; AppAI requires splice. Labels grant no effects. Anchor dependencies form a DAG. Transformation preserve/may_change are disjoint; every preserved property maps to mandatory Anchors. Reflex declarations join the same graph.

Progressive-web requires JavaScript/mixed tissue, preview.kind=progressive-web, state_profile=json-body/1, and exactly index.html/base.js/style.css assets under previews/ with raw-byte pins. Artifact delivery has no preview. Optional reference_gui declares source_root, inventory path/canonical pin and coverage_anchor. Only current contracts are read.

## Recipe: kpp.recipe/4

Retains the existing contract fields, including `anchors` as the historical wire
name for obligations. Adds required `implementation.components` and optional
`anchor_binding` (`none` by default, or `shared-neutral`). Binding metadata on
obligations requires the selected adapter. No recipe is rewritten on validation.
See LANGUAGE-CHOICES.md for selection, tissue consistency and preparation rules.

## Workspace: kpp.workspace/3

new validates recipe, Pantry and pins before publishing. recipe.json and ingredient-labels.json are fixed. state owns workspace_id, revision, phase, enabled module records, acceptance and GUI inventory/evidence. load refuses changed recipe, seeds, shipped runtime, modules or inventory.

install admits immutable reviewed JavaScript with existing enabled dependencies. module-disable [--cascade] withdraws resources; module-enable restores retained source. Active/source changes clear acceptance and return to BUILDING. Native exclusive writer locking serializes mutations. recover-writer --reviewed proves no active writer and validates committed pins; partial staging is never adopted.

serve binds loopback. preview-export --out NEW.zip [--browser-state CHECKPOINT.json] carries exact pinned sources; preview-import --bundle FILE --output UNUSED restores without execution. Explicit checkpoints must match recipe/profile/source fingerprint. Incoming approval is cleared and new workspace identity makes carried GUI observations stale. See PREVIEW-RECOVERY.md.

## Evidence

status/graph/coverage/next/handoff derive from one Functional Graph. gui-matrix separates discovery, accounting, presence, functionality, testing and acceptance. Observations supply no approval. accept records explicit manual Baker attestation with fresh dependency checks; gui-accept binds reviewed captures. complete requires all mandatory Anchors/preservation obligations with current evidence.

`build-step --workspace DIR` derives `mantle.kpp-build-step/1` from those same
requirements and dependencies. Its next obligation includes the actual statement
and test; it excludes unrelated optional work. The bounded host driver
`mantleos.kpp.build.run` opens/checks the useful preview before refinement, re-reads
the graph after every cycle, rejects recipe drift and retains unsatisfied work on
budget, blocking or review stops. It never calls accept/complete. A caller's host
receipt is not independent proof of rendering and cannot be fabricated by a model.

Completion publishes a pinned receipt before COMPLETE state. Content-addressed prior receipts and full approval/invalidation records retain provenance. Missing/changed current receipts invalidate COMPLETE. Receipt scope is this recipe's obligations, not universal equivalence.

Executed tests require test --execute --reviewed --workspace WS --candidate DIR --suite DIR --out NEW.json. kpp.reflex-test-report/2 records EXPLICIT_REVIEWED_LOCAL_PYTHON; there is no sandbox. test-check rechecks pins; test-accept --baker LABEL is separate. Changed source/tests/reports invalidate evidence.

Anchor execution uses the shared MantleOS interpreter, including EMIT_TEXT/0.2 literals and NOTEPAD_LLM/1.3 explicit JSON commands; bridge-python writes syntax-checked text without executing it. Unsupported profiles fail. Portable Reflex and preview use the same strict bounded archive handling. Hashes provide integrity, never authentication.


## Organ projections and reviewed browser source revisions

`organ-project` derives `organ.projection/0.1` from `organ.mapping/0.1` and the
same pinned recipe. Complete unique ownership and declared cross-organ
dependencies are validated. `organ-evidence` joins explicit source/node references
from canonical `kpp.static-scan/2`; native coverage and uncertainty remain visible.
Neither operation writes acceptance or grants effects.

The Notepad Save `module-test` profile executes explicitly reviewed local Chromium
checks in a pinned disposable preview. `kpp.module-test-report/1` binds candidate,
baseline identity/revision/fingerprint, recipe, mapping, scanner and test source.
`module-replace --reviewed --expected-revision N` requires current passing evidence;
`module-restore` selects a retained predecessor with the same module identity and
dependencies. Workspace/3 optionally retains immutable `revisions`, selected and
previous hashes, and a monotonic module generation. Files are prepared before an
atomic state publication. All retained sources are verified and transported;
unreferenced staging files are never admitted by recovery. Approval is cleared on
transport. Acceptance is invalidated by replacement/restoration.

Current and explicitly retained prior runtimes remain readable without rewriting
old workspaces. Replacement requires a current-runtime workspace. See
[the runnable Save demonstration](ORGAN-SAVE.md) for commands, tests and limits.

See ARTISANAL-CONSTRUCTION.md for optional recipe/4 construction.techniques and unchanged explicit acceptance.
