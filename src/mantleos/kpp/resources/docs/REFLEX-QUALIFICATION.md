# Experimental REFLEX/0.1 qualification

REFLEX is an opt-in, bounded JSON language and offline VM. It is not a new
Anchor profile, automatically calcified skill, live MIND, or production Body
installation. Existing `kpp reflex-plan`, `reflex-stage`, `reflex-test` and
Reflex/preview transfer refer to the earlier Python adapter workflow and remain
unchanged. `kpp reflex-book` is the separate experimental language surface.

## Reused source and verified starting point

See [reuse review](REFLEX-REUSE.md) and [exact provenance](REFLEX-PROVENANCE.json).
The maintainer-supplied 104-file ZIP exists; 103 listed checksums matched and the
original 64 tests were independently reproduced. Earlier narrative-only handoffs
could not establish this. Original receipts in `docs/reflex-history` are immutable
historical claims, not current tests. The language's prototype SPEC lives at
`src/mantleos/reflex_book/SPEC.md`. Its Int/GeoFix/Region dialect remains restricted;
roadmap Decimal/Quantity and other proposed operators are unsupported.

Approval verification now validates an explicit receipt field set, eliminating
the `test_reviewer` placeholder collision while retaining real self-approval,
HMAC, expiry and scope checks. HMAC establishes control of a local trusted key,
not reviewer identity or production permission. The SQLite registry remains a
disposable simulation and is never instantiated by carrier operations.

## Discover, validate and run offline

From a source checkout set `PYTHONPATH` to the absolute `src` path (PowerShell:
`$env:PYTHONPATH=(Resolve-Path src).Path`). No model or network is needed.

```console
python -m kpp pantry --id reflex-book --level source --check-source
python -m kpp language-plan --recipe recipes/reflex-book-qualification.json
python -m kpp reflex-book validate examples/reflex_book/location_rule.json
python -m kpp reflex-book compile examples/reflex_book/location_rule.json --output .work/location.rfx
python -m kpp reflex-book run .work/location.rfx --input examples/reflex_book/location_anomaly.json
python examples/reflex_book/qualify.py --output .work/reflex-qualification
```

The last command runs the original corpus and regressions, writes pinned source,
platform/Python/zlib, local timing and test evidence, and constructs two native
examples from one clearly synthetic Body. Original binary fixtures are stored as
hex text and materialized only in disposable test directories. Use
`--examples-only` to generate/recheck examples without unit execution; its report
explicitly labels tests NOT_RUN. Existing output directories are refused.

The generated `reflex-candidate.vcw` and `reflex-candidate.png` contain the same
canonical rule and fresh Raven Engram, empty initial ledger and no inherited
conversation or approval. Founding persona/identity and executable declarations
are identical between the pair. Outputs belong outside runtime resources; no
generated carrier, SQLite database, operator credential or approval is bundled.

## Native transport: verified Body, inert attachment

`native-pack SOURCE --carrier cartridge|chroma --output NEW.vcw|NEW.png` creates
a fresh Body using current lifecycle/carrier APIs. `native-verify` and
`native-unpack` require `--expected-sha256` from independently trusted metadata;
unpack also requires a new `--output` file. MantleOS uses the same commands under
`python -m mantleos kpp reflex-book`.

```console
python -m kpp reflex-book native-verify .work/reflex-qualification/reflex-candidate.vcw --carrier cartridge --expected-sha256 fd1edf144fed8b097f5a63b17415e33361bd8a3b0023f57295cf44165e13f207
python -m kpp reflex-book native-unpack .work/reflex-qualification/reflex-candidate.png --carrier chroma --expected-sha256 fd1edf144fed8b097f5a63b17415e33361bd8a3b0023f57295cf44165e13f207 --output .work/recovered-rule.json
```

This known digest is independently pinned for the checked synthetic location
fixture only. Do not trust a digest supplied by an arbitrary incoming carrier.

The exact two-file `REFLEX-DATA` attachment carries canonical `program.json` and
`manifest.json`. The experimental native attachment manifest reuses the checked
raw manifest fields with explicit native schema/edition, authority NONE,
installed false and executable_on_decode false. Only local trusted restoration
code reads it; carried runtime is never imported. Outer native carrier structure
and integrity, exact attachment contents, canonical IR and external digest are
all checked. Extra approval fields, wrong boolean types and malformed attachments
are refused. Decode returns inert IR, never VM execution or admission.

Raw RFC1 and strict two-file REFLEX ZIP are retained separately, with their
original 256 KiB ceiling and semantics. Native full Bodies use current carrier
limits plus a 16 MiB input-file ceiling. This is not an OS security sandbox.
ZIP re-encoding canonicality remains tied to Python/zlib; cross-runtime evidence
does not silently redefine that edition. Synthetic geometry is not a geofence
and must not be used for safety or clinical decisions.

## Evidence and remaining gates

Recipe/4 uses existing unbound measurable obligations, Python as implementation
language, and no new Anchor model. Its checks map to the REFLEX suite and generated
report. Existing `kpp test` is specifically the earlier staged Python-adapter
harness; do not fabricate that adapter's stage manifest to qualify this language.
The qualification runner supplies separate Taster evidence, never Baker acceptance.

M0–M3: experimental implementation and tests, not a qualified production Book.
M4: native data-transport compatibility evidence prepared for maintainer review.
M5: proposed experimental Pantry ingredient/recipe, not Baker accepted.
M6/M7: broader performance/host-isolation qualification and production adoption
remain deferred. Passing CI, checksums and receipt fields grant no host authority.

AppAI layered wake continuity, separate MIND sleep, scheduling, experiential age,
rebirth, automatic calcification and immune policies are later work. Existing
Body stasis, permissions, born identities, Engram examples and supported Anchor
profiles are unchanged. Source visibility does not relicense shared components.

The bundled prepared evaluator and evidence inspector are documented in
[REFLEX-BOOK.md](REFLEX-BOOK.md). Older imports alias the same implementation;
local delivery still does not grant qualification or Baker acceptance.
