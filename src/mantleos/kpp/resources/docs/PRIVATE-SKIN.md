# Private Skin and MIND pilot

Opt-in experimental controller API: `mantleos.appai.private_session` takes a
`Skin`, an independent Ed25519 signer, a private MIND adapter, and an owner policy.
The controller provisions these outside courier-controlled files and tools.
`python -m mantleos skin --help` provides trusted operator Journal import,
verification and sealed export. Provision a random 32-byte key privately first.
Cryptography is an optional dependency; unavailable crypto fails explicitly.

## Responsibility contract

Skin stores shared canonical `mantle.engram-record/1` records (and explicit
historical Raven records) inside individually authenticated AES-GCM ciphertexts.
Authenticated keyed token deltas produce a rebuildable in-memory search index.
Appends authenticate only the new event; cold objects are not rewritten on turns.
Startup verifies all ciphertext metadata and the object inventory. It opens no
historical record payload until retrieval or replay requires one. Constitution
and selected quarantines are decrypted when the private controller opens.
Object insertion recomputes the object inventory; it is a cold-path operation.

`private_appai.design()` uses existing canonical Anchor applications. Its readable
design view is PRIVATE-SKIN.anchor.txt. Host-generated Anchor messages validate
semantic proposals. Python performs storage/cryptography and orchestration;
this does not qualify a new executable Anchor profile.

## Controller and courier

The trusted controller calls `admit_user(request_id,user)` on actual UI intake.
The courier can then submit only that binding using `courier({op,args})`.
Supported operations are `status`, `encounter`, and `result`; encounter/result
arguments are request_id and user. Courier input cannot select source paths,
keys, provider routes, policies, SQL, raw memories, or PRIMER export.

The private MIND receives the complete constitution PRIMER and two recent exchanges plus up to six matching
records within 16 KiB, reporting omitted record count. Ordinary replies use one generation. Checked body.status or bounded engram.query actions use the shared
CheckedActionExecutor through a narrow Skin ledger adapter and the independent
read broker. Effect stages and the verified observation are durably retained before
the second model frame. Restart resumes from that observation without another
action. Incomplete attempts require review; a second action under the same request
is refused. No general filesystem/tool action is implemented in this pilot. Owner policy
controls conversation, expiry and allowed model labels; revocation is checked
before commit and replay. Policies are controller inputs, never model authority.

The controller pins `public_key(signer)` independently. Its display calls
`verify_release(release,public,identity=...,request_id=...,user=...)` before showing the exact
reply. This checks the signature, request/input binding and exact reply digest.
It must also pin the intended identity and retain its latest accepted checkpoint.
Streaming private drafts directly to users bypasses this contract.

HostMind requires an explicit isolation checker and a host-owned worker callback.
A checker must actually demonstrate the courier cannot read private state, keys,
process memory or worker transcripts. The supplied synthetic checker is a fixture,
not proof of Windows or Linux isolation. No qualified host worker is bundled.
The existing Hermes graft still injects a public PRIMER and is NOT a private
Skin deployment. Use the separate controller pilot rather than attaching private
keys/state to an ordinary Hermes installation.

OpenRouterMind is an alternative explicitly selected by the owner. It requires
a model, provider allowlist, token/price ceilings, call budget and private key.
No request occurs at import or construction. HTTPS calls disable fallback and
require privacy routing parameters (data_collection=deny, zdr=true). Unknown
outcomes consume a call; no automatic retry. The selected provider sees private
context. Price ceilings, 128 KiB maximum frame and call budget give bounded
request exposure; use an independently capped provider credential for account
spending enforcement. Transport tests are synthetic; live routing is untested.

## Preservation and recovery

import-journal verifies current Journal source/PRIMER and encrypts the complete
original SQLite carrier as an immutable origin object, preserving all prior
executable snapshots, attachments and request bindings. Exact canonical records
are imported into Skin. New private turns retain their distinct source label.
There is no silent format rewrite or automatic plaintext cartridge/PNG export.
Explicit import-legacy-skin supports the historical raven-skin/1 envelope using
an owner-supplied selector file and current trusted Journal verification. Both
the historical encrypted envelope and complete decrypted Journal are retained
inside new encryption. Resolve pending encounters before import. No original
Raven was decrypted during qualification. The import-native-prototype operation supports raven.sealed-records/1 with an
explicit native vault key, legacy founding Skin and selector. It verifies the
full native keyed chain/index and every imported legacy record before mapping
newer events into canonical records with prototype-bridge provenance. The whole
consistent native SQLite image and exact authenticated payloads are retained in
new encryption. Original operator grants are data and grant no new authority.
Failed migrations retain a staging file for review and do not publish the named
output. The adapter was exercised with manufactured data, not the private Raven
vault; other native schema editions fail explicitly.
The recover command lets SQLite recover its local transaction, then verifies
all encrypted objects and records; inconsistent state requires owner review.

Sealed export uses SQLite backup and includes no raw key or signer. Receiving
Bodies require separately provisioned keys and independently pinned signer/public
identity. Operator verification checks every AEAD object and canonical record.
`checkpoint()` and `require_checkpoint()` detect divergence or rollback behind a
controller-retained head. Rolling back the entire controller and vault together
requires an independent witness to detect; no witness service is installed.

Quarantine appends a private-quarantine record through `mantleos.immune` and takes
effect on the next controller open. Canonical records remain intact. Diagnostics
contain reason codes and digests, not raw private detail. Admission, policy edits,
key provisioning and recovery are operator-side Python operations; no courier
operation grants them.

## Qualification boundary

Run `python tools/private_skin_specimen.py --output NEW_DIRECTORY` for synthetic
0/100/1000 histories, 20 warm samples and optional 20 MiB objects. A generic model
may still disclose or infer persona traits through its intended replies; encryption
does not establish semantic non-disclosure. Persona fidelity and hidden reasoning
are not proven by signed continuity. No actual Raven material ships here.

Windows ACLs, Linux separate users, protected private worker transcripts, actual
UI gating, live host cognition and live OpenRouter calls require deployment
qualification. They are explicitly untested in this delivery. Unsupported host
isolation must fail closed; selecting another provider requires owner action.

The read-only tools/qualify_private_skin.py harness probes existing private state, key and worker-transcript canary files plus a live Body process handle using an independently provisioned courier command. It creates no users or services and changes no ACLs. A same-user Windows run correctly returned UNQUALIFIED: the courier could read all canaries and obtain a Body memory handle. Separate-user Windows/Linux runs remain untested; this harness does not certify model-provider transcript APIs.

OpenRouter provider routing slugs and returned display labels can differ. Configure both explicitly when needed: providers=["openai"], provider_labels=["OpenAI"]. The result must match the configured model and response-label allowlist; unsupported response shapes fail closed. This is consistency checking against a trusted service, not cryptographic provider attestation. See https://openrouter.ai/docs/guides/features/router-metadata .
The whole developer ZIP, historical known-selector Skin and any plaintext founding copies must also stay outside courier access during deployment. Protecting only the new vault does not protect those older copies.

[Qualification and measurements](PRIVATE-SKIN-VERIFICATION.md) distinguish executed synthetic checks from unqualified deployment behavior.
