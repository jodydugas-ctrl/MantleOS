# Verification record

Current release workflow and commit-bound evidence indexing:
[RELEASE-HANDOFF.md](RELEASE-HANDOFF.md). The dated observations below retain
their original scope; they are not receipts for subsequent commits.

Current r3 results: [log-adoption-verification.json](log-adoption-verification.json). These cover optional techniques and synthetic augmentation. Prior receipts below remain historical.

Current recipe/4 revision results are in [recipe-v4-verification.json](recipe-v4-verification.json). Earlier records below, including the original handoff receipt, remain historical.

## Save organ integration and scanner reconciliation — 23 October 2026

Executed locally on Windows x64, CPython 3.14.2 and Chromium 145.0.7632.6:

| Check | Result | Scope |
| --- | --- | --- |
| Combined MantleOS suite | 321 run, 316 passed, 5 skipped; 369.315s | Full suite including shared KPP checks |
| Primary KPP suite | 228 run, 223 passed, 5 skipped; 65.310s | Complete standalone workflow suite |
| Save organ browser demonstration | PASS | Two broken candidates rejected; reviewed replacement; injected activation failure; state-preserving restoration; recovered browser checkpoint |
| Candidate behavior profile | PASS | Nine checks covering exact Unicode/empty bytes, filename, single user gesture, failure isolation, cleanup, storage failure and Open |
| Existing browser probes | 4 PASS | Notepad, calculator, managed recovery/transport and GUI observations |
| JavaScript syntax | 11 PASS | Current and retained runtime plus all preview modules |
| KPP doctor and adaptive smoke | PASS | Local deterministic tooling; no model/provider required |
| Documented MantleOS walkthroughs | 5 PASS | Foundation, working examples, thoughts, KPP and discovery |
| Offline distributions | Both projects built | Wheels and source distributions using already provisioned pinned build tools |
| Fresh KPP wheel | PASS outside checkouts | Identical facade modules, packaged contracts/runtime assets and doctor |

The five skips require unavailable Windows symlink privileges. Discovery's junction
refusal test passed. Other Python versions, operating systems, external model
providers, SCAN v0.28 and native-reference parity were not qualified here.

The first KPP full run exposed missing retained Qt entry points and lost projected
HTML control IDs in the pre-existing scanner work. Those were repaired and tested,
along with a trace CLI forwarding regression and equivalent filter normalization.
All final shared source originates in KPP. The former MantleOS discovery suite is
now in shared KPP tests, updated to prove overlap of captured-file extraction.

The two negative candidate reports intentionally record FAIL; admission rejects
them and preserves the active baseline. The final demonstration passes with three
retained Save revisions, BUILDING phase and no Baker acceptance. Managed JavaScript
is not a sandbox, and hashes/report declarations are not authentication.

Repeat the new probe using `tools/check_organ_save.py --output NEW_DIRECTORY
--execute --reviewed`. Existing release validation and full verification commands
remain applicable. Local receipts, candidate sources, screenshots, checkpoints,
history and initial failing logs remain outside Git under MantleOS's ignored
`.work/organ-bridge/`. No remote publication or configuration was performed.


## KPP primary GitHub project — 15 October 2026

The owner requested a public Kitchen Party Protocol project and made KPP the
primary place for ongoing protocol/shared-system development. The new repository
is [Kitchen-Party-Protocol](https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol),
final prepared commit `6f4919cafb96e8f415434036a04762de69a6f5b8`.
MantleOS remains associated through the same implementation. Both checkouts have
230 byte-identical common source files; the fresh GitHub clone matches all 367
reviewed project files. Source promotion is explicit, with no automatic updater.

Newly executed checks:

| Check | Result | Scope |
| --- | --- | --- |
| Combined suite after the path fix | **302 run: 297 passed, 5 skipped**, 340.033 seconds | Windows CPython 3.14.2 with writable workspace TEMP/TMP and loopback access |
| Standalone KPP qualification | **195 run: 190 passed, 5 skipped**, 51.759 seconds | Full suite, doctor, adaptive example, exact inventory and six JavaScript syntax checks |
| Hosted CI | **All eight matrix jobs passed** | Windows/Linux, Python 3.11–3.14; tests, source integrity, builds and installed command outside checkout |
| Both distributions | Built successfully | KPP and MantleOS wheels/source distributions with the reviewed fix |
| Fresh installed KPP wheel | PASS | Doctor, independent Notepad workspace, identical shared module objects and corrected installed export source |
| Documented walkthroughs | PASS during project preparation | Foundation (17 checks), organism examples, thoughts, KPP and discovery |
| Fresh GitHub clone | PASS | Exact export/source/document parity, retained component licenses and clean source inventory |

