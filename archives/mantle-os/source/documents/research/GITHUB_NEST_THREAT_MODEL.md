# GitHub NEST Threat-Model Delta

This is the threat-model extension for GitHub remote residency, in the same
table style as `THREAT_EXTENSION.md`. It adds the GitHub provider as a transport
and records the required response for each new threat. "Prevention" vs
"detection" vs "unavailable" is reported honestly by `mantle nest doctor`.

## New assets

- **Secret envelope / Body plaintext** — the only thing that must never leak.
- **Transport manifest + seals** — integrity/carriage; not SELF.
- **GitHub App credentials / provider secrets** — inbound to the transport only;
  never to the MIND, never persisted in the repo.
- **State-branch history** — durable lineage; pages/artifacts are not canonical.

## Threat table

| Threat | Required response |
| --- | --- |
| GitHub provider / API outage | Body runs offline on materialized bytes; publish/reconcile fails loudly and is queued; no silent drop of verified lineage. |
| Malicious or malformed repository content | All inbound bytes are OTHER; materialization is exact-revision; secrets are never opened from an unverified manifest; content never executes as Body. |
| Compromised / ephemeral runner | Actions default token read-only; runner does not receive decryption authority or write credentials; secrets open only in owner-local private directories. |
| Access drift (unexpected collaborator / install) | `nest doctor` reports unexpected collaborators/app installations; private visibility is enforced before any secret opening (GHNEST-16). |
| Repository deletion / transfer / visibility flip | Fails loudly; preserves last verified local/spore recovery material; a copied repo is OTHER until an explicit rebind ceremony (GHNEST-16). |
| Webhook disorder (late/out-of-order/duplicate/unsigned/wrong-installation) | HMAC verified; delivery GUID dedup; normalized events enter Senses exactly once (GHNEST-8); failures route through Immune (GHNEST-9). |
| Credential leakage (token, app key, genesis_key, API keys) | Plaintext-publication and secret-shaped-payload refusal before any publish (GHNEST-3); envelope opening capability never exposed to MIND (GHNEST-10). |
| Concurrent writers on the state branch | Expected-parent compare-and-swap refuses non-force overlap; no silent force/overwrite (GHNEST-6); conflict is an Immune event. |
| Tamper of manifest / sealed Body / Prime / ancestors / receipts | Fingerprint binding detects tamper (GHNEST-5); tampered material is never trusted as authority (GHNEST-19). |
| Remote unavailability during Body execution | Body has no network in Phase 1 (GHNEST-13); local checkpoint always precedes remote publication. |
| Scheduled heartbeat drift / missed pulse | Next heartbeat repairs the pulse; drift and drop are visible in the next receipt and Immune record (GHNEST-14). |
| Actions artifacts/caches used as canonical memory | Refused: artifacts are temporary evidence only (GHNEST-11); canonical memory is the fingerprinted NEST/VCW. |
| Rename / transfer changing the display name | Numeric repo ID is primary identity; name is drift-detection data (GHNEST-2); rebind ceremony needed to adopt a new identity. |
| Segment reconstruction divergence | Segment transport must reconstruct the exact checkpoint or matching fingerprint (GHNEST-20) before it ships. |
| Workflow permission / action-pin regression | Workflows declare minimum permissions and SHA-pin actions; audit doctor reports status (GHNEST-17). |
| Certification drift restored as authority | A stale certification is never restored as authority (GHNEST-19); checks are evidence, not SELF. |

## Trust boundaries

- *Body / SELF:* the genesis key and the local deterministic checkpoint. Never
  leaves the local, verified, plaintext context.
- *Transport (GitHub):* carries sealed bytes and receipts. It can withhold,
  delay, or reorder; it cannot forge a SELF seal or forge a Body result. It is
  OTHER evidence until verified and adopted.
- *MIND:* receives none of the GitHub tokens, handles, or envelope-opening
  capability (GHNEST-10). It may *propose* a GitHub action; the Body validates
  and Limbs performs the effect.

## Honest control reporting

For every plan-dependent preventive control, `mantle nest doctor` distinguishes:

- **`enforced`** — GitHub rules prevent the operation (e.g. rulesets block force push);
- **`detected`** — Body seals and doctor checks catch it only after the fact;
- **`unavailable`** — the account plan does not expose the control.

Detection is never advertised as prevention.
