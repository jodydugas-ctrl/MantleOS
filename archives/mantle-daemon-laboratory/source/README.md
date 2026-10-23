# Mantle Daemon Laboratory

This repository is a small, local proof of a Git-resident Mantle Daemon. Its durable
continuity is the combination of constitutional files, an exploded VCW PNG stack, and
Git history. A fresh runtime reconstructs the minimum BODY, runs a Heartbeat without a
MIND, verifies the candidate, and commits only the accepted tissue.

The experiment is deliberately conservative: the default authority is `NO`, the first
MIND is deterministic and offline, and no host code is acquired or executed from VCW.
The full vocabulary, hypothesis, non-goals, and evidence standard are in
[`docs/EXPERIMENT.md`](docs/EXPERIMENT.md).

## Quick start

```text
python -m daemon init --root .
python -m daemon verify --root .
python -m daemon heartbeat --root .
python -m daemon incarnation --root . --count 5
python -m unittest discover -s tests -v
python tools/full_audit.py --root . --endurance 100
```

The package uses only the Python standard library and requires Python 3.9 or newer.
The reference VCW dimensions are 800x800 RGBA, matching the released Mantle encoder.

The prepared GitHub Actions entry point is `.github/workflows/heartbeat.yml`. It runs the
same local command; it does not create a repository, grant permissions, or inject a live
LLM credential.
