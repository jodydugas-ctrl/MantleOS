# REFLEX/0.1 M4 — Carrier integrity and isolation review

**Status:** `M4_EXPERIMENTAL_TRANSPORTS_TESTED`; **not** `M4_ACCEPTED`, `BOOK_FROZEN`, `BODY_QUALIFIED`, `BAKER_ACCEPTED`, or `NATIVE_CARRIER_ADOPTED`.

**Scope:** This is an offline additive overlay over M3. It introduces two deliberately separate **REFLEX-only data transports**. It does **not** alter production `src/mantleos`, the KPP pin, ChromaMem, VCW Cube, Cartridge, or the M3 registry.

## Implemented contract

- Canonical REFLEX IR is validated with the existing M0 strict parser and must match exact canonical UTF-8 bytes. Reordered keys, whitespace and other noncanonical source cannot masquerade as a fixed carrier payload; `carrier-pack` accepts a readable source and normalizes it *before* encoding.
- `CarrierAdapter` protocol: `carrier_id`, `encode(canonical, manifest) -> bytes`, `decode(blob) -> (canonical, manifest)`, `verify(blob, expected_digest) -> report`.
- A carrier manifest binds exact program bytes, program ID, Book edition, SHA-256 and the transport edition. It **must** contain `authority: NONE`, `installed: false` and `executable_on_decode: false`; any grants/receipts/importable code/new fields are refused.
- `reflex-raw/0.1-experimental`: standalone RFC1 frame (`magic[4]`, `manifest_length:u32be`, `program_length:u32be`, `sha256(domain || manifest || program)[32]`, canonical manifest JSON, canonical program JSON). Digest binds the whole data section but is **not** an identity signature.
- `reflex-zip/0.1-experimental`: standalone ZIP with exactly two regular, ordered members, `manifest.json` and `program.json`. Rejects extra paths, duplicate entries, ZIP comments, symlinks, encrypted members, external entries, oversized declared/uncompressed members, malformed/truncated archives and noncanonical local/archive metadata. This is **not** a MantleOS Cartridge.
- An independent **caller-supplied** `--expected-sha256` is mandatory for CLI verify/unpack and must match exact canonical REFLEX program bytes. Self-consistent malicious archives cannot choose their own trusted digest via a manifest.
- Decoding never performs VM execution, `ExperimentalRegistry.install`, carrier import, M3 approval or BODY mutation. `carrier-unpack` only writes a new canonical `.json` file with exclusive creation (existing files are not overwritten).

## Sizes and refusal codes

- Canonical payload: 1–65,536 bytes; canonical manifest: 1–4,096 bytes; full carrier: <=262,144 bytes.
- New refusal codes: `E_CARRIER` malformed/unsupported carrier, `E_CANONICAL` noncanonical JSON manifest/program. Existing `E_INTEGRITY` and `E_SIZE` remain in force. ZIP decompression errors become a stable `E_CARRIER` refusal rather than leaking zlib exceptions.
- Only `raw` and `zip` transport selectors are admitted. Unknown formats/editions refused. No code execution or installer on decode.

## Run the conformance suite

```bash
python -m unittest discover -s tests -v
python -m experiments.reflex_book.tools.record_m4_test_receipt
python -m experiments.reflex_book.cli carrier-pack examples/reflex_book/location_rule.json --carrier raw --output .work/location.rfc
python -m experiments.reflex_book.cli carrier-pack examples/reflex_book/location_rule.json --carrier zip --output .work/location.reflex.zip
```

Use the program SHA-256 reported by `carrier-pack` as a locally observed digest; for a real *trust check*, obtain the expected SHA-256 independently through a trusted host, not from the untrusted carrier itself:

```bash
python -m experiments.reflex_book.cli carrier-verify .work/location.rfc --carrier raw --expected-sha256 EXPECTED_HEX_FROM_TRUSTED_HOST
python -m experiments.reflex_book.cli carrier-unpack .work/location.reflex.zip --carrier zip --expected-sha256 EXPECTED_HEX_FROM_TRUSTED_HOST --output .work/location.extracted.json
```

## Native carrier decision — still blocked

The current MantleOS `cartridge.pack()` requires a **verified full BODY directory**. `chromamem.export_body()` also requires a verified full BODY, with explicit bootstrap/manifest/Engram semantics, and is not a generic carrier serializer. The private `chromamem._encode` record-tape helper is **not a supported external API** and should not be called from experimental REFLEX for nominal M4 acceptance. A ZIP of two REFLEX files is **not a Cartridge** simply because both use ZIP internally. Historical VCW RGBA remains a different, archived substrate; the ambiguous VCW Stack format is still blocked pending its actual specification.

**Decision required:** Should an official reviewed MantleOS **read-only file attachment interface** be published for carrying non-governing REFLEX candidate bytes inside a verified BODY export? If not, choose a separately approved standalone native adapter and publish format/test vectors before making M4's final gate claim. Native adoption must require the usual independent BODY permission/admission process. No ad hoc KPP pinned edits.

## Results and remaining checks

Evidence receipt is `TEST-RECEIPT-M4.json` (observed results on one local Python platform). Suite includes earlier M0–M3 tests plus conformance, two-program roundtrips, seeded mutations, active payload manipulation, ZIP-bomb limits, archive confusion, authority-smuggling refusals and no-runtime-invocation checks. Output sizes/latencies are *measured*, not forecast; ZIP byte reproducibility is **specific to local CPython + zlib** and is not a cross-platform format guarantee.

- [x] Exact canonical IR round-trip through two *experimental* carriers.
- [x] Corrupted container and mismatched host digest refused; no side effects.
- [x] Previous M3 conformance preserved in the extracted overlay.
- [ ] Independent approval of a **real MantleOS native carrier adapter** (M4 exit criterion).
- [ ] Review/accept M0 language contract, M3 authority model and M4 refusal semantics.
- [ ] Run full MantleOS/KPP regression suites in a compatible repository checkout.
- [ ] Cross-runtime/cross-OS/zlib golden vectors and performance evidence.
- [ ] Production review/Baker acceptance, audited integration, and real trust-key management.

**Next action:** reviewer examines and chooses native carrier interface; do not merge as a qualified BODY profile and do not claim full M4 exit.
