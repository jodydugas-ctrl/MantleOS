# MantleOS

**Build living software. Give it a competent Body before attaching a MIND.**

This is the current MantleOS experimental testbed, prepared from the verified
23 October 2026 r3 container with a fresh Git history. Historical projects live
under `archives/`; their histories are data, not ancestors or supported runtime.
[Kitchen Party Protocol](https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol)
remains independently maintained, with the exact shared source selected by a
reviewed Git-commit pin. Public viewing does not relicense bundled components.

Explore the [working Engram examples](#working-engram-examples): fresh Raven
memory in two KPP-selectable carrier formats.

For an AI host, start with [MANTLE.md](MANTLE.md). Instructions and runnable
capabilities ship together: scanning, Anchor coding, app creation, portable
executable thoughts, memory, AppAI missions, and cartridge/PNG continuity.
This edition removes obsolete format readers and duplicate resources; it has no
artificial size cap. The earlier instruction-only kit is superseded.

MantleOS is Jody Dugas's experimental testbed for exploring how AI can embody
code. It uses a Python framework for biologically inspired software:
functional Bodies, optional cognition, memory, continuity and reviewed adaptation.
The experiments test concrete behavior and preservation; their results do not
establish broader claims about AI identity or consciousness.

This is **0.1.0a9, preview-first construction in one MantleOS/KPP system**. It brings together selected
Mantle OS, MantleOS2, MantleOS 4, and Raven mechanisms. It does not inherit their
historical certification claims. [Capability status](docs/heritage.md) and
[verification results](docs/verification.md) describe the actual delivery.

[Kitchen Party Protocol](https://github.com/jodydugas-ctrl/Kitchen-Party-Protocol)
is independently maintained as the development protocol. Shared changes originate
in KPP and are promoted identically through reviewed offline updates. MantleOS
is the primary repository for this experimental testbed.

KPP supplies the preferred construction contract. CELL means the smallest unit
produced by its kernel. All Anchor uses share immutable singularities and only
BlackHole, WhiteHole, or Neutral types; recipe/3 and explicitly bound recipe/4 obligations add attributes to those Anchors.
KPP is the construction subsystem in this same implementation, also exported
as its own standalone project. `python -m mantleos kpp --help` exposes its full
recipe, Pantry, workspace, Reflex, testing, GUI and Baker-acceptance tooling.
The standalone `python -m kpp` entry point aliases those exact modules.
See [the common system definitions](docs/kpp.md).

Chat app builds open the first useful Canvas slice while BUILDING, then keep
Chase working against the remaining recipe obligations. The shared
`kpp build-step` command and bounded `mantleos.kpp.build.run` host driver retain
unmet requirements and acceptance gates. [Canvas construction](docs/canvas-builds.md)
describes the tested sequence and the boundary between local preparation and
the receiving chat host's tools.

```console
python -m mantleos kpp systems
python -m mantleos kpp doctor
python tools/export_kpp.py --output .work/my-standalone-kpp
python tools/export_kpp.py --check .work/my-standalone-kpp
```

## Start here

Python 3.11–3.14. The core has no third-party runtime dependencies.

```powershell
# Windows PowerShell, from this repository
$env:PYTHONPATH = "src"
python -m mantleos demo --output .work/my-first-organism
```

```sh
# Linux or macOS, from this repository
PYTHONPATH=src python -m mantleos demo --output .work/my-first-organism
```

Choose a new output directory on each run. The demonstration builds a synthetic
notebook, edits it without a MIND, recalls its record, retrieves cold memory,
simulates cloud recovery, admits a reviewed tissue change, rolls it back, and
verifies cartridge and Chroma transfers. It uses no network or model provider.
Its `report.json` records the checks. All generated state stays under the chosen
directory, outside Git.

For an installed command, provision the build tools and install locally:

```console
python -m venv .venv
# Activate .venv using your shell, then:
python -m pip install -r requirements-dev.txt
python -m pip install --no-build-isolation --no-deps -e .
mantleos --help
```

Dependency provisioning may need network access. The normal runtime and tests
work offline afterward. The source-based quick start needs no installation.

## Working examples

**New KPP test bake:** [Mantle Paint](examples/paint/README.md), an offline
Bio-Software pixel editor with Windows XP Paint as its Chase target:

```console
python examples/paint/build.py --output .work/my-paint
```

Open the generated `Mantle-Paint.html` in a browser/HTML Canvas, or carry the
adjacent complete `Mantle-Paint.anchor` to another authorized host. The example
includes drawing tools, local organism memory, recovery, tests and an explicit
native-parity gap; it does not claim completed XP equivalence.

```console
python -m mantleos examples demo --output .work/example-collection
python examples/kpp/walkthrough.py --output .work/kpp-example
python -m mantleos examples build notepad --output .work/notepad
python -m mantleos examples run notepad --directory .work/notepad
```

The collection includes portable Engrams, interactive Anchor Notepad, a bounded
Workspace Observer, and a separately provisioned Hermes AppAI. Hermes considers
the whole integrated host its SELF and stays resident while a representative
inspects a specimen. [Working examples](docs/examples.md) covers construction,
private Raven rebirth, host activation, standing mission policy, result review,
transport, and reversible removal. Offline replies are explicitly scripted;
real cognition uses the existing host handoff.

## Scan, create, and carry executable thoughts

For an application with Qt `.ui` sources, investigate code and interface
declarations concurrently with shared source pins:

```console
python -m mantleos scan discover LOCAL_SOURCE --gui-root LOCAL_SOURCE/ui --identity SOURCE_REVISION --output NEW_EXTERNAL_DIRECTORY
python examples/discovery/walkthrough.py --output .work/discovery-example
```

[Concurrent discovery](docs/discovery.md) explains the limits, checked authority,
three-file evidence bundle and equivalent serial timing baseline. Ordinary
`scan inspect` remains available for source trees without Qt.

```console
python examples/thoughts/walkthrough.py --output .work/thought-walkthrough
```

The walkthrough scans a small app, authors `Counter.anchor`, verifies its
self-contained HTML/Python targets in an isolated receiving process, and runs
portable Notepad editing without importing MantleOS. An authorized receiving LLM
can open the carried app using its available tools. Provider-specific reliability
is not assumed. [Executable thoughts](docs/thoughts.md) documents the authoring,
inspection, transfer, and receiving-host workflow.

## Use a Body

```console
mantleos new --identity notebook --output .work/notebook
mantleos --body .work/notebook inspect
mantleos --body .work/notebook run greeting
mantleos --body .work/notebook run notepad --inputs-file examples/notebook/insert.json --commit --request-id first-note
mantleos --body .work/notebook query Observe
mantleos --body .work/notebook save --output .work/notebook.vcw --permit-effect
mantleos --body .work/notebook save --output .work/notebook.png --format chroma --permit-effect
mantleos restore .work/notebook.vcw --output .work/restored
```

`python -m mantleos` is equivalent to `mantleos`. A snapshot contains executable
runtime source and needs Python on its receiving host; no interpreter is bundled.
Restoration verifies content and does not run embedded code. A trusted restored
Body can use `python runtime.py status` without the source repository.

## Python API

```python
from mantleos import organism, lifecycle, evolution

organism.create(".work/api-notebook", identity="api-notebook")
result = lifecycle.run(".work/api-notebook", "greeting")

candidate = organism.notebook_tissue("Ready to remember and reconsider.")
proposal = evolution.propose(".work/api-notebook", candidate)
evidence = evolution.validate(".work/api-notebook", proposal)
# Review the candidate and evidence before this operator-only call:
evolution.apply(".work/api-notebook", proposal, approval=proposal["sha256"])
```

The approval digest binds the operator's decision to exact content. It is not a
signature or a sandbox. A MIND receives a bounded context and returns proposals;
the host must not give it the operator API or unrestricted Python execution.

## Learn and contribute

- [Architecture and evolution](docs/architecture.md): CELL, tissue, organs, carriers, stores.
- [Design philosophy](docs/philosophy.md): a family of expressions, operational metaphors, and evidence boundaries.
- [Interface and format guide](docs/interfaces.md): commands, Python ports, supported formats.
- [Heritage ledger](docs/heritage.md): source map, conflicts, preservation and deferral decisions.
- [Verification](docs/verification.md): executed evidence and limits.
- [Measured Chroma optimization](examples/optimization/README.md): SCAN/Optimizer application, regression checks, and matched timing evidence.
- [Contributing](CONTRIBUTING.md) and [security boundaries](SECURITY.md).

Source and licenses belong in Git. Live identity, personal Engrams, credentials,
snapshots, build outputs, and cold archives do not. Historical projects and their recoverable public-safe histories are preserved in
[archives/](archives/README.md). The current implementation starts at the supplied
23 October 2026 r3 baseline; archived APIs, formats and applications have no compatibility
or migration promise. See [consolidation](docs/CONSOLIDATION.md).


[Notepad Save organs](docs/ORGAN-SAVE.md) demonstrate recipe ownership, fresh SCAN
observations, browser downloads, regression rejection, reviewed source replacement
and restoration while retaining the user's draft. Implementation originates in
KPP and is promoted here as identical shared source.

## Explicit implementation choices

KPP is the development protocol. Recipe/4 records required, preferred or
recommendation choices per component, with optional Anchor binding. Python,
JavaScript, Anchor and declared alternatives are recipe decisions. A Rust
declaration adds no execution backend. See [language choices](docs/LANGUAGE-CHOICES.md).
Use `python -m mantleos kpp language-plan --recipe FILE` for a read-only report.

Selective augmentation and role-neutral Baker responsibility are described in
`docs/ARTISANAL-CONSTRUCTION.md`. Run the synthetic, provider-free example with
`python -m mantleos.augmentation --output UNUSED_DIRECTORY`. Recipe/4 can select
`construction.techniques: []` to refine requirements without Chase.

## Working Engram examples

Try a fresh synthetic Engram in either native VCW cartridge or Chroma PNG form.
Both checked files encode the same Body, Raven persona and empty initial memory;
they contain no inherited conversation, archive or previous identity. These are
working examples of the shared memory and carrier capabilities available as KPP
ingredients. `--persona FILE --persona-name NAME` replaces the default Raven persona.

| KPP carrier ingredient | Download original carrier |
| --- | --- |
| `vcw-cartridge-memory` | [raven-fresh.vcw](https://raw.githubusercontent.com/jodydugas-ctrl/MantleOS/main/examples/engrams/artifacts/raven-fresh.vcw) |
| `chroma-png-memory` | [raven-fresh.vcw.png](https://raw.githubusercontent.com/jodydugas-ctrl/MantleOS/main/examples/engrams/artifacts/raven-fresh.vcw.png) |

Both use `engram-continuity`. Download the original PNG bytes; a resized image or
screenshot does not preserve the encoded carrier. The [generator](examples/engrams/generate.py)
constructs one fresh Body and writes both encodings. Recipes and the generator are
included in normal distributions; the reviewed sample binaries are in repository handoffs.

With MantleOS installed, or `PYTHONPATH=src`, restore into new disposable directories:

```python
from mantleos import cartridge, chromamem, engram

cartridge.unpack("examples/engrams/artifacts/raven-fresh.vcw", ".work/showcase-vcw")
chromamem.extract_body("examples/engrams/artifacts/raven-fresh.vcw.png", ".work/showcase-chroma")
for body in (".work/showcase-vcw", ".work/showcase-chroma"):
    print(cartridge.verify(body))
    assert engram.read(body + "/ENGRAM.jsonl") == []
```

See the [Engram guide](docs/ENGRAM-CARRIERS.md) for generation, custom personas and
an explicit append/save/reload example. Restoration, verification and memory persistence
work offline. Model interaction requires a separately configured host and its permissions.

Evidence: [carrier tests](tests/kpp/test_engram_carriers.py),
[artifact-export tests](tests/test_reviewed_engram_exports.py),
[passing Engram implementation CI](https://github.com/jodydugas-ctrl/MantleOS/actions/runs/40038486205)
and [current main CI](https://github.com/jodydugas-ctrl/MantleOS/actions/workflows/ci.yml?query=branch%3Amain).
Tests and checksums provide evidence; they do not grant Baker or host acceptance.


## Experimental REFLEX qualification

The [qualification guide](docs/REFLEX-QUALIFICATION.md) covers the bounded REFLEX/0.1
compiler/VM, original conformance corpus and native data-only VCW/Chroma examples.
Run `python -m mantleos kpp pantry --id reflex-book` to discover the experimental
ingredient. The [reuse report](docs/REFLEX-REUSE.md) pins current and archived source.
This is not an executable Body profile, production adoption or Baker acceptance.


## REFLEX reference inspector

The bundled experimental toolkit now supports `python -m mantleos reflex-book`.
Run `python -m mantleos reflex-book demo --output .work/new-reflex-demo` for a
synthetic freshness example, then inspect or reproduce its records.
See [the toolkit guide](docs/REFLEX-BOOK.md) and [repository update notes](docs/REFLEX-REFERENCE-UPDATE.md).
Native Body execution remains deferred; evidence does not grant Baker acceptance.

Current release, installed-wheel checks and beginner workflow: [release handoff](docs/RELEASE-HANDOFF.md).
