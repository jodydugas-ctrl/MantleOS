# Apps as executable thoughts

An executable thought is a self-contained Anchor application document. It holds
the complete supported Anchor program, author-compiled HTML/Python targets, their
digests, and a small receiving bridge. It can be inspected, saved, shared with
another authorized host, and reopened without rebuilding the application or
installing MantleOS on that receiving host.

The literal-output `EMIT_TEXT/0.2` profile can carry a newly authored HTML/JS app.
The browser implements that app's behavior; Anchor faithfully emits its declared
payload. This is not a claim that a static scan can automatically reconstruct any
arbitrary application. Notepad has its own complete deterministic profile,
`NOTEPAD_LLM/1.3`, with independently executable editing semantics.

## Scan and author

Set `PYTHONPATH=src` as in README, then use fresh paths:

```console
python -m mantleos scan inspect examples/thoughts --workspace .work/counter-scan
python -m mantleos anchor-code emit --input examples/thoughts/counter.html --name Counter --output .work/Counter.anchor --permit-effect
python -m mantleos anchor-code inspect .work/Counter.anchor
python -m mantleos anchor-code launch .work/Counter.anchor --target html --output .work/Counter.html --permit-effect
```

The bundled Counter is a small new application: add observations and reset the
count. It is a Bio-Software example with page-local state, no credentials, and no
network. A host/model can author a different HTML application and follow the same
path. SCAN retains source analysis, dossiers, tracing, compacting, measured
experiments, semantic-discovery handoffs, and Chase tooling; use `scan --help`
and `blueprint --help` for the supported commands and their bounds.

For Notepad:

```console
python -m mantleos anchor-code app notepad --output .work/Notepad.anchor --permit-effect
python -m mantleos anchor-code launch .work/Notepad.anchor --target python --output .work/notepad.py --permit-effect
python .work/notepad.py
```

Enter `{"op":"INSERT","text":"Remember this thought."}`. It returns a complete
state checkpoint. Python is an optional host implementation of the self-contained
Anchor profile; the profile's rules also travel in the `.anchor` file.

## Receive on another LLM host

Give the receiving host the `.anchor` file and an explicit request to run the app.
Its launch section identifies the complete targets and receiver procedure. With
an authorized Python tool, the carried bridge verifies and writes the selected
target to a new host-approved file. An interactive HTML/Canvas tool can then open
the browser app. Without Python, a host may open the complete Canvas block using
an appropriate HTML tool. Without either capability, report the limitation and
retain the artifact; do not claim it ran.

The author's runtime is not installed by the bridge. Checksums establish payload
integrity, not publisher trust or permission to execute JavaScript/Python. Review
untrusted code under host policy before use. Files cannot bypass host rules.

## Offline proof and limits

```console
python examples/thoughts/walkthrough.py --output .work/thought-walkthrough
```

This runs SCAN, creates Counter and Notepad thoughts, materializes the carried
Counter through the receiver bootstrap in isolated Python (`-I -S`), compares
the received HTML with the authored bytes, executes the standalone Counter emitter,
and checks Notepad edit/undo in another isolated process. No model calls occur.
The Counter's browser buttons require a separate browser interaction check.

Generated app payloads remain complete even though repository templates now
share one Unicode table and generate the repeated Notepad profile on demand.
Cross-provider LLM instruction-following remains host-dependent; offline
receiving-process checks do not certify every model or Canvas integration.
