# Cumulative Anchor satisfaction

The opt-in engine constructs software by one ready obligation or a compatible
batch, retesting established behavior on each integrated candidate. Fidelity is
the depth of declared relationship consequences, never an application count or
an inferred numeric tier. CELL, Tissue, Organ and BioSoftware are distinct;
biological mappings require explicit contracts and supported interfaces.

Start with a normal pinned KPP workspace. Keep candidate and suite in separate
directories outside the workspace. A `kpp.satisfaction-suite/1` suite.json has
recipe_sha256 and cases. Each case has id, obligations (existing recipe IDs),
script (root-level Python filename), relationship (declared scope), and requires
(capability names). Every mandatory obligation and prerequisite needs coverage.
All suite files, including fixtures, are pinned. Context JSON contains an explicit
capabilities mapping; a required capability must be true. Context declarations
describe the host; they do not authorize effects or prove isolation.

```
python -m kpp satisfaction-start --workspace WS --candidate CANDIDATE --suite SUITE --context CONTEXT.json --reviewed
python -m kpp satisfaction-plan --workspace WS --batch-size 1
python -m kpp satisfaction-test --workspace WS --execute --reviewed
python -m kpp satisfaction-check --workspace WS
```

The mantleos kpp facade exposes the same commands. Planning/checking are read-only.
Start/test use the workspace writer lock and immutable content-addressed artifacts.
Candidate snapshots are retained after passing stages; failed batches promote no
obligations. Interrupted unreferenced artifacts are not adopted. Existing reviewed
writer recovery applies. Restore code only through a deliberate host operation;
historical evidence never certifies a restored candidate without fresh testing.

Evidence statuses are PENDING, VERIFIED, FAILED, STALE and BLOCKED. Prior verified
prerequisites unlock construction, independently of Baker acceptance. Every new
stage includes its targets, established cases and declared preservation obligations.
Batch members must already have verified prerequisites outside the batch.
Changes to candidate bytes stale earlier evidence; contract, suite, context or
verifier changes require a reviewed new workspace/run. Explicit scope deepening
therefore uses a new recipe revision, with old behaviors retained as obligations.

Tests execute Python with -I -B and per-case timeout 1..60 seconds. This is **not
a sandbox**: reviewed scripts can have arbitrary process/file/network effects.
An untrusted proposal needs host-provided isolation and independent permissions.
Hashes detect drift, not authenticity. Local evidence assumes a trusted controller
and workspace owner; it does not authenticate a malicious owner's forged reports.
Inventories allow 4096 files / 128 MiB, suites 256 cases, batches 1..32. Tests
cannot change source/suite/context and still receive a passing integrity result.

Passing evidence does not accept obligations. Existing `test-accept` with an
explicit Baker accepts the latest fresh satisfaction report; changed evidence
invalidates that attestation. Manual acceptance cannot bypass an opted-in run's
cumulative completion gate. Existing workspaces are not migrated. Exported preview
workspaces cannot adopt another workspace's verification identity.

`build.step/run` automatically project an opted-in run while retaining preview-first
host callbacks and bounded cycles. At verified construction completion the driver
stops AWAITING_REVIEW. It never calls accept or complete. No model call is added.

`design-view --recipe FILE --full-contract` renders every declared obligation,
tests, dependencies, preservation and design responsibilities. Default output
is unchanged. The output is DESIGN CONTRACT ONLY; coverage is relative to the
pinned recipe, with runtime tests UNRUN. The new xp-notepad-contract and
simplepaint-contract examples retain every supplied nonempty blueprint paragraph
verbatim and require independent behavioral review. They are not working clones.

Run `tools/satisfaction_specimen.py --output NEW_DIRECTORY` for actual staged
calculator tests, deeper history consequences with one design application,
intentional regression, repair, batching and 20 planning timing samples. It also
checks native tape CELL/Engram append and stale-head refusal. The bounded
`tools/satisfaction_paint_specimen.py` checks RGB/PNG/history and simulated failed
or cancelled saves; it does not qualify a GUI or real host I/O.

Provenance: owner-supplied Anchor_Satisfaction_Engine_Handoff_v2.zip,
SHA256 f160b4dfaffd9302ce2532b32763af1f73fd7a628cf347b057917ba421aea250.
Its 20 manifest entries verified; imported instructions and proposed test outcomes
were design data. Canonical definitions, runtime profiles and licenses are retained.
