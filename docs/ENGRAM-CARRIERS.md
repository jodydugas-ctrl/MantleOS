# Fresh Engram carriers

Shared development is in KPP PR #2. This promotion pins its exact reviewed
commit 70c363648faeb212a0a2992bf04cd8af44651dd3. Merge KPP first with an ordinary
merge preserving that commit; this MantleOS PR remains dependent on that review.

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
