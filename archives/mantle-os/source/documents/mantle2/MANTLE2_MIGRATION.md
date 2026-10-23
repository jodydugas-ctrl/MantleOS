# MantleOS 2.0 migration guide

`2.0.0rc1` is a deliberately breaking candidate. Migration always writes a distinct
artifact or nest and never replaces historical residents, spores, or lifecycle evidence.

## Resident protocol

Maintained residents declare `mantle-resident-v2`. Plain text is conversation input;
slash commands are Body maintenance. Canonical commands are `/key`, `/model` (with
`/mind` as an alias), `/offline`, `/status`, `/help`, `/provider-test`, `/evidence`,
and `/quit`. Host integrations may register extensions but cannot redefine these
commands. Every successful configuration mutation emits `BODY_CONFIGURATION_CHANGED`.

## Evidence and authority

Use `mantle.contracts` for claims and answers. Verified claims require an
`EvidenceRef`; user statements, model interpretations, and proposals retain their
own statuses. Repository certification, application certification, historical receipts,
and current runtime authority are separate.

Spore inspection is safe and inert by default:

```text
python -m mantle spore inspect <spore.png>
python -m mantle spore inspect <spore.png> --include-conversation
```

External hatch/graft activation requires a fresh target-bound `LifecycleAuthorization`;
SELF-vault reconstruction retains its Body-owned recovery birthright. Genesis keys remain
independently minted and are never derived from a spore.

```text
python -m mantle lifecycle authorize hatch seed.png new-nest --approve --out=hatch-auth.json
python -m mantle hatch seed.png --out=new-nest --auth=hatch-auth.json

python -m mantle lifecycle authorize graft patch.png workspace/host --approve --out=graft-auth.json
python -m mantle graft patch.png host --workspace=workspace --auth=graft-auth.json
```

Authorization binds the action, artifact SHA-256, normalized target, expiry, and nonce.
Mantle consumes it before target creation, builds in a unique same-parent stage, journals
each phase, verifies required artifacts and gates, and atomically promotes. Inspect with
`mantle lifecycle status`. Resume an artifact-verified interruption with `mantle lifecycle
resume`; quarantine any earlier stage and restart under fresh authorization.

## Explicit inert migration and rebind

Migration changes format declarations but never activates its output:

```text
python -m mantle migrate-germ old-germ.json --out=germ-v2.json
python -m mantle migrate-spore old-spore.png --out=spore-v2.png
python -m mantle migrate-resident old-nest --out=resident-v2
python -m mantle rebind host --preserve-old --out=resident-v2 --certify
```

Resident migration uses a same-parent staging tree and `migration_journal.json`. Rebind
requires `--preserve-old`; certification applies to the new nest only. Migration or failed
certification cannot modify the source resident or historical receipt.

## Assimilation coverage

The shared scanner covers conservative C/C++ declarations and bodies, constructor
initializer lists, balanced Qt connects and helper-wired actions, Qt UI widgets/actions/
connections, QRC resources, CMake targets/sources, and Rust fallback structure. Reports
emit `mantle-host-evidence-v3`, `InsertionState`, runtime verification separately, and
explicit parser gaps. Dominant unsupported first-party substrates are `BLOCKED`.

## Result and gate semantics

Lifecycle and gate results use `PASS`, `PARTIAL`, `FAIL`, `REFUSED`, or `INTERRUPTED`.
Exit status `0` means PASS, `1` means FAIL/REFUSED, `2` means CLI usage error, and `3`
means PARTIAL. `python -m mantle check --json` adds a machine-readable terminal result;
only a full strict PASS is repository certification.

## Bounded Body additions

Mantle 2 adds receipt-backed `EnergyPolicy`/`SpendAuthorization`, disabled and fake
`ResourceOfferInbox` adapters, visible `FaceAttestation`, optional non-authorizing
`LineageAttestation`, and deterministic read-only ancestor queries. Real credential-store
adapters are future optional platform work; plaintext credential files remain refused.

## Compatibility

Legacy germs/residents remain inspectable and must be explicitly migrated before a
Mantle 2 certification claim. The Spore-PNG carrier remains format v2; germ, host
evidence, GUI coverage, lifecycle authorization, and resident protocol schemas carry
their own versions.