The first restricted combined run had one local preview-server startup failure:
301 run, 5 skipped. That test passed with loopback access; the final complete
run above passed in that environment. The first hosted matrix passed Linux and
found a real Windows short-path alias containment issue. Preview and Reflex export
now resolve output paths before comparing them with protected roots. The new
real-directory-alias regression runs on hosts with symlink permission; five local
symlink checks explicitly skip where that privilege is absent. The corrected
[hosted run](https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol/actions/runs/38744690807)
is observed evidence, not merely a CI declaration.

Existing license terms remain; public visibility does not relicense reserved-rights
components. Imported archives and private state are excluded. Real browser probes,
live providers/cloud and native reference parity were not rerun. No package registry
publication or product Baker acceptance was performed. Receipts are under ignored
`.work/kpp-project/`, including `combined-final-tests.log`,
`standalone-final-validation.json`, the build logs and walkthrough results.


## Current release: 0.1.0a6 — preview-first Canvas and Chase, 15 October 2026

MantleOS and standalone KPP **1.1.0a2** share the same construction implementation.
The chat contract now directs the host to open the first useful BUILDING surface
before later stages or portable packaging. It supplies compact recipe-derived
steps and a bounded host driver that continues Chase, retains unmet obligations,
rejects scope drift and stops explicitly for review/blocking/budget limits.
The driver supplies no acceptance authority. Carried Bodies now include KPP's
preview assets/resources and expose `python runtime.py kpp`.

New local Windows x64 / CPython 3.14.2 execution:

| Check | Result | Scope |
| --- | --- | --- |
| Complete combined suite | **298 run: 294 passed, 4 skipped**, 358.126 seconds | Existing checks plus 12 Canvas loading/build regressions; Windows symlink creation unavailable |
| Standalone KPP qualification | **191 run: 187 passed, 4 skipped** | Doctor, adaptive smoke, exact inventory and six JavaScript syntax checks passed |
| Staged app in real in-app Chromium | PASS | Useful calculator before extension generation; addition/subtraction; live extension arrival without reload or lost inputs/result; extension works; base behavior retained; 0/3 unaccepted Anchors remain open |
| Synthetic Engram hosted frames/projection | PASS | Real ORIENT/RESPOND construction packets and projection contain the same preview-first rule; no live model or committed reply |
| All documented walkthroughs | PASS | Foundation (17 checks), organisms, portable thoughts, KPP, concurrent discovery and Paint build |
| Matched local preparation benchmark | PASS, exact app/HTML/preview byte parity | Seven alternating fresh-process pairs after a discarded warmup pair; two synthetic/local app workloads |

Notepad's local browser preparation median fell from **73.35 ms to 20.37 ms**
(72.23% less time); a larger HTML fixture fell from **174.06 ms to 55.46 ms**
(68.14%). Native launch preparation fell 79.49% / 75.90%; full file delivery
fell 22.42% / 34.65%. Portable byte materialization stays about 2–3 ms, with no
general acceleration claim. The Notepad request contract shrank from **215,779
to 3,245 JSON bytes** (98.50% smaller) by making the full compiled example opt-in.
Those bytes previously appeared repeatedly in hosted transaction frames.

These timings measure local preparation, not live model generation, network or
ChatGPT Canvas mounting. A real staged browser interaction was checked; the full
optional Playwright probes, live LLM/provider/cloud, other Python versions/platforms
and real Hermes host requalification were not rerun. Private identities/carriers
were not modified. No product Baker acceptance or publication was performed.

See [the build guide](canvas-builds.md), [reproducible measurements](../examples/canvas/README.md)
and [portable scoped evidence](../src/mantleos/kpp/resources/release-evidence/CANVAS.json).
Raw receipts: `.work/canvas-performance/full-tests.log`,
`standalone-validation.json`, `hosted-contract-check.json`, `measurement.json`
and the walkthrough logs beneath `.work/canvas-performance/`.

