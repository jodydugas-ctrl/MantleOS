# Files.AppAI

Files.AppAI is an offline deterministic aide for the `files-community/Files` source
snapshot at commit `7aa516aca1a97e08ffd74a5cc79a91d00e828a2c`. It answers
evidence-bound project questions, generates focused MSBuild commands, classifies source
paths, records an append-only local session ledger, and keeps the Files mutation boundary
closed.

## Use

Serve the examples directory, then open `http://localhost:8765/files_appai/`:

```powershell
python -B -m http.server 8765 --directory examples
```

The face is also a static document and can be opened directly from
`examples/files_appai/index.html`. It makes no model or network call.

## Generate And Certify

The PNG and nest are generated artifacts. Do not edit them:

```powershell
$env:PYTHONPATH = "src"
python -B examples/files_appai/build.py
python -B examples/files_appai/certify.py
```

`build.py` deletes and recreates `Files.AppAI.spore.png` from `germ.json` plus
`index.html`. `certify.py` deletes and recreates `Files.AppAI.nest`, hatches through the
normal Mantle birth door, re-runs Stage 1, verifies the sealed phenotype, and writes a
machine-readable receipt.

See [STAGE1_CERTIFICATION.md](STAGE1_CERTIFICATION.md) for the gate evidence and
[PROBLEM_LOG.md](PROBLEM_LOG.md) for problems, fixes, and prevention rules.
