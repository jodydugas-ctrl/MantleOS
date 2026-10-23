# Mantle Notepad AppAI Stage-1 Body Certification

## AppAI Declaration

- Target language: browser JavaScript
- Target runtime: static HTML/CSS/JavaScript in a modern browser
- Host path: `examples/notepad_appai/index.html`
- Target storage: browser memory, localStorage append-only ledger, operator-selected text files
- Body mode: standard Phase-1 Body
- Budget policy: sleep; no model calls, no hidden network, no API key requirement
- DNR policy: operator-defined; no reconstruction or MIND fusion without fresh, target-bound operator and guardian approvals
- MIND state: dormant readiness surface only

## Organ Map

| Organ | Body responsibility |
|---|---|
| Heart | App boot, UI refresh, before-close guard |
| Genome | App identity, settings, budget policy, DNR policy, embedded declaration |
| Senses | Keyboard input, menu actions, file-open events |
| Memory | Current document state, settings, recent file name, append-only ledger |
| Immune | File safety checks, bad/locked file errors, large-file guard, redaction boundary |
| Limbs | Open, save, save-as, download fallback, clipboard commands, close guard |
| Brain | Dormant Phase-2 affordance; no model call or mutation authority |

## Parity Matrix

| Feature | Expected classic Notepad behavior | Implemented behavior | Test/evidence | Status |
|---|---|---|---|---|
| New | Clears document after unsaved prompt | `newFile` confirms dirty state, clears buffer, resets filename | `notepad_appai_smoke.mjs` | PASS |
| Open | Loads plain text | File picker/File object text load, 5 MB guard, errors caught | `notepad_appai_smoke.mjs` | PASS |
| Save | Writes current document | Body/Limb save path, File System Access or adapter/fallback | `notepad_appai_smoke.mjs` | PASS |
| Save As | Prompts destination and writes | Body/Limb save-as path, proof emitted | `notepad_appai_smoke.mjs` | PASS |
| Plain text | No rich text | `<textarea>`, `text/plain;charset=utf-8`, no formatting in buffer | manual + smoke test | PASS |
| Unsaved detection | Dirty marker and confirm before destructive action | saved-buffer comparison, New/Open/Close guard, `beforeunload` | `notepad_appai_smoke.mjs` | PASS |
| Clean text commits | Text input should not append VCW/ledger rows per keystroke | editor input updates dirty UI only; one `HOST_TEXT_COMMIT` row with `commit_policy=submit_or_blur` is appended on blur or save/open/new proof actions; legacy `buffer_changed` and `buffer_committed` rows are migrated on load | `notepad_appai_smoke.mjs` | PASS |
| Cut/copy/paste/delete/select all/undo | Basic editing commands | Clipboard/selection commands plus native undo | manual inspection | PASS |
| Find/Find Next | Select next matching text | deterministic string search with wrap-around | `notepad_appai_smoke.mjs` | PASS |
| Replace | Replace current/all matches | deterministic current/all replacement | `notepad_appai_smoke.mjs` | PASS |
| Go To line | Moves caret to line | line offset calculation | `notepad_appai_smoke.mjs` | PASS |
| Time/Date | Inserts local time/date | F5/menu insertion at selection | manual inspection | PASS |
| Word Wrap | Toggles wrapping | CSS/wrap toggle and status update | `notepad_appai_smoke.mjs` | PASS |
| Resident host consultation | Software/body questions answered from resident evidence first | Embedded host evidence index and `consultHostEvidence()` API | `notepad_appai_smoke.mjs` | PASS |
| Font selection | Basic font family/size | dialog applies editor font settings | manual inspection | PASS |
| Status bar | Shows position/encoding/line endings/wrap/MIND | status bar with toggled visibility | manual inspection | PASS |
| File errors | Missing/locked/bad path handled gracefully | failures become immune events and failed proof records | `notepad_appai_smoke.mjs` | PASS |
| Phase-1 no LLM | App launches/works without keys or model calls | no fetch/XHR/WebSocket path in app code; external requests observed as zero | `notepad_appai_smoke.mjs` | PASS |

## Action Execution Proofs

Effectful limb actions emit append-only proof records with:

- `action_id`
- attempted/ok
- method
- redacted ref
- reason
- actor/authorship
- timestamp
- evidence, including byte counts and SHA-256 hashes for saves

Covered actions: open, failed open, save, save-as.

## Stage-1 Gate

| Gate | Evidence | Verdict |
|---|---|---|
| Body launches with no MIND | Static app boot, embedded declaration | PASS |
| Core editing works | Playwright buffer/edit assertions | PASS |
| File actions are Body/Limb actions | Save/open proofs in ledger | PASS |
| Unsaved-change prompts work | rejected and accepted New flow tested | PASS |
| AppAI declaration exists | JSON declaration parsed in test | PASS |
| Organ map exists | JSON organ map parsed in test | PASS |
| Host evidence index exists | JSON evidence index parsed; structure/control answers use it | PASS |
| No hidden model/network call | Playwright observed zero external requests | PASS |
| MIND dormant | `brainStatus()` reports dormant/no mutation authority | PASS |

## MIND Readiness Report

The Body is ready to be considered for a separate `Vocare` cast. Phase 2 is not authorized here.

Potential future Brain intentions, after fresh technical evidence and explicit target-bound operator and guardian approvals:

- summarize note
- suggest title
- extract tasks
- rewrite selected text
- answer questions about current note

Containment rule: MIND may propose intentions only. Body must apply, verify, record, and enforce.

## Final Grimoire Receipt

WHAT:
- Built a clean-room Notepad-style Mantle OS/AppAI Body at `examples/notepad_appai/index.html`.
- Added Stage-1 certification evidence in this file.
- Added Playwright verification at `examples/tests/notepad_appai_smoke.mjs`.

WHY:
- The operator requested a deterministic Phase-1 Body with classic Notepad feature parity, AppAI declaration, organ map, proof records, and no MIND fusion.

EVIDENCE:
- Embedded AppAI declaration, organ map, and parity matrix in `index.html`.
- Embedded host evidence index and local-first consultation API for software/body questions.
- Append-only ledger and Action Execution Proof records for effectful file actions.
- Smoke test covers launch, edit, clean `HOST_TEXT_COMMIT` behavior on blur, no per-keystroke text ledger writes, new/open/save/save-as, unsaved guard, find/replace, word wrap, file error handling, declaration, organ map, host evidence consultation, dormant Brain, and no external network.

TESTS:
- `python -m http.server 8765 --directory examples`
- `cd examples/tests`
- `node notepad_appai_smoke.mjs`

RISKS:
- Browser save/open behavior depends on File System Access API support; fallback behavior is used where unsupported.
- Clipboard commands depend on browser permission policy.
- This is a web AppAI demo, not a native Windows binary.

OPEN QUESTIONS:
- Whether a native shell wrapper is desired later.
- Whether Phase 2 should ever be authorized through a separate `Vocare` cast.

CONFIDENCE:
- High for deterministic Body behavior covered by smoke tests.
- Medium for exact native-desktop parity because browser security limits file and clipboard surfaces.

NEXT:
- Stop after Stage-1 certification. Do not fuse MIND without fresh technical evidence and explicit target-bound operator and guardian approvals.