## Prior release: 0.1.0a5 — one MantleOS/KPP system, 15 October 2026

KPP's full construction workflow is promoted into `mantleos.kpp`. Its standalone
project is generated from the same canonical package; the `kpp` entry point
aliases the actual modules, including `kpp.anchors is mantleos.anchors`.
Both distributions publish byte-identical common system definitions. Independent
KPP grammar/Python-call extraction is replaced by the shared implementation.
The actual canonical CELL source now generates the portable CELL specimen.

New local execution on Windows x64 / CPython 3.14:

| Check | Result | Scope |
| --- | --- | --- |
| Complete combined suite | **286 run: 282 passed, 4 skipped**, 275.952 seconds | All existing MantleOS checks, 168 retained KPP checks and 11 unification regressions; Windows symlink creation unavailable |
| Clean standalone qualification | **179 run: 175 passed, 4 skipped** | Same workflow and shared-system regressions; doctor, smoke, exact inventory and six JavaScript syntax checks passed |
| Shared-system regressions | 11 passed | Same definition objects/functions, Neutral requirement binding, redefinition refusal, native literal/Notepad profiles, identical native graph/Qt inventory, projection tamper refusal, HTML record budget, canonical CELL specimen, common document and source-export drift gate |
| All documented walkthroughs | PASS | Foundation (17 checks), organisms, executable thoughts, KPP, discovery, Paint build and KPP adapter smoke |
| KPP discovery CLI | PASS | Same parallel three-file native/Qt bundle and consistent source pins |

The unmodified supplied KPP baseline ran 168 tests: 163 passed, four skipped,
one loopback preview-start failure inside the sandbox. Final qualification ran
with loopback access and that HTTP test passed. Integration checks also caught
and corrected a stale test asset path and a lost Pantry search label. The richer
scanner inventories inert data as well as code; staging and review now preserve
the complete pinned source inventory while keeping the Python attachment and
execution/admission/acceptance boundaries explicit.

Raw receipts are `.work/kpp-alignment/full-final-tests.log`,
`.work/kpp-alignment/standalone-validation.json`, and
`.work/kpp-alignment/walkthroughs/results.json`. The source-bound portable
[unification record](../src/mantleos/kpp/resources/release-evidence/UNIFICATION.json)
retains current code/profile hashes and named unrun checks. Historical imported
receipts are not reused as certification. Python 3.11–3.13, Linux/macOS, hosted CI,
real browser probes, live providers/cloud and real Hermes requalification were
not rerun. No product Baker acceptance, GitHub setup or publication is performed.

## SCAN/Optimizer application — 15 October 2026

The supplied SCAN/Optimizer 1.0.0 was run locally against a frozen copy of the
182 tracked project files, including the Paint example. Its 52 manifest entries
verified. The static graph contains 22,790 nodes and 28,522 edges; 50 files have
no supported syntax adapter and remain explicit coverage gaps. Static findings
were treated as hypotheses. Profiling then confirmed unnecessary per-byte work
when reconstructing PNG filter-0 rows.

The native Chroma reader and self-contained optical loader now append filter-0
rows directly, preserving their previous-row state for subsequent filtered rows.
No format, Anchor, CELL, authority, memory or admission contract is changed.
Existing carriers are not rewritten; new exports bind the updated loader bytes.

Newly executed on Windows x64, CPython 3.14, offline:

| Check | Result | Scope |
| --- | --- | --- |
| Independent decoder regressions | 7 passed on baseline and candidate | All 25 filter pairs, single-pixel rows, wraparound, changed-source reads, corrupt framing/filter/CRC/tape, isolated portable reader |
| Matched setup-inclusive experiment | PASS; every measured pair improved | Five alternating pairs after discarded warmup; identical stdout; successful checks on both sides; unchanged source identities |
| Complete current suite | 107 run: 106 passed, 1 skipped; 317.002 seconds | Directory-link creation unavailable in this sandbox; discovery containment link test skipped and remains untested in this run |
| Foundation demo | 17 checks passed | Body, MIND states, memory, evolution/rollback, cartridge/Chroma and simulated continuity |
| Organism, thought, KPP and discovery walkthroughs | PASS each | Existing offline workflows retained |
| Paint build | PASS | UTF-8 targets, isolated receiver and altered-thought refusal; native XP parity and Baker acceptance remain open |

