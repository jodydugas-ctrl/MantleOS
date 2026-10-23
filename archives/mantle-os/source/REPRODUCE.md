# Reproducing Mantle OS Certification

The reference certification is closed-world: every admitted Python minor runs the same
strict gate with the optional certification dependencies installed. A missing prerequisite,
internal skip, uncovered scenario row, surviving security mutant, or failed command blocks
the claim.

## Local clean environment

With Python 3.12 available:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install pip==25.1.1
python -m pip install -r requirements-certification.txt
python -m pip install -e .
python tools/environment_receipt.py .artifacts/environment.json
python -m mantle check --strict
python tools/mutate.py --report .artifacts/mutation-report.json
```

On PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Pinned container

```bash
docker build -f Dockerfile.reproduce -t mantle-reproduce .
docker run --rm mantle-reproduce
```

The container fixes the Python patch release and all non-stdlib certification packages.
The Git commit remains the source identity and is recorded in the environment receipt.

## VS Code / compatible dev container

Open the repository in the configuration under `.devcontainer/`. The image is built from
the same `Dockerfile.reproduce`; creation writes `.artifacts/environment.json`.

## Evidence to attach to a report

Attach:

- `.artifacts/environment.json`;
- the full `python -m mantle check --strict` output;
- `.artifacts/mutation-report.json`; and
- for an application-specific failure, the `mantle certify <nest>` receipt or refusal.

Do not attach model keys, environment-variable dumps, nest genesis keys, private memory
bands, or provider request bodies.
