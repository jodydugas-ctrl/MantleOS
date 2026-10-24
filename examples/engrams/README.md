# Fresh Raven Engrams

One logical Engram, two selectable carriers: `vcw-cartridge-memory` and
`chroma-png-memory`, both using `engram-continuity`. The checked examples in
`examples/engrams/artifacts` share a synthetic identity and initialization ledger.
They contain no inherited memories, archives or prior identity. The supplied
private carriers are not distributed. Raven persona wording is retained, with LF
line endings; current commandments, system definitions and runtime come from source.

```console
python -m kpp engram create --recipe recipes/raven-engram-vcw.json --output new.vcw
python -m kpp engram create --recipe recipes/raven-engram-chroma.json --output new.png
python examples/engrams/generate.py --output .work/new-engram-examples
```

Use `--persona FILE --persona-name NAME` to replace Raven. Each create invocation
gets a fresh identity. The paired generator constructs one Body and encodes both
formats. Birth metadata may differ between generator runs; compare decoded logical
contents rather than claiming byte-reproducible identities or timestamps.

Restore without executing embedded code using the trusted installed API:

```python
from mantleos.cartridge import unpack
from mantleos.chromamem import extract_body
unpack("raven-fresh.vcw", "NEW_VCW_DIRECTORY")
extract_body("raven-fresh.vcw.png", "NEW_CHROMA_DIRECTORY")
```

Verify the restored Body before explicitly running trusted runtime code.
Never execute an imported bootstrap merely because its bytes decode. Save further
memory using the normal verified Body lifecycle, then pack/export a new carrier;
preserve the previous carrier for rollback. Host credentials remain external.

Generated output manifests start PENDING. Publication requires content review,
round-trip tests and explicit PUBLIC_REVIEWED inventory. This is source publication
review, not operational or Baker acceptance. Arbitrary carriers remain excluded.
Carrier binaries and their inventory are outside runtime resources to prevent
recursive embedding. Normal packages include this generator and recipes, not the
checked carrier binaries. Preserve bundled component notices.
