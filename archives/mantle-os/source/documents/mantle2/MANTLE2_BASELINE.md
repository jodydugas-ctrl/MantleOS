# MantleOS 2.0 local baseline

Captured before the consolidation branch changes.

| Field | Value |
| --- | --- |
| Repository | MantleOS |
| Base commit | `c9d6274c6c2e562fd8c1630dd9395197fe60ad6e` |
| Branch | `codex/mantle-2-platform-consolidation` |
| Product base | Organize.AppAI `8ef42a4dbe1991d197c65862825634b0c252af16` |
| Python | 3.10+ required by `pyproject.toml` |
| Release target | `2.0.0rc1` (local, deliberately breaking candidate) |

## Gate baseline

The pre-change Mantle branch passed the invariant registry and the Stage-1/Stage-2
audit paths recorded in the working session. The full `mantle check` is retained as a
separate local log because its duration is environment-dependent. No online repository
was changed.

## Historical artifacts

The NotepadNext lifecycle spore, terminal, auditor, resident, and audit artifacts in
`work/notepadnext-assimilation/` are preserved as historical evidence. The old audit
claim that a Body key is derived from a spore is explicitly non-canonical for Mantle 2;
the replacement audit must state independent genesis-key minting.

