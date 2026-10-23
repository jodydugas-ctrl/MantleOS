# Organize.AppAI Mantle 2 integration

This release targets Mantle resident protocol v2. The upstream `organize`
commands remain deterministic; Mantle is an optional resident seam.

## Resident commands

The terminal uses Mantle's shared Body dispatcher for `/key`, `/model` (and `/mind`),
`/offline`, `/status`, `/help`, `/provider-test`, and `/evidence`. Organize-specific
extensions remain `/credits` and `/authorize`. Plain text goes to the existing
bounded conversation path. If Mantle is unavailable, a narrow standalone fallback
keeps model/offline/status behavior available without silently changing policy.

## Evidence boundary

`explain` and `why` remain deterministic. `assist` gathers bounded configuration and
trace evidence first, validates provider citations against opaque supplied IDs, and
now exposes a serialised Mantle `GroundedAnswer` alongside the historical response
dictionary. Inferred answers remain inferred; proposals remain proposals; refused
operations remain refused.

## Safety

Keys stay in terminal process memory. Proposals are validated, saved separately,
simulated, and never installed or executed automatically. Workspace containment,
symlink escape refusal, and the no-delete/no-shell/no-inline-Python generation policy
remain unchanged.
