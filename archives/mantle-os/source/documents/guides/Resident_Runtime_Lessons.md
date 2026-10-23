# Resident Runtime Lessons

Lessons from Mantle/NotepadNext.AppAI that must carry into future residents.
Use this as the tracked companion to local assimilation receipts: every item
names the failure mode, the platform fix, and the prevention rule.

## Conversation and Command Channels

**Failure seen:** ordinary conversational prompts were parsed as app commands or
triggered reflex-style inventory dumps. The resident answered from a maintenance
channel instead of continuing the MIND conversation.

**Fix:** slash-prefixed input is the only terminal command channel. Plain text is
always a user message to the MIND. When plain text asks the resident to act on its
host, the MIND interprets intent against SELF/body evidence and emits a hidden
Body directive; the user does not need to type slash commands for app work.

Mantle now supplies a shared Body control plane in
`mantle.resident.BodyCommandDispatcher`. Its canonical commands are `/key`,
`/model`, `/offline`, `/status`, and `/help`; host residents register additional
Body commands on the same dispatcher. The default model is `openrouter/free`.
`/mind` is a compatibility alias for `/model`, because a failed real-user attempt
showed that the older spelling was discoverable enough to be expected. Help identifies
the alias instead of expanding an unknown-command response into an oversized command
dump.
`/key` supports a terminal-owned hidden-input handoff, and the credential remains
only in `ResidentSessionState` process memory.

**Prevention:** certify every resident with a command-boundary test:

- `/key`, `/help`, `/memory`, `/reset-vcw`, and other maintenance verbs require
  the leading slash.
- `write this in a new tab`, `open the File menu`, and similar prose must stay in
  the conversation lane and may only invoke Body through a MIND-to-Body plan.
- A fallback or offline answer may report a missing Body nerve, but must not
  expose internal directive syntax as the expected user interface.
- Slash commands must not call the provider or consume MIND energy. Accepted,
  refused, failed, and incomplete commands all append a redacted VCW receipt.
- A configuration mutation must append `BODY_CONFIGURATION_CHANGED` and emit
  `body_configuration_changed`; the event contains public state and changed field
  names, never the credential value.
- App working surfaces remain host-specific. The universal maintenance command
  set does not imply that every host has tabs, documents, menus, or other app
  controls.

## Provider Identity and Terminal Output

**Failure seen:** a resident retained only the configured OpenRouter route and discarded
the model name returned by the provider. When asked which model was running, the MIND
could only say it had no sensory evidence. The same captured session contained a C0
control byte in provider prose, rendered by the terminal as `^A`.

**Fix:** normalized usage receipts now preserve `requested_model`, `response_model`,
`generation_model`, `resolved_model`, and `model_evidence`. A provider-reported model is
observed routing evidence, not a verified claim about hidden infrastructure. Resident
protocol helpers redact output and neutralize ANSI, C0/C1, and bidirectional-formatting
controls before display or VCW storage.

**Prevention:** fake-transport tests must use different requested and returned model IDs
and assert both survive. Every provider output boundary must sanitize visible text before
printing, persisting, or assembling it into later context.

## Body Nerves and Surface Truth

**Failure seen:** the resident knew a sample of Qt actions but did not grok its
body. It could report a selected tab while missing the editor text, and it
treated absent sample controls as proof that a feature did not exist.

**Fix:** every user-manipulable surface must be entered into the GUI nerve map:
menus, actions, toolbar buttons, text boxes, tabs, documents, panels, dialogs,
status outputs, shortcuts, and any display whose value can affect user trust.
Each surface needs a VCW status such as `verified_body_operation`,
`observer_registered`, `sense_only`, `not_implemented`, or `maintenance_gap`.

**Prevention:** Phase-0 body work is not complete until each surface has all of:

- discovery evidence naming where it came from;
- a resident-facing SELF entry;
- an observer or a documented maintenance gap;
- an execution nerve only when the Body can prove it;
- a readback or output strategy;
- a VCW event schema for the observation, action proof, and visible result.

Do not answer capability questions from capped samples. Answer from the full
coverage table and separate "I can observe this" from "I can operate this."

## App-Local Vocabulary

**Failure seen:** a NotepadNext resident was asked to delete the current project
and start a new one. It refused literally because NotepadNext is not a
project-based IDE, then guessed the current tab was blank from the tab title.

**Fix:** app-local nouns are part of SELF/body evidence. In a Notepad-like app,
`current project` may safely map to the active document/workspace when the user
does not name a filesystem path, repository, folder, disk, or source project.
The resident should translate to the nearest mapped surface, execute only the
safe app-local operation, and prove the result by Body readback.

**Prevention:** every surface map should carry domain aliases and refusal
boundaries:

- local aliases such as project -> document/workspace for Notepad-style apps;
- hard stops for filesystem words such as repo, directory, path, disk, or drive;
- the Body nerve that implements the translated intent;
- the verifier that proves the translated visible state.

Do not refuse safe intent just because the user's noun is not the host's formal
noun. Do not delete filesystem state unless the user explicitly names a
filesystem target and the resident has a certified destructive-action policy.

## Text Inputs

**Failure seen:** the resident inferred a fresh tab was empty even though the user
had typed text into the editor. It had tab-selection evidence but no committed
text event in the VCW.

**Fix:** text-like surfaces use commit semantics instead of per-keystroke
logging. A `HOST_TEXT_COMMIT` event records the field/editor identity, trigger
(`submit`, `blur`, `focus_lost`, `explicit_readback`, or Body write proof),
length/hash, and bounded text or redacted text according to policy.