The measured workload builds approximately 3 MiB of synthetic text, encodes its
PNG and twice decodes it through both readers. Median process duration fell from
**3.2422 seconds to 0.3487 seconds (89.24% less elapsed time)**. Startup, fixture
construction, compression, disk I/O, validation and cleanup are included; fresh
working-copy construction is excluded. This result describes that local workload,
not whole-application speed or other machines, Python versions or platforms.
[The example](../examples/optimization/README.md) and
[measurement summary](../examples/optimization/measurement.json) retain the
contract, source/harness hashes, graph references and raw timing pairs.

Local raw receipts: `.work/optimizer/scan/latest-scan.json`,
`.work/optimizer/png-profile.prof`, `.work/optimizer/experiment.json`,
`.work/optimizer/full-tests.log` and `.work/optimizer/verification/`.
The initial test attempt encountered an unwritable sandbox temporary directory;
the completed runs use an explicit writable workspace TEMP/TMP. No paid model,
live provider/cloud, real Hermes qualification, new browser qualification, remote
configuration or publication was performed.

## Paint KPP test bake — 14 October 2026

[Mantle Paint](../examples/paint/README.md) is a new Bio-Software example, with
Windows XP Paint as its Chase target. It is usable in HTML Canvas; native XP
equivalence remains an open requirement. [Source-bound results](../examples/paint/verification.json)
distinguish the following newly executed checks from historical claims:

- MantleOS: **100 tests passed**, no skips, Windows CPython 3.14, 204.352 seconds.
- Raster Body: **32 Node tests passed**, including containment, selection masks,
  transforms, exact BMP round trips, memory lineage and malformed inputs.
- Browser fixture: **22 checks passed** in the in-app Chromium browser, covering
  actual Canvas/text/PNG behavior and authored DOM events with isolated test data.
- Real pointer/keyboard: shapes, text, color roles and undo/redo worked. A real
  local BMP opened at 128 × 96; Save As downloaded a 640 × 400 24-bit BMP whose
  decoded pixels contain the test painting and antialiased text.
- Portable Anchor: isolated receiving HTML and UTF-8 Python output match exactly;
  a modified carried payload is refused. The standalone HTML is 69,378 bytes and
  the complete thought is 222,272 bytes, with no app-time dependencies or network.
- Supplied KPP 1.0.1-dev: **176 tests run, 171 passed, 5 skipped** for unavailable
  symlink creation. The initial preview-server failure was resolved by rerunning
  under the required loopback permissions. Doctor, recipe/Pantry/workspace,
  Scan/Functional Graph, coverage and Chase priorities were exercised.
- KPP `complete` correctly refuses this unapproved nine-obligation recipe.
  No Baker attestation was fabricated. Native XP parity remains explicitly unmet.

Tests caught and corrected off-canvas rectangle clipping and free-selection
transform-mask corruption. No native XP executable, Microsoft code, proprietary
assets, paid model, live cloud or remote publication is involved. The linked
historical guide could be read through web retrieval; direct PDF byte retrieval
failed certificate validation, so no raw-file or executable pin is invented.

## Current release: 0.1.0a4 — 14 October 2026

The supplied experimental KPP parallel-discovery proposal is adapted into the
existing SCAN/checked-action path. New results below are from Windows, CPython
3.14, standard-library-only offline execution. No real Hermes checkout, model,
network provider or GUI runtime was used for this milestone.

