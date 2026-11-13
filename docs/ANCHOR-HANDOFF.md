# Portable Anchor handoff

`ANCHOR-HANDOFF.md` is one readable file carrying the complete Notepad Fidelity 9
source, contracts, tests, a standard-library receiver, and bridge instructions.
It is a development and execution handoff. For blind model assessment, give the
model only `notepad/blind_public/`; the complete handoff reveals reference code.
No independent external-model response file was supplied or scored.

## Read and run

A receiving LLM can read the `START-HERE.md` section, then
`notepad/LOGICAL-INTERPRETATION.md`, `notepad/LOGICAL-CONTRACT.json`,
`notepad/GATE-ECONOMY.json`, and `notepad/Notepad.anchor.txt` directly in the file.
Use the public challenge's result contract for the precise benchmark response
shape; the live shell has its own documented trace envelope.

Copy the complete `receiver.py` section to a new file after reviewing it. Python
3.11–3.14 and its standard library suffice for extraction and the logical shell:

```sh
python receiver.py inspect ANCHOR-HANDOFF.md
python receiver.py extract ANCHOR-HANDOFF.md --directory received
cd received/notepad
python logical_shell.py --port 8765
```

Open http://127.0.0.1:8765/. The shell has editing, history, search/replace,
virtual files and virtual clipboard. Browser file selection and download remain
explicit user interactions. `python notepad_surface.py` opens the separate Tk
application, requiring Tk and a display; that application uses actual guarded
file/clipboard capabilities. Extraction does not start either application.

With KPP available, the same receiver ships as `receiver.anchor` using the
existing EMIT_TEXT/0.2 profile:

```sh
python -m kpp anchor bridge-python receiver.anchor --out receiver.py
python receiver.py inspect ANCHOR-HANDOFF.md
```

The command writes the receiver; run it separately. The readable Fidelity 9
`Notepad.anchor.txt` is a design contract, not a native executable profile.
Fidelity 9 and the repository's NOTEPAD_LLM/1.3 are distinct contracts.

## Write and revise

Extract to a new directory, edit the source and matching contracts deliberately,
run the tests, then use:

```sh
python receiver.py repack ANCHOR-HANDOFF.md --directory received --output REVISED.md
```

Repacking preserves the original inventory, recalculates payload hashes and records
the parent handoff digest. It does not certify changes or update preservation pins.
For intentional additions/removals, use `pack(files, metadata=...)` from receiver.py
with an explicit mapping of portable relative paths to UTF-8 bytes, then inspect
the resulting file. Retain prior artifacts for comparison. Change the contract
version when changing its meaning. Keep private keys and live state out of public
handoffs. Imported provenance records describe the original bytes; subsequent
edits require a new provenance record rather than reusing the original claim.

## Encode in another language

The normative starting point is the supplied logical contract and per-action Gate
clauses, augmented by v2 public challenge result and observation contracts. The
32 trace cases are public development conformance vectors. They are not independent
LLM scores. Reimplementing prose requires explicit decisions where underspecified;
record those as a new version rather than inferring new Anchor syntax.

Port these values faithfully: Unicode code-point offsets and half-open ranges;
exact object fields; Boolean distinct from integer; text-change-only revision
increments; baseline-derived dirty status; bounded undo/redo with stale-history
rejection; conflict observations; unsuccessful effects; successful no-match
`{"kind":"none"}`; one history record per Replace All. Python regex ignore-case
semantics are not interchangeable with JavaScript Unicode case folding. A port
must match those cases or return UNDETERMINED where required semantics are absent.

A host can instead call `python notepad/bridge.py` as a persistent JSONL child
process. Each input is exactly `{"action":...,"payload":...}`; each output is
one shell response, with non-ASCII characters JSON-escaped so legacy Windows
stdout encodings preserve every Unicode code point. The process owns one in-memory document and returns simulated
effects only. `node notepad/bridge-client.js` demonstrates this from JavaScript,
using `PYTHON` or `python3` and passing stdin/stdout unchanged. Other languages can
use the same protocol. This is verified Python-backed execution, not an independent
JavaScript implementation. A restart creates a fresh document; protocol state is
not an exported durable snapshot.

## Verify

```sh
cd received/notepad
python -m unittest discover -s . -p 'test_*.py' -q
python notepad_blueprint_gate.py --verify
```

Use Xvfb on headless Linux for the Tk tests. A skipped GUI test is unverified.
Run a port against the trace corpus and the same negative cases before claiming
compatibility. Model predictions, reference implementation results, actual host
effects, and Baker acceptance require their own evidence.

## Container format: anchor.handoff/1

All bytes are UTF-8. The receiver enforces a 32 MiB total input limit and at most
512 files. The fixed prefix precedes one JSON manifest and its closing marker.
The manifest has exactly schema, files, metadata and authority. Authority is NONE.
Each file entry has path, bytes and sha256. A file header introduces a readable
fenced section; read exactly `bytes` UTF-8 bytes, verify SHA-256, then require the
closing fence/marker. Embedded fences and marker strings are data within those
lengths. Reject duplicate/case-colliding paths, reserved device names, traversal,
file/directory collisions, malformed lengths, changed bytes, and trailing content.
Metadata is descriptive and does not authorize actions. Hashes verify integrity,
not origin or equivalence of code and contracts. No automatic migration, execution,
model API, new Anchor definition or execution profile is introduced.

The receiver validates all sections before creating a new destination. Extraction
and repacking refuse existing outputs. The outer receiver must be reviewed under
the receiving host's policy; a carried receiver cannot authenticate itself.

## Build from the repository

```sh
PYTHONPATH=src python -m mantleos.anchor_handoff_build --output NEW-HANDOFF.md
```

Sources live under `src/mantleos/kpp/resources/examples/notepad-fidelity9`.
The generator includes all selected source bytes, receiver, EMIT_TEXT receiver,
and component notices in one file. The owner supplied the Fidelity 9 ZIP;
IMPORT-PROVENANCE.json records its digest and imported source hashes. No new
license grant is inferred from public visibility. The original private key and
control answers remain outside Git and the handoff. The source-containing handoff
is unsuitable for source-hidden benchmark testing even without that key.
