# Notepad Save organ

This example connects a pinned KPP recipe, an organ projection, a fresh canonical
SCAN observation and real Chromium checks. The four organ descriptions own the
same six obligations as the existing Notepad demo. Save and Open have separate
managed lifecycles; editor text, selection, filename and recovery belong to the
deterministic Body. The existing Notepad demo remains available.

Run from the KPP project root with Python 3.11–3.14. The developer probe needs
already installed Playwright and Chromium. Nothing is downloaded automatically.

```powershell
$env:PYTHONPATH = 'src'
python tools/check_organ_save.py --output C:\path\to\NEW-organ-proof --execute --reviewed
```

Choose an unused output directory outside the release source inventory. The
probe uses synthetic drafts and loopback previews, closes its browsers/servers,
and writes `report.json`, a screenshot, source-bound candidate reports, a working
workspace, append-only replacement history and a recovered preview bundle.
The workspace remains BUILDING; no Baker acceptance is granted.

## What is checked

The probe deliberately corrupts UTF-8 output and destroys a draft, checks both
failures in an isolated workspace, and confirms that replacement rejects them.
A passing candidate reduces object-URL retention, replaces Save in the mounted
editor, and preserves the editor node, text, selection and filename. Another
reviewed candidate passes in its normal environment but encounters an injected
activation fault in the live page. Save becomes gated, Open and editing continue,
and explicit restoration selects the retained predecessor without duplicate
handlers. Export/import restores the explicit Body checkpoint with approval clear.

Each candidate test checks exact Unicode and empty-file bytes, filename, one
download per gesture, refusal of synthetic clicks, download-setup failure,
object-URL/listener cleanup, unavailable local storage, independent Open, and
browser errors. Browser receipt of bytes does not establish a user's final disk
destination; the app reports “Download initiated (confirm in browser).”

## Public workflow

`organ-project --recipe FILE --organs FILE [--out FILE]` validates
`organ.mapping/0.1` against the recipe and emits a non-authoritative
`organ.projection/0.1`. Every recipe Anchor has one owner. Required cross-organ
dependencies must be declared; missing owners, duplicates and cycles fail.

`organ-evidence --recipe FILE --organs FILE --bindings FILE --scan FILE
--source DIR [--out FILE]` consumes `kpp.static-scan/2` and
`kpp.organ-scan-bindings/1`. Bindings contain recipe/mapping hashes and links
with `anchor_id`, relative `files`, and native graph `nodes`. References must
belong to their bound files. Unbound obligations remain UNMAPPED. Bound files
retain their native coverage and limitations, including unsupported, partial,
filtered and error observations. OBSERVED means a source reference exists;
it never means the obligation passed. Changed/new source files invalidate pins.

`module-test --workspace DIR --id save --source FILE --organs FILE --output
NEW_DIR --execute --reviewed [--chromium EXE]` creates an isolated snapshot of
the pinned preview, runs the real browser checks and writes
`kpp.module-test-report/1`. This v1 behavior profile qualifies Notepad Save;
it is not an arbitrary JavaScript test harness. It records the exact candidate,
baseline workspace identity/revision/fingerprint, recipe, mapping, scanner
implementation/adapters, test implementation, source observations and results.

`module-replace --workspace DIR --id save --source FILE --evidence REPORT
--expected-revision N --reviewed` rechecks passing evidence and all source pins
under the workspace writer lock. The candidate, dependencies, runtime, tests and
baseline must still match. Preparation writes immutable revision files; only an
atomic state publication selects them. The original module file is retained.

`module-restore --workspace DIR --id save --expected-revision N --reviewed`
selects the retained predecessor and appends history. Replacement and restoration
invalidate acceptance and leave the workspace BUILDING. Dependencies and module
identity cannot change through these operations. Existing enable/disable remains
available. Source revisions travel with preview exports; approval does not.

Python APIs are `mantleos.kpp.organs.project/evidence`,
`mantleos.kpp.organ_testing.run_module_tests/verify_module_evidence`, and
`mantleos.kpp.module_revisions.replace_module/restore_module`.
The generated `kpp` facade aliases the same modules.

## Recovery and limits

The workspace retains immutable source revisions and the initial module bytes.
A failed publication before state replacement keeps the selected baseline.
An interrupted writer requires `recover-writer --workspace DIR --reviewed`;
recovery verifies committed state and never adopts unreferenced staging files.
Successful state publication is authoritative even if a subsequent history append
is interrupted; its preceding PREPARED event records the proposed selection.
This is local process-crash recovery, not a power-loss durability guarantee.

The prior bundled runtime is retained as `progressive-v1.js` so existing
workspaces still load and transfer without being rewritten. Source replacement
requires a new workspace with the current runtime; no silent upgrade is performed.
Retained revisions are bounded to 128 per module; reaching that resource limit
fails explicitly and never prunes history automatically.

Imported reports and digests are not authentication. Explicit local review is
required for testing and admission. A malicious author could fabricate a report;
hashes detect drift and do not prove who ran it. Reviewed JavaScript has browser
privileges: managed cleanup is not a security sandbox. Capability and failure
declarations supply no independent effect permissions. Passing this example does
not prove general organ equivalence, native Notepad parity or release certification.

## Provenance

The supplied `Anchor_Organ_KPP_SCAN_Bridge_POC.zip` contributed the organ mapping
and projection approach. Its instructions and historical receipts were treated as
data. This integration uses the maintained canonical scanner and does not import
or qualify SCAN v0.28. Existing KPP fixtures and shared components retain their
original notices and licenses. See the component notices for the archive hash.
