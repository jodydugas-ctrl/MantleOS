# Concurrent discovery

`scan discover` captures one native SCAN graph and derives both code and Qt
interface views from its pinned bytes. Parallel mode extracts captured files in
two standard-library workers; graph admission and SQLite cache writes remain on
the owning thread. The three-file bundle is published only after complete
pre/post source checks. This reconciles the earlier independent-scanner design
with KPP's maintained canonical scanner. Historical KPP 1.0.1-dev receipts describe
that earlier implementation and do not qualify this revision.

```console
python -m mantleos scan discover PATH_TO_LOCAL_SOURCE --gui-root PATH_TO_LOCAL_SOURCE/ui --identity MY_SOURCE_REVISION --output NEW_EXTERNAL_DIRECTORY
python examples/discovery/walkthrough.py --output .work/discovery-example
```

The GUI root defaults to the source root and must remain inside it. Qt `.ui`
files are required; an unsupported GUI framework produces an explicit error.
Use `scan inspect` for ordinary source investigations without Qt. Existing scan,
Anchor authoring, app creation, portable thoughts and organism commands remain
available. No KPP recipe/acceptance runtime or second SCAN implementation is
installed. No subagents, remote workers, source downloads or services are started.

The new output directory contains exactly:

- `code-scan.json`: the existing `scan.report/1`, usable by trace, plan and other
  native SCAN tools. Unsupported files, including C/C++, retain their paths and
  hashes with explicit coverage gaps.
- `gui-inventory.json`: `kpp.gui-inventory/2`, with widgets, actions, action
  placements/groups, connections and tab order. Entries start with empty Anchor
  links. There is no automatic mapping or approval of requirements.
- `discovery.json`: `mantle.parallel-discovery/1`, binding the shared source
  inventory, native graph digest, coverage gaps, GUI limitations, measurements
  and both file-byte and canonical-JSON hashes of the other artifacts.

The native graph and KPP GUI inventory retain their own schemas. KPP's
`kpp.static-scan/2` is another derived view of that same graph. Its `code`,
`interface` and `data` filters retain the complete source inventory and mark
unselected files FILTERED. Qt and HTML declarations are read by the canonical
interface adapter. KPP recipe acceptance remains downstream review work.

```python
from mantleos import kernel

action = kernel.scan('scan.discover', {
    'source': 'local-source', 'gui_root': 'local-source/ui',
    'identity': 'operator-checked-revision', 'output': 'new-discovery'
}, permit=True)
report = action['observation']['result']
```

This uses the existing checked-action authority interface. A Body must declare
the capability; existing Bodies do not acquire new grants automatically.
Operator diagnostics do not append results into an Engram without separate
memory admission. Discovery does not execute the specimen or enable optional
external parsing providers.

## Scope and failure behavior

Bounded pre/post inventories cover all selected files, using native exclusions
for generated directories, credentials named `.env*`, bytecode and VCS state.
The traversal is capped **before sorting**, prunes excluded subtrees, and refuses
selected symlinks and Windows reparse points. Each read is bounded and checked
for observed size/time changes. Every scanner file hash must match the inventory;
GUI file membership must also match exactly.

Default limits are 1,000 files, 16 MB total, 512 KB per file, 60 seconds and
100,000 graph records. Set `--max-files`, `--max-bytes`, `--max-file-bytes`,
`--max-seconds` and `--max-nodes` to narrower or supported larger limits. The
maximums are 1,000 files, 64 MB, 2 MB per file, 3,600 seconds and 500,000 records;
traversal is capped at 100,000 entries. Qt adds 256-file, 16 MB, nesting and
declaration caps. XML DTDs and entities, including UTF-16 encodings, are refused.
Unlike an ordinary partial SCAN, an incomplete source inventory cannot produce
the joined bundle. Semantic coverage gaps remain disclosed in a valid bundle.

A worker error, observed source drift, pin disagreement or publication failure
produces no completed output bundle. Worker caches and interim reports stay in
a disposable external staging directory. The three-file bundle is renamed into
place after checks; an existing output is refused. A process crash can leave an
orphan staging directory, which is not a completed bundle. No durability or
distributed multiwriter guarantee is claimed.

Checksums identify observed bytes, not trusted authorship or a verified Git
commit. Pre/post checks cannot detect every transient edit reverted between
reads. Keep the selected checkout stable. Deadlines are cooperative checks;
threaded parsing is bounded but cannot be forcibly terminated as a process.
Static declarations do not establish C++ behavior, Qt signal/slot resolution,
runtime GUI coverage or visual fidelity.

## Measure on the intended workload

`--execution serial` uses the same extraction, pins and limits as the default
`parallel` mode. Its sole purpose is an equivalent-scope baseline. The walkthrough
alternates the first runner, uses three fresh workspaces per mode, checks equal
graph/source pins, and records timings in its generated `report.json`.

Only captured-byte per-file extraction moves to the two workers. Source reads,
graph admission and SQLite cache writes stay on the owning thread. Python CPU
work still encounters the interpreter's threading constraints. Measure before adding further workers. There is no universal speed
multiplier and this is not distributed swarm orchestration.
