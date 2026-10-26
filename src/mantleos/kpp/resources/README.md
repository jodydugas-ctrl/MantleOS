# Kitchen Party Protocol

Build useful software from a Pantry and a pinned Recipe. The Baker chooses the
outcome; the Oven implements it; Scan gathers observations; Chase works through
the unmet obligations. Useful software can be used while BUILDING. Completion
requires evidence and explicit Baker acceptance.

KPP is the primary project we maintain going forward. MantleOS was built using
KPP and remains an associated project. Both share one implementation of Anchors,
CELLs, programs, SCAN, Body, memory and carriers. Read [SYSTEMS.md](SYSTEMS.md)
and [the project guide](docs/PROJECT.md). Current version: **1.1.0a4**, alpha.

`python -m kpp` and `python -m mantleos kpp` reach the same modules. `python -m kpp systems` describes their shared contracts. `python tools/verify_shared.py --source MANTLEOS_ROOT` checks the shared source against a selected checkout.

KPP builds useful software from a Pantry and a pinned Recipe. The Baker chooses the outcome and acceptance; the Oven implements it; Scan discovers bounded observations; Chase selects the next unmet obligation. Fidelity means depth of behavioral consequences. A usable BUILDING app is distinct from an accepted COMPLETE recipe.

Compatible recipe/3 and recipe/4 contracts, one Functional Graph, one browser module runtime, one reviewed local Python test path. Python 3.11–3.14 and the standard library run the kitchen; a browser is needed only for browser previews. No third-party Python package, model account, container engine, Node runtime, Qt installation or remote service is required. Optional developer browser probes use separately available Playwright/Chromium; they are not product dependencies.

Run directly from source with `PYTHONPATH=src` and `python -m kpp`, or install
the local project with `python -m pip install .` to get the `kpp` command.
Installation uses setuptools; the running kitchen has no third-party Python
dependencies. Python 3.11–3.14 is supported; the verification guide records
which environments have actually been exercised. No package registry release
is implied by the GitHub project.

```powershell
$env:PYTHONPATH = "src"
python -m kpp doctor
python -m kpp new --recipe recipes/notepad-demo.json --workspace workspaces/notes
python -m kpp serve --workspace workspaces/notes --port 8765
```

Open http://127.0.0.1:8765 immediately. Type while BUILDING. In another terminal, after reviewing the example sources:

```powershell
$env:PYTHONPATH = "src"
python -m kpp install --workspace workspaces/notes --id edit --source previews/notepad/edit.js
python -m kpp install --workspace workspaces/notes --id files --source previews/notepad/files.js --depends edit
python -m kpp coverage --workspace workspaces/notes
```

Notepad and progressive-calculator use the same runtime. There is no recipe-ID dispatch or automatic baking. Installation does not accept Anchors. `accept --anchor ID --evidence TEXT --baker LABEL` records a separate manual attestation; `complete` refuses unmet required Anchors.

Chat construction is preview-first: open a useful BUILDING surface, then keep
the Chase loop active using `build-step --workspace DIR`. A visible app does not
end the bake. `mantleos.kpp.build.run` supports bounded host-supplied preview and
refinement operations without granting acceptance. See [the shared build guide](docs/CANVAS-BUILDS.md).

```powershell
python -m kpp gui-scan references/synthetic-qt --identity synthetic-qt-editor
python -m kpp new --recipe recipes/qt-gui-coverage-demo.json --workspace workspaces/gui-audit
python -m kpp graph --workspace workspaces/gui-audit
```

The synthetic fixture has two UI files and 20 declarations. Anchor mappings establish accounting; the independent matrix reports presence, behavior, testing and Baker approval separately. Run `python -m kpp gui-matrix --workspace workspaces/gui-audit`. Approved exclusions retain their reasons. Capture/comparison commands bind observations to source and context, without granting approval.

Use `module-disable`/`module-enable` for managed withdrawal/reactivation, `recover-writer --reviewed` after an interrupted writer, and `preview-export`/`preview-import` for exact source transport with optional explicit Body state. Read [GUI reference](docs/GUI-REFERENCE.md), [recovery](docs/PREVIEW-RECOVERY.md), [contracts](docs/PROTOCOL.md), [security](docs/SECURITY.md), [completion scope](docs/COMPLETION-AUDIT.md) and [KPP.md](KPP.md). General tooling is complete within these supported profiles. Notepad Next remains an example; no clone or parity is claimed. Tests never grant Baker acceptance.

## Shared systems and discovery

```console
python -m kpp systems
python -m kpp bind --recipe recipes/notepad-demo.json
python -m kpp discover references/synthetic-qt --identity synthetic-qt --output workspaces/discovery
python tools/verify_shared.py
```

`anchor run YOUR_NOTEPAD.anchor --input COMMAND.json` uses the same explicit
JSON-command profile as MantleOS. `anchor bridge-python` still materializes
EMIT_TEXT Python data without running it. `python -m mantleos --help` exposes
the included Body, memory, carrier, app-authoring and host workflows.

The source and definition parity gates are regression-tested. Make ongoing KPP
and common-system changes here in `src/mantleos`, then promote reviewed common
changes to MantleOS. The package name preserves compatibility; `src/kpp` is an
entry-point facade. The exporter produces clean releases from this project.
[release-evidence/UNIFICATION.json](release-evidence/UNIFICATION.json) records
new local checks and unrun browser/platform behavior. Original imported receipts
are not certifications of this build.

See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and generated views.
KPP's MIT license covers the KPP contributions; bundled shared components retain
their own terms, including reserved rights. See [component notices](THIRD-PARTY-NOTICES.md)
and [licensing details](docs/PROJECT.md#provenance-and-licensing).


The [Notepad Save organ demonstration](docs/ORGAN-SAVE.md) connects recipe-owned
organs, fresh source observations, real browser checks and reviewed source
replacement/restoration. Run `python tools/check_organ_save.py --output NEW_DIR
--execute --reviewed` with locally available Playwright/Chromium. It preserves
drafts and retained source and leaves acceptance open.

## Experimental REFLEX qualification

The [REFLEX guide](docs/REFLEX-QUALIFICATION.md) describes the bounded offline language,
original test corpus, source-pinned reuse review and synthetic native VCW/Chroma
examples. Discover `reflex-book` in the Pantry. This experimental capability is
separate from the existing Python reflex-adapter workflow and grants no Body authority.
