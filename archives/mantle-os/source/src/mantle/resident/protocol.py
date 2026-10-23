#!/usr/bin/env python3
"""Canonical resident terminal/MIND/Body protocol rules.

These helpers capture the platform lessons from NotepadNext.AppAI without tying
future residents to that host. Generated terminals can use this module for the
three-lane runtime:

* slash-prefixed maintenance commands,
* ordinary prose for MIND conversation,
* hidden MIND-authored Body requests that fail closed and write proof to VCW.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from typing import Any, Dict, Iterable, List, Tuple

from ..core.redact import redact, redact_str


VCW_TEXT_LIMIT = 8000
BODY_DIRECTIVE_RE = re.compile(r"<APPAI_BODY>(.*?)</APPAI_BODY>", re.DOTALL)
ANSI_ESCAPE_RE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))"
)
SECRET_COMMANDS = {"/key", "/secret", "/token", "/password", "/credential"}
TOKEN_STOP_WORDS = frozenset(
    "a an and are as at be can do for from how i in is it me my of on or "
    "please tell the this to use what when where which with you your".split()
)

RESIDENT_RUNTIME_POLICIES = {
    "command_channel_policy": (
        "Only slash-prefixed input is a terminal maintenance/configuration command. "
        "Non-slash user prose is conversation for the resident MIND, never a "
        "deterministic Body/reflex parser input."
    ),
    "body_command_policy": (
        "Slash-prefixed maintenance/configuration commands are handled by the "
        "deterministic Body, never the MIND. Mantle residents share a small canonical "
        "command set and may register host-specific Body commands. Every command "
        "outcome and configuration change is redacted and appended to Prime VCW."
    ),
    "mind_body_lane_policy": (
        "Effectful host mutation flows through a hidden MIND-authored Body request "
        "lane. User prose may ask; MIND selects mapped Body nerves; Body executes "
        "and proves."
    ),
    "directive_fail_closed_policy": (
        "Any detected hidden Body directive is stripped from visible output. Raw or "
        "escaped JSON may execute; malformed directives produce a bounded Body "
        "failure proof, never leaked tool syntax."
    ),
    "transcript_vcw_policy": (
        "Sidecar logs are mirrors only. Committed user submits, MIND responses, "
        "Body requests/proofs, lifecycle boundaries, configuration changes, "
        "surface observations, failures, and visible outputs must be recorded into "
        "the current Prime VCW first-class event stream."
    ),
    "secret_boundary_policy": (
        "Secret-bearing commands are sanitized before transcript/VCW storage. Raw "
        "keys belong in session memory, environment variables, OS credentials, or "
        "another explicit secret boundary; VCW stores only redacted text and hashes."
    ),
    "surface_retrieval_policy": (
        "MIND capability answers and Body planning retrieve from the complete "
        "surface map. Capped samples are display summaries only and cannot support "
        "absence claims."
    ),
    "body_proof_policy": (
        "A Body operation may report ok=true only after target surface, action, "
        "pre/post state, visible output/state variables, and VCW proof write are "
        "represented in the proof record."
    ),
    "text_commit_policy": (
        "Text inputs do not write every keypress into VCW. They record one durable "
        "text value when the user submits, the input loses focus/blur commits, a "
        "declared low-volume host boundary fires, or Body performs an explicit "
        "readback proof."
    ),
    "mind_context_rehydration_policy": (
        "Before every resident MIND call, Body reads a bounded recent slice from the "
        "current Prime VCW event stream and places it in the MIND context. A resident "
        "must not answer continuity, pronoun, or 'what did we discuss' questions from "
        "provider session memory or sidecar transcripts alone."
    ),
    "heartbeat_scheduler_policy": (
        "A fused resident Body owns exactly one natural cognitive heartbeat scheduler "
        "with a 600-second cadence. Body, Senses, Reflexes, Immune distress, user "
        "submits, and explicit pain may add unscheduled wakes, but these never move "
        "or replace the natural baseline. A committed non-command user submit is an "
        "unscheduled heartbeat so conversation does not wait for the next natural tick. "
        "Each heartbeat makes at most one MIND/provider API call; Body commands and "
        "sensory/reflex observations are batched inside that pulse. Every natural or "
        "unscheduled MIND/provider call records a HEARTBEAT_PULSE receipt in the current "
        "Prime VCW, including wake reason, command stack, provider attempt/result, API "
        "call count, batched-command flag, and drift where applicable."
    ),
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sanitize_visible_text(text: str, *, limit: int = VCW_TEXT_LIMIT) -> str:
    """Redact and neutralize terminal-control text from an untrusted source."""
    if limit <= 0:
        raise ValueError("visible text limit must be positive")
    cleaned = ANSI_ESCAPE_RE.sub("", redact_str(str(text or "")))
    bidi_controls = {0x061C, 0x200E, 0x200F, *range(0x202A, 0x202F),
                     *range(0x2066, 0x206A)}
    safe = "".join(
        char if (
            char in "\n\r\t" or
            (ord(char) >= 0x20 and not 0x7F <= ord(char) <= 0x9F and
             ord(char) not in bidi_controls)
        ) else "\ufffd"
        for char in cleaned
    )
    return safe[:limit]


def sanitize_user_submit(text: str) -> str:
    """Redact secret-bearing command payloads before durable logging."""
    raw = str(text or "")
    stripped = raw.strip()
    if not stripped.startswith("/"):
        return sanitize_visible_text(raw)
    command = stripped.split(None, 1)[0].lower()
    if command in SECRET_COMMANDS:
        return "%s [REDACTED_SECRET]" % command
    return sanitize_visible_text(raw)


def classify_user_submit(text: str) -> Dict[str, Any]:
    """Classify one committed Enter submit for resident routing."""
    raw = str(text or "")
    stripped = raw.strip()
    is_command = stripped.startswith("/")
    command = stripped.split(None, 1)[0].lower() if is_command else ""
    return {
        "kind": "terminal_command" if is_command else "mind_conversation",
        "is_command": is_command,
        "command": command,
        "sanitized_text": sanitize_user_submit(raw),
        "raw_sha256": _sha256(raw),
        "policy": (
            RESIDENT_RUNTIME_POLICIES["command_channel_policy"]
            if not is_command else
            "slash-prefixed terminal maintenance/configuration command"
        ),
    }


def _loads_directive_payload(raw_payload: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError:
        try:
            unescaped = raw_payload.replace(r"\"", '"')
            parsed = json.loads(unescaped)
        except json.JSONDecodeError as exc:
            raise ValueError("MIND Body request was malformed") from exc
    if not isinstance(parsed, dict):
        raise ValueError("MIND Body request must be a JSON object")
    if not str(parsed.get("action") or "").strip():
        raise ValueError("MIND Body request is missing action")
    return parsed


def parse_mind_body_directives(text: str) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Strip and parse hidden MIND-to-Body directives.

    Returns `(visible_text, requests, errors)`. Detected directives never remain
    in `visible_text`, even when malformed.
    """
    source = str(text or "")
    requests: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    def repl(match: re.Match[str]) -> str:
        raw_payload = match.group(1).strip()
        try:
            payload = _loads_directive_payload(raw_payload)
            requests.append(payload)
        except ValueError as exc:
            errors.append({
                "ok": False,
                "error": str(exc),
                "raw_sha256": _sha256(raw_payload),
                "visible_message": "Body proof failed: %s." % str(exc),
            })
        return ""

    visible = sanitize_visible_text(BODY_DIRECTIVE_RE.sub(repl, source)).strip()
    return visible, requests, errors