| Check | Newly executed result | Scope |
| --- | --- | --- |
| Complete core suite | 98 passed, no skips, 201.758 seconds | Retained 84 tests plus 14 discovery checks, including a real Windows link-containment refusal |
| Discovery integration checks | 14 passed within complete suite | Barrier proves overlap; equal serial/parallel graphs; exact scanner read pins; drift, missing UI, malformed/encoded XML, budgets, traversal, worker errors, publication interruption, containment and authority |
| Original patch's targeted tests | 8 run: 7 passed, 1 skipped | Unmodified tests against staged supplied KPP code; symlink creation unavailable in that sandbox run; integrated link test passed separately |
| Supplied archive inventory | 125 hashes matched | ZIP CRC and SHA-256 inventory checked; archive identity in provenance |
| Qt interoperability | Exact match and upstream validator PASS | Integrated and supplied scanners on 24 synthetic `.ui` files, 72 declarations |
| Foundation demo | 17 checks passed | Body, MIND states, memory, evolution, rollback, carriers and simulated continuity |
| Organism, thought and KPP demonstrations | PASS each | Existing functions retained; no live host or universal receiving-LLM claim |
| Discovery walkthrough | PASS | Three fresh-workspace serial/parallel runs each; source and native graph pins equal |
| Distribution build | Built successfully offline | Fresh source stage, pinned provisioned tools; source archive and wheel |
| Wheel-only discovery walkthrough | PASS | Package imports from extracted wheel alone; scanner and KPP license present |

The standalone final synthetic timing run averaged **1.082 seconds serial** and
**1.043 seconds parallel** (serial/parallel ratio **1.038**). This is a modest
local result on 24 Python / 24 Qt files, not a general acceleration guarantee.
An earlier run alongside focused tests measured 1.215 / 1.123 seconds; the final
run was made after other verification processes completed. Source snapshot
checks are included in each reported duration. No Notepad Next checkout was
used; no performance or visual-conformance claim is made for that application.

The new command overlaps independent native and Qt scanners. Native per-file
extraction remains sequential, its SQLite connection stays on its owning thread,
and optional external parsing is not enabled. Graph coverage gaps remain explicit.
Selected redirection, budget exhaustion and observed source drift prevent joined
publication. Pre/post hashing is not an atomic filesystem snapshot or proof of
authorship. No automatic Anchor mapping, Recipe approval or authority expansion
is added. See [discovery boundaries](discovery.md).

After making temporary-link test cleanup portable across Windows and Linux,
all 14 focused discovery tests passed again locally with no skips. The complete
98-test result precedes that test-cleanup-only change; runtime code is unchanged.

Receipts: `.work/parallel-discovery-tests.log`,
`.work/parallel-discovery-upstream.log`, `.work/parallel-discovery-interop.json`,
`.work/parallel-discovery-benchmark-final/report.json`,
`.work/parallel-foundation-demo/report.json`,
`.work/parallel-organism-examples/report.json`, `.work/parallel-thoughts/report.json`
and `.work/parallel-kpp-example/report.json`. Historical Hermes qualification
is unchanged and was not rerun. Windows/Linux CI is prepared; Linux and other
supported Python editions were not executed locally in this milestone.
Build and final focused receipts are `.work/parallel-build.log`,
`.work/parallel-wheel-example/report.json` and
`.work/parallel-discovery-final-focused.log`.

## Prior release: 0.1.0a3 — 14 October 2026

The creator's CELL/Anchor definitions and newer KPP profile are implemented.
Local verification uses Windows, Python 3.14 and the standard library; no model,
provider, live cloud or remote publication is invoked.

| Check | Result | Scope |
| --- | --- | --- |
| New alignment regression suite | 12 passed | Immutable singularities/types, shared code/project/register views, kernel units, KPP binding and profile vectors |
| Cross-runtime comparison with supplied KPP interpreter | 13 checks passed | Four KPP specimens into MantleOS, five generated literals into KPP, four malformed cases refused by both |
| Complete current core suite | 84 passed | Prior 72 obligations retained plus 12 alignment checks |
| Foundation demo | 17 checks passed | Deterministic Body, MIND states, memory/archives, evolution/rollback, both carriers and simulated cloud |
| Organism collection | PASS | Engram, Notepad, Observer and hosted fixture handoff |
| Executable-thought walkthrough | PASS | SCAN, app authoring, isolated receiving process and standalone Notepad |
| New KPP walkthrough | PASS | Recipe as Neutral attributes, two CELL kernels, four exact literal specimens and deterministic Body |
| Distribution build | Built successfully offline | Source archive and wheel from a fresh source snapshot |

The new profile rejects the old differing primer explicitly. Current schemas
are kernel `mantle.cell/2`, `mantle.program/1`, `mantle.tissue/2`,
`mantle.anatomy/1`, conversation register `/2`, and project Blueprint `/3`.
Old artifacts remain unchanged; no implicit historical migration is performed.
Singularity/type checks compare trusted source definitions; a rehashed changed
meaning is refused. Attributes supply context without changing those constants.

