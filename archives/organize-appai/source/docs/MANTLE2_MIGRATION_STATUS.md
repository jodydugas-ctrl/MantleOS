# Organize.AppAI Mantle 2 migration status

| Item | State |
| --- | --- |
| Release branch | `main` (prepared on `codex/organize-appai-mantle2`) |
| Base commit | `8ef42a4dbe1991d197c65862825634b0c252af16` |
| Target protocol | `mantle-resident-v2` |
| Default requested model | `openrouter/free` |
| Shared Body dispatcher | integrated through pinned MantleOS `v2.0.0rc1` |
| Standalone fallback | retained for dependency-light upstream tests |
| Deterministic explain/why | preserved |
| Proposal execution | refused automatically; simulation only |
| Historical residents/certificates | preserved outside this product worktree |

A fresh project-local `.venv-mantle2` was created because the historical checked-in
virtual environment was stale. Runtime and declared development dependencies were
installed without global package changes. The complete suite passes on Windows with
`299 passed, 4 skipped`; the skips are platform/optional-feature cases. The offline demo
passes against the pinned MantleOS release candidate, and a fresh preserved resident
certification passed after installing the documented optional Pillow dependency. The
local environment remains ignored by Git.
