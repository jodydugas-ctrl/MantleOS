# GitHub NEST Guide

This guide explains how to use GitHub as an **optional remote NEST** for an AppAI,
following `documents/research/GITHUB_NEST_ADR.md`. It is written for the operator;
for the trust-boundary and credential model see `Mantle_for_Engineers.md`.

> One-sentence rule: **Materialize GitHub into a verified local NEST, let the
> deterministic Body live there, then publish a secret-free, SELF-sealed
> checkpoint through Limbs using exact-revision compare-and-swap — never let
> GitHub become SELF, the Heart, or Phase-1 authority.**

## What GitHub provides (and what it never is)

GitHub supplies storage, events, ephemeral workers, checks, and governance. It is
**OTHER evidence**. A GitHub commit signature, an Actions result, or a GitHub App
identity does not independently authorize MIND fusion, rebirth, grafting, skill
calcification, or fact promotion. The Body's genesis key remains the cryptographic
SELF.

The ABODE/residency law that makes GitHub a den and never the creature is carried
in the organism's Grimoire: the non-edition
[`residency/grimoire-residency-v1.md`](../grimoire/residency/grimoire-residency-v1.md)
companion, which defines the `local`, `cloud`, and `github` nesting forms under one
residency rule.

## Layout

- **Host repository** — the source you already have (may stay public).
- **One private NEST repository per organism** — carries the sealed NEST. This is
  the recommended deployment. A same-repository layout is an explicit advanced
  choice with privacy/recursion/growth/access coupling.

## Creating the remote NEST

Use a **GitHub App** (preferred) or a short-lived token, installed only on the
NEST repository. Store the credential in a local `AUTH.json` (never commit it):

```json
{ "token": "<short-lived-token>", "token_type": "token" }
```

## Commands

```text
python -m mantle nest inspect github:OWNER/REPO --auth=AUTH.json
python -m mantle nest connect LOCAL_NEST github:OWNER/REPO --auth=AUTH.json
python -m mantle nest pull  github:OWNER/REPO --out=LOCAL_DIR --envelope-key=KEY --auth=AUTH.json
python -m mantle nest push  LOCAL_NEST github:OWNER/REPO --envelope-key=KEY --auth=AUTH.json
python -m mantle nest sync  github:OWNER/REPO --auth=AUTH.json
python -m mantle nest doctor github:OWNER/REPO --auth=AUTH.json
python -m mantle nest install-template audit|heartbeat [--out=DIR]
python -m mantle nest disconnect github:OWNER/REPO --preserve-remote
```

- `--envelope-key=KEY` — a 32-byte key file. **Keep the key safe.** Without the key
  the remote `body.sealed` cannot be opened. Omitting it mints an ephemeral key for
  a labeled personal prototype. Production should use GitHub OIDC to an external
  KMS so no long-lived decryption credential is stored in the repository.
- `--transport=fake` — deterministic in-memory transport for dry runs/tests.

## Staying inside GitHub's limits

The publisher builds **the entire tree locally in a temporary directory** and then
performs exactly **three wire writes per checkpoint** (one tree with all blobs
inline, one commit, one non-force ref update) — **constant regardless of NEST
size**, never N per-file API calls. The Body runs fully offline; only the sealed,
secret-free checkpoint crosses the network. This is enforced by GHNEST-4
("fewer, larger updates").

## Lifecycle

- **Connect** binds a local NEST to a remote by stable numeric repository ID.
- **Push** publishes one atomic, secret-free, SELF-sealed checkpoint by
  exact-revision compare-and-swap. A moved branch is a conflict — fetch and
  reconcile, never force.
- **Pull** materializes the remote into a private temp directory and opens the
  envelope only after the manifest hash and private visibility are verified.
- **Doctor** reports repository privacy, numeric ID, state branch, manifest
  presence, and plan-dependent controls honestly as `enforced` / `detected` /
  `unavailable`.

## Recovery and honesty

- A private repository is **access control, not SELF**. GitHub is not the only
  backup; keep an independent spore/export.
- Scheduled Actions are **soft-time signals**, not a real-time clock; a dropped run
  becomes visible in the next heartbeat receipt and Immune record.
- Checks prove what they actually execute, not general correctness.
- Pages is disabled on the NEST repository; Actions artifacts are **never
  canonical** memory — they carry temporary evidence only.

See `documents/research/GITHUB_NEST_THREAT_MODEL.md` for the full threat table and
the `GHNEST-*` invariant list in `src/mantle/audits/ghnest.py`.
