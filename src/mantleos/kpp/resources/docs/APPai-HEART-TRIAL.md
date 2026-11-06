# AppAI Heart notes trial

The **AppAI Heart Spore** ([recipe](../recipes/appai-heart-spore.json)) describes
the Heart with four canonical Anchor applications and leaves its implementation
language open. The concrete trial selects Python
and reuses SQLite. These are design responsibilities implemented by ordinary
Python. The local runner targets a 600-second natural beat for this recipe.

The historical Mantle OS MIT sources at revision
`8e90a4f84998518d6abd8309dfa285a9ea7e8b24` were reviewed for cadence and cascade
behavior (`resident/heartbeat.py`, `resident/protocol.py`, and `organs/heart.py`).
The trial implements its own short scheduling loop and uses the current Engram
ledger, SCAN, checked effects, KPP Pantry, and satisfaction verifier. Historical
receipts do not qualify this specimen.

From an installed package or a source checkout with `src` on `PYTHONPATH`:

```console
python -m mantleos heart plant UNUSED_DIRECTORY
python -m mantleos heart run UNUSED_DIRECTORY --natural-beats 1 --stage-reviewed
python -m mantleos heart status UNUSED_DIRECTORY
```

Plant runs the native notes baseline before beat 1 and records a synthetic
PRIMER and toolchain pins. The runner can stage one bundled export candidate in
a separate child. Alternatively, run `heart stage DIRECTORY --reviewed`.
Use the notes app directly with `python DIRECTORY/notes.py --db DIRECTORY/notes.sqlite list`.
The notes process and its SQLite storage remain independent of the Heart runner.

Review the staged source, discovery record, and KPP execution receipt under
`.heart/construction`. An operator can authorize the exact candidate with
`heart integrate DIRECTORY --approve CANDIDATE_REVIEW`. The candidate's hash
binds that decision to the observed source. Authentication is the responsibility
of the local operator environment. `heart rollback DIRECTORY --approve CHANGE`
withdraws the added adapter and retains the candidate and journal. Use
`heart recover DIRECTORY` to reconcile an interrupted change or retain
interrupted staging before deliberately retrying.

After observing a natural beat and integrating the reviewed export,
`heart qualify DIRECTORY --reviewed` checks the mandatory obligations with MIND
disconnected and produces a review hash. Qualification runs pinned local Python
checks in disposable directories. Those checks require trusted local source.
The workspace records readiness separately from Baker acceptance. An explicit
`heart birth DIRECTORY --approve QUALIFICATION_REVIEW --baker LABEL` completes
KPP acceptance and records birth. Preserve the directory to retain its evidence
and local continuity. Keep the specimen and its state out of Git.

The runner supports explicit restart and bounded extra wakes. A missed cadence
is reconciled as one pulse with a missed-interval count. Provider checks use
only synthetic subprocesses. This trial exercises the local Python fixture
and does not establish automatic OS startup, live provider, or other platform
behavior.
