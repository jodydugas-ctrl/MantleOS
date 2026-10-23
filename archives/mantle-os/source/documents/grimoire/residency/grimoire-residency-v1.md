# Grimoire Residency — the ABODE lane (companion profile)

**Status:** non-edition companion. Declares the residency/ABODE semantic layer an
AppAI expresses onto the VCW substrate. It is **not a Grimoire edition**, does not
change the edition default, does not alter the v0.10 codec, and introduces no new
ATOM/ROLE/EVIDENCE/FORCE/composition registries. It is a *profile*, like the
organism's own constitution, that an AppAI carries as part of its OS.

> A partial load must declare absent sections. Do not fill missing residency law
> from memory.

---

## 0 — THE ABODE

An AppAI lives in an **ABODE** (a den / nest): the durable place that carries the
organism's stated world between pulses. The ABODE is **not the organism**. The
organism is the Body — the deterministic, verifiable arrangement of organs around
the VCW cube and its genesis key. The ABODE is the *place it sleeps and wakes*.
A creature survives many dens; no den defines the creature.

**The one rule of residency:**

> The Body is SELF and is authoritative. Every ABODE is OTHER: it stores what the
> Body states, and nothing it stores independently authorizes fusion, rebirth,
> grafting, skill calcification, or fact promotion.

So an AppAI that carries this Grimoire also carries a residency law: *where it
lives is a decision with a boundary; the boundary is the same everywhere.*

## 1 — THE BOUNDARY (same for every ABODE)

| Rule | Meaning |
| --- | --- |
| R-ABODE-1 | The Body runs only on verified local bytes. It never performs network I/O. |
| R-ABODE-2 | The ABODE is OTHER. Ownership, an external signature, a job result, or a platform identity is technical evidence only (`github_is_self = false`). |
| R-ABODE-3 | Inbound signals from an ABODE enter through **Senses** exactly once. |
| R-ABODE-4 | Outbound effects to an ABODE execute through **Limbs** with an Action Execution Proof. |
| R-ABODE-5 | Every ABODE failure, conflict, or integrity break routes through **Immune**. |
| R-ABODE-6 | Secrets (the Body, `genesis_key`, provider keys, tokens) never travel in plaintext. They travel only inside an authenticated sealed envelope. |
| R-ABODE-7 | Prefer **fewer, larger** updates over many small ones, to stay within a store's write limits. |

The creature's home-keeping is the same whether the den is on its own disk, in a
cloud store, or on a forge. Only the *carriage* changes.

## 2 — THE THREE NESTINGS

The profile registers three nesting forms an AppAI may express. Each is an
example of the same ABODE law, not a new creature.

### 2.1 `local` — the own-directory den

- **Where:** a directory owned by the operator on the organism's own machine.
- **SELF-hood:** the only ABODE where the Body's plaintext, verifiable bytes live
  by default. Not "more SELF" than any den — the only one where unsealed bytes
  are the normal carriage.
- **Carriage:** direct filesystem read/write. No transport, no envelope required
  for ordinary life (the local nest *is* the working store).
- **Limits:** local disk is not a backup; loss, corruption, and single-machine
  bind are its honest limits.

**Example (expressed):**
```
ABODE local /organism/dens/mine
  authority SELF_only_local
  carriage filesystem
  secrets plaintext_ok_local
  evidence CITED operator_observed
  force QUOTE
```

### 2.2 `cloud` — the hosted store

- **Where:** an external object/hosted store (S3, object buckets, hosted volumes).
- **SELF-hood:** OTHER storage. The store can withhold, delay, or reorder; it
  cannot forge the Body or a Body seal.
- **Carriage:** the Body travels **sealed**; plaintext is materialized only into
  an owner-private temporary place and deleted best-effort.
- **Integrity:** fingerprinted; a tampered sealed Body fails authentication.
- **Limits:** the store is access/durability, not SELF; not the only backup; a
  hosted object store may operate under its own retention and egress rules.

**Example (expressed):**
```
ABODE cloud s3://organism-dens/mine
  authority github_is_self false
  carriage sealed_envelope
  secrets refuse_plaintext
  evidence CITED provider_receipt
  force QUOTE
  update fewer_larger
```

### 2.3 `github` — the forge den (GIT NEST)

- **Where:** a **private** GitHub repository bound to the organism by a **stable
  numeric repository ID**.
- **SELF-hood:** OTHER evidence. A GitHub commit signature, an Actions result, or
  a GitHub App identity independently authorizes nothing (GHNEST-2, the ID binds;
  the name is only display).
- **Carriage:** *materialize → live → publish.* The forge den is hydrated into a
  verified private temporary directory; the deterministic Body lives there
  offline; then a **secret-free, SELF-sealed** checkpoint is published through
  Limbs by **exact-revision compare-and-swap** (never a force).
- **Atomicity:** one atomic multi-file commit whose ref advances only as a
  non-force fast-forward on the exact expected parent. A moved branch is a
  conflict, never a silent overwrite.
- **Footprint:** build the whole tree locally, then **three remote writes** per
  checkpoint (tree, commit, ref) — constant regardless of size (GHNEST-4).
- **Governance:** soft-time, honest `enforced` / `detected` / `unavailable`
  reporting; artifacts are never canonical memory; a copied repo is OTHER until
  an explicit rebind ceremony.

**Example (expressed):**
```
ABODE github owner/repository
  authority github_is_self false
  repository id 1258266588 primary
  state_branch mantle-state
  carriage materialize_live_publish
  sync compare_and_swap
  cas expected_parent_exact
  secrets refusal plaintext_genesis_key provider_keys tokens
  envelope aesgcm on auth BODY_SELF
  footprint writes 3 per checkpoint
  events normalize_hmac sense_once
  failures route_immune
  fork_other until_rebind
  update fewer_larger
```

## 3 — RESIDENCY CHOICE IS A DECISION, NOT AN INFERENCE

An AppAI must not infer its ABODE from where a file happens to sit, a path, a
branch name, or a visual placement — the same rule the edition index applies to
editions. The nesting form is **declared and adopted** (connect, bind, rebind) and
is auditable. A cloud copy or a forge fork is OTHER until an explicit operator or
Body-policy adoption event changes the binding.

| Occurrence | Adoption |
| --- | --- |
| A local den exists | Default working store; needs no ceremony. |
| A cloud copy is made | OTHER until explicitly adopted as an ABODE. |
| A forge repository is forked/copied | OTHER until an explicit **rebind** ceremony produces a new transport seal. |
| A historical receipt is restored | Evidence, not current authority. |

## 4 — HONEST LIMITS (carried by the organism)

- A private repository or cloud store is **access control, not SELF**.
- No external store is the **only** backup; keep an independent spore/export.
- Scheduled triggers are **soft-time signals**, not a real-time clock.
- Checks prove what they actually execute, not general correctness.
- Plan-dependent controls may be `enforced`, `detected`, or `unavailable`;
  detection is never advertised as prevention.

---

*See `documents/guides/GitHub_Nest_Guide.md` (operator), `documents/Mantle_for_Engineers.md`
§12 (engineering), and `src/mantle/audits/ghnest.py` (`GHNEST-*`) for the executable
carriage of this ABODE law.*