KPP's own release reports are supplied evidence. Its complete standalone suite
was not rerun here; these are newly executed integration checks. The thin recipe
binding does not duplicate KPP's full workspace/GUI/acceptance implementation.
Previously qualified Hermes connections are unchanged and were not requalified
against the real upstream host in this turn. No new live LLM or browser claim
is made; execution on another LLM still requires its supported authorized tools.

Receipts: `.work/kpp-alignment-contract-tests.log`,
`.work/kpp-alignment-interoperability.json`, `.work/kpp-alignment-tests-verified.log`,
`.work/kpp-alignment-demo-verified/report.json`,
`.work/kpp-alignment-examples/report.json`, `.work/kpp-alignment-thoughts/report.json`,
`.work/kpp-alignment-walkthrough/report.json`, and `.work/kpp-alignment-build.log`.
The initial broader demo caught two naming errors in the refactor; both were
corrected before the successful evolution/rollback demonstration.

## Prior release: 0.1.0a2 — 14 October 2026

Local platform: Windows, CPython 3.14. Runtime tests use `python -S` and the
standard library. All fixtures are synthetic. No provider, paid model, remote
publication, or live cloud was used.

| Check | Newly executed result | Scope |
| --- | --- | --- |
| Focused streamlining regressions | 5 passed | Exact generated profile/browser hashes, standalone compilation, new app authoring/receipt, current PNG founding, removed legacy command |
| Complete core suite | 72 passed | Current Body, authority, memory, carriers, archive/continuity, AppAI/mission tests, and the new regressions |
| Foundation demonstration | 17 checks passed | MIND absent/disabled/failing, editing, recall/archive, evolution/rollback, cartridge/PNG and simulated cloud recovery |
| Organism collection | PASS | Fresh Engram, hosted scripted encounter, experienced carriers, Notepad construction, Observer changes |
| Executable-thought walkthrough | PASS | Actual SCAN, new Counter app, independent receiver bootstrap, identical HTML/Python output, standalone Notepad edit/undo |
| Source package and wheel | Built successfully offline | Fresh source stage; pinned provisioned build tools; no legacy package or duplicate resources |
| Wheel-only walkthrough | PASS | SCAN, app authoring, standalone receiver, and Notepad executed using the installed wheel alone |

The complete suite was 74 tests before streamlining. Seven obsolete reader tests
were removed with their implementations and five current-function regressions
were added. No current-skill test was removed to obtain this result.

The new walkthrough uses isolated receiving Python processes (`-I -S`): generated
apps need no MantleOS import on the receiver. Counter HTML is generated and its
payload verified. Browser interaction was not verified in this turn: the loopback
browser timed out and the local-file URL was blocked by browser policy. The
Notepad browser output has the exact pre-change SHA-256, checked by regression.
No claim of universal LLM/Canvas reliability follows from local execution.

Receipts remain outside Git in `.work/streamline-tests.log`,
`.work/streamline-demo/report.json`, `.work/streamline-examples/report.json`,
`.work/streamline-thoughts/report.json`, and `.work/streamline-build.log`.
The sandbox could not resolve build temporary paths; the final offline build
succeeded using approved execution outside that sandbox, confined to this workspace.

## Retained prior evidence and limits

Commit `5a8eb40` contains the full 13–14 October qualification history. The pinned
Hermes host previously passed 85 selected native tests pristine and integrated,
four host-connection tests, reversible removal, and the resident mission
walkthrough. Host graft/mission code has not changed here. Those are prior
receipts, not a fresh native-host certification of a2; current synthetic
AppAI/mission tests passed as part of the 72-test suite.

Historical codec/Book/old-PNG checks do not describe supported current formats:
those compatibility adapters are removed. Current cartridge and Chroma package
`/2` round trips remain covered. Linux and Python 3.11–3.13 are prepared in or
supported by the project configuration, but were not rerun locally for this
change. CI has not been executed remotely. Live cloud, external LLM providers,
optional calibrated scanner backends, and distributed swarms remain unqualified.

Use the commands in [CONTRIBUTING](../CONTRIBUTING.md) to repeat the current
verification. Documentation and provenance distinguish implementation from
historical receipts and described-only plans.
