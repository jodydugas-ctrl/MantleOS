# Fresh Engram carriers

Shared development is maintained in [Kitchen Party Protocol](https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol).
The published Engram ingredients were introduced by [KPP PR #2](https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol/pull/2).
The original Engram examples were reviewed at KPP commit `70c363648faeb212a0a2992bf04cd8af44651dd3`, retained by its ordinary merge. Their checked sample bytes remain unchanged.
The currently promoted shared source, including subsequent experimental additions,
is pinned in `upstream/kpp.lock.json`. Future changes require reviewed promotion.

```console
python -m mantleos kpp engram create --recipe src/mantleos/kpp/resources/recipes/raven-engram-vcw.json --output fresh.vcw
python -m mantleos kpp engram create --recipe src/mantleos/kpp/resources/recipes/raven-engram-chroma.json --output fresh.png
python examples/engrams/generate.py --output .work/new-examples
```

The same Engram supports either carrier. Raven is the default only for this
Engram constructor; --persona FILE --persona-name NAME replaces it. Each create
invocation starts a fresh identity; the paired generator uses one synthetic Body
for both encodings. Current initialization has an empty memory ledger. The checked
samples contain no inherited conversations, archive, identity or approval.

See examples/engrams/README.md for the trusted restoration APIs, host boundaries
and current-source provenance. The provided personal carriers remain external.
Reviewed example binaries are explicitly inventoried outside runtime resources;
ordinary distributions contain the generator and recipes, not these binary samples.
All existing licensing and component notices continue to apply.

## Offline memory persistence demonstration

After restoring the README's disposable `.work/showcase-vcw` copy, deliberately
append a synthetic observation and save new carriers. The checked originals remain
unchanged; no model or remote service is involved.

```python
from pathlib import Path
from mantleos import cartridge, chromamem, engram, lifecycle

body = Path(".work/showcase-vcw")
prior = (body / "ENGRAM.jsonl").read_bytes()
lifecycle.admit(body, "synthetic-memory", {"observation": "offline showcase"},
                expected_head=engram.head(body / "ENGRAM.jsonl"))
assert (body / "ENGRAM.jsonl").read_bytes().startswith(prior)
cartridge.pack(body, ".work/showcase-saved.vcw")
chromamem.export_body(body, ".work/showcase-saved.png")
cartridge.unpack(".work/showcase-saved.vcw", ".work/showcase-reloaded-vcw")
chromamem.extract_body(".work/showcase-saved.png", ".work/showcase-reloaded-chroma")
for restored in (".work/showcase-reloaded-vcw", ".work/showcase-reloaded-chroma"):
    cartridge.verify(restored)
    assert engram.read(Path(restored) / "ENGRAM.jsonl") == engram.read(body / "ENGRAM.jsonl")
```

All destinations must be new. Run the trusted maintained implementation; carrier
decoding does not execute embedded programs or authorize a host. Raven/custom-persona,
fresh-state, corruption, overwrite-refusal and save/reload tests are linked from
the README showcase. Passing these tests is separate from Baker acceptance.
