# Attribution and licensing

| Component | Origin | Terms |
| --- | --- | --- |
| Shared MantleOS runtime, Anchor reference tooling, ChromaMem, SCAN | Supplied MantleOS Windows release and Raven cartridge | Original distribution has no selected open-source license; retained for private use. |
| Removed original VCW codec (historical attribution) | `jodydugas-ctrl/mantle-os`, commit `8e90a4f84998518d6abd8309dfa285a9ea7e8b24`, `examples/vcw/vcw_cube.py` | MIT, retained in `licenses/mantle-os-MIT.txt`. |
| Removed Book/AES-GCM excerpt (historical attribution) | `jodydugas-ctrl/MantleOS2`, commit `a624546a57abf463c8e160a17d34f0ea12e8646b`, `src/mantleos/runtime.py` | MIT, retained in `licenses/MantleOS2-MIT.txt`. |
| Hermes connection recipes and native qualification scope | Same MantleOS2 pin, `examples/hermes/adapter.py` and `certify_native.py` | MIT; recipes adapted to the unified runtime; original source hash in provenance. |
| Optional Hermes host | `nousresearch/hermes-agent`, commit `63279301bcbdc185c1b07b98a9312eb0c862f26d` | MIT, retained in `licenses/hermes-MIT.txt`; full upstream license stays in the ignored installation. Host source is not vendored. |
| Unicode case-fold reference data | Inherited Anchor engine | Original Unicode notice retained under `src/mantleos/anchor_engine/reference_materials/unicode/LICENSE.txt`. |

`docs/provenance.json` binds adopted material to source hashes and records local
adaptations. File names and version labels are not substitutes for those hashes.
Raven's private persona and experience are not included. Python interpreters and
third-party binary libraries are not vendored.

Generated portable Bodies carry the runtime's applicable notices. A public
release requires a separate licensing review; private repository status does
not change inherited license obligations.

The a2 release removes those historical codec/Book sources. Their notices remain
for attribution; current Hermes and Unicode terms still apply. The Notepad
profile is generated from canonical templates, with the Unicode data retained
once in source and embedded in each portable output.

KPP 1.0.0 contributes the canonical EMIT_TEXT/0.2 primer/limits and four teaching
specimens. The recipe example is retained as data for the shared-Anchor binding.
The archive SHA-256 is in docs/kpp.md and original component hashes are in
provenance.json. Copyright and MIT terms are retained in licenses/KPP-MIT.txt.
The supplied release evidence is historical, not certification of this integration.

The supplied experimental KPP 1.0.1-dev parallel-discovery derivative contributes
the two-scanner scheduling/join design and Qt declaration extraction adapted in
`src/mantleos/scan/discovery.py`. Its MIT terms remain in `licenses/KPP-MIT.txt`;
source-member hashes and the archive identity are recorded in provenance.json.
Traversal, bounded reads and publication are adapted to MantleOS; its original
patch receipts are distinguished from newly executed tests.

KPP general-tooling 1.0.0 also contributes the complete canonical construction
workflow, progressive workspace assets, examples and synthetic tests, promoted
to `mantleos.kpp` in a5. Its original MIT notice is retained in
`src/mantleos/kpp/resources/LICENSE` and `licenses/KPP-MIT.txt`. Shared Anchor,
CELL, execution and SCAN definitions come from the existing MantleOS source.
The standalone export retains all component licenses; KPP's MIT notice does not
relicense the complete private MantleOS distribution.
