# Interfaces and compatibility

## Public operations

`mantleos` and `python -m mantleos` use the same entry point. Output is JSON except
help and inherited human-oriented diagnostic commands. Foundation errors return
exit code 2.
`PARTIAL` inspection is explicitly labeled and is not a passing verification.

| Operation | Python API | CLI |
| --- | --- | --- |
| Kernel CELL units | `cells.produce`, `cells.validate`, `kernel.produce_cell` | `cell FILE` |
| Program/tissue composition | `tissue.program`, `tissue.tissue`, validators | `program FILE`, `tissue FILE` |
| Full KPP workflow | `mantleos.kpp` | `kpp --help` |
| Recipe organ projection | `kpp.organs.project` | `kpp organ-project --recipe FILE --organs FILE` |
| Source-bound organ observations | `kpp.organs.evidence` | `kpp organ-evidence --recipe FILE --organs FILE --bindings FILE --scan FILE --source DIR` |
| Reviewed browser candidate checks | `kpp.organ_testing.run_module_tests` | `kpp module-test --workspace DIR --id save --source FILE --organs FILE --output NEW_DIR --execute --reviewed` |
| Replace/restore browser tissue | `kpp.module_revisions.replace_module/restore_module` | `kpp module-replace` / `kpp module-restore`; source evidence, expected revision and explicit review required |
| Shared system definitions | `mantleos.kpp.systems.describe` | `kpp systems` |
| Concurrent KPP discovery | `mantleos.scan.discovery.discover` | `kpp discover SOURCE --identity LABEL --output NEW_DIR` |
| Apply KPP recipe attributes | `kitchen.bind`, `kitchen.inspect_binding` | `anchor-code kpp --recipe FILE [--output FILE --permit-effect]` |
| Construct synthetic notebook | `organism.create(output, identity=..., tissue=...)` | `new --output DIR [--identity ID] [--tissue FILE]` |
| Execute deterministic program | `lifecycle.run(body, program, inputs, commit=..., request_id=...)` | `--body DIR run PROGRAM --inputs-file FILE --commit --request-id ID` |
| Query memory | `compiled.query(body, text)` | `--body DIR query TEXT` |
| Snapshot and restore | `lifecycle.save`, `lifecycle.restore` | `save --output FILE --format cartridge\|chroma --permit-effect`, `restore FILE --output DIR` |
| Propose and review evolution | `evolution.propose`, `evolution.validate` | `--body DIR evolve propose --tissue FILE --output PROPOSAL`; `evolve validate PROPOSAL` |
| Admit reviewed evolution | `evolution.apply(..., approval=digest)` | `--body DIR evolve apply PROPOSAL --approve SHA256` |
| Roll back tissue | `evolution.rollback(..., expected_revision=..., approval=...)` | `--body DIR evolve rollback --revision SHA256 --approve SHA256` |
| Simulate cloud sync/recovery | `replication.sync`, `replication.restore` | `--body DIR continuity sync --store DIR`; `continuity restore --store DIR --output NEW` |
| Create portable apps/thoughts | `anchor_apps.app_document`, `anchor_canvas.emit` | `anchor-code emit --input APP.html --output App.anchor --name App --permit-effect` |
| Build apps progressively in chat | `kpp.build.step/run`, `ProgressiveBuild` | `kpp build-step --workspace DIR`; open the first useful preview, then pursue unmet recipe requirements with preserved user state |
| Receive a thought | `anchor_app_bridge.materialize` | `anchor-code launch FILE --output NEW.html --permit-effect` |
| Analyze a source tree | `kernel.scan(operation, arguments, permit=...)` | `scan inspect SOURCE --workspace OUTSIDE_SOURCE` |
| Concurrent code and Qt discovery | `kernel.scan('scan.discover', arguments, permit=True)` | `scan discover SOURCE --gui-root UI_SUBTREE --identity REVISION --output NEW_EXTERNAL_DIRECTORY` |
| Construct/run distinct examples | `examples.build`, `examples.observe`, `examples.handoff` | `examples build NAME --output DIR`; `examples run NAME --directory DIR` |
| Resident AppAI lifecycle | `appai.clone`, `birth`, `phase`, `run`, `reverse` | `appai birth\|activate\|stasis\|run\|reverse --nest DIR` |
| Standing mission policy | `missions.authorize`, `missions.revoke` | `mission authorize --approve ...`; `mission revoke --nest DIR --policy ID` |
| Dispatch, inspect, review, admit | `missions.dispatch`, `run`, `inspect`, `review`, `admit`, `recover` | `mission --help`; `appai run --policy ID --request-id ID ...` |

See [working examples](examples.md) for complete argument lists, host provisioning,
operator boundaries, and the offline representative walkthrough.

`new` constructs the reference organism. Advanced birth contracts retain the
existing `lifecycle.create` API. Hosted sessions and Anchor app tools retain
their inherited command paths; use `session --help` or `anchor-code --help`.
No command requires activating Raven.

## Versioned definitions

`mantle.cell/2`: `schema`, `kernel`, `payload`, `sha256`. A `chroma.rgb/1`
payload is exactly one RGB triple. A `tape.segment/1` payload has `sequence` and
one `record` with the same `seq`. Undefined kernels and malformed units fail.

`mantle.program/1`: `schema`, `id`, `profile`, `payload`, `dependencies`,
`capabilities`, `sha256`. Payload is the complete self-contained Anchor source.
The digest covers canonical JSON of the other fields. IDs are portable; the
currently composable profiles require no external capability grants.

`mantle.tissue/2`: `schema`, `id`, `programs`, `sha256`. Duplicate identifiers,
case collisions, missing dependencies and cycles are errors. TISSUE.json binds
actual executable source bytes. Programs are no longer labeled CELLs.

`anchor.application/1` references a source-defined singularity and carries
contextual `attributes`. `anchor.conversation-state/2` and `anchor.blueprint/3`
use the same definition/type/singularity bindings. A digest cannot authorize a
changed singularity. KPP recipe/3 fields are preserved as application attributes.

`mantle.tissue-proposal/1`: `schema`, `base_revision`, `candidate`, `sha256`.
The base revision binds the current compiled snapshot, including memory and
program sources. Any intervening committed edit invalidates approval of the
old proposal. The operator must review a new proposal.

## Current formats

| Format | Allowed path | Limits |
| --- | --- | --- |
| `vcw/1` cartridge | Verify, pack, restore, run trusted restored Body | No encryption or publisher authentication |
| ChromaMem v5, native package `/2` / AgentChroma 0.2 | Decode, verify, snapshot, restore | Preserve original PNG bytes; lossy edits destroy the carrier |
| Anchor application `/2` | Verify payloads and semantics; explicit example import regenerates supported targets | Launch prose is advisory; outdated compiled targets are not implicitly executed |
| `raven.archive-cartridge/1` | Verify, append objects, retrieve, mirror | Local cooperating writers; retained name is a wire identifier |
| `raven.cloud-head/1`, `raven.cloud-segment/1` | Local replication and recovery | No live cloud qualification |

Old RGBA VCW, encrypted Book, image package `/1`, and the legacy anatomy
inspection adapter have been removed. There is no automatic cross-format semantic migration. Unsupported editions stay
unsupported until a source-backed adapter and conformance tests exist. Cloning
source does not create identity. Restoring a snapshot continues the identity
encoded in that snapshot; creating a new organism requires an explicit identity.
