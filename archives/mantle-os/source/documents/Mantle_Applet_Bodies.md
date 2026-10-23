# VCW Applet Bodies — APPLET-BODY-CAPSULE

*Doctrine note. The Grimoire is the canonical VCW software profile
([`grimoire/`](grimoire/README.md)); applet-body procedure lives beside the other app
doctrine documents because it is Mantle runtime behavior, not Grimoire lane semantics. The
implementation is [`src/mantle/applet_body.py`](../src/mantle/applet_body.py).*

## The subspell

**APPLET-BODY-CAPSULE raises an app into a VCW-resident capsule: source as inert tissue,
state as append-only memory, organ map as diagnosis, and face as phenotype. It is not
executable authority until trialed, calcified, or rendered through an approved host
boundary.**

A VCW Applet Body is a small app, tool, or project stored as app tissue inside a parent
AppAI's VCW. It composes existing Mantle surfaces rather than inventing a separate runtime:
the assimilation scanner dissects the project read-only (N1-N4, zero files modified, zero
files executed); the organ map diagnoses it; the source is chunked into a private (veiled) data band with
per-file SHA-256 hashes and OTHER provenance; the state passes the secret boundary
(redaction) before it appends; and the face is an ordinary `mantle.phenotype` face —
worn, shed, and rendered only through a host boundary, exactly like every other face.

## Status honesty

| Status | Meaning |
| --- | --- |
| `capsule` | Source, state, face, and organ map are stored. NOT certified as a Zombie Body. |
| `zombie_body` | Only if the deterministic Body requirements pass the Stage-1 gate. |
| `mind_ready` | Only under the normal MIND containment and Stage-1 rules. |

Everything `applet-create` produces is a `capsule`. The smaller deterministic audit,
`audit_applet_body` (CLI `applet-audit`), verifies the capsule — manifest present, every
chunk hash-valid, bundle hash intact, no stored path escapes the applet root, organ map
and state present, face SELF-openable, export dry-run verified, all bands inert data
bands — and certifies **nothing alive**. A capsule is never falsely labeled a Body.

## AppAI terminal and text-entry discipline

Every wearable app face should declare an AppAI contact affordance. GUI faces expose an
`AppAI` button, menu item, tab, or platform-native equivalent that opens a terminal-like
chat surface with the prompt box at the bottom; command-line faces expose the same surface
as `<appname> --appAI`. The terminal is Body-owned and MIND-facing: opening it is a Limb
operation, prompt submission enters through Senses, and any MIND answer still obeys the
normal `thoughts`/`brain` write surface.

Faces must not append a VCW row for every character typed in a text field. Text entry is
durable only at a commit boundary: submit, blur/focus-loss, or an explicitly declared
low-volume host event. This keeps the VCW coherent and prevents user typing from becoming
hundreds of meaningless memories.

## The spell shape

**clone → dissect → capsule → audit → optional zombie body.** Never one gulp.
`applet-clone` only clones and hands the bytes to the same dissection path; creation ends
at `capsule`; `applet-audit` is a separate, explicit cast; and nothing but the real
Stage-1 gate may ever pronounce a body alive. (A SEED hatch — egg, vault, spore — is
different by nature: hatching *is* a birth, so it faces the Stage-1 gate inside the
hatchery. Assimilated tissue never gets that shortcut.)

## The hard rules

Stored or cloned project code is never executed, imported, or installed. `applet-clone`
accepts only explicit `https://github.com/<owner>/<repo>@<40-hex-commit>` sources and
requires `--allow-network`. It fetches only that commit, checks it out detached in a
controlled workspace with hooks and submodules disabled, receipts the commit plus a
deterministic source-tree hash, and hands the bytes to the same
`applet-create` path. SELF/OTHER is preserved: applet source carries foreign provenance
and may only become SELF through the existing trial/calcify pathways. Secrets are
redacted before state or reports append (HF-B20 holds for applet tissue); suspicious
inputs raise immune events; the applet bands pass the same `validate_genome` gate as any
self-redesigned app band; history is append-only. Export ("download the sourcecode")
reconstructs the files from the VCW into a local directory, verifying every hash before
writing, refusing path traversal, and refusing overwrite unless asked.

## Commands

GitHub applet ingestion uses `git -c core.longpaths=true clone` so Windows hosts can
checkout deep native/vendor trees before Mantle performs its read-only census. Generated
app bands should be assigned with `allocate_app_band()` or exact framework atlas entries;
manual spans that overlap reserved vault, phenotype, spore, or applet tissue are refused
by `validate_genome()`.

```bash
python -m mantle applet-create <organism-dir> <source-dir> <name>   # raise a capsule
python -m mantle applet-list   <organism-dir>
python -m mantle applet-show   <organism-dir> <name>                # manifest, no blobs
python -m mantle applet-export <organism-dir> <name> <dest-dir> [--overwrite]
python -m mantle applet-wear   <organism-dir> <name>                # phenotype boot manifest
python -m mantle applet-audit  <organism-dir> <name>                # the capsule audit
python -m mantle applet-clone  <organism-dir> <https-github-url>@<40-hex-commit> <name> --allow-network
```

The five dedicated bands sit in the free slice of the app-band range (550–749):
`applets_manifest` (700), `applets_source` (704, private, chunked like the phenotype
band), `applets_state` (728), `applets_organs` (736), `applets_log` (744) — clear of the
assimilator's host bands (550–699) and the phenotype bands (640–661). Invariants
APPLET-1 … APPLET-5 in `mantle.audits.invariants` prove the guarantees red/green.
