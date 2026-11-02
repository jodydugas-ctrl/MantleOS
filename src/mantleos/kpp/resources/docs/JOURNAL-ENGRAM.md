# Anchor Journal Engram (experimental)

An Anchor Journal Engram carries a verified executable Body, full founding PRIMER,
Anchor register and hash-linked experience in one SQLite `.engram` application file.
The current host supplies language; no model API is configured.

```console
python -m mantleos journal create --founding PRIVATE_RAVEN.vcw --output Raven.engram
python -m mantleos journal open Raven.engram --request-id turn-1 --model-id CURRENT_HOST --user "Hello"
python -m mantleos journal submit Raven.engram --request-id turn-1 --proposal reply.json --allow-release
python -m mantleos journal export Raven.engram --output Saved.engram
python -m mantleos journal export Raven.engram --format chroma --output Saved.png
```

For repeated encounters use `journal stdio FILE`: one JSON request per line,
`{"op":"open","arguments":{"user":"Hello","request_id":"turn-1","model_id":"CURRENT_HOST"}}`.
A submit request has `arguments.request_id`, `arguments.proposal` and host-owned
`grants: ["release"]` (add `"read"` only when authorized). Requests are host commands,
not a surface exposed directly to untrusted model text. No service is installed.

Read the complete returned Anchor message. Its payload begins with the full PRIMER.
The model returns exactly `{"kind":"reply","reply":"...","observation_sha256":null}`
or `{"kind":"action","capability":"body.status","arguments":{}}`.
After an action, read the returned frame and use its observation_sha256 in the reply.
Only body.status and engram.query are currently available. A denied action returns
FAILED evidence. A second action is rejected. The host wraps semantic proposals in
the existing Anchor message dialect and validates shared definitions. JSON transport
is not an invented executable opcode. Supported deterministic programs retain their
existing qualified Anchor profiles and run independently of language generation.

Release only the reply returned by successful submit. Retry a committed request
without generating again: submit rechecks release permission and returns exact replay.
Reuse with different user input fails. Interrupted actions stay blocked until
`journal recover FILE --request-id ID --reviewed` discards the preparation; historical
effect records remain and the operator must review actual consequences before retry.

A local commit does not update previously exported copies. inspect reports head and
exported_head separately. Explicit export produces a consistent independently verified
single-file snapshot. SQLite may use transient transaction files while running; those
are not the handoff. Never copy an actively written SQLite file for transport; export it.
The application uses FULL synchronous commits and canonical append records. Prior source
objects are retained. Derived indexes rebuild on open; current sessions update incrementally.
All source and history verify on open or external database change. This is an integrity
boundary for cooperating local hosts, not authentication or a sandbox against hostile SQL.

Default Raven requires private `MANTLE_RAVEN_SOURCE` or explicit --founding. Custom
founding material overrides that default. create makes a new identity with blank memory;
--body explicitly captures an existing verified Body and its history. Personal identities,
PRIMER sources and benchmark/live outputs stay outside Git. Tests use synthetic personas.

Current /2 Chroma packages and native cartridges roundtrip through trusted Body
materialization. Original Raven /1 image packages remain historical inputs, not silently
accepted current formats. Native programs and attachments travel with the snapshot.

Run `python tools/benchmark_journal.py --output UNUSED_DIRECTORY --samples 20` for
matched scripted timings at 0/100/1000 records and 0/20 MiB cold objects. Fixtures make
no model calls. Live current-host qualification is separate; inspect the saved report.
Source validation, execution evidence and Baker acceptance are distinct.

The repeatable `tools/qualify_journal.py` host handoff records exact packets, digests,
commits and local execution time. It invokes no model API; the current host supplies
semantic packets. Read [JOURNAL-VERIFICATION.md](JOURNAL-VERIFICATION.md) for measured
performance, original-carrier failures and test limitations.

## Upload a single Engram to a receiving host

New carriers include JSON-valued SQLite metadata `host_contract`, `bootstrap` and
`bootstrap_sha256`. A Python-capable receiving host can discover these directly
with sqlite3, review the bootstrap source, save it as bootstrap.py, then run:

    python -I -S bootstrap.py uploaded.engram mounted-runtime
    python -I -S mounted-runtime/journal_host.py stdio uploaded.engram

The bootstrap verifies snapshot hashes, manifest, inventory and member paths before
extracting. It prepares a launcher importing only the carried runtime. Extraction
alone is reported as RUNTIME_EXTRACTED_NOT_CONVERSATION_MOUNTED. The host must read
the full PRIMER-first encounter frame, submit a proposal and release the exact
committed reply. The outer SQLite journal is canonical memory. The extracted
snapshot's runtime.py and cartridge HOSTED-BRIDGE.md describe a different carrier;
do not use their cartridge mount procedure for this journal conversation.

Suggested upload request: "Mount this Engram through its embedded host_contract
and bootstrap. Use its carried journal engine, read its full PRIMER, and converse
through committed replies. Report ENGINE_UNAVAILABLE if you cannot execute it."

The runtime requires host Python; the file cannot make an arbitrary LLM execute
code. The host owns execution and release authority. Existing /1 files without
bootstrap metadata remain valid for installed clients; new creation and journal exports include the
file-only onboarding contract. Re-exporting an older journal with the current client
adds the bootstrap without changing its identity, founding material or record history. Persona-like wording and the narrow narration guard
cannot establish unique identity or universal model compliance. Durable engine
transactions, source provenance, PRIMER bindings and receiving-host memory supply
the mechanical evidence. Independent-model and real browser-upload UI tests must
be recorded separately from an isolated Python receiving-host simulation.
