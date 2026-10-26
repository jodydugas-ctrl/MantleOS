# Inactive Body attachments

`mantle.attachments/1` carries opaque data inside a verified Body. Its optional
`ATTACHMENTS.json` contains exactly `schema` and `attachments`. Each record has
`sha256` (lowercase SHA-256 over attachment bytes), `bytes`, `media_type`, and
`path` (`attachments/<sha256>.bin`). Digests are unique. Up to 64 attachments,
each 1–262144 bytes, are supported. The index is limited to 65536 bytes. Unknown
versions, fields, extra files, unsafe paths and inconsistent bytes are refused.
Bodies without attachment metadata retain their existing behavior.

```powershell
$env:PYTHONPATH = 'src'
python -m mantleos --body BODY attachment add CANDIDATE.rfc --media-type application/vnd.mantle.reflex-raw --expected-sha256 ATTACHMENT_BYTE_DIGEST --output NEW_BODY
python -m mantleos --body NEW_BODY attachment inspect
python -m mantleos --body NEW_BODY attachment extract --sha256 ATTACHMENT_BYTE_DIGEST --output NEW_CANDIDATE.rfc
```

The Python API is `mantleos.attachments.add(body, payload: bytes, *, media_type,
expected_sha256, output)`, `inspect(body)`, and `extract(body, *, sha256, output)`.
Operations refuse interrupted transactions and existing destinations. Adding data
locks the source, stages a new copy, refreshes the compiled source bindings and
Body manifest, validates, then publishes to a separate destination. Original
identity, history, program sources and program state are preserved. The compiled
envelope changes because it binds the added bytes. No attachment-removal or
in-place mutation operation is supplied.

Public `cartridge.pack/unpack` and `chromamem.export_body/extract_body` retain
attachments as ordinary manifest-bound files. Chroma export requires `.png`.
Verification treats payloads as opaque data; it never imports or executes them.
Reports explicitly record authorized=false, installed=false, executed=false.
The attachment digest supplies integrity linkage, not authenticity or approval.

## Experimental REFLEX adapter

The REFLEX handoff's `experiments.reflex_book.carriers.native` adapter validates
the existing raw RFC1 envelope before attachment and after extraction. Its
`attach(body, envelope, *, expected_program_sha256, output)` and
`extract(body, *, attachment_sha256, expected_program_sha256, output)` require
the independently supplied digest of the canonical program. That digest differs
from the digest of the complete raw attachment. Raw envelope, manifest and source
limits remain in force. The adapter is experimental source supplied with the
continuation bundle; the generic runtime has no REFLEX-language dependency.

Run the bundle's `demo_native.py` from its SOURCE directory with PYTHONPATH set to
the associated checkout's `src`, and pass an unused `--output` directory. It
constructs a synthetic Body and carries the example through Cartridge and Chroma.
This implementation is available for review; tests supply no formal Book freeze,
native execution profile, production admission or Baker acceptance. Existing KPP
Reflex staging remains a separate workflow feature.
