# Contributing

Make KPP changes in this project. Keep one contract, one functional graph and
one shared implementation. The deterministic Body must remain useful without
a MIND. Preserve licenses and use synthetic fixtures. Read AGENTS.md,
SYSTEMS.md and [the project guide](docs/PROJECT.md).

Set PYTHONPATH=src (PowerShell: `$env:PYTHONPATH = "src"`). Run focused tests,
then the complete checks from the project root:

```console
python -m unittest discover -s tests -q
python -m kpp doctor
python examples/adaptive-reflex/smoke.py
python tools/verify_shared.py
python tools/verify_release.py
```

For packaging changes, build a wheel and source distribution, install the wheel
into a fresh environment, and run `kpp doctor` outside this checkout:

```console
python -m pip install build==1.3.0 setuptools==80.9.0
python -m build --no-isolation
```

Run the associated MantleOS suite and documented walkthroughs when changing
shared runtime boundaries. Promote the same reviewed shared source there, then
compare with `python tools/verify_shared.py --source MANTLEOS_ROOT`.
Record skipped and unrun checks. CI configuration is not an executed result.

Edit generated documents and scaffolding at the source paths in the project
guide. Export to a fresh directory and review the diff. Refresh shared pins and
the release inventory only after reviewing changes. Use
`python tools/refresh_release.py` when generated views already match.
Keep validation output outside the source tree or under ignored `.work/`.

Browser checks are optional developer instrumentation. See
[verification](docs/RELEASE-VALIDATION.md) for the four probes and their limits.
Passing checks never grants Baker acceptance. Credentials, private Engrams,
carriers and imported archives stay out of commits. Public visibility preserves
each component's existing license terms. Publication requires a maintainer request.
