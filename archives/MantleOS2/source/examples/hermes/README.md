# Hermes Delta Specimen

`upstream.lock.json` names the exact Hermes commit certified by the alpha.2
construction gate. The source repository is not copied here. The checked-in
`seed/` directory is the complete public delta for the un-born reference Body.

Reconstruct the optional example candidate from its pinned upstream checkout with:

```console
git clone https://github.com/nousresearch/hermes-agent.git hermes-agent
git -C hermes-agent checkout 63279301bcbdc185c1b07b98a9312eb0c862f26d
mantle delta apply examples/hermes/seed --destination hermes-agent
mantle delta verify examples/hermes/seed --destination hermes-agent
```

Ordinary `mantle assimilate` now constructs a generic, un-innervated candidate;
it does not auto-select this reference adapter. The seed contains the public
`mantle/` construction payload, complete direct
source-nerve patch, upstream proof, and checksums. Use `mantle delta apply`,
`mantle delta verify`, and the explicitly approved `mantle delta reverse` to
exercise reconstruction. Runtime identity, unique Personality, keys, provider
material, communication transcripts, and live VCW data are excluded.

The example-only adapter, focused tests, and native-behavior comparison are
recorded here and in `NATIVE_BEHAVIOR_CERTIFICATION.md`. The same 85 upstream
tests can run against pristine and constructed checkouts in the manually
dispatched Hermes reference workflow, not on normal MantleOS2 PRs or releases.

The source patch has eight direct Nerves. Its efferent Nerve records a redacted
AppAI Limb proposal at Hermes's native tool-authority boundary; it neither
registers Mantle as a plugin nor replaces Hermes's existing guardrails. Common
turn seams cover terminal and gateway operation; two additional Nerves record
their real session shutdown boundaries.
