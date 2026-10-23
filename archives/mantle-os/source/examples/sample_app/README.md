# Mantle OS Sample App

This directory is the canonical Path-B teaching host for Mantle OS. It is deliberately
ordinary application code, not Mantle code: a coding agent should be able to dissect it,
map its surfaces to organs, and preserve host behavior while adding Mantle residency.

## Why This Example Exists

Use this example when an agent needs to learn the assimilation path from
The Mantle Grimoire:

```bash
$env:PYTHONPATH="src"
python -m mantle assimilate examples/sample_app --dry-run
python -m mantle assimilate examples/sample_app --out=assimilation
python -m mantle anchor examples/sample_app
python -m mantle lifecycle authorize graft examples/eggs/notes_graft.json workspace/sample_app --approve --out=graft-auth.json
python -m mantle graft examples/eggs/notes_graft.json examples/sample_app --workspace=workspace --auth=graft-auth.json
```

The first command must modify zero host files. Hooking and anchoring are only lawful after
the read-only inventory exists. External grafting additionally requires a fresh one-shot
authorization bound to the artifact and exact promoted target; the original host remains
unchanged.

## Expected Organ Map

| Host surface | Expected role | Mantle organ | Why it matters |
| --- | --- | --- | --- |
| `main_loop` / `mainLoop` | `HEARTBEAT` | Heart | The host's pulse or scheduler. |
| `handle_create_note` / `handleCreateNote` | `SENSOR_EVENT` | Senses | Inbound request boundary. |
| `on_timer_tick` / `onTimerTick` | `HEARTBEAT` | Heart | Scheduled pulse/tick surface. |
| `set_note` / `setNote` | `STATE_TRANSITION` | Memory | Mutates in-memory state. |
| `update_note` / `updateNote` | `STATE_TRANSITION` | Memory | Mutates existing state. |
| `save_notes` / `saveNotes` | `PERSISTENCE_WRITE` | Memory | Writes durable state. |
| `validate_note` / `validateNote` | `ERROR_DEFENSE` | Immune | Rejects invalid input. |
| `sanitize_note_text` / `sanitizeNoteText` | `ERROR_DEFENSE` | Immune | Normalizes untrusted input. |
| `check_auth_token` / `checkAuthToken` | `SECRET_BOUNDARY` | Immune | Crosses credential material. |
| `send_notification` / `sendNotification` | `ARM_ACTION` | Limbs | External effect. |
| `render_note_list` / `renderNoteList` | `DISPLAY_RENDER` | Limbs | Human-visible output. |
| `suggest_tags_with_llm` / `suggestTagsWithLlm` | `MIND_AFFORDANCE` | Brain | Dormant judgment point; not Phase-1 logic. |
| `summarize_notes` / `summarizeNotes` | `INTERNAL_UTILITY` | External host code | Useful helper, not an organ boundary. |

The Python and JavaScript twins should produce the same organ counts when the optional
tree-sitter scanner is installed. Without tree-sitter, the Python path remains the
ground-truth fixture.

## Agent Guidance

Before changing this example, preserve these invariants:

- It stays a plain notes app. Do not import `mantle` into the host.
- The app remains safe to run locally and writes only `notes.json`, which the script cleans up.
- Python and JavaScript twins stay role-equivalent.
- The MIND affordance is visible but dormant; Phase 1 must not depend on it.
- Secrets are example-only and must never become real credentials.

When an assimilator output disagrees with this README, treat the disagreement as evidence:
either the example drifted, or the scanner's deterministic role evidence needs updating.
