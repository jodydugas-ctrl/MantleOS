# Optional Engram limbs

`engram-limbs` is an experimental Pantry ingredient implemented by
`mantleos.limbs`. It does not require Node-RED, a Prime MIND, a provider, or a fixed
limb count. Omit it for an ordinary agent. One limb can be useful without parallel
execution; several can also run sequentially under a one-worker budget.

Recipe/4 may select `engram-limbs` and declare `limb_composition` with schema
`mantle.limb-composition/1`, members, and workers. Each member declares id,
interfaces, and existing recipe obligation IDs. These are design requirements,
not runtime permissions. Private Journal paths, identities and grants belong in
the owner's runtime registry. Old recipes and workspaces are not migrated.

Initial limits are 32 members, eight workers, and 128 pending intentions. Zero
members use zero workers. Limits are implementation bounds, not anatomy or Anchor
semantics. Studio explicitly chooses eight roles and two workers.

## Operator and host interfaces

```
python -m mantleos limbs birth --out NEW.engram --founding VERIFIED_BODY_OR_CARRIER
python -m mantleos limbs init --root NEW_DIRECTORY --members MEMBERS.json --workers 1 --reviewed
python -m mantleos limbs submit --root DIRECTORY --limb ROLE --operation remember --input DATA.json --request-id UNIQUE_ID
python -m mantleos limbs run --root DIRECTORY --reviewed
python -m mantleos limbs status --root DIRECTORY
python -m mantleos limbs disable --root DIRECTORY --limb ROLE --reviewed
python -m mantleos limbs recover --root DIRECTORY --reviewed
```

MEMBERS.json is an owner-side list of objects containing id, journal and grants.
The small CLI registers only its built-in remember/digest specimen handlers.
The Python API accepts separately reviewed host callbacks and an independent
broker. Models and imported graphs cannot supply callback imports or approval.
Handler source, Journal identity, founding material, executable snapshot and
register are bound. An explicitly selected parent/custom founding source takes
precedence; otherwise the existing configured Raven factory requires setup.
Registration of an existing Engram retains its experience and needs owner review;
new factory births do not silently inherit another identity or history.

## Continuity and effects

Tasks are durably claimed under a short SQLite transaction. Computation runs
outside the global writer transaction, under a per-limb nonblocking worker lease.
Results append to the actual canonical Journal, then bind the coordinator record.
The coordinator is rebuildable task metadata, not another Engram interpretation.
Source/grant changes and revoked authority fail explicitly. Shared Body effects
still need their existing checked authority and transaction boundaries.

Recovery must acquire the worker lease, refusing active work. A retained canonical
result can be reconciled without running its handler again. An interrupted
callback with no result remains NEEDS_REVIEW. There is no exactly-once guarantee
for arbitrary external side effects and no automatic uncertain retry.

Callbacks execute as trusted local Python; this is not an OS sandbox or private
MIND isolation. The host is responsible for appropriate execution boundaries.
Hashes detect drift, not authenticity. Tests and limb results never grant Baker
acceptance. Status is operational metadata; verified result retrieval rechecks
the task/input/token and canonical record before projection.

Use the single-limb-agent, sequential-limb-agent and parallel-limb-agent recipes
as declarations, not passing acceptance receipts. Synthetic tests and qualification
reports must identify the actual worker/process behavior and tested scope.
