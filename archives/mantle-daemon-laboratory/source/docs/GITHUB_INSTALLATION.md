# GitHub installation guide

The local release candidate is designed for a private repository. Before the first live
run, create an empty private repository, upload the verified tree, and review Actions
permissions. The workflow needs repository contents write permission only if checkpoints
are expected to commit; read-only mode is a supported negative test.

The workflow dispatch form defaults to read-only. The read-only job receives only
`contents: read` and disables checkout credentials. Set `checkpoint_write` to `true` only
after reviewing the repository target and permissions; the separate write job then receives
`contents: write`, commits only the verified checkpoint paths, and pushes.

Selected destination: `jodydugas-ctrl/mantle-daemon-laboratory`.

The BODY-only trial has now passed in read-only mode, write-enabled checkpoint mode, and
read-only mode again after the checkpoint.

From the extracted release candidate, the upload shape is:

```text
git init
git add .
git commit -m "birth: initialize laboratory specimen"
git branch -M main
git remote add origin https://github.com/<owner>/<private-repo>.git
git push -u origin main
```

The first GitHub run should be BODY-only. It must use the same command as local tests:

```text
python -m daemon verify --root .
python -m daemon heartbeat --root .
```

No external network access is required for BODY-only operation. A real MIND is a later
experiment and must add exactly one provider secret through the platform secret store;
the secret must never be written to VCW, receipts, or logs. Provider selection and the
destination repository are intentionally left for an explicit operator decision.
