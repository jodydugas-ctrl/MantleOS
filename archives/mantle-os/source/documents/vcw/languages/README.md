# VCW Language Forge / Tome / Book — document index

The VCW Language Forge is the meta-Book that forges the four-stream language
each VCW layer speaks. The Grimoire — Mantle's original semantic profile — is
upgraded into the first FROZEN Book of this system:

```text
TOME: OPERATIONAL
BOOK: reason-evidence
EDITION: 0.10
DIALECT: mantle-standard
IMPLEMENTATION LINEAGE: grimoire-v0.10
```

The Frozen Grimoire v0.10 (documents/grimoire/editions/grimoire-v0.10.md) is
**not rewritten**. `reason-evidence@0.10` delegates to the frozen v010 codec,
so every existing v0.10 byte decodes identically. Old memory remains
interpretable under the law that created it.

## Documents

| Path | Contents |
|---|---|
| `VCW_LANGUAGE_FORGE_v0.2.md` | The single meta-specification: substrate law, forging procedure, capsule template, generator prompt. |
| `tomes/TOME_OPERATIONAL.md` | OPERATIONAL Tome — reason-evidence@0.10 (FROZEN, lineage grimoire-v0.10). |
| `tomes/TOME_COMPUTATIONAL.md` | COMPUTATIONAL Tome — computational-thought (CANDIDATE, codec owed). |
| `tomes/TOME_USER_LANGUAGES.md` | USER LANGUAGES Tome — user-language / english-user-chat (CANDIDATE, codec owed). |
| `tomes/TOME_SPORE.md` | SPORE Tome — agent-instruction / spore-standard (CANDIDATE; how to *be* a spore). |

`TOME_*` files are imported byte-identical from the forge work (per the
migration plan §27).

## Code

```text
src/mantle/vcw/languages/
    types.py       BookKey / BookManifest, lifecycle + conformance axes
    errors.py      fixed refusal codes + ENCODING REFUSED
    canonical.py   one canonical serialization + digest recipe
    codec.py       the Book codec protocol
    manifest.py    manifest construction + validation
    registry.py    the Body-approved Book registry
    framing.py     framing library (framed-run / preorder-tree / sequence)
    integrity.py   rotated (authoritative) + xor (legacy) parity, fingerprints
    data_frames.py canonical DATA frames + full-digest references
    adoption.py    Body/operator adoption receipts
    books/
        reason_evidence/    the OPERATIONAL Book (FROZEN, v0.10-delegating)
```

## Law

Presence is not authority. Decoding is not adoption. Force is not
authorization. A model cannot promote a Book, record, rule, or carrier by
confidence or by wording.