**Prevention:** every editable text surface must declare
`commit_policy=submit_or_blur` or an explicit equivalent. Residents may avoid
recording every keypress, but they must record the final user-visible value when
the user submits, leaves the field, changes documents, or asks what is there.
If a live readback nerve is unavailable, the resident must say it cannot read
the current value yet; it must not guess from tab state.

## Opaque Native Controls

**Failure seen:** the packaged Qt NotepadNext window exposed zero editor child
HWNDs, so a Win32 child-control scanner could see the top-level window but not
the `ScintillaNext` editor. The resident therefore failed to clear/read the
actual body surface until another observation channel was added.

**Fix:** the resident added fallback nerves through Windows UI Automation and
clipboard-mediated readback. UIA supplied the opaque editor rectangle and status
labels such as document length; keyboard/clipboard interaction supplied committed
text when available; the status bar supplied empty-document proof when clipboard
copy returned only line endings.

**Prevention:** native GUI certification should not depend on one accessibility
API. For every visible user surface, the nerve map should name primary and
secondary channels when possible: HWND/control text, UI Automation, accessibility
patterns, status labels, clipboard-mediated reads, file/export proof, or
host-native observers. If all channels fail, record a maintenance gap instead of
guessing.

## VCW Continuity

**Failure seen:** the resident wrote conversation events to storage but did not
rehydrate recent VCW history into the MIND prompt. It answered "I have no prior
context" even though the terminal transcript had earlier turns.

**Fix:** before every MIND call, assemble a bounded recent-context block from the
canonical VCW. Include recent user messages, MIND replies, Body action proofs,
surface observations, lifecycle events, and relevant failures. The MIND prompt
must distinguish canonical VCW entries from lossy terminal display text.

**Prevention:** residents need a recall test:

- speak about a topic;
- continue with anaphora such as "what do they mean?";
- ask for the last few exchanged items;
- require the answer to cite recent VCW entries, not terminal scrollback.

Sidecar files and transcripts are mirrors only. A sidecar write failure must be
recorded and fail open so the resident can keep working from canonical VCW. A
canonical VCW write failure is an immune event and must be visible to the MIND.

## Heartbeat Scheduler

**Failure seen:** a resident inherited Mantle's `Heart` organ and passed Body
certification, but the app-specific runtime had no live scheduler. Its terminal
blocked on user input, so no ten-minute MIND/API heartbeat fired during stasis,
unscheduled sensory wakes were not distinct from ordinary chat, and no
`HEARTBEAT_PULSE` stream existed in Prime VCW.

**Fix:** resident Body certification must prove the resident-bound lifecycle,
not only the library organ. A fused resident needs exactly one natural cognitive
heartbeat scheduler with a 600-second cadence. User submits, Senses, Reflexes,
Immune distress, explicit pain, and other significant Body events may add
unscheduled wakes, but those wakes do not move or replace the natural baseline.
Every natural or unscheduled MIND/provider call must record a `HEARTBEAT_PULSE`
receipt in Prime VCW.

**User conversation:** a committed non-command user message is not an ordinary
terminal chat shortcut. It is an unscheduled Heart pulse that wakes cognition
early so the user does not wait for the next natural ten-minute beat. The pulse
may batch committed text, sensory observations, reflex findings, and Body
commands, but it still makes at most one MIND/provider API call.

**Prevention:** every resident heartbeat receipt should include:

- beat number and natural interval;
- wake type: natural or unscheduled;
- wake reason and coordinates;
- the heartbeat command stack for that API call;
- API call count and a batched-command flag;
- provider attempted/result/error and response hash;
- drift for natural beats when measurable.

If the provider key is missing, the heartbeat still records into VCW with
`provider_attempted=false`; the AppAI still ages by recorded experience.

## Shared Primer

**Failure seen:** the Hermes example resident used an older short Primer while
core Mantle residents used the shared AppAI Primer. GitHub CI caught the drift in
the shared-Primer smoke test.

**Fix:** all real AppAI births must use the shared Primer helpers
`appai_truths()` and `appai_commandments()`. Integration addons may use a vendored
runtime helper with an exact text fallback, but they must not invent their own
shortened commandments.

**Prevention:** example residents, adapters, addons, and generated templates must
be covered by Primer parity tests. When the Primer changes, update all tracked
examples and CI smoke tests in the same patch.

## Example and Audit Discipline

Every platform contract change must update the examples and audits that teach the
contract. For the NotepadNext work this meant aligning the example AppAI, Stage-1
certification notes, smoke tests, resident protocol helpers, evidence reports,
and invariant audits.

Minimum regression set for these issues:

- `RESIDENT-RT-1 runtime-protocol` invariants pass.
- `RESIDENT-CMD-1 body-command-control` proves Body-only routing, the
  `openrouter/free` default, extension registration, change visibility, refusal
  receipts, and secret absence.
- GUI coverage reports include text commit policy and body test plan entries.
- Text-surface audits require `HOST_TEXT_COMMIT` coverage.
- Surface maps include app-local aliases and refusal boundaries.
- Opaque native controls have at least one readback/verifier strategy or a
  maintenance gap.
- Resident prompts include recent VCW context before provider calls.
- Resident Body audits prove one 600-second scheduler, unscheduled wake behavior,
  heartbeat command-stack receipts, and `HEARTBEAT_PULSE` VCW persistence.
- Example residents answer from shared Primer text.
- CI checks relevant examples after every push.