def resident_vcw_event(kind: str,
                       payload: Dict[str, Any] | None = None,
                       *,
                       text: str = "",
                       source: str = "resident-runtime",
                       ok: bool | None = None) -> Dict[str, Any]:
    """Build a bounded/redacted event payload suitable for `memory.remember`."""
    redacted = sanitize_user_submit(text)
    event: Dict[str, Any] = {
        "kind": str(kind),
        "source": source,
        "observed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "policy": RESIDENT_RUNTIME_POLICIES["transcript_vcw_policy"],
        "payload": redact(dict(payload or {})),
    }
    if ok is not None:
        event["ok"] = bool(ok)
    if text:
        event["text"] = redacted[:VCW_TEXT_LIMIT]
        event["text_sha256"] = _sha256(redacted)
        event["redacted"] = redacted != text
    return event


def text_commit_event(surface_id: str,
                      text: str,
                      *,
                      boundary: str,
                      source: str = "resident-text-surface",
                      payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build a VCW event for committed text without logging per-key input."""
    event_payload = {
        "surface": surface_id,
        "commit_boundary": boundary,
        "commit_policy": "submit_or_blur",
        "policy": RESIDENT_RUNTIME_POLICIES["text_commit_policy"],
    }
    event_payload.update(payload or {})
    return resident_vcw_event(
        "HOST_TEXT_COMMIT",
        event_payload,
        text=text,
        source=source,
        ok=True,
    )


def heartbeat_pulse_event(beat_number: int,
                          *,
                          wake: Dict[str, Any] | None = None,
                          provider_attempted: bool,
                          provider_ok: bool,
                          command_stack: List[str] | None = None,
                          api_call_count: int | None = None,
                          commands_batched: bool = True,
                          interval_seconds: int = 600,
                          source: str = "resident-heartbeat",
                          payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build a VCW event for natural or unscheduled resident Heart pulses."""
    event_payload = {
        "beat_number": int(beat_number),
        "interval_seconds": int(interval_seconds),
        "wake_type": "unscheduled" if wake else "natural",
        "wake": dict(wake or {}),
        "provider_attempted": bool(provider_attempted),
        "provider_ok": bool(provider_ok),
        "api_call_count": int(api_call_count if api_call_count is not None else (1 if provider_attempted else 0)),
        "commands_batched": bool(commands_batched),
        "command_stack": list(command_stack or []),
        "policy": RESIDENT_RUNTIME_POLICIES["heartbeat_scheduler_policy"],
    }
    event_payload.update(payload or {})
    return resident_vcw_event(
        "HEARTBEAT_PULSE",
        event_payload,
        source=source,
        ok=True,
    )


def _event_content(entry: Dict[str, Any]) -> Dict[str, Any]:
    content = entry.get("content")
    return content if isinstance(content, dict) else {}


def _event_text(entry: Dict[str, Any]) -> str:
    content = _event_content(entry)
    return str(content.get("text") or content.get("message") or "")


def recent_conversation_events(events: Iterable[Dict[str, Any]],
                               *,
                               current_user_text: str = "",
                               limit: int = 12,
                               include_commands: bool = False) -> List[Dict[str, Any]]:
    """Return recent USER/MIND turns from VCW entries, excluding current submit once.

    Resident terminals usually append the current user submit before they build the
    MIND prompt. For continuity, the recent-history slice should describe prior
    conversation; the current turn is supplied separately as the active user prompt.
    """
    selected: List[Dict[str, Any]] = []
    skipped_current = False
    current = str(current_user_text or "")
    for entry in reversed(list(events or [])):
        opcode = str(entry.get("opcode") or "")
        if opcode not in {"USER_MESSAGE", "MIND_RESPONSE"}:
            continue
        text = _event_text(entry)
        if not text:
            continue
        marker = _event_content(entry).get("marker")
        is_slash_command = (
            isinstance(marker, dict) and bool(marker.get("slash_command"))
        ) or text.strip().startswith("/")
        if not include_commands and opcode == "USER_MESSAGE" and is_slash_command:
            continue
        if not skipped_current and current and opcode == "USER_MESSAGE" and text == current:
            skipped_current = True
            continue
        selected.append({
            "opcode": opcode,
            "role": "user" if opcode == "USER_MESSAGE" else "mind",
            "text": text,
            "ts": _event_content(entry).get("ts") or entry.get("ts"),
            "id": entry.get("id"),
        })
        if len(selected) >= limit:
            break
    return list(reversed(selected))


def render_recent_vcw_context(events: Iterable[Dict[str, Any]],
                              *,
                              current_user_text: str = "",
                              limit: int = 12,
                              text_limit: int = 900) -> str:
    """Render bounded recent VCW conversation for a resident MIND prompt."""
    recent = recent_conversation_events(
        events,
        current_user_text=current_user_text,
        limit=limit,
    )
    if not recent:
        return (
            "Recent VCW conversation before this user turn: none found in the "
            "current Prime VCW event stream."
        )
    lines = [
        "Recent VCW conversation before this user turn "
        "(canonical memory, newest entries included last):"
    ]
    for event in recent:
        text = event["text"]
        if len(text) > text_limit:
            text = text[:text_limit] + " ...[truncated]"
        lines.append("- %s: %s" % (event["role"], text.replace("\n", "\\n")))
    return "\n".join(lines)


def _query_tokens(query: str) -> List[str]:
    return [
        token for token in re.findall(r"[a-z0-9_]+", str(query or "").lower())
        if token not in TOKEN_STOP_WORDS
    ]


def _surface_haystack(surface: Dict[str, Any]) -> str:
    values = [
        surface.get("id"),
        surface.get("label"),
        surface.get("surface_type"),
        surface.get("kind"),
        surface.get("class"),
        surface.get("shortcut"),
        " ".join(str(p) for p in surface.get("placements", []) or []),
    ]
    return " ".join(str(value or "") for value in values).lower()


def relevant_surface_slice(coverage: Dict[str, Any],
                           query: str,
                           *,
                           limit: int = 12) -> List[Dict[str, Any]]:
    """Retrieve relevant surfaces from the complete GUI coverage map."""
    tokens = _query_tokens(query)
    surfaces = list(coverage.get("surfaces") or [])
    if not tokens:
        return surfaces[:limit]
    scored = []
    for surface in surfaces:
        hay = _surface_haystack(surface)
        score = 0
        for token in tokens:
            if token in str(surface.get("id", "")).lower():
                score += 4
            elif token in str(surface.get("label", "")).lower():
                score += 3
            elif token in hay:
                score += 1
        if score:
            scored.append((score, surface))
    scored.sort(key=lambda item: (-item[0], str(item[1].get("id") or "")))
    return [surface for _score, surface in scored[:limit]]


def surface_slice_prompt(surfaces: Iterable[Dict[str, Any]]) -> str:
    """Render a compact MIND evidence slice without implying absence."""
    rows = []
    for surface in surfaces:
        rows.append("- `%s` label=%r status=%s risk=%s shortcut=%r placements=%s" % (
            surface.get("id"),
            surface.get("label"),
            surface.get("vcw_status"),
            surface.get("risk"),
            surface.get("shortcut", ""),
            surface.get("placements", []),
        ))
    return "\n".join(rows)
